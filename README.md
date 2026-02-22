---
title: AI Lead Gen Agent
emoji: 🤖
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---



> An AI-powered system that automatically identifies, qualifies, and reaches out to potential business leads from remote job postings.

---

## Overview

The AI Lead Gen Agent monitors job boards (RemoteOK), uses an LLM (DeepSeek via OpenRouter) to qualify companies as potential customers, drafts personalized cold outreach emails, and tracks everything in a PostgreSQL database.

**Fully automated pipeline:**
```
RemoteOK API → Normalize → Filter → AI Qualify → Email Draft → Gmail SMTP
```

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11 |
| LLM | DeepSeek V3 via [OpenRouter](https://openrouter.ai) |
| AI Orchestration | LangChain |
| Database | PostgreSQL via [Supabase](https://supabase.com) |
| ORM | SQLAlchemy |
| API | FastAPI + Uvicorn |
| Email | Gmail SMTP |
| Containerization | Docker |
| Deployment | Hugging Face Spaces |

---

## Quick Start

### 1. Clone & install
```bash
git clone https://github.com/thasvithu/ai-lead-gen-agent.git
cd ai-lead-gen-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in your API keys and DB URL
```

Required variables:
| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENROUTER_MODEL` | e.g. `deepseek/deepseek-chat-v3-0324:free` |
| `DATABASE_URL` | PostgreSQL connection string (Supabase) |
| `GMAIL_USER` | Gmail sender address |
| `GMAIL_APP_PASSWORD` | Gmail App Password (16 chars) |
| `PRODUCT_DESCRIPTION` | What your product does (used for AI prompts) |

### 3. Initialize database
```bash
python scripts/setup_db.py
```

### 4. Run ingestion
```bash
# Fetch & save job postings (no AI filter)
python scripts/run_ingestion.py --no-ai --limit 50

# Fetch & save with AI keyword generation
python scripts/run_ingestion.py --limit 50
```

### 5. Qualify leads with AI
```python
from app.services.lead_service import process_new_postings
print(process_new_postings())
```

### 6. Run outreach (dry-run)
```bash
python scripts/run_outreach.py --dry-run
```

### 7. Start the API server
```bash
uvicorn api.main:app --reload
# Open http://localhost:8000/docs
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingestion/run` | Fetch, filter, and save job postings |
| `POST` | `/ingestion/qualify` | Run AI qualification on unprocessed postings |
| `GET` | `/ingestion/status` | Queue size (unprocessed postings) |
| `GET` | `/leads` | List leads (filter by status) |
| `GET` | `/leads/stats` | Lead counts by status |
| `GET` | `/leads/{id}` | Get lead detail |
| `PATCH` | `/leads/{id}/status` | Update lead status |
| `POST` | `/outreach/run` | Email all qualified leads |
| `POST` | `/outreach/{lead_id}` | Email a specific lead |
| `GET` | `/outreach/history` | Email send history |
| `GET` | `/health` | Health check |

Full interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Project Structure

```
ai-lead-gen-agent/
├── api/
│   ├── main.py                  # FastAPI app + routers
│   ├── schemas.py               # Pydantic request/response models
│   └── endpoints/
│       ├── ingestion_routes.py
│       ├── lead_routes.py
│       └── outreach_routes.py
├── app/
│   ├── config.py                # Centralized settings (pydantic-settings)
│   ├── ai_engine/
│   │   ├── processor.py         # LangChain chains
│   │   ├── prompt_templates.py  # All prompts
│   │   └── utils.py             # LLM factory, JSON parser, truncator
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── repository.py        # All DB read/write operations
│   │   └── session.py           # Engine + session factory
│   ├── ingestion/
│   │   ├── fetcher.py           # RemoteOK API client
│   │   ├── normalizer.py        # HTML cleaning + job normalization
│   │   └── filters.py           # Keyword + AI-assisted filtering
│   ├── outreach/
│   │   ├── mailer.py            # Gmail SMTP sender (dry-run safe)
│   │   └── templates.py         # HTML email renderer
│   └── services/
│       ├── lead_service.py      # AI qualification orchestrator
│       └── scoring.py           # Lead qualification gate
├── scripts/
│   ├── run_ingestion.py         # CLI: ingest job postings
│   ├── run_outreach.py          # CLI: send outreach emails
│   └── setup_db.py              # CLI: initialize DB schema
├── tests/
│   ├── conftest.py              # Shared fixtures + env var injection
│   ├── test_ingestion.py        # 18 ingestion tests
│   ├── test_ai_engine.py        # 19 AI engine tests
│   ├── test_db.py               # 14 repository tests (in-memory SQLite)
│   └── test_outreach.py         # 18 outreach tests
├── Dockerfile                   # HuggingFace Spaces compatible
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Individual suites
python -m pytest tests/test_ingestion.py -v   # 18 tests
python -m pytest tests/test_ai_engine.py -v   # 19 tests
python -m pytest tests/test_db.py -v          # 14 tests
python -m pytest tests/test_outreach.py -v    # 18 tests
```

**Total: 69 tests, 0 failures.**

---

## Deployment (Hugging Face Spaces)

This project is deployed as a **Docker Space** on Hugging Face.

1. Fork this repo and create a new Hugging Face Space (Docker type)
2. Set all environment variables in the Space **Settings → Variables and Secrets**
3. Push to the `main` branch — Spaces auto-builds from `Dockerfile`
4. Access your API at `https://<username>-<space-name>.hf.space/docs`

---

## License

MIT