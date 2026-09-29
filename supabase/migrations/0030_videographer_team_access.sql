-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0030_videographer_team_access.sql

insert into permissions (scope) values
  ('video:team:read:videographer'),
  ('video:team:read:marketing'),
  ('video:team:read:programs'),
  ('video:team:read:student_success')
on conflict (scope) do nothing;

-- The Videographer role can work only with its department's assets.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'videographer'
  and p.scope = 'video:team:read:videographer'
on conflict do nothing;

-- Marketing staff can access Marketing video assets, not other department libraries.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('marketing', 'marketing_lead')
  and p.scope = 'video:team:read:marketing'
on conflict do nothing;

-- CEO has cross-department video visibility.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'ceo'
  and p.scope like 'video:team:read:%'
on conflict do nothing;