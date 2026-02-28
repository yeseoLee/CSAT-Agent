from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import GraphNodes, NodeDependencies
from .routing import route_after_ingest, route_after_verify, route_pdf_type
from .state import AgentState


def build_graph(deps: NodeDependencies | None = None):
    nodes = GraphNodes(deps=deps)
    builder = StateGraph(AgentState)

    builder.add_node("ingest_pdf", nodes.ingest_pdf)
    builder.add_node("detect_pdf_type", nodes.detect_pdf_type)
    builder.add_node("extract_text", nodes.extract_text)
    builder.add_node("ocr_text", nodes.ocr_text)
    builder.add_node("extract_text_and_ocr", nodes.extract_text_and_ocr)
    builder.add_node("math_extraction", nodes.math_extraction)
    builder.add_node("merge_and_normalize", nodes.merge_and_normalize)
    builder.add_node("parse_problem", nodes.parse_problem)
    builder.add_node("plan_solution", nodes.plan_solution)
    builder.add_node("solve_with_tools", nodes.solve_with_tools)
    builder.add_node("verify_solution", nodes.verify_solution)
    builder.add_node("explain", nodes.explain)
    builder.add_node("finalize_failure", nodes.finalize_failure)

    builder.add_edge(START, "ingest_pdf")
    builder.add_conditional_edges(
        "ingest_pdf",
        route_after_ingest,
        {
            "detect_pdf_type": "detect_pdf_type",
            "finalize_failure": "finalize_failure",
        },
    )
    builder.add_conditional_edges(
        "detect_pdf_type",
        route_pdf_type,
        {
            "extract_text": "extract_text",
            "ocr_text": "ocr_text",
            "extract_text_and_ocr": "extract_text_and_ocr",
        },
    )

    builder.add_edge("extract_text", "math_extraction")
    builder.add_edge("ocr_text", "math_extraction")
    builder.add_edge("extract_text_and_ocr", "math_extraction")
    builder.add_edge("math_extraction", "merge_and_normalize")
    builder.add_edge("merge_and_normalize", "parse_problem")
    builder.add_edge("parse_problem", "plan_solution")
    builder.add_edge("plan_solution", "solve_with_tools")
    builder.add_edge("solve_with_tools", "verify_solution")
    builder.add_conditional_edges(
        "verify_solution",
        route_after_verify,
        {
            "explain": "explain",
            "replan": "plan_solution",
            "finalize_failure": "finalize_failure",
        },
    )

    builder.add_edge("explain", END)
    builder.add_edge("finalize_failure", END)
    return builder.compile()
