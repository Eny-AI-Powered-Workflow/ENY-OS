-- /home/obed/Documents/Eny_consulting/supabase/migrations/0014_operational_alerts.sql

create table if not exists operational_alerts (
  id uuid primary key default gen_random_uuid(),
  team text not null default 'sales_enrollment',
  alert_type text not null,
  severity text not null default 'critical',
  source text not null,
  message text not null,
  result_id uuid references batch_execution_results(id) on delete set null,
  status text not null default 'open',
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  acknowledged_at timestamptz,
  acknowledged_by uuid references auth.users(id) on delete set null
);

create index if not exists operational_alerts_open_idx
  on operational_alerts(team, status, severity, created_at desc);
create index if not exists operational_alerts_result_idx
  on operational_alerts(result_id, created_at desc);

alter table operational_alerts enable row level security;

drop policy if exists "Sales users can view operational alerts" on operational_alerts;
create policy "Sales users can view operational alerts"
on operational_alerts for select
using (
  exists (
    select 1 from user_roles ur
    join roles r on r.id = ur.role_id
    where ur.user_id = auth.uid()
      and r.name in ('ceo', 'enrollment')
  )
);

drop policy if exists "Sales users can create operational alerts" on operational_alerts;
create policy "Sales users can create operational alerts"
on operational_alerts for insert
with check (auth.uid() is not null);

drop policy if exists "Sales users can acknowledge operational alerts" on operational_alerts;
create policy "Sales users can acknowledge operational alerts"
on operational_alerts for update
using (auth.uid() is not null)
with check (auth.uid() is not null);
