-- Sprint 11: perfil da família + soft delete em conversas

-- ── Feature A: perfil da família ──────────────────────────────────────────────

create table user_family_profiles (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null unique references auth.users(id) on delete cascade,
  mother_name      text,
  child_name       text,
  child_age        int check (child_age between 0 and 12),
  child_birth_date date,
  raw_context      jsonb default '{}',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

alter table user_family_profiles enable row level security;

create policy "Usuário lê próprio perfil"
  on user_family_profiles for select using (auth.uid() = user_id);

create policy "Usuário atualiza próprio perfil"
  on user_family_profiles for all using (auth.uid() = user_id);

create trigger set_updated_at
  before update on user_family_profiles
  for each row execute function set_updated_at();

-- ── Feature C: soft delete em conversas ───────────────────────────────────────

alter table conversations add column deleted_at timestamptz;
