-- ListingAI: schema iniziale Supabase
-- Eseguire una sola volta nel SQL Editor del progetto Supabase.
-- Le policy impediscono agli utenti autenticati di leggere o modificare gli annunci altrui.

create extension if not exists pgcrypto;

create table if not exists public.listings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default '',
  description text not null default '',
  hashtags text not null default '',
  category text not null default '',
  brand text not null default '',
  size text not null default '',
  color text not null default '',
  condition text not null default '',
  material text not null default '',
  details text not null default '',
  price numeric(10,2),
  platform text not null default 'Generico',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists listings_user_id_idx on public.listings(user_id);
create index if not exists listings_created_at_idx on public.listings(created_at desc);

alter table public.listings enable row level security;

drop policy if exists "Users can view their own listings" on public.listings;
create policy "Users can view their own listings"
  on public.listings for select
  to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "Users can create their own listings" on public.listings;
create policy "Users can create their own listings"
  on public.listings for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their own listings" on public.listings;
create policy "Users can update their own listings"
  on public.listings for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete their own listings" on public.listings;
create policy "Users can delete their own listings"
  on public.listings for delete
  to authenticated
  using ((select auth.uid()) = user_id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_listings_updated_at on public.listings;
create trigger set_listings_updated_at
before update on public.listings
for each row execute function public.set_updated_at();
