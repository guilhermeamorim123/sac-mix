---
type: agent-spec
platform: openai-gpt
---

# Capa ML

**Type:** OpenAI Custom GPT
**Category:** E-commerce / Product Photography
**Created:** 2026-06-22
**Owner:** Guilherme Figueredo / empresa da família

## Purpose

Capa ML generates 3 professional cover image options per ML listing session. The user pastes the listing text + uploads product photos. The agent analyzes the product, recommends the 3 best visual styles with justification, and generates them one at a time for Maurício to choose from.

Built as a companion to Criativo Meli (which handles the 7 gallery images). This agent is dedicated exclusively to position-1 cover images — no text, visual-first, optimized for thumbnail legibility at 60×60px.

Primary user: Maurício (gestor de anúncios). Products: electronics, home appliances, home decor, and more.

## Features

- Product analysis: extracts category, positioning, and benefit from the listing
- Style recommendation: picks the 3 best styles from a 4-style pool based on the product
- Style pool: Recorte Dramático, Ambiente Recortado, Destaque Emocional, Contraste Competitivo
- Generates 3 cover options one at a time (user triggers each with "próxima")
- Selective regeneration — redo any single cover on request
- Thumbnail legibility built into every generation (works at 60×60px)
- ML policy compliant: no text, no watermarks, no prohibited elements
- Full Brazilian Portuguese interface

## Architecture

| Artifact | Purpose |
|----------|---------|
| `prompt.md` | System prompt — role, workflow, style pool, rules (≤8000 chars) |
| `knowledge/capa-style-guide.md` | Visual execution guide per style — DALL-E patterns, category matrix, thumbnail rules |
| `config.md` | GPT settings, capabilities, conversation starters, test prompts |

## Style Pool

| Style | Visual Concept | Best For |
|-------|---------------|----------|
| Recorte Dramático | 3/4 angle, accent color bg, dramatic lighting | Electronics, tech |
| Ambiente Recortado | White bg + 1 minimal contextual prop | Appliances, decor |
| Destaque Emocional | Benefit visual top 60%, product bottom 40% | Comfort, seasonal |
| Contraste Competitivo | Deliberate visual contrast vs. category norm | Crowded categories |

## Usage Flow

```
User provides:
  → ML listing text (pasted)
  → Product photos (at least 1 upload)

GPT outputs:
  → Product analysis + 3 style recommendations with justification
  → Awaits confirmation

On confirmation:
  → Capa 1 — [Style Name]
  → "próxima" →
  → Capa 2 — [Style Name]
  → "próxima" →
  → Capa 3 — [Style Name]
  → Summary + offer to regenerate any cover
```

## Relationship to Criativo Meli

| Agent | Purpose | Images |
|-------|---------|--------|
| Capa ML | Cover image (position 1) | 3 options to choose from |
| Criativo Meli | Gallery images (positions 2-8) | 7 editorial images with text overlays |

Typical workflow: run Capa ML first → choose the cover → run Criativo Meli for the gallery.

## Changelog

- 2026-06-22: Initial creation — 4-style pool, 3-option flow, thumbnail legibility focus
