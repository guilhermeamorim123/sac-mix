#!/usr/bin/env bash
#
# setup_mac.sh — one-shot setup of this vault on a fresh macOS machine.
#
# Run it from the vault root after cloning:
#     git clone https://github.com/guilhermeamorim123/sac-mix.git ~/"Chief of Staff"
#     cd ~/"Chief of Staff"
#     bash scripts/setup_mac.sh
#
# Idempotent: safe to re-run. It never overwrites secrets it cannot regenerate;
# anything it cannot do for you is printed as a TODO at the end.

set -uo pipefail

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$VAULT_ROOT"

WHATSAPP_UPSTREAM="https://github.com/verygoodplugins/whatsapp-mcp.git"
TODO=()

say()  { printf '\n\033[1;32m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m  ! %s\033[0m\n' "$1"; }
ok()   { printf '  \033[0;32mok\033[0m %s\n' "$1"; }

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------
say "Checking prerequisites"

missing=()
for cmd in git python3 uv go node claude; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "$cmd"
  else
    warn "$cmd not found"
    missing+=("$cmd")
  fi
done

if [ ${#missing[@]} -gt 0 ]; then
  cat <<EOF

Install what is missing, then re-run this script:

  brew install git python3 go node
  curl -LsSf https://astral.sh/uv/install.sh | sh      # uv
  npm install -g @anthropic-ai/claude-code             # claude

EOF
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Claude Code config: _claude/ -> .claude/
# ---------------------------------------------------------------------------
say "Bootstrapping .claude/ from the _claude/ mirror"
python3 scripts/bootstrap_claude.py </dev/null || warn "bootstrap_claude.py reported a problem"

# ---------------------------------------------------------------------------
# 3. Wikilink index (required by the wikilink hook)
# ---------------------------------------------------------------------------
say "Seeding the wikilink index"
python3 scripts/seed_wikilink_index.py || warn "seed_wikilink_index.py reported a problem"

# ---------------------------------------------------------------------------
# 4. WhatsApp MCP — vendored separately, it carries its own .git
# ---------------------------------------------------------------------------
say "Setting up whatsapp-mcp"
if [ -d "whatsapp-mcp/.git" ]; then
  ok "already cloned"
else
  git clone "$WHATSAPP_UPSTREAM" whatsapp-mcp \
    && ok "cloned from upstream" \
    || warn "clone failed — clone it manually into ./whatsapp-mcp"
fi
TODO+=("Start the WhatsApp bridge and scan the QR code to link this Mac as a new device:
     cd '$VAULT_ROOT/whatsapp-mcp/whatsapp-bridge' && go run .
   Do not run the bridge on both machines against the same session at once.")

# ---------------------------------------------------------------------------
# 5. Keep .claude/settings.local.json out of git (it holds tokens)
# ---------------------------------------------------------------------------
say "Protecting .claude/settings.local.json from accidental commits"
GITIGNORE_GLOBAL="$HOME/.config/git/ignore"
mkdir -p "$(dirname "$GITIGNORE_GLOBAL")"
touch "$GITIGNORE_GLOBAL"
if grep -qxF '**/.claude/settings.local.json' "$GITIGNORE_GLOBAL"; then
  ok "already in $GITIGNORE_GLOBAL"
else
  echo '**/.claude/settings.local.json' >> "$GITIGNORE_GLOBAL"
  ok "added to $GITIGNORE_GLOBAL"
fi

# ---------------------------------------------------------------------------
# 6. Required environment variable
# ---------------------------------------------------------------------------
say "Setting CLAUDE_CODE_FORK_SUBAGENT"
ZSHRC="$HOME/.zshrc"
touch "$ZSHRC"
if grep -q 'CLAUDE_CODE_FORK_SUBAGENT' "$ZSHRC"; then
  ok "already in ~/.zshrc"
else
  echo 'export CLAUDE_CODE_FORK_SUBAGENT=1' >> "$ZSHRC"
  ok "added to ~/.zshrc (run: source ~/.zshrc)"
fi

# ---------------------------------------------------------------------------
# 7. Secrets that git cannot carry
# ---------------------------------------------------------------------------
say "Checking for untracked secrets"
if [ -f "buscapp/.env.local" ]; then
  ok "buscapp/.env.local present"
else
  warn "buscapp/.env.local missing"
  TODO+=("Recreate buscapp/.env.local (copy the values from the Windows machine):
     ANTHROPIC_API_KEY=sk-ant-...
     TAVILY_API_KEY=tvly-...")
fi
TODO+=("Run 'claude' and log in. Permissions in .claude/settings.local.json do
   not sync between machines, so you will be asked to approve tools again.")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
say "Done. Remaining manual steps:"
i=1
for t in "${TODO[@]}"; do
  printf '\n%2d. %s\n' "$i" "$t"
  i=$((i + 1))
done

cat <<'EOF'

Two-machine routine
-------------------
Run /cos-sync at the START and at the END of every session, on both
machines. It pulls, commits and pushes. Skipping it is what produces
merge conflicts.

EOF
