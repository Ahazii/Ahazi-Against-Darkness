from __future__ import annotations

import ast
from typing import Any


ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Constant,
    ast.Name,
)


def _safe_eval(node: ast.AST, variables: dict[str, int]) -> int:
    if not isinstance(node, ALLOWED_NODES):
        raise ValueError("Unsafe expression")

    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, variables)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return int(node.value)
        raise ValueError("Unsupported constant")
    if isinstance(node, ast.Name):
        if node.id in variables:
            return int(variables[node.id])
        raise ValueError("Unknown variable")
    if isinstance(node, ast.UnaryOp):
        operand = _safe_eval(node.operand, variables)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return operand
    if isinstance(node, ast.BinOp):
        left = _safe_eval(node.left, variables)
        right = _safe_eval(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return int(left / right)
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return int(left**right)

    raise ValueError("Unsupported expression")


def eval_formula(formula: str, variables: dict[str, int]) -> int:
    expression = ast.parse(formula, mode="eval")
    return _safe_eval(expression, variables)
