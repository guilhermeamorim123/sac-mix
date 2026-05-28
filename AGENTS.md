# AGENTS.md

This file is the agent instructions for **Codex**. The full system definition lives in `CLAUDE.md` (written for Claude Code); both share the same vault — `context/`, `templates/`, `memory/`, `docs/reference/` are host-agnostic.

## First time here?
Run `/cos-setup` (or follow the manual setup in `CLAUDE.md`). When you choose `host: codex`, `cos-setup` regenerates this file with:
- Your "Your Setup" block (owner, role, company, persona, language, active capabilities)
- A prose walk-through of the CoS workflows (`/cos-daily-brief`, `/cos-prepare-1on1`, etc.) adapted to Codex (skills under `.claude/skills/` are Claude-Code-native; on Codex you read them as reference and follow the steps yourself or via your own custom commands)

## Capability roles (same model as Claude Code)
The CoS is MCP-agnostic: it defines **capability roles** (`tasks`, `comms`, `calendar`, `email`, `docs`) that you map to MCPs in `context/cos-config.md`. On Codex, MCPs are configured in `~/.codex/config.toml`. See `docs/reference/integrations.md` + `docs/reference/config-contract.md` for the model.

## Loader pattern
- `cos-vault-loader`, `cos-references-loader` — file-only, always-on.
- `cos-mcp-loader` — example pattern for querying any MCP. Adapt to Codex's tool-use surface.

---

> This is a stub. Once you run `/cos-setup` with `host: codex`, this file is replaced by a full Codex-adapted version of the CoS instructions.
