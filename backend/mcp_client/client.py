"""
MediMind — Model Context Protocol (MCP) Client Adapter
======================================================
Connects LangGraph agents and FastAPI services to the MediMind Clinical MCP Server
via the standardized JSON-RPC stdio transport using `langchain-mcp-adapters`.

Enables:
1. Dynamic tool discovery from the MCP server into LangGraph agents.
2. Direct invocation of MCP tools with structured validation.
3. Fetching of MCP clinical resources (guidelines, lab ranges) via URIs (`clinical://...`).
4. Retrieval of MCP standardized prompt templates.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient


_client_instance: Optional[MultiServerMCPClient] = None
_cached_tools: Optional[List[BaseTool]] = None
_cached_tools_map: Optional[Dict[str, BaseTool]] = None


def get_mcp_client() -> MultiServerMCPClient:
    """
    Get or create the singleton MultiServerMCPClient connected to the MediMind Clinical MCP Server.
    Uses stdio transport executing the server module in a dedicated Python subprocess.
    """
    global _client_instance
    if _client_instance is None:
        # Guarantee UTF-8 encoding across Windows/Linux stdio pipes
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        _client_instance = MultiServerMCPClient(
            connections={
                "clinical": {
                    "command": sys.executable,
                    "args": ["-m", "backend.mcp_server.clinical_server"],
                    "transport": "stdio",
                    "env": env,
                }
            }
        )
    return _client_instance


async def get_clinical_mcp_tools() -> List[BaseTool]:
    """
    Dynamically discover all tools exposed by the MediMind Clinical MCP Server.
    Converts them into LangGraph-compatible LangChain BaseTool instances.
    """
    global _cached_tools, _cached_tools_map
    if _cached_tools is not None:
        return _cached_tools

    client = get_mcp_client()
    tools = await client.get_tools()
    _cached_tools = tools
    _cached_tools_map = {t.name: t for t in tools}
    return _cached_tools


async def get_clinical_mcp_tool_by_name(name: str) -> Optional[BaseTool]:
    """
    Fetch a specific MCP tool by its registered name.
    
    Examples:
        - 'check_drug_interactions'
        - 'lookup_icd10_code'
        - 'interpret_lab_values'
        - 'search_medical_literature'
    """
    tools = await get_clinical_mcp_tools()
    for t in tools:
        if t.name == name:
            return t
    return None


async def read_clinical_resource(uri: str) -> str:
    """
    Read content from an MCP Clinical Resource URI.
    
    Supported URIs:
        - 'clinical://guidelines/triage-protocol'
        - 'clinical://reference/lab-ranges'
        - 'clinical://guidelines/antibiotic-stewardship'
    """
    client = get_mcp_client()
    resources = await client.get_resources()
    for r in resources:
        if str(r.metadata.get("uri")) == uri:
            return r.as_string()
    return f"Resource not found: {uri}"


async def get_clinical_prompt_template(
    prompt_name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Retrieve and format a clinical prompt template from the MCP server.
    
    Supported prompts:
        - 'clinical_triage_intake'
        - 'differential_diagnosis_review'
    """
    client = get_mcp_client()
    messages = await client.get_prompt(
        server_name="clinical",
        prompt_name=prompt_name,
        arguments=arguments or {},
    )
    if messages:
        return str(messages[0].content)
    return ""


def get_clinical_mcp_tools_sync() -> List[BaseTool]:
    """
    Synchronous helper to retrieve MCP tools for non-async contexts or initialization.
    Safely handles running vs non-running event loops.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, get_clinical_mcp_tools())
                return future.result()
        else:
            return loop.run_until_complete(get_clinical_mcp_tools())
    except Exception:
        return asyncio.run(get_clinical_mcp_tools())

