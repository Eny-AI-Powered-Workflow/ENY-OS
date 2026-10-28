-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0058_ghl_social_analytics.sql

alter table social_posts
  drop constraint if exists social_posts_platform_check;

alter table social_posts
  add constraint social_posts_platform_check
  check (platform in ('linkedin', 'instagram', 'facebook', 'x', 'tiktok', 'youtube', 'pinterest'));

create table if not exists social_accounts (
  id uuid primary key default gen_random_uuid(),
  ghl_location_id text not null,
  platform text not null check (platform in ('linkedin', 'instagram', 'facebook', 'x', 'tiktok', 'youtube', 'pinterest')),
  external_account_id text not null,
  display_name text not null,
  account_type text,
  active boolean not null default true,
  is_expired boolean not null default false,
  metadata_json jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint social_accounts_external_identity_key
    unique (ghl_location_id, platform, external_account_id)
);

create index if not exists social_accounts_location_platform_idx
  on social_accounts(ghl_location_id, platform, active);

alter table social_accounts enable row level security;

create policy "Authenticated users can view social accounts"
  on social_accounts for select using (auth.uid() is not null);
