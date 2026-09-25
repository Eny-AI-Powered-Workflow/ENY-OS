-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0018_marketing_rbac.sql

insert into roles (name) values
  ('marketing'),
  ('marketing_lead')
on conflict (name) do nothing;

insert into permissions (scope) values
  ('marketing:read'),
  ('marketing:write'),
  ('marketing:approve'),
  ('marketing:publish'),
  ('marketing:analytics'),
  ('marketing:configure'),
  ('marketing:research')
on conflict (scope) do nothing;

-- Marketing staff can create, edit, analyze, and submit work.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'marketing'
  and p.scope in (
    'marketing:read',
    'marketing:write',
    'marketing:analytics',
    'marketing:research'
  )
on conflict do nothing;

-- Marketing leads can approve, publish, configure, and research.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'marketing_lead'
  and p.scope like 'marketing:%'
on conflict do nothing;

-- CEO receives complete Marketing visibility and control.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'ceo'
  and p.scope like 'marketing:%'
on conflict do nothing;
