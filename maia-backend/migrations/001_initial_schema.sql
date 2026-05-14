-- MaIA — Schema inicial
-- Aplicar no Supabase SQL Editor (projeto de dev)

-- ============================================================
-- profiles
-- ============================================================
create table if not exists public.profiles (
    id          uuid primary key references auth.users(id) on delete cascade,
    email       text,
    plan        text not null default 'trial' check (plan in ('trial', 'active', 'inactive')),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles: user vê o próprio" on public.profiles
    for select using (auth.uid() = id);

create policy "profiles: user atualiza o próprio" on public.profiles
    for update using (auth.uid() = id);

-- trigger: cria profile automaticamente ao criar usuário
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
    insert into public.profiles (id, email, plan)
    values (new.id, new.email, 'trial')
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ============================================================
-- conversations
-- ============================================================
create table if not exists public.conversations (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references public.profiles(id) on delete cascade,
    title       text not null default 'Nova conversa',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index if not exists conversations_user_id_idx on public.conversations(user_id);

alter table public.conversations enable row level security;

create policy "conversations: user vê as próprias" on public.conversations
    for select using (auth.uid() = user_id);

create policy "conversations: user cria" on public.conversations
    for insert with check (auth.uid() = user_id);

create policy "conversations: user atualiza as próprias" on public.conversations
    for update using (auth.uid() = user_id);

create policy "conversations: user deleta as próprias" on public.conversations
    for delete using (auth.uid() = user_id);

-- ============================================================
-- messages
-- ============================================================
create table if not exists public.messages (
    id              uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.conversations(id) on delete cascade,
    role            text not null check (role in ('user', 'assistant')),
    content         text not null,
    model_used      text,           -- null para mensagens do user
    tokens_in       integer,
    tokens_out      integer,
    created_at      timestamptz not null default now()
);

create index if not exists messages_conversation_id_idx on public.messages(conversation_id);
create index if not exists messages_created_at_idx on public.messages(created_at);

alter table public.messages enable row level security;

create policy "messages: user vê mensagens de suas conversas" on public.messages
    for select using (
        exists (
            select 1 from public.conversations c
            where c.id = conversation_id and c.user_id = auth.uid()
        )
    );

create policy "messages: user insere em suas conversas" on public.messages
    for insert with check (
        exists (
            select 1 from public.conversations c
            where c.id = conversation_id and c.user_id = auth.uid()
        )
    );

-- ============================================================
-- updated_at triggers
-- ============================================================
create or replace function public.update_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger profiles_updated_at
    before update on public.profiles
    for each row execute function public.update_updated_at();

create trigger conversations_updated_at
    before update on public.conversations
    for each row execute function public.update_updated_at();
