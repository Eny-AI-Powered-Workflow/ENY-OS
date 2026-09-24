-- /home/obed/Documents/Eny_consulting/supabase/migrations/0017_ea_action_reporting.sql

create table if not exists ea_action_items (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  action_type text not null,
  status text not null default 'open',
  priority text not null default 'normal',
  due_at timestamptz,
  completed_at timestamptz,
  owner_id uuid references auth.users(id) on delete set null,
  source text not null default 'ea_workspace',
  details jsonb not null default '{}'::jsonb,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ea_action_events (
  id uuid primary key default gen_random_uuid(),
  action_id uuid not null references ea_action_items(id) on delete cascade,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists ea_action_items_status_idx on ea_action_items(status, due_at);
create index if not exists ea_action_items_type_idx on ea_action_items(action_type, status);
create index if not exists ea_action_events_action_idx on ea_action_events(action_id, created_at desc);

alter table ea_action_items enable row level security;
alter table ea_action_events enable row level security;

drop policy if exists "EA users can view action items" on ea_action_items;
create policy "EA users can view action items" on ea_action_items for select using (auth.uid() is not null);
drop policy if exists "EA users can create action items" on ea_action_items;
create policy "EA users can create action items" on ea_action_items for insert with check (auth.uid() = created_by);
drop policy if exists "EA users can update action items" on ea_action_items;
create policy "EA users can update action items" on ea_action_items for update using (auth.uid() is not null) with check (auth.uid() is not null);
drop policy if exists "EA users can view action events" on ea_action_events;
create policy "EA users can view action events" on ea_action_events for select using (auth.uid() is not null);
drop policy if exists "EA users can create action events" on ea_action_events;
create policy "EA users can create action events" on ea_action_events for insert with check (auth.uid() = actor_id);
