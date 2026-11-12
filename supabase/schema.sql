-- AGROVISION project persistence (run in Supabase SQL Editor).
-- Each authenticated user can only read and modify their own projects.

create table if not exists public.farm_projects (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
    project_name text not null check (char_length(project_name) between 1 and 120),
    latitude double precision not null check (latitude between -90 and 90),
    longitude double precision not null check (longitude between -180 and 180),
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists farm_projects_user_created_idx
    on public.farm_projects (user_id, created_at desc);

alter table public.farm_projects enable row level security;

drop policy if exists "Users can read their own AGROVISION projects" on public.farm_projects;
create policy "Users can read their own AGROVISION projects"
    on public.farm_projects for select
    to authenticated
    using (auth.uid() = user_id);

drop policy if exists "Users can create their own AGROVISION projects" on public.farm_projects;
create policy "Users can create their own AGROVISION projects"
    on public.farm_projects for insert
    to authenticated
    with check (auth.uid() = user_id);

drop policy if exists "Users can update their own AGROVISION projects" on public.farm_projects;
create policy "Users can update their own AGROVISION projects"
    on public.farm_projects for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "Users can delete their own AGROVISION projects" on public.farm_projects;
create policy "Users can delete their own AGROVISION projects"
    on public.farm_projects for delete
    to authenticated
    using (auth.uid() = user_id);

grant select, insert, update, delete on public.farm_projects to authenticated;
