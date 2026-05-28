# {GPT Name}

> One-paragraph description of what this GPT does and who it's for.

## Features

- Feature 1
- Feature 2
- Feature 3

## Architecture

| Artifact | Purpose |
|----------|---------|
| `prompt.md` | Main system prompt (≤8000 chars) |
| `knowledge/*.md` | Knowledge files to upload |
| `actions/*.yaml` | OpenAPI action schemas (if any) |
| `config.md` | Capabilities, starters, settings |

## Knowledge File Plan

| File | Structure | Loading | Purpose |
|------|-----------|---------|---------|
| `knowledge/{file}.md` | {FAQ/Reference Guide/SOP/Glossary/Style Guide} | {Read before / Consult on-demand} | {What it contains} |

## Files

```
{gpt-name}/
├── README.md
├── prompt.md
├── knowledge/
│   └── *.md / *.json
├── actions/
│   └── *.yaml
└── config.md
```

## Configuration Guide

1. Go to [ChatGPT GPT Editor](https://chatgpt.com/gpts/editor)
2. Paste the contents of `prompt.md` into the **Instructions** field
3. Upload all files from `knowledge/` to the **Knowledge** section
4. Configure capabilities as specified in `config.md`
5. Add conversation starters from `config.md`
6. If actions exist, paste each schema from `actions/` into the **Actions** section
7. Verify: all knowledge files in config match uploaded files, conversation starters match prompt workflows

## Changelog

- YYYY-MM-DD: Initial creation
