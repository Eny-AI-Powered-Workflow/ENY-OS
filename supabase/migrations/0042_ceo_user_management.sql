-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0042_ceo_user_management.sql
-- Restrict account-role assignment to users with the CEO role.
insert into permissions (scope)
values ('users:manage')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'ceo'
  and p.scope = 'users:manage'
on conflict do nothing;
