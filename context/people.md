---
type: context
---

# People Directory

> Pessoas mencionadas em reuniões. Perfis em `team/<member>/` (diretos) e `people/` (demais).

## Meu Time (diretos)
```dataview
TABLE role AS "Cargo", email AS "Email"
FROM "team"
WHERE type = "person"
SORT name ASC
```

## Outros
```dataview
TABLE role AS "Cargo", company AS "Empresa"
FROM "people"
WHERE type = "person"
SORT name ASC
```

---
**See also:** [[team]]
