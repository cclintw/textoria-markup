# Textoria Markup

[Codex Skill](.agents/skills/textoria-markup/SKILL.md) · [GNU GPL v3 or later](LICENSE)

Textoria Markup is a text annotation tool for Codex. Provide an entity vocabulary, keyword list, or annotation rules to create an annotated reader with chapter navigation, entity information, and keyword context. You can continue refining the annotations through chat.

If you do not yet have a vocabulary, you can choose to have AI build a reference vocabulary and apply it to your text. Read the results locally, export them, or publish a website for others to browse.

## Features

- **Multiple annotation sources:** Use existing vocabularies, keyword lists, written rules, or an AI-extracted reference vocabulary. These approaches can be combined.
- **Chapter navigation:** Preserve the text's chapter hierarchy and highlight entity types in different colors.
- **Entity lists and context:** Browse entities by type, view the paragraphs where they appear, and use KWIC (keyword in context) to locate and check passages.
- **Corrections through chat:** Copy text and location information from the reader, then ask Codex to add, remove, or change annotations for a single occurrence, paragraph, chapter, or the whole text.
- **Reusable vocabularies:** Save revised entity vocabularies for future annotation work.
- **Export and sharing:** Export a single HTML file, DocuSky metadata tables, or DocuXML, or publish a reading website with Sites.

## Installation

### Option 1: Install through Codex

Open your working project in the Codex app, paste the following command into the chat, and send it:

```text
$skill-installer --repo cclintw/textoria-markup --path .agents/skills/textoria-markup --dest .agents/skills
```

After installation, you can start using the Skill on your next turn.

### Option 2: Download and install manually

1. Open [the GitHub repository](https://github.com/cclintw/textoria-markup) and choose **Code → Download ZIP**.
2. Extract it and locate the `.agents/skills/textoria-markup/` folder. Enable hidden files if needed.
3. Copy the entire `textoria-markup` Skill folder into your working project's `.agents/skills/` folder. The resulting entrypoint should be `<your-project>/.agents/skills/textoria-markup/SKILL.md`.

## How to use

### 1. Provide your text

Upload a text file in your Codex project and say:

```text
Please annotate the uploaded text.
```

Supported formats are TXT, Markdown, HTML, and CSV with a specified text column. PDFs and images need to be converted to text and checked for recognition errors first. You can also provide a local file path.

Codex will confirm where to store the collection, preserve the original file, and provide a working copy and chapter preview for review. You can edit the Markdown headings or describe the chapter arrangement in chat. Annotation proceeds after you confirm the structure.

### 2. Choose your annotation sources

Use any of the following approaches, individually or together:

| Approach | What to provide |
|---|---|
| Entity vocabulary or keyword list | Upload names, types, aliases, or a keyword list with one term per line. |
| Annotation rules | Describe the conditions for annotation, such as text between particular words. |
| AI-extracted reference vocabulary | Ask Codex to use [Textoria Entity Extractor](https://github.com/cclintw/textoria-entity-extractor) to build a vocabulary from the text, then apply the annotations. |

If you already have a vocabulary, say:

```text
Please annotate the full text using the uploaded vocabulary.
```

If you do not have a vocabulary, say:

```text
Please use AI to extract an entity vocabulary and complete the annotation of the full text.
```

Textoria Entity Extractor handles AI extraction, and Codex helps prepare the required Skill. Unless you specify particular types, extraction covers all applicable entity types supported by that tool. You can also define a narrower scope for your research.

For rule-based annotation, say:

```text
Mark the two to six characters after 「名曰」 and before the following comma as a person name. Do not cross a full stop or paragraph boundary.
```

### 3. Read and revise

Open the reader provided by Codex. Browse entities by type in the left sidebar, read the text in the center, and click an annotation to view entity information and the paragraphs where it appears.

To request a correction, use the copy button beside an entity or paragraph, paste the location information into Codex, and describe the change. For example:

```text
Change this occurrence to a place name. Apply the change only to this occurrence.
```

To add an annotation, select unannotated text in the reader, click **+**, and paste the copied information into the chat. The reader's buttons only copy information; Codex updates the annotations and reader after you submit your correction request.

### 4. Export and share

Ask for an export directly in chat, or click an export icon at the top of the reader and paste the copied request into Codex.

| Output | Purpose |
|---|---|
| Entity vocabulary CSV / JSON | Review or reuse the annotation vocabulary. JSON preserves more complete vocabulary and correction information. |
| Single HTML file | Read or share the complete annotated text in a browser, with chapter navigation, entity lists, and context lookup. |
| DocuSky metadata CSV / Excel | Organize titles, authors, dates, and sources for use alongside DocuXML. |
| DocuXML | Bring the text and annotations into the DocuSky database-building workflow. |

Entity vocabularies and DocuSky metadata tables serve different purposes. The metadata tables are not entity name lists for batch annotation.

For a website link, click the globe icon to copy a publishing request, then paste it into Codex and send it. This feature requires Sites to be available. New websites default to private and include the full text and annotations. If you later revise the text, publish again to update the online version.

## Saved results and usage notes

Results are stored under `textoria-markup/collections/` in your working project. Each collection keeps its original files, working copy, annotation data, reader, and exports. You can open the reader directly in a local browser.

- Once annotation data has been created, editing the earlier Markdown working copy does not automatically update the annotations. Request subsequent revisions through Codex.
- AI vocabularies and text matching may miss entities or produce incorrect annotations. Check the results against the source context. Some overlapping names cannot be displayed together; arbitrary nested or crossing annotations are not currently supported.
- Adding a new document to an existing collection is not currently supported. Create a separate collection for a new text.

## Versions and updates

See [the GitHub repository](https://github.com/cclintw/textoria-markup) for updates. When citing results or documenting research methods, record the version or Git commit used so you can check it later.

## Author and citation

Author and developer: **Chance Chun-Cheng Lin** (GitHub: [cclintw](https://github.com/cclintw)). To cite this project, use the following format and add the version you used:

```text
Chance Chun-Cheng Lin. Textoria Markup: A Codex Skill for Text Annotation. https://github.com/cclintw/textoria-markup.
```

Software citation metadata is available in [CITATION.cff](CITATION.cff). See [NOTICE.md](NOTICE.md) for attribution and acknowledgments.

## License

This project is released under the [GNU General Public License, version 3 or any later version](LICENSE) (`GPL-3.0-or-later`). Source texts and third-party materials retain their respective rights.

## Support the project

If this project helps your work, please give it a **GitHub star ⭐**, report an issue, or suggest an improvement. Before sharing text examples, please check that you have permission to share the material.
