"""End-to-end tests for the Nexus Multi-Agent Productivity Assistant API."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# =============== Health & Root ===============

class TestHealth:
    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "Nexus" in data["message"]
        assert "version" in data

    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["db_connected"] is True
        assert data["mcp_active"] is True
        assert data["status"] == "healthy"
        assert "agents" in data
        # 6 sub-agents + 1 orchestrator = 7
        assert data["agents"]["total_agents"] == 7
        assert "gemini_enabled" in data
        assert "google_connected" in data


# =============== Chat / Orchestrator ===============

class TestChat:
    def test_chat_help(self):
        r = client.post("/api/chat", json={"message": "help", "user_id": "test"})
        assert r.status_code == 200
        data = r.json()
        assert "Orchestrator" in data["active_agent"]

    def test_chat_create_task(self):
        r = client.post("/api/chat", json={"message": "create task Buy groceries", "user_id": "test"})
        assert r.status_code == 200
        data = r.json()
        assert data["active_agent"] == "Task Planning Agent"
        assert "groceries" in data["response"].lower() or "task" in data["response"].lower()

    def test_chat_remember(self):
        r = client.post("/api/chat", json={"message": "remember that the meeting is at 3pm", "user_id": "test"})
        assert r.status_code == 200
        assert r.json()["active_agent"] == "Context Retrieval Agent"

    def test_chat_retrieve_memory(self):
        client.post("/api/chat", json={"message": "remember that the password is 1234", "user_id": "test_mem"})
        r = client.post("/api/chat", json={"message": "what do you remember?", "user_id": "test_mem"})
        assert r.status_code == 200
        assert r.json()["active_agent"] == "Context Retrieval Agent"

    def test_chat_schedule_meeting(self):
        r = client.post("/api/chat", json={"message": "schedule a meeting Team standup at 9am", "user_id": "test"})
        assert r.status_code == 200
        assert r.json()["active_agent"] == "Scheduling Agent"

    def test_chat_create_note(self):
        r = client.post("/api/chat", json={"message": "note: Project ideas for Q2", "user_id": "test"})
        assert r.status_code == 200
        assert r.json()["active_agent"] == "Notes Agent"

    def test_chat_list_tasks(self):
        client.post("/api/chat", json={"message": "create task Test listing", "user_id": "test_list"})
        r = client.post("/api/chat", json={"message": "show my tasks", "user_id": "test_list"})
        assert r.status_code == 200
        assert r.json()["active_agent"] == "Task Planning Agent"

    def test_chat_list_events(self):
        r = client.post("/api/chat", json={"message": "show my calendar", "user_id": "test"})
        assert r.status_code == 200
        assert r.json()["active_agent"] == "Scheduling Agent"

    def test_chat_list_notes(self):
        r = client.post("/api/chat", json={"message": "show my notes", "user_id": "test"})
        assert r.status_code == 200
        assert r.json()["active_agent"] == "Notes Agent"

    def test_chat_fallback(self):
        r = client.post("/api/chat", json={"message": "hello there", "user_id": "test"})
        assert r.status_code == 200
        # Either Orchestrator handles it or Gemini generates a response
        assert r.json()["active_agent"] in ["Nexus Orchestrator", "Error Handler"]

    def test_chat_workflow_plan_my_day(self):
        r = client.post("/api/chat", json={"message": "plan my day", "user_id": "test"})
        assert r.status_code == 200
        data = r.json()
        assert data["active_agent"] == "Nexus Orchestrator"
        assert "Workflow" in " ".join(data["actions_taken"])

    def test_chat_complete_task(self):
        cr = client.post("/api/tasks", json={"title": "Task to complete"}, params={"user_id": "test_complete"})
        task_id = cr.json()["task"]["id"]
        r = client.post("/api/chat", json={"message": f"complete task #{task_id}", "user_id": "test_complete"})
        assert r.status_code == 200
        assert "done" in r.json()["response"].lower()

    # Gmail and Drive (without Google auth, these should handle gracefully)
    def test_chat_check_email(self):
        r = client.post("/api/chat", json={"message": "check my email", "user_id": "test"})
        assert r.status_code == 200
        assert r.json()["active_agent"] == "Gmail Agent"

    def test_chat_search_drive(self):
        r = client.post("/api/chat", json={"message": "search drive for report", "user_id": "test"})
        assert r.status_code == 200
        assert r.json()["active_agent"] == "Drive Agent"


# =============== Task REST API ===============

class TestTasks:
    def test_create_and_list(self):
        r = client.post("/api/tasks", json={"title": "REST task", "priority": "high"}, params={"user_id": "rest_test"})
        assert r.status_code == 200
        assert r.json()["task"]["title"] == "REST task"

        r = client.get("/api/tasks", params={"user_id": "rest_test"})
        assert r.status_code == 200
        assert any(t["title"] == "REST task" for t in r.json()["tasks"])

    def test_update_task(self):
        r = client.post("/api/tasks", json={"title": "Update me"}, params={"user_id": "rest_test"})
        tid = r.json()["task"]["id"]
        r = client.put(f"/api/tasks/{tid}", json={"status": "in_progress", "priority": "high"})
        assert r.status_code == 200
        assert r.json()["task"]["status"] == "in_progress"

    def test_delete_task(self):
        r = client.post("/api/tasks", json={"title": "Delete me"}, params={"user_id": "rest_test"})
        tid = r.json()["task"]["id"]
        assert client.delete(f"/api/tasks/{tid}").status_code == 200

    def test_delete_nonexistent(self):
        assert client.delete("/api/tasks/99999").status_code == 404


# =============== Event REST API ===============

class TestEvents:
    def test_create_and_list(self):
        r = client.post("/api/events", json={"title": "Team Sync", "start_time": "2024-01-15 10:00"}, params={"user_id": "event_test"})
        assert r.status_code == 200
        r = client.get("/api/events", params={"user_id": "event_test"})
        assert len(r.json()["events"]) > 0

    def test_delete_event(self):
        r = client.post("/api/events", json={"title": "Delete event", "start_time": "2024-01-15"}, params={"user_id": "event_test"})
        eid = r.json()["event"]["id"]
        assert client.delete(f"/api/events/{eid}").status_code == 200


# =============== Notes REST API ===============

class TestNotes:
    def test_create_and_list(self):
        client.post("/api/notes", json={"title": "My Note", "content": "Some content", "tags": "work"}, params={"user_id": "note_test"})
        r = client.get("/api/notes", params={"user_id": "note_test"})
        assert len(r.json()["notes"]) > 0

    def test_update_note(self):
        r = client.post("/api/notes", json={"title": "Edit me"}, params={"user_id": "note_test"})
        nid = r.json()["note"]["id"]
        assert client.put(f"/api/notes/{nid}", json={"content": "Updated"}).status_code == 200

    def test_delete_note(self):
        r = client.post("/api/notes", json={"title": "Remove me"}, params={"user_id": "note_test"})
        nid = r.json()["note"]["id"]
        assert client.delete(f"/api/notes/{nid}").status_code == 200

    def test_filter_by_tag(self):
        client.post("/api/notes", json={"title": "Tagged", "tags": "project"}, params={"user_id": "tag_test"})
        r = client.get("/api/notes", params={"user_id": "tag_test", "tag": "project"})
        assert len(r.json()["notes"]) > 0


# =============== Memory REST API ===============

class TestMemory:
    def test_create_and_list(self):
        client.post("/api/memory", json={"content": "Important fact", "category": "facts"}, params={"user_id": "mem_test"})
        r = client.get("/api/memory", params={"user_id": "mem_test"})
        assert len(r.json()["memories"]) > 0

    def test_filter_by_category(self):
        client.post("/api/memory", json={"content": "Work note", "category": "work"}, params={"user_id": "mem_cat_test"})
        r = client.get("/api/memory", params={"user_id": "mem_cat_test", "category": "work"})
        assert len(r.json()["memories"]) > 0

    def test_delete_memory(self):
        r = client.post("/api/memory", json={"content": "Forget me"}, params={"user_id": "mem_test"})
        mid = r.json()["memory"]["id"]
        assert client.delete(f"/api/memory/{mid}").status_code == 200


# =============== MCP Tools ===============

class TestMCPTools:
    def test_list_tools(self):
        r = client.get("/api/tools")
        assert r.status_code == 200
        tools = r.json()["tools"]
        # At minimum 3 local tools, more if Google configured
        assert len(tools) >= 3
        names = {t["name"] for t in tools}
        assert {"calendar", "task_manager", "notes"}.issubset(names)

    def test_execute_calendar_tool(self):
        r = client.post("/api/tools/execute", json={
            "tool_name": "calendar", "action": "create",
            "params": {"user_id": "tool_test", "title": "MCP Event", "start_time": "2024-03-01 14:00"},
        })
        assert r.json()["status"] == "success"

    def test_execute_task_tool(self):
        r = client.post("/api/tools/execute", json={
            "tool_name": "task_manager", "action": "create",
            "params": {"user_id": "tool_test", "title": "MCP Task"},
        })
        assert r.json()["status"] == "success"

    def test_execute_notes_tool(self):
        r = client.post("/api/tools/execute", json={
            "tool_name": "notes", "action": "create",
            "params": {"user_id": "tool_test", "title": "MCP Note"},
        })
        assert r.json()["status"] == "success"

    def test_execute_unknown_tool(self):
        assert client.post("/api/tools/execute", json={
            "tool_name": "nonexistent", "action": "create", "params": {},
        }).status_code == 404


# =============== Agents Info ===============

class TestAgentInfo:
    def test_list_agents(self):
        r = client.get("/api/agents")
        assert r.status_code == 200
        data = r.json()
        assert data["orchestrator"] == "Nexus Orchestrator"
        assert len(data["sub_agents"]) == 6
        assert data["total_tools"] >= 3
        assert "gemini_enabled" in data
        assert "google_services" in data


# =============== Google Auth Status ===============

class TestGoogleAuth:
    def test_auth_status(self):
        r = client.get("/api/auth/google/status")
        assert r.status_code == 200
        data = r.json()
        assert "credentials_configured" in data
        assert "authenticated" in data
