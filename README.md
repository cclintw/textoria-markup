# Textoria Markup

[繁體中文](readme_zh-TW.md)

A Codex skill for annotating texts with external vocabularies, keyword lists and reusable context/regex rules. Inspect a static three-column reader and request corrections in dialogue. Textoria Markup does **not** perform a second AI entity-extraction pass.

## Install

After this repository is published as `cclintw/textoria-markup`, paste this in a Codex project conversation:

```text
$skill-installer --repo cclintw/textoria-markup --path .agents/skills/textoria-markup --dest .agents/skills
```

The destination is the project's `.agents/skills/textoria-markup/`. Installing the skill does not create user data. This repository is being prepared locally; no GitHub repository or release has been published by this task. Existing skill installations need a reviewed update; the installer is not an automatic updater. No Codex plugin is bundled.

## Use

1. Upload the source text (TXT, Markdown, HTML/HTM or CSV with a named text column). Other formats, such as PDFs and images, need appropriate conversion and review first. Uploading a file or discussing the tool alone does not start annotation.
2. Codex inspects encoding and readability, then resolves collection ownership before saving files. It archives an unchanged copy in `uploads/` and provides a clickable link to the editable UTF-8 `clean/<stem>_clean.md`, with a preparation report. The file opens in a panel or browser only when requested. Consequential cleanup requires confirmation; edited working copies are preserved. Cleaning-only requests stop here without creating a corpus or website.
3. For structure creation, edit Markdown headings (`# 卷一`, `## 城內`, `### 永寧寺`, with a space after `#`) or describe the structure in dialogue. Codex rereads the latest working copy and previews headings, order and paragraph segmentation. Confirm the preview before `corpus.json` and stable IDs are created. Review the actual saved hierarchy again before annotation; every structural revision needs a fresh preview.
4. Supply entity tables, one-column keyword files or prose instructions, optionally combined with explicitly requested AI extraction through the separate extractor skill. Codex normalizes unfamiliar input into validated JSON and combines new sources before matching; it does not perform its own second entity-extraction pass. New-source type and explicit identity conflicts are preserved; existing formal vocabulary and corrections have priority.
5. Confirm the action and scope. An explicit instruction that already names both provides authorization. The program applies literal/context/regex matches, then regenerates the reader and formal vocabulary.
6. Review the generated reader. Select unannotated text and use **+**, or use entity/paragraph copy icons, then paste into Codex and request an addition, change or deletion. These controls only copy context; they do not save or send messages. Confirm the action and occurrence/paragraph/chapter/book scope before mutation; a single selection does not imply a global change.

Appending a document to an existing corpus is not implemented. Do not rebuild or replace an existing corpus from raw sources to add text or revise annotations. See the [workflow and stage boundaries](.agents/skills/textoria-markup/references/workflow.md) for the current limitations.

Example requests:

```text
Prepare this text without changing its punctuation. Use the uploaded name/type/alias CSV to annotate the whole text; retain all type conflicts.

Use this one-column file for keyword annotation (default type: key-word).

Extract 2–6 characters between 名曰 and ， as person names; stop at 。 and stay within a paragraph.
```

Vocabulary uploads, rules and optional Textoria Entity Extractor results can be combined. When AI extraction is explicitly requested, reuse an available extractor skill or install the configured cclintw/textoria-entity-extractor skill through skill-installer. Follow installer availability guidance, then normalize all new sources together before matching. Missing inputs never automatically trigger extraction.

## Data and frontend

```text
<PROJECT>/
├── .agents/skills/textoria-markup/     # instructions, Python and shared theme
└── textoria-markup/collections/collection-<ASCII-slug>/
    ├── uploads/                       # original sources and attachments
    ├── clean/<stem>_clean.md           # editable UTF-8 preparation, with report
    ├── corpus.json                    # authoritative master after structure confirmation
    ├── site/                          # regenerated static HTML/CSS/JS
    ├── exports/entity.json             # complete reusable formal vocabulary
    ├── exports/entity.csv              # UTF-8 BOM exchange view
    └── .history/                      # optional compressed revision snapshots
```

Shared Jinja templates and template parts live in the skill's `themes/default/`. CSS/JS are copied from its static assets. Chapter text, entity information and whole-book KWIC are generated from corpus. The reader can be opened as a local file or served over loopback. The browser is a review/copy interface; it never writes corpus itself. Guide navigation opens in the same tab and restores reader state on return.

`corpus.json` is the authoritative master. After it is created, editing the clean Markdown does not automatically update saved text or annotations. Structure creation and unannotated reader rebuilds do not create `exports/`; formal entity JSON/CSV is generated after annotation inputs or edits, including accepted terms with zero matches, or on an explicit export request. JSON preserves complete reusable vocabulary and identity links; CSV provides one row per alias and type with IDs and scopes. Deletions retain entity records and scoped exclusions so reruns do not restore removed tags.

## Capabilities and boundaries

- Literal vocabularies, aliases/scopes, multiple source types, independent same-span keywords.
- Paragraph-local between/regex rules, stable rule IDs, regex time limits.
- Revision-checked occurrence/paragraph/chapter/book edits, shared entity name/alias changes, new types, rule edits and confirmed undo.
- Regenerated reader, counts/KWIC and formal entity JSON/CSV. The three public document exports are standalone HTML, CSV/Excel metadata tables and DocuXML.
- Partially overlapping ranges are reported rather than silently overwritten; arbitrary nested/crossing markup is not rendered.
- Empty chapters retain their heading and display the path to their first readable descendant, preserving paragraph ownership and IDs. Chapter navigation reflects the actual hierarchy.
- If reader generation fails after a valid corpus save, the master is saved but the view is stale; rebuild before reporting the webpage as updated.
- No autonomous AI entity extraction, SNA/co-occurrence analysis, translation or semantic extraction. Hosting is available only through an explicit Sites publishing request, as described below; no Codex plugin is bundled.

## Exports

HTML, CSV/Excel and DocuXML icons follow **+** in that order. They copy requests to paste into Codex; exports run on an explicit request and are saved under `exports/`:

- `<collection title>.html`: self-contained reader with both sidebars, hierarchical chapter navigation and in-file KWIC locating. CSS, JS and all text data are embedded; top add/export/help actions are removed.
- `<collection title>_metadata.csv` / `.xlsx`: editable DocuSky metadata, one row per top-level division, with filenames matching DocuXML records. These tables contain metadata rather than full text or BatchTagging instructions.
- `<collection title>_docu.xml`: DocuXML 1.3, one top-level division per document with all descendant paragraphs and current annotations. Custom metadata retains the full division hierarchy and annotation provenance. Local checks cover text, structure and lexical compatibility; actual DocuSky compatibility still requires its validator/import results.

CSV/Excel table export uses an available bundled spreadsheet runtime, resolved only when needed and never silently installed. HTML and DocuXML do not require that runtime. Existing TEI outputs are legacy; TEI, EPUB, SQLite and Access are not offered in the current export menu. See the [export reference](.agents/skills/textoria-markup/references/exports.md).

## Sites publishing

The globe icon after DocuXML copies a collection-specific publishing request. Clicking it alone does not authorize publication. Submit an explicit request to publish through the available Sites skill/tools. New Sites default to private; updates preserve an identified existing Site's audience and identity.

Publishing uses the latest standalone reader as the static index, including the full text and annotations. It excludes uploads, clean files, the corpus master, history and unrelated files. Showcase HTML retains the top icons as copy-only commands and includes the complete help as a separate page in the same tab. Entity categories start collapsed on initial load and chapter changes; returning from help can restore reading state. These controls do not grant editing rights.

Publication is a snapshot and does not automatically synchronize later corpus changes. Codex returns the verified deployed URL. If Sites is unavailable, it provides the local standalone reader instead of switching hosting platforms.

## Development

Python 3.10+ with `requirements.txt` is required. Codex checks an existing runtime first; creating a venv or installing dependencies requires authorization. Developers can run:

```sh
python -m unittest discover -s .agents/skills/textoria-markup/scripts/tests -v
```

Workflow and schemas are in the skill's [references](.agents/skills/textoria-markup/references/). Source-preparation intermediates use system temporary directories and are not permanent masters. Old data migration copies and verifies before cleanup; the accepted original UI is retained locally in an ignored backup.

See [LICENSE](LICENSE), [attribution](NOTICE.md) and [citation metadata](CITATION.cff). User data, generated websites, histories and local backups are excluded from Git by default.
