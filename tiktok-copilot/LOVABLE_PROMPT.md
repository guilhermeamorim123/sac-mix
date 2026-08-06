# Prompt para o Lovable

Cole o bloco abaixo no Lovable. Antes disso, conecte o projeto ao Supabase
(botão de integração do Lovable) e rode o `schema.sql` no SQL Editor — assim o
Lovable já enxerga as tabelas e gera os hooks certos.

Depois de gerar, peça ajustes em iterações curtas ("deixa o card de lead
quente mais destacado", "muda o gráfico pra barras"). O Lovable responde melhor
a pedidos incrementais do que a um refactor gigante.

---

## PROMPT (copiar daqui para baixo)

Construa um painel web para vendedores de live commerce no TikTok. Ele fica
aberto num segundo monitor enquanto a pessoa transmite, então precisa ser
legível de longe: fontes grandes, alto contraste, informação densa mas não
apertada. Tema escuro por padrão.

Backend: Supabase (já conectado). Todos os dados vêm de lá; **não crie dados
mockados fora do modo de demonstração**. Use Supabase Realtime para as tabelas
`messages`, `leads` e `lives` — a tela precisa atualizar sozinha, sem refresh.

Stack: React + Vite + TypeScript + Tailwind + shadcn/ui. Recharts para gráficos.

### Navegação

Duas páginas, com uma barra lateral fixa e estreita alternando entre elas:

1. **Ao Vivo** (rota `/`)
2. **Lives Prontas** (rota `/lives`)

No topo da barra lateral: nome da loja, um indicador redondo de status
(verde "no ar" / cinza "offline") e um contador de espectadores.

---

### PÁGINA 1 — "Ao Vivo"

Layout de três colunas em telas grandes; empilhado no mobile.

**Coluna esquerda — Chat ao vivo (~30% da largura)**

Lista das linhas de `messages`, ordenada por `received_at` desc, rolagem
automática para o topo quando chega mensagem nova (com um botão "pausar
rolagem" que aparece se o usuário rolar para baixo manualmente).

Cada linha mostra: avatar circular com a inicial do `nickname`, o `nickname`,
o `text`, e uma etiqueta pequena com o `intent`. Colora a borda esquerda da
linha pelo `lead_score`: 0–2 cinza, 3–6 azul, 7–8 âmbar, 9–10 vermelho.

Se `whatsapp` não for nulo, mostre um ícone de telefone ao lado do nome.

**Coluna central — Fila de resposta (~40%)**

O núcleo do produto. Mostra as mensagens que ainda não têm `replied_with`,
priorizadas por `lead_score` desc (não por horário — o que importa é quem está
mais perto de comprar).

Cada item é um card com:
- a pergunta original, em texto menor e opaco;
- a `suggested_reply` em destaque, fonte grande, é o que a pessoa vai ler no ar;
- um selo "PRECISA DE VOCÊ" em âmbar quando `requires_human` for true;
- três botões: **Enviar** (insere uma linha em `commands` com
  `kind='send_reply'` e `payload={text, message_id}`), **Copiar** (clipboard) e
  **Editar** (abre um campo de texto inline para ajustar antes de enviar).

Acima da fila, uma barra de controle com:
- um switch grande **Auto-resposta** que insere em `commands` um
  `kind='pause_auto'` ou `'resume_auto'`;
- ao lado dele, em texto pequeno: "respondendo automaticamente só preço, frete,
  prazo e como comprar";
- um botão vermelho **PARAR TUDO**, sempre visível.

**Coluna direita — Leads e coaching (~30%)**

Três blocos empilhados:

1. **Leads quentes** — linhas de `leads` com `best_score >= 7`, ordenadas por
   `best_score` desc. Cada card: nickname, score num badge, o `last_message`,
   e o WhatsApp com botão de copiar quando existir. Um seletor de `status`
   (novo / contatado / negociando / vendido / perdido) que grava direto na
   tabela.

2. **Números da live** — quatro contadores grandes: comentários, leads quentes,
   WhatsApps capturados, respostas automáticas enviadas. Cada um com uma
   sparkline dos últimos 10 minutos.

3. **Coaching** — um card que mostra dicas contextuais. Regras, calculadas no
   frontend a partir dos dados dos últimos 3 minutos:
   - Se nenhuma mensagem chegou há mais de 90s: "Chat parado — faça uma
     pergunta pra plateia ou mostre outro produto."
   - Se mais de 5 mensagens têm o mesmo `product_mentioned`: "Muita gente
     perguntando sobre {produto}. Mostra ele agora."
   - Se há 3+ leads com score >= 8 sem resposta: "{n} pessoas prontas pra
     comprar esperando. Responde elas primeiro."
   - Se `intent='preco'` passou de 40% das mensagens: "O preço não está claro.
     Fala ele em voz alta e põe na tela."

---

### PÁGINA 2 — "Lives Prontas"

Biblioteca das lives já gravadas, para decidir qual reexibir. Lê da view
`lives_ranking`.

**Topo — faixa de supervisão.** Uma barra larga, impossível de ignorar, lendo
`replay_supervisao`. Quando `presente` for false ou o `ultimo_checkin` tiver
mais de `intervalo_min` minutos, ela fica **vermelha** e diz: "Nenhum supervisor
de plantão — a reexibição está travada." Com um botão **Assumir plantão** que
pede o nome e insere em `commands` um `kind='supervisor_checkin'`. Quando
alguém está de plantão, a faixa fica verde, mostra o nome e um cronômetro
regressivo até o próximo check-in obrigatório.

**Grade de cards**, um por live, ordenados por `score` desc. Cada card:

- título e data da gravação;
- duração em formato `1h 15min`;
- uma **tarja de rating** bem visível no topo do card:
  verde `BOA`, âmbar `REGULAR`, vermelho `RUIM`;
- o `score` como um anel de progresso de 0 a 100;
- quatro números lado a lado: vendas, receita, comentários, leads;
- `vendas_por_hora` em destaque, rotulado "vendas/hora" — é a métrica que
  decide se vale reexibir;
- o texto de `recomendacao` num bloco citado;
- rodapé com "reexibida {replays}x" e a data do último replay;
- botão **Reexibir esta live**, que fica **desabilitado com tooltip
  explicativo** enquanto não houver supervisor de plantão.

**Filtros** no topo da grade: por rating, por período, e uma ordenação
alternando entre score, vendas/hora e data.

**Painel de comparação**: acima da grade, um gráfico de barras (Recharts)
comparando `vendas_por_hora` de todas as lives, com uma linha horizontal
tracejada marcando a média. Deixa óbvio quais estão acima e abaixo do padrão.

---

### Detalhes que importam

- Estados vazios com texto útil, não só "sem dados": explique o que fazer para
  aparecer algo ali.
- Toda ação que escreve em `commands` mostra um toast de confirmação e um
  estado de carregamento — a pessoa precisa saber que o comando saiu.
- Formate valores em pt-BR: `R$ 1.234,56`, datas `dd/mm/aaaa`.
- Responsivo de verdade: no celular as três colunas viram abas.
- Acessibilidade: contraste AA, foco visível, os botões de ação alcançáveis por
  teclado.
