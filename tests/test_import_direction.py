"""Only main.py composes routes; anything else wanting a route's answer uses queries/."""

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "radarvan"


def _imported_modules(path: Path) -> set[str]:
    package_parts = path.relative_to(PACKAGE.parent).with_suffix("").parts[:-1]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            keep = len(package_parts) - node.level + 1
            base = list(package_parts[:keep]) if node.level else []
            module = ".".join([*base, *([node.module] if node.module else [])])
            found.add(module)
            found.update(f"{module}.{alias.name}" for alias in node.names)
    return found


def test_only_main_imports_routes() -> None:
    offenders = []
    for path in PACKAGE.rglob("*.py"):
        rel = path.relative_to(PACKAGE)
        if rel == Path("main.py"):
            continue
        offenders.extend(
            f"{rel}: {module}"
            for module in _imported_modules(path)
            if module.startswith("radarvan.routes.")
        )
    assert offenders == [], offenders
