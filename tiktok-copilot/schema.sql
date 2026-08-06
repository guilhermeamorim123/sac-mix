-- Schema do Supabase para o TikTok AI Co-pilot.
-- Rode inteiro no SQL Editor do Supabase (uma vez).

-- ==========================================================================
-- 1. MENSAGENS DO CHAT  (pagina "Ao Vivo")
-- ==========================================================================
create table if not exists messages (
    message_id        text primary key,
    seller_id         text not null,
    live_id           uuid,
    user_id           text not null,
    username          text not null,
    nickname          text,
    text              text not null,
    intent            text,
    lead_score        int  not null default 0,
    suggested_reply   text,
    requires_human    boolean not null default true,
    product_mentioned text,
    whatsapp          text,
    replied_with      text,
    reply_source      text check (reply_source in ('auto', 'manual')),
    received_at       timestamptz not null default now()
);

create index if not exists idx_messages_seller_time on messages (seller_id, received_at desc);
create index if not exists idx_messages_hot on messages (seller_id, lead_score desc)
    where lead_score >= 7;

-- ==========================================================================
-- 2. LEADS  (CRM)
-- ==========================================================================
create table if not exists leads (
    seller_id      text not null,
    username       text not null,
    nickname       text,
    whatsapp       text,
    best_score     int  not null default 0,
    last_message   text,
    messages_count int  not null default 0,
    status         text not null default 'novo'
                   check (status in ('novo', 'contatado', 'negociando', 'vendido', 'perdido')),
    first_seen_at  timestamptz not null default now(),
    last_seen_at   timestamptz not null default now(),
    primary key (seller_id, username)
);

create index if not exists idx_leads_hot on leads (seller_id, best_score desc);
create index if not exists idx_leads_whats on leads (seller_id) where whatsapp is not null;

-- Consolida o lead numa operacao atomica. Guarda o MELHOR score historico, nao
-- o ultimo: quem disse "quero 2" e depois mandou um emoji segue sendo quente.
create or replace function upsert_lead(
    p_seller_id text, p_username text, p_nickname text,
    p_whatsapp text, p_score int, p_last_message text
) returns void language sql as $$
    insert into leads (seller_id, username, nickname, whatsapp, best_score,
                       last_message, messages_count, last_seen_at)
    values (p_seller_id, p_username, p_nickname, p_whatsapp, p_score,
            p_last_message, 1, now())
    on conflict (seller_id, username) do update set
        nickname       = excluded.nickname,
        whatsapp       = coalesce(excluded.whatsapp, leads.whatsapp),
        best_score     = greatest(leads.best_score, excluded.best_score),
        last_message   = excluded.last_message,
        messages_count = leads.messages_count + 1,
        last_seen_at   = now();
$$;

-- ==========================================================================
-- 3. COMANDOS  (painel -> agente local)
-- ==========================================================================
-- O painel roda no navegador e nao alcanca o Playwright. Entao ele enfileira
-- comandos aqui e o agente na maquina do vendedor faz polling.
create table if not exists commands (
    id         uuid primary key default gen_random_uuid(),
    seller_id  text not null,
    kind       text not null check (kind in ('send_reply', 'pause_auto',
                                             'resume_auto', 'supervisor_checkin')),
    payload    jsonb not null default '{}'::jsonb,
    status     text not null default 'pending' check (status in ('pending', 'done', 'failed')),
    created_at timestamptz not null default now(),
    done_at    timestamptz
);

create index if not exists idx_commands_pending on commands (seller_id, created_at)
    where status = 'pending';

-- ==========================================================================
-- 4. LIVES  (pagina "Lives Prontas")
-- ==========================================================================
create table if not exists lives (
    id             uuid primary key default gen_random_uuid(),
    seller_id      text not null,
    titulo         text not null,
    tipo           text not null default 'ao_vivo' check (tipo in ('ao_vivo', 'replay')),
    video_path     text,                      -- arquivo gravado, para reexibicao
    gravada_em     timestamptz not null default now(),
    duracao_min    int,

    -- metricas coletadas durante a transmissao
    viewers_pico   int default 0,
    viewers_media  int default 0,
    comentarios    int default 0,
    leads_captados int default 0,
    vendas         int default 0,
    receita        numeric(10,2) default 0,

    -- avaliacao (preenchida pelo agente ao encerrar)
    rating         text check (rating in ('boa', 'regular', 'ruim')),
    score          int,                       -- 0-100
    recomendacao   text,                      -- "vale rodar de novo porque..."
    replays        int not null default 0,
    ultimo_replay  timestamptz
);

create index if not exists idx_lives_seller on lives (seller_id, gravada_em desc);

-- Vendas por hora e a metrica que decide se a live vale replay: normaliza
-- lives de duracoes diferentes e e o que de fato paga a conta.
create or replace view lives_ranking as
select
    l.*,
    case when coalesce(l.duracao_min, 0) > 0
         then round((l.vendas::numeric * 60) / l.duracao_min, 2)
         else 0 end                                    as vendas_por_hora,
    case when l.comentarios > 0
         then round((l.leads_captados::numeric * 100) / l.comentarios, 1)
         else 0 end                                    as taxa_conversao_lead
from lives l;

-- ==========================================================================
-- 5. SESSAO DE REPLAY  (trava de supervisao)
-- ==========================================================================
-- Replay so pode rodar com alguem de plantao. Sem check-in recente, o agente
-- desliga a auto-resposta e para a reexibicao.
create table if not exists replay_supervisao (
    seller_id       text primary key,
    supervisor      text,
    presente        boolean not null default false,
    ultimo_checkin  timestamptz,
    -- o agente exige um check-in a cada N minutos
    intervalo_min   int not null default 15
);

-- ==========================================================================
-- 6. RLS  (multi-tenant para o SaaS)
-- ==========================================================================
alter table messages           enable row level security;
alter table leads              enable row level security;
alter table commands           enable row level security;
alter table lives              enable row level security;
alter table replay_supervisao  enable row level security;

-- Cada usuario so enxerga a propria loja. O seller_id vai no JWT como claim.
-- Ajuste se voce usar outra estrategia de tenancy.
create policy "tenant_isolation" on messages for all
    using (seller_id = auth.jwt() ->> 'seller_id');
create policy "tenant_isolation" on leads for all
    using (seller_id = auth.jwt() ->> 'seller_id');
create policy "tenant_isolation" on commands for all
    using (seller_id = auth.jwt() ->> 'seller_id');
create policy "tenant_isolation" on lives for all
    using (seller_id = auth.jwt() ->> 'seller_id');
create policy "tenant_isolation" on replay_supervisao for all
    using (seller_id = auth.jwt() ->> 'seller_id');

-- O agente local usa a service_role key, que ignora RLS por design.

-- ==========================================================================
-- 7. REALTIME  (o painel escuta estas tabelas)
-- ==========================================================================
alter publication supabase_realtime add table messages;
alter publication supabase_realtime add table leads;
alter publication supabase_realtime add table lives;
