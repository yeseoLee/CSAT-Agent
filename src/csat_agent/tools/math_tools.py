from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import sympy as sp
from langchain_core.tools import StructuredTool
from sympy.parsing.sympy_parser import parse_expr

try:
    import z3
except ImportError:  # pragma: no cover - optional dependency at runtime
    z3 = None


def _safe_sympy_expr(expr: str) -> sp.Expr:
    return parse_expr(expr, evaluate=True)


@dataclass
class MathToolWrapper:
    """Wrapper around symbolic/numeric math tools used by the graph."""

    def simplify_expr(self, expr: str) -> str:
        parsed = _safe_sympy_expr(expr)
        return str(sp.simplify(parsed))

    def solve_equation(self, equation: str, variable: str = "x") -> list[str]:
        var = sp.Symbol(variable)
        if "=" in equation:
            lhs, rhs = equation.split("=", 1)
            eq_obj = sp.Eq(_safe_sympy_expr(lhs), _safe_sympy_expr(rhs))
        else:
            eq_obj = sp.Eq(_safe_sympy_expr(equation), 0)
        solutions = sp.solve(eq_obj, var)
        return [str(solution) for solution in solutions]

    def differentiate(self, expr: str, variable: str = "x") -> str:
        parsed = _safe_sympy_expr(expr)
        var = sp.Symbol(variable)
        return str(sp.diff(parsed, var))

    def integrate_definite(
        self,
        expr: str,
        variable: str = "x",
        lower: float | None = None,
        upper: float | None = None,
    ) -> str:
        parsed = _safe_sympy_expr(expr)
        var = sp.Symbol(variable)
        if lower is None or upper is None:
            return str(sp.integrate(parsed, var))
        return str(sp.integrate(parsed, (var, lower, upper)))

    def solve_integer_constraints(
        self,
        symbols: Iterable[str],
        constraints: Iterable[str],
        lower_bound: int = 0,
        upper_bound: int = 999,
    ) -> dict[str, int]:
        if z3 is None:
            raise RuntimeError("z3-solver is not installed.")

        symbol_map = {name: z3.Int(name) for name in symbols}
        solver = z3.Solver()

        for symbol in symbol_map.values():
            solver.add(symbol >= lower_bound, symbol <= upper_bound)

        env: dict[str, Any] = {"Abs": z3.Abs, **symbol_map}
        for raw_expr in constraints:
            # Skeleton-only parser for constraints; replace with a dedicated parser in production.
            solver.add(eval(raw_expr, {"__builtins__": {}}, env))  # noqa: S307

        if solver.check() != z3.sat:
            return {}

        model = solver.model()
        result: dict[str, int] = {}
        for name, symbol in symbol_map.items():
            evaluated = model.eval(symbol, model_completion=True)
            result[name] = int(evaluated.as_long())
        return result

    def as_langchain_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(
                func=self.simplify_expr,
                name="sympy_simplify_expr",
                description="Simplify a symbolic expression with SymPy.",
            ),
            StructuredTool.from_function(
                func=self.solve_equation,
                name="sympy_solve_equation",
                description="Solve an equation for a target variable with SymPy.",
            ),
            StructuredTool.from_function(
                func=self.differentiate,
                name="sympy_differentiate",
                description="Differentiate an expression with respect to a variable.",
            ),
            StructuredTool.from_function(
                func=self.integrate_definite,
                name="sympy_integrate",
                description="Integrate an expression (indefinite or definite).",
            ),
            StructuredTool.from_function(
                func=self.solve_integer_constraints,
                name="z3_solve_integer_constraints",
                description="Solve bounded integer constraints with z3-solver.",
            ),
        ]
