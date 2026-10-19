-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0046_ai_message_context_scopes.sql

alter table ai_messages
  add column if not exists context_scopes jsonb not null default '[]'::jsonb;

-- Before scopes were recorded, every chat received CRM contact context.
-- Require current CRM permissions before exposing any legacy assistant reply.
update ai_messages
set context_scopes = '["leads:read", "pipeline:read"]'::jsonb
where role = 'assistant'
  and context_scopes = '[]'::jsonb;
