-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0034_business_support_phase_one_two_rbac.sql

-- Add only the read-only landing permission for the future Business Support module.
insert into permissions (scope)
values ('business_support:dashboard:read')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('business_support', 'ceo')
  and p.scope = 'business_support:dashboard:read'
on conflict do nothing;