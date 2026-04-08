from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import logging

from agents.orchestrator import OrchestratorAgent
from database.alloydb import (
    check_db_health,
    get_tasks, create_task, update_task, delete_task,
    get_events, create_event, delete_event,
    get_notes, create_note, update_note, delete_note,
    get_memory, save_to_memory, delete_memory,
    save_google_token, get_google_token, delete_google_token,
)
from tools.mcp_tools import check_mcp_health, list_tools, get_tool, google_tools_available

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nexus AI Backend API",
    description="Multi-Agent System with Gemini NLU, Google Services & MCP Tools",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============== Pydantic Models ===============

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"

class ChatResponse(BaseModel):
    response: str
    actions_taken: List[str]
    active_agent: str

class SystemStatus(BaseModel):
    status: str
    db_connected: bool
    mcp_active: bool
    google_connected: bool
    gemini_enabled: bool
    agents: dict

class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    due_date: Optional[str] = None

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None

class EventCreateRequest(BaseModel):
    title: str
    start_time: str
    end_time: Optional[str] = None
    description: str = ""
    location: str = ""

class NoteCreateRequest(BaseModel):
    title: str
    content: str = ""
    tags: str = ""

class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None

class MemoryCreateRequest(BaseModel):
    content: str
    category: str = "general"

class MCPToolRequest(BaseModel):
    tool_name: str
    action: str
    params: dict = {}


# =============== Initialize ===============
orchestrator = OrchestratorAgent()

# Public base URL — set BASE_URL env var in Cloud Run to your service URL
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


def _get_redirect_uri():
    return f"{BASE_URL}/api/auth/google/callback"


# =============== Core Endpoints ===============

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Nexus API",
        "version": "3.0.0",
        "gemini": orchestrator.gemini_enabled,
        "google_services": google_tools_available(),
    }


@app.get("/health", response_model=SystemStatus)
def health_check():
    db_ok = check_db_health()
    mcp_ok = check_mcp_health()
    google_ok = google_tools_available()
    agent_status = orchestrator.get_agent_status()
    all_ok = db_ok and mcp_ok
    return SystemStatus(
        status="healthy" if all_ok else "degraded",
        db_connected=db_ok,
        mcp_active=mcp_ok,
        google_connected=google_ok,
        gemini_enabled=orchestrator.gemini_enabled,
        agents=agent_status,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Primary chat endpoint - routes through Orchestrator (Gemini NLU or regex)."""
    try:
        result = orchestrator.process_request(request.message, request.user_id)
        return ChatResponse(
            response=result["message"],
            actions_taken=result["actions"],
            active_agent=result["agent"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============== Google Auth Endpoints (Web Server Flow - works on Cloud Run) ===============

@app.get("/api/auth/google/status")
def google_auth_status(user_id: str = "default_user"):
    """Check if this user has connected their Google account."""
    try:
        from google_auth import is_google_configured
        token_row = get_google_token(user_id)
        return {
            "credentials_configured": is_google_configured(),
            "authenticated": token_row is not None,
            "email": token_row["email"] if token_row else None,
            "name": token_row["name"] if token_row else None,
            "login_url": f"/api/auth/google/login?user_id={user_id}",
        }
    except Exception as e:
        return {"credentials_configured": False, "authenticated": False, "error": str(e)}


@app.get("/api/auth/google/login")
def google_login(user_id: str = "default_user"):
    """
    Step 1 — redirect the user's browser to Google's consent screen.
    user_id is passed as OAuth 'state' so we know who to save the token for after.
    """
    try:
        from google_auth import get_authorization_url, is_google_configured
        if not is_google_configured():
            raise HTTPException(
                status_code=400,
                detail="credentials.json not found. Download Web App OAuth2 credentials from Google Cloud Console and place in backend/."
            )
        auth_url = get_authorization_url(_get_redirect_uri(), state=user_id)
        return RedirectResponse(url=auth_url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/google/callback")
def google_callback(code: str = None, state: str = "default_user", error: str = None):
    """
    Step 2 — Google sends the user back here with an authorization code.
    Exchange it for tokens, store them per-user in the database,
    then redirect back to the frontend.
    """
    if error:
        return RedirectResponse(url=f"{BASE_URL}/?auth_error={error}")
    if not code:
        return RedirectResponse(url=f"{BASE_URL}/?auth_error=no_code")

    try:
        from google_auth import exchange_code_for_tokens
        user_id = state  # state = user_id we set in step 1

        result = exchange_code_for_tokens(code, _get_redirect_uri())
        save_google_token(
            user_id=user_id,
            email=result["email"],
            name=result["name"],
            token_json=result["token_json"],
        )
        logger.info(f"Google OAuth success: user={user_id} email={result['email']}")
        return RedirectResponse(url=f"{BASE_URL}/?auth_success=true&email={result['email']}")

    except Exception as e:
        logger.exception("Google OAuth callback failed")
        return RedirectResponse(url=f"{BASE_URL}/?auth_error=callback_failed")


@app.delete("/api/auth/google/logout")
def google_logout(user_id: str = "default_user"):
    """Disconnect a user's Google account by removing their stored token."""
    deleted = delete_google_token(user_id)
    return {
        "success": deleted,
        "message": "Google account disconnected." if deleted else "No Google account was connected.",
    }


# =============== Task Endpoints ===============

@app.get("/api/tasks")
def list_tasks(user_id: str = "default_user", status: Optional[str] = None):
    return {"tasks": get_tasks(user_id, status)}

@app.post("/api/tasks")
def create_task_endpoint(req: TaskCreateRequest, user_id: str = "default_user"):
    return {"task": create_task(user_id, req.title, req.description, req.priority, req.due_date)}

@app.put("/api/tasks/{task_id}")
def update_task_endpoint(task_id: int, req: TaskUpdateRequest):
    result = update_task(task_id, **req.model_dump(exclude_none=True))
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"task": result}

@app.delete("/api/tasks/{task_id}")
def delete_task_endpoint(task_id: int):
    if not delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": f"Task #{task_id} deleted"}


# =============== Event Endpoints ===============

@app.get("/api/events")
def list_events(user_id: str = "default_user"):
    return {"events": get_events(user_id)}

@app.post("/api/events")
def create_event_endpoint(req: EventCreateRequest, user_id: str = "default_user"):
    return {"event": create_event(user_id, req.title, req.start_time, req.end_time, req.description, req.location)}

@app.delete("/api/events/{event_id}")
def delete_event_endpoint(event_id: int):
    if not delete_event(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": f"Event #{event_id} deleted"}


# =============== Notes Endpoints ===============

@app.get("/api/notes")
def list_notes(user_id: str = "default_user", tag: Optional[str] = None):
    return {"notes": get_notes(user_id, tag)}

@app.post("/api/notes")
def create_note_endpoint(req: NoteCreateRequest, user_id: str = "default_user"):
    return {"note": create_note(user_id, req.title, req.content, req.tags)}

@app.put("/api/notes/{note_id}")
def update_note_endpoint(note_id: int, req: NoteUpdateRequest):
    result = update_note(note_id, **req.model_dump(exclude_none=True))
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"note": result}

@app.delete("/api/notes/{note_id}")
def delete_note_endpoint(note_id: int):
    if not delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": f"Note #{note_id} deleted"}


# =============== Memory Endpoints ===============

@app.get("/api/memory")
def list_memory(user_id: str = "default_user", category: Optional[str] = None):
    return {"memories": get_memory(user_id, category)}

@app.post("/api/memory")
def create_memory_endpoint(req: MemoryCreateRequest, user_id: str = "default_user"):
    return {"memory": save_to_memory(user_id, req.content, req.category)}

@app.delete("/api/memory/{memory_id}")
def delete_memory_endpoint(memory_id: int):
    if not delete_memory(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"message": f"Memory #{memory_id} deleted"}


# =============== MCP Tool Endpoints ===============

@app.get("/api/tools")
def list_mcp_tools():
    return {"tools": list_tools(), "google_available": google_tools_available()}

@app.post("/api/tools/execute")
def execute_mcp_tool(req: MCPToolRequest):
    tool = get_tool(req.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool_name}' not found")
    return tool.execute(req.action, req.params)


# =============== Agent Info ===============

@app.get("/api/agents")
def list_agents():
    return orchestrator.get_agent_status()


# =============== Serve React Frontend (production) ===============

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React SPA for any non-API route."""
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=(port == 8000))
