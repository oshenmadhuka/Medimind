"""
MediMind — Triage Agent
Classifies patient urgency using clinical triage protocols.
Priority levels: P1 (Critical) → P4 (Non-Urgent)
"""
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal

from backend.graph.state import AgentState, TriageResult
from backend.core.config import settings


# ── Triage Output Schema ──────────────────────────────────────────────────────

class TriageOutput(BaseModel):
    priority: Literal["P1", "P2", "P3", "P4"] = Field(
        description="Triage priority level"
    )
    priority_label: str = Field(
        description="Human readable label: Critical | Urgent | Semi-Urgent | Non-Urgent"
    )
    reasoning: str = Field(
        description="Clinical reasoning for the priority assignment"
    )
    escalate_immediately: bool = Field(
        description="True if patient needs immediate emergency escalation"
    )
    red_flags: list[str] = Field(
        default=[],
        description="Critical warning signs identified"
    )
    vital_concerns: list[str] = Field(
        default=[],
        description="Concerning vital sign abnormalities"
    )


# ── Triage Prompt ─────────────────────────────────────────────────────────────

TRIAGE_SYSTEM_PROMPT = """You are an expert Emergency Medicine Physician and Triage Specialist 
with 20+ years of experience in clinical triage. You follow evidence-based triage protocols
including the Manchester Triage System (MTS) and Emergency Severity Index (ESI).

## Triage Priority Levels:
- **P1 - CRITICAL**: Life-threatening condition. Immediate intervention required.
  Examples: cardiac arrest, stroke, severe respiratory distress, septic shock
  
- **P2 - URGENT**: Potentially life-threatening. Seen within 10-15 minutes.
  Examples: chest pain, high fever, acute abdominal pain, altered consciousness
  
- **P3 - SEMI-URGENT**: Stable but needs timely care. Seen within 30-60 minutes.
  Examples: moderate pain, vomiting, minor trauma, UTI symptoms
  
- **P4 - NON-URGENT**: Minor illness. Can wait 1-2 hours.
  Examples: mild cold, routine check, minor skin conditions

## RED FLAGS to always escalate to P1/P2:
- Chest pain + shortness of breath
- Sudden severe headache ("thunderclap")
- Facial drooping, arm weakness, speech difficulty (stroke signs)
- SpO2 < 92%
- Systolic BP < 90 or > 200
- Temperature > 40°C or < 35°C
- Altered mental status
- Signs of anaphylaxis

Analyze the patient information carefully and assign the most appropriate triage priority.
Be conservative — when in doubt, escalate to a higher priority.
"""

TRIAGE_HUMAN_PROMPT = """
## Patient Information:
- **Name**: {name}
- **Age**: {age} years
- **Gender**: {gender}

## Chief Complaint & Symptoms:
{symptoms}

## Symptom Duration: {duration}
## Reported Severity: {severity}

## Vitals:
{vitals}

## Relevant Medical History:
{medical_history}

## Current Medications:
{medications}

Please perform a clinical triage assessment and assign the appropriate priority level.
"""


# ── Triage Agent Node ─────────────────────────────────────────────────────────

def triage_agent_node(state: AgentState) -> AgentState:
    """
    Triage Agent Node — classifies patient urgency.
    Runs first in the pipeline for all new patients.
    """
    print("\n🚨 TRIAGE AGENT: Assessing patient urgency...")

    patient = state.get("patient_info")
    if not patient:
        return {**state, "error": "No patient information found for triage"}

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,
    ).with_structured_output(TriageOutput)

    # Format vitals nicely
    vitals = patient.get("vitals", {})
    vitals_str = "\n".join([f"- {k.upper()}: {v}" for k, v in vitals.items()]) or "Not provided"

    prompt = ChatPromptTemplate.from_messages([
        ("system", TRIAGE_SYSTEM_PROMPT),
        ("human", TRIAGE_HUMAN_PROMPT),
    ])

    chain = prompt | llm

    result: TriageOutput = chain.invoke({
        "name": patient.get("name", "Unknown"),
        "age": patient.get("age", "Unknown"),
        "gender": patient.get("gender", "Unknown"),
        "symptoms": "\n".join([f"• {s}" for s in patient.get("symptoms", [])]),
        "duration": patient.get("symptom_duration", "Not specified"),
        "severity": patient.get("severity", "Not specified"),
        "vitals": vitals_str,
        "medical_history": "\n".join([f"• {h}" for h in patient.get("medical_history", [])]) or "None reported",
        "medications": "\n".join([f"• {m}" for m in patient.get("current_medications", [])]) or "None",
    })

    triage_result: TriageResult = {
        "priority": result.priority,
        "priority_label": result.priority_label,
        "reasoning": result.reasoning,
        "escalate_immediately": result.escalate_immediately,
    }

    emoji_map = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}
    print(f"{emoji_map.get(result.priority, '⚪')} Priority: {result.priority} — {result.priority_label}")
    if result.red_flags:
        print(f"⚠️  Red flags: {', '.join(result.red_flags)}")

    from langchain_core.messages import AIMessage
    triage_message = AIMessage(
        content=f"**Triage Assessment Complete**\n\n"
                f"Priority: {result.priority} — {result.priority_label}\n\n"
                f"Reasoning: {result.reasoning}\n\n"
                f"Red Flags: {', '.join(result.red_flags) if result.red_flags else 'None identified'}\n"
                f"Immediate Escalation Required: {'YES ⚠️' if result.escalate_immediately else 'No'}",
        name="triage_agent"
    )

    return {
        **state,
        "triage_result": triage_result,
        "current_agent": "triage_agent",
        "messages": [*state.get("messages", []), triage_message],
    }
