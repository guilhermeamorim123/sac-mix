# Capa ML — GPT Configuration

## Identity

| Field | Value |
|-------|-------|
| **Name** | Capa ML |
| **Description** | Gera 3 opções de capa profissional para anúncios no Mercado Livre. Cole o anúncio + mande as fotos — o agente recomenda os melhores estilos e gera as capas para você escolher. |
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

## Model Recommendation

Use **GPT-5.5** or **GPT-5.5 Pro** for best DALL-E image quality and instruction-following.

---

## Knowledge Files to Upload

| File | Purpose |
|------|---------|
| `knowledge/capa-style-guide.md` | Style execution guide — 4 visual styles with DALL-E prompt patterns, category recommendations, thumbnail rules |

---

## Conversation Starters

```
O que você consegue fazer por mim?
```
```
Aqui estão as fotos e o anúncio — gera as 3 opções de capa
```
```
Refaz a capa 2, quero algo mais escuro
```
```
Gera capas para este produto de decoração de casa...
```

---

## Setup Instructions (step by step)

1. Acesse **chatgpt.com** → clique em **Explore GPTs** → **Create a GPT**
2. Vá para a aba **Configure**
3. **Name:** `Capa ML`
4. **Description:** cole o campo Description acima
5. **Instructions:** cole o conteúdo completo de `prompt.md`
6. **Knowledge:** faça upload de `knowledge/capa-style-guide.md`
7. **Capabilities:**
   - Marque: `Image Generation`
   - Desmarque: `Web Browsing`, `Code Interpreter`, `Canvas`
8. **Model:** selecione GPT-5.5 ou GPT-5.5 Pro
9. **Conversation Starters:** adicione os 4 starters acima
10. **Save** → teste com um produto real

---

## Test Prompts

**Teste 1 — Fluxo completo:**
> Envie 1 foto de um aquecedor + cole o anúncio do Aquecedor AQ04 Mimo Style

Esperado: GPT analisa, recomenda Destaque Emocional + Ambiente Recortado + Recorte Dramático (nessa ordem para produto de aquecimento), aguarda confirmação, gera 3 capas uma por vez.

**Teste 2 — Troca de estilo antes de gerar:**
> Após a recomendação, responda: "Troca a capa 3 por Contraste Competitivo"

Esperado: GPT aceita a troca e confirma antes de gerar.

**Teste 3 — Regeneração seletiva:**
> Após as 3 capas: "Refaz a capa 1, quero o produto com ângulo mais frontal"

Esperado: GPT regera apenas a capa 1 mantendo o mesmo estilo.

**Teste 4 — Input incompleto:**
> Apenas: "Gera uma capa pra mim"

Esperado: GPT pede foto e anúncio antes de continuar.