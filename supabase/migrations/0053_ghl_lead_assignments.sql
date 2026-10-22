-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0053_ghl_lead_assignments.sql
create table if not exists lead_assignments (
  contact_id text primary key,
  assigned_user_id uuid not null references auth.users(id) on delete cascade,
  assigned_department text not null check (assigned_department in ('sales', 'enrollment')),
  assigned_by_user_id uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists lead_assignments_owner_idx
  on lead_assignments(assigned_user_id, assigned_department);

alter table lead_assignments enable row level security;
revoke all on lead_assignments from public, anon, authenticated;
grant all on lead_assignments to service_role;

insert into lead_assignments (
  contact_id,
  assigned_user_id,
  assigned_department,
  created_at,
  updated_at
)
select distinct on (contact_id)
  contact_id,
  assigned_user_id,
  assigned_department,
  created_at,
  updated_at
from batch_execution_results
where assigned_user_id is not null
  and assigned_department in ('sales', 'enrollment')
order by contact_id, updated_at desc, created_at desc
on conflict (contact_id) do nothing;
