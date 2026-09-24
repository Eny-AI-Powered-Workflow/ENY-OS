-- /home/obed/Documents/Eny_consulting/supabase/migrations/0015_executive_assistant_permissions.sql

insert into permissions (scope) values
  ('assistant:briefing:read'),
  ('assistant:briefing:write')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('ceo', 'executive_assistant')
  and p.scope in ('assistant:briefing:read', 'assistant:briefing:write')
on conflict do nothing;

comment on table permissions is 'EA briefing scopes are intentionally separate from generic AI chat and workflow trigger permissions.';
