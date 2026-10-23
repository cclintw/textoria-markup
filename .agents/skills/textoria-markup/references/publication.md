# Repository and updates

Ship only the skill, shared theme, tests, source-format examples and project documentation. Keep user texts/corpora/sites/exports, snapshots, backups, temporary data and environments out of Git. Install command after this repository is published:

```text
$skill-installer --repo cclintw/textoria-markup --path .agents/skills/textoria-markup --dest .agents/skills
```

The installer is not an updater and refuses existing destinations. No plugin was created. A future updater must preserve user data and local settings, verify releases and replace only code/templates. Renaming the physical parent project or a GitHub repository is separate from changing the generated data container.
