-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0051_security_rls.sql
-- Keep RBAC tables inaccessible to anonymous clients and prevent self-service role changes.
alter table roles enable row level security;
alter table permissions enable row level security;
alter table role_permissions enable row level security;
alter table user_roles enable row level security;

revoke all on roles, permissions, role_permissions, user_roles from public, anon;
revoke insert, update, delete, truncate, references, trigger
  on roles, permissions, role_permissions, user_roles from authenticated;
grant select on roles, permissions, role_permissions to authenticated;
grant select on user_roles to authenticated;
grant all on roles, permissions, role_permissions, user_roles to service_role;

drop policy if exists "authenticated users can read roles" on roles;
create policy "authenticated users can read roles"
  on roles for select to authenticated using (true);

drop policy if exists "authenticated users can read permissions" on permissions;
create policy "authenticated users can read permissions"
  on permissions for select to authenticated using (true);

drop policy if exists "authenticated users can read role permissions" on role_permissions;
create policy "authenticated users can read role permissions"
  on role_permissions for select to authenticated using (true);

drop policy if exists "users can read their own role assignments" on user_roles;
create policy "users can read their own role assignments"
  on user_roles for select to authenticated using (user_id = auth.uid());

revoke all on audit_logs from public, anon;
revoke insert, update, delete, truncate, references, trigger on audit_logs from authenticated;
grant select on audit_logs to authenticated;
grant all on audit_logs to service_role;
