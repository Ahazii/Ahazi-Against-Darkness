from __future__ import annotations

import random
import re


def roll_d6() -> int:
    return random.randint(1, 6)


def roll_2d6() -> int:
    return roll_d6() + roll_d6()


def roll_d66() -> int:
    return roll_d6() * 10 + roll_d6()


def roll_formula(formula: str) -> int:
    formula = formula.strip().lower()
    if formula == "1":
        return 1

    match = re.fullmatch(r"(\d*)d6([+-]\d+)?", formula)
    if match:
        count = int(match.group(1)) if match.group(1) else 1
        modifier = int(match.group(2)) if match.group(2) else 0
        return sum(roll_d6() for _ in range(count)) + modifier

    raise ValueError(f"Unsupported dice formula: {formula}")
