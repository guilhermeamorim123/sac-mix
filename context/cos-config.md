---
type: config
host: claude-code
owner: "[[Guilherme Figueredo]]"
role: "Estudante | Gestor de Anuncios | T.I. | Seller"
cos_persona: "BIG FRIEND"
team_size: 0
language: "pt-BR"
capabilities:
  tasks:    { mcp: "", enabled: false }
  comms:    { mcp: "whatsapp", enabled: true }
  calendar: { mcp: "", enabled: false }
  email:    { mcp: "", enabled: false }
  docs:     { mcp: "Google Drive", enabled: true }
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
vault-only - sem MCP configurado.

### comms
WhatsApp MCP — bridge local rodando em `whatsapp-mcp/whatsapp-bridge/`. MCP registrado em `.mcp.json` como `whatsapp`. Ferramentas disponíveis: list_chats, list_messages, send_message, search_contacts, get_direct_chat_by_contact.

### calendar
vault-only - sem calendario digital configurado.

### email
vault-only - email nao e canal principal de trabalho por ora.

### docs
Google Drive - planilhas de vendas e anuncios da empresa da familia. Conectar em claude.ai/connectors com a conta Google do usuario.
