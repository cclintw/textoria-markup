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

1. Upload the source text (TXT, Markdown, HTML or CSV with a text column).
2. Codex checks encoding automatically. Confirm the collection, archive the original in uploads/, then review the UTF-8 clean/<stem>_clean.md in the right-side editor. Edit Markdown headings or describe the structure in dialogue; confirm the preview before corpus.json is created.
3. Supply entity tables, one-column keyword files or prose instructions. Codex normalizes unfamiliar input into validated JSON; it does not reread the entire text to discover entities.
4. Confirm scope. The program applies literal/context/regex matches directly. New-source type conflicts are preserved; existing formal vocabulary and corrections have priority.
5. Review the generated reader. Select text and use **+**, or use entity/paragraph copy icons, then paste into Codex and request an addition, change or deletion. Confirm the action/scope before mutation.

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
└── textoria-markup/collections/collection-<slug>/
    ├── uploads/                       # original sources and attachments
    ├── clean/<stem>_clean.md           # editable UTF-8 preparation, with report
    ├── corpus.json                    # authoritative master after structure confirmation
    ├── site/                          # regenerated static HTML/CSS/JS
    ├── exports/entity.json             # complete reusable formal vocabulary
    ├── exports/entity.csv              # UTF-8 BOM exchange view
    └── .history/                      # optional compressed revision snapshots
```

Shared Jinja templates and template parts live in the skill's `themes/default/`. CSS/JS are copied from its static assets. Chapter text, entity information and whole-book KWIC are generated from corpus. The reader can be opened as a local file or served over loopback. The browser is a review/copy interface; it never writes corpus itself. Guide navigation opens in the same tab and restores reader state on return.

## Capabilities and boundaries

- Literal vocabularies, aliases/scopes, multiple source types, independent same-span keywords.
- Paragraph-local between/regex rules, stable rule IDs, regex time limits.
- Revision-checked occurrence/paragraph/chapter/book edits, shared entity name/alias changes, new types, rule edits and confirmed undo.
- Regenerated reader, counts/KWIC, entity JSON/CSV, standalone annotated HTML with embedded CSS, TEI XML. HTML, CSV/Excel and DocuXML icons follow + and copy export requests to paste into Codex.
- Partially overlapping ranges are reported rather than silently overwritten; arbitrary nested/crossing markup is not rendered.
- DocuXML uses one top-level division per document with all descendant paragraphs and matching metadata rows; full structure/provenance is retained in custom metadata. Actual DocuSky import should be checked with its validator. Single-file HTML embeds both sidebars, chapter navigation and in-file KWIC locating, omitting top editing/export actions.
- No autonomous AI entity extraction, SNA/co-occurrence analysis, hosted deployment or plugin installation.

## Development

Python 3.10+ with `requirements.txt` is required. Codex checks an existing runtime first; creating a venv or installing dependencies requires authorization. Developers can run:

```sh
python -m unittest discover -s .agents/skills/textoria-markup/scripts/tests -v
```

Workflow and schemas are in the skill's [references](.agents/skills/textoria-markup/references/). Source-preparation intermediates use system temporary directories and are not permanent masters. Old data migration copies and verifies before cleanup; the accepted original UI is retained locally in an ignored backup.

See [LICENSE](LICENSE), [attribution](NOTICE.md) and [citation metadata](CITATION.cff). User data, generated websites, histories and local backups are excluded from Git by default.
