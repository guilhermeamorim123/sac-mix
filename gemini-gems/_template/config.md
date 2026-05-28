# {Gem Name} — Configuration

## Identity

- **Name**: {Display name — short, memorable, max ~40 chars}
- **Description**: {One-line description of what the Gem does}
- **Icon**: {Emoji or description — Gemini can auto-generate an icon}

## Knowledge Files to Upload

<!-- Max 10 files. Supported: PDF, TXT, CSV, MD, Google Docs, Google Sheets, and other text formats -->
<!-- Each file should be focused on one topic for better retrieval -->

| File | Format | Purpose |
|------|--------|---------|
| `knowledge/{file1}.md` | Markdown | {Description} |
| `knowledge/{file2}.pdf` | PDF | {Description} |

## Sharing Settings

| Setting | Value | Notes |
|---------|-------|-------|
| Visibility | Private / Anyone with link / Workspace | Choose based on audience |
| Workspace sharing | Yes/No | Only for Google Workspace accounts |

## Built-in Capabilities

<!-- Gems inherit ALL Gemini capabilities — no toggles needed. Document which ones this Gem should actively use. -->

| Capability | Usage in This Gem |
|------------|-------------------|
| Google Search grounding | {When to search: e.g., "for current prices", "for recent news"} |
| Code execution | {When to run code: e.g., "for data analysis", "for calculations"} |
| Image generation (Imagen) | {When to generate: e.g., "for diagrams", "not used"} |
| File analysis | {When to analyze uploads: e.g., "for PDFs", "for spreadsheets"} |
| Google Workspace integration | {If applicable: e.g., "read from Google Docs"} |

## Test Prompts

<!-- 3-4 prompts to verify the Gem works correctly after creation -->
1. "{Test core workflow}"
2. "{Test knowledge file retrieval}"
3. "{Test edge case / off-scope handling}"
4. "{Test output format compliance}"
