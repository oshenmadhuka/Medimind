"""
MediMind — Tools: ICD-10 Code Lookup
Searches for ICD-10 diagnosis codes from local embedded knowledge.
Uses a curated dataset of common ICD-10 codes for clinical use.
"""
from langchain_core.tools import tool
from difflib import get_close_matches


# ── Common ICD-10 Code Dataset ────────────────────────────────────────────────
# Curated set of common clinical diagnoses with ICD-10 codes

ICD10_CODES = {
    # Cardiovascular
    "myocardial infarction": {"code": "I21.9", "description": "Acute myocardial infarction, unspecified"},
    "heart failure": {"code": "I50.9", "description": "Heart failure, unspecified"},
    "atrial fibrillation": {"code": "I48.91", "description": "Unspecified atrial fibrillation"},
    "hypertension": {"code": "I10", "description": "Essential (primary) hypertension"},
    "angina pectoris": {"code": "I20.9", "description": "Angina pectoris, unspecified"},
    "cardiac arrest": {"code": "I46.9", "description": "Cardiac arrest, cause unspecified"},
    "stroke": {"code": "I64", "description": "Stroke, not specified as haemorrhage or infarction"},
    "deep vein thrombosis": {"code": "I82.409", "description": "Acute DVT of unspecified deep veins"},
    "pulmonary embolism": {"code": "I26.99", "description": "Other pulmonary embolism without acute cor pulmonale"},

    # Respiratory
    "pneumonia": {"code": "J18.9", "description": "Pneumonia, unspecified organism"},
    "asthma": {"code": "J45.909", "description": "Unspecified asthma, uncomplicated"},
    "copd": {"code": "J44.1", "description": "COPD with acute exacerbation"},
    "bronchitis": {"code": "J40", "description": "Bronchitis, not specified as acute or chronic"},
    "pleural effusion": {"code": "J90", "description": "Pleural effusion, not elsewhere classified"},
    "respiratory failure": {"code": "J96.90", "description": "Respiratory failure, unspecified, unspecified whether with hypoxia or hypercapnia"},
    "covid-19": {"code": "U07.1", "description": "COVID-19, virus identified"},
    "influenza": {"code": "J11.1", "description": "Influenza due to unidentified influenza virus with other respiratory manifestations"},

    # Gastrointestinal
    "appendicitis": {"code": "K37", "description": "Unspecified appendicitis"},
    "peptic ulcer": {"code": "K27.9", "description": "Peptic ulcer, site unspecified, unspecified as acute or chronic"},
    "gastroenteritis": {"code": "K59.1", "description": "Functional diarrhea"},
    "pancreatitis": {"code": "K85.9", "description": "Acute pancreatitis without necrosis or infection, unspecified"},
    "cholecystitis": {"code": "K81.9", "description": "Cholecystitis, unspecified"},
    "cirrhosis": {"code": "K74.60", "description": "Unspecified cirrhosis of liver"},
    "crohn disease": {"code": "K50.90", "description": "Crohn's disease of small intestine without complications"},
    "ibs": {"code": "K58.9", "description": "Irritable bowel syndrome without diarrhea"},
    "gerd": {"code": "K21.0", "description": "Gastro-esophageal reflux disease with esophagitis"},

    # Infectious Diseases
    "sepsis": {"code": "A41.9", "description": "Sepsis, unspecified organism"},
    "urinary tract infection": {"code": "N39.0", "description": "Urinary tract infection, site not specified"},
    "uti": {"code": "N39.0", "description": "Urinary tract infection, site not specified"},
    "cellulitis": {"code": "L03.90", "description": "Cellulitis, unspecified"},
    "meningitis": {"code": "G03.9", "description": "Meningitis, unspecified"},
    "tuberculosis": {"code": "A15.9", "description": "Respiratory tuberculosis unspecified"},
    "malaria": {"code": "B54", "description": "Unspecified malaria"},

    # Neurological
    "migraine": {"code": "G43.909", "description": "Migraine, unspecified, not intractable, without status migrainosus"},
    "epilepsy": {"code": "G40.909", "description": "Epilepsy, unspecified, not intractable, without status epilepticus"},
    "alzheimers": {"code": "G30.9", "description": "Alzheimer's disease, unspecified"},
    "parkinsons": {"code": "G20", "description": "Parkinson's disease"},
    "multiple sclerosis": {"code": "G35", "description": "Multiple sclerosis"},
    "transient ischemic attack": {"code": "G45.9", "description": "Transient cerebral ischaemic attack, unspecified"},

    # Endocrine
    "type 1 diabetes": {"code": "E10.9", "description": "Type 1 diabetes mellitus without complications"},
    "type 2 diabetes": {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications"},
    "hypothyroidism": {"code": "E03.9", "description": "Hypothyroidism, unspecified"},
    "hyperthyroidism": {"code": "E05.90", "description": "Thyrotoxicosis, unspecified without thyrotoxic crisis or storm"},
    "obesity": {"code": "E66.9", "description": "Obesity, unspecified"},
    "cushing syndrome": {"code": "E24.9", "description": "Cushing's syndrome, unspecified"},

    # Musculoskeletal
    "rheumatoid arthritis": {"code": "M06.9", "description": "Rheumatoid arthritis, unspecified"},
    "osteoarthritis": {"code": "M19.90", "description": "Primary osteoarthritis, unspecified site"},
    "gout": {"code": "M10.9", "description": "Gout, unspecified"},
    "fracture": {"code": "M84.40", "description": "Pathological fracture, unspecified site"},
    "low back pain": {"code": "M54.5", "description": "Low back pain"},
    "fibromyalgia": {"code": "M79.3", "description": "Panniculitis"},

    # Mental Health
    "depression": {"code": "F32.9", "description": "Major depressive disorder, single episode, unspecified"},
    "anxiety": {"code": "F41.9", "description": "Anxiety disorder, unspecified"},
    "bipolar disorder": {"code": "F31.9", "description": "Bipolar disorder, unspecified"},
    "schizophrenia": {"code": "F20.9", "description": "Schizophrenia, unspecified"},
    "ptsd": {"code": "F43.10", "description": "Post-traumatic stress disorder, unspecified"},

    # Oncology
    "lung cancer": {"code": "C34.90", "description": "Malignant neoplasm of unspecified part of unspecified bronchus and lung"},
    "breast cancer": {"code": "C50.919", "description": "Malignant neoplasm of unspecified site of unspecified female breast"},
    "colon cancer": {"code": "C18.9", "description": "Malignant neoplasm of colon, unspecified"},
    "prostate cancer": {"code": "C61", "description": "Malignant neoplasm of prostate"},
    "leukemia": {"code": "C95.90", "description": "Leukemia, unspecified, not having achieved remission"},
}


@tool
def lookup_icd10_code(diagnosis: str) -> dict:
    """
    Look up the ICD-10 code for a given diagnosis name.
    
    Args:
        diagnosis: The diagnosis name (e.g., "pneumonia", "type 2 diabetes")
        
    Returns:
        ICD-10 code, description, and any close matches found
    """
    query = diagnosis.lower().strip()

    # Exact match
    if query in ICD10_CODES:
        return {
            "query": diagnosis,
            "match_type": "exact",
            "icd10_code": ICD10_CODES[query]["code"],
            "description": ICD10_CODES[query]["description"],
        }

    # Partial match
    for key, value in ICD10_CODES.items():
        if query in key or key in query:
            return {
                "query": diagnosis,
                "match_type": "partial",
                "icd10_code": value["code"],
                "description": value["description"],
                "matched_term": key,
            }

    # Fuzzy match using difflib
    close_matches = get_close_matches(query, ICD10_CODES.keys(), n=3, cutoff=0.6)
    if close_matches:
        suggestions = [
            {
                "term": match,
                "icd10_code": ICD10_CODES[match]["code"],
                "description": ICD10_CODES[match]["description"],
            }
            for match in close_matches
        ]
        return {
            "query": diagnosis,
            "match_type": "fuzzy",
            "suggestions": suggestions,
            "note": "Exact match not found. Please verify with the suggestions above.",
        }

    return {
        "query": diagnosis,
        "match_type": "not_found",
        "note": "No ICD-10 code found. Please consult the official ICD-10-CM database.",
        "icd10_code": "Z99.9",  # default
        "description": "Unspecified condition",
    }


@tool
def search_icd10_by_code(icd10_code: str) -> dict:
    """
    Reverse lookup — find a diagnosis name from its ICD-10 code.
    
    Args:
        icd10_code: The ICD-10 code (e.g., "I21.9", "J18.9")
        
    Returns:
        Matching diagnosis name and description
    """
    code_upper = icd10_code.upper().strip()

    for diagnosis, data in ICD10_CODES.items():
        if data["code"] == code_upper:
            return {
                "icd10_code": code_upper,
                "diagnosis": diagnosis,
                "description": data["description"],
            }

    return {
        "icd10_code": icd10_code,
        "note": "Code not found in local database. Consult the official ICD-10-CM index.",
    }
