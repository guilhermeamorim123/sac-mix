# CoS Reference: Integrations (MCP-agnostic)

> Referenced by `CLAUDE.md` / `AGENTS.md`. Changes here must follow the Structure Change Policy.
> Read this file when the agent instructions direct you to. Companion: `docs/reference/config-contract.md`.

The CoS does not hardcode specific MCPs. Instead, it defines **capability roles** that abstract the kinds of external data the workflows can use. The user wires their own stack (via `/cos-setup` or by hand) by mapping each role to one MCP (or leaving it empty for vault-only).

---

## Capability roles

| Role | Purpose | Common MCP examples |
|------|---------|---------------------|
| `tasks` | task/project tracker | ClickUp, Linear, Notion, Todoist, Asana |
| `comms` | team communication | Slack, Discord, Teams, Mattermost |
| `calendar` | calendar / scheduling | Google Calendar, Outlook, Fastmail |
| `email` | email | Gmail, Outlook |
| `docs` | files / documents | Google Drive, Notion, Dropbox |

Each role lives in `context/cos-config.md → capabilities.<role>` with two keys:
- `enabled` (bool) — is this role active for the user
- `mcp` (string) — which MCP the user wired to it (empty = vault-only)

Plus a free-text block under `## MCP details → ### <role>` capturing whatever the MCP needs (IDs, channels, filters, timezone, etc.).

---

## How wiring works (per host)

### Claude Code
- MCPs come in as **claude.ai connectors** (logged in at claude.ai/connectors).
- A connector turns on its MCP server in the Claude Code session. The CoS skills detect availability via the `cos-mcp-loader` at runtime.
- To wire a new MCP: connect at claude.ai, then add it to a capability role in `cos-config.md`.

### Codex
- MCPs are configured by the user in `~/.codex/config.toml`.
- The CoS workflows are described in `AGENTS.md` for Codex; the loader pattern is the same conceptually but Codex calls the MCP through its own tool-use interface.
- To wire a new MCP: add it to `config.toml`, restart Codex, then update `cos-config.md`.

---

## The loader pattern

Three loaders ship in `.claude/agents/`:

| Loader | Purpose |
|--------|---------|
| `cos-vault-loader` | file-only; reads vault notes (profiles, decisions, pendings, daily-briefs, projects, memory). Always-on. |
| `cos-references-loader` | file-only; reads templates and `docs/reference/`. Always-on. |
| `cos-mcp-loader` | **example** loader for ANY MCP. The skill tells it the role, the MCP name, and the MCP details from config. Read its docstring for the input/output contract. Clone and rename it (e.g. `cos-clickup-loader.md`) if you want to specialize for one MCP. |

Skills spawn loaders via the Agent tool. For each declared role, the skill checks `capabilities.<role>.enabled`; if true, it spawns `cos-mcp-loader` with the role+MCP+details; if false, that role's step is skipped and the skill operates vault-only.

---

## Permissions

| Action | Permission |
|--------|-----------|
| Read/query via any role's MCP | Free — anytime, no approval needed |
| Write/send/create via any role's MCP (tasks, calendar events, messages, drafts, file uploads, etc.) | **Requires the owner's approval** — always present content and wait for confirmation |
| Read or write to the vault | Free — when part of a CoS workflow |

The CoS treats outbound side-effects (anything that leaves a trace outside the vault) as needing the owner's go. Reads are free.

---

## Vault-only fallbacks (when a role is OFF)

| Role OFF | What the CoS does instead |
|----------|---------------------------|
| `tasks` | Tasks tracked as `- [ ]` Obsidian Tasks under `## Tarefas` in the project note (see `docs/reference/obsidian-tasks.md`). |
| `comms` | Skills skip channel/DM enrichment and rely on member profiles + meeting records. |
| `calendar` | Skills ask the owner for meeting times instead of consulting an agenda. |
| `email` | Skills skip email enrichment. |
| `docs` | Skills rely on what's already in the vault. |

The vault is the floor. Capabilities are enrichment on top.

---

## Routing tasks (when `tasks` is configured)

When creating tasks from meetings or direct requests:
1. A major project (1+ week)? → the `tasks` MCP's "projects" list (or equivalent). Create only with the owner's approval.
2. An inbound request from another team? → the "solicitações"/inbox list.
3. Everything else → the default tasks list.

The exact list names/IDs are workspace-specific and live in `cos-config.md → MCP details → tasks`.

---

## Adding a new capability role

If you find the CoS needs a kind of data not covered by the 5 roles above, you can extend:
1. Add a new entry to `capabilities:` in `cos-config.md` (e.g. `crm: { mcp: "", enabled: false }`).
2. Add a `### crm` section under `## MCP details`.
3. Reference `crm` from any skill's Step 0 that wants to use it.
4. The `cos-mcp-loader` doesn't change — it's generic.
