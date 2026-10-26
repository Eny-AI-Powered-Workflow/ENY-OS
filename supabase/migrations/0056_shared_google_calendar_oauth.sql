-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0056_shared_google_calendar_oauth.sql
create table if not exists google_calendar_oauth_states (
  id uuid primary key default gen_random_uuid(),
  state_hash text not null unique,
  connected_by uuid not null references auth.users(id) on delete cascade,
  redirect_origin text not null,
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists google_calendar_oauth_states_expires_at_idx
  on google_calendar_oauth_states (expires_at);

create table if not exists google_calendar_connections (
  id uuid primary key default gen_random_uuid(),
  shared_slot smallint not null default 1 unique check (shared_slot = 1),
  connected_by uuid references auth.users(id) on delete set null,
  access_token_encrypted text not null,
  refresh_token_encrypted text not null,
  token_expires_at timestamptz not null,
  scopes text[] not null default '{}',
  status text not null default 'connected'
    check (status in ('connected', 'error')),
  connected_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table google_calendar_oauth_states enable row level security;
alter table google_calendar_connections enable row level security;

insert into permissions (scope)
values ('calendar:read'), ('calendar:manage')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where (r.name = 'ceo' and p.scope in ('calendar:read', 'calendar:manage'))
   or (r.name in ('executive_assistant', 'marketing', 'marketing_lead') and p.scope = 'calendar:read')
on conflict do nothing;
