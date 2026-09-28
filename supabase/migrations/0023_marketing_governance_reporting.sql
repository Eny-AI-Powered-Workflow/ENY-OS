-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0023_marketing_governance_reporting.sql

alter table marketing_content_items
  add column if not exists requires_ceo_approval boolean not null default false,
  add column if not exists compliance_flags jsonb not null default '[]'::jsonb;

alter table marketing_video_assets
  add column if not exists duration_seconds integer;

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'marketing_metric_observations' and column_name = 'metadata'
  ) and not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'marketing_metric_observations' and column_name = 'metadata_json'
  ) then
    alter table marketing_metric_observations rename column metadata to metadata_json;
  else
    alter table marketing_metric_observations add column if not exists metadata_json jsonb not null default '{}'::jsonb;
  end if;
end $$;

create table if not exists marketing_content_versions (
  id uuid primary key default gen_random_uuid(),
  content_id uuid not null references marketing_content_items(id) on delete cascade,
  revision integer not null,
  snapshot jsonb not null,
  change_note text not null,
  changed_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique (content_id, revision)
);

create table if not exists marketing_weekly_reviews (
  id uuid primary key default gen_random_uuid(),
  week_start date not null,
  summary text not null,
  decisions jsonb not null default '[]'::jsonb,
  metrics_snapshot jsonb not null default '{}'::jsonb,
  attendees jsonb not null default '[]'::jsonb,
  completed_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique (week_start)
);

create index if not exists marketing_content_versions_history_idx on marketing_content_versions(content_id, revision desc);
create index if not exists marketing_weekly_reviews_week_idx on marketing_weekly_reviews(week_start desc);

alter table marketing_content_versions enable row level security;
alter table marketing_weekly_reviews enable row level security;

create policy "Authenticated users can view Marketing content versions" on marketing_content_versions for select using (auth.uid() is not null);
create policy "Authenticated users can create Marketing content versions" on marketing_content_versions for insert with check (auth.uid() = changed_by);
create policy "Authenticated users can view Marketing weekly reviews" on marketing_weekly_reviews for select using (auth.uid() is not null);
create policy "Authenticated users can create Marketing weekly reviews" on marketing_weekly_reviews for insert with check (auth.uid() = completed_by);
