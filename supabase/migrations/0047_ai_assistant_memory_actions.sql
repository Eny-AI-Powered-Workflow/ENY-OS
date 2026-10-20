-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0047_ai_assistant_memory_actions.sql

create table if not exists ai_user_memory (
  user_id uuid primary key references auth.users(id) on delete cascade,
  preferences jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists ai_action_proposals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  workflow_name text not null,
  summary text not null,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'executing', 'rejected', 'executed', 'failed', 'expired')),
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  expires_at timestamptz not null,
  executed_at timestamptz,
  execution_result jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ai_action_proposals_user_status_idx
  on ai_action_proposals(user_id, status, created_at desc);
create index if not exists ai_action_proposals_expiry_idx
  on ai_action_proposals(status, expires_at);

alter table ai_user_memory enable row level security;
alter table ai_action_proposals enable row level security;

drop policy if exists "Users can manage own AI memory" on ai_user_memory;
create policy "Users can manage own AI memory" on ai_user_memory
  for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can read own AI action proposals" on ai_action_proposals;
create policy "Users can read own AI action proposals" on ai_action_proposals
  for select using (auth.uid() = user_id);

drop policy if exists "Users can create own AI action proposals" on ai_action_proposals;
create policy "Users can create own AI action proposals" on ai_action_proposals
  for insert with check (
    auth.uid() = user_id
    and status = 'pending'
    and approved_by is null
    and approved_at is null
    and executed_at is null
    and execution_result is null
  );
