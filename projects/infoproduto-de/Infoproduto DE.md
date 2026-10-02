---
type: project
name: "Infoproduto DE"
status: "em andamento"
owner: "[[Guilherme Figueredo]]"
started: 2026-08-15
tags:
  - project/infoproduto-de
  - project/active
---

# Infoproduto DE — Das Selbstversorger-Jahr

## Description

Infoproduto próprio em alemão, vendido para o mercado alemão com tráfego pago
no Meta. A estratégia é **arbitragem de geografia**: pegar um formato já
validado nos EUA e ser cedo com ele num mercado que ainda não o tem.

O formato copiado é o de guia de autossuficiência — os equivalentes americanos
(*The Self-Sufficient Backyard*, *No Grid Survival Projects*) estão no topo da
Digistore24. O que **não** foi copiado é o enquadramento: a versão americana é
prepper e sobrevivencialista; esta é ancorada em **Schrebergarten**, que é
cultura nativa alemã.

**Produto:** guia de 12 meses para colher o ano inteiro em 40 m².
**Preço:** €37, com order bump de €17 (Einkochen & Fermentieren).

## Key Decisions

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| 1 | 2026-08-15 | Produto próprio, não afiliado | Guilherme quer preço e campanha dele; com produto próprio fica com 100% da venda |
| 2 | 2026-08-15 | Alemanha, não Portugal | Escolha do dono. Maior economia da UE, maior poder de compra, e **não está** na lista de taxa de localização da Meta (que atinge UK, França, Itália, Espanha, Áustria e Turquia) |
| 3 | 2026-08-15 | Nicho de autossuficiência | Formato provado nos EUA, promessa modesta, sem alegação de saúde ou dinheiro — passa na política de Unrealistic Outcomes da Meta, ao contrário do nicho de "áudio da mente" |
| 4 | 2026-08-15 | Registro sóbrio, não hype | Copy de resposta direta americana performa mal na Alemanha; o registro que vende ali é técnico e com prova |
| 5 | 2026-08-15 | Nenhum depoimento inventado | Depoimento falso é infração do UWG na Alemanha e abmahnfähig. Os blocos ficam vazios até existir prova real |

## Estado

| Peça | Estado |
|---|---|
| Página de vendas (alemão) | Feita — `fonte/pagina-de-vendas.html`, publicada como artifact |
| E-book PDF (alemão, 11 páginas) | Feito — `Das-Selbstversorger-Jahr.pdf` |
| Revisão por nativo alemão | **Pendente — bloqueia gastar em tráfego** |
| Checkout | Indefinido: Stripe (IVA é seu) vs Lemon Squeezy / Digistore24 (IVA é deles) |
| Impressum, AGB, Widerruf, privacidade | Pendente — obrigatório na Alemanha |
| Banner de consentimento (GDPR) | Pendente — sem ele o pixel degrada e a operação fica irregular |

## Current Risks & Blockers

| # | Risk/Blocker | Severity | Status |
|---|-------------|----------|--------|
| 1 | **Guilherme não fala alemão** — não consegue avaliar a copy, ler comentários do anúncio, fazer suporte nem responder reembolso | **Alta** | Open — mitigação obrigatória: revisão nativa paga antes do primeiro euro em tráfego |
| 2 | Sem Impressum a operação é abmahnfähig — é o motivo nº 1 de advertência na Alemanha | Alta | Open |
| 3 | IVA europeu devido desde a primeira venda se usar Stripe (vendedor de fora da UE não tem piso) | Média | Open — resolve trocando por merchant of record |
| 4 | **Distribuição, de novo** — é o mesmo gargalo do [[Atendente IA]] e de todos os outros produtos do vault | **Alta** | Open — Digistore24 daria acesso a afiliados alemães, ao custo de 60–70% de comissão |
| 5 | Conteúdo de jardinagem não revisado por especialista local | Média | Open — os dados são práticas correntes alemãs, mas ninguém do ramo conferiu |

## Notes

O capítulo 7 tem um aviso de segurança sobre **botulismo** que foi decisão
deliberada: conserva de legume pouco ácido em banho-maria é risco real, e o
guia manda fermentar, congelar ou usar panela de pressão em vez disso. Além de
ser o certo, esse tipo de rigor é o que dá credibilidade no mercado alemão.

Este projeto nasceu no mesmo dia em que o [[Radar Infoproduto]] foi mergeado,
e é uma quinta direção em dois dias. O [[Atendente IA]] segue sendo a operação
de receita com prazo em 13/09/2026.

---
**See also:** [[Radar Infoproduto]] | [[Atendente IA]] | [[Guilherme Figueredo]]
