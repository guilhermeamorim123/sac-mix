---
type: reference
---

# Config Contract

> How every CoS skill consumes `context/cos-config.md`. Each skill's **Step 0** applies this contract with its own list of capability roles.

## At Step 0, the skill MUST:

1. **Read `context/cos-config.md`.** Extract:
   - **Identity**: `owner`, `role`, `cos_persona`, `language`. Use `language` for all output. Refer to the user via `owner`/"você" — never a hardcoded name.
   - **Host**: `host` (`claude-code` or `codex`). Informational; tells the skill which agent instructions file is canonical (`CLAUDE.md` vs `AGENTS.md`).
   - **Capabilities**: the `capabilities:` map. For each declared role (`tasks`, `comms`, `calendar`, `email`, `docs`):
     - `enabled` (bool) — whether the user wants this role active
     - `mcp` (string) — name of the MCP wired to it (empty if vault-only)
   - **MCP details**: the free-text blocks under `## MCP details → ### <role>` — IDs, channels, filters, timezone. The skill passes these to `cos-mcp-loader` as context.

2. **For each capability role the skill declares it can use:**
   - **`enabled: false` (or `mcp` empty)** → SKIP that role's loader/steps entirely. Operate vault-only for that role.
   - **`enabled: true`** → spawn `cos-mcp-loader` with: role name, `mcp` value, and the corresponding "MCP details" content. The loader queries the MCP and returns a markdown summary.
     - If the MCP errors or is unreachable, the loader reports it and the skill proceeds vault-only for that role with a one-line warning to the user.

3. **Never hard-stop for a missing capability.** The `cos-vault-loader` and `cos-references-loader` always run. A skill with every capability disabled still runs and produces value from vault notes alone.

4. **If `context/cos-config.md` is missing or unpopulated** (`owner` still `[[Owner Name]]`): tell the user to run `/cos-setup` first, then proceed vault-only with all capabilities treated as off.

## Capability roles (canonical list)
- `tasks` — task/project tracker (ClickUp, Linear, Notion, Todoist…)
- `comms` — team communication (Slack, Discord, Teams…)
- `calendar` — calendar (Google Calendar, Outlook…)
- `email` — email (Gmail, Outlook…)
- `docs` — file/document store (Google Drive, Notion, Dropbox…)

Skills reference roles by name. The MCP behind each role is the user's choice.

## Loader pattern
- `cos-vault-loader` — file-only, always available, reads the vault.
- `cos-references-loader` — file-only, always available, reads templates/conventions/memory index.
- `cos-mcp-loader` — generic example for ANY MCP. The skill tells it which role + MCP + details to query. Copy it to `cos-<mcp>-loader.md` if you specialize one for your stack.
