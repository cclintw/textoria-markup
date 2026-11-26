# Operations and normalized input

All commands are executed by Codex with a verified Python, not required user shell knowledge. `<SCRIPTS>` is this installed skill's scripts directory.

## Intake and stage boundaries

Default to the complete annotated-reader workflow defined in SKILL.md. Stage boundaries identify prerequisites and storage rules, not separate approval gates or stopping points. Stop at an intermediate stage only on an explicit user restriction. Once annotation inputs are available and the structure is confirmed, continue through apply, reader/sidebar rebuild, formal vocabulary export and verification without asking again whether to annotate.

Before persistent writes, run `textoria_intake.py /path/text.md --project-root <PROJECT>`. It returns `needs_collection_choice` with the existing collection list. Ask new collection versus a named existing one only if the user has not already specified it. After their answer, repeat with `--mode new|existing --collection-slug ...` to validate the target. These commands are read-only: `target_resolved` identifies a destination, not permission for later stages or an import.

- Explicit cleaning-only request: after ownership is resolved, preserve the original under the chosen `uploads/` without overwriting a different file; use `textoria_prepare.py` to produce `clean/<stem>_clean.md` (UTF-8 for every supported source format), plus a preparation report. Preserve an existing edited clean file; do not regenerate over it. Provide a clickable clean Markdown link; do not automatically open it unless requested. Inspect UTF-8/readability and Markdown syntax first; ask before consequential changes. Do not create a corpus or website. The clean working copy is deliberately persistent; all other preprocessing directories remain temporary.
- Full preparation: inspect cleanup needs, then preview division headings/order and paragraph segmentation. Offer heading edits (`# 卷一`, `## 城內`, `### 永寧寺`, with spaces) or dialogue instructions. Re-read the latest clean file and obtain confirmation before committing structure. Build from that file using `--prepared-md` and its reviewed `--prepared-sha256`, plus `--no-clean`; never rebuild from the original instead. Do not run the combined source builder to obtain a preview: it writes corpus and may build the site.
- Additional text in an existing collection: the intake planner can resolve the destination for cleaning-only output. **Appending a new document to an existing corpus is not implemented.** Do not call `textoria_build.py` against it, replace its corpus, silently create another collection, or claim the document has been integrated. When the requested next stage requires append, explain the limitation and implement a reusable, ID-preserving append operation before proceeding.
- After saving structure, show the actual resulting hierarchy again. If lengthy, generate a disposable Markdown TOC preview from saved corpus divisions and provide a link for user review, even if the structure came from an uploaded TOC. Verify it against the confirmed preview yourself: if unchanged, continue annotation without a second confirmation; only materially changed structure needs renewed user confirmation.
- Request annotation sources only if missing: (1) uploaded vocabulary/keywords, (2) dialogue/uploaded rules, (3) optional AI extraction using the separate extractor skill. Choices are combinable. Reuse previously supplied inputs without asking for them again. Only explicit selection of (3) authorizes the extractor discovery/install workflow in [optional-extractor.md](optional-extractor.md); missing sources alone never trigger extraction. An explicit request to stop at a particular stage limits the workflow; discussing or confirming an intermediate step does not impose such a limit.

```sh
<PYTHON> <SCRIPTS>/textoria_prepare.py /path/text.txt --project-root <PROJECT> --collection-slug text --profile preserve
# After the user reviews clean/text_clean.md and confirms its structure:
<PYTHON> <SCRIPTS>/textoria_build.py /path/text.txt --project-root <PROJECT> --collection-slug text --prepared-md <COLLECTION>/clean/text_clean.md --prepared-sha256 <REVIEWED_SHA256> --no-clean
# Legacy combined build, only for an explicitly confirmed automated workflow:
<PYTHON> <SCRIPTS>/textoria_build.py /path/text.txt --project-root <PROJECT> --collection-slug text --label 文本名稱 --no-clean
<PYTHON> <SCRIPTS>/textoria_annotation.py <COLLECTION> apply /path/entities.csv --confirmed
<PYTHON> <SCRIPTS>/textoria_annotation.py <COLLECTION> apply /path/words.txt --keywords --confirmed
<PYTHON> <SCRIPTS>/textoria_annotation.py <COLLECTION> apply /path/instructions.txt --normalized <TEMP>/input.json --confirmed
<PYTHON> <SCRIPTS>/textoria_annotation.py <COLLECTION> rerun --confirmed
<PYTHON> <SCRIPTS>/textoria_rebuild.py <COLLECTION> --site
```

`--paragraph-id` and `--division-id` restrict apply/rerun to existing fixed IDs. Use the action/scope already authorized in the conversation when adding `--confirmed`; the full workflow defaults to applying the supplied reference input to the designated text in full. Ask only if scope is genuinely unresolved. An ordinary rebuild never performs matching or AI extraction. Source build and structure-only rebuild do not generate exports/. Formal vocabulary exports begin after annotation input is applied; `textoria_rebuild.py <COLLECTION> --export` explicitly exports even an empty vocabulary when requested. Source build creates an unannotated reader as an intermediate artifact; continue with direct annotation to regenerate the reader, left entity categories/list and formal exports before delivering the completed task.

Normalize mixed attachment contents as:

```json
{
  "entities": [
    {"name":"金陵","types":["place"]},
    {"name":"寶玉","types":["person","artifact"],"aliases":["寶二爺"]}
  ],
  "keywords": ["功名","婚姻"],
  "rules": [
    {"id":"rule-001","kind":"between","before":"名曰","after":"，","min_length":2,"max_length":6,"include_boundaries":false,"cross_paragraph":false,"stop_chars":["。"],"type":"person"},
    {"id":"rule-002","kind":"regex","pattern":"授([^。]+?)一職","group":1,"type":"office","scope":{"division_ids":["div-000001"]}}
  ]
}
```

Name lists use literal matching, not generated regex. Rules are paragraph-local. Between boundaries are literals, excluded from capture; choose the first following closing boundary. Regex supports a bounded subset, capture groups, optional i/m/s flags and a two-second per-paragraph subprocess budget. Explain unsupported patterns rather than silently dropping conditions. For multiple required conditions, express separate supported rules or add a reviewed reusable engine feature; do not run arbitrary user code. Scope resolves chapter labels into canonical IDs; never put human chapter labels into ID arrays. Do not add default stop punctuation unless it is requested or confirmed.

CSV recognizes name/type/alias and 名稱/類型/別名; unfamiliar columns are interpreted by Codex. UTF-8 TXT/MD keyword files need one literal term per nonempty line, no header or special filename. Other encodings are converted after inspection. Uploaded binary tables/PDFs are not blindly parsed as text; Codex must read and normalize them first with the source preserved.

Preserve supplied record references and coordinates in normalized entity input. JSON accepts `source_refs` and `location`. CSV accepts these fields as JSON cells or flat `source`, `source_id`, `url`, `latitude`, and `longitude` columns. Local NER reference set JSON preserves record identifiers, source references, and locations. For an unresolved reference, use `status: candidate` and keep its coordinates on that reference.

Changes to stored rules must use `update-rule` and a confirmed request; an upload with a colliding, changed rule ID is rejected. A rerun may add new matches but won't erase previous tags. Read revisions again after every operation.

For multiple newly provided sources, including optional extractor output, normalize and combine them in one batch before matching. Do not sequentially apply each new table as if the first were an already reviewed formal vocabulary; that would incorrectly suppress conflicts from later inputs. Keep provenance for all source files.
