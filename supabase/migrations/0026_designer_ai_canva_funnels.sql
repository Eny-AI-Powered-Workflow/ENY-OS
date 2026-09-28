-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0026_designer_ai_canva_funnels.sql

insert into permissions (scope) values
  ('design:ai'),
  ('design:canva')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('graphic_designer', 'ceo')
  and p.scope in ('design:ai', 'design:canva')
on conflict do nothing;

alter table design_templates
  add column if not exists canva_dataset jsonb not null default '{}'::jsonb;

alter table design_assets
  add column if not exists generation_prompt text,
  add column if not exists generation_sources jsonb not null default '[]'::jsonb,
  add column if not exists generation_draft jsonb not null default '{}'::jsonb,
  add column if not exists canva_job_id text,
  add column if not exists external_design_id text,
  add column if not exists external_design_url text,
  add column if not exists external_edit_url text,
  add column if not exists external_view_url text,
  add column if not exists external_thumbnail_url text,
  add column if not exists external_urls_expires_at timestamptz,
  add column if not exists export_job_id text;

create table if not exists canva_oauth_states (
  id uuid primary key default gen_random_uuid(),
  state_hash text not null unique,
  verifier_encrypted text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists canva_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  access_token_encrypted text not null,
  refresh_token_encrypted text not null,
  token_expires_at timestamptz not null,
  scopes text[] not null default '{}'::text[],
  canva_user_id text,
  canva_team_id text,
  status text not null default 'connected' check (status in ('connected', 'revoked', 'error')),
  connected_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists design_ai_drafts (
  id uuid primary key default gen_random_uuid(),
  request_id uuid not null references design_requests(id) on delete cascade,
  audience text not null check (audience in ('marketing', 'programs', 'student_success')),
  title text not null,
  visual_direction text not null,
  copy_variants jsonb not null default '[]'::jsonb,
  template_suggestions jsonb not null default '[]'::jsonb,
  source_documents jsonb not null default '[]'::jsonb,
  prompt text not null,
  status text not null default 'draft' check (status in ('draft', 'selected', 'discarded')),
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now()
);

create table if not exists design_funnels (
  id uuid primary key default gen_random_uuid(),
  funnel_key text not null unique,
  title text not null,
  audience text not null default 'marketing' check (audience = 'marketing'),
  provider text not null default 'webflow' check (provider = 'webflow'),
  site_id text,
  collection_id text,
  page_id text,
  collection_item_id text,
  public_url text,
  conversion_events jsonb not null default '[]'::jsonb,
  status text not null default 'draft' check (status in ('draft', 'in_review', 'approved', 'published', 'archived')),
  owner_id uuid not null references auth.users(id) on delete restrict,
  created_by uuid not null references auth.users(id) on delete restrict,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  published_by uuid references auth.users(id) on delete set null,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists design_funnel_variants (
  id uuid primary key default gen_random_uuid(),
  funnel_id uuid not null references design_funnels(id) on delete cascade,
  version integer not null,
  variant_key text not null,
  title text not null,
  content_json jsonb not null,
  form_fields jsonb not null default '[]'::jsonb,
  conversion_event text not null,
  status text not null default 'draft' check (status in ('draft', 'in_review', 'approved', 'published', 'superseded', 'rejected')),
  external_item_id text,
  previous_published_snapshot jsonb not null default '{}'::jsonb,
  created_by uuid not null references auth.users(id) on delete restrict,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  published_by uuid references auth.users(id) on delete set null,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  unique (funnel_id, version, variant_key)
);

create table if not exists design_funnel_events (
  id uuid primary key default gen_random_uuid(),
  funnel_id uuid not null references design_funnels(id) on delete cascade,
  variant_id uuid references design_funnel_variants(id) on delete set null,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists design_provider_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  entity_type text not null,
  entity_id uuid,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  status text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists design_ai_drafts_request_idx on design_ai_drafts(request_id, created_at desc);
create index if not exists design_funnels_status_idx on design_funnels(status, updated_at desc);
create index if not exists design_funnel_variants_status_idx on design_funnel_variants(funnel_id, status, version desc);
create index if not exists design_funnel_events_history_idx on design_funnel_events(funnel_id, created_at desc);
create index if not exists design_provider_events_history_idx on design_provider_events(provider, entity_type, entity_id, created_at desc);

alter table canva_oauth_states enable row level security;
alter table canva_connections enable row level security;
alter table design_ai_drafts enable row level security;
alter table design_funnels enable row level security;
alter table design_funnel_variants enable row level security;
alter table design_funnel_events enable row level security;
alter table design_provider_events enable row level security;

-- No client-side SELECT policy for OAuth state or connection rows. Tokens and PKCE verifier
-- are accessible only through the backend database connection/service role.

create policy "Designer can read design AI drafts" on design_ai_drafts for select using (
  exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:manage')
);

create policy "Designer and marketing leads can read marketing funnels" on design_funnels for select using (
  exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope in ('design:manage', 'design:funnels', 'design:review_marketing'))
);
create policy "Designer and marketing leads can read funnel variants" on design_funnel_variants for select using (
  exists (
    select 1 from design_funnels f
    join user_roles ur on ur.user_id = auth.uid()
    join role_permissions rp on rp.role_id = ur.role_id
    join permissions p on p.id = rp.permission_id
    where f.id = funnel_id and p.scope in ('design:manage', 'design:funnels', 'design:review_marketing')
  )
);
create policy "Designer and marketing leads can read funnel events" on design_funnel_events for select using (
  exists (
    select 1 from design_funnels f
    join user_roles ur on ur.user_id = auth.uid()
    join role_permissions rp on rp.role_id = ur.role_id
    join permissions p on p.id = rp.permission_id
    where f.id = funnel_id and p.scope in ('design:manage', 'design:funnels', 'design:review_marketing')
  )
);

create policy "Designer can read provider audit events" on design_provider_events for select using (
  exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:manage')
);
