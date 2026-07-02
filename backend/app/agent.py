from __future__ import annotations

from .database import ReadonlyDatabase
from .llm import classify_intent_with_ollama
from .models import AskResponse


def answer_question(database: ReadonlyDatabase, question: str, user_ctx: object = None) -> AskResponse:
    """Run the FabriQ LangGraph pipeline and return a structured response."""
    from .graph import build_graph, make_initial_state

    graph = build_graph(llm_classifier=classify_intent_with_ollama)
    initial_state = make_initial_state(database, question, user_ctx)
    final_state = graph.invoke(initial_state)
    return final_state["response"]
