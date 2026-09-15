-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0008_enrollment_operations.sql

alter table batch_execution_results
  add column if not exists queue_status text not null default 'new',
  add column if not exists assigned_user_id uuid references auth.users(id) on delete set null,
  add column if not exists follow_up_status text not null default 'not_started',
  add column if not exists follow_up_at timestamptz;

alter table batch_retries
  add column if not exists next_attempt_at timestamptz;

-- Keep the earliest ledger row if 0007 was exercised more than once before
-- idempotency was added. This makes the unique index safe on the live database.
delete from batch_execution_results duplicate
using batch_execution_results keeper
where duplicate.approval_id = keeper.approval_id
  and duplicate.contact_id = keeper.contact_id
  and duplicate.id > keeper.id;

create unique index if not exists batch_execution_results_approval_contact_uidx
  on batch_execution_results(approval_id, contact_id);
create index if not exists batch_execution_results_assignment_idx
  on batch_execution_results(assigned_user_id, queue_status);
create index if not exists batch_retries_due_idx
  on batch_retries(status, next_attempt_at);

create table if not exists enrollment_audit_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete restrict,
  result_id uuid references batch_execution_results(id) on delete set null,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists enrollment_audit_events_result_idx
  on enrollment_audit_events(result_id, created_at desc);
create index if not exists enrollment_audit_events_type_idx
  on enrollment_audit_events(event_type, created_at desc);

alter table enrollment_audit_events enable row level security;

drop policy if exists "Users can view their enrollment audit events" on enrollment_audit_events;
create policy "Users can view their enrollment audit events"
on enrollment_audit_events for select
using (auth.uid() = user_id);

drop policy if exists "Users can create their enrollment audit events" on enrollment_audit_events;
create policy "Users can create their enrollment audit events"
on enrollment_audit_events for insert
with check (auth.uid() = user_id);

-- Verify the live schema after applying this migration:
-- select table_name, column_name
-- from information_schema.columns
-- where table_name in ('batch_execution_results', 'batch_retries', 'enrollment_audit_events')
-- order by table_name, ordinal_position;
