-- /home/obed/Documents/Eny_consulting/supabase/migrations/0016_ea_coordination_research.sql

insert into permissions (scope) values
  ('assistant:automation:trigger'),
  ('assistant:research:write')
on conflict (scope) do nothing;

insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name in ('ceo', 'executive_assistant')
  and p.scope in ('assistant:automation:trigger', 'assistant:research:write')
on conflict do nothing;

create table if not exists ea_research_briefs (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  source_url text not null,
  summary text not null,
  confidence text not null default 'unverified',
  status text not null default 'draft',
  requires_approval boolean not null default true,
  created_by uuid not null references auth.users(id) on delete restrict,
  reviewed_by uuid references auth.users(id) on delete set null,
  review_note text,
  created_at timestamptz not null default now(),
  reviewed_at timestamptz
);

create index if not exists ea_research_briefs_status_idx
  on ea_research_briefs(status, created_at desc);

alter table ea_research_briefs enable row level security;

drop policy if exists "EA users can view research briefs" on ea_research_briefs;
create policy "EA users can view research briefs"
on ea_research_briefs for select
using (auth.uid() is not null);

drop policy if exists "EA users can create research briefs" on ea_research_briefs;
create policy "EA users can create research briefs"
on ea_research_briefs for insert
with check (auth.uid() = created_by);

drop policy if exists "EA users can review research briefs" on ea_research_briefs;
create policy "EA users can review research briefs"
on ea_research_briefs for update
using (auth.uid() is not null)
with check (auth.uid() is not null);
