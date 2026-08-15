---
type: spec
subtype: design
name: "Radar Infoproduto — Design"
project: "[[Radar Infoproduto]]"
owner: "[[Guilherme Figueredo]]"
date: 2026-08-14
status: aprovado
tags:
  - project/radar-infoproduto
---

# Radar Infoproduto — Design

## Objetivo

Um script que encontra **infoprodutos validados rodando na Europa e no Reino
Unido**, ranqueados por evidência de lucro, para que [[Guilherme Figueredo]]
possa **modelar** uma oferta própria em euro.

"Validado" aqui tem definição operacional: a oferta paga anúncio há muito tempo.
Ninguém sustenta verba de mídia por meses no prejuízo. Longevidade de anúncio é
o sinal mais honesto disponível sem acesso ao faturamento de terceiros.

## Não-objetivos

- Não é buscador de produto para promover como afiliado
- Não extrai preço nem estrutura de oferta da landing page (v1 entrega o link)
- Não cobre EUA (ver "A limitação que define o escopo")
- **Não cobre o mercado brasileiro.** Anúncio entregue no Brasil não existe no
  acervo comercial da API, e pôr `BR` na lista de países degrada a coleta
  inteira para anúncio político. O que o radar enxerga é o infoprodutor
  lusófono que anuncia **na Europa** — não o que anuncia no Brasil
- Não é SaaS, não tem interface web, não roda na nuvem

## A limitação que define o escopo

A API pública da Ad Library da Meta **só devolve anúncio comercial quando o país
de entrega é da União Europeia ou o Reino Unido**. Isso não é escolha de design
— é como a API funciona. Fora de UE/UK, o parâmetro `ad_type=ALL` devolve apenas
anúncio político e de tema social.

A causa é o DSA: a lei europeia obriga plataformas grandes a manter repositório
público de **todo** anúncio entregue na UE, com dado de alcance, por cerca de 12
meses. Não existe obrigação equivalente nos EUA, e a Meta não expõe aquele
inventário por API.

Consequência prática, e ela é contraintuitiva: **a Europa é a metade aberta, os
EUA são a metade fechada.** Cobrir os EUA exigiria raspar a interface web (que a
Meta bloqueia ativamente) ou pagar ferramenta de terceiro. Ambos ficam fora do
v1.

O lado bom: por ser dado obrigatório do DSA, cada anúncio da UE traz **alcance
real** (`eu_total_reach`, `total_reach_by_location`, quebra por idade/gênero/
país), não só datas. O sinal é quantitativo, não proxy.

## Decisões

| # | Decisão | Motivo |
|---|---------|--------|
| 1 | Só Meta Ad Library API no v1 | Única fonte com API oficial, gratuita e estável. ClickBank e TikTok entram como coletores adicionais depois |
| 2 | Coletor plugável desde o v1 | ClickBank e TikTok entram como arquivos novos, sem reescrever o miolo |
| 3 | Identificação por domínio de destino, não só palavra-chave | Palavra-chave sozinha traz e-commerce e SaaS; domínio de plataforma de funil é quase prova |
| 4 | Histórico em JSON versionado, não SQLite | O vault viaja por git entre máquinas. Binário gitignorado divergiria entre notebook e desktop |
| 5 | Cache do JSON bruto por rodada | 200 chamadas/hora. Ajustar score ou markdown não pode custar cota |
| 6 | Landing page não é baixada no v1 | Modelar oferta é trabalho de julgamento. O script entrega o link; a leitura é humana |
| 7 | Agrupamento por `(page_id, domínio)` | Uma oferta roda dezenas de criativos. A unidade de análise é a oferta, não o anúncio |
| 8 | Português é **rótulo**, não filtro (revisto em 15/08/2026) | A decisão original excluía Brasil. Revertida pelo dono: o infoprodutor lusófono que anuncia na Europa é justamente a cunha de menor atrito para ele. Hotmart e Kiwify passam de bloqueio a plataforma de funil — que é o que sempre foram |

## Fontes avaliadas e descartadas

| Fonte | Status | Por quê |
|-------|--------|---------|
| Meta Ad Library | **Adotada** | API oficial, grátis, alcance incluído (UE/UK) |
| TikTok Creative Center | Descartada no v1 | Sem API. Só automação de navegador, quebra a cada mudança de layout |
| ClickBank | Adiada | Sem API pública de marketplace. HTML raspável, mas ToS cinza e frágil |
| Google Trends | Adiada | Mostra atenção, não pagamento. Sinal fraco para o objetivo |

## Arquitetura

```
scripts/radar_infoproduto.py     entrada: argparse, bootstrap de venv, orquestração
scripts/radar/
  __init__.py
  config.py        termos, domínios de funil, países, pesos, limiares
  meta_client.py   único módulo que toca a rede: paginação, rate limit, retry
  classify.py      anúncio → é infoproduto? é lusófono? (funções puras)
  offers.py        anúncios → ofertas agrupadas + score (funções puras)
  store.py         histórico JSON, merge, diff entre rodadas
  render.py        ofertas → nota markdown
  tests/
    fixtures/      resposta real da API, capturada uma vez
    test_classify.py
    test_offers.py
    test_render.py
    test_store.py
```

`scripts/radar_infoproduto.py` segue o padrão dos scripts existentes do vault:
docstring com uso no topo, `from __future__ import annotations`,
`VAULT = Path(__file__).resolve().parent.parent`, argparse, mensagens ao usuário
em pt-BR, código e comentários em inglês.

Dependências (`requests`) via venv privado com re-exec, igual ao
`transcrever_audio.py`. Diretório: `scripts/.venv-radar/`, adicionado ao
`.gitignore`.

Os testes ficam em `scripts/radar/tests/` — **não** em `scripts/tests/`, que está
no `.gitignore` do vault e desapareceria do repositório.

## Fluxo de dados

```
config.SEARCH_TERMS + config.COUNTRIES
   ↓  meta_client.fetch_ads()
       → data/runs/YYYY-MM-DD/raw.json          (cache bruto, resumível)
   ↓  classify.keep_infoproducts()
       → anúncios de infoproduto, lusófonos marcados
   ↓  offers.group_and_score()
       → ofertas com score
   ↓  store.merge()
       → data/history.json + diff (novo / sobreviveu / morreu)
   ↓  render.write_note()
       → projects/radar-infoproduto/runs/YYYY-MM-DD.md
```

Caminho dos dados: `projects/radar-infoproduto/data/`. O `raw.json` de cada
rodada fica gitignorado (volume alto, regenerável); `history.json` é versionado.

## Config

`config.py` é dado puro, sem lógica. É o arquivo que o dono edita toda semana.

**Países** — os 27 da UE mais `GB`. Lista explícita de códigos ISO.

**Termos de busca** — vocabulário de oferta em inglês no v1:
`masterclass`, `free training`, `free webinar`, `online course`,
`digital course`, `coaching program`, `mentorship`, `bootcamp`, `cohort`,
`certification`, `join the challenge`, `free guide`, `playbook`, `templates`,
`private community`, `side hustle`.

Alemão, espanhol, francês e italiano ficam para a v2 — inglês cobre UK, Irlanda
e a maior parte do marketing digital europeu, e cada idioma novo multiplica a
cota consumida.

**Domínios de plataforma de funil** — a impressão digital que identifica
infoproduto: `kajabi`, `clickfunnels`, `teachable`, `thinkific`,
`learnworlds`, `systeme.io`, `kartra`, `whop`, `skool`, `thrivecart`,
`samcart`, `podia`, `circle.so`, `mightynetworks`, `gumroad`, `stan.store`,
`everwebinar`, `webinarjam`, `demio`, `msgsndr` (GoHighLevel).

**Plataformas lusófonas** — `hotmart`, `eduzz`, `kiwify`, `braip`,
`monetizze`, `ticto`, `perfectpay`, `cakto`, `greenn`, `herospark`. Elas são
plataformas de funil como as de cima, e contam como sinal **positivo** de
infoproduto. A lista existe separada só para **rotular** a oferta como
lusófona, nunca para descartá-la.

**Plataformas de e-commerce** — usadas para *excluir*, não para incluir:
`shopify`, `myshopify`, `amazon`, `etsy`, `ebay`, `woocommerce`, `bigcartel`,
`shopee`, `aliexpress`. Anúncio que aponta para uma delas é loja, não
infoproduto.

Construtor de site genérico (`squarespace`, `wix`) fica **fora** desta lista de
propósito: o coach solo que roda o funil inteiro num deles é exatamente quem o
radar procura, e listá-los o excluiria de saída. Eles caem na regra 2, que
exige termo de oferta — a afirmação mais fraca, que é a correta aqui.

**Modo de busca** — a API aceita `search_type` (`KEYWORD_UNORDERED` ou
`KEYWORD_EXACT_PHRASE`). O padrão desordenado infla o volume com falso positivo
em termo de duas palavras. Começar em frase exata e afrouxar se o volume vier
baixo. Confirmar o nome exato do parâmetro na documentação no início da
implementação.

**Pesos e limiares** — ver seção Score.

## Classificação

Um anúncio é infoproduto se passar em **qualquer** uma destas:

1. O domínio em `ad_creative_link_captions` bate com a lista de plataformas de
   funil — incluindo as lusófonas, que são plataformas de funil como as outras
2. O texto do anúncio bate com termo de oferta **e** o destino é domínio próprio

"Domínio próprio" quer dizer: o domínio registrável extraído da caption não
aparece em nenhuma das listas conhecidas — nem plataforma de funil, nem
lusófona, nem de e-commerce. É o caso do infoprodutor que usa domínio dele.
Como a regra 2 é a mais propensa a falso positivo, ela exige as duas condições
juntas.

### Rótulo de idioma, não filtro

Nada é descartado por ser lusófono. A oferta é **marcada** como tal se
**qualquer** uma for verdade:

1. `languages` contém `pt`
2. O domínio de destino bate com a lista de plataformas lusófonas

O rótulo é "lusófono", não "brasileiro", de propósito: `pt` pega português de
Portugal também, e chamar isso de brasileiro seria simplesmente errado. Para o
dono, aliás, os dois interessam pelo mesmo motivo — é oferta que ele lê sem
fricção nenhuma.

`target_locations` com `BR` não entra na regra porque, na prática, não ocorre:
a coleta só pede países da UE e do Reino Unido.

Ambas as funções são puras, recebem o dicionário do anúncio e devolvem booleano.
São o coração testável do sistema.

## De anúncio para oferta

Chave de identidade: `(page_id, domínio_de_destino)`. Uma página pode vender
mais de uma oferta; um domínio pode ser anunciado por mais de uma página. O par
identifica a oferta.

Campos agregados por oferta:

| Campo | Origem |
|-------|--------|
| `page_name`, `page_id` | do primeiro anúncio |
| `domain` | `ad_creative_link_captions` |
| `earliest_ad_start` | menor `ad_delivery_start_time` do grupo |
| `days_live` | hoje − `earliest_ad_start` |
| `active_creatives` | anúncios do grupo sem `ad_delivery_stop_time` |
| `total_creatives` | todos os anúncios do grupo — fora do score, mas vai na ficha: 40 criativos totais com 3 ativos é oferta em declínio |
| `reach` | soma de `eu_total_reach` |
| `countries` | união de `total_reach_by_location` |
| `lusofono` | verdadeiro se **qualquer** anúncio do grupo for lusófono |
| `sample_copy` | os 3 `ad_creative_bodies` mais longos |
| `snapshot_urls` | `ad_snapshot_url` dos 5 criativos mais recentes |

## Score

Três sinais normalizados, escala 0–100:

```
longevidade = min(days_live, 180) / 180
criativos   = log10(1 + active_creatives) / log10(1 + 50)     [teto 1.0]
alcance     = log10(1 + reach) / log10(1 + 1_000_000)         [teto 1.0]

score = 100 * (0.5*longevidade + 0.3*criativos + 0.2*alcance)
```

Log em criativos e alcance porque as duas distribuições têm cauda pesada — sem
log, uma oferta gigante esmaga o ranking inteiro e some com o resto.

Longevidade pesa mais porque é o único dos três que é difícil de fingir.

**Portão de maturidade:** oferta com `days_live < 21` não entra no ranking
principal. Vai para uma seção separada, "Emergentes" — pode estar em teste e
morrer semana que vem. Os pesos e o portão vivem em `config.py`.

## Histórico

`data/history.json`, versionado no git:

```json
{
  "schema_version": 1,
  "offers": {
    "<page_id>|<domain>": {
      "page_id": "123",
      "page_name": "Exemplo Academy",
      "domain": "exemplo.kajabi.com",
      "first_seen_run": "2026-08-14",
      "last_seen_run": "2026-08-21",
      "earliest_ad_start": "2026-03-02",
      "runs": [
        {"date": "2026-08-14", "days_live": 165, "active_creatives": 22,
         "reach": 480000, "score": 78.4}
      ]
    }
  }
}
```

O diff entre rodadas classifica cada oferta em **nova**, **sobreviveu** ou
**morreu** (estava na rodada anterior, sumiu nesta).

Esse arquivo é metade do valor do projeto. Uma rodada isolada mostra quem
anuncia hoje; a série mostra quem **sobreviveu**, e sobrevivência é a prova de
lucro que o objetivo pede.

## Saída

`projects/radar-infoproduto/runs/YYYY-MM-DD.md`, com frontmatter do vault
(`type: radar-run`, `date`, `tags: project/radar-infoproduto`).

Estrutura:

1. **Resumo** — quantos anúncios coletados, quantos sobreviveram ao filtro,
   quantas ofertas, quantas novas, quantas morreram desde a última rodada
2. **Ranking** — tabela das ofertas maduras: posição, anunciante, domínio, dias
   no ar, criativos ativos, alcance, score, e uma coluna de idioma marcando as
   lusófonas
3. **Fichas do top 20** — uma seção por oferta: promessa (o texto do anúncio),
   países, idioma, links de snapshot, e o link do domínio de destino para abrir
   na mão
4. **Emergentes** — ofertas com menos de 21 dias, sem ranking
5. **Mortas nesta rodada** — sumiram desde a última. Sinal de oferta que não
   sustentou

## Tratamento de erro

| Situação | Comportamento |
|----------|---------------|
| Token ausente ou expirado | Sai com mensagem em pt-BR explicando como gerar e onde colocar |
| País fora de UE/UK na config | **Falha na largada.** Este é o modo de falha traiçoeiro: a API não dá erro, devolve só anúncio político, e o resultado parece uma lista ruim em vez de uma config errada |
| Rate limit (200/h) | Backoff exponencial, 3 tentativas. Esgotou de vez: salva o bruto parcial e avisa "coletei 6 dos 16 termos, rode de novo em 1h" |
| Falha de rede | 3 tentativas com backoff, depois pula o termo e registra no log |
| Termo sem resultado | Não é erro. Vai para o log — termo vazio é sinal para tirar da config |
| Anúncio sem `ad_creative_link_captions` | Descartado silenciosamente, contabilizado no resumo |
| `raw.json` já existe para a data | Reusa o cache. `--force` refaz a coleta |

O token vem de variável de ambiente `META_AD_LIBRARY_TOKEN` ou de um `.env` na
raiz do vault, que já está no `.gitignore`.

## Testes

`classify`, `offers`, `render` e `store` são funções puras. Testam com fixture
de resposta real da API, capturada uma vez e commitada. **Nenhum teste toca a
rede.**

| Alvo | Cobre |
|------|-------|
| `test_classify` | Reconhece domínio de funil; rejeita e-commerce; exclui `pt`; exclui plataforma BR; anúncio sem caption |
| `test_offers` | Agrupamento por chave composta; `days_live` de anúncio ativo e de encerrado; teto do log; portão dos 21 dias |
| `test_store` | Primeira rodada; merge de rodada nova; detecção de nova/sobreviveu/morreu |
| `test_render` | Nota gerada tem frontmatter válido, ranking ordenado, seção de mortas quando existe e quando não existe |

`meta_client` recebe só teste de montagem de URL e de parsing de paginação. O
resto dele é I/O e se verifica rodando.

## Pré-requisitos

1. **App de desenvolvedor na Meta com verificação de identidade.** Tem etapa
   humana e pode levar dias. Nenhuma linha de código adianta antes do token
   sair. É o primeiro passo, e ele é do dono, não do código
2. Python 3.9+ (a máquina tem 3.9.6)
3. `META_AD_LIBRARY_TOKEN` no ambiente ou no `.env` da raiz

Se a verificação travar, o plano B é antecipar o coletor do ClickBank, que não
exige credencial nenhuma.

## Riscos

| # | Risco | Severidade | Mitigação |
|---|-------|-----------|-----------|
| 1 | Verificação de identidade na Meta trava ou demora | Alta | Plano B: coletor ClickBank primeiro |
| 2 | Termos em inglês trazem pouco volume na UE continental | Média | Medir na primeira rodada; idiomas extras entram na v2 |
| 3 | Filtro de domínio deixa passar e-commerce e SaaS | Média | Lista de exclusão de plataformas de e-commerce; revisar o top 20 na mão nas primeiras rodadas |
| 4 | Cota de 200/h insuficiente conforme os termos crescem | Baixa | Cache do bruto e coleta resumível já resolvem; se apertar, dividir os termos entre dias |
| 5 | **Construir isto em vez de vender o [[Atendente IA]]** | **Alta** | Risco de projeto, não de código. O radar não gera receita — ele informa uma decisão futura. A meta de 13/09/2026 continua sendo abordagens, não código |

## Fora de escopo no v1

Cobertura dos EUA. Coletores de TikTok, ClickBank e Trends. Download e parsing
de landing page. Idiomas além do inglês. Execução agendada (cron entra depois de
o script rodar limpo na mão). Interface web. Alerta por WhatsApp.

---
**See also:** [[Radar Infoproduto]] | [[Atendente IA]] | [[Guilherme Figueredo]]
