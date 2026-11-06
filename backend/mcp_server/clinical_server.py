"""
MediMind — Clinical Intelligence Model Context Protocol (MCP) Server
======================================================================
An enterprise-grade MCP server adhering to Anthropic's Model Context Protocol.
Exposes clinical intelligence tools, contextual resources, and prompt templates
to any MCP-compliant client (LangGraph, Claude Desktop, Cursor, external hospital agents).

Pillars implemented:
1. 🛠️  Tools:
    - check_drug_interactions: OpenFDA drug-drug safety & contraindication checks
    - get_drug_info: OpenFDA drug monograph, dosage forms, and warnings
    - interpret_lab_values: Reference ranges & critical alert flags (CBC, BMP, LFT, etc.)
    - lookup_icd10_code: ICD-10 clinical diagnosis codification
    - search_icd10_by_code: Reverse ICD-10 lookup
    - search_medical_literature: Semantic RAG retrieval over PubMed & clinical guidelines
2. 📑  Resources:
    - clinical://guidelines/triage-protocol: Emergency Severity Index (ESI) standards
    - clinical://reference/lab-ranges: Reference ranges & critical cutoff values
    - clinical://guidelines/antibiotic-stewardship: First-line empiric antibiotic regimens
3. 💬  Prompts:
    - clinical_triage_intake: Standardized clinical emergency triage intake template
    - differential_diagnosis_review: Structured Bayesian differential diagnostic reasoning
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

from backend.tools.drug_interaction import (
    check_drug_interactions as _check_drug_interactions,
    get_drug_info as _get_drug_info,
)
from backend.tools.icd10_lookup import (
    lookup_icd10_code as _lookup_icd10_code,
    search_icd10_by_code as _search_icd10_by_code,
    ICD10_CODES,
)
from backend.tools.lab_interpreter import (
    interpret_lab_values as _interpret_lab_values,
    LAB_REFERENCE_RANGES,
)
from backend.tools.pubmed_rag import (
    retrieve_medical_evidence as _retrieve_medical_evidence,
)


# ── FastMCP Server Initialization ─────────────────────────────────────────────

mcp = FastMCP(
    name="MediMind Clinical Intelligence Server",
    instructions=(
        "MediMind MCP Server exposes standardized clinical decision support tools, "
        "evidence retrieval, and medical reference resources for AI clinical agents."
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. MCP TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def check_drug_interactions(medications: List[str]) -> Dict[str, Any]:
    """
    Check for drug-drug interactions, FDA safety alerts, and contraindications.
    
    Args:
        medications: List of medication brand or generic names (e.g. ['Lisinopril', 'Potassium Chloride'])
        
    Returns:
        Dictionary mapping each medication to identified interaction warnings and source.
    """
    return _check_drug_interactions.invoke({"medications": medications})


@mcp.tool()
def get_drug_info(drug_name: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive drug monograph information from the OpenFDA database.
    
    Args:
        drug_name: Name of the drug (brand or generic, e.g. 'Metformin', 'Amoxicillin')
        
    Returns:
        Drug monograph containing dosage forms, indications, warnings, and contraindications.
    """
    return _get_drug_info.invoke({"drug_name": drug_name})


@mcp.tool()
def interpret_lab_values(lab_results: Dict[str, float], gender: str = "unknown") -> Dict[str, Any]:
    """
    Interpret a panel of clinical laboratory test results against standard reference ranges.
    Flags abnormal values and highlights immediate life-threatening CRITICAL values.
    
    Args:
        lab_results: Dictionary of {test_name: numeric_value}, e.g. {'troponin_i': 0.15, 'potassium': 6.8}
        gender: Patient biological sex for gender-specific ranges ('male', 'female', or 'unknown')
        
    Returns:
        Detailed clinical interpretation with normal, high, low, and critical alerts.
    """
    return _interpret_lab_values.invoke({"lab_results": lab_results, "gender": gender})


@mcp.tool()
def lookup_icd10_code(diagnosis: str) -> Dict[str, Any]:
    """
    Look up standardized ICD-10 diagnostic coding for a clinical condition.
    Supports exact, partial, and fuzzy clinical terminology matching.
    
    Args:
        diagnosis: Name of disease, condition, or symptom (e.g. 'Myocardial Infarction', 'Pneumonia')
        
    Returns:
        Primary ICD-10 code, standardized description, and alternative suggestions if fuzzy match.
    """
    return _lookup_icd10_code.invoke({"diagnosis": diagnosis})


@mcp.tool()
def search_icd10_by_code(icd10_code: str) -> Dict[str, Any]:
    """
    Perform reverse lookup to find diagnosis details from an ICD-10 code.
    
    Args:
        icd10_code: The ICD-10 code (e.g. 'I21.9', 'J18.9')
        
    Returns:
        Diagnosis name and standardized clinical description.
    """
    return _search_icd10_by_code.invoke({"icd10_code": icd10_code})


@mcp.tool()
def search_medical_literature(query: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """
    Perform semantic vector search (RAG) over indexed PubMed abstracts and clinical practice guidelines.
    
    Args:
        query: Clinical query or question (e.g. 'empiric treatment for community acquired pneumonia')
        n_results: Maximum number of evidence documents to retrieve (default: 3)
        
    Returns:
        List of ranked evidence snippets with PMIDs, guidelines citations, and relevance scores.
    """
    return _retrieve_medical_evidence.invoke({"query": query, "n_results": n_results})


# ══════════════════════════════════════════════════════════════════════════════
# 2. MCP RESOURCES
# ══════════════════════════════════════════════════════════════════════════════

@mcp.resource("clinical://guidelines/triage-protocol")
def get_triage_guidelines() -> str:
    """Emergency Severity Index (ESI) 5-Level Clinical Triage Protocol and Decision Tree."""
    return """# Emergency Severity Index (ESI) Triage Protocol

## Level 1: Resuscitation (Immediate Life Threat)
- **Criteria**: Requires immediate life-saving intervention (airway, breathing, circulation).
- **Examples**: Cardiac arrest, respiratory failure, severe trauma with shock, unresponsive patient.
- **Action**: Immediate physician evaluation and resuscitation team activation.

## Level 2: Emergent (High Risk / Time Sensitive)
- **Criteria**: High risk situation, confused/lethargic/disoriented, or severe pain/distress (8-10/10).
- **Examples**: Active chest pain suspicious for ACS, signs of acute stroke (FAST+), testicular torsion, ectopic pregnancy risk.
- **Vitals Alert**: HR > 100 or < 50, RR > 20 or < 10, SpO2 < 92%, SBP < 90 mmHg.
- **Action**: Bed placement within 10 minutes, continuous monitoring.

## Level 3: Urgent (Stable, Multiple Resources Needed)
- **Criteria**: Normal vital signs, requires 2 or more hospital resources (labs, imaging, IV fluids, specialist consult).
- **Examples**: Abdominal pain, closed fracture with stable vitals, moderate asthma exacerbation.
- **Action**: Evaluation within 30-60 minutes.

## Level 4: Less Urgent (Stable, Single Resource Needed)
- **Criteria**: Normal vital signs, requires exactly 1 resource (e.g., simple X-ray or suture).
- **Examples**: Simple laceration, ankle sprain, uncomplicated urinary tract infection.
- **Action**: Fast-track care, target evaluation < 120 minutes.

## Level 5: Non-Urgent (No Resources Needed)
- **Criteria**: Routine medication refill, minor rash, suture removal.
- **Action**: Clinic referral or fast-track discharge.
"""


@mcp.resource("clinical://reference/lab-ranges")
def get_lab_reference_ranges() -> str:
    """Clinical Laboratory Normal & Critical Reference Ranges (CBC, BMP, LFT, Cardiac)."""
    return f"""# Standard Clinical Laboratory Reference Ranges

The following values represent standard adult reference intervals and life-threatening critical cutoffs.

## Reference Table (JSON Representation)
```json
{json.dumps(LAB_REFERENCE_RANGES, indent=2)}
```

## Critical Action Thresholds:
- **Potassium < 2.5 or > 6.5 mEq/L**: Risk of fatal ventricular arrhythmias — immediate ECG & telemetry.
- **Sodium < 120 or > 160 mEq/L**: Severe seizure and osmotic myelinolysis risk — controlled correction.
- **Glucose < 40 mg/dL**: Severe neuroglycopenia — immediate IV dextrose (D50W).
- **Troponin I > 0.04 ng/mL**: Suggestive of myocardial injury — immediate 12-lead ECG and ACS protocol.
- **Hemoglobin < 7.0 g/dL**: Transfusion threshold for most asymptomatic adult inpatients.
"""


@mcp.resource("clinical://guidelines/antibiotic-stewardship")
def get_antibiotic_guidelines() -> str:
    """First-Line Empiric Antimicrobial Regimens for Acute Clinical Presentations."""
    return """# First-Line Empiric Antimicrobial Therapy Guidelines (IDSA / WHO)

## 1. Community-Acquired Pneumonia (CAP)
- **Outpatient (No comorbidities)**: Amoxicillin 1g PO TID OR Doxycycline 100mg PO BID (5 days).
- **Outpatient (With comorbidities / COPD / Diabetes)**: Augmentin (875/125mg BID) + Azithromycin 500mg daily.
- **Inpatient Non-Severe**: Ceftriaxone 1-2g IV daily + Azithromycin 500mg IV daily OR Levofloxacin 750mg IV daily.
- **Inpatient Severe (ICU)**: Ceftriaxone + Azithromycin + Vancomycin (if MRSA risk).

## 2. Sepsis & Septic Shock (Unknown Source)
- **First Hour Bundle**: Vancomycin 15-20 mg/kg IV + Cefepime 2g IV q8h (or Piperacillin-Tazobactam 4.5g IV q6h).
- **If intra-abdominal suspected**: Add Metronidazole 500mg IV q8h (if not using Pip-Tazo).

## 3. Uncomplicated Urinary Tract Infection (Cystitis)
- **First-Line**: Nitrofurantoin 100mg PO BID x 5 days OR TMP-SMX DS 1 tab PO BID x 3 days.
- **Alternative**: Fosfomycin 3g PO single dose.

## 4. Acute Bacterial Meningitis
- **Adults < 50**: Ceftriaxone 2g IV q12h + Vancomycin 15-20 mg/kg IV q8-12h.
- **Adults ≥ 50 or immunocompromised**: Add Ampicillin 2g IV q4h (to cover Listeria monocytogenes) + Dexamethasone 10mg IV prior to first antibiotic dose.
"""


# ══════════════════════════════════════════════════════════════════════════════
# 3. MCP PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
def clinical_triage_intake(
    patient_age: int,
    gender: str,
    symptoms: str,
    vitals: str,
) -> str:
    """Generate a structured clinical triage intake prompt for emergency assessment."""
    return f"""You are an Emergency Medicine Triage Officer assessing a patient according to the Emergency Severity Index (ESI).

PATIENT DETAILS:
- Age: {patient_age}
- Biological Sex: {gender}
- Chief Complaint & Symptoms: {symptoms}
- Presenting Vitals: {vitals}

INSTRUCTIONS:
1. Review presenting vitals against high-risk criteria (HR > 100 or < 50, RR > 20, SpO2 < 92%, SBP < 90).
2. Determine if immediate life-saving intervention is required (ESI Level 1 / P1).
3. If not, determine if this is a high-risk situation or severe acute pain (ESI Level 2 / P2).
4. Estimate hospital resources needed (Labs, ECG, Imaging, IV fluids).
5. Output the recommended Priority (P1 Resuscitation, P2 Emergent, P3 Urgent, P4 Non-urgent) and clinical rationale.
"""


@mcp.prompt()
def differential_diagnosis_review(
    primary_symptoms: str,
    patient_context: str,
    lab_summary: str = "None provided",
) -> str:
    """Generate a systematic Bayesian differential diagnostic prompt."""
    return f"""You are an Internal Medicine Diagnostician conducting a differential diagnosis evaluation.

CLINICAL PRESENTATION:
- Presenting Symptoms: {primary_symptoms}
- Patient Context & History: {patient_context}
- Laboratory Findings: {lab_summary}

DIAGNOSTIC MANDATE:
1. Identify the single most probable primary diagnosis.
2. Provide at least 3-5 ranked differential diagnoses with likelihood (High/Medium/Low) and clinical reasoning.
3. Explicitly screen for must-not-miss "Red Flag" conditions.
4. Recommend high-yield diagnostic investigations to confirm or rule out the top hypotheses.
"""


# ── Server Entry Point ────────────────────────────────────────────────────────

def main():
    """Run the MediMind Clinical MCP Server."""
    # Note: On stdio transport, never print to stdout as stdout is the JSON-RPC communication channel.
    import sys
    sys.stderr.write("MediMind Clinical MCP Server starting up (stdio transport)...\n")
    sys.stderr.flush()
    mcp.run()


if __name__ == "__main__":
    main()
