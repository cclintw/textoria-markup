# Single corpus contract

`<PROJECT>/textoria-markup/collections/collection-<ASCII-slug>/` contains `uploads/`, `clean/<stem>_clean.md` (always UTF-8) with a preparation report, `corpus.json` after confirmed structure, generated `site/` and `exports/`. Optional `.history/` holds compressed revisions, not a second editable master. The clean directory is a deliberate editable preparation stage; no intermediate/annotation/config tree is recreated. Users may edit Markdown heading levels before confirmation. Once corpus exists it remains authoritative; later changes to clean files must not silently replace fixed IDs or source text in corpus.

The existing structural schema_version `2.0` is preserved for migration compatibility. `storage_format: textoria-markup-single-corpus-v1` distinguishes the new storage lifecycle. Corpus holds collection, documents, divisions, paragraphs, annotation_profile, vocabulary and annotation_state. Original text occurs once in paragraph `content` nodes. A node is `{text}` or `{text, annotation}`; same-span keyword memberships remain `keyword_annotations`. Keep stable IDs; a directory's name equals collection_id. `counts` is validated from actual content on every save.

`annotation_profile` contains editable types/labels/TEI mappings; `vocabulary.terms` contains IDs, canonical names, original aliases and scopes. Existing TEI mapping metadata is retained, not a claim of complete TEI export. `annotation_state` contains rules, imports/receipts, source_differences, exclusions, overrides, and unresolved partial overlaps. Migrated `rules_text` and provenance are historical records; obsolete AI/candidate instructions inside them do not override this skill's workflow.

Regex/between rules have stable IDs and explicit scopes; they are validated and interpreted, never executed as Python. Each source has an archived upload hash and normalized-data hash. Do not persist a permanent normalized-import JSON beside the corpus. Temporary import JSON may be discarded after verified commit.

Create exports/ after annotation inputs/edits or an explicit export request, not at structure creation. The text-specific `exports/entity.json` uses schema `textoria-markup-reference-1` and contains vocabulary terms, type definitions, entity and name tables, relations, and rules. CSV includes `id,name,type,alias,occurrences,match_policy,scope,source_refs,location,name_kind,name_status`, with one row per name form and type. Export accepted terms including terms with zero confirmed occurrences. The corpus remains the authoritative source.

Each term and exported entity includes `source_refs` and `location`. Use an empty array for missing references and `null` for a missing confirmed location. A reference contains `source`, `source_id`, `url`, `status`, and `location`. The status is `linked` or `candidate`. A location contains `latitude`, `longitude`, `source`, and `source_id`. Candidate coordinates stay with the candidate reference. Existing CBDB person evidence can provide an official record link when it identifies one linked person.

The reader displays sources for people and places. For a place with coordinates, omit references without coordinates and show one representative per map position, preferring a reference with a record URL at that position. Show a dropdown only when two or more distinct map positions are available. If no coordinates are available, show direct links for references with valid record URLs. The map opens at the confirmed location when available or at the first available position. Switching locations updates the preview without changing the saved record. Leaflet maps use the HTTP or HTTPS reader.

A regex match and a clipper result can add scoped vocabulary aliases. Reruns don't reinterpret saved/manual spans. New same-span entities are grouped preserving all source types/explicit identities; partial overlaps are recorded, not silently overwritten. The reader does not currently visualize general nested or crossing ranges.

## Name identities and relational JSON (identity schema 1.0)

`corpus.json` remains authoritative. On save, an additive, revision-checked migration adds `identity_schema_version: "1.0"`, `vocabulary.terms[].aliases[].name_id/name_kind`, and annotation `name_id` links, including links on `term_alternatives`. It preserves source text, existing term/occurrence IDs, scopes, exclusions and overrides. Legacy reads remain supported; the new name-reference validator applies to migrated corpora. The historical `aliases` list is a list of matching forms, not proof that every entry is a semantic alias.

`name_kind` is one of `canonical`, `alias`, `courtesy_name`, `sobriquet`, `alternative`, `abbreviation`, `variant`, `contextual_form`, or `unspecified`. New CSV `name` is canonical and its explicitly supplied `alias` forms are aliases; explicit normalized input may supply a more precise kind. A manually confirmed occurrence spelling is a contextual form. Migration labels an exact canonical spelling `canonical`, but does not infer the meaning of other legacy forms: they remain `unspecified` unless already classified. Do not infer a semantic alias solely because its spelling differs from the canonical name, and do not merge different entities during migration.

Name IDs derive deterministically from the owning entity ID, exact spelling, scope and match policy. Source evidence/receipts and scope are retained; no evidence is invented. The same spelling can belong to different entity IDs. When several forms match one occurrence, prefer the most specific applicable scope. Canonical labels belong to the entity; raw mention spellings stay in the original content nodes. An annotation's source range counts Unicode code points in the saved paragraph content, including any literal formatting syntax; the reader's source mapping preserves those offsets.

`exports/entity.json` contains these reusable tables:

- `entities`: `entity_id`, `canonical_name`, `markup_ids`, `sources`.
- `names`: `name_id`, owning `entity_id`, exact `text`, `name_kind`, `match_policy`, `scope`, `sources`, and any supplied evidence metadata. It includes canonical spellings, not just aliases.
- `relations`: `subject_id`, `type`, and `object_id`, with evidence when supplied.
- `rules`: validated matching rules, with a target `term_id` when the rule links a form to an existing entity.

Full paragraph text, per-occurrence annotations, offsets, exclusions and overrides remain in `corpus.json`. Ambiguous mentions retain alternative IDs in the corpus. The reader displays them for review and counts confirmed identities by entity ID.

Formal JSON re-import validates the entity and name projections against the formal terms. Legacy vocabulary-v1 exports remain importable. CSV provides a flat name listing.

HTML exposes `data-entity-id`, `data-mention-id`, `data-name-id`, `data-name-kind`, and `data-identity-status`. For ambiguous identities, `data-entity-id` identifies the primary display candidate. Read the status and alternatives for the complete identity information.
