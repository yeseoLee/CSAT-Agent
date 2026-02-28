from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda

from ..tools.document_tools import DocumentToolWrapper
from ..tools.math_tools import MathToolWrapper
from .state import AgentState


def _default_parse(payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("text", "")
    operation = "simplify"
    variable = "x"
    expression = None

    lowered = text.lower()
    if "derivative" in lowered or "d/dx" in lowered:
        operation = "differentiate"
    elif "integral" in lowered:
        operation = "integrate"
    elif "equation" in lowered or "solve" in lowered:
        operation = "solve_equation"

    match = re.search(r"f\(x\)\s*=\s*([^\n]+)", text)
    if match:
        expression = match.group(1).strip()

    return {
        "operation": operation,
        "variable": variable,
        "expression": expression,
        "constraints": ["0 <= answer <= 999", "answer is integer"],
    }


def _default_plan(payload: dict[str, Any]) -> dict[str, Any]:
    parse_result = payload.get("parse_result", {})
    operation = parse_result.get("operation", "simplify")

    steps = [
        "Normalize extracted expressions and constraints.",
        f"Run main math tool operation: {operation}.",
        "Apply domain/integer/range constraints if present.",
        "Substitute result back into constraints for verification.",
    ]

    return {"steps": steps}


def _default_explain(payload: dict[str, Any]) -> str:
    answer = payload.get("candidate_answer")
    verification = payload.get("verification", {})
    ok = verification.get("ok", False)
    reason = verification.get("reason", "no_reason")

    if ok:
        return f"Candidate answer: {answer}\nVerification: passed"
    return f"Candidate answer: {answer}\nVerification failed: {reason}"


@dataclass
class NodeDependencies:
    document_tools: DocumentToolWrapper = field(default_factory=DocumentToolWrapper)
    math_tools: MathToolWrapper = field(default_factory=MathToolWrapper)
    parser: Runnable[dict[str, Any], dict[str, Any]] = field(
        default_factory=lambda: RunnableLambda(_default_parse)
    )
    planner: Runnable[dict[str, Any], dict[str, Any]] = field(
        default_factory=lambda: RunnableLambda(_default_plan)
    )
    explainer: Runnable[dict[str, Any], str] = field(
        default_factory=lambda: RunnableLambda(_default_explain)
    )


def _append_tool_log(
    existing: list[dict[str, Any]],
    tool_name: str,
    payload: dict[str, Any],
    success: bool = True,
    error: str | None = None,
) -> list[dict[str, Any]]:
    next_logs = list(existing)
    next_logs.append(
        {
            "tool": tool_name,
            "payload": payload,
            "success": success,
            "error": error,
        }
    )
    return next_logs


class GraphNodes:
    def __init__(self, deps: NodeDependencies | None = None) -> None:
        self.deps = deps or NodeDependencies()

    def ingest_pdf(self, state: AgentState) -> AgentState:
        pdf_path = Path(state["input_pdf_path"])
        if not pdf_path.exists():
            errors = list(state.get("errors", []))
            errors.append(f"PDF file not found: {pdf_path}")
            return {
                "errors": errors,
                "final_response": "Input PDF file was not found.",
            }
        return {}

    def detect_pdf_type(self, state: AgentState) -> AgentState:
        pdf_path = state["input_pdf_path"]
        try:
            pdf_type = self.deps.document_tools.detect_pdf_type(pdf_path)
            tool_logs = _append_tool_log(
                state.get("tool_logs", []),
                "detect_pdf_type",
                {"input_pdf_path": pdf_path, "pdf_type": pdf_type},
            )
            return {"pdf_type": pdf_type, "tool_logs": tool_logs}
        except Exception as exc:  # pragma: no cover - runtime dependency path
            logs = _append_tool_log(
                state.get("tool_logs", []),
                "detect_pdf_type",
                {"input_pdf_path": pdf_path},
                success=False,
                error=str(exc),
            )
            errors = list(state.get("errors", []))
            errors.append(str(exc))
            return {"tool_logs": logs, "errors": errors}

    def extract_text(self, state: AgentState) -> AgentState:
        pdf_path = state["input_pdf_path"]
        try:
            raw_text = self.deps.document_tools.extract_text(pdf_path)
            quality = dict(state.get("quality_signals", {}))
            quality["digital_pages"] = len([text for text in raw_text.values() if text.strip()])
            logs = _append_tool_log(
                state.get("tool_logs", []),
                "extract_text",
                {"pages": len(raw_text)},
            )
            return {"raw_text_by_page": raw_text, "quality_signals": quality, "tool_logs": logs}
        except Exception as exc:  # pragma: no cover - runtime dependency path
            logs = _append_tool_log(
                state.get("tool_logs", []),
                "extract_text",
                {"input_pdf_path": pdf_path},
                success=False,
                error=str(exc),
            )
            errors = list(state.get("errors", []))
            errors.append(str(exc))
            return {"tool_logs": logs, "errors": errors}

    def ocr_text(self, state: AgentState) -> AgentState:
        pdf_path = state["input_pdf_path"]
        try:
            ocr_text = self.deps.document_tools.ocr_text(pdf_path)
            non_empty = [value for value in ocr_text.values() if value.strip()]
            quality = dict(state.get("quality_signals", {}))
            quality["ocr_pages"] = len(non_empty)
            logs = _append_tool_log(
                state.get("tool_logs", []),
                "ocr_text",
                {"pages": len(ocr_text)},
            )
            return {"ocr_text_by_page": ocr_text, "quality_signals": quality, "tool_logs": logs}
        except Exception as exc:  # pragma: no cover - runtime dependency path
            logs = _append_tool_log(
                state.get("tool_logs", []),
                "ocr_text",
                {"input_pdf_path": pdf_path},
                success=False,
                error=str(exc),
            )
            errors = list(state.get("errors", []))
            errors.append(str(exc))
            return {"tool_logs": logs, "errors": errors}

    def extract_text_and_ocr(self, state: AgentState) -> AgentState:
        text_updates = self.extract_text(state)
        merged_state: AgentState = {**state, **text_updates}
        ocr_updates = self.ocr_text(merged_state)

        raw_text_by_page = text_updates.get("raw_text_by_page", state.get("raw_text_by_page", {}))
        ocr_text_by_page = ocr_updates.get("ocr_text_by_page", state.get("ocr_text_by_page", {}))
        quality_signals = ocr_updates.get(
            "quality_signals", text_updates.get("quality_signals", state.get("quality_signals", {}))
        )
        tool_logs = ocr_updates.get(
            "tool_logs", text_updates.get("tool_logs", state.get("tool_logs", []))
        )
        errors = ocr_updates.get("errors", text_updates.get("errors", state.get("errors", [])))

        return {
            "raw_text_by_page": raw_text_by_page,
            "ocr_text_by_page": ocr_text_by_page,
            "quality_signals": quality_signals,
            "tool_logs": tool_logs,
            "errors": errors,
        }

    def math_extraction(self, state: AgentState) -> AgentState:
        pdf_path = state["input_pdf_path"]
        snippets = self.deps.document_tools.extract_math_latex(pdf_path)
        logs = _append_tool_log(
            state.get("tool_logs", []),
            "extract_math_latex",
            {"snippet_count": len(snippets)},
        )
        return {"latex_snippets": snippets, "tool_logs": logs}

    def merge_and_normalize(self, state: AgentState) -> AgentState:
        normalized_problem = self.deps.document_tools.merge_and_normalize(
            raw_text_by_page=state.get("raw_text_by_page", {}),
            ocr_text_by_page=state.get("ocr_text_by_page", {}),
            latex_snippets=state.get("latex_snippets", []),
        )
        return {"normalized_problem": normalized_problem}

    def parse_problem(self, state: AgentState) -> AgentState:
        parse_result = self.deps.parser.invoke({"text": state.get("normalized_problem", "")})
        metadata = dict(state.get("metadata", {}))
        metadata["answer_format"] = "integer"
        metadata["range"] = [0, 999]
        return {"parse_result": parse_result, "metadata": metadata}

    def plan_solution(self, state: AgentState) -> AgentState:
        plan = self.deps.planner.invoke(
            {
                "parse_result": state.get("parse_result", {}),
                "retries": state.get("retries", 0),
            }
        )
        return {"plan_steps": plan.get("steps", [])}

    def solve_with_tools(self, state: AgentState) -> AgentState:
        parse_result = state.get("parse_result", {})
        operation = parse_result.get("operation", "simplify")
        expression = parse_result.get("expression")
        variable = parse_result.get("variable", "x")
        candidate_answer: Any = None
        payload: dict[str, Any] = {"operation": operation, "expression": expression}

        try:
            if expression:
                if operation == "differentiate":
                    candidate_answer = self.deps.math_tools.differentiate(
                        expression, variable=variable
                    )
                elif operation == "integrate":
                    candidate_answer = self.deps.math_tools.integrate_definite(
                        expression, variable=variable
                    )
                elif operation == "solve_equation":
                    candidate_answer = self.deps.math_tools.solve_equation(
                        expression, variable=variable
                    )
                else:
                    candidate_answer = self.deps.math_tools.simplify_expr(expression)
            payload["candidate_answer"] = candidate_answer
            logs = _append_tool_log(state.get("tool_logs", []), "solve_with_tools", payload)
            return {"candidate_answer": candidate_answer, "tool_logs": logs}
        except Exception as exc:  # pragma: no cover - runtime dependency path
            logs = _append_tool_log(
                state.get("tool_logs", []),
                "solve_with_tools",
                payload,
                success=False,
                error=str(exc),
            )
            errors = list(state.get("errors", []))
            errors.append(str(exc))
            return {"tool_logs": logs, "errors": errors}

    def verify_solution(self, state: AgentState) -> AgentState:
        candidate = state.get("candidate_answer")
        metadata = state.get("metadata", {})
        retries = state.get("retries", 0)

        if candidate is None:
            return {
                "verification": {"ok": False, "reason": "candidate_answer_missing"},
                "retries": retries + 1,
            }

        if metadata.get("answer_format") == "integer":
            try:
                candidate_value = int(candidate)
                low, high = metadata.get("range", [0, 999])
                if not (low <= candidate_value <= high):
                    return {
                        "verification": {
                            "ok": False,
                            "reason": f"answer_out_of_range_{low}_{high}",
                        },
                        "retries": retries + 1,
                    }
            except (TypeError, ValueError):
                # For expression outputs, only format check is skipped at skeleton stage.
                pass

        return {"verification": {"ok": True, "reason": "passed"}}

    def explain(self, state: AgentState) -> AgentState:
        final_response = self.deps.explainer.invoke(
            {
                "candidate_answer": state.get("candidate_answer"),
                "verification": state.get("verification", {}),
                "plan_steps": state.get("plan_steps", []),
            }
        )
        return {"final_response": final_response}

    def finalize_failure(self, state: AgentState) -> AgentState:
        verification_reason = state.get("verification", {}).get("reason")
        error_reason = "; ".join(state.get("errors", [])) if state.get("errors") else None
        reason = verification_reason or error_reason or "unknown_failure"
        return {"final_response": f"Failed to solve problem. reason={reason}"}
