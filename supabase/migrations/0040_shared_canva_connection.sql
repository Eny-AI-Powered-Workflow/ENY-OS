-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0040_shared_canva_connection.sql

-- Retain the most recently updated connection from earlier per-user deployments.
delete from canva_connections older
using canva_connections newer
where older.updated_at < newer.updated_at
   or (older.updated_at = newer.updated_at and older.id < newer.id);

alter table canva_connections
  drop constraint if exists canva_connections_user_id_key,
  drop constraint if exists canva_connections_user_id_fkey,
  alter column user_id drop not null;

alter table canva_connections
  add constraint canva_connections_user_id_fkey
    foreign key (user_id) references auth.users(id) on delete set null,
  add column shared_slot smallint not null default 1,
  add constraint canva_connections_shared_slot_check check (shared_slot = 1),
  add constraint canva_connections_shared_slot_key unique (shared_slot);
