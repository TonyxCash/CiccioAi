-- Ciccio AI: schema iniziale Supabase
-- Eseguire nel SQL Editor del progetto Supabase.
create extension if not exists pgcrypto;

create table if not exists public.ciccio_memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  kind text not null default 'Nota',
  content text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.ciccio_tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  status text not null default 'Da fare'
    check (status in ('Da fare', 'In corso', 'Completata')),
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.ciccio_finance_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  kind text not null check (kind in ('Entrata', 'Spesa')),
  amount numeric(12,2) not null check (amount >= 0),
  description text not null,
  created_at timestamptz not null default now()
);

alter table public.ciccio_memories enable row level security;
alter table public.ciccio_tasks enable row level security;
alter table public.ciccio_finance_entries enable row level security;

drop policy if exists "Users manage own Ciccio memories" on public.ciccio_memories;
create policy "Users manage own Ciccio memories" on public.ciccio_memories
for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own Ciccio tasks" on public.ciccio_tasks;
create policy "Users manage own Ciccio tasks" on public.ciccio_tasks
for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own Ciccio finance entries" on public.ciccio_finance_entries;
create policy "Users manage own Ciccio finance entries" on public.ciccio_finance_entries
for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
