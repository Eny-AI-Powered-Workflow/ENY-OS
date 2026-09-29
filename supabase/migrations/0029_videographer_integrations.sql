-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0029_videographer_integrations.sql

alter table marketing_video_assets
  add column if not exists team text not null default 'marketing',
  add column if not exists audience text not null default 'marketing';

create index if not exists marketing_video_assets_team_audience_idx
  on marketing_video_assets(team, audience, created_at desc);

-- Videographers may connect their own Canva account for approved supporting graphics.
insert into role_permissions (role_id, permission_id)
select r.id, p.id
from roles r
cross join permissions p
where r.name = 'videographer'
  and p.scope = 'design:canva'
on conflict do nothing;