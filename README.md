# Multi-Agent Productivity Assistant

A multi-agent AI system that helps users manage tasks, schedules, and information by coordinating specialized sub-agents, Google services, and MCP tools.

**Live Demo**: [https://nexus-assistant-fmitunhgmq-uc.a.run.app](https://nexus-assistant-fmitunhgmq-uc.a.run.app)

## Architecture

```
User (Chat UI / REST API)
       |
  Nexus Orchestrator (Gemini 2.5 Flash NLU + Regex Fallback)
       |
  +----+----+--------+--------+--------+--------+
  |         |        |        |        |        |
Task    Schedule  Context   Notes   Gmail    Drive
Agent    Agent    Agent    Agent   Agent    Agent
  |         |        |        |        |        |
  +----+----+--------+--------+--------+--------+
       |                                |
   MCP Tools                     Google APIs
  (Local DB)              (Calendar, Tasks, Gmail, Drive)
       |
   SQLite DB (5 tables)
```

## Features

- **Gemini-powered NLU** - Intent classification via Gemini 2.5 Flash with regex fallback
- **6 specialized sub-agents** - Task, Calendar, Memory, Notes, Gmail, Drive
- **7 MCP tools** - 3 local (SQLite-backed) + 4 Google API integrations
- **Per-user Google OAuth** - Web-based OAuth2 flow; each user connects their own Google account
- **Multi-step workflows** - "Plan my day" and "Weekly review" chain multiple agents
- **Full REST API** - 20+ endpoints for tasks, events, notes, memory, tools, and auth
- **React frontend** - Chat UI with sidebar, status bar, Google sign-in, suggestion chips
- **Cloud Run deployed** - Multi-stage Docker build, auto-deployed

## Quick Start

### Local Development

```bash
# Backend
cd backend
python -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
python main.py                    # Starts on http://localhost:8000

# Frontend (separate terminal)
npm install
npm run dev                       # Starts on http://localhost:5173
```

### Enable Gemini AI

```bash
# Get API key from https://aistudio.google.com/apikey
echo "GEMINI_API_KEY=your_key_here" > backend/.env
```

Without a Gemini API key, the system falls back to regex-based intent parsing (still fully functional).

### Enable Google Services

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable APIs: Calendar, Tasks, Gmail, Drive
3. Create **OAuth2 credentials** (Web Application type)
4. Add authorized redirect URIs:
   - `http://127.0.0.1:8000/api/auth/google/callback` (local dev)
   - `https://YOUR_CLOUD_RUN_URL/api/auth/google/callback` (production)
5. Download the credentials file as `backend/credentials.json`
6. Sign in via the **Google Account** section in the sidebar

### Deploy to Cloud Run

```bash
# Set your GCP project
gcloud config set project YOUR_PROJECT_ID

# Set Gemini key
export GEMINI_API_KEY=your_key

# Deploy (builds Docker image, deploys to Cloud Run, sets BASE_URL)
./deploy.sh
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Chat with the orchestrator |
| GET | `/health` | System health status |
| GET/POST/PUT/DELETE | `/api/tasks` | Task CRUD |
| GET/POST/DELETE | `/api/events` | Event CRUD |
| GET/POST/PUT/DELETE | `/api/notes` | Notes CRUD |
| GET/POST/DELETE | `/api/memory` | Memory CRUD |
| GET | `/api/tools` | List MCP tools |
| POST | `/api/tools/execute` | Execute MCP tool directly |
| GET | `/api/agents` | List all agents |
| GET | `/api/auth/google/status` | Google OAuth status |
| GET | `/api/auth/google/login` | Start Google sign-in flow |
| GET | `/api/auth/google/callback` | OAuth callback handler |
| DELETE | `/api/auth/google/logout` | Disconnect Google account |

## Chat Examples

```
create task Buy groceries high priority
show my tasks
complete task #1
schedule a meeting Team standup at 9am
show my calendar
remember that the deadline is Friday
what do you remember?
note: Key decisions from today's meeting #work
show my notes
check my email
search drive for report
plan my day
weekly review
help
```

## Tech Stack

- **Backend**: FastAPI, Python 3.12, SQLite
- **Frontend**: React 18, Vite
- **AI**: Google Gemini 2.5 Flash (intent parsing + response generation)
- **Google APIs**: Calendar, Tasks, Gmail, Drive (per-user OAuth2)
- **Deployment**: Docker (multi-stage), Google Cloud Run

## Testing

```bash
cd backend
python -m pytest tests/test_api.py -v    # 36 tests
```
