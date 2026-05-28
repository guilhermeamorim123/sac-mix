---
name: list-agents
description: List all created agents in the Agent Maker project
user-invocable: true
allowed-tools: Bash, Read, Glob
---

# List Agents

Scan the project and list all created agents.

## Steps

1. Use Glob to find all `README.md` files in `claude-agents/*/`, `openai-gpts/*/`, and `gemini-gems/*/` (excluding `_template/` folders)

2. For each agent found, read the first 5 lines of its README.md to extract the name and description

3. Present a summary table:

```
| # | Name | Type | Description | Files | Last Modified |
|---|------|------|-------------|-------|---------------|
```

4. If no agents exist yet, say: "No agents created yet. Use /new-agent to create your first one!"

**Note**: Skip `_template/` directories — those are reference templates, not actual agents.
