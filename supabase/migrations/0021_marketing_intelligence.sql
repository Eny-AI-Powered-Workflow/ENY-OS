-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0021_marketing_intelligence.sql

insert into permissions (scope) values
  ('marketing:seo'),
  ('marketing:social')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('ceo', 'marketing', 'marketing_lead')
  and p.scope in ('marketing:seo', 'marketing:social')
on conflict do nothing;

create table if not exists marketing_seo_observations (
  id uuid primary key default gen_random_uuid(),
  observation_type text not null,
  keyword text,
  url text,
  value jsonb not null default '{}'::jsonb,
  source text not null,
  observed_at timestamptz not null,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now()
);

create table if not exists marketing_social_mentions (
  id uuid primary key default gen_random_uuid(),
  platform text not null,
  external_id text,
  author text,
  text text not null,
  url text,
  matched_term text not null,
  classification text not null default 'unclassified',
  sentiment text not null default 'unclassified',
  risk_level text not null default 'low',
  status text not null default 'open',
  source text not null,
  observed_at timestamptz not null,
  owner_id uuid references auth.users(id) on delete set null,
  metadata_json jsonb not null default '{}'::jsonb,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now()
);

create table if not exists marketing_intelligence_events (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists marketing_seo_observations_type_idx on marketing_seo_observations(observation_type, observed_at desc);
create index if not exists marketing_seo_observations_keyword_idx on marketing_seo_observations(keyword, observed_at desc);
create index if not exists marketing_social_mentions_risk_idx on marketing_social_mentions(risk_level, status, observed_at desc);
create index if not exists marketing_social_mentions_platform_idx on marketing_social_mentions(platform, observed_at desc);
create index if not exists marketing_intelligence_events_entity_idx on marketing_intelligence_events(entity_type, entity_id, created_at desc);

alter table marketing_seo_observations enable row level security;
alter table marketing_social_mentions enable row level security;
alter table marketing_intelligence_events enable row level security;

create policy "Authenticated users can view Marketing SEO observations" on marketing_seo_observations for select using (auth.uid() is not null);
create policy "Authenticated users can view Marketing social mentions" on marketing_social_mentions for select using (auth.uid() is not null);
create policy "Authenticated users can view Marketing intelligence events" on marketing_intelligence_events for select using (auth.uid() is not null);
