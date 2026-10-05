-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0038_ai_chat_all_roles.sql

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where p.scope = 'ai:chat'
on conflict do nothing;
