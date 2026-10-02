-- Schema do banco do Livewire (Postgres/Supabase).
-- Rode inteiro no SQL Editor, uma vez, num projeto novo.
--
-- Este arquivo foi regerado a partir do banco em producao do painel
-- (Lovable Cloud / Supabase) em 06/08/2026 -- ele e o espelho do que esta la,
-- nao um rascunho. Se voce mudar o banco pelo painel, regere este arquivo.
--
-- Duas coisas para saber antes de ler:
--
-- 1. Tudo e multi-tenant por `seller_id`. O painel so enxerga as lojas as quais
--    o usuario logado esta vinculado em `seller_users` (funcao `tem_acesso`).
-- 2. O agente local usa a chave service_role, que ignora RLS por design.

-- ==========================================================================
-- 1. LOJAS E ACESSO
-- ==========================================================================
create table if not exists sellers (
    id              text primary key,          -- ex: 'mix-conecta'
    nome            text not null,
    tiktok_username text,
    plano           text not null default 'trial'
                    check (plano in ('trial', 'ativo', 'suspenso')),
    criado_em       timestamptz not null default now()
);

create table if not exists seller_users (
    seller_id  text not null references sellers(id) on delete cascade,
    user_id    uuid not null references auth.users(id) on delete cascade,
    papel      text not null default 'dono'
               check (papel in ('dono', 'operador', 'supervisor')),
    criado_em  timestamptz not null default now(),
    primary key (seller_id, user_id)
);

create index if not exists idx_seller_users_user on seller_users (user_id);

-- SECURITY DEFINER de proposito: as policies chamam esta funcao, e ela precisa
-- ler `seller_users` sem cair na propria policy (recursao infinita).
create or replace function tem_acesso(p_seller_id text)
returns boolean language sql stable security definer set search_path to 'public' as $$
    select exists (
        select 1 from seller_users
         where seller_id = p_seller_id and user_id = auth.uid()
    );
$$;

-- ==========================================================================
-- 2. CATALOGO E PREFERENCIAS  (editados pelo painel, lidos pelo agente)
-- ==========================================================================
-- O que esta aqui vira o system prompt da IA. Preco errado nesta tabela e
-- preco errado dito no ar.
create table if not exists produtos (
    id            uuid primary key default gen_random_uuid(),
    seller_id     text not null references sellers(id) on delete cascade,
    nome          text not null,
    preco         numeric(10,2),
    estoque       int,
    cores         text[] default '{}',
    tamanhos      text[] default '{}',
    obs           text,
    ativo         boolean not null default true,
    ordem         int not null default 0,
    atualizado_em timestamptz not null default now()
);

create index if not exists idx_produtos_seller on produtos (seller_id, ordem);

create table if not exists frete_regras (
    id        uuid primary key default gen_random_uuid(),
    seller_id text not null references sellers(id) on delete cascade,
    regiao    text not null,             -- 'Sudeste', 'Gratis', 'Pagamento'...
    descricao text not null,             -- 'R$ 14,90 - 3 a 5 dias uteis'
    ordem     int not null default 0
);

create index if not exists idx_frete_seller on frete_regras (seller_id, ordem);

-- Politicas da loja que a IA pode citar: troca, garantia, retirada, etc.
create table if not exists base_conhecimento (
    id            uuid primary key default gen_random_uuid(),
    seller_id     text not null references sellers(id) on delete cascade,
    titulo        text not null,
    conteudo      text not null,
    ativo         boolean not null default true,
    ordem         int not null default 0,
    atualizado_em timestamptz not null default now()
);

create index if not exists idx_conhecimento_seller on base_conhecimento (seller_id, ordem);

-- Uma linha por loja. O agente rele periodicamente durante a live, entao mudar
-- aqui pelo painel muda o comportamento sem reiniciar nada.
create table if not exists configuracoes (
    seller_id          text primary key references sellers(id) on delete cascade,
    auto_reply_enabled boolean not null default false,
    max_por_minuto     int not null default 4,
    intents_auto       text[] not null default '{preco,frete,prazo,como_comprar}',
    tom_de_voz         text default 'Direto, animado, informal -- tom de live de venda.',
    instrucoes_extras  text,
    hot_lead_threshold int not null default 7
);

-- ==========================================================================
-- 3. MENSAGENS DO CHAT  (pagina "Ao Vivo")
-- ==========================================================================
create table if not exists messages (
    message_id        text primary key,
    seller_id         text not null,
    live_id           uuid,              -- preenchido pelo agente, nasce na sessao
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
-- 4. LEADS  (CRM)
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
-- 5. COMANDOS  (painel -> agente local)
-- ==========================================================================
-- O painel roda no navegador e nao alcanca o Playwright. Entao ele enfileira
-- comandos aqui e o agente na maquina do vendedor faz polling.
create table if not exists commands (
    id         uuid primary key default gen_random_uuid(),
    seller_id  text not null,
    kind       text not null check (kind in ('send_reply', 'pause_auto', 'resume_auto',
                                             'supervisor_checkin', 'replay_live')),
    payload    jsonb not null default '{}'::jsonb,
    status     text not null default 'pending' check (status in ('pending', 'done', 'failed')),
    created_at timestamptz not null default now(),
    done_at    timestamptz
);

create index if not exists idx_commands_pending on commands (seller_id, created_at)
    where status = 'pending';

-- Check-in de supervisao e contagem de replay sao efeitos que precisam valer na
-- hora, mesmo com o agente offline -- por isso acontecem no banco, nao no
-- agente. O agente ainda le o comando para liberar o auto-envio na sua ponta.
create or replace function aplicar_comando_supervisao()
returns trigger language plpgsql security definer set search_path to 'public' as $$
begin
  if new.kind = 'supervisor_checkin' then
    insert into replay_supervisao (seller_id, supervisor, presente, ultimo_checkin)
    values (new.seller_id, new.payload ->> 'supervisor', true, now())
    on conflict (seller_id) do update set
      supervisor     = excluded.supervisor,
      presente       = true,
      ultimo_checkin = now();

  elsif new.kind = 'replay_live' and (new.payload ->> 'live_id') is not null then
    update lives
       set replays       = replays + 1,
           ultimo_replay = now()
     where id = (new.payload ->> 'live_id')::uuid;
  end if;

  return new;
end $$;

drop trigger if exists trg_comando_supervisao on commands;
create trigger trg_comando_supervisao
    after insert on commands
    for each row execute function aplicar_comando_supervisao();

-- ==========================================================================
-- 6. LIVES  (pagina "Lives Prontas")
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
    vendas         int default 0,             -- zerado ate o TikTok Shop entrar
    receita        numeric(10,2) default 0,   -- idem

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
-- 7. SESSAO DE REPLAY  (trava de supervisao)
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
-- 8. RLS  (multi-tenant)
-- ==========================================================================
alter table sellers            enable row level security;
alter table seller_users       enable row level security;
alter table produtos           enable row level security;
alter table frete_regras       enable row level security;
alter table base_conhecimento  enable row level security;
alter table configuracoes      enable row level security;
alter table messages           enable row level security;
alter table leads              enable row level security;
alter table commands           enable row level security;
alter table lives              enable row level security;
alter table replay_supervisao  enable row level security;

create policy "acesso_loja"   on sellers            for all using (tem_acesso(id))        with check (tem_acesso(id));
create policy "acesso_vinculo" on seller_users      for all using (user_id = auth.uid())  with check (user_id = auth.uid());
create policy "acesso_loja"   on produtos           for all using (tem_acesso(seller_id)) with check (tem_acesso(seller_id));
create policy "acesso_loja"   on frete_regras       for all using (tem_acesso(seller_id)) with check (tem_acesso(seller_id));
create policy "acesso_loja"   on base_conhecimento  for all using (tem_acesso(seller_id)) with check (tem_acesso(seller_id));
create policy "acesso_loja"   on configuracoes      for all using (tem_acesso(seller_id)) with check (tem_acesso(seller_id));
create policy "acesso_loja"   on messages           for all using (tem_acesso(seller_id)) with check (tem_acesso(seller_id));
create policy "acesso_loja"   on leads              for all using (tem_acesso(seller_id)) with check (tem_acesso(seller_id));
create policy "acesso_loja"   on commands           for all using (tem_acesso(seller_id)) with check (tem_acesso(seller_id));
create policy "acesso_loja"   on lives              for all using (tem_acesso(seller_id)) with check (tem_acesso(seller_id));
create policy "acesso_loja"   on replay_supervisao  for all using (tem_acesso(seller_id)) with check (tem_acesso(seller_id));

-- ==========================================================================
-- 9. REALTIME  (o painel escuta estas tabelas)
-- ==========================================================================
alter publication supabase_realtime add table messages;
alter publication supabase_realtime add table leads;
alter publication supabase_realtime add table lives;

-- ==========================================================================
-- 10. PRIMEIRA LOJA
-- ==========================================================================
insert into sellers (id, nome, tiktok_username, plano)
values ('mix-conecta', 'Mix Conecta', '@mixconecta', 'ativo')
on conflict (id) do nothing;

insert into configuracoes (seller_id) values ('mix-conecta')
on conflict (seller_id) do nothing;

insert into replay_supervisao (seller_id) values ('mix-conecta')
on conflict (seller_id) do nothing;

-- Vincule seu usuario a loja depois de criar a conta pelo painel:
--   insert into seller_users (seller_id, user_id, papel)
--   values ('mix-conecta', '<uuid do auth.users>', 'dono');

-- --------------------------------------------------------------------------
-- PENDENCIA CONHECIDA (nao replicada aqui de proposito)
--
-- No banco atual, `seller_id` de messages/leads/commands/lives/
-- replay_supervisao carrega `default 'mix-conecta'`, heranca da fase em que o
-- sistema era de uma loja so. Num SaaS multi-loja isso e uma armadilha: um
-- insert que esqueca o seller_id cai silenciosamente na Mix Conecta. Antes de
-- entrar a segunda loja, rode:
--   alter table messages          alter column seller_id drop default;
--   alter table leads             alter column seller_id drop default;
--   alter table commands          alter column seller_id drop default;
--   alter table lives             alter column seller_id drop default;
--   alter table replay_supervisao alter column seller_id drop default;
-- --------------------------------------------------------------------------
