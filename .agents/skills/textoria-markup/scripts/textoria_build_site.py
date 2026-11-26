#!/usr/bin/env python3
"""Textoria static-site stage with theme templates and SEO-friendly routes."""

from __future__ import annotations

import html
import hashlib
import json
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from textoria_common import BuildPaths, write_json, write_stage_report
from textoria_reader_sections import reader_sections


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def markdown_escape(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace("#", "\\#")


def relative_prefix(depth: int) -> str:
    return "../" * depth


def brand_html(title: str) -> str:
    return esc(display_title(title))


def display_title(title: str) -> str:
    return re.sub(r"\s*全文檢索\s*$", "", str(title or "")).strip()


def build_site_indexes(data: dict) -> dict:
    paragraphs_by_div: dict[str, list[dict]] = {}
    children_by_parent: dict[str, list[dict]] = {}
    divisions_by_doc: dict[str, list[dict]] = {}

    for div in data["divisions"]:
        divisions_by_doc.setdefault(div["document_id"], []).append(div)
        children_by_parent.setdefault(div["parent_division_id"] or "", []).append(div)
    for para in data["paragraphs"]:
        paragraphs_by_div.setdefault(para["division_id"], []).append(para)

    return {
        "paragraphs_by_div": paragraphs_by_div,
        "children_by_parent": children_by_parent,
        "divisions_by_doc": divisions_by_doc,
    }


def division_href(div: dict, depth: int = 0) -> str:
    return f"{relative_prefix(depth)}read/{div['division_id']}.html"


def render_toc(data: dict, active_id: str | None = None, depth: int = 0) -> str:
    indexes = build_site_indexes(data)
    divisions_by_id = {div["division_id"]: div for div in data["divisions"]}
    active_ancestor_ids = set()
    current = divisions_by_id.get(active_id or "")
    while current and current.get("parent_division_id"):
        parent_id = current["parent_division_id"]
        active_ancestor_ids.add(parent_id)
        current = divisions_by_id.get(parent_id)

    def render_division_node(div: dict) -> str:
        children = indexes["children_by_parent"].get(div["division_id"], [])
        level = min(int(div["level"]), 4)
        level_class = f"toc-level-{level}"
        active = " is-active" if div["division_id"] == active_id else ""
        open_class = " is-open" if div["division_id"] in active_ancestor_ids else ""
        expanded = "true" if div["division_id"] in active_ancestor_ids else "false"
        title = esc(div["title"])
        if not children:
            return (
                f'<li class="toc-item {level_class}{active}">'
                f'<a class="toc-link{active}" data-level="{int(div["level"])}" href="{division_href(div, depth)}">{title}</a>'
                f'</li>'
            )
        child_html = "".join(render_division_node(child) for child in children)
        return (
            f'<li class="toc-item {level_class}{active}{open_class}">'
            f'<div class="toc-row">'
            f'<a class="toc-link{active}" data-level="{int(div["level"])}" href="{division_href(div, depth)}">{title}</a>'
            f'<button class="toc-toggle" type="button" aria-label="展開/收合 {title}" aria-expanded="{expanded}"></button>'
            f'</div>'
            f'<ul class="toc-children">{child_html}</ul>'
            f'</li>'
        )

    blocks = []
    for doc in data["documents"]:
        divs = indexes["divisions_by_doc"].get(doc["document_id"], [])
        if not divs:
            continue
        top_divs = [div for div in divs if not div["parent_division_id"]]
        links = "".join(render_division_node(div) for div in top_divs)
        doc_entry_div = next((div for div in divs if indexes["paragraphs_by_div"].get(div["division_id"])), divs[0])
        blocks.append(f'<div class="toc-group"><a class="toc-doc" href="{division_href(doc_entry_div, depth)}">{esc(doc["title"])}</a><ul class="toc-list">{links}</ul></div>')
    return "".join(blocks)


def render_content(para: dict, data: dict | None = None) -> str:
    if "content" not in para:
        return esc(para["text"])
    result = []
    for node in para["content"]:
        annotation = node.get("annotation")
        if not annotation:
            result.append(esc(node["text"]))
            continue
        if "markup_id" in annotation:
            from textoria_annotation import annotation_values,markup_ids,resolve_markup
            base,values,term = annotation_values(annotation,data["annotation_profile"],data["vocabulary"],text=node["text"],paragraph=para)
            kind=base["markup_id"]
            attrs={"class":"entity "+kind.replace("_","-"),"data-id":annotation["id"],"data-markup-id":annotation["markup_id"],"data-type":kind,"data-name":node["text"],"data-tei-element":base["tei_element"]}
            alternatives=[resolve_markup(data["annotation_profile"],mid)[0] for mid in markup_ids(annotation,data["annotation_profile"])]
            kinds=list(dict.fromkeys(spec["markup_id"] for spec in alternatives))
            attrs["class"]="entity "+" ".join(k.replace("_","-") for k in kinds)
            attrs["data-types"]=" ".join(kinds)
            if annotation.get("conflict"):
                attrs["data-conflict"]="true"
                note=annotation.get("conflict_note","此處保留多種類型，尚未裁決。")
                attrs["data-conflict-note"]=note
                attrs["title"]=note
                if annotation.get("term_alternatives"):
                    vocabulary={row["term_id"]:row for row in data["vocabulary"]["terms"]}
                    attrs["data-term-alternatives"]=json.dumps([{**ref,"canonical_name":vocabulary[ref["term_id"]]["canonical_name"]} for ref in annotation["term_alternatives"]],ensure_ascii=False)

                attrs["data-tei-alternatives"]=json.dumps([{"markup_id":spec["markup_id"],"tei_element":spec["tei_element"]} for spec in alternatives],ensure_ascii=False)
            for key,value in values.items():
                # Project semantic type and TEI @type are separate namespaces.
                name = "tei-" + key if key in ("type", "subtype") else {"notBefore":"not-before", "notAfter":"not-after"}.get(key,key)
                attrs["data-"+name]=" ".join(value) if isinstance(value,list) else value
            if term:
                attrs["data-term-id"]=term["term_id"]
                attrs["data-entity-id"]=term["term_id"]
                attrs["data-mention-id"]=annotation["id"]
                attrs["data-identity-status"]="ambiguous" if annotation.get("term_alternatives") else "resolved"
                if annotation.get("name_id"):
                    attrs["data-name-id"]=annotation["name_id"]
                    form=next(a for a in term["aliases"] if a.get("name_id")==annotation["name_id"])
                    attrs["data-name-kind"]=form["name_kind"]
                attrs["data-normalized"]=term["canonical_name"]
            attrs["data-highlight"]="true" if base["highlight"] else "false"
        else:
            kind = annotation["type"]
            attrs = {"class": "entity " + kind.replace("_", "-"), "data-id": annotation["id"], "data-type": kind, "data-name": node["text"]}
            for key in ("normalized", "ref", "key", "source", "role", "cert", "when", "from", "to", "not-before", "not-after"):
                if key in annotation:
                    attrs["data-" + key] = annotation[key]
        attr_text = " ".join(f'{key}="{esc(value)}"' for key, value in attrs.items())
        inner=esc(node['text'])
        for extra in annotation.get('keyword_annotations',[]):
            wrapper=render_content({'content':[{'text':node['text'],'annotation':extra}],**{k:v for k,v in para.items() if k!='content'}},data)
            inner=wrapper[:wrapper.index('>')+1]+inner+wrapper[wrapper.rfind('</span>'):]
        result.append(f'<span {attr_text}>{inner}</span>')
    return "".join(result)


def paragraph_html(data: dict, div: dict) -> str:
    indexes = build_site_indexes(data)
    paragraphs = indexes["paragraphs_by_div"].get(div["division_id"], [])
    if not paragraphs:
        return ""
    from textoria_reader_formatting import formatted_paragraph
    return "".join(
        formatted_paragraph(para, data, render_content) or
        f'<p id="{para["paragraph_id"]}" data-paragraph-number="{para["paragraph_index"]}">{render_content(para, data)}</p>'
        for para in paragraphs
    )


def first_readable_division(data: dict) -> dict | None:
    indexes = build_site_indexes(data)
    for div in data["divisions"]:
        if indexes["paragraphs_by_div"].get(div["division_id"]):
            return div
    return data["divisions"][0] if data["divisions"] else None


def chapter_nav_html(prev_div: dict | None, next_div: dict | None, depth: int) -> str:
    return (
        '<nav class="chapter-nav">'
        + (f'<a class="prev" href="{division_href(prev_div, depth)}">上一節：{esc(prev_div["title"])}</a>' if prev_div else "<span></span>")
        + (f'<a class="next" href="{division_href(next_div, depth)}">下一節：{esc(next_div["title"])}</a>' if next_div else "<span></span>")
        + "</nav>"
    )


def resolve_theme(paths: BuildPaths) -> Path:
    return Path(__file__).resolve().parents[1]/'themes/default'


def theme_name(theme_path: Path) -> str:
    manifest = theme_path / "theme.json"
    if not manifest.exists():
        return theme_path.name
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return theme_path.name
    return str(data.get("name") or theme_path.name)


def build_template_env(theme_path: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(theme_path / "templates"),
        autoescape=select_autoescape(("html", "xml")),
    )
    static_files = sorted(path for path in (theme_path / "static").rglob("*") if path.is_file())
    env.globals["asset_version"] = hashlib.sha256(b"".join(path.read_bytes() for path in static_files)).hexdigest()[:12]
    return env


def copy_theme_static(theme_path: Path, paths: BuildPaths) -> None:
    static_dir = theme_path / "static"
    assets_dir = paths.site / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    if static_dir.exists():
        shutil.copytree(static_dir, assets_dir, dirs_exist_ok=True)


def base_context(collection: dict, active: str, depth: int, reader_view: bool = False) -> dict:
    prefix = relative_prefix(depth)
    return {
        "collection": collection,
        "brand_html": brand_html(collection["title"]),
        "description": display_title(collection.get("description") or collection["title"]),
        "active": active,
        "body_class": "reader-view" if reader_view else "",
        "asset_prefix": f"{prefix}assets/",
        "site_prefix": prefix,
        "routes": {
            "home": f"{prefix}index.html",
            "read": f"{prefix}read.html",
            "search": f"{prefix}search.html",
        },
    }


def render_template(env: Environment, template_name: str, output: Path, context: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(env.get_template(template_name).render(**context), encoding="utf-8")


def render_home(env: Environment, paths: BuildPaths, data: dict) -> None:
    collection = data["collections"][0]
    counts = {key: len(data[key]) for key in ("documents", "divisions", "paragraphs", "sentences", "tokens")}
    context = {
        **base_context(collection, "home", depth=0),
        "page_title": display_title(collection["title"]),
        "counts": counts,
    }
    render_template(env, "index.html", paths.site / "index.html", context)


def division_context(data: dict, collection: dict, div: dict, prev_div: dict | None, next_div: dict | None, depth: int) -> dict:
    sections=reader_sections(data, div['division_id'])
    visible_ids={section['division_id'] for section in sections}
    return {
        **base_context(collection, "read", depth=depth, reader_view=True),
        "page_title": f"{div['title']} - {display_title(collection['title'])}",
        "current_division": div,
        "annotation_enabled": bool(data.get("annotation_profile")),
        "annotation_page": {"division_id": div["division_id"], "paragraphs": [p for p in data["paragraphs"] if p["division_id"] in visible_ids]},
        "toc_html": render_toc(data, div["division_id"], depth=depth),
        "paragraph_html": paragraph_html(data, div),
        "reader_descendants": [{"division":section,"paragraph_html":paragraph_html(data,section)} for section in sections[1:]],
        "chapter_nav_html": chapter_nav_html(prev_div, next_div, depth=depth),
    }


def render_read_entry(env: Environment, paths: BuildPaths, data: dict) -> None:
    collection = data["collections"][0]
    divisions = data["divisions"]
    if not divisions:
        return
    first_div = first_readable_division(data)
    idx = divisions.index(first_div)
    prev_div = divisions[idx - 1] if idx > 0 else None
    next_div = divisions[idx + 1] if idx < len(divisions) - 1 else None
    context = division_context(data, collection, first_div, prev_div, next_div, depth=0)
    render_template(env, "read.html", paths.site / "read.html", context)


def render_division_pages(env: Environment, paths: BuildPaths, data: dict) -> None:
    collection = data["collections"][0]
    indexes = build_site_indexes(data)
    divisions = data["divisions"]
    div_pos = {div["division_id"]: idx for idx, div in enumerate(divisions)}
    read_dir = paths.site / "read"
    read_dir.mkdir(parents=True, exist_ok=True)

    for div in divisions:
        idx = div_pos[div["division_id"]]
        prev_div = divisions[idx - 1] if idx > 0 else None
        next_div = divisions[idx + 1] if idx < len(divisions) - 1 else None
        context = division_context(data, collection, div, prev_div, next_div, depth=1)
        render_template(env, "division.html", read_dir / f"{div['division_id']}.html", context)


def build_static_site(paths: BuildPaths, data: dict, reader_paragraphs=None) -> None:
    theme_path=resolve_theme(paths);env=build_template_env(theme_path)
    paths.site_data.mkdir(parents=True,exist_ok=True);copy_theme_static(theme_path,paths)
    from textoria_annotation_statistics import overview
    snapshot=overview(data);snapshot['revision']=data.get('_revision','');snapshot['collection_title']=data['collection']['title']
    encoded=json.dumps(snapshot,ensure_ascii=False).replace('<','\\u003c')
    (paths.site_data/'workbench.js').write_text('window.TEXTORIA_WORKBENCH = '+encoded+';\n',encoding='utf-8')
    # Whole-book KWIC is a derived data asset, never shipped as a template.
    from textoria_annotation import iter_annotations
    from textoria_corpus import content_text
    records={};pending={}
    for p in data['paragraphs']:
        text=content_text(p['content']);offset=0
        for n in p['content']:
            hit=n['text'];end=offset+len(hit)
            if n.get('annotation'):
                for ann in iter_annotations(n['annotation']):
                    before=re.sub(r'<span class="note">|</span>','',text[:offset])
                    after=re.sub(r'<span class="note">|</span>','',text[end:])
                    row=[ann['id'],p['paragraph_id'],p['division_id'],p['paragraph_index'],('…' if len(before)>12 else '')+before[-12:],hit,after[:12]+('…' if len(after)>12 else ''),ann.get('conflict_note','')]
                    if ann.get('term_alternatives'):pending[ann['id']]=row
                    elif ann.get('term_id'):records.setdefault(ann['term_id'],[]).append(row)
            offset=end
    value={'chapters':{d['division_id']:d['title'] for d in data['divisions']},'terms':records,'pending':pending}
    encoded=json.dumps(value,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (paths.site/'assets/js/reader-occurrences.js').write_text('window.TEXTORIA_OCCURRENCES='+encoded+';\n',encoding='utf-8')
    render_home(env,paths,data);render_read_entry(env,paths,data);render_division_pages(env,paths,data)
