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

   Migration `supabase/migrations/0033_customer_success_least_privilege.sql`
   replaces Customer Success' unused broad `students:write` grant with
   operation-specific scopes and adds provider-specific payment-read scopes.
   Apply it after 0032. Kajabi and Paystack credentials belong only in the
   backend environment; configure them from `backend/.env.example`. Kajabi
   reads are site-filtered by `KAJABI_SITE_ID` and Paystack results are limited
   to provider-reported NGN transactions. For the Student Success roster, set
   `KAJABI_CLIENT_ID`, `KAJABI_CLIENT_SECRET`, and `KAJABI_SITE_ID`; configure
   `PAYSTACK_SECRET_KEY`; and set
   `CUSTOMER_SUCCESS_SHEETS_SERVICE_ACCOUNT_JSON`,
   `CUSTOMER_SUCCESS_PROGRAM_SHEET_ID`, and
   `CUSTOMER_SUCCESS_PROGRAM_SHEET_RANGE`. Grant that service account viewer
   access to the Program Sheet. Its spreadsheet ID and service-account JSON
   must remain in backend-managed environment secrets, never in the frontend
   or source control.

   For Marketing phases 9–12, apply the next unapplied migrations in order:
   `supabase/migrations/0022_marketing_video_analytics.sql` and
   `supabase/migrations/0023_marketing_governance_reporting.sql`. Configure
   provider credentials in the backend environment only; see
   `backend/.env.example` for Whisper, private media storage, optional Canva,
   GHL email consent, and reporting thresholds. `OPENAI_API_KEY` enables both
   embeddings and Whisper transcription. Email scheduling requires
   `GHL_MARKETING_CONSENT_FIELD_ID` to identify a GHL custom field that contains
   an explicit opt-in value. The Render backend build installs FFmpeg; it is
   required to extract audio from uploaded videos before Whisper transcription.

   The Graphic & Funnel Designer foundation uses
   `supabase/migrations/0024_graphic_designer_foundation.sql`. It adds the
   `graphic_designer` role and audience-scoped design permissions. After
   applying `supabase/migrations/0042_ceo_user_management.sql`, the CEO assigns
   this and other non-CEO roles from CEO Cockpit → Accounts and role approvals.
   Roles are authoritative in `user_roles`; do not put them in user-editable
   Supabase Auth metadata. Start with
   `GRAPHIC_DESIGN_FOUNDATION_TEMPLATE.md` and enter only approved source
   material in the Designer workspace. For Designer requests, private asset
   files, and manual template production, apply
   `supabase/migrations/0025_design_requests_assets_templates.sql` after 0024.
   `SUPABASE_DESIGN_ASSET_BUCKET` (default `design-assets`) and
   `DESIGN_ASSET_MAX_UPLOAD_MB` (default `50`) are optional backend settings;
   they are not secrets. Storage access uses the existing Supabase service-role
   key on the backend only. Canva API credentials are not needed for this
   manual-template phase; store approved Canva template links in the workspace.

   Google sign-in also creates new Supabase Auth accounts. In Supabase
   Authentication → Providers, enable Google and enter the OAuth client ID and
   secret from Google Cloud Console. Add the Supabase Google callback URL shown
   in that provider's settings (usually
   `https://<project-ref>.supabase.co/auth/v1/callback`) to the Google OAuth
   client's authorized redirect URIs. In Supabase Authentication → URL
   Configuration, set **Site URL** to the canonical production frontend origin
   (for example, `https://eny-os.vercel.app`) and add the exact
   `https://<production-host>/auth/callback` URL under **Redirect URLs**. Add
   `http://localhost:3000/auth/callback` there only for local development. Set
   Vercel's `NEXT_PUBLIC_SITE_URL` to the same canonical production origin
   without a trailing slash, then redeploy the frontend; the checked-in local
   example uses `http://localhost:3000`. Production Google sign-in fails
   explicitly if this variable is missing instead of silently redirecting to a
   development origin. The frontend uses PKCE for OAuth callbacks. After a
   first Google sign-in, accounts remain pending until the CEO assigns at least
   one role in CEO Cockpit.

   No new Render environment variable is required: the backend already requires
   `SUPABASE_URL` and the server-only `SUPABASE_SERVICE_ROLE_KEY` in
   `backend/.env.example`; ensure both are set on the Render backend service.
   Never put the service-role key in frontend/`NEXT_PUBLIC_*` variables. The
   frontend continues to use `NEXT_PUBLIC_SUPABASE_URL`,
   `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `NEXT_PUBLIC_API_URL`.

   To enable the shared Canva Connect account, apply the next unapplied
   migrations `0039_design_system_document_provider.sql`,
   `0040_shared_canva_connection.sql`, and
   `0041_canva_oauth_return_url.sql` in order. Set
   `CANVA_CLIENT_ID`, `CANVA_CLIENT_SECRET`, `CANVA_TOKEN_ENCRYPTION_KEY`,
   `CANVA_REDIRECT_URI`, and `CANVA_OAUTH_SCOPES` in the backend Render
   environment. `CANVA_REDIRECT_URI` must point to the backend, not the Vercel
   frontend root. Register the exact callback URL in Canva Developers; the
   suggested Render callback is
   `https://eny-consulting-backend.onrender.com/api/v1/canva/oauth/callback`.
   Canva must return first to the backend callback above so FastAPI can exchange
   and save the tokens. FastAPI then returns the popup to
   `/canva/oauth-complete` on the approved frontend origin; the opener refreshes
   `/canva/status` and remains on `/dashboard/videographer`.
   The API checks this origin against `BACKEND_CORS_ORIGINS`, `ALLOWED_ORIGINS`,
   or `CORS_ORIGIN_REGEX`; include the deployed frontend origin there.
   `CANVA_POST_CONNECT_REDIRECT` remains a fallback for OAuth states created
   before this return URL change.
   Generate `CANVA_TOKEN_ENCRYPTION_KEY` using Fernet and preserve it across
   deployments, since changing it makes stored tokens undecryptable. Tokens are
   encrypted in a single shared database connection row and are never returned
   by the browser-facing API.

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

   The shared, read-only Google Calendar & Tasks workspace uses backend-only
   OAuth credentials. Apply
   `supabase/migrations/0039_shared_calendar_read_permissions.sql` after 0038.
   Add `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and
   `GOOGLE_OAUTH_REFRESH_TOKEN` to the backend's Render environment. The
   refresh token must be issued for both
   `https://www.googleapis.com/auth/calendar.events.readonly` and
   `https://www.googleapis.com/auth/tasks.readonly`; do not use a short-lived
   access token or an OAuth Playground refresh token. For an external OAuth
   consent screen, publish the app rather than leaving it in Testing (testing
   refresh tokens expire after seven days). The Calendar UI and API grant read
   access to the CEO, Executive Assistant, Marketing, and Marketing Lead roles
   only.

   The Enrollment follow-up workflow reads its GHL configuration from n8n
   environment variables. Also set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`,
   `GHL_BASE_URL`, `GHL_LOCATION_ID`, `GHL_PRIVATE_TOKEN`, and
   `GHL_NOTIFICATION_FROM_EMAIL` in the n8n service, then redeploy n8n.
    