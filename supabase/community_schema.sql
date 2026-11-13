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


-- AGROVISION Field Lab: public, opt-in experiment notes and contributor-reported comparisons.
create table if not exists public.field_lab_trials (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
    title text not null check (char_length(title) between 3 and 90),
    display_alias text not null check (char_length(display_alias) between 2 and 32),
    macroregion text not null check (macroregion in ('Norte','Nordeste','Centro-Oeste','Sudeste','Sul')),
    crop text not null check (char_length(crop) between 2 and 40),
    season text not null check (char_length(season) between 4 and 20),
    hypothesis text not null check (char_length(hypothesis) between 5 and 700),
    strategy text not null check (char_length(strategy) between 2 and 500),
    comparator text not null check (char_length(comparator) between 2 and 500),
    metric text not null check (char_length(metric) between 2 and 50),
    unit text not null check (char_length(unit) between 1 and 24),
    baseline_value double precision,
    alternative_value double precision,
    notes text not null default '' check (char_length(notes) <= 1000),
    status text not null default 'community observation',
    published boolean not null default true,
    created_at timestamptz not null default now()
);
create index if not exists field_lab_trials_public_idx
    on public.field_lab_trials (crop, season, macroregion, created_at desc)
    where published = true;
alter table public.field_lab_trials enable row level security;
drop policy if exists "Anyone can read published Field Lab records" on public.field_lab_trials;
create policy "Anyone can read published Field Lab records"
    on public.field_lab_trials for select to anon, authenticated
    using (published = true or auth.uid() = user_id);
drop policy if exists "Users can publish their own Field Lab records" on public.field_lab_trials;
create policy "Users can publish their own Field Lab records"
    on public.field_lab_trials for insert to authenticated
    with check (auth.uid() = user_id and published = true);
drop policy if exists "Users can delete their own Field Lab records" on public.field_lab_trials;
create policy "Users can delete their own Field Lab records"
    on public.field_lab_trials for delete to authenticated
    using (auth.uid() = user_id);
grant select on public.field_lab_trials to anon, authenticated;
grant insert, delete on public.field_lab_trials to authenticated;


-- Longitudinal follow-up observations linked to a public Field Lab hypothesis.
create table if not exists public.field_lab_updates (
    id uuid primary key default gen_random_uuid(),
    trial_id uuid not null references public.field_lab_trials(id) on delete cascade,
    user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
    display_alias text not null check (char_length(display_alias) between 2 and 32),
    season text not null check (char_length(season) between 4 and 20),
    observation_date date not null check (observation_date <= current_date),
    stage text not null check (stage in ('Plantio','Desenvolvimento','Colheita','Pós-colheita','Acompanhamento')),
    arm text not null check (arm in ('Estratégia','Comparador','Outro')),
    observed_value double precision not null check (observed_value > '-Infinity'::float8 and observed_value < 'Infinity'::float8),
    unit text not null check (char_length(unit) between 1 and 24),
    method text not null check (char_length(method) between 3 and 500),
    notes text not null default '' check (char_length(notes) <= 1000),
    published boolean not null default true,
    created_at timestamptz not null default now()
);
create index if not exists field_lab_updates_trial_date_idx
    on public.field_lab_updates (trial_id, observation_date, created_at)
    where published = true;
alter table public.field_lab_updates enable row level security;
drop policy if exists "Anyone can read published Field Lab updates" on public.field_lab_updates;
create policy "Anyone can read published Field Lab updates"
    on public.field_lab_updates for select to anon, authenticated
    using (published = true or auth.uid() = user_id);
drop policy if exists "Users can publish Field Lab updates" on public.field_lab_updates;
create policy "Users can publish Field Lab updates"
    on public.field_lab_updates for insert to authenticated
    with check (
        auth.uid() = user_id
        and published = true
        and exists (
            select 1 from public.field_lab_trials t
            where t.id = trial_id and t.published = true
        )
    );
drop policy if exists "Users can delete their own Field Lab updates" on public.field_lab_updates;
create policy "Users can delete their own Field Lab updates"
    on public.field_lab_updates for delete to authenticated
    using (auth.uid() = user_id);
grant select on public.field_lab_updates to anon, authenticated;
grant insert, delete on public.field_lab_updates to authenticated;
