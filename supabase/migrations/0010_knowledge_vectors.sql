-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0010_knowledge_vectors.sql

create extension if not exists vector with schema extensions;

alter table knowledge_documents
  add column if not exists embedding extensions.vector(1536),
  add column if not exists metadata jsonb not null default '{}'::jsonb;

create index if not exists knowledge_documents_embedding_idx
  on knowledge_documents using ivfflat (embedding extensions.vector_cosine_ops)
  with (lists = 50);

create or replace function match_knowledge_documents(
  query_embedding extensions.vector(1536),
  match_roles text[],
  match_count integer default 5
)
returns table (
  id uuid,
  title text,
  department text,
  content text,
  source text,
  metadata jsonb,
  similarity double precision
)
language sql
stable
as $$
  select
    kd.id,
    kd.title,
    kd.department,
    kd.content,
    kd.source,
    kd.metadata,
    1 - (kd.embedding <=> query_embedding) as similarity
  from knowledge_documents kd
  where kd.is_active = true
    and kd.embedding is not null
    and kd.department = any(match_roles)
  order by kd.embedding <=> query_embedding
  limit match_count;
$$;
