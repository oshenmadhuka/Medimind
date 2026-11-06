"""
MediMind — Tools: Lab Value Interpreter
Interprets lab results and flags abnormal values with clinical context.
"""
from langchain_core.tools import tool


# ── Reference Ranges ──────────────────────────────────────────────────────────

LAB_REFERENCE_RANGES = {
    # Complete Blood Count (CBC)
    "wbc": {"name": "White Blood Cells", "unit": "10³/µL", "low": 4.5, "high": 11.0,
            "critical_low": 2.0, "critical_high": 30.0},
    "rbc": {"name": "Red Blood Cells", "unit": "10⁶/µL",
            "low_male": 4.5, "high_male": 5.9, "low_female": 4.0, "high_female": 5.2,
            "critical_low": 2.0, "critical_high": 8.0},
    "hemoglobin": {"name": "Hemoglobin", "unit": "g/dL",
                   "low_male": 13.5, "high_male": 17.5, "low_female": 12.0, "high_female": 15.5,
                   "critical_low": 7.0, "critical_high": 20.0},
    "hematocrit": {"name": "Hematocrit", "unit": "%",
                   "low_male": 41, "high_male": 53, "low_female": 36, "high_female": 46,
                   "critical_low": 20, "critical_high": 60},
    "platelets": {"name": "Platelets", "unit": "10³/µL", "low": 150, "high": 400,
                  "critical_low": 50, "critical_high": 1000},

    # Basic Metabolic Panel (BMP)
    "sodium": {"name": "Sodium", "unit": "mEq/L", "low": 136, "high": 145,
               "critical_low": 120, "critical_high": 160},
    "potassium": {"name": "Potassium", "unit": "mEq/L", "low": 3.5, "high": 5.0,
                  "critical_low": 2.5, "critical_high": 6.5},
    "chloride": {"name": "Chloride", "unit": "mEq/L", "low": 98, "high": 106,
                 "critical_low": 80, "critical_high": 115},
    "co2": {"name": "CO2/Bicarbonate", "unit": "mEq/L", "low": 22, "high": 29,
            "critical_low": 10, "critical_high": 40},
    "bun": {"name": "Blood Urea Nitrogen", "unit": "mg/dL", "low": 7, "high": 20,
            "critical_low": 2, "critical_high": 100},
    "creatinine": {"name": "Creatinine", "unit": "mg/dL",
                   "low_male": 0.7, "high_male": 1.3, "low_female": 0.6, "high_female": 1.1,
                   "critical_low": 0, "critical_high": 10},
    "glucose": {"name": "Glucose", "unit": "mg/dL", "low": 70, "high": 100,
                "critical_low": 40, "critical_high": 500},

    # Liver Function Tests (LFT)
    "alt": {"name": "ALT (SGPT)", "unit": "U/L", "low": 7, "high": 56,
            "critical_low": 0, "critical_high": 1000},
    "ast": {"name": "AST (SGOT)", "unit": "U/L", "low": 10, "high": 40,
            "critical_low": 0, "critical_high": 1000},
    "bilirubin_total": {"name": "Total Bilirubin", "unit": "mg/dL", "low": 0.1, "high": 1.2,
                        "critical_low": 0, "critical_high": 15},
    "albumin": {"name": "Albumin", "unit": "g/dL", "low": 3.4, "high": 5.4,
                "critical_low": 1.5, "critical_high": 6},

    # Cardiac Markers
    "troponin_i": {"name": "Troponin I", "unit": "ng/mL", "low": 0, "high": 0.04,
                   "critical_low": 0, "critical_high": 0.5},
    "bnp": {"name": "BNP", "unit": "pg/mL", "low": 0, "high": 100,
            "critical_low": 0, "critical_high": 900},

    # Thyroid
    "tsh": {"name": "TSH", "unit": "mIU/L", "low": 0.4, "high": 4.0,
            "critical_low": 0.1, "critical_high": 10},

    # Lipid Panel
    "cholesterol_total": {"name": "Total Cholesterol", "unit": "mg/dL", "low": 0, "high": 200,
                          "critical_low": 0, "critical_high": 400},
    "ldl": {"name": "LDL Cholesterol", "unit": "mg/dL", "low": 0, "high": 100,
            "critical_low": 0, "critical_high": 300},
    "hdl": {"name": "HDL Cholesterol", "unit": "mg/dL",
            "low_male": 40, "low_female": 50, "high": 60,
            "critical_low": 20, "critical_high": 100},
}


def interpret_single_lab(test_name: str, value: float, gender: str = "unknown") -> dict:
    """Interpret a single lab value against reference ranges."""
    test_key = test_name.lower().replace(" ", "_").replace("-", "_")

    if test_key not in LAB_REFERENCE_RANGES:
        return {
            "test": test_name,
            "value": value,
            "status": "unknown",
            "interpretation": "Reference range not available in system",
        }

    ref = LAB_REFERENCE_RANGES[test_key]

    # Handle gender-specific ranges
    low = ref.get("low") or ref.get(f"low_{gender}", ref.get("low_male", 0))
    high = ref.get("high") or ref.get(f"high_{gender}", ref.get("high_male", 999))
    critical_low = ref.get("critical_low", low * 0.5)
    critical_high = ref.get("critical_high", high * 1.5)

    if value <= critical_low:
        status = "CRITICAL LOW"
        flag = "🔴"
    elif value >= critical_high:
        status = "CRITICAL HIGH"
        flag = "🔴"
    elif value < low:
        status = "LOW"
        flag = "🟡"
    elif value > high:
        status = "HIGH"
        flag = "🟡"
    else:
        status = "NORMAL"
        flag = "🟢"

    return {
        "test": ref["name"],
        "value": f"{value} {ref['unit']}",
        "status": status,
        "flag": flag,
        "reference_range": f"{low} – {high} {ref['unit']}",
        "is_critical": "CRITICAL" in status,
        "interpretation": f"{ref['name']} is {status.lower()} at {value} {ref['unit']} "
                          f"(ref: {low}–{high} {ref['unit']})",
    }


@tool
def interpret_lab_values(lab_results: dict, gender: str = "unknown") -> dict:
    """
    Interpret a panel of lab test results against clinical reference ranges.
    
    Args:
        lab_results: Dictionary of {test_name: value} pairs
                     Example: {"glucose": 350, "hemoglobin": 8.5, "sodium": 138}
        gender: Patient gender for gender-specific ranges (male/female/unknown)
        
    Returns:
        Interpreted results with flags, reference ranges, and critical alerts
    """
    interpretations = []
    critical_alerts = []
    abnormal_tests = []

    for test_name, value in lab_results.items():
        try:
            result = interpret_single_lab(test_name, float(value), gender)
            interpretations.append(result)

            if result.get("is_critical"):
                critical_alerts.append(f"CRITICAL: {result['interpretation']}")
            elif result.get("status") not in ("NORMAL", "unknown"):
                abnormal_tests.append(result["interpretation"])
        except (ValueError, TypeError) as e:
            interpretations.append({
                "test": test_name,
                "value": value,
                "status": "error",
                "interpretation": f"Could not interpret: {str(e)}"
            })

    return {
        "results": interpretations,
        "critical_alerts": critical_alerts,
        "abnormal_tests": abnormal_tests,
        "total_tests": len(interpretations),
        "critical_count": len(critical_alerts),
        "abnormal_count": len(abnormal_tests),
        "summary": (
            f"⚠️ {len(critical_alerts)} CRITICAL values require immediate attention. "
            if critical_alerts else ""
        ) + f"{len(abnormal_tests)} abnormal values noted out of {len(interpretations)} tests.",
    }
