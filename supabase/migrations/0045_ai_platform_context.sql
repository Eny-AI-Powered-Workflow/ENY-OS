-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0045_ai_platform_context.sql

insert into permissions (scope)
values ('knowledge:read_all'), ('platform:read')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'ceo'
  and p.scope in ('knowledge:read_all', 'platform:read')
on conflict do nothing;
