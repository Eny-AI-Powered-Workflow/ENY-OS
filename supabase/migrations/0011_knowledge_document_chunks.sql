-- /home/obed/Documents/Eny_consulting/supabase/migrations/0011_knowledge_document_chunks.sql

-- A single SOP can contain multiple vector chunks with the same title and department.
-- Keep replacement scoped by title + department in the API instead of enforcing
-- uniqueness on every chunk row.
drop index if exists knowledge_documents_title_department_idx;

create index if not exists knowledge_documents_title_department_idx
  on knowledge_documents(title, department);
