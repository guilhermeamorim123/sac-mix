---
type: config
host: claude-code
owner: "[[Owner Name]]"
role: "—"
cos_persona: "Chief of Staff"
team_size: 0
language: "pt-BR"
capabilities:
  tasks:    { mcp: "", enabled: false }
  comms:    { mcp: "", enabled: false }
  calendar: { mcp: "", enabled: false }
  email:    { mcp: "", enabled: false }
  docs:     { mcp: "", enabled: false }
---

# CoS Config

> Identidade + host + stack de MCPs do seu Chief of Staff. Preenchido por `/cos-setup` (entrevista) ou editável à mão. As skills lêem este arquivo no Step 0 e aplicam o [[config-contract|Config Contract]].

## Identity
- **owner** — você (wikilink, ex: `"[[Maria Souza]]"`)
- **role** — seu cargo (ex: "Gerente de Vendas")
- **cos_persona** — como o CoS se posiciona (default: "Chief of Staff")
- **language** — idioma das respostas e registros (default: "pt-BR")

## Host
`host` define qual agente roda o vault: `claude-code` (usa `CLAUDE.md` + skills nativas) ou `codex` (usa `AGENTS.md`). `/cos-setup` gera o arquivo de instruções certo para o host escolhido.

## Capabilities → MCPs
Cada papel abaixo é uma necessidade do CoS. Ligue (`enabled: true`) e aponte (`mcp`) para a ferramenta que você usa. Vazio = o CoS opera **vault-only** para aquele papel (ainda funciona, só sem enriquecimento externo).

| Papel | O que é | Exemplos de MCP |
|-------|---------|-----------------|
| `tasks` | rastreador de tarefas/projetos | ClickUp, Linear, Notion, Todoist |
| `comms` | comunicação do time | Slack, Discord, Teams |
| `calendar` | agenda | Google Calendar, Outlook |
| `email` | email | Gmail, Outlook |
| `docs` | arquivos/documentos | Google Drive, Notion, Dropbox |

## MCP details
> Para cada capability ligada, anote aqui o que o MCP precisa (IDs de lista, canais, workspace, timezone, filtros). É texto livre — as skills passam isto ao `cos-mcp-loader` como contexto.

### tasks
_(ex: workspace/space, listas relevantes, quais status contam como "concluído")_

### comms
_(ex: canais relevantes, seu handle/user id)_

### calendar
_(ex: calendário primário, timezone)_

### email
_(ex: filtros, remetentes relevantes)_

### docs
_(ex: pastas/drives relevantes)_
