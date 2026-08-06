---
type: agent-spec
platform: openai-gpt
---

# Nota 10 — Agente de Estudos para Vestibular

Agente de estudos personalizado para Guilherme, estudante de ensino médio/vestibular. Recebe PDFs, slides e texto colado, e transforma em resumos, questões de revisão e planos de estudo. Adapta o estilo de explicação por área: passo a passo para exatas, direto ao ponto para humanas.

## Features

- Processar conteúdo (PDF/texto) → resumo estruturado com fórmulas/conceitos-chave
- Questões de revisão em 3 níveis: Aquecimento / Nível prova / Desafio
- Modo Véspera de Prova — top 5 conceitos mais prováveis + macetes
- Plano de estudos semanal personalizado por matéria e data de prova
- Estilo adaptativo: exatas (passo a passo) vs humanas (bullets diretos)
- Método de recordação ativa — respostas reveladas sob demanda
- **Prova virtual** — GPT cria caderno de questões (múltipla escolha + dissertativa) e corrige com feedback
- **Modo Gabarito** — manda as questões da prova real e o GPT resolve todas
- **Trabalho escolar em PDF** — escreve trabalhos humanizados e exporta PDF formatado
- Tom de amigo que é bom de estudo — sem enrolação

## Architecture

| Artifact | Purpose |
|----------|---------|
| `prompt.md` | System prompt principal (≤8000 chars) |
| `knowledge/study-methodology.md` | Metodologia de questões, plano de estudos, técnicas de aprendizado |
| `config.md` | Capabilities, starters, settings |

## Knowledge File Plan

| File | Structure | Loading | Purpose |
|------|-----------|---------|---------|
| `knowledge/study-methodology.md` | Reference Guide | **Read before starting** | Metodologia de active recall, níveis de questão, construção de plano de estudos |

## Files

```
nota-10/
├── README.md
├── prompt.md
├── knowledge/
│   └── study-methodology.md
└── config.md
```

## Configuration Guide

1. Acesse [ChatGPT GPT Editor](https://chatgpt.com/gpts/editor)
2. Cole o conteúdo de `prompt.md` no campo **Instructions**
3. Faça upload de `knowledge/study-methodology.md` na seção **Knowledge**
4. Configure capabilities conforme `config.md`
5. Adicione os conversation starters de `config.md`
6. Salve e teste com os prompts de teste em `config.md`

## Changelog

- 2026-06-01: Initial creation
- 2026-06-01: Added Workflow 5 (Prova Virtual), Workflow 6 (Trabalho em PDF humanizado), Workflow 7 (Modo Gabarito); enabled Code Interpreter
