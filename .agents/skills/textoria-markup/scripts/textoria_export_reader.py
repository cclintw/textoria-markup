"""Embed the shared interactive reader, all chapters and all assets into one HTML."""
import json
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from textoria_common import ensure_dirs
from textoria_corpus import to_render_data
from textoria_reader_sections import reader_sections
from textoria_annotation import iter_annotations


def standalone_reader(data,stage,*,showcase=False,help_href="help.html"):
    from textoria_build_site import build_static_site
    render=to_render_data(data);build_static_site(ensure_dirs(stage),render)
    site=stage/'site';soup=BeautifulSoup((site/'read.html').read_text(encoding='utf-8'),'html.parser')
    removed='.chapter-navigation' if showcase else '#addEntity,#exportHtml,#exportXml,#exportTable,#exportDocuxml,#publishSite,#readerHelp,.chapter-navigation'
    for node in soup.select(removed):
        node.decompose()
    reader=soup.select_one('.reader');reader.clear()
    for d in render['divisions']:
        page=BeautifulSoup((site/'read'/f"{d['division_id']}.html").read_text(encoding='utf-8'),'html.parser')
        article=page.find('article',id=d['division_id']);article.extract()
        for child in article.find_all('article'):child.decompose()
        for container in article.select('[id="annotationText"]'):container.attrs.pop('id',None)
        article['hidden']='';reader.append(article)
    for link in soup.select('#chapterLinks .toc-link'):
        did=Path(urlsplit(link['href']).path).stem;link['data-division-id']=did;link['href']='#'+did
    page=soup.select_one('#annotationPage')
    page.string=json.dumps({'division_id':render['divisions'][0]['division_id'],'paragraphs':data['paragraphs']},ensure_ascii=False).replace('<','\\u003c')
    config={'currentId':render['divisions'][0]['division_id'],'chapters':{d['division_id']:[v['division_id'] for v in reader_sections(data,d['division_id'])] for d in render['divisions']}}
    script=soup.new_tag('script');script.string='window.TEXTORIA_SINGLE_FILE='+json.dumps(config,ensure_ascii=False).replace('<','\\u003c')+';\n'+'''(()=>{const s=window.TEXTORIA_SINGLE_FILE;const requested=location.hash.slice(1);if(s.chapters[requested])s.currentId=requested;const visible=new Set(s.chapters[s.currentId]);document.querySelectorAll('.reader article[id]').forEach(a=>a.hidden=!visible.has(a.id));})();'''
    # Config must precede the adapter and data scripts.
    page.insert_before(script)
    for link in list(soup.select('link[rel="stylesheet"]')):
        style=soup.new_tag('style');style.string=(site/urlsplit(link['href']).path).read_text(encoding='utf-8');link.replace_with(style)
    for external in soup.select('script[src]'):
        path=site/urlsplit(external['src']).path
        external.string=path.read_text(encoding='utf-8').replace('</script','<\\/script');external.attrs.pop('src',None)
    if showcase:
        soup.body['data-showcase']='true'
        soup.select_one('#readerHelp')['href']=help_href
    return str(soup)


def validate_reader(path,data):
    soup=BeautifulSoup(Path(path).read_text(encoding='utf-8'),'html.parser')
    showcase=soup.body.get('data-showcase')=='true'
    forbidden='link[href],script[src],iframe[src],img[src]' if showcase else 'link[href],script[src],iframe,img[src],#addEntity,#exportXml,#exportHtml,#exportTable,#exportDocuxml,#publishSite,#readerHelp'
    if soup.select(forbidden):
        raise ValueError('Standalone reader has external assets or editing actions.')
    if showcase:
        link=soup.select_one('#readerHelp')
        href=link.get('href','') if link else ''
        if not href or urlsplit(href).scheme or href.startswith(('#','/')) or soup.select('dialog,iframe'):
            raise ValueError('Showcase help must use a sibling page in the same tab.')
        guide_path=Path(path).parent/href
        if not guide_path.is_file():raise ValueError('Showcase help page is missing.')
        guide=BeautifulSoup(guide_path.read_text(encoding='utf-8'),'html.parser')
        if guide.select('script[src],link[href],iframe,img[src]') or not guide.select_one('[data-reader-return]'):
            raise ValueError('Showcase help must be complete and self-contained.')
        if not all(soup.select_one('#'+id) for id in ['addEntity','exportHtml','exportTable','exportDocuxml','publishSite','readerHelp']):
            raise ValueError('Showcase actions are missing.')
    ids=[n['id'] for n in soup.select('[id]')]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate single-file reader IDs.')
    actual={p['id']:p.get_text() for p in soup.select('.reader p[data-paragraph-number]')}
    if actual!={p['paragraph_id']:''.join(n['text'] for n in p['content']) for p in data['paragraphs']}:raise ValueError('Single-file reader text changed.')
    expected_ids={a['id'] for p in data['paragraphs'] for n in p['content'] if n.get('annotation') for a in iter_annotations(n['annotation'])}
    if {n['data-id'] for n in soup.select('.reader .entity[data-id]')}!=expected_ids:raise ValueError('Single-file reader annotation IDs changed.')
    if not soup.select_one('#entityTree') or not soup.select_one('#chapterPickerButton') or not soup.select_one('.inspector'):raise ValueError('Single-file reader controls missing.')
    return True


def standalone_guide(stage,reader_href):
    """Keep the local guide's full-page layout and same-tab return behavior."""
    site=Path(stage)/'site';guide=BeautifulSoup((site/'assets/help.html').read_text(encoding='utf-8'),'html.parser')
    for link in guide.select('[data-reader-return]'):link['href']=reader_href
    for link in guide.select('link[rel="stylesheet"]'):
        style=guide.new_tag('style');style.string=(site/'assets'/link['href']).read_text(encoding='utf-8');link.replace_with(style)
    for script in guide.select('script[src]'):
        script.string=(site/'assets'/script['src']).read_text(encoding='utf-8').replace('</script','<\\/script');script.attrs.pop('src',None)
    return str(guide)
