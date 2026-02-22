# API Reference

Base URL (local): `http://localhost:8000`
Base URL (HF Spaces): `https://<username>-ai-lead-gen-agent.hf.space`

Interactive Swagger UI: `{base_url}/docs`

---

## System

### `GET /health`
Returns liveness status.
```json
{ "status": "ok", "service": "ai-lead-gen-agent" }
```

### `GET /`
Returns service info.
```json
{ "message": "...", "docs": "/docs", "product": "..." }
```

---

## Ingestion

### `POST /ingestion/run`
Fetch, normalize, filter, and save job postings.

**Request body:**
```json
{ "limit": 50, "use_ai_filter": true }
```

**Response:**
```json
{
  "fetched": 50, "normalized": 47, "passed_filter": 15,
  "saved": 9, "skipped_duplicates": 6, "message": "..."
}
```

### `POST /ingestion/qualify`
Run AI qualification on all unprocessed postings.

**Response:**
```json
{ "processed": 9, "qualified": 6, "rejected": 3, "message": "..." }
```

### `GET /ingestion/status`
Returns count of postings awaiting AI qualification.

**Query params:** `limit` (default: 100)

---

## Leads

### `GET /leads`
List leads, optionally filtered by status.

**Query params:**
- `status`: `new` | `qualified` | `emailed` | `replied` | `rejected`
- `limit`: 1–200 (default: 50)

### `GET /leads/stats`
Aggregate counts by status.
```json
{ "new": 0, "qualified": 10, "emailed": 5, "replied": 1, "rejected": 2, "total": 18 }
```

### `GET /leads/{lead_id}`
Get full lead detail including company and job posting.

### `PATCH /leads/{lead_id}/status`
Manually update lead status.
```json
{ "status": "replied" }
```

---

## Outreach

### `POST /outreach/run`
Run outreach for all qualified leads.

**Query params:**
- `limit`: 1–100 (default: 20)
- `dry_run`: `true` | `false` (default: `true`)

**Response:**
```json
{ "attempted": 10, "sent": 8, "failed": 1, "skipped": 1, "message": "..." }
```

### `POST /outreach/{lead_id}`
Send outreach for a specific lead.

**Query params:** `dry_run` (default: `true`)

### `GET /outreach/history`
List all email send attempts.

**Query params:** `limit` (default: 50)
