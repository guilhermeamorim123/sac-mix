# Grade de Provas — Guilherme 2026
Date: 2026-06-01
School: IPÊ Centro Educacional — Ensino Médio

> Use this file to track upcoming exams. When the user starts a conversation, proactively check if any exam is within 3 days and alert them.

## Regras do calendário escolar
- Provas P1 e P2: sempre às terças e quintas-feiras (1ª aula, tarde)
- Recuperação/Substitutiva: normalmente às segundas-feiras às 14h10
- Simulados ENEM: sábados (tarde)
- Simulado FUVEST (3ª série): durante a semana (manhã)

---

## 1º Trimestre — CONCLUÍDO

| Data | Matéria | Tipo |
|------|---------|------|
| 24/02 (Ter) | Matemática | P1 |
| 26/02 (Qui) | L. Inglesa | P1 |
| 03/03 (Ter) | Física | P1 |
| 05/03 (Qui) | Geografia | P1 |
| 06/03 (Sex) | Obra Literária 1 | Prova |
| 10/03 (Ter) | Química | P1 |
| 12/03 (Qui) | História | P1 |
| 17/03 (Ter) | L. Portuguesa | P1 |
| 19/03 (Qui) | Biologia | P1 |
| 24/03 (Ter) | Matemática | P2 |
| 26/03 (Qui) | L. Inglesa | P2 |
| 31/03 (Ter) | Fil./Soc. | Prova única |
| 02/04 (Qui) | Literatura | Prova única |
| 07/04 (Ter) | Física | P2 |
| 09/04 (Qui) | Geografia | P2 |
| 14/04 (Ter) | Química | P2 |
| 15/04 (Qua) | L. Portuguesa | P2 (6ª aula) |
| 16/04 (Qui) | História | P2 |
| 23/04 (Qui) | Biologia | P2 |

---

## 2º Trimestre — EM ANDAMENTO

| Data | Matéria | Tipo | Status |
|------|---------|------|--------|
| 05/05 (Ter) | Matemática | P1 | ✅ Feita |
| 07/05 (Qui) | L. Inglesa | P1 | ✅ Feita |
| 12/05 (Ter) | Física | P1 | ✅ Feita |
| 14/05 (Qui) | Geografia | P1 | ✅ Feita |
| 19/05 (Ter) | Química | P1 | ✅ Feita |
| 21/05 (Qui) | História | P1 | ✅ Feita |
| 26/05 (Ter) | L. Portuguesa | P1 | ✅ Feita |
| 28/05 (Qui) | Biologia | P1 | ✅ Feita |
| **02/06 (Ter)** | **Matemática** | **P2** | **⚠️ AMANHÃ** |
| 11/06 (Qui) | L. Inglesa | P2 | 🔜 Em 10 dias |
| 16/06 (Ter) | Física | P2 | 🔜 Em 15 dias |
| 18/06 (Qui) | Geografia | P2 | 🔜 Em 17 dias |
| 23/06 (Ter) | Química | P2 | 🔜 Em 22 dias |
| 25/06 (Qui) | História | P2 | 🔜 Em 24 dias |

---

## 3º Trimestre — (Após férias de julho)

| Data | Matéria | Tipo |
|------|---------|------|
| 08/09 (Ter) | Matemática | P1 |
| 10/09 (Qui) | L. Inglesa | P1 |
| 15/09 (Ter) | Química | P1 |
| 17/09 (Qui) | Geografia | P1 |
| 22/09 (Ter) | Física | P1 |
| 24/09 (Qui) | História | P1 |
| 06/10 (Ter) | L. Portuguesa | P1 |
| 08/10 (Qui) | Biologia | P1 |
| 20/10 (Ter) | L. Inglesa | P2 |
| 22/10 (Qui) | História | P2 |
| 27/10 (Ter) | Química | P2 |
| 29/10 (Qui) | Literatura | Prova única |
| 03/11 (Ter) | Física | P2 |
| 05/11 (Qui) | Fil./Soc. | Prova única |
| 10/11 (Ter) | L. Portuguesa | P2 |
| 12/11 (Qui) | Geografia | P2 |
| 17/11 (Ter) | Matemática | P2 |
| 24/11 (Ter) | Biologia | P2 (3ª série) |
| 26/11 (Qui) | Biologia | P2 (1ª e 2ª séries) |

---

## Simulados ENEM 2026

| Data | Evento |
|------|--------|
| 14/03 (Sáb) | 1º ENEM Simulado D1 (1ª e 2ª séries) |
| 21/03 (Sáb) | 1º ENEM Simulado D2 (1ª/2ª) + D1 (3ª) |
| 28/03 (Sex) | 1º ENEM Simulado D2 (3ª) |
| 16/05 (Sex) | 2º ENEM Simulado D1 (1ª e 2ª séries) |
| 23/05 (Sex) | 2º ENEM Simulado D2 (1ª/2ª) + D1 (3ª) |
| 30/05 (Sáb) | 2º ENEM Simulado D2 (3ª) |
| 19/09 (Sex) | 3º ENEM Simulado D1 (todas as séries) |
| 26/09 (Sex) | 3º ENEM Simulado D2 (todas as séries) |

---

## Instruções para o agente

Quando o usuário iniciar uma conversa:
1. Verifique se alguma prova está a 3 dias ou menos (use a data de hoje)
2. Se sim, alerte: "⚠️ Atenção: sua prova de [Matéria] é em [N] dia(s). Quer que eu monte o pacote de revisão?"
3. Se a prova for amanhã: entre automaticamente no Modo Véspera de Prova assim que o usuário enviar qualquer conteúdo
