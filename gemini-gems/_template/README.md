# {Gem Name}

> One-paragraph description of what this Gem does and who it's for.

## Features

- Feature 1
- Feature 2
- Feature 3

## Architecture

| Artifact | Purpose |
|----------|---------|
| `instructions.md` | Custom instructions for the Gem |
| `knowledge/*.md` | Knowledge files to upload (max 10) |
| `config.md` | Name, description, sharing settings |

## Knowledge File Plan

| File | Format | Purpose |
|------|--------|---------|
| `knowledge/{file}.md` | Markdown | {What it contains} |

## Files

```
{gem-name}/
├── README.md
├── instructions.md
├── knowledge/
│   └── *.md / *.pdf / *.csv
└── config.md
```

## Configuration Guide

1. Go to [Gemini Gems](https://gemini.google.com/gems)
2. Click **New Gem** (or **Create** / **+**)
3. Set the **Name** and **Description** from `config.md`
4. Paste the contents of `instructions.md` into the **Instructions** field
5. Upload all files from `knowledge/` to the **Knowledge** section (drag & drop or click upload)
6. Choose an icon/emoji or generate one with Gemini
7. Configure sharing settings as specified in `config.md`
8. Click **Save** and test with the suggested test prompts

## Changelog

- YYYY-MM-DD: Initial creation
