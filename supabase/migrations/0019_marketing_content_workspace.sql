-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0019_marketing_content_workspace.sql

create table if not exists marketing_content_items (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  content_type text not null,
  channel text not null,
  status text not null default 'draft',
  content text not null,
  campaign_owner_id uuid references auth.users(id) on delete set null,
  due_at timestamptz,
  prompt text,
  source_documents jsonb not null default '[]'::jsonb,
  confidence text not null default 'unverified',
  revision integer not null default 1,
  approval_required boolean not null default true,
  created_by uuid not null references auth.users(id) on delete restrict,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists marketing_content_events (
  id uuid primary key default gen_random_uuid(),
  content_id uuid not null references marketing_content_items(id) on delete cascade,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists marketing_content_status_idx on marketing_content_items(status, due_at);
create index if not exists marketing_content_channel_idx on marketing_content_items(channel, content_type);
create index if not exists marketing_content_events_idx on marketing_content_events(content_id, created_at desc);

alter table marketing_content_items enable row level security;
alter table marketing_content_events enable row level security;

drop policy if exists "Marketing users can view content" on marketing_content_items;
create policy "Marketing users can view content" on marketing_content_items for select using (auth.uid() is not null);
drop policy if exists "Marketing users can create content" on marketing_content_items;
create policy "Marketing users can create content" on marketing_content_items for insert with check (auth.uid() = created_by);
drop policy if exists "Marketing users can update content" on marketing_content_items;
create policy "Marketing users can update content" on marketing_content_items for update using (auth.uid() is not null) with check (auth.uid() is not null);
drop policy if exists "Marketing users can view events" on marketing_content_events;
create policy "Marketing users can view events" on marketing_content_events for select using (auth.uid() is not null);
drop policy if exists "Marketing users can create events" on marketing_content_events;
create policy "Marketing users can create events" on marketing_content_events for insert with check (auth.uid() = actor_id);
