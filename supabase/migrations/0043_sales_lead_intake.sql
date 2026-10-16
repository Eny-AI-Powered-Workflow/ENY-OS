-- /home/obed/Documents/Eny_consulting/supabase/migrations/0043_sales_lead_intake.sql
insert into roles (name) values ('sales')
on conflict (name) do nothing;

insert into permissions (scope) values ('ai:chat')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'sales'
  and p.scope in ('leads:read', 'leads:write', 'pipeline:read', 'ai:chat')
on conflict do nothing;

create table if not exists ghl_lead_intake (
  id uuid primary key default gen_random_uuid(),
  contact_id text not null unique,
  source text,
  status text not null default 'pending_review',
  approval_id uuid references cohort_approvals(id) on delete set null,
  received_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ghl_lead_intake_review_idx
  on ghl_lead_intake(status, received_at desc);

alter table ghl_lead_intake enable row level security;

drop policy if exists "Sales and Enrollment can view lead intake" on ghl_lead_intake;
create policy "Sales and Enrollment can view lead intake"
on ghl_lead_intake for select
using (
  exists (
    select 1
    from user_roles ur
    join roles r on r.id = ur.role_id
    where ur.user_id = auth.uid()
      and r.name in ('ceo', 'enrollment', 'sales')
  )
);

drop policy if exists "Authenticated Sales and Enrollment can manage lead intake" on ghl_lead_intake;
create policy "Authenticated Sales and Enrollment can manage lead intake"
on ghl_lead_intake for all
using (
  exists (
    select 1
    from user_roles ur
    join roles r on r.id = ur.role_id
    where ur.user_id = auth.uid()
      and r.name in ('ceo', 'enrollment', 'sales')
  )
)
with check (
  exists (
    select 1
    from user_roles ur
    join roles r on r.id = ur.role_id
    where ur.user_id = auth.uid()
      and r.name in ('ceo', 'enrollment', 'sales')
  )
);

drop policy if exists "Sales users can view operational alerts" on operational_alerts;
create policy "Sales users can view operational alerts"
on operational_alerts for select
using (
  exists (
    select 1
    from user_roles ur
    join roles r on r.id = ur.role_id
    where ur.user_id = auth.uid()
      and r.name in ('ceo', 'enrollment', 'sales')
  )
);

alter table batch_execution_results
  add column if not exists score_reasoning text,
  add column if not exists score_factors jsonb,
  add column if not exists score_evidence jsonb,
  add column if not exists score_unknowns jsonb,
  add column if not exists next_best_action text;

comment on column batch_execution_results.score_reasoning is 'Evidence-based scoring explanation returned by the approved scoring contract.';
comment on column batch_execution_results.score_factors is 'Normalized intent, fit, and engagement component scores used to calculate score.';
comment on column batch_execution_results.score_evidence is 'Evidence strings used by the AI scoring decision.';
comment on column batch_execution_results.score_unknowns is 'Scoring dimensions that lacked sufficient evidence.';
comment on column batch_execution_results.next_best_action is 'Suggested human next action; it does not trigger outreach.';
