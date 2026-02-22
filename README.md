# AI Lead Generation Agent

An autonomous AI system that identifies, qualifies, and reaches out to potential business leads based on job postings.

## Features
- Fetches job postings from RemoteOK (free API)
- AI-powered lead qualification via LLM (OpenRouter)
- Personalized cold email generation
- Gmail SMTP outreach with dry-run mode
- CRM storage in Supabase PostgreSQL
- REST API via FastAPI

## Quick Start

### 1. Clone & Setup Environment
```bash
git clone <repo-url>
cd ai-lead-gen-agent

python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

### 3. Initialize the Database
```bash
python scripts/setup_db.py
```

### 4. Run the Agent

**Fetch & qualify leads:**
```bash
python scripts/run_ingestion.py
```

**Send outreach emails (dry-run by default):**
```bash
python scripts/run_outreach.py
```

**Start the API server:**
```bash
uvicorn api.main:app --reload
# Open http://localhost:8000/docs
```

### 5. Docker
```bash
cp .env.example .env   # fill in your secrets
docker-compose up --build
```

## Project Structure
```
ai-lead-gen-agent/
├── app/
│   ├── config.py          # Central configuration (env vars)
│   ├── ingestion/         # Job board fetching & filtering
│   ├── ai_engine/         # LLM prompt chains (LangChain + OpenRouter)
│   ├── outreach/          # Email sending (Gmail SMTP)
│   ├── services/          # Business logic orchestration
│   └── db/                # SQLAlchemy ORM + session
├── api/                   # FastAPI routes + schemas
├── scripts/               # CLI scripts
├── tests/                 # pytest test suite
└── docs/                  # Architecture & API documentation
```

## Tech Stack
| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| LLM | OpenRouter (`trinity-large-preview:free`) |
| AI Orchestration | LangChain |
| API | FastAPI |
| Database | Supabase PostgreSQL |
| Email | Gmail SMTP |
| Deployment | Docker |

## License
MIT