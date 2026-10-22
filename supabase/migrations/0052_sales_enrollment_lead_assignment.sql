-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0052_sales_enrollment_lead_assignment.sql
insert into roles (name) values ('sales_lead'), ('enrollment_lead')
on conflict (name) do nothing;

insert into permissions (scope)
values ('sales:leads:assign'), ('enrollment:leads:assign')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where (r.name = 'sales_lead' and p.scope in ('leads:read', 'leads:write', 'pipeline:read', 'sales:leads:assign'))
   or (r.name = 'enrollment_lead' and p.scope in ('leads:read', 'leads:write', 'pipeline:read', 'enrollment:leads:assign'))
   or (r.name = 'ceo' and p.scope in ('sales:leads:assign', 'enrollment:leads:assign'))
on conflict do nothing;

alter table batch_execution_results
  add column if not exists assigned_department text;

create index if not exists batch_execution_results_department_assignment_idx
  on batch_execution_results(assigned_department, assigned_user_id, queue_status);

update batch_execution_results result
set assigned_department = 'sales'
where result.assigned_user_id is not null
  and result.assigned_department is null
  and exists (
    select 1
    from user_roles ur
    join roles r on r.id = ur.role_id
    where ur.user_id = result.assigned_user_id
      and r.name in ('sales', 'sales_lead')
  )
  and not exists (
    select 1
    from user_roles ur
    join roles r on r.id = ur.role_id
    where ur.user_id = result.assigned_user_id
      and r.name in ('enrollment', 'enrollment_lead')
  );

update batch_execution_results result
set assigned_department = 'enrollment'
where result.assigned_user_id is not null
  and result.assigned_department is null
  and exists (
    select 1
    from user_roles ur
    join roles r on r.id = ur.role_id
    where ur.user_id = result.assigned_user_id
      and r.name in ('enrollment', 'enrollment_lead')
  )
  and not exists (
    select 1
    from user_roles ur
    join roles r on r.id = ur.role_id
    where ur.user_id = result.assigned_user_id
      and r.name in ('sales', 'sales_lead')
  );
