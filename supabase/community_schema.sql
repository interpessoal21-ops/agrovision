-- AGROVISION Commons: explicit opt-in sharing of anonymized aggregate climate fingerprints.
-- Run in Supabase SQL Editor after schema.sql. No coordinates, email, farm name or raw daily rows are stored.
create table if not exists public.community_snapshots (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
    display_alias text not null check (char_length(display_alias) between 2 and 32),
    macroregion text not null check (macroregion in ('Norte','Nordeste','Centro-Oeste','Sudeste','Sul')),
    crop text not null check (char_length(crop) between 2 and 40),
    season text not null check (char_length(season) between 4 and 20),
    metrics jsonb not null,
    source_metadata jsonb not null default '{}'::jsonb,
    published boolean not null default true,
    created_at timestamptz not null default now()
);
create index if not exists community_snapshots_public_idx
    on public.community_snapshots (macroregion, crop, season, created_at desc)
    where published = true;
alter table public.community_snapshots enable row level security;
drop policy if exists "Anyone can read published AGROVISION community snapshots" on public.community_snapshots;
create policy "Anyone can read published AGROVISION community snapshots"
    on public.community_snapshots for select
    to anon, authenticated
    using (published = true or auth.uid() = user_id);
drop policy if exists "Users can publish their own AGROVISION snapshots" on public.community_snapshots;
create policy "Users can publish their own AGROVISION snapshots"
    on public.community_snapshots for insert
    to authenticated
    with check (auth.uid() = user_id and published = true);
drop policy if exists "Users can delete their own AGROVISION snapshots" on public.community_snapshots;
create policy "Users can delete their own AGROVISION snapshots"
    on public.community_snapshots for delete
    to authenticated
    using (auth.uid() = user_id);
grant select on public.community_snapshots to anon, authenticated;
grant insert, delete on public.community_snapshots to authenticated;
