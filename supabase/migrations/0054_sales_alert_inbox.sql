-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0054_sales_alert_inbox.sql
insert into permissions (scope)
values ('sales:alerts:read'), ('sales:alerts:manage')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('ceo', 'sales', 'sales_lead', 'enrollment', 'enrollment_lead')
  and p.scope in ('sales:alerts:read', 'sales:alerts:manage')
on conflict do nothing;

create table if not exists operational_alert_user_states (
  alert_id uuid not null references operational_alerts(id) on delete cascade,
  user_id uuid not null,
  read_at timestamptz,
  dismissed_at timestamptz,
  primary key (alert_id, user_id)
);

create index if not exists operational_alert_user_states_user_idx
  on operational_alert_user_states(user_id, dismissed_at, read_at);

alter table operational_alert_user_states enable row level security;
revoke all on operational_alert_user_states from public, anon, authenticated;
grant all on operational_alert_user_states to service_role;
