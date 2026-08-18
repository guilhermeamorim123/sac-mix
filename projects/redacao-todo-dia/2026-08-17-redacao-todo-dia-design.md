---
type: spec
subtype: design
name: "Redação Todo Dia — Design"
project: "[[Redação Todo Dia]]"
owner: "[[Guilherme Figueredo]]"
date: 2026-08-17
status: em revisão
tags:
  - project/redacao-todo-dia
---

# Redação Todo Dia — Design

## Objetivo

Um infoproduto sazonal para o **ENEM 2026** (provas em 8 e 15 de novembro),
vendido com **tráfego pago no Meta** para público aberto, que resolve duas
coisas ao mesmo tempo:

1. **Ser comprado** — promessa concreta, ticket de impulso, checkout com Pix.
2. **Ser usado** — o aluno escreve uma redação, fotografa, e recebe correção
   nas 5 competências do ENEM em minutos. Cada correção é a dose que faz voltar.

A segunda metade é o diferencial. Quase todo produto de ENEM vende bem e é
abandonado em duas semanas, porque o valor está no conteúdo e o conteúdo não
cobra nada de volta. Aqui o valor está no **retorno**.

**Nome de trabalho:** Redação Todo Dia. Descreve o mecanismo, não faz claim de
resultado. Alternativas descartadas: "Redação 1000" e "Nota Mil" (claim de
resultado, risco na política do Meta), "Corretor ENEM" (genérico demais).

## Não-objetivos

- **Não é curso de redação.** O guia e o ebook são material de apoio; a
  espinha dorsal é a correção.
- **Não é assinatura.** Pagamento único, acesso até 15/11/2026. Assinatura
  aumenta a fricção de compra num público de 17 anos e não faz sentido num
  produto com data de validade natural.
- **Não corrige outras matérias.** Só redação. Escopo aberto não fecha em 83
  dias.
- **Não usa a bridge de WhatsApp não-oficial.** Ver "Decisões" nº 4.
- **Não promete nota, aprovação ou vaga.** Ver "Decisões" nº 6.

## A janela que define o cronograma

Hoje é **17/08/2026**. As provas são **8 e 15 de novembro** e as inscrições
**fecharam em 12/06** — o público já pagou os R$85 e está comprometido, o que
elimina a etapa de convencer alguém a prestar o exame.

Mas a janela de **venda** é menor que a janela até a prova: ninguém compra
material de estudo a menos de três semanas do ENEM. Na prática dá para vender
até **meados de outubro**, o que deixa cerca de **cinco semanas de tráfego** se
o produto ficar pronto no começo de setembro.

## Arquitetura do produto

Três camadas, cada uma cobrindo a falha da outra.

| Camada | O que é | Falha que cobre |
|---|---|---|
| **Corretor** | Foto da redação manuscrita → nota nas 5 competências (0–200 cada, 0–1000 total) + 2 pontos de melhoria por competência | Sem ele, o aluno escreve no vácuo e desiste |
| **Desafio diário** | Tema + repertório + tarefa de 10 min, por email às 18h, até a prova | Sem ele, o aluno precisa decidir estudar todo dia — e não decide |
| **Guia** | Estrutura, modelos de introdução e conclusão, banco de repertório | Sem ele, a correção aponta o erro e o aluno não sabe como consertar |
| **Painel de evolução** | Gráfico das notas ao longo do tempo | É o que faz voltar: ver a linha subir de 520 para 680 é prova de que funciona |

O painel é pequeno de construir e é a peça que mais retém. Não cortar.

## Arquitetura técnica

### Stack

| Peça | Escolha | Motivo |
|---|---|---|
| App | Next.js na **Vercel**, com Supabase para auth/dados/arquivos | Escolha do dono. Front próprio em vez do Lovable |
| Correção | **API route server-side**, nunca no browser | A `ANTHROPIC_API_KEY` não pode sair do servidor: no cliente, qualquer um abre o DevTools e usa sua chave |
| Auth | Magic link por email (Supabase Auth) | Senha é fricção pura num público de 17 anos |
| Storage | Supabase Storage (fotos) | Nativo do stack |
| Checkout | Kiwify ou Hotmart | Pix nativo, nota fiscal, reembolso, webhook |
| IA | Claude via API (`claude-opus-5`) | Visão de alta resolução + avaliação; ver abaixo |
| Email | Resend | Desafio diário + magic link |

### Fluxo de liberação de acesso

```
Compra na Kiwify
   → webhook (order.approved) → Supabase Edge Function
   → INSERT em entitlements (email, expires_at = 2026-11-15)
   → aluno faz login com magic link no mesmo email
   → app checa entitlements antes de liberar qualquer tela
```

Reembolso dispara `order.refunded` → `UPDATE entitlements SET revoked = true`.

### A restrição da Vercel que molda o app

Uma correção completa são duas chamadas ao Opus 5 com thinking ligado — na
casa de dezenas de segundos, às vezes mais de um minuto. O limite padrão de
função na Vercel é **60s no Hobby** e 60s no Pro (até 300s configurável).
Com **Fluid compute** ligado, o teto vai a 300s no Hobby.

Isso não é detalhe de infraestrutura: se a função estourar, o aluno vê erro
depois de esperar um minuto olhando para uma tela parada, e a correção que já
foi paga se perde. Três providências, todas obrigatórias:

1. Ligar **Fluid compute** e declarar `maxDuration` na rota de correção
2. **Streaming** da resposta, para o aluno ver progresso em vez de tela morta
3. Gravar a correção no banco **assim que chega**, antes de renderizar — se o
   navegador cair, o aluno não perde o que pagou

### Fluxo de correção — duas etapas, com confirmação humana no meio

Este é o coração do produto e a decisão de design mais importante dele.

```
1. Aluno fotografa a redação manuscrita e faz upload
2. Etapa A — TRANSCRIÇÃO
   Claude recebe a imagem e devolve SÓ o texto transcrito, sem avaliar nada
3. O texto transcrito é mostrado ao aluno para conferir e corrigir
   ("Confere se li tua letra direito")
4. Etapa B — AVALIAÇÃO
   Claude recebe o texto CONFIRMADO + a rubrica oficial das 5 competências
   e devolve JSON estruturado com notas e feedback
5. Nota salva no histórico → aparece no gráfico
```

**Por que separar em duas etapas:** o risco técnico número 1 é OCR de letra
manuscrita de adolescente. Se o modelo lê errado, corrige errado, e o aluno
perde a confiança na primeira semana. Separando, o erro de leitura vira uma
tela de conferência de 10 segundos em vez de uma correção errada. Também dá
ao aluno a sensação de controle, que é boa para retenção.

### Contrato da etapa B (saída estruturada)

Usar `output_config.format` com JSON Schema — nada de parsear texto livre:

```json
{
  "competencias": [
    { "numero": 1, "nota": 160, "justificativa": "...", "melhorias": ["...", "..."] }
  ],
  "nota_total": 780,
  "fuga_ao_tema": false,
  "resumo": "..."
}
```

Regras da rubrica que precisam estar no prompt de sistema, porque são regras
reais do ENEM e o modelo erra sem elas:

Conferidas contra a [Cartilha do Participante do INEP](https://download.inep.gov.br/publicacoes/institucionais/avaliacoes_e_exames_da_educacao_basica/a_redacao_no_enem_2025_cartilha_do_participante.pdf):

- **Oito causas anulam a redação inteira:** fuga total ao tema, texto não
  dissertativo-argumentativo, parte deliberadamente desconectada do tema,
  impropérios ou desenhos, identificação fora do espaço próprio, texto
  predominantemente em língua estrangeira, texto ilegível, folha em branco.
  As duas últimas e a de identificação importam **porque a entrada é foto**
- **Até 7 linhas (7 inclusive) → nota 0.** A regra é "até", não "menos de"
- **Tangenciamento não anula, mas trava C2, C3 e C5 em 40 pontos cada.** Não é
  penalização dentro da escala normal — é teto duro, e são três competências,
  não duas. É a regra que mais se erra
- **Cópia dos textos motivadores não anula:** as linhas copiadas são
  descontadas da contagem, e só zera se sobrarem 7 ou menos
- **Proposta de intervenção que fere direitos humanos → competência 5 = 0.**
  Até 2017 zerava a redação inteira; desde 2018 zera só a C5
- Texto sem proposta de intervenção → competência 5 baixa mesmo com texto bom

A aritmética e os zeramentos **não** são delegados ao modelo: ele julga cada
competência, e o código soma e aplica as regras de anulação. Somar cinco
números é onde LLM erra sem ganhar nada em troca.

### Modelo e custo por correção

Model IDs (confirmados na referência da API em 17/08/2026):

| Modelo | ID | Input $/1M | Output $/1M |
|---|---|---|---|
| Claude Opus 5 | `claude-opus-5` | $5,00 | $25,00 |
| Claude Sonnet 5 | `claude-sonnet-5` | $3,00 ($2,00 promocional até 31/08/2026) | $15,00 ($10,00 promocional) |
| Claude Haiku 4.5 | `claude-haiku-4-5` | $1,00 | $5,00 |

Opus 5 e Sonnet 5 estão na faixa de **visão em alta resolução** (até 2576 px no
lado maior, até ~4784 tokens por imagem), que é exatamente o que letra
manuscrita fotografada precisa. Haiku 4.5 fica fora — economia falsa quando a
qualidade da leitura é o produto.

**Estimativa por correção completa (etapa A + etapa B), com foto em alta
resolução e redação de ~30 linhas:**

> ⚠️ **Estimativa revisada em 17/08/2026 e ainda não medida.** A primeira
> versão deste spec dizia ~US$ 0,08 por correção. Estava errada: o thinking do
> Opus 5 vem **ligado por padrão** e domina os tokens de saída, e a foto entra
> na faixa de alta resolução (até 4.784 tokens só de imagem).

| | Opus 5, effort alto |
|---|---|
| Etapa A (transcrição) — entrada com foto | ~US$ 0,025 |
| Etapa A — saída (texto + thinking) | ~US$ 0,050 |
| Etapa B (avaliação) — entrada com rubrica cacheada | ~US$ 0,004 |
| Etapa B — saída (JSON + thinking) | ~US$ 0,150 |
| **Total** | **~US$ 0,23** (faixa plausível 0,14–0,33) |
| Em reais (a US$1 ≈ R$5,20) | **~R$ 1,20** |

**Isso muda a conta do produto.** Um aluno que mande 25 redações passa de ~R$11
para **~R$30**. Num produto de R$47 com ~9% de taxa (~R$43 líquidos), o custo
de IA come **cerca de 70% da receita** — não os 25% da estimativa original.

Três alavancas, na ordem em que valem a pena:

1. **`effort` por etapa.** Transcrição é OCR, não raciocínio: já está em `low`.
   A avaliação está em `high` durante a calibração porque é a qualidade que
   está sendo medida — mas o Opus 5 rende muito acima do esperado em `medium`
   e `low`, e essa é a alavanca mais direta. Varrer os três níveis contra o
   mesmo conjunto é tarefa da semana 2.
2. **Redimensionar a foto** para ~2576 px no lado maior antes do upload. Corta
   tokens de imagem e evita o limite de 10 MB da API.
3. **Trocar para Sonnet 5**, que custa ~40% menos por token.

**Nenhum desses números foi medido contra a API.** O harness imprime o custo
real de cada correção e o total da calibração — o primeiro `run.py calibrar`
substitui esta tabela inteira por dados.

**Decisão:** começar em `claude-opus-5` na fase de calibração, quando a
qualidade da correção é a única coisa que importa. Depois da calibração, medir
Sonnet 5 contra o mesmo conjunto de redações; se o erro médio ficar dentro da
tolerância, trocar. A economia é R$4,50 por aluno ativo — relevante em volume,
irrelevante enquanto não houver volume.

Aplicar **prompt caching** na rubrica das 5 competências (bloco estável, mesmo
em toda requisição). O mínimo cacheável no Opus 5 é 512 tokens; a rubrica passa
disso. Isso derruba o custo de input da etapa B em ~90% nas leituras seguintes.

**Rate limit:** 3 correções por dia por usuário. Uso real fica muito abaixo
disso (1/dia é a promessa), e o teto protege contra abuso e contra custo
descontrolado. 3 × 60 dias = 180 correções, teto de ~R$77 no pior caso
absoluto num único aluno — que não vai acontecer, mas é o limite conhecido.

### Desafio diário

- Tabela `daily_themes` com 60 temas pré-escritos (tema, texto motivador curto,
  repertório sugerido, tarefa de 10 min)
- Cron diário às 18h dispara email via Resend com o tema do dia e link direto
  para a tela de envio
- Emails param em 07/11 (véspera da primeira prova)

Os 60 temas são conteúdo produzido uma vez, antes do lançamento. É o item de
produção mais demorado depois da calibração.

## Oferta e precificação

Dois planos, com o degrau em **conteúdo**, não em cota de correção.

| Plano | Preço | O que tem |
|---|---|---|
| **Corretor** | **R$ 45,90** | Correção nas 5 competências (até 3/dia) + desafio diário + guia + painel de evolução, até 15/11/2026 |
| **Acesso completo** | **R$ 59,90** | Tudo do Corretor **+ ebook**: 20 temas prováveis de 2026 com redação-modelo comentada, banco de repertório, e exercícios estilo ENEM |

**Por que o degrau é conteúdo e não cota.** O ebook é PDF: custo marginal zero,
então os R$14 de diferença entram quase inteiros. Se os planos se separassem
por "mais correções", o plano caro teria margem **pior** que o barato — o
oposto do que se quer.

**Por que só R$14 de diferença.** É pequeno demais para recusar quando o de
cima tem algo que o de baixo não tem. A meta é que a maioria suba de plano, não
que os dois vendam igual.

### A conta que decide se esses preços funcionam

Com ~9% de taxa de plataforma e CPA de R$20:

| | Líquido | IA (20 correções a R$1,20) | CPA | Sobra |
|---|---|---|---|---|
| R$ 45,90 | 41,77 | −24,00 | −20,00 | **−R$ 2,23** |
| R$ 59,90 | 54,51 | −24,00 | −20,00 | **+R$ 10,51** |

**No custo de IA atual, o plano de baixo dá prejuízo em quem usa o produto** —
e "usar o produto" é a tese inteira. Quem compra e não abre é lucrativo; quem
escreve toda semana dá prejuízo. Incentivo invertido.

A mesma conta com a correção a R$0,40, que é onde ela deve cair depois da
varredura de `effort`:

| | Líquido | IA (20 correções a R$0,40) | CPA | Sobra |
|---|---|---|---|---|
| R$ 45,90 | 41,77 | −8,00 | −20,00 | **+R$ 13,77** |
| R$ 59,90 | 54,51 | −8,00 | −20,00 | **+R$ 26,51** |

**Conclusão: a varredura de `effort` não é otimização, é pré-condição destes
preços.** Roda junto com a calibração, na mesma semana.

**Ancoragem:** correção humana avulsa custa R$25–40 por redação. O plano
completo custa menos que duas correções avulsas e entrega dezenas delas.

**Pix é obrigatório** — exigir cartão de um público de 17 anos descarta metade
do tráfego, e em boa parte dos casos quem paga é a mãe.

## Página de vendas — o comprador duplo

O clique vem do aluno, o pagamento muitas vezes vem da mãe. A página precisa
funcionar para os dois medos:

| Persona | Medo | O que a página precisa mostrar |
|---|---|---|
| Aluno | Travar na hora da prova e não saber por onde começar | Print de uma correção real, com nota e apontamentos |
| Mãe | Ter jogado dinheiro fora num curso que o filho não abriu | O gráfico de evolução e a garantia de 7 dias |

## Decisões

| # | Data | Decisão | Racional |
|---|---|---|---|
| 1 | 2026-08-17 | Tráfego pago, público aberto | Escolha do dono. É a habilidade central dele (gestor de anúncios). Descartada a venda para os colegas do IPÊ, que teria distribuição quente mas teto de ~100 pessoas |
| 2 | 2026-08-17 | Redação, não plano de estudos nem revisão de conteúdo | É a única dor do ENEM onde "comprar" e "usar" podem ser a mesma coisa: correção é entrega recorrente com valor mensurável |
| 3 | 2026-08-17 | Web app primeiro, WhatsApp depois (ou nunca) | Sobe em dias, sem depender de aprovação humana da Meta. WhatsApp reteria melhor, mas travar o lançamento em burocracia numa janela de 83 dias é o risco maior |
| 5 | 2026-08-17 | Não usar a bridge WhatsApp de `whatsapp-mcp/` | É cliente não-oficial. Com centenas de clientes pagantes mandando foto, o número é banido — e junto vão os clientes e o canal pessoal do Guilherme |
| 6 | 2026-08-17 | Transcrição confirmada pelo aluno antes da avaliação | Converte o maior risco técnico (OCR de letra ruim) numa tela de conferência, em vez de numa correção errada |
| 7 | 2026-08-17 | Promessa de método, nunca de resultado | "Escreva uma redação por dia e receba correção nas 5 competências" passa na política de Unrealistic Outcomes do Meta. "Garanta nota 1000" derruba conta — lição já aprendida no [[Infoproduto DE]] |
| 8 | 2026-08-17 | Pagamento único até 15/11, não assinatura | Produto sazonal com validade natural; assinatura adiciona fricção de compra sem adicionar receita dentro da janela |
| 8 | 2026-08-17 | Kiwify/Hotmart, não Stripe | Pix nativo, nota fiscal e reembolso resolvidos, webhook pronto. Stripe sem Pix descarta metade do público |
| 9 | 2026-08-17 | `claude-opus-5` na calibração, avaliar `claude-sonnet-5` depois | A qualidade da correção é o produto inteiro. Otimizar custo antes de saber que a correção é boa é otimizar a coisa errada |

## Riscos e bloqueios

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| 1 | **A correção sair inconsistente.** Se a nota oscila sem motivo, o aluno percebe na segunda redação e pede reembolso | **Alta** | Calibrar contra um conjunto com nota conhecida cobrindo a faixa toda — o INEP só publica as nota 1000, então a faixa do meio precisa vir de redações corrigidas de cursinho ou simulado. Meta: erro médio ≤ 80 pontos no total, ≤ 40 por competência. **Isto é a semana 1 e bloqueia todo o resto** |
| 2 | **OCR de letra manuscrita ruim** | **Alta** | Etapa de confirmação (decisão 5) + teste com 15 fotos de letra real antes de escrever uma linha de landing page |
| 3 | **Custo de IA come ~70% da receita** na estimativa revisada, contra 25% na original | **Alta** | Varredura de `effort`, redimensionar foto, avaliar Sonnet 5. Medir antes de decidir — o harness já imprime o custo real |
| 4 | **CAC acima de R$25** | Alta | Ticket de impulso + Pix + order bump. Se o CPA não fechar em duas semanas de teste, o produto não escala e vira venda orgânica |
| 4 | **Taxa de reembolso.** CDC dá 7 dias de arrependimento; infoproduto para público jovem tem taxa alta | Média | Entrar na conta do ROAS desde o começo. O painel de evolução é o melhor antídoto: quem vê a nota subir não pede reembolso |
| 5 | **Não é mercado vazio.** Já existem apps de correção por IA no Brasil, alguns com caixa | Média | Diferencial é a janela sazonal + ritmo diário + pagar uma vez em vez de assinar |
| 6 | **Competir por tempo com o [[Atendente IA]]**, que tem meta de R$1–3k até 13/09 e precisa de 80 abordagens | **Alta** | Decisão consciente do dono. Registrado aqui para não virar surpresa em setembro |
| 7 | Conteúdo dos 60 temas não revisado por professor de redação | Média | Aceitável no v1; os temas são o insumo, a correção é o produto |

## Plano de execução

| Semana | Datas | Entrega | Porta de saída |
|---|---|---|---|
| 1 | 17–24/08 | Calibração da correção + teste de OCR com letra manuscrita real | **Se o erro médio passar de 80 pontos ou o OCR falhar, o projeto morre aqui — e morre barato** |
| 2 | 25–31/08 | App funcional (upload → transcrição → confirmação → correção → painel), checkout, landing | App recebe uma redação de ponta a ponta |
| 3 | 01–07/09 | 60 temas escritos, guia, order bump. 10 beta-testers de graça | Feedback real de 10 alunos, ajuste da correção |
| 4+ | 08/09 → 15/10 | Tráfego | ROAS ≥ 1,5 na primeira semana, senão revisar oferta |

A semana 1 é deliberadamente uma porta de saída. Se a correção não for boa,
nada do resto importa, e é melhor descobrir isso gastando uma semana do que
descobrir depois de construir app, landing e 60 temas.

## Testes

| O que | Como | Critério |
|---|---|---|
| Calibração da correção | 20 redações com nota conhecida: as nota 1000 publicadas pelo INEP (âncora de teto) + redações corrigidas de cursinho/simulado cobrindo a faixa 400–900 | Erro médio ≤ 80 pts no total, ≤ 40 pts por competência |
| Transcrição (OCR) | 15 fotos de letra manuscrita real, incluindo letra ruim e foto torta | ≥ 90% das palavras corretas antes da confirmação do aluno |
| Fuga ao tema | 5 redações fora do tema + 3 tangenciando | 5/5 fugas zeradas; 3/3 tangenciamentos travados em 40 nas C2, C3 e C5 **sem** zerar |
| Webhook de liberação | Compra de teste na Kiwify | Acesso liberado em < 60s |
| Custo real | Medir `usage` de 50 correções reais | Dentro de ±30% da estimativa de US$ 0,08 |

## Tratamento de erro

| Situação | Comportamento |
|---|---|
| Foto ilegível | Pede foto nova, com dica ("luz de cima, folha reta"). **Não consome cota** |
| Texto com até 7 linhas | Avisa antes de corrigir; se o aluno confirmar, corrige, zera e explica a regra |
| Falha da API | 2 tentativas com backoff; se falhar, devolve a cota e avisa |
| Fuga total ao tema | Zera a redação inteira e **explica a regra** — é conteúdo pedagógico, não erro. Tangenciamento é caso diferente: trava C2, C3 e C5 em 40 sem zerar |
| Acesso expirado (após 15/11) | Painel e histórico continuam visíveis; envio de nova redação bloqueado |

---
**See also:** [[Atendente IA]] | [[Infoproduto DE]] | [[Guilherme Figueredo]]
