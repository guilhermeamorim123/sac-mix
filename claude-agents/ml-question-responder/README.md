---
type: agent-readme
---

# ML Question Responder

Agente de atendimento e conversão de vendas para vendedores do Mercado Livre. Busca perguntas pendentes via API, analisa o sentimento do comprador, responde com tom persuasivo e posta automaticamente quando confiante.

## Features

- Suporte a múltiplas contas de vendedor (ML_ACCESS_TOKEN_1, _2, ...)
- Análise de sentimento do comprador (curioso, cético, frustrado, animado, sensível a preço)
- Resposta persuasiva com benefício-chave relevante ao contexto
- Limiar de confiança: só posta automaticamente quando ≥90% seguro
- Escalada automática para tópicos bloqueados (preço, devoluções, defeitos)
- Fila de revisão em `pending-questions.md`
- Log diário de respostas em `logs/YYYY-MM-DD.md`
- Busca web como fallback quando anúncio não tem o dado (antes de escalar)
- Resposta genérica humanizada para casos sem dado em nenhuma fonte
- **SAC Mix IA (opcional)** — base de conhecimento por produto (consultada com
  prioridade máxima antes da busca web) + histórico de todas as respostas
  visível na tela "SAC Mix IA" do app mixfoco.com.br. Ver seção abaixo.

## Architecture

```
ml-question-responder/
├── CLAUDE.md                          # Instruções do agente
├── .claude/
│   ├── settings.json                  # Permissões Bash
│   └── skills/answer-questions/
│       └── SKILL.md                   # /answer-questions skill
├── scripts/
│   ├── ml_auth.py                     # OAuth2 multi-conta
│   ├── get_questions.py               # GET /my/questions
│   ├── get_item.py                    # GET /items/{id} + /description
│   └── post_answer.py                 # POST /answers
├── context/
│   └── answer-guidelines.md           # Tom, sentimento, templates, escalada
└── logs/                              # Criado em runtime (gitignored)
```

## Setup

### 1. Criar app no Mercado Livre Developers

1. Acesse https://developers.mercadolivre.com.br
2. Crie uma nova aplicação com escopo `questions:read` e `questions:write`
3. Anote o `App ID` e `Secret Key`

### 2. Autorizar na sua conta de vendedor

Execute o fluxo OAuth2:

```bash
python scripts/ml_auth.py --setup --account 1
```

O script abre o browser para autorizar. Após autorizar, salva os tokens nas variáveis de ambiente.

### 3. Configurar variáveis de ambiente (por conta)

```bash
# Conta 1
export ML_CLIENT_ID_1="seu_app_id"
export ML_CLIENT_SECRET_1="seu_secret"
export ML_ACCESS_TOKEN_1="APP_USR-..."
export ML_REFRESH_TOKEN_1="TG-..."

# Conta 2
export ML_CLIENT_ID_2="seu_app_id"
export ML_CLIENT_SECRET_2="seu_secret"
export ML_ACCESS_TOKEN_2="APP_USR-..."
export ML_REFRESH_TOKEN_2="TG-..."
```

No Windows (PowerShell persistente):
```powershell
[System.Environment]::SetEnvironmentVariable("ML_CLIENT_ID_1","seu_app_id","User")
[System.Environment]::SetEnvironmentVariable("ML_CLIENT_SECRET_1","seu_secret","User")
[System.Environment]::SetEnvironmentVariable("ML_ACCESS_TOKEN_1","APP_USR-...","User")
[System.Environment]::SetEnvironmentVariable("ML_REFRESH_TOKEN_1","TG-...","User")
```

### 4. Instalar dependências

```bash
pip install requests
```

### 5. Integrar ao seu vault CoS

Copie a pasta `claude-agents/ml-question-responder/` para o projeto onde você quer usar o agente, ou rode direto daqui com:

```bash
claude  # e depois /answer-questions
```

### 6. (Opcional) Integração SAC Mix IA — histórico + base de conhecimento por produto

O `auto_responder.py` (o script que roda no GitHub Actions, ver `scripts/auto_responder.py`)
pode reportar cada resposta dada e consultar uma base de conhecimento por produto
gerenciada na tela **SAC Mix IA** do app `mixfoco.com.br`. Sem essas variáveis, o
agente funciona exatamente como antes — só não reporta histórico nem consulta a KB.

```bash
export MIXFOCO_API_URL="https://mixfoco.com.br"
export MIXFOCO_ML_IA_SECRET="mesmo_valor_do_ML_IA_INGEST_SECRET_configurado_na_API"
```

No GitHub Actions, configure os secrets `MIXFOCO_API_URL` e `MIXFOCO_ML_IA_SECRET`
no repositório (Settings → Secrets and variables → Actions) — já estão referenciados
em `.github/workflows/ml-responder.yml`.

Fluxo:
1. Antes de gerar a resposta, o script busca `GET /mixfoco/ml-ia/kb-produto/{item_id}`
   — entradas cadastradas na tela SAC Mix IA para aquele MLB específico
2. Se houver entradas, elas viram contexto de **prioridade máxima** no prompt do Claude
   (fonte reportada como `KB` no log e no histórico)
3. Depois de responder (ou escalar/errar), o script reporta via
   `POST /mixfoco/ml-ia/ingest` — a resposta aparece na sub-aba "Respostas da IA"
4. A base de conhecimento por produto é gerenciada direto na sub-aba
   "Base de Conhecimento por Produto" (criar/editar/remover por item_id/SKU)

## Usage

```
/answer-questions
```

O agente busca todas as perguntas pendentes, processa cada uma e mostra um resumo ao final.

## Files

| Arquivo | Descrição |
|---------|-----------|
| `CLAUDE.md` | Instruções completas do agente |
| `.claude/settings.json` | Permissões necessárias |
| `.claude/skills/answer-questions/SKILL.md` | Skill `/answer-questions` |
| `scripts/auto_responder.py` | Script standalone rodado pelo GitHub Actions — busca, responde, posta, reporta ao SAC Mix IA |
| `scripts/ml_auth.py` | Autenticação OAuth2, refresh de tokens |
| `scripts/get_questions.py` | Busca perguntas UNANSWERED por conta |
| `scripts/get_item.py` | Busca título, atributos e descrição do anúncio |
| `scripts/post_answer.py` | Posta resposta aprovada no ML |
| `context/answer-guidelines.md` | Regras de tom, sentimento e persuasão |

## Changelog

- 2026-07-04: Integração opcional com SAC Mix IA (mixfoco.com.br) — histórico de
  respostas + base de conhecimento por produto consultada antes da busca web
- 2026-05-28: Initial creation
