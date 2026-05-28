---
type: company
name: "{{NAME}}"
aliases:
  - {{ALIAS}}
status: active
tags:
  - company/partner
---

# {{NAME}}

> **Setor:** {{SECTOR}} | **Relação:** {{RELATIONSHIP}}

---

## Contexto

<!-- Informações sobre a empresa, natureza da parceria, produtos/serviços relevantes. -->

---

## Contatos Conhecidos

<!-- Pessoas desta empresa mencionadas em reuniões. Claude atualiza proativamente. -->

---

## Histórico de Interações

```dataview
TABLE date AS "Data", subtype AS "Tipo"
FROM #meeting
WHERE contains(file.outlinks, this.file.link)
SORT date DESC
LIMIT 10
```

---
**See also:** [[people]]
