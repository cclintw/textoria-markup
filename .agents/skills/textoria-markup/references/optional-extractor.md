# Optional entity extraction

Read only when the user explicitly chooses **由 AI 自動提取實體詞表作為標註參考表** (option 3) or asks to use Textoria Entity Extractor. The user-facing option does not mention the helper skill or installation. Handle dependency discovery/installation without asking the user to repeat their selection or install it manually. This is an optional cooperating skill, not an automatic dependency of Markup. Vocabulary upload, rules and extraction can be combined.

## Discover or install

1. Check the available skill catalog and the project's `.agents/skills/textoria-entity-extractor/SKILL.md`, including applicable ancestor project skills and an available user-level installation. Read the discovered skill; reuse an existing valid installation. Do not overwrite an installed skill or install a duplicate solely because it is outside the project.
2. If missing, use the available `skill-installer` skill. Read its instructions and locate its actual helper script; do not assume a machine-specific installation path. The configured, user-approved repository is `cclintw/textoria-entity-extractor`, repository path `.agents/skills/textoria-entity-extractor`. Install into `<PROJECT>/.agents/skills`.

User-facing invocation:

```text
$skill-installer --repo cclintw/textoria-entity-extractor --path .agents/skills/textoria-entity-extractor --dest .agents/skills
```

`$skill-installer` denotes a Codex skill invocation, not a shell executable. The actual installer helper is:

```sh
<PYTHON> <INSTALLER_SKILL_DIR>/scripts/install-skill-from-github.py --repo cclintw/textoria-entity-extractor --path .agents/skills/textoria-entity-extractor --dest <PROJECT>/.agents/skills
```

Selecting AI extraction authorizes preparing and using this configured optional dependency; still follow runtime network/filesystem approvals. Installer scripts use network and require escalation in a sandbox, as specified by the installer skill. Do not weaken those permission boundaries. An earlier request to document installation does not itself select AI extraction for the current document.

3. If the installer skill/helper is unavailable, or installation fails, report the concrete blocker briefly. Do not claim successful installation, silently substitute a different repository or perform full-text extraction inside Markup. Preserve the current source/structure and existing uploads; offer to continue with available tables/rules or retry after the issue is resolved. Do not discard other selected sources because extraction failed.
4. After successful installation, verify that the expected SKILL.md exists and read it. Continue the selected extraction workflow as soon as the skill is available, without a second extraction opt-in. Follow the installer's next-turn availability guidance: if activation requires the next turn, briefly tell the user installation is complete and extraction can continue on their next message; do not claim it ran immediately. An already available installation can execute in the current turn.

## Extract and combine

Use the current confirmed text as the extraction input, respecting the extractor skill's own collection/output conventions and the user's requested categories/scope. Do not re-extract if the user already supplied the needed extractor output. Do not alter Markup's fixed source text, chapter IDs or paragraph IDs while handing off to extraction. If those prerequisites are not yet confirmed, resolve them before extraction.

After extraction, read the actual resulting vocabulary and inspect its encoding/schema. Combine it with all other newly uploaded entity/keyword tables and normalized rules in one normalized input batch. Keep original source receipts/provenance, preserve multiple incoming types and explicit identities, and let existing corpus formal vocabulary/manual corrections win over incoming conflicts. Apply according to the confirmed action/scope, then generate reader and formal exports. If the user already explicitly requested the complete extraction-plus-annotation workflow and scope, do not ask the same scope question again.
