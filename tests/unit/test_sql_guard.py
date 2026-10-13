"""Static analysis test for SQL injection prevention (Phase 2, AT-05).

Verifies that no SQL query in carecast/ is constructed using:
- f-strings (JoinedStr)
- String concatenation (+)
- % operator formatting
- .format() method calls
All queries must use parameterised placeholders (?).
"""

import ast
from pathlib import Path


def _check_node_for_sql_construction(node: ast.AST, file_path: Path) -> list[str]:
    violations: list[str] = []

    # Check calls to execute / executemany
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in ("execute", "executemany"):
            if node.args:
                sql_arg = node.args[0]
                # Check for f-string
                if isinstance(sql_arg, ast.JoinedStr):
                    violations.append(
                        f"{file_path}:{node.lineno} - f-string used in db.{func.attr}() call"
                    )
                # Check for % or +
                elif isinstance(sql_arg, ast.BinOp) and isinstance(sql_arg.op, (ast.Mod, ast.Add)):
                    violations.append(
                        f"{file_path}:{node.lineno} - string concatenation/% used in db.{func.attr}() call"
                    )
                # Check for .format()
                elif isinstance(sql_arg, ast.Call) and isinstance(sql_arg.func, ast.Attribute):
                    if sql_arg.func.attr == "format":
                        violations.append(
                            f"{file_path}:{node.lineno} - .format() used in db.{func.attr}() call"
                        )

    # General check: any f-string containing SQL keywords
    if isinstance(node, ast.JoinedStr):
        text_parts = [
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        ]
        full_text = " ".join(text_parts).upper()
        sql_keywords = ("SELECT ", "INSERT INTO", "UPDATE ", "DELETE FROM", "WHERE ")
        if any(kw in full_text for kw in sql_keywords):
            violations.append(
                f"{file_path}:{node.lineno} - SQL keyword found inside f-string: {full_text[:40]}..."
            )

    return violations


def test_at_05_sql_guard_no_dynamic_queries() -> None:
    """AT-05: Ensure no dynamic SQL construction exists across carecast package."""
    carecast_dir = Path("carecast")
    assert carecast_dir.exists(), "carecast directory not found"

    all_violations: list[str] = []

    for py_file in carecast_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            violations = _check_node_for_sql_construction(node, py_file)
            all_violations.extend(violations)

    assert not all_violations, f"Found SQL injection vulnerabilities:\n" + "\n".join(all_violations)
