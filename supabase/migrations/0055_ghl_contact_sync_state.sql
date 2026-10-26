-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0055_ghl_contact_sync_state.sql
create table if not exists ghl_contact_sync_state (
  id integer primary key check (id = 1),
  cursor_id text,
  cursor_after text,
  status text not null default 'idle',
  cycle_cutoff_at timestamptz,
  last_run_at timestamptz,
  last_success_at timestamptz,
  contacts_scanned integer not null default 0,
  contacts_queued integer not null default 0,
  updated_at timestamptz not null default now()
);

alter table ghl_contact_sync_state enable row level security;
revoke all on ghl_contact_sync_state from public, anon, authenticated;
grant all on ghl_contact_sync_state to service_role;
