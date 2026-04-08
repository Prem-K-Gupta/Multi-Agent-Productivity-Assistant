# Multi-Agent Productivity Assistant

A multi-agent AI system that helps users manage tasks, schedules, and information by coordinating specialized sub-agents, Google services, and MCP tools.

## Architecture

```
User (Chat/API)
       |
  Nexus Orchestrator (Gemini NLU)
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
   SQLite / AlloyDB
```

## Features

- **Gemini-powered NLU** - Natural language understanding for intent classification
- **6 specialized sub-agents** - Task, Calendar, Memory, Notes, Gmail, Drive
- **7 MCP tools** - 3 local (SQLite) + 4 Google API integrations
- **Multi-step workflows** - "Plan my day" chains multiple agents
- **Full REST API** - 20+ endpoints for tasks, events, notes, memory, tools
- **React frontend** - Glassmorphism chat UI with live status panel
- **Cloud Run ready** - Dockerfile, deploy script included

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

### Enable Google Services

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable APIs: Calendar, Tasks, Gmail, Drive
3. Create OAuth2 credentials (Desktop app)
4. Download as `backend/credentials.json`
5. Start backend - it will open browser for OAuth consent on first request

### Deploy to Cloud Run

```bash
# Set your GCP project
gcloud config set project YOUR_PROJECT_ID

# Optional: set Gemini key
export GEMINI_API_KEY=your_key

# Deploy
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
| GET/POST | `/api/auth/google/*` | Google OAuth status/trigger |

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
- **AI**: Google Gemini 2.0 Flash
- **Google APIs**: Calendar, Tasks, Gmail, Drive
- **Deployment**: Docker, Google Cloud Run

## Testing

```bash
cd backend
python -m pytest tests/test_api.py -v    # 36 tests
```
