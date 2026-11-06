"""
MediMind — Treatment Agent
Generates evidence-based treatment plans and checks for drug interactions.
"""
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from backend.graph.state import AgentState, TreatmentResult
from backend.tools.drug_interaction import check_drug_interactions
from backend.tools.pubmed_rag import retrieve_medical_evidence
from backend.core.config import settings


# ── Treatment Output Schema ───────────────────────────────────────────────────

class MedicationItem(BaseModel):
    name: str
    dose: str
    route: str          # oral | IV | IM | topical | inhaled
    frequency: str
    duration: str
    indication: str


class TreatmentOutput(BaseModel):
    treatment_plan: list[str] = Field(description="Step-by-step treatment plan")
    medications: list[MedicationItem] = Field(description="Medications to prescribe")
    follow_up_timeline: str = Field(description="When patient should follow up")
    lifestyle_recommendations: list[str] = Field(
        description="Diet, exercise, lifestyle modifications"
    )
    referrals: list[str] = Field(
        default=[],
        description="Specialist referrals needed"
    )
    monitoring_parameters: list[str] = Field(
        description="Parameters to monitor during treatment"
    )
    patient_education: list[str] = Field(
        description="Key points to educate patient about"
    )


# ── Treatment Prompt ──────────────────────────────────────────────────────────

TREATMENT_SYSTEM_PROMPT = """You are an expert Clinical Pharmacologist and Internal Medicine Specialist
with deep expertise in evidence-based treatment protocols.

You create comprehensive, safe treatment plans following current clinical guidelines.

## Key Principles:
1. **Evidence-Based**: Follow latest clinical guidelines (ACC/AHA, IDSA, WHO, etc.)
2. **Safety First**: Always check for contraindications with patient's existing medications
3. **Patient-Centered**: Consider patient's comorbidities, allergies, and lifestyle
4. **Stepped Approach**: Start with first-line therapy; outline escalation path
5. **Monitoring**: Always specify what to monitor and when

## Medical Evidence Retrieved:
{retrieved_evidence}

## Drug Interaction Alerts:
{drug_interaction_alerts}

IMPORTANT: If drug interaction alerts exist, explicitly address them in your treatment plan.
"""

TREATMENT_HUMAN_PROMPT = """
## Patient: {name} | Age: {age} | Gender: {gender}

## Confirmed Diagnosis: {primary_diagnosis} (ICD-10: {icd10_code})
## Triage Priority: {priority}

## Current Medications (for interaction checking):
{current_medications}

## Allergies: {allergies}

## Relevant Medical History: {medical_history}

## Key Lab Values: {labs}

Please create a comprehensive, evidence-based treatment plan for this patient.
Consider the drug interactions flagged above and current medications carefully.
"""


# ── Treatment Agent Node ──────────────────────────────────────────────────────

def treatment_agent_node(state: AgentState) -> AgentState:
    """
    Treatment Agent Node — creates evidence-based treatment plans.
    Checks drug interactions before recommending medications.
    """
    print("\n💊 TREATMENT AGENT: Generating treatment plan...")

    patient = state.get("patient_info")
    diagnosis = state.get("diagnosis_result")
    triage = state.get("triage_result")

    if not patient or not diagnosis:
        return {**state, "error": "Missing patient or diagnosis data for treatment"}

    # ── Step 1: Check Drug Interactions ──────────────────────────────────────
    current_meds = patient.get("current_medications", [])
    drug_interaction_alerts = []

    if current_meds:
        print(f"💊 Checking interactions for: {', '.join(current_meds)}")
        interaction_results = check_drug_interactions.invoke({"medications": current_meds})
        for med, data in interaction_results.items():
            if data.get("warnings"):
                for warning in data["warnings"]:
                    drug_interaction_alerts.append(f"{med}: {warning}")

    drug_alerts_text = (
        "\n".join([f"⚠️ {alert}" for alert in drug_interaction_alerts])
        if drug_interaction_alerts
        else "No significant drug interactions detected."
    )

    # ── Step 2: RAG — Retrieve Treatment Evidence ─────────────────────────────
    rag_query = f"treatment guidelines for {diagnosis['primary_diagnosis']}"
    evidence_docs = retrieve_medical_evidence.invoke({
        "query": rag_query,
        "n_results": 3,
    })

    evidence_text = "\n\n".join([
        f"**{doc.get('source', 'Unknown')}**:\n{doc.get('content', '')}"
        for doc in evidence_docs
    ])

    # ── Step 3: Generate Treatment Plan ──────────────────────────────────────
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.1,
    ).with_structured_output(TreatmentOutput)

    vitals = patient.get("vitals", {})
    labs_str = str(vitals.get("labs", "None provided"))

    prompt = ChatPromptTemplate.from_messages([
        ("system", TREATMENT_SYSTEM_PROMPT),
        ("human", TREATMENT_HUMAN_PROMPT),
    ])

    chain = prompt | llm
    result: TreatmentOutput = chain.invoke({
        "retrieved_evidence": evidence_text,
        "drug_interaction_alerts": drug_alerts_text,
        "name": patient.get("name", "Patient"),
        "age": patient.get("age", "Unknown"),
        "gender": patient.get("gender", "Unknown"),
        "primary_diagnosis": diagnosis.get("primary_diagnosis", "Unknown"),
        "icd10_code": diagnosis.get("icd10_code", ""),
        "priority": triage.get("priority", "Unknown") if triage else "Unknown",
        "current_medications": ", ".join(current_meds) or "None",
        "allergies": ", ".join(patient.get("allergies", [])) or "None",
        "medical_history": ", ".join(patient.get("medical_history", [])) or "None",
        "labs": labs_str,
    })

    # Format medications for display
    meds_text = "\n".join([
        f"• {m.name} {m.dose} {m.route} {m.frequency} x {m.duration} — for {m.indication}"
        for m in result.medications
    ])

    treatment_result: TreatmentResult = {
        "treatment_plan": result.treatment_plan,
        "medications": [
            {
                "name": m.name, "dose": m.dose, "route": m.route,
                "frequency": m.frequency, "duration": m.duration,
                "indication": m.indication,
            }
            for m in result.medications
        ],
        "drug_interactions": drug_interaction_alerts,
        "follow_up_timeline": result.follow_up_timeline,
        "lifestyle_recommendations": result.lifestyle_recommendations,
        "referrals": result.referrals,
    }

    print(f"✅ Treatment plan generated with {len(result.medications)} medications")
    if drug_interaction_alerts:
        print(f"⚠️  {len(drug_interaction_alerts)} drug interaction warnings flagged")

    plan_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(result.treatment_plan)])
    treatment_message = AIMessage(
        content=f"**Treatment Plan Complete**\n\n"
                f"**Treatment Steps:**\n{plan_text}\n\n"
                f"**Medications:**\n{meds_text}\n\n"
                f"**Drug Interaction Alerts:**\n{drug_alerts_text}\n\n"
                f"**Follow-up:** {result.follow_up_timeline}\n\n"
                f"**Referrals:** {', '.join(result.referrals) if result.referrals else 'None required'}",
        name="treatment_agent"
    )

    return {
        **state,
        "treatment_result": treatment_result,
        "current_agent": "treatment_agent",
        "messages": [*state.get("messages", []), treatment_message],
    }
