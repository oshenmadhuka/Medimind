"""
MediMind — Supervisor Agent
The central orchestrator that routes between specialized clinical agents.
Uses a structured LLM call to decide which agent to invoke next.
"""
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal

from backend.graph.state import AgentState
from backend.core.config import settings


# ── Routing Schema ────────────────────────────────────────────────────────────

class SupervisorDecision(BaseModel):
    """Structured output for supervisor routing."""
    next: Literal["triage_agent", "diagnosis_agent", "treatment_agent",
                  "note_summarizer", "human_review", "END"]
    reasoning: str = Field(description="Why this agent was selected next")


# ── Supervisor Prompt ─────────────────────────────────────────────────────────

SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor Agent for MediMind, an AI-powered clinical 
decision support system. Your role is to orchestrate a team of specialized medical AI agents 
to provide comprehensive clinical assessments.

## Your Team of Agents:
1. **triage_agent** — Classifies patient urgency (P1-Critical to P4-Non-Urgent)
2. **diagnosis_agent** — Generates differential diagnoses using medical evidence (RAG)
3. **treatment_agent** — Creates treatment plans and checks drug interactions
4. **note_summarizer** — Summarizes clinical notes and findings
5. **human_review** — Routes to a human doctor for final approval
6. **END** — Marks the workflow as complete

## Routing Rules:
- ALWAYS start with `triage_agent` for new patients
- After triage: route to `diagnosis_agent`
- After diagnosis: route to `treatment_agent`
- After treatment: route to `note_summarizer`
- After summarization: route to `human_review`
- If human approved: route to `END`
- If human rejected with modifications: route back to `diagnosis_agent`
- If P1 (Critical) patient: route directly to `human_review` FIRST, then continue

## Current State:
{state_summary}

Based on the current state, decide which agent should act next.
"""


# ── Supervisor Node ───────────────────────────────────────────────────────────

def create_supervisor_llm():
    """Create LLM with structured output for routing decisions."""
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,
    )
    return llm.with_structured_output(SupervisorDecision)


def build_state_summary(state: AgentState) -> str:
    """Build a human-readable summary of current state for the supervisor."""
    lines = []
    lines.append(f"Session: {state.get('session_id', 'unknown')}")

    if state.get("patient_info"):
        p = state["patient_info"]
        lines.append(f"Patient: {p.get('name', 'Unknown')}, Age: {p.get('age')}")
        lines.append(f"Symptoms: {', '.join(p.get('symptoms', []))}")

    lines.append(f"Triage Complete: {state.get('triage_result') is not None}")
    if state.get("triage_result"):
        lines.append(f"Priority: {state['triage_result'].get('priority', 'Unknown')}")

    lines.append(f"Diagnosis Complete: {state.get('diagnosis_result') is not None}")
    lines.append(f"Treatment Complete: {state.get('treatment_result') is not None}")
    lines.append(f"Note Summary Complete: {state.get('note_summary') is not None}")
    lines.append(f"Awaiting Human Review: {state.get('awaiting_human_review', False)}")

    if state.get("human_review"):
        lines.append(f"Human Review Decision: {'Approved' if state['human_review']['approved'] else 'Rejected'}")

    return "\n".join(lines)


def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor node — determines which agent to call next.
    This is the central router of the LangGraph workflow.
    """
    print(f"\n{'='*50}")
    print("🧠 SUPERVISOR: Analyzing state and routing...")

    # If already completed, go to END
    if state.get("completed"):
        return {**state, "next_agent": "END", "current_agent": "supervisor"}

    # If human just approved, end the workflow
    if state.get("human_review") and state["human_review"].get("approved"):
        print("✅ Human approved — workflow complete")
        return {**state, "next_agent": "END", "current_agent": "supervisor", "completed": True}

    llm = create_supervisor_llm()
    state_summary = build_state_summary(state)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_SYSTEM_PROMPT),
        ("human", "What is the next agent to invoke?"),
    ])

    chain = prompt | llm
    decision: SupervisorDecision = chain.invoke({"state_summary": state_summary})

    print(f"🔀 Routing to: {decision.next}")
    print(f"📋 Reasoning: {decision.reasoning}")

    return {
        **state,
        "next_agent": decision.next,
        "current_agent": "supervisor",
    }


def route_from_supervisor(state: AgentState) -> str:
    """
    Conditional edge function — returns the next node name based on
    the supervisor's routing decision.
    """
    next_agent = state.get("next_agent", "END")
    return next_agent
