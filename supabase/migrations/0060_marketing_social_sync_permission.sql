-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0060_marketing_social_sync_permission.sql

insert into permissions (scope)
values ('marketing:social:sync')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('ceo', 'marketing', 'marketing_lead')
  and p.scope = 'marketing:social:sync'
on conflict do nothing;
