-- /home/obed/Documents/Eny_consulting/supabase/migrations/0012_batch_operating_policy.sql

alter table cohort_approvals
  add column if not exists decision text not null default 'approved',
  add column if not exists decision_reason text,
  add column if not exists decided_by uuid references auth.users(id) on delete set null,
  add column if not exists decided_at timestamptz;

alter table batch_execution_results
  add column if not exists operating_decision text not null default 'hold',
  add column if not exists failure_class text,
  add column if not exists recovery_owner_id uuid references auth.users(id) on delete set null,
  add column if not exists recovery_status text not null default 'unassigned';

alter table batch_retries
  add column if not exists failure_class text,
  add column if not exists recovery_owner_id uuid references auth.users(id) on delete set null,
  add column if not exists operating_decision text not null default 'hold';

update cohort_approvals
set decision = 'approved',
    decided_at = coalesce(decided_at, created_at)
where status in ('approved_for_scoring', 'executing', 'completed', 'completed_with_failures', 'failed')
  and decision = 'approved';

update batch_execution_results
set operating_decision = 'rerun',
    recovery_status = 'assigned'
where status = 'failed'
  and operating_decision = 'hold';

create index if not exists batch_execution_results_policy_idx
  on batch_execution_results(status, operating_decision, recovery_status, failure_class);
create index if not exists batch_retries_policy_idx
  on batch_retries(status, operating_decision, next_attempt_at);

comment on column cohort_approvals.decision is 'Approval policy decision: approved, rejected, held, or escalated.';
comment on column batch_execution_results.operating_decision is 'Recovery decision: rerun, hold, or escalate.';
comment on column batch_execution_results.failure_class is 'Controlled failure category used to route recovery ownership.';
