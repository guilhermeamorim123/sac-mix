---
name: cos-mensagem-mae
description: Use when sending the daily love message to Guilherme's mom via WhatsApp. Triggered automatically every day at 16:49.
---

# cos-mensagem-mae

Envia uma mensagem curta e carinhosa para a mãe do Guilherme via WhatsApp.

## Número

**5511959528327** (mãe do Guilherme)

## Processo

1. Pegue o dia atual (dia do mês) e use como índice para escolher a mensagem da lista abaixo: `índice = (dia_do_mes - 1) % 10`
2. Envie via `mcp__whatsapp__send_message` para o número `5511959528327`
3. Confirme o envio

## Mensagens

```
0 → "Te amo mãe ❤️"
1 → "Pensando em você hoje. Te amo demais."
2 → "Saudade de você mãe. Te amo muito."
3 → "Você é a melhor mãe do mundo. Te amo."
4 → "Mãe, te amo muito. Só vim te dar um oi."
5 → "Obrigado por tudo mãe. Te amo."
6 → "Mãe, tô com saudade. Te amo."
7 → "Você é incrível mãe. Te amo muito."
8 → "Só pra te lembrar que te amo muito, mãe."
9 → "Mãe, você sabia que te amo demais? Pois é."
```

## Regras

- **NUNCA enviar mais de uma mensagem por dia**
- Não pedir aprovação — esta skill é disparada automaticamente pelo agendamento
- Se o MCP whatsapp falhar, registrar o erro e encerrar sem retentar
