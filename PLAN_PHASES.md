# ENY Consulting Platform - Implementation Plan for Phases 1-3

Based on the current state of the repository and the defined roadmap, here is the implementation plan for Phases 1-3.

## Current State
- Backend structure has been initialized with:
  - RBAC models (Role, Permission, UserRole, RolePermission, AuditLog)
  - Database session and base configuration
  - Core security (JWT validation with Supabase)
  - Configuration management
  - Service clients for GHL, n8n, and Claude (with mock fallbacks)
  - API endpoints for auth, leads, pipeline, and agents
  - Main FastAPI application with CORS middleware
  - API router configuration
- Frontend structure needs to be created
- No frontend modules or components exist yet
- Database migrations exist (0001_init_rbac.sql) but need to be applied

## Phase 1: Auth & RBAC End-to-End
**Goal:** Prove one real logged-in user gets the correct role, sees only permitted modules, and every permission check is audited.

### Current Status:
- ✅ RBAC schema designed and migrated (0001_init_rbac.sql)
- ✅ `require_permission()` enforcement dependency created
- ✅ Service clients stubbed with mock fallbacks
- ❌ Role-gated dashboard shell in Next.js (not started)
- ❌ Docker-compose for local backend + n8n (not started)
- ❌ Test-user seed script (not started)
- ❌ Real Supabase session wired (frontend → backend)
- ❌ Mock-data fallback in ghl_service.py (partially done - needs completion)
- ❌ Audit log population verification (not tested)
- ❌ Role-based nav verification (not implemented)

### Remaining Tasks:
1. **Frontend Setup:**
   - Initialize Next.js app with TypeScript, TailwindCSS
   - Create authentication context using Supabase
   - Implement protected routes with role-based redirect

2. **Authentication Flow:**
   - Create login page (`/login`) using Supabase Auth
   - Implement session handling and token storage
   - Create auth context/provider for frontend

3. **RBAC Integration:**
   - Create `lib/permissions.ts` with MODULES array
   - Implement `can()` helper function for client-side checks
   - Build DashboardShell component with dynamic nav based on permissions
   - Create AccessBadge component to display user roles/permissions

4. **Testing & Verification:**
   - Create seed script for test users (one per role)
   - Verify audit logs populate for granted/denied permissions
   - Confirm each seeded role sees correct nav in `/dashboard`
   - Test role switching and session persistence

### Exit Criteria:
- Can log in as `enrollment@test.eny.dev` and `ceo@test.eny.dev` locally
- See different dashboards based on role
- See audit log entries for each permission check (grant/deny)

## Phase 2: GHL Integration Live
**Goal:** Replace mock leads with real GHL data.

### Current Status:
- ✅ GHL service client created with mock fallback
- ❌ Real GHL Private Integration Token + Location ID not registered
- ❌ Mock fallback not yet swapped for live GHLClient.get_contacts()
- ❌ Tag contact write path not implemented/tested
- ❌ Pipeline read endpoint not added

### Remaining Tasks:
1. **Environment Configuration:**
   - Obtain GHL Private Token and Location ID from client
   - Add to `.env` and `.env.example`
   - Verify connection to GHL API

2. **Service Implementation:**
   - Replace mock returns in `get_contacts()` with real API calls
   - Implement `get_contact()` for single contact retrieval
   - Implement `tag_contact()` with proper GHL API interaction
   - Implement `get_pipeline_data()` for opportunities/pipeline data
   - Add error handling and logging for all GHL operations

3. **API Endpoints:**
   - Complete `/leads` endpoint with proper filtering/pagination
   - Add `/leads/{contact_id}` endpoint for individual contact
   - Add `/leads/{contact_id}/tags` endpoint for tagging
   - Add `/pipeline` endpoint for pipeline data
   - Add `/pipeline/forecast` endpoint for revenue forecasting

4. **Testing:**
   - Verify real data flow from GHL → API → Frontend
   - Test tagging functionality in GHL UI
   - Validate pipeline data accuracy
   - Ensure error handling works correctly

### Exit Criteria:
- Leads/pipeline data coming from real GHL account
- Tag contact functionality working and visible in GHL
- Pipeline read endpoint returning real opportunity data
- Mock fallbacks removed or only used when credentials missing

## Phase 3: First Real Agent: Lead Scorer
**Goal:** Prove the full agent loop once, end to end — gateway → n8n → Claude → result → dashboard.

### Current Status:
- ✅ n8n service client created with mock fallback
- ✅ Claude service client created with lead scoring method
- ✅ Agents trigger endpoint created (`/agents/trigger/{workflow_name}`)
- ❌ ENY-SALES-SCORE workflow not built in n8n
- ❌ Webhook route not wired for lead-scorer
- ❌ "Hot Leads" card not added to dashboard
- ❌ Workflow JSON not exported/documentted

### Remaining Tasks:
1. **n8n Workflow Creation:**
   - Build ENY-SALES-SCORE workflow in n8n:
     - Trigger: Webhook (lead-scorer)
     - Node 1: Claude API call (lead scoring)
     - Node 2: GHL Contact update (add tags based on score)
     - Node 3: Slack notification (for hot leads)
   - Configure workflow to accept lead data and return score/tags
   - Set up error handling and logging

2. **Backend Integration:**
   - Wire `/api/v1/agents/trigger/lead-scorer` endpoint
   - Ensure endpoint requires `agents:trigger` permission
   - Pass lead data from GHL to n8n webhook
   - Store agent results in new `agent_logs` table (to be created)

3. **Database Enhancement:**
   - Add `agent_logs` table to track workflow executions
   - Fields: id, workflow_name, input_data, output_data, status, created_at
   - Enable RLS for appropriate role access

4. **Frontend Component:**
   - Create "Hot Leads" card component
   - Fetch scored leads from new endpoint (or enhanced leads endpoint)
   - Display lead name, score, tags, and recommended action
   - Refresh periodically or via webhook

5. **Testing & Verification:**
   - Trigger workflow manually via API endpoint
   - Verify Claude scoring logic with test data
   - Check GHL tags updated correctly
   - Confirm Slack notification sent for high-scoring leads
   - Validate dashboard displays scored leads accurately
   - Ensure audit logs capture permission checks

### Exit Criteria:
- n8n workflow triggers successfully from API endpoint
- Claude scores leads and returns actionable insights
- GHL contact tags updated based on score thresholds
- Results visible in Enrollment Dashboard "Hot Leads" card
- Full audit trail: permission check → workflow trigger → agent execution

## Notes:
- Phase 1 must be fully complete before starting Phase 2
- Phase 2 must be complete before starting Phase 3 (requires real GHL data)
- Each phase should include unit tests for new components
- Documentation should be updated as each phase completes