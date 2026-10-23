# Dialogue edits

No browser save form is used. Copy icons transfer readable chapter/paragraph/entity context and canonical IDs to dialogue. The plus icon preserves one unannotated paragraph selection. Confirm occurrence/paragraph/division/all scope and action before writing.

```sh
<PYTHON> <SCRIPTS>/textoria_workbench.py <COLLECTION> state
<PYTHON> <SCRIPTS>/textoria_workbench.py <COLLECTION> plan <TEMP>/request.json
<PYTHON> <SCRIPTS>/textoria_workbench.py <COLLECTION> edit <TEMP>/request.json
```

Example confirmed deletion:

```json
{"operation":"delete","revision":"current state revision","scope":"occurrence","paragraph_id":"p-0000001","annotation_id":"m-existing","confirmed":true}
```

For paragraph/division/all, also give `term_id` to select the entity; division uses paragraph_id as the chapter anchor. New annotations use `operation: save`, scope, paragraph_id, start/end/text and markup_id. For modifying existing annotations, specify annotation_id and scope, optional markup_id, canonical_name and attributes. Attributes not provided are preserved; changing type may require explicit attribute adjustment. `modify-term` changes shared canonical_name/adds aliases for the named term_id. A per-occurrence type change creates/uses the appropriate entity link rather than silently changing the global master. `create-type` accepts markup_id/label; `update-rule` accepts a complete rule object. All mutations require confirmed:true and a current revision. `undo` restores the most recent revision only after confirmation.

Offsets count Unicode code points, zero based, end exclusive. The browser converts UTF-16 offsets. Preserve all original text and unrelated IDs. Deleting primary entities retains their independent same-span keywords and records exclusions. Partial-range overlaps remain unsupported by the flat representation; explain and locate them.

The reader keeps original visual layout, tree filters, current occurrence, three copy formats, chapter navigation, single-line KWIC and same-tab guide return state. Rebuild refreshes all derived data. Never infer successful visual verification from syntax tests alone.
