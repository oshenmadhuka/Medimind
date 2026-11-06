"""
Tests for MediMind Clinical Intelligence MCP Server & Client
Verifies MCP tools, resources, and prompts over stdio transport.
"""

import pytest
import asyncio
from backend.mcp_client.client import (
    get_clinical_mcp_tools,
    get_clinical_mcp_tool_by_name,
    read_clinical_resource,
    get_clinical_prompt_template,
)


@pytest.mark.asyncio
async def test_mcp_tools_discovery():
    """Verify that all clinical tools are dynamically discovered via MCP protocol."""
    tools = await get_clinical_mcp_tools()
    tool_names = [t.name for t in tools]

    expected_tools = [
        "check_drug_interactions",
        "get_drug_info",
        "interpret_lab_values",
        "lookup_icd10_code",
        "search_icd10_by_code",
        "search_medical_literature",
    ]

    for expected in expected_tools:
        assert expected in tool_names, f"Expected MCP tool '{expected}' not found"


@pytest.mark.asyncio
async def test_mcp_tool_icd10_execution():
    """Verify executing lookup_icd10_code through MCP tool invocation."""
    tool = await get_clinical_mcp_tool_by_name("lookup_icd10_code")
    assert tool is not None, "lookup_icd10_code tool should be found"

    result = await tool.ainvoke({"diagnosis": "pneumonia"})
    assert result is not None
    # Result text contains the ICD-10 code J18.9
    result_str = str(result)
    assert "J18.9" in result_str or "pneumonia" in result_str.lower()


@pytest.mark.asyncio
async def test_mcp_tool_lab_interpreter_execution():
    """Verify executing interpret_lab_values through MCP tool invocation."""
    tool = await get_clinical_mcp_tool_by_name("interpret_lab_values")
    assert tool is not None, "interpret_lab_values tool should be found"

    result = await tool.ainvoke({
        "lab_results": {"troponin_i": 0.25, "potassium": 6.8},
        "gender": "male",
    })
    result_str = str(result)
    assert "CRITICAL" in result_str or "troponin" in result_str.lower()


@pytest.mark.asyncio
async def test_mcp_resource_retrieval():
    """Verify reading clinical guidelines and lab ranges as MCP resources."""
    triage_guideline = await read_clinical_resource("clinical://guidelines/triage-protocol")
    assert "Emergency Severity Index" in triage_guideline
    assert "Level 1: Resuscitation" in triage_guideline

    lab_ranges = await read_clinical_resource("clinical://reference/lab-ranges")
    assert "Standard Clinical Laboratory Reference Ranges" in lab_ranges
    assert "Potassium" in lab_ranges


@pytest.mark.asyncio
async def test_mcp_prompt_retrieval():
    """Verify fetching standardized clinical prompt templates via MCP."""
    prompt_text = await get_clinical_prompt_template(
        "clinical_triage_intake",
        arguments={
            "patient_age": "52",
            "gender": "female",
            "symptoms": "substernal chest pain radiating to left arm",
            "vitals": "BP 160/95, HR 105",
        },
    )
    assert "Emergency Medicine Triage Officer" in prompt_text
    assert "substernal chest pain" in prompt_text

