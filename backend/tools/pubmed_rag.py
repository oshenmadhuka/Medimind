"""
MediMind — Tools: PubMed RAG
Retrieves evidence-based medical information from a ChromaDB vector store
seeded with PubMed abstracts and clinical guidelines.
"""
from langchain_core.tools import tool
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
import os

from backend.core.config import settings


# ── Embedding Model ───────────────────────────────────────────────────────────

_embedding_model = None

def get_embeddings():
    """Lazy-load the embedding model (avoids loading at import time)."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
    return _embedding_model


# ── ChromaDB Client ───────────────────────────────────────────────────────────

def get_vector_store() -> Chroma:
    """Get or create the ChromaDB vector store."""
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory="./chroma_db",
    )


# ── Seed Medical Literature ───────────────────────────────────────────────────

SEED_MEDICAL_DOCS = [
    # Pneumonia
    Document(
        page_content="""Community-acquired pneumonia (CAP) is one of the most common infectious diseases. 
        Diagnosis is based on clinical features (fever, cough, dyspnea) and radiographic infiltrates. 
        Empiric treatment for outpatients: amoxicillin 500mg TID x 5 days (non-severe) or 
        azithromycin 500mg x 3 days for atypical coverage. Hospitalized patients: beta-lactam + macrolide or 
        respiratory fluoroquinolone. CURB-65 score guides admission decision.""",
        metadata={"source": "IDSA CAP Guidelines 2019", "condition": "pneumonia", "pmid": "30977855"}
    ),
    # Sepsis
    Document(
        page_content="""Sepsis is a life-threatening organ dysfunction caused by dysregulated host response to infection.
        Surviving Sepsis Campaign 2021 Bundles: Within 1 hour — measure lactate, obtain blood cultures, 
        administer broad-spectrum antibiotics, 30mL/kg crystalloid for hypotension (MAP<65), 
        vasopressors for persistent hypotension. Source control is critical. 
        qSOFA criteria: RR≥22, AMS, SBP≤100. Sequential Organ Failure Assessment (SOFA) score for diagnosis.""",
        metadata={"source": "Surviving Sepsis Campaign 2021", "condition": "sepsis", "pmid": "34599691"}
    ),
    # Type 2 Diabetes
    Document(
        page_content="""Type 2 diabetes management follows ADA Standards of Care 2024. 
        First-line therapy: lifestyle modification + metformin 500-2000mg/day (if tolerated).
        For patients with CVD or HF: GLP-1 agonists (semaglutide, liraglutide) or SGLT-2 inhibitors (empagliflozin) preferred.
        HbA1c target: <7% for most patients, <8% for elderly/comorbid.
        Monitoring: HbA1c every 3 months until stable, then every 6 months. Annual nephropathy screening.""",
        metadata={"source": "ADA Standards of Care 2024", "condition": "type 2 diabetes", "pmid": "38078578"}
    ),
    # Hypertension
    Document(
        page_content="""Hypertension treatment per ACC/AHA 2017 guidelines. 
        Stage 1 HTN (130-139/80-89): lifestyle modification first. 
        Stage 2 HTN (≥140/90): antihypertensive drugs + lifestyle changes.
        First-line agents: thiazide diuretics (HCTZ), ACE inhibitors/ARBs, calcium channel blockers.
        Target BP: <130/80 for most patients. Avoid ACE inhibitor + ARB combination.
        Resistant HTN: consider spironolactone as 4th agent.""",
        metadata={"source": "ACC/AHA Hypertension Guidelines 2017", "condition": "hypertension", "pmid": "29133356"}
    ),
    # Myocardial Infarction
    Document(
        page_content="""STEMI management: Primary PCI is preferred reperfusion strategy (door-to-balloon <90 min).
        Fibrinolysis if PCI not available within 120 min of diagnosis.
        Dual antiplatelet therapy: aspirin 325mg + clopidogrel/ticagrelor/prasugrel.
        Anticoagulation: unfractionated heparin or enoxaparin.
        Long-term: statin therapy (high-intensity), ACE inhibitor, beta-blocker, aspirin.
        NSTEMI: risk stratify with TIMI/GRACE score. Early invasive strategy for high-risk.""",
        metadata={"source": "ACC/AHA STEMI Guidelines 2022", "condition": "myocardial infarction", "pmid": "35521772"}
    ),
    # Stroke
    Document(
        page_content="""Ischemic stroke acute management: IV alteplase 0.9mg/kg (max 90mg) within 4.5h of onset 
        if no contraindications. Mechanical thrombectomy for large vessel occlusion up to 24h with imaging selection.
        NIHSS score for severity. CT to rule out hemorrhage before thrombolytics.
        Secondary prevention: antiplatelets (aspirin ± dipyridamole or clopidogrel) for non-cardioembolic stroke.
        Anticoagulation (warfarin/DOAC) for cardioembolic (AF-related) stroke.
        BP management: permissive HTN in acute phase (allow up to 220/120 if no thrombolytics).""",
        metadata={"source": "AHA/ASA Stroke Guidelines 2019", "condition": "stroke", "pmid": "31367371"}
    ),
    # Asthma
    Document(
        page_content="""Asthma management follows GINA 2023 stepwise approach.
        Step 1-2 (mild): as-needed low-dose ICS-formoterol or SABA.
        Step 3-4 (moderate): low-to-medium ICS + LABA.
        Step 5 (severe): high-dose ICS + LABA ± tiotropium ± biologics (dupilumab, mepolizumab).
        Acute exacerbation: SABA every 20 min x 3, systemic corticosteroids, O2 to SpO2 93-95%.
        Severe: IV magnesium sulfate 2g over 20 min. Consider heliox, IV SABA if no improvement.""",
        metadata={"source": "GINA Guidelines 2023", "condition": "asthma", "pmid": "37012981"}
    ),
    # Acute Appendicitis
    Document(
        page_content="""Acute appendicitis presents with periumbilical pain migrating to RLQ, nausea, low-grade fever.
        Alvarado score ≥7 suggests appendicitis. CT abdomen is gold standard (sensitivity 94%, specificity 95%).
        Uncomplicated appendicitis: laparoscopic appendectomy or antibiotics alone (amoxicillin-clavulanate).
        Perforated appendicitis: emergency surgery + broad-spectrum antibiotics (pip-tazo or meropenem).
        WBC >18,000 and CT showing perforation favor surgical approach.""",
        metadata={"source": "WSES Jerusalem Guidelines 2020", "condition": "appendicitis", "pmid": "32693813"}
    ),
    # Pneumothorax
    Document(
        page_content="""Spontaneous pneumothorax: primary (no lung disease) vs secondary (underlying lung disease).
        Small primary pneumothorax (<2cm): observation and supplemental O2.
        Large pneumothorax (>2cm): needle aspiration or chest tube insertion.
        Tension pneumothorax: medical emergency — immediate needle decompression (2nd intercostal space, midclavicular line) 
        followed by chest tube. Classic triad: hypotension, absent breath sounds, tracheal deviation.""",
        metadata={"source": "BTS Pleural Disease Guidelines 2023", "condition": "pneumothorax", "pmid": "36977625"}
    ),
    # Urinary Tract Infection
    Document(
        page_content="""Uncomplicated UTI in women: trimethoprim-sulfamethoxazole DS BID x 3 days (if local resistance <20%),
        or nitrofurantoin macrocrystals 100mg BID x 5 days, or fosfomycin 3g single dose.
        Complicated UTI (men, pregnant, structural abnormality): fluoroquinolone x 7-14 days.
        Pyelonephritis (outpatient): ciprofloxacin 500mg BID x 7 days or TMP-SMX DS BID x 14 days.
        Hospitalized pyelonephritis: IV ceftriaxone, transition to oral when clinically improved.""",
        metadata={"source": "IDSA UTI Guidelines 2022", "condition": "urinary tract infection", "pmid": "36462200"}
    ),
]


def initialize_vector_store():
    """
    Initialize ChromaDB with seed medical literature.
    Run this once to populate the vector store.
    """
    print("🔧 Initializing ChromaDB vector store with medical literature...")
    vs = get_vector_store()

    # Check if already populated
    existing = vs.get()
    if existing and len(existing.get("ids", [])) > 0:
        print(f"✅ Vector store already populated with {len(existing['ids'])} documents")
        return vs

    vs.add_documents(SEED_MEDICAL_DOCS)
    print(f"✅ Added {len(SEED_MEDICAL_DOCS)} medical documents to vector store")
    return vs


@tool
def retrieve_medical_evidence(query: str, n_results: int = 3) -> list[dict]:
    """
    Retrieve evidence-based medical literature relevant to a clinical query.
    Uses semantic search over PubMed abstracts and clinical guidelines.
    
    Args:
        query: Clinical question or diagnosis to search for
               Example: "treatment for community-acquired pneumonia"
        n_results: Number of evidence documents to retrieve (default: 3)
        
    Returns:
        List of relevant medical evidence with source citations
    """
    try:
        vs = get_vector_store()
        docs_with_scores = vs.similarity_search_with_relevance_scores(
            query, k=n_results
        )

        results = []
        for doc, score in docs_with_scores:
            results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "condition": doc.metadata.get("condition", "General"),
                "pmid": doc.metadata.get("pmid"),
                "relevance_score": round(score, 3),
            })

        return results if results else [
            {"content": "No specific evidence found. Please consult current clinical guidelines.",
             "source": "System", "relevance_score": 0.0}
        ]

    except Exception as e:
        return [{"content": f"Evidence retrieval error: {str(e)}",
                 "source": "System", "relevance_score": 0.0}]
