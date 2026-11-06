"""
MediMind — LangGraph State Schema
Defines the shared state that flows between all agents in the graph.
"""
from typing import TypedDict, Annotated, Sequence, Optional, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class PatientInfo(TypedDict):
    """Structured patient intake data."""
    patient_id: str
    name: str
    age: int
    gender: str
    symptoms: list[str]
    symptom_duration: str          # e.g. "3 days", "2 weeks"
    severity: str                  # mild | moderate | severe
    medical_history: list[str]     # past conditions
    current_medications: list[str]
    allergies: list[str]
    vitals: dict                   # {"bp": "120/80", "temp": "38.5", "spo2": "98"}


class TriageResult(TypedDict):
    """Output of the Triage Agent."""
    priority: Literal["P1", "P2", "P3", "P4"]
    priority_label: str            # Critical | Urgent | Semi-Urgent | Non-Urgent
    reasoning: str
    escalate_immediately: bool


class DiagnosisResult(TypedDict):
    """Output of the Diagnosis Agent."""
    primary_diagnosis: str
    icd10_code: str
    confidence: float              # 0.0 – 1.0
    differential_diagnoses: list[dict]  # [{"name": ..., "likelihood": ...}]
    supporting_evidence: list[str]      # RAG-retrieved evidence
    red_flags: list[str]


class TreatmentResult(TypedDict):
    """Output of the Treatment Agent."""
    treatment_plan: list[str]
    medications: list[dict]        # [{"name": ..., "dose": ..., "duration": ...}]
    drug_interactions: list[str]   # warnings from OpenFDA
    follow_up_timeline: str
    lifestyle_recommendations: list[str]
    referrals: list[str]


class ClinicalNoteSummary(TypedDict):
    """Output of the Note Summarizer Agent."""
    summary: str
    key_findings: list[str]
    action_items: list[str]
    references: list[str]          # PubMed article references used


class HumanReviewDecision(TypedDict):
    """Doctor's review decision (human-in-the-loop)."""
    approved: bool
    reviewer_name: str
    reviewer_notes: str
    modifications: Optional[str]


class AgentState(TypedDict):
    """
    Central state object shared across all LangGraph nodes.
    Every agent reads from and writes to this state.
    """
    # ── Conversation ──────────────────────────────────────────────────
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str

    # ── Patient Data ──────────────────────────────────────────────────
    patient_info: Optional[PatientInfo]

    # ── Agent Outputs ─────────────────────────────────────────────────
    triage_result: Optional[TriageResult]
    diagnosis_result: Optional[DiagnosisResult]
    treatment_result: Optional[TreatmentResult]
    note_summary: Optional[ClinicalNoteSummary]

    # ── Human-in-the-Loop ─────────────────────────────────────────────
    human_review: Optional[HumanReviewDecision]
    awaiting_human_review: bool

    # ── Routing & Control ─────────────────────────────────────────────
    current_agent: str             # tracks which agent is active
    next_agent: Optional[str]      # supervisor routing decision
    error: Optional[str]           # error messages
    completed: bool                # marks workflow as done

    # ── Metadata ──────────────────────────────────────────────────────
    run_id: Optional[str]          # LangSmith run ID for tracing
