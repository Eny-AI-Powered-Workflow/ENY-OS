# Workflows Registry

This directory contains exported n8n workflow JSON files that can be imported into the n8n instance.

## Webhook-Path Registry

| Workflow Name | Webhook Path | Description |
|---------------|--------------|-------------|
| ENY-SALES-SCORE | /webhook/eny-sales-score | Lead scoring workflow that analyzes leads and assigns scores based on engagement and fit criteria |
| ENY-ENROLLMENT-FOLLOW-UP | /webhook/eny-enrollment-follow-up | Queues approved hot-lead follow-up for the Enrollment team |
| ENY-VIDEO-PUBLISH | /webhook/eny-video-publish | Validates an approved clip and sends it to the configured publishing adapter |

## How to Use

1. To import a workflow into n8n:
   - Go to n8n UI → Workflows → Import
   - Select the JSON file from this directory
   - Activate the workflow

2. To trigger a workflow from the frontend/backend:
   - Use the `/api/v1/agents/trigger/{workflow_name}` endpoint
   - Example: `POST /api/v1/agents/trigger/eny-sales-score`

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

### ENY-SALES-SCORE
- **Webhook Path**: `/webhook/eny-sales-score`
- **Description**: Analyzes incoming leads and assigns a score based on predefined criteria (engagement, demographic fit, behavioral signals)
- **Trigger Type**: Webhook
- **Expected Input**: Lead data object with contact information and engagement metrics
- **Output**: Updated lead record with score and appropriate tags (hot, warm, cold, follow-up)

### ENY-ENROLLMENT-FOLLOW-UP
- **Webhook Path**: `/webhook/eny-enrollment-follow-up`
- **Description**: Receives an approved, assigned hot lead and queues the configured Enrollment follow-up action.
- **Trigger Type**: Webhook
- **Expected Input**: `contact_id`, `result_id`, `approval_id`, `assigned_user_id`, `source`, `score`, and `category`
- **Output**: Success after the GHL contact is loaded and tagged with `eny-follow-up-queued`. The inbox email is best-effort: the response includes `notification_sent` and `notification_error` if delivery fails after the tag succeeds.
- **Required n8n environment variables**: `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`, `GHL_BASE_URL`, `GHL_LOCATION_ID`, `GHL_PRIVATE_TOKEN`, `GHL_NOTIFICATION_FROM_EMAIL`
- **Recommended webhook protection**: configure the Webhook node with a dedicated header secret and set the same value as backend `N8N_WEBHOOK_TOKEN`.

### ENY-VIDEO-PUBLISH
- **Webhook Path**: `/webhook/eny-video-publish`
- **Workflow File**: `eny-video-publish.json`
- **Description**: Receives an approved clip, its private signed source URL and time range, then delegates clipping/publication to a configured channel adapter. The backend marks the output published only after this workflow confirms success.
- **Expected Input**: `asset_id`, `title`, `caption`, `source_media_url`, `start_seconds`, `end_seconds`, `channel`, and approval metadata.
- **Required n8n environment variables**: `ENY_VIDEO_PUBLISHER_URL`, `ENY_VIDEO_PUBLISHER_TOKEN`.
- **Webhook protection**: configure the imported Webhook node with header authentication using the same secret as backend `N8N_WEBHOOK_TOKEN`.
- **Important**: The channel adapter must actually trim the requested time range and return `{ "published": true, "url": "..." }` (or `{ "status": "published" }`). The included workflow is inactive until imported, configured, and activated. It deliberately does not report a simulated publish as complete.

## Development Notes

- Workflows should be exported from n8n and placed in this directory with descriptive names
- Each workflow should have a corresponding entry in the webhook-path registry above
- When adding new workflows, update this README.md accordingly
- For development/testing workflows, consider adding a `-dev` suffix to the filename

## Example Usage in Code

```typescript
// Trigger the ENY-SALES-SCORE workflow
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