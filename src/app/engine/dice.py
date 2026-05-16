from __future__ import annotations

import random
import re


def roll_d6() -> int:
    return random.randint(1, 6)


def roll_2d6() -> int:
    return roll_d6() + roll_d6()


def roll_tile_key() -> str:
    return f"{roll_d6()}{roll_d6()}"


def roll_start_tile_key() -> str:
    return f"0{roll_d6()}"


def roll_formula(formula: str) -> int:
    formula = formula.strip().lower()
    if formula.isdigit():
        return int(formula)

    match = re.fullmatch(r"(\d*)d6([+-]\d+)?", formula)
    if not match:
        raise ValueError(f"Unsupported dice formula: {formula}")
    count = int(match.group(1) or "1")
    modifier = int(match.group(2) or "0")
    return sum(roll_d6() for _ in range(count)) + modifier
