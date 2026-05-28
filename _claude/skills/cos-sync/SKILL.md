---
name: cos-sync
description: Sincroniza repositorio local com remote (pull, commit all, push)
user-invocable: false
argument-hint: [commit message]
allowed-tools: Bash, Glob
---

> **ARCHIVED (2026-03-18):** Vault now uses Obsidian Sync. This skill is kept for reference/reuse in other vaults.

Sincronizar o repositorio git local com o remote.

Execute os passos abaixo **sequencialmente**, parando imediatamente se qualquer passo falhar.

## Step 1 — Check Status

```bash
git status --porcelain
git status --short --branch
```

- Se working directory limpo E nao tem commits ahead do remote → responda "Nada para sincronizar. Repositorio ja esta atualizado." → PARE.

## Step 2 — Pull Remote (safe rebase)

Se existem mudancas locais nao commitadas (output do `git status --porcelain` nao vazio):

```bash
git stash push -m "sync-auto-stash"
```

Entao:

```bash
git pull --rebase origin main
```

Se o pull falhar com conflitos:
- Rode `git rebase --abort`
- Se fez stash, rode `git stash pop`
- Informe o usuario: "Conflito ao fazer pull. Resolva manualmente e tente novamente."
- PARE.

Se fez stash, restaure:

```bash
git stash pop
```

Se o stash pop tiver conflitos:
- Informe o usuario: "Conflito ao restaurar mudancas locais. Resolva manualmente."
- PARE.

## Step 3 — Stage & Commit

```bash
git add -A
```

Verifique se ha algo para commitar:

```bash
git diff --cached --stat
```

Se nao ha nada staged (output vazio), pule para Step 4.

### Commit message

- Se `$ARGUMENTS` foi fornecido e nao esta vazio → use como commit message
- Se nao → gere uma mensagem descritiva baseada nos arquivos alterados. Formato:
  - Analise os arquivos mudados e crie uma mensagem curta e descritiva em ingles
  - Exemplos: "Update tasks and process weekly 2026-02-23", "Add team member profiles", "Update context files"

```bash
git commit -m "<message>"
```

## Step 4 — Push

```bash
git push origin main
```

Se o push falhar → informe o usuario com o erro exato. PARE.

## Step 5 — Confirm

Mostre um resumo compacto:

```
Sync completo!
- Arquivos alterados: <N>
- Commit: <hash curto> — <mensagem>
- Branch: main (up to date with origin/main)
```
