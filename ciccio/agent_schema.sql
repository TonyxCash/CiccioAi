-- Ciccio autonomous run log. Run this once in Supabase SQL Editor.
-- The GitHub Actions runner uses the service-role key stored as a secret.
create table if not exists public.ciccio_agent_runs (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  goal text not null,
  action text not null,
  reason text not null,
  expected_result text not null,
  verification text not null,
  status text not null default 'planned'
    check (status in ('planned', 'approved', 'in_progress', 'completed', 'blocked', 'failed')),
  result text not null default '',
  model text not null default ''
);

alter table public.ciccio_agent_runs enable row level security;
-- No anon/authenticated policies are created. Server-side access is via the
-- Supabase service-role key, which must only be stored in GitHub Actions Secrets
-- and must never be placed in source code or Streamlit's public-facing UI.


-- Durable work memory and task list shared by the Streamlit app and scheduled agent.
create table if not exists public.ciccio_memories (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  kind text not null,
  content text not null
);
create index if not exists ciccio_memories_created_at_idx
  on public.ciccio_memories (created_at desc);

create table if not exists public.ciccio_tasks (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  title text not null,
  status text not null default 'Da fare'
    check (status in ('Da fare', 'In corso', 'Completata')),
  notes text not null default '',
  updated_at timestamptz not null default now()
);
create index if not exists ciccio_tasks_created_at_idx
  on public.ciccio_tasks (created_at desc);

alter table public.ciccio_memories enable row level security;
alter table public.ciccio_tasks enable row level security;
-- No client policies: access remains server-side using the service-role secret.
