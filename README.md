# MediMind — AI-Powered Clinical Intelligence Platform

<div align="center">

![MediMind Banner](https://img.shields.io/badge/MediMind-Clinical%20AI-blue?style=for-the-badge&logo=heart)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple?style=for-the-badge)
![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-crimson?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-Llama%203.3-orange?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=for-the-badge)
![React](https://img.shields.io/badge/React-19-cyan?style=for-the-badge)

**Production-grade multi-agent clinical decision support system built with LangGraph & Model Context Protocol (MCP)**

</div>

---

## 🎯 Project Overview

MediMind is an **end-to-end AI engineering portfolio project** demonstrating:

| Concept | Implementation |
|---|---|
| **Multi-Agent Orchestration** | LangGraph Supervisor → 4 specialized agents |
| **Model Context Protocol (MCP)** | FastMCP Clinical Server + LangGraph MCP Client over stdio JSON-RPC |
| **RAG Pipeline** | PubMed literature → ChromaDB → Semantic search |
| **Tool Calling via MCP** | OpenFDA API, Lab interpreter, ICD-10 lookup, RAG |
| **Clinical Resources (MCP)** | `clinical://` URIs for ESI triage protocols & lab reference ranges |
| **Human-in-the-Loop** | LangGraph `interrupt_before` doctor approval workflow |
| **Stateful Sessions** | LangGraph MemorySaver (upgradable to PostgreSQL) |
| **Streaming** | FastAPI SSE → React real-time updates |
| **Agent Evaluation** | LangSmith traces + custom eval datasets |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  LANGGRAPH SUPERVISOR AGENT              │
│            (Routes tasks to specialized agents)         │
└────────┬──────────┬──────────┬──────────┬──────────────┘
         │          │          │          │
    ┌────▼────┐ ┌───▼────┐ ┌──▼─────┐ ┌──▼──────────┐
    │ TRIAGE  │ │ DIAG-  │ │TREATMENT│ │ CLINICAL    │
    │  AGENT  │ │ NOSIS  │ │  AGENT  │ │ NOTE        │
    │         │ │ AGENT  │ │         │ │ SUMMARIZER  │
    └────┬────┘ └───┬────┘ └──┬──────┘ └──┬──────────┘
         │          │         │            │
         └──────────┼─────────┴────────────┘
                    │  (LangGraph MCP Client / stdio JSON-RPC)
                    ▼
┌─────────────────────────────────────────────────────────┐
│         MEDIMIND CLINICAL MCP SERVER (FastMCP)          │
│   (Universal protocol layer accessible by LangGraph,    │
│    Claude Desktop, Cursor, or external hospital AI)     │
├─────────────────────────────────────────────────────────┤
│ 🛠️ Standardized Tools:                                  │
│   • check_drug_interactions (OpenFDA API)               │
│   • get_drug_info (OpenFDA monographs)                  │
│   • interpret_lab_values (CBC, BMP, LFT reference ranges)│
│   • lookup_icd10_code & search_icd10_by_code            │
│   • search_medical_literature (PubMed RAG / ChromaDB)   │
├─────────────────────────────────────────────────────────┤
│ 📑 Clinical Resources:                                  │
│   • clinical://guidelines/triage-protocol (ESI standard)│
│   • clinical://reference/lab-ranges (Normal & critical) │
│   • clinical://guidelines/antibiotic-stewardship (IDSA) │
├─────────────────────────────────────────────────────────┤
│ 💬 Clinical Prompts:                                    │
│   • clinical_triage_intake                              │
│   • differential_diagnosis_review                       │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│              HUMAN-IN-THE-LOOP CHECKPOINT               │
│         (Doctor reviews & approves diagnosis)           │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Groq API key](https://console.groq.com) (free)

### 1. Clone & Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd medimind

# Setup environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the Backend

```bash
# From project root
python run_backend.py

# OR directly:
uvicorn backend.api.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API Docs at: http://localhost:8000/docs

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

---

## 📁 Project Structure

```
medimind/
├── backend/
│   ├── agents/
│   │   ├── supervisor.py          # LangGraph supervisor + routing
│   │   ├── triage_agent.py        # Urgency classification (P1-P4)
│   │   ├── diagnosis_agent.py     # RAG-powered differential diagnosis
│   │   ├── treatment_agent.py     # Treatment planning + drug checks
│   │   └── note_summarizer.py     # SOAP note generation
│   ├── mcp_server/
│   │   └── clinical_server.py     # FastMCP Clinical Server (Tools, Resources, Prompts)
│   ├── mcp_client/
│   │   └── client.py              # MultiServerMCPClient adapter for LangGraph
│   ├── tools/
│   │   ├── drug_interaction.py    # OpenFDA API integration
│   │   ├── lab_interpreter.py     # Lab value reference ranges
│   │   ├── icd10_lookup.py        # ICD-10 code database
│   │   └── pubmed_rag.py          # ChromaDB + HuggingFace embeddings
│   ├── graph/
│   │   ├── state.py               # AgentState TypedDict schema
│   │   └── graph_builder.py       # StateGraph construction + compile
│   ├── api/
│   │   └── main.py                # FastAPI + SSE streaming + MCP endpoints
│   └── core/
│       └── config.py              # Pydantic Settings
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── PatientForm.jsx    # Multi-step patient intake
│       │   ├── AgentPipeline.jsx  # Visual pipeline progress
│       │   ├── AgentThoughts.jsx  # Real-time streaming panel
│       │   ├── DiagnosisCard.jsx  # Results display cards
│       │   └── Sidebar.jsx        # Navigation
│       └── pages/
│           ├── Dashboard.jsx      # Sessions overview
│           └── SessionPage.jsx    # Live assessment view
├── tests/
│   └── test_mcp_clinical_server.py # MCP protocol & tool test suite
├── mcp_claude_desktop_config.json # Ready configuration for Claude Desktop & Cursor
├── .env.example
├── run_backend.py
└── README.md
```

---

## 🔑 Key Technical Deep-Dives

### 1. Model Context Protocol (MCP) Server Architecture
MediMind decouples clinical intelligence into an autonomous **FastMCP** server implementing all 3 MCP pillars:
* **Tools (`@mcp.tool`)**: Exposes drug safety lookups, lab interpretations, ICD-10 coding, and PubMed RAG.
* **Resources (`@mcp.resource`)**: Exposes read-only clinical URIs like `clinical://guidelines/triage-protocol` and `clinical://reference/lab-ranges`.
* **Prompts (`@mcp.prompt`)**: Standardizes clinical emergency triage and differential diagnosis prompts.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MediMind Clinical Intelligence Server")

@mcp.tool()
def lookup_icd10_code(diagnosis: str) -> dict:
    """Standardized ICD-10 clinical diagnosis codification."""
    ...

@mcp.resource("clinical://guidelines/triage-protocol")
def get_triage_guidelines() -> str:
    """ESI 5-level clinical triage protocol."""
    ...
```

### 2. LangGraph MCP Client (`langchain-mcp-adapters`)
LangGraph agents dynamically discover tools and resources from the MCP server over standard input/output (`stdio`) JSON-RPC 2.0 frames:
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "clinical": {
        "command": "python",
        "args": ["-m", "backend.mcp_server.clinical_server"],
        "transport": "stdio",
    }
})

tools = await client.get_tools()  # Dynamically loaded into LangGraph agents!
```

### 3. Connect to Antigravity IDE, Cursor, or Claude Desktop
Because MCP is an open standard, any MCP-compatible AI environment can connect to MediMind's Clinical MCP server with zero code changes:
* **Antigravity IDE**: Configured in `~/.gemini/config/mcp_config.json` (or copy from `mcp_config.json`). Inspect connected tools anytime in the UI under **Additional Options (...) > MCP Servers**.
* **Claude Desktop / Cursor**: Copy the contents of `mcp_config.json` into your local MCP configuration file (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "medimind-clinical": {
      "command": "uv",
      "args": ["run", "--directory", "D:\\Freelance projects\\Langraph Project", "python", "-m", "backend.mcp_server.clinical_server"],
      "env": {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### 4. LangGraph Supervisor Pattern
The supervisor uses structured LLM output to decide the next agent:
```python
class SupervisorDecision(BaseModel):
    next: Literal["triage_agent", "diagnosis_agent", "treatment_agent", ...]
    reasoning: str
```

### 5. Human-in-the-Loop Checkpoint
Graph pauses execution before doctor review node:
```python
app = workflow.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["human_review"],  # ← Pause here!
)
```

---

## 💬 Interview Talking Points & CV Highlights

1. **Model Context Protocol (MCP)**:
   > *"I engineered a dedicated clinical Model Context Protocol (MCP) server adhering to Anthropic's open specification. Instead of hardcoding tools inside LangChain, MCP decouples the tools into an independent JSON-RPC microservice. This allows our clinical tools to be consumed interchangeably by LangGraph agents, Claude Desktop, or external hospital systems."*

2. **The 3 Pillars of MCP (Tools, Resources, Prompts)**:
   > *"Most developers only know MCP tools. I implemented all three MCP primitives: executable Tools (OpenFDA, ICD-10, RAG), contextual Resources (`clinical://guidelines/...` for triage and lab reference ranges), and standardized Prompts for emergency intake."*

3. **Multi-Agent Orchestration with LangGraph**:
   > *"I built a supervisor-subagent architecture where a central supervisor routes between 4 specialized agents (Triage, Diagnosis, Treatment, Note Summarizer) based on graph state."*

4. **Human-in-the-Loop Safety**:
   > *"In clinical AI, fully autonomous decisions are dangerous. I used LangGraph's `interrupt_before` to pause execution, requiring an attending physician to review and approve the diagnosis before the treatment agent generates prescriptions."*

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Protocol Layer** | Model Context Protocol (MCP), FastMCP, `langchain-mcp-adapters` |
| **Agent Orchestration** | LangGraph 0.2, LangChain |
| **LLM** | Groq (Llama 3.3 70B / Mixtral) |
| **Vector Store** | ChromaDB + sentence-transformers |
| **Backend API** | FastAPI + SSE Streaming |
| **Frontend** | React + Vite |
| **Observability** | LangSmith |
| **External APIs** | OpenFDA API, PubMed |

---

## 🧪 Testing the MCP Server

Run the test suite covering MCP tool discovery, execution, resources, and prompts:
```bash
uv run python -m pytest tests/test_mcp_clinical_server.py -v
```

---

## 📄 License

MIT License — Free to use for educational and portfolio purposes.
