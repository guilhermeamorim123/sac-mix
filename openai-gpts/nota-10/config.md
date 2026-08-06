# Nota 10 — Configuração do GPT

## Capabilities

| Capability | Enabled | Notes |
|------------|---------|-------|
| Web Search | Yes | Para buscar explicações complementares quando o conteúdo enviado for insuficiente |
| Code Interpreter | Yes | Necessário para gerar PDFs dos trabalhos escolares (Workflow 6) |
| Image Generation | No | Fora do escopo |
| Canvas | No | Fora do escopo |

## Conversation Starters

1. "O que você consegue fazer por mim?"
2. "Me manda o conteúdo da matéria e vou resumir para você..."
3. "Quero questões de revisão de nível vestibular sobre..."
4. "Prova amanhã de Matemática — me manda o conteúdo!"

## Knowledge Files to Upload

| File | Format | Structure | Loading | Purpose |
|------|--------|-----------|---------|---------|
| `knowledge/study-methodology.md` | Markdown | Reference Guide | **Read before starting** | Metodologia de active recall, níveis de questão, plano de estudos, estilo por matéria |

## Additional Settings

- **Name**: Nota 10
- **Description**: Seu assistente de estudos para o vestibular. Manda o conteúdo e eu resumo, crio questões e monto seu plano de estudos.
- **Profile Picture**: Ícone de livro aberto com um "10" em destaque, cores verde e branco

## Test Prompts

Use esses prompts para testar o GPT após configurar:

1. Cole um trecho de texto sobre Termodynamics (Física) e verifique:
   - O agente gera um resumo com fórmulas no bloco separado
   - O agente oferece questões de revisão após o resumo
   - O estilo é passo a passo

2. Cole um trecho sobre a Revolução Francesa (História) e verifique:
   - O agente gera um resumo em bullets diretos, sem fórmulas
   - O estilo é conciso, sem enrolação

3. Diga "Prova amanhã de Química" e verifique:
   - O agente entra no Modo Véspera
   - Gera os 5 pontos + macetes + 3 questões de aquecimento

4. Peça um plano de estudos para "ENEM em novembro, foco em Matemática e Redação, 2h por dia" e verifique:
   - O agente pergunta mais detalhes antes de gerar o plano
   - O plano segue as regras de distribuição de energia por dia

5. Peça as respostas das questões SEM tentar responder primeiro e verifique:
   - O agente não revela as respostas antes de incentivar a tentativa
