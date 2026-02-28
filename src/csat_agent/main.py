from __future__ import annotations

import argparse
from pathlib import Path

from .graph.builder import build_graph
from .graph.state import make_initial_state


def run(pdf_path: str, max_retries: int = 2) -> dict:
    graph = build_graph()
    initial_state = make_initial_state(input_pdf_path=pdf_path, max_retries=max_retries)
    return graph.invoke(initial_state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CSAT math LangGraph pipeline.")
    parser.add_argument("pdf_path", type=str, help="Path to the input problem PDF.")
    parser.add_argument("--max-retries", type=int, default=2, help="Max verify loop retries.")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        raise SystemExit(f"File not found: {pdf_path}")

    final_state = run(str(pdf_path), max_retries=args.max_retries)
    print(final_state.get("final_response", "No final response"))


if __name__ == "__main__":
    main()
