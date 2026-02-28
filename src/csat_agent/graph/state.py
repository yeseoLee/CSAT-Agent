from __future__ import annotations

from typing import Any, Literal, TypedDict
from uuid import uuid4

PdfType = Literal["digital", "scanned", "mixed", "unknown"]


class MathSnippet(TypedDict, total=False):
    page: int
    bbox: tuple[float, float, float, float] | None
    latex: str
    confidence: float


class VerificationResult(TypedDict, total=False):
    ok: bool
    reason: str
    checked_constraints: list[str]
    counterexample: str | None


class AgentState(TypedDict, total=False):
    run_id: str
    input_pdf_path: str
    pdf_type: PdfType
    raw_text_by_page: dict[int, str]
    ocr_text_by_page: dict[int, str]
    latex_snippets: list[MathSnippet]
    normalized_problem: str
    parse_result: dict[str, Any]
    metadata: dict[str, Any]
    plan_steps: list[str]
    tool_logs: list[dict[str, Any]]
    candidate_answer: Any
    verification: VerificationResult
    final_response: str
    retries: int
    max_retries: int
    quality_signals: dict[str, Any]
    errors: list[str]


def make_initial_state(input_pdf_path: str, max_retries: int = 2) -> AgentState:
    return AgentState(
        run_id=str(uuid4()),
        input_pdf_path=input_pdf_path,
        pdf_type="unknown",
        raw_text_by_page={},
        ocr_text_by_page={},
        latex_snippets=[],
        normalized_problem="",
        parse_result={},
        metadata={},
        plan_steps=[],
        tool_logs=[],
        candidate_answer=None,
        verification=VerificationResult(ok=False, reason="not_verified"),
        final_response="",
        retries=0,
        max_retries=max_retries,
        quality_signals={},
        errors=[],
    )
