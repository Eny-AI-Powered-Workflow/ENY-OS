-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0044_social_platform_analytics.sql

create table if not exists social_posts (
  id uuid primary key default gen_random_uuid(),
  platform text not null check (platform in ('linkedin', 'instagram', 'facebook', 'x', 'tiktok', 'youtube')),
  account_id text not null,
  external_post_id text not null,
  content_id uuid references marketing_content_items(id) on delete set null,
  delivery_id uuid references marketing_deliveries(id) on delete set null,
  text text,
  permalink text,
  media_type text,
  published_at timestamptz not null,
  metadata_json jsonb not null default '{}'::jsonb,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint social_posts_external_identity_key unique (platform, account_id, external_post_id)
);

create table if not exists social_metric_observations (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references social_posts(id) on delete cascade,
  metric_key text not null check (metric_key in (
    'impressions', 'reach', 'likes', 'comments', 'shares', 'saves', 'clicks',
    'views', 'watch_time_seconds'
  )),
  metric_value numeric not null check (metric_value >= 0),
  unit text not null default 'count',
  provider text not null,
  source text not null,
  observed_at timestamptz not null,
  metadata_json jsonb not null default '{}'::jsonb,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  constraint social_metric_observations_snapshot_key unique (post_id, metric_key, observed_at)
);

create index if not exists social_posts_platform_published_idx
  on social_posts(platform, published_at desc);
create index if not exists social_metric_observations_post_metric_idx
  on social_metric_observations(post_id, metric_key, observed_at desc);

alter table social_posts enable row level security;
alter table social_metric_observations enable row level security;

create policy "Authenticated users can view social posts"
  on social_posts for select using (auth.uid() is not null);
create policy "Authenticated users can view social metric observations"
  on social_metric_observations for select using (auth.uid() is not null);
