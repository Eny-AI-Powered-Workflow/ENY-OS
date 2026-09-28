-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0025_design_requests_assets_templates.sql

insert into permissions (scope) values
  ('design:request'),
  ('design:publish_marketing'),
  ('design:publish_programs')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('marketing', 'business_support', 'programs_manager', 'customer_success')
  and p.scope = 'design:request'
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('graphic_designer', 'marketing_lead')
  and p.scope = 'design:request'
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'marketing_lead'
  and p.scope = 'design:publish_marketing'
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'programs_manager'
  and p.scope = 'design:publish_programs'
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'ceo'
  and p.scope like 'design:%'
on conflict do nothing;

create table if not exists design_requests (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  brief text not null,
  request_type text not null,
  audience text not null check (audience in ('shared', 'marketing', 'programs', 'student_success')),
  status text not null default 'requested' check (status in ('requested', 'in_progress', 'in_review', 'completed', 'cancelled')),
  requester_id uuid not null references auth.users(id) on delete restrict,
  owner_id uuid references auth.users(id) on delete set null,
  due_at timestamptz,
  campaign_name text,
  program_name text,
  source_content_id uuid references marketing_content_items(id) on delete set null,
  source_video_asset_id uuid references marketing_video_assets(id) on delete set null,
  reference_urls jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists design_request_events (
  id uuid primary key default gen_random_uuid(),
  request_id uuid not null references design_requests(id) on delete cascade,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists design_templates (
  id uuid primary key default gen_random_uuid(),
  template_key text not null,
  title text not null,
  category text not null,
  audience text not null check (audience in ('shared', 'marketing', 'programs', 'student_success')),
  provider text not null default 'manual_canva',
  provider_template_id text,
  template_url text,
  status text not null default 'draft' check (status in ('draft', 'in_review', 'approved', 'archived')),
  base_brand_document_id uuid not null references design_system_documents(id) on delete restrict,
  base_brand_version integer not null,
  locked_fields jsonb not null default '[]'::jsonb,
  locked_values jsonb not null default '{}'::jsonb,
  editable_fields jsonb not null default '[]'::jsonb,
  usage_rights jsonb not null default '{}'::jsonb,
  version integer not null default 1,
  created_by uuid not null references auth.users(id) on delete restrict,
  updated_by uuid not null references auth.users(id) on delete restrict,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (template_key, audience)
);

create table if not exists design_template_versions (
  id uuid primary key default gen_random_uuid(),
  template_id uuid not null references design_templates(id) on delete cascade,
  version integer not null,
  snapshot jsonb not null,
  change_note text not null,
  changed_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique (template_id, version)
);

create table if not exists design_template_events (
  id uuid primary key default gen_random_uuid(),
  template_id uuid not null references design_templates(id) on delete cascade,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists design_assets (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  asset_type text not null,
  audience text not null check (audience in ('shared', 'marketing', 'programs', 'student_success')),
  status text not null default 'draft' check (status in ('draft', 'in_review', 'approved', 'published', 'rejected', 'archived')),
  provider text not null default 'manual_upload',
  request_id uuid references design_requests(id) on delete set null,
  template_id uuid references design_templates(id) on delete set null,
  template_version integer,
  locked_values_snapshot jsonb not null default '{}'::jsonb,
  variant_values jsonb not null default '{}'::jsonb,
  brand_document_id uuid not null references design_system_documents(id) on delete restrict,
  brand_version integer not null,
  campaign_name text,
  program_name text,
  source_content_id uuid references marketing_content_items(id) on delete set null,
  source_video_asset_id uuid references marketing_video_assets(id) on delete set null,
  usage_rights jsonb not null default '{}'::jsonb,
  revision integer not null default 1,
  created_by uuid not null references auth.users(id) on delete restrict,
  updated_by uuid not null references auth.users(id) on delete restrict,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  published_by uuid references auth.users(id) on delete set null,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists design_asset_files (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references design_assets(id) on delete cascade,
  file_kind text not null check (file_kind in ('source', 'export', 'preview')),
  provider text not null default 'manual_upload',
  original_filename text not null,
  mime_type text not null,
  size_bytes bigint not null,
  storage_path text not null unique,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now()
);

create table if not exists design_asset_versions (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references design_assets(id) on delete cascade,
  revision integer not null,
  snapshot jsonb not null,
  change_note text not null,
  changed_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique (asset_id, revision)
);

create table if not exists design_asset_events (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references design_assets(id) on delete cascade,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists design_requests_queue_idx on design_requests(status, audience, due_at);
create index if not exists design_request_events_history_idx on design_request_events(request_id, created_at desc);
create index if not exists design_templates_audience_status_idx on design_templates(audience, status, category);
create index if not exists design_template_versions_history_idx on design_template_versions(template_id, version desc);
create index if not exists design_assets_queue_idx on design_assets(audience, status, created_at desc);
create index if not exists design_asset_files_asset_idx on design_asset_files(asset_id, created_at desc);
create index if not exists design_asset_versions_history_idx on design_asset_versions(asset_id, revision desc);
create index if not exists design_asset_events_history_idx on design_asset_events(asset_id, created_at desc);

alter table design_requests enable row level security;
alter table design_request_events enable row level security;
alter table design_templates enable row level security;
alter table design_template_versions enable row level security;
alter table design_template_events enable row level security;
alter table design_assets enable row level security;
alter table design_asset_files enable row level security;
alter table design_asset_versions enable row level security;
alter table design_asset_events enable row level security;

create policy "Requester or Designer can read design requests" on design_requests for select using (
  requester_id = auth.uid() or exists (
    select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id
    where ur.user_id = auth.uid() and p.scope = 'design:manage'
  )
);
create policy "Request participants can read request events" on design_request_events for select using (
  exists (select 1 from design_requests r where r.id = request_id)
);

create policy "Audience roles can read design templates" on design_templates for select using (
  exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:manage')
  or (status = 'approved' and audience in ('marketing', 'shared') and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:templates'))
  or (status = 'approved' and audience in ('programs', 'student_success', 'shared') and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:read_programs'))
  or (status = 'in_review' and audience = 'marketing' and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:review_marketing'))
  or (status = 'in_review' and audience in ('programs', 'student_success') and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:review_programs'))
);

create policy "Audience roles can read design assets" on design_assets for select using (
  exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:manage')
  or (status in ('approved', 'published') and audience in ('marketing', 'shared') and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:read_marketing'))
  or (status in ('approved', 'published') and audience in ('programs', 'student_success', 'shared') and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:read_programs'))
  or (status = 'in_review' and audience = 'marketing' and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:review_marketing'))
  or (status = 'in_review' and audience in ('programs', 'student_success') and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:review_programs'))
);

create policy "Authorized roles can read design asset files" on design_asset_files for select using (
  exists (select 1 from design_assets a where a.id = asset_id)
);
create policy "Authorized roles can read design asset versions" on design_asset_versions for select using (
  exists (select 1 from design_assets a where a.id = asset_id)
);
create policy "Authorized roles can read design asset events" on design_asset_events for select using (
  exists (select 1 from design_assets a where a.id = asset_id)
);
create policy "Authorized roles can read design template versions" on design_template_versions for select using (
  exists (select 1 from design_templates t where t.id = template_id)
);
create policy "Authorized roles can read design template events" on design_template_events for select using (
  exists (select 1 from design_templates t where t.id = template_id)
);

-- Keep existing foundation review queues aligned with the audience boundary:
-- shared items are readable cross-team only after approval.
drop policy if exists "Designer and audience roles can read design documents" on design_system_documents;
create policy "Designer and audience roles can read design documents" on design_system_documents for select using (
  exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:manage')
  or (status = 'approved' and audience in ('marketing', 'shared') and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:read_marketing'))
  or (status = 'approved' and audience in ('programs', 'student_success', 'shared') and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:read_programs'))
  or (status = 'in_review' and audience = 'marketing' and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:review_marketing'))
  or (status = 'in_review' and audience in ('programs', 'student_success') and exists (select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id where ur.user_id = auth.uid() and p.scope = 'design:review_programs'))
);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'design-assets',
  'design-assets',
  false,
  52428800,
  array['image/png', 'image/jpeg', 'image/webp', 'application/pdf', 'video/mp4']
)
on conflict (id) do update set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
