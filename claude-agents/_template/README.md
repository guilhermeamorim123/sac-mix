# {Agent Name}

> One-paragraph description of what this agent does and who it's for.

## Features

- Feature 1
- Feature 2
- Feature 3

## Architecture

| Artifact | Purpose |
|----------|---------|
| `CLAUDE.md` | Core agent instructions (index, ≤150 lines) |
| `.claude/settings.json` | Permissions and hooks |
| `.claude/skills/...` | Slash commands (if any) |
| `.claude/agents/...` | Sub-agent definitions (if any) |
| `workflows/...` | Detailed workflow files (if any) |
| `context/...` | Context/knowledge files via @import (if any) |
| `templates/...` | Output templates (if any) |
| `.mcp.json` | MCP server integrations (if any) |

## Files

```
{agent-name}/
├── README.md
├── CLAUDE.md
├── .claude/
│   ├── settings.json
│   ├── agents/
│   └── skills/
│       └── {skill-name}/
│           └── SKILL.md
├── workflows/
│   └── {workflow-name}.md
└── context/
    └── *.md
```

## Runtime Structure

<!-- What the agent creates/manages when in use (beyond source files) -->
<!-- Example for a meeting manager: -->
<!-- team/<member-name>/meetings/YYYY-MM-DD/meeting.md -->
<!-- Example for a code reviewer: -->
<!-- reports/review-YYYY-MM-DD.md -->

## Integration

To deploy this agent to your project:

1. Copy the entire `{agent-name}/` folder to your target location
2. The `CLAUDE.md` should be at the project root
3. The `.claude/` directory should be at the project root
4. If present, copy `.mcp.json` to the project root
5. If the agent has `context/` files, review and customize them for your domain
6. Merge any settings from `.claude/settings.json` with your existing settings

**Note**: If your project already has a CLAUDE.md, merge the contents rather than replacing.

## Changelog

- YYYY-MM-DD: Initial creation
