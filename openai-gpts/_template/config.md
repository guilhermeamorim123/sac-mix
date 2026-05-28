# {GPT Name} — Configuration

## Capabilities

| Capability | Enabled | Notes |
|------------|---------|-------|
| Web Search | Yes/No | Enable if GPT needs real-time data |
| Code Interpreter | Yes/No | Enable for data analysis, code execution |
| Image Generation | Yes/No | Enable for visual content creation |
| Canvas | Yes/No | Enable for collaborative editing |

## Conversation Starters

<!-- Formula: 1 educational + 1 core workflow + 1 secondary workflow + 1 advanced. Under 80 chars each. -->
1. "{Educational — what can you do? / how does this work?}"
2. "{Core workflow trigger}..."
3. "{Secondary workflow trigger}..."
4. "{Advanced or specific request}..."

## Knowledge Files to Upload

| File | Format | Structure | Loading | Purpose |
|------|--------|-----------|---------|---------|
| `knowledge/{workflow-guide}.md` | Markdown | Reference Guide | **Read before starting** | {Workflow methodology} |
| `knowledge/{file1}.md` | Markdown | {FAQ/SOP/Guide/Glossary/Style} | Consult on-demand | {Description} |
| `knowledge/{file2}.json` | JSON | Lookup Table | Consult on-demand | {Description} |

## Actions

| Action | Schema File | Auth | Error Fallback | Description |
|--------|-------------|------|----------------|-------------|
| {Action name} | `actions/{schema}.yaml` | None/API Key/OAuth | "{User-friendly fallback message}" | {Description} |

## Additional Settings

- **Name**: {GPT display name}
- **Description**: {Short public description for GPT store}
- **Profile Picture**: {Description or path to image}
