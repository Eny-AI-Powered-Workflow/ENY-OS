-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0049_ai_action_approval_permissions.sql

insert into permissions (scope) values
  ('assistant:actions:propose'),
  ('assistant:actions:approve'),
  ('assistant:actions:execute')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('ceo', 'programs_manager', 'customer_success')
  and p.scope in (
    'assistant:actions:propose',
    'assistant:actions:approve',
    'assistant:actions:execute'
  )
on conflict do nothing;
