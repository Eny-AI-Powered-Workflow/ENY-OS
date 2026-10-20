-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0048_creative_ai_assessment_access.sql

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
join permissions p on p.scope = 'design:ai'
where r.name in ('videographer', 'marketing', 'marketing_lead')
on conflict do nothing;
