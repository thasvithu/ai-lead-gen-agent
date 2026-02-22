---
description: How to keep Supabase database alive (prevent auto-pause after 7 days of inactivity)
---

## Overview
Supabase free-tier projects auto-pause after 7 days of no activity.
The GitHub Actions workflow at `.github/workflows/keep_supabase_alive.yml` pings the DB every 5 days via a cron job.

## One-time Setup

### Step 1 — Add the required GitHub Secrets
Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL — e.g. `https://vnfmpfpnvfugytvqizdl.supabase.co` |
| `SUPABASE_ANON_KEY` | Your Supabase `anon` public key (from Supabase → Settings → API) |

> **Why not DATABASE_URL?** Direct psycopg2 connections from GitHub Actions fail with an IPv6 unreachable error. The HTTP REST ping works reliably over IPv4.

### Step 2 — Verify the workflow is enabled
Go to **Actions** tab → "Keep Supabase Alive" → Ensure it's not disabled.

## Running Manually
In the **Actions** tab, select "Keep Supabase Alive" → click **Run workflow** → **Run workflow** (green button).

## Checking it worked
The workflow logs should print:
```
✅ Supabase ping successful: (1,)
```

## Cron Schedule
The workflow runs every **5 days at 08:00 UTC**:
```yaml
cron: "0 8 */5 * *"
```
To change the interval, edit `.github/workflows/keep_supabase_alive.yml` and adjust the cron expression.
