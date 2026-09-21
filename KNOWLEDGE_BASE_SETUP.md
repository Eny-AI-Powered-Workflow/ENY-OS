<!-- /home/obed/Documents/Eny_consulting/Eny_consulting/KNOWLEDGE_BASE_SETUP.md -->
# ENY Knowledge Base Setup

## What This Is

ENY OS does not train or fine-tune Claude on the SOPs. It uses retrieval-augmented generation (RAG):

```text
SOP content
  -> chunks
  -> embeddings
  -> Supabase pgvector
  -> role-filtered semantic retrieval
  -> Claude prompt
  -> answer grounded in approved ENY knowledge
```

Claude remains the generation model. The embedding model converts text into vectors so semantically related SOP content can be found even when the user's wording does not exactly match the document.

## Activation Order

1. Apply `supabase/migrations/0010_knowledge_vectors.sql` after the existing migrations.
2. Add this Render backend variable:

```text
OPENAI_API_KEY=<embedding-provider-key>
EMBEDDING_MODEL=text-embedding-3-small
```

3. Redeploy the backend.
4. Confirm the authenticated caller has `agents:configure` before ingesting documents.
5. Ingest one small Sales SOP first.
6. Ask ENY AI Desk a question using the same topic and verify the answer cites or reflects the SOP.
7. Ingest the remaining department SOPs.

The API can operate without `OPENAI_API_KEY`; it falls back to the existing PostgreSQL full-text retrieval. Vector ingestion itself is intentionally disabled until an embedding key is configured.

## Ingesting an SOP

Use the protected endpoint through the backend. The endpoint requires `agents:configure`, so only the configured CEO/developer access path can load knowledge.

```bash
curl -X POST "$API_URL/api/v1/ai/knowledge/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sales Lead Qualification SOP",
    "department": "enrollment",
    "source": "ENY Sales handbook v1",
    "content": "Paste the approved SOP content here."
  }'
```

The service chunks long documents, embeds each chunk, replaces the prior document with the same title and department, and stores metadata such as chunk order and ingesting user.

Supported department values should match role scopes where possible:

```text
ceo
enrollment
programs_manager
customer_success
business_support
executive_assistant
developer
```

## What the AI Can See

A user only receives knowledge entries whose `department` matches one of the user's database roles. A Sales/Enrollment user can retrieve Enrollment knowledge; a Program Manager can retrieve Program Manager knowledge; a CEO can retrieve CEO knowledge.

Knowledge is reference material, not an instruction override. The AI prompt still tells Claude to treat retrieved text as data and to distinguish facts from assumptions.

## Verification Checklist

- Migration applied successfully.
- `vector` extension enabled.
- `knowledge_documents.embedding` exists.
- `match_knowledge_documents` exists.
- `OPENAI_API_KEY` is configured only in Render/Supabase-safe service configuration.
- Ingestion returns `status: ingested`.
- The document is scoped to the intended department.
- AI Desk uses the SOP for a matching question.
- A user in a different role cannot retrieve the department's knowledge.
- Existing AI chat still works when embeddings are unavailable through the full-text fallback.

## Security and Cost Rules

- Never put the embedding key in Markdown, Git, browser code, or an n8n workflow.
- Use the backend ingestion endpoint; do not expose embedding credentials to the frontend.
- Ingest approved, versioned SOP content only.
- Do not ingest passwords, tokens, private keys, unnecessary personal data, or raw CRM exports.
- Review embedding-provider usage and set a spending limit.
- Re-ingest a revised SOP using the same title and department so the old chunks are replaced.
- Keep the original SOP in the organization's document repository; Supabase stores the retrieval copy.
