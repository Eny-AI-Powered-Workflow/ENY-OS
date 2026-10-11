-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0039_design_system_document_provider.sql

alter table design_system_documents
  add column if not exists provider text not null default 'manual_upload';
