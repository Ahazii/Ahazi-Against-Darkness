"""Report functions referencing scope-sensitive identifiers without declaring them."""
from __future__ import annotations

import re
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / "src" / "app" / "static" / "app.js"

WATCH = (
    "immediateLocked",
    "combatLocked",
    "actionLocked",
    "hirelingLocked",
    "inExploration",
    "inCombat",
    "livingFoes",
    "reactionsPending",
)


def extract_functions(source: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for match in re.finditer(r"^function (\w+)\(([^)]*)\)", source, re.M):
        name = match.group(1)
        params = match.group(2)
        brace = source.find("{", match.end() - 1)
        depth = 0
        end = brace
        for i in range(brace, len(source)):
            if source[i] == "{":
                depth += 1
            elif source[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        out.append((name, params, source[brace + 1 : end - 1]))
    return out


def locals_and_params(params: str, body: str) -> set[str]:
    names = set(re.findall(r"\b(?:const|let|var)\s+(\w+)", body))
    for part in params.split(","):
        token = part.strip().split("=")[0].strip()
        if token.startswith("..."):
            token = token[3:]
        if token:
            names.add(token)
    return names


def main() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    issues: list[str] = []
    for name, params, body in extract_functions(source):
        scope = locals_and_params(params, body)
        for ident in WATCH:
            if ident in params.split(","):
                continue
            if not re.search(rf"\b{re.escape(ident)}\b", body):
                continue
            if ident in scope:
                continue
            # ignore nested function bodies by only checking if declared anywhere in outer function
            # still a hit if outer function uses ident without declaring
            issues.append(f"{name}: uses `{ident}` without local/param declaration")

    print("=== Scope-sensitive identifier leaks ===")
    for line in sorted(set(issues)):
        print(f"  {line}")

    if not issues:
        print("  none found")


if __name__ == "__main__":
    main()
