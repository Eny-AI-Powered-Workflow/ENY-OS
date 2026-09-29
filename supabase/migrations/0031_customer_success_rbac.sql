-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0031_customer_success_rbac.sql

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'customer_success'
  and p.scope in ('students:read', 'students:write')
on conflict do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'ceo'
  and p.scope in (
    'students:read',
    'students:write',
    'design:workspace',
    'design:read_programs',
    'design:request'
  )
on conflict do nothing;