-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0037_business_support_contract_status_read.sql

insert into permissions (scope)
values ('business_support:contracts:read')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('business_support', 'ceo', 'programs_manager')
  and p.scope = 'business_support:contracts:read'
on conflict do nothing;-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0037_business_support_contract_status_read.sql

insert into permissions (scope)
values ('business_support:contracts:read')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('business_support', 'ceo', 'programs_manager')
  and p.scope = 'business_support:contracts:read'
on conflict do nothing;