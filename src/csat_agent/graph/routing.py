from __future__ import annotations

from .state import AgentState


def route_after_ingest(state: AgentState) -> str:
    if state.get("errors"):
        return "finalize_failure"
    return "detect_pdf_type"


def route_pdf_type(state: AgentState) -> str:
    pdf_type = state.get("pdf_type", "unknown")
    if pdf_type == "digital":
        return "extract_text"
    if pdf_type == "scanned":
        return "ocr_text"
    return "extract_text_and_ocr"


def route_after_verify(state: AgentState) -> str:
    verification = state.get("verification", {})
    if verification.get("ok"):
        return "explain"

    retries = int(state.get("retries", 0))
    max_retries = int(state.get("max_retries", 2))

    if retries < max_retries:
        return "replan"
    return "finalize_failure"
