"""
MediMind — FastAPI Application
Main API server with SSE streaming, session management, and human review endpoints.
"""
import sys
# Guarantee UTF-8 stdout/stderr across Windows console and threads
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import uuid
import json
import asyncio
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.graph.graph_builder import get_graph
from backend.graph.state import AgentState, PatientInfo, HumanReviewDecision
from backend.tools.pubmed_rag import initialize_vector_store


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    print("🚀 MediMind API starting up...")
    # Initialize ChromaDB with medical literature
    try:
        initialize_vector_store()
        print("✅ Vector store initialized")
    except Exception as e:
        print(f"⚠️  Vector store initialization failed: {e}")

    # Pre-warm the graph
    get_graph()
    print("✅ LangGraph compiled and ready")
    print(f"🌐 API running on port {settings.APP_PORT}")

    yield

    print("👋 MediMind API shutting down...")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="MediMind Clinical AI API",
    description="AI-Powered Clinical Decision Support System using LangGraph multi-agent architecture",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    patient_name: str = Field(..., description="Patient full name")
    patient_age: int = Field(..., ge=0, le=150)
    patient_gender: str = Field(..., pattern="^(male|female|other)$")
    symptoms: list[str] = Field(..., min_length=1)
    symptom_duration: str = Field(default="Not specified")
    severity: str = Field(default="moderate", pattern="^(mild|moderate|severe)$")
    medical_history: list[str] = Field(default=[])
    current_medications: list[str] = Field(default=[])
    allergies: list[str] = Field(default=[])
    vitals: dict = Field(default={})


class SessionResponse(BaseModel):
    session_id: str
    status: str
    message: str


class ReviewRequest(BaseModel):
    approved: bool
    reviewer_name: str = Field(default="Dr. Reviewer")
    reviewer_notes: str = Field(default="")
    modifications: str = Field(default="")


# ── In-Memory Session Store (use Redis/DB in production) ──────────────────────
sessions: dict[str, dict] = {}


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MediMind API", "version": "1.0.0"}


@app.post("/sessions", response_model=SessionResponse)
async def create_session(request: StartSessionRequest):
    """
    Create a new patient session and start the clinical AI workflow.
    Returns a session_id to track progress.
    """
    session_id = str(uuid.uuid4())

    patient_info: PatientInfo = {
        "patient_id": session_id,
        "name": request.patient_name,
        "age": request.patient_age,
        "gender": request.patient_gender,
        "symptoms": request.symptoms,
        "symptom_duration": request.symptom_duration,
        "severity": request.severity,
        "medical_history": request.medical_history,
        "current_medications": request.current_medications,
        "allergies": request.allergies,
        "vitals": request.vitals,
    }

    initial_state: AgentState = {
        "messages": [],
        "session_id": session_id,
        "patient_info": patient_info,
        "triage_result": None,
        "diagnosis_result": None,
        "treatment_result": None,
        "note_summary": None,
        "human_review": None,
        "awaiting_human_review": False,
        "current_agent": "init",
        "next_agent": None,
        "error": None,
        "completed": False,
        "run_id": None,
    }

    sessions[session_id] = {
        "state": initial_state,
        "status": "created",
    }

    return SessionResponse(
        session_id=session_id,
        status="created",
        message=f"Session created for {request.patient_name}. Connect to /sessions/{session_id}/stream to start.",
    )


@app.get("/sessions/{session_id}/stream")
async def stream_session(session_id: str):
    """
    Server-Sent Events endpoint for real-time agent streaming.
    Connect here to receive live updates from each agent as they run.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events as agents run."""
        session = sessions[session_id]

        # If session is already completed, return final state immediately
        if session.get("status") == "completed":
            state = session["state"]
            payload = {
                "event": "completed",
                "current_agent": "supervisor",
                "completed": True,
                "message": "Clinical assessment complete.",
                "triage": state.get("triage_result"),
                "diagnosis": state.get("diagnosis_result"),
                "treatment": state.get("treatment_result"),
                "note_summary": state.get("note_summary"),
                "human_review": state.get("human_review"),
            }
            yield f"data: {json.dumps(payload)}\n\n"
            return

        graph = get_graph()
        initial_state = session["state"]
        config = {"configurable": {"thread_id": session_id}}

        try:
            # Stream graph execution
            async for event in graph.astream(initial_state, config=config, stream_mode="values"):
                current_agent = event.get("current_agent", "unknown")
                next_agent = event.get("next_agent")

                # Build SSE payload
                payload = {
                    "event": "agent_update",
                    "current_agent": current_agent,
                    "next_agent": next_agent,
                    "triage_complete": event.get("triage_result") is not None,
                    "diagnosis_complete": event.get("diagnosis_result") is not None,
                    "treatment_complete": event.get("treatment_result") is not None,
                    "note_complete": event.get("note_summary") is not None,
                    "awaiting_review": event.get("awaiting_human_review", False),
                    "completed": event.get("completed", False),
                    "error": event.get("error"),
                }

                # Include agent-specific data
                if event.get("triage_result"):
                    payload["triage"] = event["triage_result"]
                if event.get("diagnosis_result"):
                    payload["diagnosis"] = event["diagnosis_result"]
                if event.get("treatment_result"):
                    payload["treatment"] = event["treatment_result"]
                if event.get("note_summary"):
                    payload["note_summary"] = event["note_summary"]
                if event.get("human_review"):
                    payload["human_review"] = event["human_review"]

                # Update session state
                sessions[session_id]["state"] = event
                sessions[session_id]["status"] = "awaiting_review" if event.get("awaiting_human_review") else "running"

                # If completed or awaiting review, update status in payload before yielding
                if event.get("awaiting_human_review"):
                    sessions[session_id]["status"] = "awaiting_review"
                    payload["event"] = "awaiting_human_review"
                    payload["message"] = "Workflow paused. Awaiting doctor review."
                    yield f"data: {json.dumps(payload)}\n\n"
                    return

                if event.get("completed"):
                    sessions[session_id]["status"] = "completed"
                    payload["event"] = "completed"
                    payload["message"] = "Clinical assessment complete."
                    yield f"data: {json.dumps(payload)}\n\n"
                    return

                yield f"data: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.1)  # Small delay for UI updates

        except Exception as e:
            traceback.print_exc()
            sessions[session_id]["status"] = "error"
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get current state of a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    state = session["state"]

    return {
        "session_id": session_id,
        "status": session["status"],
        "patient_name": state.get("patient_info", {}).get("name", "Unknown"),
        "triage": state.get("triage_result"),
        "diagnosis": state.get("diagnosis_result"),
        "treatment": state.get("treatment_result"),
        "note_summary": state.get("note_summary"),
        "human_review": state.get("human_review"),
        "awaiting_human_review": state.get("awaiting_human_review", False),
        "completed": state.get("completed", False),
        "error": state.get("error"),
    }


@app.post("/sessions/{session_id}/review")
async def submit_human_review(session_id: str, request: ReviewRequest):
    """
    Submit doctor's review decision (Human-in-the-Loop).
    This resumes the paused LangGraph workflow.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    if session["status"] != "awaiting_review":
        raise HTTPException(
            status_code=400,
            detail=f"Session is not awaiting review. Current status: {session['status']}"
        )

    review_decision: HumanReviewDecision = {
        "approved": request.approved,
        "reviewer_name": request.reviewer_name,
        "reviewer_notes": request.reviewer_notes,
        "modifications": request.modifications if request.modifications else None,
    }

    # Inject review decision into state and resume graph
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    # Update state with human decision
    updated_state = {
        **session["state"],
        "human_review": review_decision,
        "awaiting_human_review": False,
    }

    # Resume the graph from the human_review checkpoint
    await graph.aupdate_state(config, updated_state)

    # Stream remaining steps
    sessions[session_id]["status"] = "running"
    sessions[session_id]["state"] = updated_state

    action = "approved" if request.approved else "rejected"
    return {
        "session_id": session_id,
        "status": "resumed",
        "review_decision": action,
        "message": f"Review {action}. Stream /sessions/{session_id}/stream-review to see completion.",
    }


@app.get("/sessions/{session_id}/stream-review")
async def stream_review_completion(session_id: str):
    """Stream the remaining workflow after human review decision."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    async def review_event_generator() -> AsyncGenerator[str, None]:
        graph = get_graph()
        config = {"configurable": {"thread_id": session_id}}

        try:
            async for event in graph.astream(None, config=config, stream_mode="values"):
                payload = {
                    "event": "agent_update",
                    "current_agent": event.get("current_agent", "unknown"),
                    "completed": event.get("completed", False),
                    "human_review": event.get("human_review"),
                    "triage": event.get("triage_result"),
                    "diagnosis": event.get("diagnosis_result"),
                    "treatment": event.get("treatment_result"),
                    "note_summary": event.get("note_summary"),
                }

                sessions[session_id]["state"] = event
                if event.get("completed"):
                    sessions[session_id]["status"] = "completed"
                    payload["event"] = "completed"
                    payload["message"] = "Clinical assessment finalized."

                yield f"data: {json.dumps(payload)}\n\n"

                if event.get("completed"):
                    return

                await asyncio.sleep(0.1)

        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        review_event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/sessions")
async def list_sessions():
    """List all active sessions (for dashboard)."""
    return {
        "sessions": [
            {
                "session_id": sid,
                "status": data["status"],
                "patient_name": data["state"].get("patient_info", {}).get("name", "Unknown"),
                "priority": data["state"].get("triage_result", {}).get("priority") if data["state"].get("triage_result") else None,
            }
            for sid, data in sessions.items()
        ],
        "total": len(sessions),
    }


# ── MCP (Model Context Protocol) Endpoints ────────────────────────────────────

@app.get("/api/mcp/tools", tags=["Model Context Protocol (MCP)"])
async def list_mcp_tools():
    """
    List all clinical tools dynamically exposed by the MediMind MCP Server.
    Demonstrates LangGraph MCP Client tool discovery over stdio JSON-RPC transport.
    """
    from backend.mcp_client.client import get_clinical_mcp_tools
    try:
        tools = await get_clinical_mcp_tools()
        return {
            "mcp_server": "MediMind Clinical Intelligence Server",
            "protocol_version": "2024-11-05",
            "transport": "stdio",
            "total_tools": len(tools),
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.args if hasattr(t, "args") else {},
                }
                for t in tools
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query MCP tools: {str(e)}")


@app.get("/api/mcp/resources", tags=["Model Context Protocol (MCP)"])
async def list_mcp_resources():
    """
    List all clinical resources (guidelines, lab ranges) available via MCP custom URIs.
    """
    from backend.mcp_client.client import get_mcp_client
    try:
        client = get_mcp_client()
        resources = await client.get_resources()
        return {
            "mcp_server": "MediMind Clinical Intelligence Server",
            "total_resources": len(resources),
            "resources": [
                {
                    "uri": str(r.metadata.get("uri")),
                    "name": getattr(r, "name", str(r.metadata.get("uri"))),
                    "mime_type": getattr(r, "mime_type", "text/plain"),
                }
                for r in resources
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list MCP resources: {str(e)}")


@app.get("/api/mcp/resources/read", tags=["Model Context Protocol (MCP)"])
async def read_mcp_resource(uri: str):
    """
    Read content from an MCP Clinical Resource URI (e.g. 'clinical://guidelines/triage-protocol').
    """
    from backend.mcp_client.client import read_clinical_resource
    try:
        content = await read_clinical_resource(uri)
        if "Resource not found" in content:
            raise HTTPException(status_code=404, detail=content)
        return {
            "uri": uri,
            "content": content,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read MCP resource: {str(e)}")

