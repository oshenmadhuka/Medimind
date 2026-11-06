"""
MediMind — Clinical Note Summarizer Agent
Summarizes all clinical findings into a structured clinical note using RAG.
Produces a final SOAP-format note ready for doctor review.
"""
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from backend.graph.state import AgentState, ClinicalNoteSummary
from backend.tools.pubmed_rag import retrieve_medical_evidence
from backend.core.config import settings


# ── Note Output Schema ────────────────────────────────────────────────────────

class ClinicalNoteOutput(BaseModel):
    soap_note: str = Field(description="Full SOAP format clinical note")
    summary: str = Field(description="Brief executive summary (2-3 sentences)")
    key_findings: list[str] = Field(description="Critical clinical findings")
    action_items: list[str] = Field(description="Immediate action items for the care team")
    references: list[str] = Field(description="Clinical guidelines referenced in the assessment")
    discharge_instructions: list[str] = Field(
        description="Patient discharge/take-home instructions"
    )


# ── Note Summarizer Prompt ────────────────────────────────────────────────────

NOTE_SUMMARIZER_SYSTEM = """You are an expert Medical Scribe and Clinical Documentation Specialist.
You create precise, professional clinical notes in SOAP format following medical documentation best practices.

## SOAP Note Format:
**S (Subjective)**: Patient's chief complaint, symptoms, history of present illness
**O (Objective)**: Vitals, exam findings, lab results, triage priority
**A (Assessment)**: Diagnosis with ICD-10 code, differential diagnoses, clinical reasoning
**P (Plan)**: Treatment plan, medications, referrals, follow-up

## Documentation Standards:
- Use precise medical terminology
- Be factual and concise — avoid speculation
- Document all relevant positive and negative findings
- Include clinical decision reasoning
- Reference evidence-based guidelines used

## Medical Evidence Available:
{retrieved_evidence}
"""

NOTE_SUMMARIZER_HUMAN = """
Please create a comprehensive clinical note for this patient encounter.

## Patient: {name} | {age}y | {gender}

## Subjective:
- Chief Complaint: {symptoms}
- Duration: {duration} | Severity: {severity}
- Medical History: {medical_history}
- Medications: {medications}
- Allergies: {allergies}

## Objective:
- Vitals: {vitals}
- Triage Priority: {priority} ({priority_label})

## Assessment:
- Primary Diagnosis: {primary_diagnosis} ({icd10_code})
- Confidence: {confidence}%
- Differential Diagnoses: {differentials}
- Red Flags: {red_flags}

## Plan:
- Treatment: {treatment_plan}
- Medications: {medications_plan}
- Follow-up: {follow_up}
- Referrals: {referrals}
- Drug Interaction Alerts: {drug_alerts}

Generate a complete, professional clinical note with action items.
"""


# ── Note Summarizer Node ──────────────────────────────────────────────────────

def note_summarizer_node(state: AgentState) -> AgentState:
    """
    Note Summarizer Agent Node — creates SOAP clinical note.
    Synthesizes all agent outputs into a professional clinical document.
    """
    print("\n📋 NOTE SUMMARIZER: Generating clinical documentation...")

    patient = state.get("patient_info")
    triage = state.get("triage_result")
    diagnosis = state.get("diagnosis_result")
    treatment = state.get("treatment_result")

    if not all([patient, triage, diagnosis, treatment]):
        return {**state, "error": "Missing required data for note generation"}

    # RAG for relevant guidelines to reference
    evidence_docs = retrieve_medical_evidence.invoke({
        "query": f"clinical guidelines {diagnosis['primary_diagnosis']}",
        "n_results": 2,
    })
    evidence_text = "\n".join([
        f"• {doc.get('source', 'Unknown')}: {doc.get('content', '')[:200]}..."
        for doc in evidence_docs
    ])

    # Format data for prompt
    differentials_str = "; ".join([
        f"{d.get('name', '')} ({d.get('likelihood', '')})"
        for d in diagnosis.get("differential_diagnoses", [])[:3]
    ])

    meds_str = "; ".join([
        f"{m.get('name', '')} {m.get('dose', '')} {m.get('frequency', '')}"
        for m in treatment.get("medications", [])
    ])

    vitals = patient.get("vitals", {})
    vitals_str = ", ".join([f"{k.upper()}: {v}" for k, v in vitals.items() if k != "labs"])

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.1,
    ).with_structured_output(ClinicalNoteOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", NOTE_SUMMARIZER_SYSTEM),
        ("human", NOTE_SUMMARIZER_HUMAN),
    ])

    chain = prompt | llm
    result: ClinicalNoteOutput = chain.invoke({
        "retrieved_evidence": evidence_text,
        "name": patient.get("name", "Patient"),
        "age": patient.get("age", "Unknown"),
        "gender": patient.get("gender", "Unknown"),
        "symptoms": ", ".join(patient.get("symptoms", [])),
        "duration": patient.get("symptom_duration", "Not specified"),
        "severity": patient.get("severity", "Not specified"),
        "medical_history": ", ".join(patient.get("medical_history", [])) or "None",
        "medications": ", ".join(patient.get("current_medications", [])) or "None",
        "allergies": ", ".join(patient.get("allergies", [])) or "None",
        "vitals": vitals_str or "Not recorded",
        "priority": triage.get("priority", "Unknown"),
        "priority_label": triage.get("priority_label", "Unknown"),
        "primary_diagnosis": diagnosis.get("primary_diagnosis", "Unknown"),
        "icd10_code": diagnosis.get("icd10_code", "Unknown"),
        "confidence": int(diagnosis.get("confidence", 0) * 100),
        "differentials": differentials_str or "None",
        "red_flags": ", ".join(diagnosis.get("red_flags", [])) or "None identified",
        "treatment_plan": "; ".join(treatment.get("treatment_plan", [])[:3]),
        "medications_plan": meds_str or "None prescribed",
        "follow_up": treatment.get("follow_up_timeline", "As needed"),
        "referrals": ", ".join(treatment.get("referrals", [])) or "None",
        "drug_alerts": ", ".join(treatment.get("drug_interactions", [])) or "None",
    })

    # Build references list
    references = [doc.get("source", "Unknown") for doc in evidence_docs]
    references.extend(result.references[:3])

    note_summary: ClinicalNoteSummary = {
        "summary": result.summary,
        "key_findings": result.key_findings,
        "action_items": result.action_items,
        "references": list(set(references)),  # deduplicate
    }

    print(f"✅ Clinical note generated ({len(result.soap_note)} chars)")
    print(f"📌 {len(result.action_items)} action items identified")

    note_message = AIMessage(
        content=f"**Clinical Note Complete — Pending Doctor Review**\n\n"
                f"**Summary:** {result.summary}\n\n"
                f"**Key Findings:**\n" + "\n".join([f"• {f}" for f in result.key_findings]) +
                f"\n\n**Action Items:**\n" + "\n".join([f"• {a}" for a in result.action_items]) +
                f"\n\n**SOAP Note:**\n{result.soap_note[:800]}...\n\n"
                f"*Routing to doctor for final review and approval.*",
        name="note_summarizer",
        additional_kwargs={"soap_note": result.soap_note, "discharge_instructions": result.discharge_instructions}
    )

    return {
        **state,
        "note_summary": note_summary,
        "awaiting_human_review": True,
        "current_agent": "note_summarizer",
        "messages": [*state.get("messages", []), note_message],
    }
