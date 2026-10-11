-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0041_canva_oauth_return_url.sql

alter table canva_oauth_states
  add column if not exists post_connect_redirect text;
