from __future__ import annotations

import random
import re


def roll_d6() -> int:
    return random.randint(1, 6)


def roll_d3() -> int:
    return random.randint(1, 3)


def roll_2d6() -> int:
    return roll_d6() + roll_d6()


def roll_tile_key() -> str:
    return f"{roll_d6()}{roll_d6()}"


def roll_start_tile_key() -> str:
    return f"0{roll_d6()}"


def roll_formula(formula: str) -> int:
    formula = formula.strip().lower().replace(" ", "")
    if formula.isdigit():
        return int(formula)
    if formula in {"d6", "1d6"}:
        return roll_d6()
    if formula in {"d3", "1d3"}:
        return roll_d3()

    match = re.fullmatch(r"(\d*)d([36])([+-]\d+)?", formula)
    if not match:
        raise ValueError(f"Unsupported dice formula: {formula}")
    count = int(match.group(1) or "1")
    sides = int(match.group(2))
    modifier = int(match.group(3) or "0")
    roller = roll_d6 if sides == 6 else roll_d3
    return sum(roller() for _ in range(count)) + modifier


def roll_exploding_d6() -> tuple[int, list[int]]:
    rolls = [roll_d6()]
    total = rolls[0]
    while rolls[-1] == 6:
        rolls.append(roll_d6())
        total += rolls[-1]
    return total, rolls
