-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0022_marketing_video_analytics.sql

create table if not exists marketing_video_assets (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  original_filename text not null,
  mime_type text not null,
  size_bytes bigint not null,
  storage_path text not null unique,
  status text not null default 'uploaded',
  transcript text,
  duration_seconds integer,
  transcript_segments jsonb not null default '[]'::jsonb,
  transcript_provider text,
  generated_outputs jsonb not null default '[]'::jsonb,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists marketing_metric_observations (
  id uuid primary key default gen_random_uuid(),
  metric_key text not null,
  metric_value numeric not null,
  campaign_name text,
  channel text,
  provider text not null,
  source text not null,
  observed_at timestamptz not null,
  metadata_json jsonb not null default '{}'::jsonb,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now()
);

create index if not exists marketing_video_assets_status_idx on marketing_video_assets(status, created_at desc);
create index if not exists marketing_metric_observations_metric_idx on marketing_metric_observations(metric_key, observed_at desc);
create index if not exists marketing_metric_observations_campaign_idx on marketing_metric_observations(campaign_name, observed_at desc);

alter table marketing_video_assets enable row level security;
alter table marketing_metric_observations enable row level security;

create policy "Authenticated users can view Marketing video assets" on marketing_video_assets for select using (auth.uid() is not null);
create policy "Authenticated users can view Marketing metric observations" on marketing_metric_observations for select using (auth.uid() is not null);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'marketing-video',
  'marketing-video',
  false,
  262144000,
  array['video/mp4', 'video/webm', 'video/quicktime', 'audio/mpeg', 'audio/mp4', 'audio/wav', 'audio/webm']
)
on conflict (id) do update set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
