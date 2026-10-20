-- /home/obed/Documents/Eny_consulting/Eny_consulting/supabase/migrations/0050_qualify_knowledge_vector_operator.sql

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
    1 - (kd.embedding OPERATOR(extensions.<=>) query_embedding) as similarity
  from knowledge_documents kd
  where kd.is_active = true
    and kd.embedding is not null
    and kd.department = any(match_roles)
  order by kd.embedding OPERATOR(extensions.<=>) query_embedding
  limit match_count;
$$;
