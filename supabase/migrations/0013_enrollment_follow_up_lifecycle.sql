-- /home/obed/Documents/Eny_consulting/supabase/migrations/0013_enrollment_follow_up_lifecycle.sql

alter table batch_execution_results
  add column if not exists lifecycle_stage text not null default 'not_started',
  add column if not exists next_step text,
  add column if not exists response_at timestamptz,
  add column if not exists booked_at timestamptz,
  add column if not exists enrollment_outcome text,
  add column if not exists lifecycle_updated_at timestamptz;

update batch_execution_results
set lifecycle_stage = case
  when follow_up_status = 'tagged' then 'queued'
  when follow_up_status = 'failed' then 'failed'
  else 'not_started'
end,
    lifecycle_updated_at = coalesce(lifecycle_updated_at, follow_up_at, updated_at, created_at)
where lifecycle_stage = 'not_started';

create index if not exists batch_execution_results_lifecycle_idx
  on batch_execution_results(lifecycle_stage, response_at, booked_at);

comment on column batch_execution_results.lifecycle_stage is 'Enrollment follow-up lifecycle: not_started, queued, outreach_sent, responded, next_step, booked, enrolled, lost, or failed.';
comment on column batch_execution_results.next_step is 'The agreed next action after a lead response.';
comment on column batch_execution_results.enrollment_outcome is 'Final enrollment outcome recorded by the team.';
