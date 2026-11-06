"""
MediMind — LangGraph Graph Builder
Assembles all agents into a LangGraph StateGraph with:
- Multi-agent supervisor routing
- Human-in-the-loop interrupt checkpoint
- PostgreSQL-backed session persistence
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.graph.state import AgentState
from backend.agents.supervisor import supervisor_node, route_from_supervisor
from backend.agents.triage_agent import triage_agent_node
from backend.agents.diagnosis_agent import diagnosis_agent_node
from backend.agents.treatment_agent import treatment_agent_node
from backend.agents.note_summarizer import note_summarizer_node


# ── Human Review Node ─────────────────────────────────────────────────────────

def human_review_node(state: AgentState) -> AgentState:
    """
    Human-in-the-loop node.
    The graph PAUSES here and waits for a human doctor to provide review.
    The doctor's decision is injected via the API endpoint /sessions/{id}/review
    """
    print("\n👨‍⚕️ HUMAN REVIEW NODE: Waiting for doctor approval...")
    # This node acts as a passthrough — the actual interrupt happens via
    # interrupt_before in the graph configuration
    return {**state, "current_agent": "human_review"}


# ── Build the Graph ───────────────────────────────────────────────────────────

def build_medimind_graph(use_memory: bool = True):
    """
    Build and compile the MediMind LangGraph workflow.
    
    Graph Flow:
    supervisor → triage_agent → supervisor → diagnosis_agent
              → supervisor → treatment_agent → supervisor
              → note_summarizer → supervisor → human_review
              → supervisor → END
    
    Args:
        use_memory: If True, use in-memory checkpointer (good for development).
                   For production, replace with PostgresSaver.
    Returns:
        Compiled LangGraph application
    """

    # ── Create State Graph ────────────────────────────────────────────────────
    workflow = StateGraph(AgentState)

    # ── Add Nodes ─────────────────────────────────────────────────────────────
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("triage_agent", triage_agent_node)
    workflow.add_node("diagnosis_agent", diagnosis_agent_node)
    workflow.add_node("treatment_agent", treatment_agent_node)
    workflow.add_node("note_summarizer", note_summarizer_node)
    workflow.add_node("human_review", human_review_node)

    # ── Entry Point ───────────────────────────────────────────────────────────
    workflow.set_entry_point("supervisor")

    # ── Supervisor Conditional Edges ──────────────────────────────────────────
    # The supervisor routes to any agent based on current state
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "triage_agent": "triage_agent",
            "diagnosis_agent": "diagnosis_agent",
            "treatment_agent": "treatment_agent",
            "note_summarizer": "note_summarizer",
            "human_review": "human_review",
            "END": END,
        }
    )

    # ── Agent → Supervisor Edges (all agents report back to supervisor) ────────
    workflow.add_edge("triage_agent", "supervisor")
    workflow.add_edge("diagnosis_agent", "supervisor")
    workflow.add_edge("treatment_agent", "supervisor")
    workflow.add_edge("note_summarizer", "supervisor")
    workflow.add_edge("human_review", "supervisor")

    # ── Checkpointer (Memory) ─────────────────────────────────────────────────
    checkpointer = MemorySaver()  # In-memory for development

    # ── Compile with Human-in-the-Loop Interrupt ──────────────────────────────
    # Graph will PAUSE before executing human_review node
    # This allows the API to inject the doctor's decision
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],  # 🔑 Human-in-the-Loop!
    )

    return app


# ── Singleton Graph Instance ──────────────────────────────────────────────────
_graph_instance = None

def get_graph():
    """Get or create the singleton graph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_medimind_graph()
    return _graph_instance
