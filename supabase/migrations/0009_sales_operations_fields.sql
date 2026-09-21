-- /home/obed/Documents/Eny_consulting/supabase/migrations/0009_sales_operations_fields.sql

alter table batch_execution_results
  add column if not exists score_origin text not null default 'approved_batch',
  add column if not exists notification_status text not null default 'not_attempted',
  add column if not exists notification_error text,
  add column if not exists notification_sent_at timestamptz,
  add column if not exists last_action_at timestamptz;

create index if not exists batch_execution_results_operations_filter_idx
  on batch_execution_results(queue_status, category, source, score);

-- Backfill the operational clock for existing rows without changing their state.
update batch_execution_results
set last_action_at = coalesce(last_action_at, updated_at, created_at)
where last_action_at is null;
