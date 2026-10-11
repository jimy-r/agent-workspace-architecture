#!/usr/bin/env python3
"""
Roles library validator.

Checks two things:

1. **Role frontmatter schema** — every `roles/*.md` except `README.md` and
   `_template.md` must declare the full role schema: `name`, `role_version`
   (semver), `description`, `category`, `default_model`, `tools` (list),
   `requires_context` (bool), `tags` (list).

2. **Binding composition** — every `<project>/.claude/agents/*.md` file must
   reference an existing canonical role via `@<workspace>/roles/<name>.md` AND
   include a context file via `@<path>/CONTEXT.md` (or `profile.md`,
   for a project that keeps its context under that name).

Run from the workspace root:
    python roles/_validate.py

Exit code 0 on success, 1 on any failure. Findings are printed grouped by file.

Wire into `audit.bat` or a pre-commit check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROLES_DIR = Path(__file__).parent.resolve()
WORKSPACE = ROLES_DIR.parent

REQUIRED_ROLE_FIELDS = {
    "name": str,
    "role_version": str,
    "description": str,
    "category": str,
    "default_model": str,
    "tools": list,
    "requires_context": bool,
    "tags": list,
}

VALID_MODELS = {"haiku", "sonnet", "opus"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict | None:
    """Tiny YAML subset parser — enough for our flat frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm: dict = {}
    for line in m.group(1).splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fm[key] = (
                [v.strip() for v in inner.split(",") if v.strip()] if inner else []
            )
        elif value.lower() in {"true", "false"}:
            fm[key] = value.lower() == "true"
        else:
            fm[key] = value.strip('"').strip("'")
    return fm


def validate_role(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        return [f"no frontmatter block"]

    # required fields present + typed
    for field, expected_type in REQUIRED_ROLE_FIELDS.items():
        if field not in fm:
            errors.append(f"missing required field: {field}")
            continue
        value = fm[field]
        if expected_type is bool and not isinstance(value, bool):
            errors.append(f"field '{field}' must be bool, got {type(value).__name__}")
        elif expected_type is list and not isinstance(value, list):
            errors.append(f"field '{field}' must be list, got {type(value).__name__}")
        elif expected_type is str and not isinstance(value, str):
            errors.append(f"field '{field}' must be str, got {type(value).__name__}")

    # name matches filename
    stem = path.stem
    if fm.get("name") != stem:
        errors.append(f"frontmatter name '{fm.get('name')}' != filename stem '{stem}'")

    # semver on role_version
    ver = fm.get("role_version", "")
    if isinstance(ver, str) and not SEMVER_RE.match(ver):
        errors.append(f"role_version '{ver}' is not semver (X.Y.Z)")

    # default_model
    if fm.get("default_model") not in VALID_MODELS:
        errors.append(
            f"default_model '{fm.get('default_model')}' not in {sorted(VALID_MODELS)}"
        )

    # five required body sections
    # Optional sections (allowed but not required):
    #   ## Red Flags
    #   ## Rationalization Table
    # These are valid between ## Constraints and ## Method.
    body = text[text.find("---", 3) + 3 :] if text.count("---") >= 2 else ""
    for section in (
        "## Identity",
        "## Directives",
        "## Constraints",
        "## Method",
        "## Output format",
    ):
        if section not in body:
            errors.append(f"missing body section: {section}")

    return errors


def find_canonical_roles() -> set[str]:
    return {
        p.stem
        for p in ROLES_DIR.glob("*.md")
        if p.name not in {"README.md", "_template.md"}
    }


def validate_binding(path: Path, canonical: set[str]) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")

    # must include a canonical role via @roles/<name>.md
    # Paths may contain spaces (e.g. "General Projects"), so match to end of line.
    role_includes = re.findall(r"@[^\n]*?/roles/([A-Za-z0-9_-]+)\.md", text)
    if not role_includes:
        errors.append("binding does not @include any canonical role from roles/")
    else:
        for role_name in role_includes:
            if role_name not in canonical:
                errors.append(f"binding @includes unknown role: {role_name}")

    # must include a context file (CONTEXT.md or profile.md)
    context_re = re.compile(r"@[^\n]*?(CONTEXT\.md|profile\.md)")
    if not context_re.search(text):
        errors.append("binding does not @include a CONTEXT.md or profile.md")

    return errors


def main() -> int:
    failures = 0

    # Phase 1: canonical roles
    role_files = sorted(
        p for p in ROLES_DIR.glob("*.md") if p.name not in {"README.md", "_template.md"}
    )
    print(f"Validating {len(role_files)} canonical roles in {ROLES_DIR}")
    for path in role_files:
        errors = validate_role(path)
        if errors:
            failures += 1
            print(f"\n  FAIL {path.relative_to(WORKSPACE)}")
            for e in errors:
                print(f"    - {e}")
        else:
            print(f"  OK   {path.relative_to(WORKSPACE)}")

    # Phase 2: project bindings
    canonical = find_canonical_roles()
    binding_files = sorted(WORKSPACE.glob("**/.claude/agents/*.md"))
    # skip global agents in <workspace>/.claude/agents (those are not role bindings)
    workspace_agents_dir = (WORKSPACE / ".claude" / "agents").resolve()
    binding_files = [
        p for p in binding_files if p.parent.resolve() != workspace_agents_dir
    ]

    print(f"\nValidating {len(binding_files)} project role bindings")
    for path in binding_files:
        errors = validate_binding(path, canonical)
        if errors:
            failures += 1
            print(f"\n  FAIL {path.relative_to(WORKSPACE)}")
            for e in errors:
                print(f"    - {e}")
        else:
            print(f"  OK   {path.relative_to(WORKSPACE)}")

    if failures:
        print(f"\n{failures} failure(s).")
        return 1
    print(f"\nAll role files and bindings valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
