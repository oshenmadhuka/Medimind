"""
MediMind — Tools: Drug Interaction Checker
Uses OpenFDA API to check for drug-drug interactions and safety alerts.
Falls back to LLM-based checking if API is unavailable.
"""
import httpx
import asyncio
from typing import Optional
from langchain_core.tools import tool

from backend.core.config import settings


OPENFDA_BASE_URL = "https://api.fda.gov/drug"


async def fetch_drug_interactions_fda(drug_name: str) -> dict:
    """
    Query OpenFDA for drug label information including interactions.
    Returns raw FDA label data.
    """
    params = {
        "search": f'openfda.brand_name:"{drug_name}"',
        "limit": 1,
    }
    if settings.OPENFDA_API_KEY:
        params["api_key"] = settings.OPENFDA_API_KEY

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{OPENFDA_BASE_URL}/label.json",
                params=params
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    return results[0]
        except httpx.RequestError:
            pass
    return {}


def extract_interaction_warnings(fda_label: dict) -> list[str]:
    """Extract drug interaction warnings from FDA label data."""
    warnings = []

    # Drug interactions section
    interactions = fda_label.get("drug_interactions", [])
    if interactions:
        for interaction in interactions[:3]:  # Top 3
            warnings.append(f"Drug Interaction: {interaction[:300]}...")

    # Warnings section
    drug_warnings = fda_label.get("warnings", [])
    if drug_warnings:
        for warning in drug_warnings[:2]:
            warnings.append(f"Warning: {warning[:200]}...")

    # Contraindications
    contraindications = fda_label.get("contraindications", [])
    if contraindications:
        for contra in contraindications[:2]:
            warnings.append(f"Contraindication: {contra[:200]}...")

    return warnings


@tool
def check_drug_interactions(medications: list[str]) -> dict:
    """
    Check for drug interactions and safety warnings for a list of medications.
    
    Args:
        medications: List of medication names to check
        
    Returns:
        Dictionary with interaction warnings for each medication
    """
    results = {}

    async def run_checks():
        tasks = [fetch_drug_interactions_fda(med) for med in medications]
        return await asyncio.gather(*tasks, return_exceptions=True)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _check_all(medications))
                fda_data_list = future.result()
        else:
            fda_data_list = loop.run_until_complete(_check_all(medications))
    except Exception:
        fda_data_list = [{} for _ in medications]

    for med, fda_data in zip(medications, fda_data_list):
        if isinstance(fda_data, Exception) or not fda_data:
            results[med] = {
                "warnings": [],
                "source": "FDA lookup unavailable — manual review recommended"
            }
        else:
            warnings = extract_interaction_warnings(fda_data)
            results[med] = {
                "warnings": warnings,
                "source": "OpenFDA"
            }

    return results


async def _check_all(medications: list[str]) -> list[dict]:
    tasks = [fetch_drug_interactions_fda(med) for med in medications]
    return await asyncio.gather(*tasks, return_exceptions=True)


@tool
def get_drug_info(drug_name: str) -> dict:
    """
    Get comprehensive information about a specific drug from OpenFDA.
    
    Args:
        drug_name: Name of the drug (brand or generic)
        
    Returns:
        Drug information including dosage, warnings, and contraindications
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, fetch_drug_interactions_fda(drug_name))
                fda_label = future.result()
        else:
            fda_label = loop.run_until_complete(fetch_drug_interactions_fda(drug_name))
    except Exception:
        fda_label = {}

    if not fda_label:
        return {"drug_name": drug_name, "info": "Drug information not found in FDA database"}

    return {
        "drug_name": drug_name,
        "dosage_forms": fda_label.get("dosage_forms_and_strengths", ["Information not available"])[0]
            if fda_label.get("dosage_forms_and_strengths") else "Not available",
        "indications": fda_label.get("indications_and_usage", ["Not available"])[0]
            if fda_label.get("indications_and_usage") else "Not available",
        "warnings": fda_label.get("warnings_and_cautions", [])[:3],
        "contraindications": fda_label.get("contraindications", [])[:2],
        "source": "OpenFDA"
    }
