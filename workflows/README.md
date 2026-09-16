# Workflows Registry

This directory contains exported n8n workflow JSON files that can be imported into the n8n instance.

## Webhook-Path Registry

| Workflow Name | Webhook Path | Description |
|---------------|--------------|-------------|
| ENY-SALES-SCORE | /webhook/eny-sales-score | Lead scoring workflow that analyzes leads and assigns scores based on engagement and fit criteria |
| ENY-ENROLLMENT-FOLLOW-UP | /webhook/eny-enrollment-follow-up | Queues approved hot-lead follow-up for the Enrollment team |

## How to Use

1. To import a workflow into n8n:
   - Go to n8n UI → Workflows → Import
   - Select the JSON file from this directory
   - Activate the workflow

2. To trigger a workflow from the frontend/backend:
   - Use the `/api/v1/agents/trigger/{workflow_name}` endpoint
   - Example: `POST /api/v1/agents/trigger/eny-sales-score`

## Available Workflows

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
- **Output**: Success only after the GHL contact is loaded and tagged with `eny-follow-up-queued`; HTTP/GHL failures terminate the workflow with an error.
- **Required n8n environment variables**: `GHL_BASE_URL`, `GHL_LOCATION_ID`, `GHL_PRIVATE_TOKEN`
- **Recommended webhook protection**: configure the Webhook node with a dedicated header secret and set the same value as backend `N8N_WEBHOOK_TOKEN`.

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