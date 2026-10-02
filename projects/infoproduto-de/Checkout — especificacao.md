---
type: spec
subtype: checkout
name: "Checkout — especificação"
project: "[[Infoproduto DE]]"
owner: "[[Guilherme Figueredo]]"
date: 2026-08-15
tags:
  - project/infoproduto-de
---

# Checkout — especificação

## O que não se constrói

Página de pagamento não se escreve. Formulário de cartão no próprio site coloca
você dentro do escopo de **PCI-DSS**, que é auditoria de segurança de verdade.

O que se faz: cria o produto no painel do provedor, ele devolve um **checkout
hospedado**, e o botão da página de vendas aponta pra lá. Todo o código de
pagamento é deles.

## A regra que anula vendas: §312j Abs. 4 BGB

Na Alemanha, o botão que fecha o pedido tem exigência literal de texto. Se
estiver errado, **o contrato não se forma** — o cliente pagou e não existe venda
válida. Não é multa; é a venda inteira sendo nula, e ele pode exigir estorno.

Só conta o que está **escrito no botão**. Texto ao redor não corrige.

**Textos permitidos no botão:**

- `zahlungspflichtig bestellen` — o porto seguro, use este
- `kostenpflichtig bestellen`
- `kaufen`

**Textos que anulam a venda:**

- `Weiter`, `Absenden`, `Anmelden`, `Jetzt herunterladen`, `Download starten`
- `Bestellen` sozinho — é contestado, não vale o risco

> A página de vendas usa `Jetzt herunterladen` no botão. Ali é legal, porque
> aquele botão só leva ao checkout — não fecha pedido. A regra vale para o
> botão final, dentro do checkout.

## Pflichtangaben: o resumo obrigatório acima do botão

Imediatamente antes do botão, em destaque, tem que aparecer:

| Item | Texto para este produto |
|---|---|
| Produto | `Das Selbstversorger-Jahr — PDF, 11 Seiten, sofortiger Download` |
| Preço total | `37,00 €` |
| Aviso de imposto | `inkl. 19 % MwSt.` |
| Custo de entrega | `Keine Versandkosten (digitaler Download)` |
| Duração / renovação | `Einmalzahlung, kein Abo` |

O preço mostrado tem que ser o final. Alemão trata preço que cresce no último
passo como pegadinha, e a lei também.

## Widerrufsverzicht: a caixa que você não pode esquecer

Produto digital tem 14 dias de direito de arrependimento **por padrão**. Ele só
cai se o cliente consentir explicitamente na entrega imediata e reconhecer que
perde o direito. Sem essa caixa, qualquer comprador pode pedir estorno por 14
dias e você devolve, mesmo tendo entregue o PDF.

**Caixa de marcação obrigatória, não pré-marcada:**

```
☐ Ich verlange ausdrücklich, dass Sie vor Ablauf der Widerrufsfrist mit der
  Ausführung des Vertrags beginnen. Mir ist bekannt, dass ich mein
  Widerrufsrecht mit Beginn der Ausführung des Vertrags verliere.
```

Pré-marcar essa caixa invalida o consentimento. Ela tem que ser marcada pelo
cliente.

## Order bump

```
Titel:        Einkochen & Fermentieren — die Grundverfahren
Beschreibung: Zeiten- und Temperaturtabellen für 12 Kulturen, plus die
              2-Prozent-Lake als Druckvorlage.
Preis:        17,00 € (inkl. 19 % MwSt.)
```

## E-mail de confirmação

Obrigatório enviar confirmação do pedido. Tem que conter os dados do pedido, o
Impressum e a instrução de arrependimento (Widerrufsbelehrung).

```
Betreff: Ihre Bestellung: Das Selbstversorger-Jahr

Vielen Dank für Ihre Bestellung.

Bestellung:      Das Selbstversorger-Jahr (PDF)
Preis:           37,00 € inkl. 19 % MwSt.
Bestellnummer:   {{bestellnummer}}
Datum:           {{datum}}

Ihr Download:    {{download_link}}
Der Link bleibt 30 Tage gültig.

Sie haben beim Kauf ausdrücklich zugestimmt, dass die Ausführung sofort
beginnt, und bestätigt, dass Ihr Widerrufsrecht damit erlischt.

Bei Problemen mit dem Download antworten Sie einfach auf diese E-Mail.

{{impressum}}
```

## Escolha de provedor — o que muda

| | Stripe | Lemon Squeezy / Paddle | Digistore24 |
|---|---|---|---|
| Você é o vendedor | **Sim** | Não | Não |
| IVA europeu | **Seu problema** | Deles | Deles |
| Checkout pronto pra §312j | **Não** — botão padrão é "Jetzt bezahlen", que é discutível | Parcial | **Sim, é alemã** |
| Order bump nativo | Não | Sim | Sim |
| Afiliados alemães | Não | Não | **Sim** |
| Taxa | ~2,9% + €0,30 | ~5% + €0,50 | ~7% + taxa fixa |

**Recomendação:** Digistore24. É alemã, o checkout já nasce conforme o §312j,
ela é a vendedora legal (IVA resolvido), tem order bump nativo — e dá acesso a
afiliados alemães, que ataca o gargalo real, que é distribuição.

O Stripe é o mais barato em taxa e o mais caro em tudo o mais: você vira
contribuinte europeu, monta o checkout conforme por conta própria, e continua
sendo a única fonte de tráfego.

## Ordem de execução

1. Escolher o provedor
2. Criar o produto, subir o PDF, configurar preço e order bump
3. Ajustar o texto do botão para `zahlungspflichtig bestellen`
4. Ligar a caixa de Widerrufsverzicht
5. Colar o link do checkout no botão da página de vendas
6. Publicar Impressum, AGB, Widerrufsbelehrung e política de privacidade
7. Banner de consentimento antes de o pixel da Meta carregar
8. **Revisão por nativo alemão de tudo acima**
9. Comprar de si mesmo uma vez e conferir o fluxo inteiro

---
**See also:** [[Infoproduto DE]]
