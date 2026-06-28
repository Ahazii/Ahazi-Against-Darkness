"""Find likely ReferenceError bugs in app.js."""
from __future__ import annotations

import re
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / "src" / "app" / "static" / "app.js"


def main() -> None:
    js = APP_JS.read_text(encoding="utf-8")
    top = set(re.findall(r"^const (\w+)", js, re.M)) | set(re.findall(r"^function (\w+)", js, re.M))

    dom_suffixes = ("El", "Btn", "Select", "Prefs", "Hint", "Panel", "Form", "Input", "Dialog")
    dom_uses = sorted(
        {
            m.group(1)
            for m in re.finditer(rf"\b(\w+(?:{'|'.join(dom_suffixes)}))\?\.", js)
            if m.group(1) not in top
        }
    )
    print("=== DOM-like identifiers used with ?. but no top-level const ===")
    for name in dom_uses:
        print(f"  {name}")

    locked_uses = sorted(
        {
            m.group(1)
            for m in re.finditer(r"\b([a-zA-Z]+Locked)\b", js)
            if m.group(1) not in top
        }
    )
    print("\n=== *Locked identifiers (check declaration per function) ===")
    for name in locked_uses:
        lines = [i + 1 for i, line in enumerate(js.splitlines()) if re.search(rf"\b{name}\b", line)]
        decl_lines = [i for i in lines if re.search(rf"\b(?:const|let|var)\s+{name}\b", js.splitlines()[i - 1])]
        use_only = [i for i in lines if i not in decl_lines]
        if use_only:
            print(f"  {name}: uses at {use_only[:6]}{'...' if len(use_only) > 6 else ''}")

    # Functions that use identifier in disabled= assignment without declaring it in same function
    print("\n=== Functions using immediateLocked/combatLocked/reactionsPending without local const ===")
    for fn_name in sorted(set(re.findall(r"^function (\w+)", js, re.M))):
        body = extract_function(js, fn_name)
        if not body:
            continue
        for ident in ("immediateLocked", "combatLocked", "reactionsPending", "inExploration", "livingFoes"):
            if re.search(rf"\b{ident}\b", body) and not re.search(rf"\b(?:const|let|var)\s+{ident}\b", body):
                # allowed if it's a function param - check header
                header = re.search(rf"function {re.escape(fn_name)}\(([^)]*)\)", js)
                params = header.group(1) if header else ""
                if ident in params:
                    continue
                # allowed if global function name
                if ident == "livingFoes" and fn_name == "appendMemberCombatActions":
                    continue  # passed as param
                if ident in {"reactionsPending"} and fn_name == "appendMemberCombatActions":
                    continue
                print(f"  {fn_name}: {ident}")


def extract_function(source: str, name: str) -> str | None:
    match = re.search(rf"function {re.escape(name)}\(", source)
    if not match:
        return None
    brace = source.find("{", match.end() - 1)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : i]
    return None


if __name__ == "__main__":
    main()
