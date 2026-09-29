-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0033_customer_success_least_privilege.sql

insert into permissions (scope) values
  ('payments:kajabi:read'),
  ('payments:paystack:read'),
  ('payments:verify'),
  ('students:attendance:read'),
  ('students:attendance:write'),
  ('students:assignments:read'),
  ('students:intervention:review'),
  ('students:intervention:approve'),
  ('students:course_access:request'),
  ('students:course_access:grant'),
  ('students:course_access:approve')
on conflict (scope) do nothing;

delete from role_permissions rp
using roles r, permissions p
where rp.role_id = r.id
  and rp.permission_id = p.id
  and r.name = 'customer_success'
  and p.scope = 'students:write';

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('customer_success', 'programs_manager', 'business_support')
  and p.scope in ('payments:kajabi:read', 'payments:paystack:read')
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'business_support'
  and p.scope in ('payments:verify', 'students:course_access:grant')
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('customer_success', 'programs_manager')
  and p.scope in (
    'students:attendance:read',
    'students:assignments:read',
    'students:intervention:review'
  )
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'customer_success'
  and p.scope in ('students:attendance:write', 'students:course_access:request')
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'programs_manager'
  and p.scope in ('students:intervention:approve', 'students:course_access:approve')
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'ceo'
  and p.scope in (
    'payments:kajabi:read',
    'payments:paystack:read',
    'payments:verify',
    'students:attendance:read',
    'students:attendance:write',
    'students:assignments:read',
    'students:intervention:review',
    'students:intervention:approve',
    'students:course_access:request',
    'students:course_access:grant',
    'students:course_access:approve'
  )
on conflict do nothing;