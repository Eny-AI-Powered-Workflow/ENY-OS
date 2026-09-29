-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0032_programs_manager_student_read.sql

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('programs_manager', 'ceo')
  and p.scope = 'students:read'
on conflict do nothing;