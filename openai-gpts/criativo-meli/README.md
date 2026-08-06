---
type: agent-spec
platform: openai-gpt
---

# Criativo Meli

**Type:** OpenAI Custom GPT
**Category:** E-commerce / Product Photography
**Created:** 2026-06-17
**Owner:** Guilherme Figueredo / empresa da família

## Purpose

Criativo Meli generates 9 professional product images for Mercado Livre listings in a single session. The user uploads 3 product photos + a description + FAQs, and the GPT automatically generates all 9 image types using DALL-E — following ML's technical specs and a clean, modern visual style.

Built for a Brazilian family business (electronics, home decor, and more). Primary user: Maurício (gestor de anúncios).

## Features

- Automatic 9-image sequence from a single input set
- Product category auto-detection (electronics, home decor, clothing, supplements, etc.)
- Mercado Livre compliant: white background on cover, square format, no prohibited elements
- Selective regeneration — redo any single image on request
- Knowledge file with ML specs, style guide, and category-specific guidance
- Clean, modern, premium visual style across all 9 images
- Full Brazilian Portuguese interface

## Architecture

| Artifact | Purpose |
|----------|---------|
| `prompt.md` | System prompt — role, workflow, rules, edge cases (≤8000 chars) |
| `knowledge/ml-image-guide.md` | ML image specs, style guide, category notes |
| `config.md` | GPT settings, capabilities, conversation starters |

## Image Types Generated

| # | Type | Goal |
|---|------|------|
| 1 | Uso Real | Lifestyle — person using the product |
| 2 | Benefícios / Features | Feature callouts, infographic style |
| 3 | Hero Product | Premium floating shot, dramatic lighting |
| 4 | Selos / Certificações | Trust badges / certifications |
| 5 | Close / Textura | Macro detail of material or finish |
| 6 | Confiança / Garantia | 1-year warranty seal visual |
| 7 | Benefícios Visuais | Bold promotional, buy-incentive image |
| 8 | FAQ | Q&A card image from provided FAQs |
| 9 | Capa | White background cover (ML required) |

## Setup Guide

1. Go to **chatgpt.com → Explore GPTs → Create a GPT**
2. In the **Configure** tab:
   - **Name:** `Criativo Meli`
   - **Description:** paste from `config.md`
   - **Instructions:** paste full content of `prompt.md`
   - **Knowledge:** upload `knowledge/ml-image-guide.md`
   - **Capabilities:** enable **Image Generation (DALL-E)** only — disable Web Browsing and Code Interpreter
   - **Conversation Starters:** paste the 4 starters from `config.md`
3. Save → test with a real product

## Usage Flow

```
User provides:
  → 3 product photos (minimum 1)
  → Product description (name, category, features, audience)
  → FAQs (3+ pairs)

GPT outputs:
  → Imagem 1 — Uso Real
  → Imagem 2 — Benefícios / Features
  → Imagem 3 — Hero Product
  → Imagem 4 — Selos / Certificações
  → Imagem 5 — Close / Textura
  → Imagem 6 — Confiança / Garantia
  → Imagem 7 — Benefícios Visuais
  → Imagem 8 — FAQ
  → Imagem 9 — Capa
  → Summary with offer to regenerate any image
```

## Changelog

- 2026-06-17: Initial creation
- 2026-06-17: Prompt rewritten to match real editorial style — text overlays integrated in all images, lifestyle backgrounds, badges by image type, composite close-ups on image 3
