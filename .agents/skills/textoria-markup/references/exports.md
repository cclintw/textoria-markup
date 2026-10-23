# Exports

Public choices are only: self-contained reader HTML, CSV/Excel metadata tables, DocuXML. TEI XML, EPUB, SQLite and Access are not offered in this skill's current export menu. Do not generate optional documents during ordinary rebuilds; formal entity.json/entity.csv remain automatically updated after annotation/edit operations.

Run `textoria_export_bundle.py <COLLECTION> --format html|table|docuxml|all` using the verified Python. `textoria_export_document.py` delegates to this current interface. Export uses a revision-checked snapshot and never mutates corpus. All files go under exports/. Previous TEI files are legacy artifacts; do not relabel them DocuXML.

## Reader HTML

`<collection title>.html` embeds the shared reader CSS, JS, whole-book data and canonical chapter/paragraph bodies. It retains the entity tree, detail/KWIC panel, hierarchical dropdown, previous/next navigation, and in-file occurrence locating. Top add/export/help actions are absent; left/right toggles remain. Chapter changes show/hide existing articles, not load another file. Empty selected parents show their first readable descendant path using the same shared resolver. Every paragraph/annotation is represented once, without duplicate IDs or repeated parent/child content. No external assets, fetch, localhost or extra files are needed. Validate all paragraph text/IDs and absence of external asset references.

## DocuXML

`<collection title>_docu.xml` uses ThdlPrototypeExport, corpus settings and documents/document. Default one top-level division per document, including all its descendants in source order once. Empty parents with child text produce a populated document. Keep stable document filename, corpus, compilation_name, title, and known metadata only. Use Paragraph Key/Type/Title for paragraph ID, owning division and full path. Store full division tree and original annotations/IDs in custom xml_metadata JSON fields. This preserves structure/provenance but does not imply DocuSky's UI automatically renders an identical nested internal TOC.

The four built-in inline tags are PersonName, LocName, Office and Date. All other types, including time, use Udef_<type> (time becomes Udef_Time); Term is the canonical name while element text preserves original spelling. Declare only custom Udef_ tags with paired feature_analysis spotlight/tag entries, Chinese spotlight titles and consecutive display_order starting at 1; built-in tags use DocuSky defaults. Validate required corpus/filename and each custom content tag’s declaration/spotlight, in addition to lexical and fidelity checks. Do not invent external authority RefId from Textoria IDs; local IDs are kept in custom provenance. Same-span types/identities/keywords are nested. Deleted annotations and unapplied overlaps remain absent from inline content. Use ASCII custom field names TextoriaDocumentId, TextoriaDivisionId and TextoriaDivisionPath in both XML and metadata table headers; Chinese values remain unchanged. Escape literal double quotes in element text as &quot; (including JSON), in addition to ordinary XML escaping. DocuSky’s validator uses stricter lexical rules than standard XML; run validate_validator_syntax as well as XML parsing, record uniqueness/counts, paragraph fidelity and annotation provenance checks. Actual DocuSky import compatibility requires its validator/import tool; don't claim a live import was tested without doing it.

## Metadata tables

`<collection title>_metadata.csv` and `.xlsx` have the same one-top-level-division-per-row document keys as DocuXML. These are metadata-only tables for DocuSky Metadata Attachment, not formal entity vocabulary and not a full-text substitute. English standard headers follow the supplied metadata specification. filename remains unique/stable; absent authors/dates/sources stay blank. Custom metadata fields match the corresponding XML metadata fields. Do not silently put long tagged full text into Excel cells or claim metadata edits update corpus automatically.

XLSX uses the optional bundled Node runtime and @oai/artifact-tool; call load_workspace_dependencies and pass resolved runtime paths as `--node <NODE_EXECUTABLE> --node-modules <NODE_MODULES>`. Do not hardcode host paths or install runtime dependencies silently. CSV + Excel are produced together for table/all. The workbook helper lives at scripts/textoria_metadata_xlsx.mjs and runs in a temporary folder with a runtime modules symlink. It preserves identifiers as text, validates cells, and optionally renders a preview with --preview <PNG>. If that runtime is unavailable, explain the blocker; HTML and DocuXML need no spreadsheet runtime.

## Reader actions

Icons appear immediately after + in this order: HTML, CSV/Excel, DocuXML. They only copy ready-to-paste instructions including collection title/ID. They never send dialogue, write corpus or download automatically. Execute an explicit pasted export request without repeating an already specified scope question, and provide output links.

Official references: https://docusky.org.tw/docusky/docuTools/userMain/ ; https://hackmd.io/@DocuSky/BksNFnEK_ ; https://docs.google.com/spreadsheets/d/1F5dtIZ3Kp_FZIvA7HwDfebBy4uwPTpiEfi9aBDx6ijM/edit?gid=0

## Distinguish metadata and batch tagging

DocuXML is the primary completed-annotation handoff for direct DocuSky database creation. Metadata CSV/Excel edits document-level fields and does not contain the current inline spans. BatchTagging tables are separate annotation instructions: tagName, tagVal, @Term, @RefId, @Aux, optional filename filters and positive/negative lookaround columns. A vocabulary table alone cannot reproduce manual per-occurrence edits/deletions. The current table export produces metadata only; do not describe it or formal entity.csv as a BatchTagging-compatible export. Support for importing or exporting full BatchTagging conditions requires explicit normalization/implementation and validation, not merely renaming headers. The metadata specification allows !doc_content to preserve marked full text during conversion, but this is not included in the current metadata-only export.

## ChatGPT / Sites publication

The globe icon follows DocuXML and copies a prompt for the current collection. No deployment occurs on click. After the user submits it, follow the available Sites workflow with the latest standalone showcase HTML (--format html --showcase) as index.html, retaining copy-only action icons and a same-tab help page; preserve layout and interactions, default a new Site to private, and reuse the identified Site for explicit updates. Local edits require a new publication; the site is not connected to corpus.json. Reading HTML contains full text/annotations; source/work files are not part of deployment. Return a verified URL, or explain missing Sites capability and provide the standalone HTML. This action is separate from the three export formats.

Showcase is independent of public/private access. Copying a prompt does not authorize mutation or publish a second site. Entity categories start collapsed and collapse again on chapter changes; visiting the help page and returning restores the prior chapter, selection, panels and scroll position. Plain HTML export without --showcase remains the stripped reading edition.
