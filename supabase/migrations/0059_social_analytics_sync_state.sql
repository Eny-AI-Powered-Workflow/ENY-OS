-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0059_social_analytics_sync_state.sql

create table if not exists social_analytics_sync_state (
  ghl_location_id text primary key,
  last_attempted_at timestamptz not null,
  last_success_at timestamptz,
  last_error text,
  last_period_days integer,
  accounts_synced integer not null default 0,
  posts_processed integer not null default 0,
  metrics_recorded integer not null default 0,
  updated_by uuid not null references auth.users(id) on delete restrict,
  updated_at timestamptz not null default now()
);

alter table social_analytics_sync_state enable row level security;

create policy "Authenticated users can view social analytics sync state"
  on social_analytics_sync_state for select using (auth.uid() is not null);
