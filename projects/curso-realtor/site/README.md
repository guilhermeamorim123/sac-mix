# Site — The 4-Hour Listing Week

Landing, checkout e entrega verificada. Projeto Vercel: `four-hour-listing-week`.

## Arquivos

| Arquivo | O que é |
|---|---|
| `index.html` | Landing em inglês |
| `success.html` | Página de obrigado; lê o `session_id` da URL |
| `api/download.js` | Verifica o pagamento no Stripe e entrega o PDF |
| `product.pdf` | O produto. **Fora de `/public` de propósito** |
| `vercel.json` | Manda o bundle da função incluir o `product.pdf` |

## Por que o PDF não tem URL pública

Ele fica fora de `/public`, então o único caminho até ele é a função — e o
único caminho pela função é um `session_id` que o Stripe confirma como pago.
Se o PDF estivesse em `/public`, a URL vazaria no primeiro fórum.

O link vale **72 horas**: tempo de o comprador voltar no dia seguinte, curto
o bastante para link compartilhado envelhecer.

## Passos para ir ao ar

### 1. O PDF entra no deploy

O deploy inicial foi feito sem ele (grande demais para a ferramenta). Conecte
o projeto do Vercel a um repositório git com esta pasta como *root directory*,
ou suba o arquivo pelo painel. Sem ele, a função responde
"file is temporarily unavailable".

### 2. Variável de ambiente

No painel do Vercel, em Settings → Environment Variables:

```
STRIPE_SECRET_KEY = sk_live_...
```

### 3. Produto e link de pagamento no Stripe

Criar o produto a US$ 47 e gerar um **Payment Link**. Na configuração do link,
em "After payment" → "Redirect customers to your website", colar:

```
https://SEUDOMINIO/success?session_id={CHECKOUT_SESSION_ID}
```

`{CHECKOUT_SESSION_ID}` é literal — o Stripe substitui pelo id real. **Se esse
trecho faltar, a página de obrigado não consegue liberar o download.**

### 4. Trocar os marcadores no `index.html`

- `STRIPE_PAYMENT_LINK` → a URL do Payment Link
- Adicionar o script do Meta Pixel no `<head>` das duas páginas
- Em `success.html`, disparar `Purchase` com valor 47 e moeda USD

### 5. Rodapé

Adicionar contato, termos e política de privacidade. O aviso legal já está
escrito — falta só o link das três páginas.

### 6. Produção

Promover o deploy de preview para produção, ou fazer um deploy novo com
`target: production`.

## Antes de gastar o primeiro dólar em anúncio

**Compre de você mesmo, uma vez, com cartão real.** Percorra o fluxo inteiro:
anúncio → landing → checkout → página de obrigado → download. É a única forma
de saber que o `session_id` está chegando e que a função está liberando.

Depois estorne pelo painel do Stripe.

## Ressalva de imposto

Rodando anúncio **só para os EUA**, imposto praticamente não existe: os limites
de nexus são US$ 100 mil ou 200 vendas por estado. Se entrar comprador europeu,
volta o IVA — e com Stripe o responsável é você, não a plataforma.

---
**See also:** [[Curso Realtor]]
