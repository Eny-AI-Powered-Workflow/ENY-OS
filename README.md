<!-- /home/obed/Documents/Eny_consulting/README.md -->

001. Next step in line for my phase 1 and2, will be ugrading soonest

# ENY Consulting Platform

Unified RBAC platform: one login, one permission system. Agents and tools
mount as modules instead of separate apps and URLs.

See `ROADMAP.md` for the full phase-by-phase build plan and `CLAUDE.md` for
AI coding tool instructions (also mirrored at `.github/copilot-instructions.md`).

## Local setup (Phase 1)

1. Backend: `cd backend && cp .env.example .env` (fill in Supabase URL, JWT
   secret, service role key, Claude key -- GHL/n8n keys can wait, mock
   fallbacks cover them for now), then:

   Qs I'm still in the dev mode, will maek everything fall in place

       pip install -r requirements.txt
       uvicorn app.main:app --reload

2. Apply the RBAC schema: run `supabase/migrations/0001_init_rbac.sql` in
   the Supabase SQL editor (or `supabase db push` if you're using the CLI).

   To enable the existing Student Success API for Customer Success and
   explicitly grant CEO access to all current Customer Success scopes, apply
   `supabase/migrations/0031_customer_success_rbac.sql` after the earlier
   migrations have been applied in order. Verify the grants with seeded roles
   in a non-production Supabase project before rollout.

   Migration `supabase/migrations/0032_programs_manager_student_read.sql`
   grants Programs & Operations the existing read-only `students:read` scope
   needed for Student Success oversight. Apply it after 0031 and verify the
   role grant in non-production before using the Student Success API.

   For Marketing phases 9–12, apply the next unapplied migrations in order:
   `supabase/migrations/0022_marketing_video_analytics.sql` and
   `supabase/migrations/0023_marketing_governance_reporting.sql`. Configure
   provider credentials in the backend environment only; see
   `backend/.env.example` for Whisper, private media storage, optional Canva,
   GHL email consent, and reporting thresholds. `OPENAI_API_KEY` enables both
   embeddings and Whisper transcription. Email scheduling requires
   `GHL_MARKETING_CONSENT_FIELD_ID` to identify a GHL custom field that contains
   an explicit opt-in value.

   The Graphic & Funnel Designer foundation uses
   `supabase/migrations/0024_graphic_designer_foundation.sql`. It adds the
   `graphic_designer` role and audience-scoped design permissions. Assign the
   role through the existing Supabase RBAC/user-role workflow; no new API keys
   or provider setup are required for phases 1–2. To grant a user this role,
   add `graphic_designer` to that user's Supabase Auth `user_metadata.roles`
   array; the existing backend token sync adds the corresponding `user_roles`
   row at their next authenticated request. Start with
   `GRAPHIC_DESIGN_FOUNDATION_TEMPLATE.md` and enter only approved source
   material in the Designer workspace. For Designer requests, private asset
   files, and manual template production, apply
   `supabase/migrations/0025_design_requests_assets_templates.sql` after 0024.
   `SUPABASE_DESIGN_ASSET_BUCKET` (default `design-assets`) and
   `DESIGN_ASSET_MAX_UPLOAD_MB` (default `50`) are optional backend settings;
   they are not secrets. Storage access uses the existing Supabase service-role
   key on the backend only. Canva API credentials are not needed for this
   manual-template phase; store approved Canva template links in the workspace.

3. Seed test users, one per role:

       python scripts/seed_dev_data.py

4. Frontend: `cd frontend && cp .env.local.example .env.local`, then:

       npm install
       npm run dev

5. Log in at `/login` as any seeded user (password: `EnyTest!2026`) and
   confirm the dashboard nav and `/dashboard/leads` behave differently by role.

6. n8n (only needed from Phase 3 onward): `docker compose up n8n`

   For a Render-hosted n8n service, add the environment variable
   `N8N_PROXY_HOPS=1` and redeploy. Render terminates the public proxy and
   forwards `X-Forwarded-For`; this setting lets n8n and express-rate-limit
   trust that single proxy hop.

   The Enrollment follow-up workflow reads its GHL configuration from n8n
   environment variables. Also set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`,
   `GHL_BASE_URL`, `GHL_LOCATION_ID`, `GHL_PRIVATE_TOKEN`, and
   `GHL_NOTIFICATION_FROM_EMAIL` in the n8n service, then redeploy n8n.
    