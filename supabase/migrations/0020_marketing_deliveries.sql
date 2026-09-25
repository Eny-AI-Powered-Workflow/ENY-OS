-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0020_marketing_deliveries.sql

insert into permissions (scope) values
  ('marketing:send'),
  ('marketing:integrations'),
  ('marketing:approve_sensitive')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('ceo', 'marketing_lead')
  and p.scope in ('marketing:send', 'marketing:integrations')
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'ceo'
  and p.scope = 'marketing:approve_sensitive'
on conflict do nothing;

create table if not exists marketing_deliveries (
  id uuid primary key default gen_random_uuid(),
  content_id uuid not null references marketing_content_items(id) on delete cascade,
  channel text not null,
  provider text not null,
  status text not null default 'scheduled',
  scheduled_at timestamptz not null,
  sent_at timestamptz,
  external_id text,
  recipient_count integer not null default 0,
  metrics jsonb not null default '{}'::jsonb,
  details jsonb not null default '{}'::jsonb,
  error text,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists marketing_delivery_events (
  id uuid primary key default gen_random_uuid(),
  delivery_id uuid not null references marketing_deliveries(id) on delete cascade,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists marketing_deliveries_status_idx on marketing_deliveries(status, scheduled_at);
create index if not exists marketing_deliveries_content_idx on marketing_deliveries(content_id, created_at desc);
create index if not exists marketing_delivery_events_idx on marketing_delivery_events(delivery_id, created_at desc);

alter table marketing_deliveries enable row level security;
alter table marketing_delivery_events enable row level security;

drop policy if exists "Marketing users can view deliveries" on marketing_deliveries;
create policy "Marketing users can view deliveries" on marketing_deliveries for select using (auth.uid() is not null);
drop policy if exists "Marketing senders can create deliveries" on marketing_deliveries;
create policy "Marketing senders can create deliveries" on marketing_deliveries for insert with check (auth.uid() = created_by);
drop policy if exists "Marketing users can update deliveries" on marketing_deliveries;
create policy "Marketing users can update deliveries" on marketing_deliveries for update using (auth.uid() is not null) with check (auth.uid() is not null);
drop policy if exists "Marketing users can view delivery events" on marketing_delivery_events;
create policy "Marketing users can view delivery events" on marketing_delivery_events for select using (auth.uid() is not null);
drop policy if exists "Marketing users can create delivery events" on marketing_delivery_events;
create policy "Marketing users can create delivery events" on marketing_delivery_events for insert with check (auth.uid() = actor_id);
