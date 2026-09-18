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
    