---
description: How to deploy the application to HuggingFace Spaces
---

## Overview
The GitHub Actions workflow at `.github/workflows/deploy_hf.yml` automatically deploys the app to HuggingFace Spaces on every push to `main`.

## One-time Setup

### Step 1 — Create a HuggingFace Space
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Choose **SDK: Docker**
3. Set visibility to **Public** (required for free tier)
4. Note your space name (e.g. `ai-lead-gen-agent`)

### Step 2 — Get a HuggingFace token
Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → **New token** → Role: **Write**.

### Step 3 — Add GitHub Secrets
Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|---|---|
| `HF_TOKEN` | Your HuggingFace write token |
| `HF_USERNAME` | Your HuggingFace username |
| `HF_SPACE_NAME` | Your Space name (e.g. `ai-lead-gen-agent`) |

### Step 4 — Add Space environment secrets
Go to your HuggingFace Space → **Settings → Variables and Secrets** → add:

| Secret | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `DATABASE_URL` | Supabase PostgreSQL URI |
| `GMAIL_USER` | Gmail sender address |
| `GMAIL_APP_PASSWORD` | Gmail App Password |
| `PRODUCT_DESCRIPTION` | Your product description |
| `MAILER_DRY_RUN` | Set to `true` for demo mode |

## How Deployment Works
1. You push to `main` on GitHub
2. GitHub Actions runs `deploy_hf.yml`
3. It pushes the code to `https://huggingface.co/spaces/<HF_USERNAME>/<HF_SPACE_NAME>`
4. HuggingFace builds the Docker image from `Dockerfile` and starts the container on **port 7860**
5. Your API is live at `https://<HF_USERNAME>-<HF_SPACE_NAME>.hf.space/docs`

## Running Deployment Manually
In the **Actions** tab → "Deploy to HuggingFace Spaces" → **Run workflow**.

## Checking Deployment Status
1. Go to your HuggingFace Space URL
2. Check the **Logs** tab in the Space for build output
3. The `/health` endpoint should return `{"status": "ok"}`
