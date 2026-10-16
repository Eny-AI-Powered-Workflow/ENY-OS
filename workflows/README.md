# Workflows Registry

This directory contains exported n8n workflow JSON files that can be imported into the n8n instance.

## Webhook-Path Registry

| Workflow Name | Webhook Path | Description |
|---------------|--------------|-------------|
| ENY-VIDEO-PUBLISH | /webhook/eny-video-publish | Validates an approved clip and sends it to the configured publishing adapter |

## How to Use

1. To import a workflow into n8n:
   - Go to n8n UI → Workflows → Import
   - Select the JSON file from this directory
   - Activate the workflow

2. To trigger a registered workflow from the frontend/backend:
   - Use the `/api/v1/agents/trigger/{workflow_name}` endpoint
   - The Sales scoring and notification paths do not use this endpoint.

## Available Workflows

### ENY-PROG-ONBOARD
- **Webhook Path**: `/webhook/eny-prog-onboard`
- **Description**: Generates an onboarding/orientation draft checklist and reminder summary for human review before any student-facing message is sent.
- **Trigger Type**: Webhook
- **Approval Model**: `shadow` mode with `programs_manager` review required before any outbound send.
- **Expected Input**: `student_id`, `program_id`, `cohort_id`, `summary`, and optional `follow_up_type`
- **Output**: A draft queue item and review record, not a live message.

### ENY-PROG-MONITOR
- **Webhook Path**: `/webhook/eny-prog-monitor`
- **Description**: Produces class/attendance and assignment summaries for review; it never decides access, grades, or compliance.
- **Trigger Type**: Webhook
- **Approval Model**: `shadow` mode with `programs_manager` or `customer_success` review required before an outbound action.
- **Expected Input**: `student_id`, `offer_id`, `attendance_status`, `assignment_status`, `capstone_status`, and `period`
- **Output**: Human-readable summary and queue item only.

### ENY-CUSTOMER-SUCCESS-CHECKIN
- **Webhook Path**: `/webhook/eny-customer-success-checkin`
- **Description**: Drafts weekly check-in or reminder messages for a staff reviewer.
- **Trigger Type**: Webhook
- **Approval Model**: `draft-only`; the message remains in the review queue until an authorized user approves sending.
- **Expected Input**: `student_name`, `category`, `message`, and optional `sentiment` metadata.
- **Output**: Draft communication item, never a live email/WhatsApp payload.

### ENY-CUSTOMER-SUCCESS-ESCALATION
- **Webhook Path**: `/webhook/eny-customer-success-escalation`
- **Description**: Escalates sensitive issues to an assigned human owner instead of letting an automated bot resolve complaints, payment disputes, or coach issues.
- **Trigger Type**: Webhook
- **Approval Model**: `manual` escalation only; requires human approval and a supervisor owner.
- **Expected Input**: `student_id`, `case_type`, `reason`, `priority`, and `assigned_owner`
- **Output**: Escalation queue item and operational log only.

### Sales & Enrollment intake and scoring

GHL contact-created events are received by the FastAPI route
`POST /api/v1/enrollment/ghl-webhook`, authenticated with the
`X-GHL-Webhook-Token` shared secret. The event is deduplicated by GHL contact
ID and displayed in the AI Desk for human batch approval. Scoring is a
separate explicit action and runs through `ClaudeService`; it is not an n8n
workflow. The weighted score uses intent (40%), offer fit (30%), and
engagement (30%), with unsupported/unknown evidence scored as zero. Hot is
85+, warm 70–84, follow-up 50–69, and cold below 50.

Hot-lead and "Notify Sales & Enrollment" actions create internal
`operational_alerts`; the latter also tags the GHL contact as queued. It never
sends an email or SMS to the lead and never marks outreach as sent. If the
legacy `eny-enrollment-follow-up.json` workflow was imported into n8n, disable
it: its previous email behavior is retired and the backend no longer calls it.

### ENY-VIDEO-PUBLISH
- **Webhook Path**: `/webhook/eny-video-publish`
- **Workflow File**: `eny-video-publish.json`
- **Description**: Receives an approved clip, its private signed source URL and time range, then delegates clipping/publication to a configured channel adapter. The backend marks the output published only after this workflow confirms success.
- **Expected Input**: `asset_id`, `title`, `caption`, `source_media_url`, `start_seconds`, `end_seconds`, `channel`, and approval metadata.
- **Required n8n environment variables**: `ENY_VIDEO_PUBLISHER_URL`, `ENY_VIDEO_PUBLISHER_TOKEN`.
- **Webhook protection**: configure the imported Webhook node with header authentication using the same secret as backend `N8N_WEBHOOK_TOKEN`.
- **Important**: The channel adapter must actually trim the requested time range and return `{ "published": true, "url": "..." }` (or `{ "status": "published" }`). The included workflow is inactive until imported, configured, and activated. It deliberately does not report a simulated publish as complete.

## Business Support Payment Verification

Payment verification is a human-operated API flow, not an n8n workflow. Business Support uses the dashboard to request a server-side Paystack reference verification; the backend records the result and reviewer under an idempotency key. Only Paystack `success`/NGN responses are marked verified. The flow does not alter provider data, grant course access, or trigger Programs onboarding. Kajabi, payment lifecycle writes, and automated follow-up remain disabled until their provider contracts, approvals, and duplicate-side-effect recovery are validated.

## Development Notes

- Workflows should be exported from n8n and placed in this directory with descriptive names
- Each workflow should have a corresponding entry in the webhook-path registry above
- When adding new workflows, update this README.md accordingly
- For development/testing workflows, consider adding a `-dev` suffix to the filename

## Example Usage in Code

No Sales scoring example is provided: intake and scoring use the human-approved
AI Desk flow described above, not a registered n8n scorer.

<!-- Historical example retained only for migration history; not an active workflow.
```typescript
// Retired: ENY-SALES-SCORE is not an approved workflow.
const res = await fetch('/api/v1/agents/trigger/eny-sales-score', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`
  },
  body: JSON.stringify({
    leadId: 'lead_123',
    engagementScore: 75,
    demographicFit: 80
  })
});
```
-->