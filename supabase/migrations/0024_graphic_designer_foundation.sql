-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0024_graphic_designer_foundation.sql

insert into roles (name) values ('graphic_designer')
on conflict (name) do nothing;

insert into permissions (scope) values
  ('design:workspace'),
  ('design:manage'),
  ('design:write'),
  ('design:read_marketing'),
  ('design:read_programs'),
  ('design:review_marketing'),
  ('design:review_programs'),
  ('design:templates'),
  ('design:funnels'),
  ('design:analytics'),
  ('design:publish')
on conflict (scope) do nothing;

-- Designer owns creation and design operations, but not final approval.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'graphic_designer'
  and p.scope in ('design:workspace', 'design:manage', 'design:write', 'design:templates', 'design:funnels', 'design:analytics')
on conflict do nothing;

-- Marketing roles can read approved Marketing assets. Leads can review and publish them.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('marketing', 'business_support')
  and p.scope in ('design:workspace', 'design:read_marketing')
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'marketing_lead'
  and p.scope in ('design:workspace', 'design:read_marketing', 'design:review_marketing', 'design:templates', 'design:funnels', 'design:analytics', 'design:publish')
on conflict do nothing;

-- Programs can review program materials. Student Success can read approved assets only.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'programs_manager'
  and p.scope in ('design:workspace', 'design:read_programs', 'design:review_programs')
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'customer_success'
  and p.scope in ('design:workspace', 'design:read_programs')
on conflict do nothing;

-- CEO has full visibility and control across all Designer resources.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'ceo'
  and p.scope like 'design:%'
on conflict do nothing;

create table if not exists design_system_documents (
  id uuid primary key default gen_random_uuid(),
  document_key text not null,
  title text not null,
  category text not null,
  audience text not null check (audience in ('shared', 'marketing', 'programs', 'student_success')),
  status text not null default 'draft' check (status in ('draft', 'in_review', 'approved', 'archived')),
  source_status text not null default 'unverified' check (source_status in ('unverified', 'verified')),
  source_reference text,
  content text not null,
  metadata_json jsonb not null default '{}'::jsonb,
  version integer not null default 1,
  created_by uuid not null references auth.users(id) on delete restrict,
  updated_by uuid not null references auth.users(id) on delete restrict,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (document_key, audience)
);

create table if not exists design_system_document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references design_system_documents(id) on delete cascade,
  version integer not null,
  snapshot jsonb not null,
  change_note text not null,
  changed_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique (document_id, version)
);

create table if not exists design_system_document_events (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references design_system_documents(id) on delete cascade,
  actor_id uuid not null references auth.users(id) on delete restrict,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists design_documents_audience_status_idx on design_system_documents(audience, status, category);
create index if not exists design_document_versions_idx on design_system_document_versions(document_id, version desc);
create index if not exists design_document_events_idx on design_system_document_events(document_id, created_at desc);

alter table design_system_documents enable row level security;
alter table design_system_document_versions enable row level security;
alter table design_system_document_events enable row level security;

drop policy if exists "Designer and audience roles can read design documents" on design_system_documents;
create policy "Designer and audience roles can read design documents" on design_system_documents for select using (
  exists (
    select 1 from user_roles ur
    join role_permissions rp on rp.role_id = ur.role_id
    join permissions p on p.id = rp.permission_id
    where ur.user_id = auth.uid() and p.scope = 'design:manage'
  )
  or (
    status = 'approved' and audience in ('marketing', 'shared') and exists (
      select 1 from user_roles ur
      join role_permissions rp on rp.role_id = ur.role_id
      join permissions p on p.id = rp.permission_id
      where ur.user_id = auth.uid() and p.scope = 'design:read_marketing'
    )
  )
  or (
    status = 'approved' and audience in ('programs', 'student_success', 'shared') and exists (
      select 1 from user_roles ur
      join role_permissions rp on rp.role_id = ur.role_id
      join permissions p on p.id = rp.permission_id
      where ur.user_id = auth.uid() and p.scope = 'design:read_programs'
    )
  )
  or (
    audience in ('marketing', 'shared') and status = 'in_review' and exists (
      select 1 from user_roles ur
      join role_permissions rp on rp.role_id = ur.role_id
      join permissions p on p.id = rp.permission_id
      where ur.user_id = auth.uid() and p.scope = 'design:review_marketing'
    )
  )
  or (
    audience in ('programs', 'student_success', 'shared') and status = 'in_review' and exists (
      select 1 from user_roles ur
      join role_permissions rp on rp.role_id = ur.role_id
      join permissions p on p.id = rp.permission_id
      where ur.user_id = auth.uid() and p.scope = 'design:review_programs'
    )
  )
);

drop policy if exists "Audience roles can read design document versions" on design_system_document_versions;
create policy "Audience roles can read design document versions" on design_system_document_versions for select using (
  exists (
    select 1 from design_system_documents d
    where d.id = document_id and (
      exists (
        select 1 from user_roles ur
        join role_permissions rp on rp.role_id = ur.role_id
        join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:manage'
      )
      or (d.status = 'approved' and d.audience in ('marketing', 'shared') and exists (
        select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:read_marketing'
      ))
      or (d.status = 'approved' and d.audience in ('programs', 'student_success', 'shared') and exists (
        select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:read_programs'
      ))
      or (d.status = 'in_review' and d.audience in ('marketing', 'shared') and exists (
        select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:review_marketing'
      ))
      or (d.status = 'in_review' and d.audience in ('programs', 'student_success', 'shared') and exists (
        select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:review_programs'
      ))
    )
  )
);

drop policy if exists "Audience roles can read design document events" on design_system_document_events;
create policy "Audience roles can read design document events" on design_system_document_events for select using (
  exists (
    select 1 from design_system_documents d
    where d.id = document_id and (
      exists (
        select 1 from user_roles ur
        join role_permissions rp on rp.role_id = ur.role_id
        join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:manage'
      )
      or (d.status = 'approved' and d.audience in ('marketing', 'shared') and exists (
        select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:read_marketing'
      ))
      or (d.status = 'approved' and d.audience in ('programs', 'student_success', 'shared') and exists (
        select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:read_programs'
      ))
      or (d.status = 'in_review' and d.audience in ('marketing', 'shared') and exists (
        select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:review_marketing'
      ))
      or (d.status = 'in_review' and d.audience in ('programs', 'student_success', 'shared') and exists (
        select 1 from user_roles ur join role_permissions rp on rp.role_id = ur.role_id join permissions p on p.id = rp.permission_id
        where ur.user_id = auth.uid() and p.scope = 'design:review_programs'
      ))
    )
  )
);
