---
name: cos-setup
description: Onboarding interativo do segundo cérebro — pergunta o host (Claude Code ou Codex), entrevista o usuário, popula context/team/memory/cos-config e ajuda a configurar a stack de MCPs por capability role. Gera CLAUDE.md OU AGENTS.md conforme o host. Modos express e completo.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, TaskCreate, TaskUpdate, TaskList
---

Transformar o template em branco no segundo cérebro personalizado do usuário. Esta skill conduz uma entrevista estruturada, fase por fase, e escreve todos os arquivos necessários para que as demais skills funcionem com contexto real desde o primeiro uso. Também ajuda o usuário a entender as capability roles do CoS e a mapear cada uma para uma ferramenta (MCP) da stack pessoal dele.

> **Contrato de segurança (leia antes de executar qualquer escrita):**
> Esta skill escreve APENAS em `context/`, `team/`, `memory/`, e no arquivo de host do CoS (`CLAUDE.md` se `host: claude-code`, ou `AGENTS.md` se `host: codex`). NUNCA edita arquivos de skill, agents ou scripts. É re-rodável: sempre pergunta antes de sobrescrever um arquivo já preenchido.

Modelo de interação:
- Uma pergunta por vez. Prefira `AskUserQuestion`.
- Valide cada fase antes de seguir.
- Sem travessão `—` no output ao usuário.
- Trate respostas vagas pedindo clarificação, não preenchendo no escuro.

---

## Fase 0 — Detecção, host e modo

1. **Detecção.** Leia `context/cos-config.md`. Se `owner` ainda é `"[[Owner Name]]"`, é primeira vez. Caso contrário, `AskUserQuestion`:
   - (A) Refazer do zero
   - (B) Ajustar pontos específicos (vá direto à fase relevante)
   - (C) Cancelar

2. **Host.** Pergunte qual agente vai rodar este vault — `AskUserQuestion`:
   - (A) **Claude Code** (usa `CLAUDE.md` + as skills nativas em `.claude/skills/`)
   - (B) **Codex** (usa `AGENTS.md`; MCPs configurados via `~/.codex/config.toml`)
   
   Registre em `cos-config.md → host`. Isto define qual arquivo de instruções a Fase 5 vai gerar.

3. **Detecção de MCPs disponíveis** (best-effort): tente chamadas leves para os MCPs mais comuns que o host suportar (ex: no Claude Code, conectores claude.ai como ClickUp/Slack/Calendar/Gmail/Drive). Anote o que está reachable — usado em Fase 4 como sugestão. Se nada for detectável, segue tudo manual (normal).

4. **Modo.** `AskUserQuestion`:
   - (A) **Express** (~5 min: Fase 1 + Fase 4 + Fase 5 somente)
   - (B) **Completo** (todas as fases)

---

## Fase 1 — Você (o dono do vault)

Entreviste com uma pergunta por vez:
- Nome completo
- Cargo / role
- Idioma preferido (default `pt-BR`)
- Estilo de gestão (ex: diretivo, coaching, hands-off; o que tente fazer mais; o que evita)
- Prioridades atuais / OKRs
- "O que você quer que esse segundo cérebro faça por você?" — meta do dono com o CoS

WRITE:
- `team/<owner-slug>/<Owner Name>.md` a partir de `templates/member-profile.md` (preencha NAME/ROLE/EMAIL; deixe `clickup_id`/`slack_id` vazios — preenchem em Fase 4 se MCPs forem ligados). `<owner-slug>` = kebab-case do nome.
- `team/<owner-slug>/<Owner Name> dev-plan.md` a partir de `templates/development-plan.md`.
- Atualize o frontmatter de `context/cos-config.md`: `owner`, `role`, `language`.

Mostre o perfil escrito ao usuário e confirme antes de seguir.

---

## Fase 2 — Empresa (Completo apenas)

Entrevista:
- Nome da empresa
- Setor
- Tamanho aproximado
- Produtos/serviços
- Stack de ferramentas que o time usa
- Estrutura organizacional (a quem você reporta, áreas vizinhas)

WRITE `context/company.md` a partir de `templates/company.md`. Guarde o nome da empresa para Fase 4 (`{{COMPANY_NAME}}`).

---

## Fase 3 — Time (Completo apenas)

Pergunte: "Você gere um time? (Sim/Não)". Se Não, pule.

Se Sim, para cada direto pergunte:
- Nome e cargo
- Especialidades / responsabilidades
- Ferramentas que ele usa
- (Se a capability `comms`/`tasks` foi/vai ser ligada) handle/user id pode ser preenchido depois

Para cada membro, crie `team/<member-slug>/<Member Name>.md` a partir de `templates/member-profile.md`. Atualize `context/team.md` com um bloco por membro seguindo o placeholder existente.

Confirme contagem com o usuário antes de escrever os arquivos.

---

## Fase 4 — Stack de MCPs (capability roles)

Este é o coração do setup. Explique brevemente:

> O CoS tem **5 capability roles** abstratos. Cada um é uma necessidade de informação externa que o CoS pode usar. Você decide quais ligar e qual ferramenta (MCP) atende cada uma. Vazias = vault-only para aquele papel (ainda funciona).

| Role | O que é | Exemplos de MCP |
|------|---------|-----------------|
| `tasks` | rastreador de tarefas/projetos | ClickUp, Linear, Notion, Todoist, Asana |
| `comms` | comunicação do time | Slack, Discord, Teams, Mattermost |
| `calendar` | agenda | Google Calendar, Outlook, Fastmail |
| `email` | email | Gmail, Outlook |
| `docs` | arquivos/documentos | Google Drive, Notion, Dropbox |

### Wizard role-by-role

Para CADA role, em ordem (`tasks → comms → calendar → email → docs`):

1. `AskUserQuestion`: "Você usa alguma ferramenta para **<role>** hoje?" — opções: (A) Sim, (B) Não / vault-only.
2. Se Sim:
   - Pergunte qual MCP (texto livre, oferecendo as opções da tabela acima como sugestão).
   - Se a Fase 0 detectou esse MCP disponível no host, mencione e ofereça usar.
   - Pergunte os detalhes que esse MCP precisa pro CoS funcionar bem (texto livre, guiado por sub-perguntas relevantes ao papel):
     - **tasks**: workspace/space, listas relevantes (ex: Demandas, Projetos, Solicitações), seu user id, statuses que contam como "concluído"
     - **comms**: canais relevantes (time, projetos, empresa), seu user id e handle (`@você`)
     - **calendar**: calendário primário, timezone (formato IANA, ex: `America/New_York`, `Europe/Lisbon`)
     - **email**: filtros relevantes, remetentes prioritários, domínio da empresa
     - **docs**: pastas/drives relevantes
   - Pra Codex: lembre o usuário que cada MCP precisa estar listado no `~/.codex/config.toml` dele.
   - Pra Claude Code: o conector claude.ai equivalente precisa estar logado em claude.ai/connectors.
3. Atualize `cos-config.md`:
   - `capabilities.<role>.mcp` = nome do MCP
   - `capabilities.<role>.enabled` = `true`
   - Sob `## MCP details → ### <role>`, escreva os detalhes que o usuário deu (texto livre).
4. Se Não: deixe `enabled: false` e `mcp: ""`. Adicione uma nota curta sob `### <role>` em `MCP details` ("vault-only").

Após percorrer todas as roles:
- Pergunte o `cos_persona` (default "Chief of Staff"; o usuário pode escolher outro tom/título).
- Confirme `team_size`.
- Apresente a config completa proposta (frontmatter + MCP details) num resumo formatado.
- `AskUserQuestion`: (A) Aprovar e gravar, (B) Ajustar.
- Em (A), grave o `cos-config.md` final.

### Educação leve

Antes de gravar, mostre ao usuário uma frase de cada role explicando o que muda na prática:
- "Com `tasks` ligada (X): seu `/cos-daily-brief` traz tarefas vencidas/próximas de lá. Sem: usa `- [ ]` no vault (Obsidian Tasks)."
- "Com `comms` ligada (X): `/cos-prepare-1on1` traz sinais do canal/DM. Sem: usa só o histórico do vault."
- "Com `calendar` ligada (X): briefing traz reuniões e blocos livres. Sem: pergunta o horário ao você."
- "Com `email` ligada (X): briefing traz emails pendentes. Sem: pula."
- "Com `docs` ligada (X): podemos buscar referências em arquivos. Sem: só vault."

---

## Fase 5 — Fechamento + arquivo de host

1. **Memória semente.** Escreva `memory/user_owner.md` (frontmatter `type: user`) com role + estilo de gestão. Adicione uma linha em `memory/MEMORY.md` sob `## User` apontando pra esse arquivo.

2. **Arquivo de host.** Dependendo do `host`:
   - Se `host: claude-code`: edite SÓ o bloco marcado de `CLAUDE.md`:
     - Encontre `<!-- cos-setup:start -->` e `<!-- cos-setup:end -->`
     - Substitua o conteúdo entre eles por um resumo: owner, role, company, persona, language, lista de capabilities ativas com o MCP de cada uma.
   - Se `host: codex`: gere/atualize `AGENTS.md` na raiz a partir do CLAUDE.md (prosa adaptada ao Codex):
     - Mesmo conteúdo de papel, mas instrua o Codex a tratar `.claude/skills/` como referência (skills são nativas do Claude Code; Codex deve seguir os passos descritos em prosa)
     - Inclua o mesmo bloco "Your Setup" populado
     - Mencione que MCPs vivem em `~/.codex/config.toml` no host do usuário

3. **Mapa do que foi criado.** Mostre uma lista enxuta dos arquivos escritos/atualizados nesta sessão.

4. **Primeiros passos.** Sugira comandos baseados nas capabilities ativas:
   - Se `calendar` ligada: "Amanhã rode `/cos-daily-brief`."
   - Se `comms` + um direto cadastrado: "Pra preparar um 1:1: `/cos-prepare-1on1 <nome>`."
   - Se `tasks` ligada: "Pra criar/evoluir um projeto: `/cos-project-management`."
   - Sempre: "Pra processar uma reunião gravada: `/cos-process-meeting`."

5. **Lembrete.** "Pode ligar/desligar capabilities depois editando `context/cos-config.md`. Se trocar o host (Claude Code ↔ Codex), me rode de novo com 'Ajustar' que eu re-gero o arquivo de instruções certo."

---

## Re-execução

- "Refazer do zero": confirme com o usuário que isso vai sobrescrever; refaça todas as fases.
- "Ajustar": `AskUserQuestion` qual fase quer revisitar (1: você, 2: empresa, 3: time, 4: MCPs, 5: arquivo de host). Pule direto pra ela.
- Antes de sobrescrever qualquer arquivo já preenchido, mostre o conteúdo atual e pergunte se quer manter/substituir/mesclar.
- NUNCA destrua registros de reunião (`weeklys/`, `daily-briefs/`, arquivos sob `team/<slug>/meetings/`) ou memória que não seja a semente `user_owner.md`.
