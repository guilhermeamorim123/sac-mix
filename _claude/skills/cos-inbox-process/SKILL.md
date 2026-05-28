---
name: cos-inbox-process
description: Processa itens da pasta +Inbox/ e distribui para os locais corretos do vault
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

Processar todos os itens na pasta `+Inbox/` e distribuir para os locais corretos do vault.

> Read `context/cos-config.md` for `language` and `owner` before processing.

## Execution

1. **List** all files in `+Inbox/` (exclude `.gitkeep` and `.processing-lock`)
2. If inbox is empty → exit silently (no message needed)
3. **Surface monitor errors**: If any `monitor-error-*.md` files exist, present them as alerts: "⚠️ O monitor autônomo registrou X erro(s). Detalhes:" then show each error summary. Ask o gestor if they want to address them or dismiss. Remove dismissed error files
4. **Note auto-monitor pendings**: If `context/pendings.md` has items tagged `[auto-monitor]`, mention: "O monitor autônomo identificou X itens pra sua revisão no pendings.md — itens com [decisão?] precisam da sua confirmação"
5. For each remaining item, process based on type:

### Markdown files (.md)
- Read content and analyze
- Determine destination:
  - Person info → create/update in `people/` or `team/`
  - Project idea/update → create/update in `projects/`
  - Decision/strategy → append to `context/decisions.md` or relevant context file
  - Meeting-related → move to appropriate `meetings/` folder
  - General note → ask o gestor where it belongs
- Apply proper frontmatter and wikilinks when creating vault files
- Delete from inbox after processing

### Images/screenshots (.png, .jpg, .jpeg, .gif, .webp)
- Ask o gestor: "Encontrei [filename] no inbox. O que é? Pra qual projeto/contexto?"
- Move to relevant folder based on the answer
- Delete from inbox after moving

### Audio files (.m4a, .mp3, .wav, .ogg)
- Ask o gestor which meeting type it is, then suggest invoking the appropriate `/cos-process-*` workflow with the inbox file path
- Leave in inbox until the workflow moves it to the correct meeting folder

### Other files (.pdf, .txt, .csv, etc.)
- Ask o gestor for context
- Move to relevant location
- Delete from inbox after moving

## After Processing

Report: "Inbox processado: X itens distribuídos, Y aguardando input, Z mantidos (audio)."

## Rules

- **Never auto-process audio** — those need transcription workflows
- Items that can't be auto-classified → ask o gestor
- Processed items are DELETED from inbox (info already in vault)
- New files created from inbox items follow templates and conventions
