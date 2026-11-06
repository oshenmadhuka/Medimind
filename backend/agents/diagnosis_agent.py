"""
MediMind — Diagnosis Agent
Generates differential diagnoses using RAG over medical literature.
Uses tool calling + LLM to produce evidence-backed diagnosis.
"""
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from backend.graph.state import AgentState, DiagnosisResult
from backend.tools.pubmed_rag import retrieve_medical_evidence
from backend.tools.icd10_lookup import lookup_icd10_code
from backend.tools.lab_interpreter import interpret_lab_values
from backend.core.config import settings


# ── Diagnosis Output Schema ───────────────────────────────────────────────────

class DifferentialItem(BaseModel):
    name: str
    likelihood: str       # High | Medium | Low
    reasoning: str


class DiagnosisOutput(BaseModel):
    primary_diagnosis: str = Field(description="The most likely diagnosis")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    differential_diagnoses: list[DifferentialItem] = Field(
        description="List of differential diagnoses ranked by likelihood"
    )
    supporting_evidence: list[str] = Field(
        description="Key clinical findings and evidence supporting the diagnosis"
    )
    red_flags: list[str] = Field(
        default=[],
        description="Clinical red flags identified that need immediate attention"
    )
    recommended_investigations: list[str] = Field(
        description="Additional tests/investigations recommended to confirm diagnosis"
    )


# ── Diagnosis Prompt ──────────────────────────────────────────────────────────

DIAGNOSIS_SYSTEM_PROMPT = """You are a world-class Internal Medicine specialist and clinical diagnostician
with expertise across all medical specialties. You follow evidence-based medicine principles 
and use systematic clinical reasoning (history → examination → investigations → diagnosis).

## Your Diagnostic Approach:
1. **Symptom Analysis**: Analyze the pattern, onset, duration, severity, and associated symptoms
2. **Clinical Reasoning**: Use Bayesian reasoning — consider pre-test probability for each condition
3. **Red Flag Recognition**: Actively screen for dangerous conditions that must not be missed
4. **Evidence-Based**: Ground your diagnoses in current medical evidence and guidelines
5. **Differential Diagnosis**: Always consider at least 3-5 differential diagnoses

## Medical Evidence Retrieved:
{retrieved_evidence}

## Critical Rules:
- Never make a definitive diagnosis without adequate clinical evidence
- Always consider "must-not-miss" diagnoses even if less likely
- Note when diagnosis is uncertain and requires further investigation
- Consider patient-specific factors (age, gender, comorbidities, medications)
"""

DIAGNOSIS_HUMAN_PROMPT = """
## Patient Details:
- Name: {name} | Age: {age} | Gender: {gender}
- Priority (Triage): {priority}

## Chief Complaint & Symptoms:
{symptoms}

## Duration: {duration} | Severity: {severity}

## Vitals:
{vitals}

## Medical History: {medical_history}
## Current Medications: {medications}
## Allergies: {allergies}

## Lab Results (if available):
{labs}

Based on the clinical presentation and medical evidence above, 
provide a comprehensive differential diagnosis with your primary diagnosis.
"""


# ── Diagnosis Agent Node ──────────────────────────────────────────────────────

def diagnosis_agent_node(state: AgentState) -> AgentState:
    """
    Diagnosis Agent Node — generates differential diagnoses.
    Uses RAG to retrieve relevant medical evidence before diagnosing.
    """
    print("\n🔬 DIAGNOSIS AGENT: Generating differential diagnosis...")

    patient = state.get("patient_info")
    triage = state.get("triage_result")

    if not patient:
        return {**state, "error": "No patient information for diagnosis"}

    # ── Step 1: RAG — Retrieve Medical Evidence ───────────────────────────────
    symptoms_text = ", ".join(patient.get("symptoms", []))
    rag_query = f"{symptoms_text} in {patient.get('age')} year old {patient.get('gender')}"

    print(f"📚 Retrieving evidence for: {rag_query}")
    evidence_docs = retrieve_medical_evidence.invoke({
        "query": rag_query,
        "n_results": 3,
    })

    evidence_text = "\n\n".join([
        f"**{doc.get('source', 'Unknown')}** (Relevance: {doc.get('relevance_score', 0):.2f}):\n{doc.get('content', '')}"
        for doc in evidence_docs
    ])

    # ── Step 2: Lab Interpretation (if labs available) ────────────────────────
    vitals = patient.get("vitals", {})
    labs_str = "No lab results provided"
    if vitals.get("labs"):
        lab_results = interpret_lab_values.invoke({
            "lab_results": vitals["labs"],
            "gender": patient.get("gender", "unknown"),
        })
        labs_str = lab_results.get("summary", "Labs interpreted")

    # ── Step 3: LLM Diagnosis Generation ─────────────────────────────────────
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.1,
    ).with_structured_output(DiagnosisOutput)

    vitals_str = "\n".join([f"- {k.upper()}: {v}" for k, v in vitals.items() if k != "labs"]) or "Not provided"

    prompt = ChatPromptTemplate.from_messages([
        ("system", DIAGNOSIS_SYSTEM_PROMPT),
        ("human", DIAGNOSIS_HUMAN_PROMPT),
    ])

    chain = prompt | llm
    result: DiagnosisOutput = chain.invoke({
        "retrieved_evidence": evidence_text,
        "name": patient.get("name", "Patient"),
        "age": patient.get("age", "Unknown"),
        "gender": patient.get("gender", "Unknown"),
        "priority": triage.get("priority", "Unknown") if triage else "Not triaged",
        "symptoms": "\n".join([f"• {s}" for s in patient.get("symptoms", [])]),
        "duration": patient.get("symptom_duration", "Not specified"),
        "severity": patient.get("severity", "Not specified"),
        "vitals": vitals_str,
        "medical_history": ", ".join(patient.get("medical_history", [])) or "None",
        "medications": ", ".join(patient.get("current_medications", [])) or "None",
        "allergies": ", ".join(patient.get("allergies", [])) or "None",
        "labs": labs_str,
    })

    # ── Step 4: ICD-10 Code Lookup ────────────────────────────────────────────
    icd10_result = lookup_icd10_code.invoke({"diagnosis": result.primary_diagnosis})
    icd10_code = icd10_result.get("icd10_code", "Z99.9")

    print(f"✅ Primary Diagnosis: {result.primary_diagnosis} ({icd10_code})")
    print(f"📊 Confidence: {result.confidence:.0%}")

    diagnosis_result: DiagnosisResult = {
        "primary_diagnosis": result.primary_diagnosis,
        "icd10_code": icd10_code,
        "confidence": result.confidence,
        "differential_diagnoses": [
            {"name": d.name, "likelihood": d.likelihood, "reasoning": d.reasoning}
            for d in result.differential_diagnoses
        ],
        "supporting_evidence": result.supporting_evidence,
        "red_flags": result.red_flags,
    }

    # Build differentials display
    differentials_text = "\n".join([
        f"• {d.name} ({d.likelihood} likelihood): {d.reasoning}"
        for d in result.differential_diagnoses
    ])

    diagnosis_message = AIMessage(
        content=f"**Diagnosis Assessment Complete**\n\n"
                f"🎯 **Primary Diagnosis**: {result.primary_diagnosis} `{icd10_code}`\n"
                f"📊 **Confidence**: {result.confidence:.0%}\n\n"
                f"**Differential Diagnoses:**\n{differentials_text}\n\n"
                f"**Red Flags:** {', '.join(result.red_flags) if result.red_flags else 'None'}\n\n"
                f"**Recommended Investigations:** {', '.join(result.recommended_investigations)}",
        name="diagnosis_agent"
    )

    return {
        **state,
        "diagnosis_result": diagnosis_result,
        "current_agent": "diagnosis_agent",
        "messages": [*state.get("messages", []), diagnosis_message],
    }
