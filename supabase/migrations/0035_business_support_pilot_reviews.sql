-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0035_business_support_pilot_reviews.sql

insert into permissions (scope) values
  ('business_support:pilot:read'),
  ('business_support:pilot:write')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('business_support', 'ceo')
  and p.scope in ('business_support:pilot:read', 'business_support:pilot:write')
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'programs_manager'
  and p.scope in ('business_support:dashboard:read', 'business_support:pilot:read')
on conflict do nothing;

create table if not exists business_support_pilot_reviews (
  id uuid primary key,
  scenario text not null check (scenario in (
    'shadow_output',
    'provider_unavailable',
    'malformed_or_duplicate_webhook',
    'delayed_payment_evidence',
    'missing_recording',
    'rejected_action'
  )),
  workflow_name text check (workflow_name is null or workflow_name in (
    'eny-prog-onboard',
    'eny-prog-monitor'
  )),
  result text not null check (result in ('expected', 'unexpected', 'not_run')),
  false_positive boolean,
  missing_data boolean,
  processing_seconds integer check (processing_seconds is null or processing_seconds >= 0),
  escalation_quality smallint check (escalation_quality is null or escalation_quality between 1 and 5),
  reviewer_user_id uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  check (scenario <> 'shadow_output' or workflow_name is not null)
);

create index if not exists business_support_pilot_reviews_created_idx
  on business_support_pilot_reviews(created_at desc);

alter table business_support_pilot_reviews enable row level security;
drop policy if exists "service role manages business support pilot reviews" on business_support_pilot_reviews;
create policy "service role manages business support pilot reviews"
on business_support_pilot_reviews for all to service_role
using (true)
with check (true);

revoke all on business_support_pilot_reviews from anon, authenticated;
grant select, insert on business_support_pilot_reviews to service_role;