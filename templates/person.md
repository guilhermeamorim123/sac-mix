---
type: person
name: "{{NAME}}"
role: "{{ROLE}}"
email: "{{EMAIL}}"
sector: "{{SECTOR}}"
company: "{{COMPANY}}"
clickup_id: {{CLICKUP_ID}}
slack_id: "{{SLACK_ID}}"
status: active
first_seen: "{{FIRST_SEEN}}"
aliases:
  - {{ALIAS}}
tags: []
---

# {{NAME}}

> **Cargo:** {{ROLE}} | **Setor:** {{SECTOR}}

---

## Notas

<!-- Contexto acumulado de reuniões e interações. Claude atualiza proativamente. -->

---

## Menções Recentes

```dataview
TABLE date AS "Data", subtype AS "Tipo"
FROM #meeting
WHERE contains(file.outlinks, this.file.link)
SORT date DESC
LIMIT 5
```

---
**See also:** [[people]]
