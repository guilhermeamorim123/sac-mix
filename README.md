# Chief of Staff — Second Brain Template

Um segundo cérebro reutilizável para gestores, em Obsidian + Claude Code. Clone, abra no Claude Code e rode `/cos-setup`: o Claude entrevista você e monta o vault com o seu contexto, seu time e as ferramentas que você usa. Tudo funciona **vault-first**, sem nenhuma integração ligada já entrega valor; conecte Slack/Gmail/ClickUp/Calendar quando quiser.

## O que é
Um "Chief of Staff" que prepara e processa 1:1s, weeklys e reuniões de projeto, mantém um log de decisões, rastreia tarefas e o desenvolvimento do time, e monta seu briefing diário. As notas são Markdown puro no Obsidian; o Claude opera sobre elas via skills.

## Pré-requisitos
- [Obsidian](https://obsidian.md) com os plugins **Tasks** e **Dataview** (comunidade).
- [Claude Code](https://claude.com/claude-code).
- No seu shell rc (`~/.zshrc`): `export CLAUDE_CODE_FORK_SUBAGENT=1` (subagentes mais rápidos). Reinicie o Claude Code depois.

## Começando (caminho rápido)
1. Use este repositório como template ("Use this template" no GitHub) ou `git clone`.
2. Abra a pasta no Obsidian (instale Tasks + Dataview) e no Claude Code.
3. Rode `/cos-setup` e responda a entrevista. Pronto: seu segundo cérebro está montado.

## Caminho manual (sem a entrevista)
Prefere preencher à mão? Edite:
1. `context/cos-config.md` — sua identidade, os toggles de integração e os IDs (só das que usar).
2. `context/company.md`, `context/team.md` — empresa e time.
3. `team/<voce>/<Seu Nome>.md` — seu perfil (a partir de `templates/member-profile.md`).
As skills lêem o `cos-config.md` no Step 0 (ver `docs/reference/config-contract.md`) e degradam sozinhas quando uma integração está off.

## Integrações (opcionais)
Ligue só o que usar, em `context/cos-config.md → integrations`. As integrações chegam via conectores do claude.ai (Slack, Gmail, ClickUp, Google Calendar, Drive). Sem nenhuma ligada, as skills rodam só com o vault:
- **Tarefas sem ClickUp** → checkboxes Obsidian Tasks (ver `docs/reference/obsidian-tasks.md`).
- **Sem Slack/Gmail/Calendar** → a skill pula esses passos e usa as notas.

## As skills
| Comando | O que faz |
|---|---|
| `/cos-setup` | Onboarding: monta seu segundo cérebro por entrevista |
| `/cos-daily-brief` | Briefing executivo e planejamento do dia |
| `/cos-prepare-1on1 <nome>` | Prepara um 1:1 |
| `/cos-prepare-weekly` | Prepara a weekly do time |
| `/cos-process-1on1 <nome>` | Processa a gravação de um 1:1 |
| `/cos-process-weekly` | Processa a gravação da weekly |
| `/cos-process-meeting` | Processa reunião de projeto/demanda |
| `/cos-project-management` | Cria/evolui projetos e tarefas |
| `/cos-context-maintenance` | Manutenção de contexto do vault |
| `/cos-session-sync` | Distribui o que foi aprendido na sessão |
| `/cos-inbox-process` | Processa itens da pasta `+Inbox/` |

## Estrutura
- `context/` — config, empresa, time, decisões, pendências
- `team/` · `people/` — perfis (diretos e demais)
- `projects/` · `companies/` — contexto de projetos e organizações
- `daily-briefs/` · `weeklys/` — registros
- `memory/` — memória persistente do CoS (índice em `MEMORY.md`)
- `templates/` · `docs/reference/` — templates e referências
- `.claude/skills/` · `.claude/agents/` — as skills e os loaders

## Privacidade
Este template não contém dados de ninguém. Tudo que você cria fica local no seu vault. Conectores são por sessão e sob seu controle.
