# Runtime

Use verified Python 3.10+ and available charset-normalizer, beautifulsoup4, jinja2, markdown-it-py. Check `textoria_runtime_check.py`. Prefer an existing supplied runtime. If dependencies are absent, obtain authorization before creating `.venv/` or installing packages; do not modify system Python or require the user to run commands. Reuse the chosen interpreter; do not write its machine-specific absolute path into the skill.

JSON, CSV, locks, regex worker isolation, gzip backups and EPUB use the standard library. No SQLite/FTS5, Node frontend build or LLM API key is required. The agent interprets supplied prose; scripts do not call an LLM. All preprocessing and import working files belong in system temporary directories and are cleaned only after successful persistence/verification.

CSV/Excel table export additionally uses the bundled Node and @oai/artifact-tool, resolved through load_workspace_dependencies. Only resolve this optional runtime when tables are requested; pass paths as command arguments, never persist machine-specific paths in the skill. HTML and DocuXML remain Python-only.
