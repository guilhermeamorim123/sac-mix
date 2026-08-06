# Criativo Meli — GPT Configuration

## Identity

| Field | Value |
|-------|-------|
| **Name** | Criativo Meli |
| **Description** | Gera 9 imagens profissionais de anúncio para Mercado Livre em uma sessão. Mande as fotos, descrição e FAQs do produto. |
| **Language** | Portuguese (Brazil) |

---

## Capabilities

| Capability | Setting |
|-----------|---------|
| Image Generation (DALL-E) | **ON** — required |
| Vision (image analysis) | **ON** — required (to analyze product photos) |
| Web Browsing | **OFF** |
| Code Interpreter | **OFF** |
| Canvas | **OFF** |

---

## Knowledge Files to Upload

| File | Purpose |
|------|---------|
| `knowledge/ml-image-guide.md` | ML technical specs, prohibited elements, style guide, category guidance |

---

## Conversation Starters

```
O que você consegue fazer por mim?
```
```
Aqui estão as fotos e a descrição — gera as 9 imagens do anúncio
```
```
Refaz a imagem 3, quero o fundo mais escuro
```
```
Cria as imagens para este produto de decoração...
```

---

## Setup Instructions (step by step)

1. Acesse **chatgpt.com** → clique em **Explore GPTs** → **Create a GPT**
2. Vá para a aba **Configure**
3. **Name:** `Criativo Meli`
4. **Description:** cole o campo Description acima
5. **Instructions:** cole o conteúdo completo de `prompt.md`
6. **Knowledge:** faça upload do arquivo `knowledge/ml-image-guide.md`
7. **Capabilities:**
   - Marque: `Image Generation`
   - Desmarque: `Web Browsing`, `Code Interpreter`, `Canvas`
8. **Conversation Starters:** adicione os 4 starters acima
9. **Save** → teste com um produto real

---

## Test Prompts

Use estes prompts para validar o GPT após criação:

**Teste 1 — Fluxo completo:**
> Envie 1 foto de um produto qualquer + "Produto: Fone de ouvido Bluetooth sem fio. Features: 30h de bateria, cancelamento de ruído, resistente à água IPX5. Público: jovens 18-35. FAQ: 1. Funciona com iPhone? Sim. 2. Tem garantia? 1 ano. 3. Carrega rápido? Sim, 2h de carga."

Esperado: GPT analisa, confirma o produto, gera imagens 1 a 9 em sequência.

**Teste 2 — Regeneração seletiva:**
> "Refaz a imagem 5, quero ver o detalhe do botão de liga/desliga"

Esperado: GPT regera apenas a imagem 5 mantendo o mesmo produto.

**Teste 3 — Input incompleto:**
> Apenas: "Gera as imagens do meu produto"

Esperado: GPT pede foto e descrição antes de continuar.