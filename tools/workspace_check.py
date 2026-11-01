#!/usr/bin/env python3
"""workspace_check.py — a scored maturity check for an agent workspace.

Point it at a directory that holds a workspace with a CLAUDE.md, an AGENTS.md
or both, and it reports how that workspace scores against the
mechanically-checkable subset of PATTERNS.md: context budget, settings and hook
shape, a permission floor, credential hygiene, skill and agent frontmatter,
canonical-copy duplication, and memory index size. The settings, hook,
permission, skill and agent checks read Claude Code's .claude/ layout only, so
another agent's config goes unscored. Every check prints one evidence line and
names the pattern it came from, so a WARN is a pointer into the reasoning
rather than a verdict.

What it deliberately does NOT do:
  - No LLM, no judge, no scoring of prose. Every check is a deterministic file
    read, so the same tree scores the same twice.
  - No network. Nothing is fetched, uploaded, or phoned home.
  - No writes. The target tree is opened read-only; the only files this ever
    creates are throwaway fixtures inside a temp dir during --self-test.
  - No execution. It never runs a script, hook, or command it finds in the
    target tree, and it treats every file's contents as untrusted data.

It measures a floor, not a ceiling. A 10/10 says the mechanical hygiene is in
place; it says nothing about whether the roles are any good, whether the memory
points at the right sources, or whether the audit cadence is honest. Those are
the parts that need a human, which is exactly why they are not scored here.

Usage:
    python workspace_check.py              # check the current directory
    python workspace_check.py <path>       # check another workspace
    python workspace_check.py --json       # machine-readable, stdout only
    python workspace_check.py --self-test  # fixture-based assertions, exit 0/1

Stdlib only, Python 3.9+, Windows and POSIX.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

# --- Pattern anchors --------------------------------------------------------
# GitHub heading slugs from PATTERNS.md: lowercase, punctuation dropped, spaces
# to hyphens (an em-dash drops out and leaves the two hyphens around it).
PATTERNS_URL = (
    "https://github.com/jimy-r/agent-workspace-architecture/blob/main/PATTERNS.md"
)
ISSUES_URL = "https://github.com/jimy-r/agent-workspace-architecture/issues"
REVIEW_URL = (
    "https://github.com/jimy-r/agent-workspace-architecture"
    "/discussions/categories/review-my-workspace"
)

PATTERN_SLUGS = {
    1: "1-pure-roles-composed-with-project-facts",
    4: "4-tier-by-mechanical-impact-not-by-tone",
    5: "5-memory-points-it-doesnt-mirror",
    6: "6-credentials-live-in-one-place-never-in-files",
    7: "7-a-cheap-hook-beats-a-careful-agent",
    9: "9-context-is-a-budget-not-a-constant",
    10: "10-a-skill-is-editable-weights--never-adopt-a-self-edit-without-a-gate",
    17: "17-one-canonical-copy-and-pointers-from-everywhere-else",
}

PASS, WARN, FAIL, NA = "PASS", "WARN", "FAIL", "NA"
SCORE_WEIGHTS = {PASS: 1.0, WARN: 0.5, FAIL: 0.0}

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}
MAX_SCAN_BYTES = 512 * 1024

CLAUDE_FILES = ("CLAUDE.md", ".claude/CLAUDE.md")
AGENTS_FILES = ("AGENTS.md", ".claude/AGENTS.md")
AGENTS_IMPORT = re.compile(r"(?<![\w`/.-])@(?:\./)?(?:\.claude/)?AGENTS\.md(?![\w.-])")

BINARY_EXTS = {
    ".7z",
    ".a",
    ".avi",
    ".bin",
    ".bmp",
    ".bz2",
    ".class",
    ".dll",
    ".dmg",
    ".db",
    ".dylib",
    ".eot",
    ".exe",
    ".flac",
    ".gif",
    ".gz",
    ".ico",
    ".iso",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lib",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".msi",
    ".nupkg",
    ".o",
    ".ogg",
    ".otf",
    ".pack",
    ".pdf",
    ".png",
    ".psd",
    ".pyc",
    ".pyo",
    ".rar",
    ".so",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tiff",
    ".ttf",
    ".wav",
    ".webp",
    ".whl",
    ".woff",
    ".woff2",
    ".xz",
    ".zip",
    ".zst",
}

# High-confidence credential shapes only. A noisy secret scanner gets muted,
# which is worse than no scanner, so anything that false-positives on ordinary
# prose or on a placeholder stays out of this list.
CRED_PATTERNS = [
    ("Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Postgres URL with password", re.compile(r"postgres(ql)?://\S+:\S+@")),
]


class Check:
    """One check result: an id, a status, one evidence line, a pattern anchor."""

    def __init__(self, check_id: str, status: str, evidence: str, pattern: int):
        self.id = check_id
        self.status = status
        self.evidence = evidence
        self.pattern = pattern

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "evidence": self.evidence,
            "pattern": PATTERN_SLUGS[self.pattern],
        }


# =============================================================================
# Filesystem helpers — read-only, failure-tolerant
# =============================================================================
def read_text(path: Path) -> str:
    """Return a file's text, or an empty string if it cannot be read."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def rel(root: Path, path: Path) -> str:
    """Display path, relative to the workspace root, forward-slashed."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def walk_files(root: Path):
    """Yield every file under root, pruning the skip dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def kb(num_bytes: int) -> float:
    return round(num_bytes / 1024.0, 1)


def mask(value: str) -> str:
    """Keep the first 8 characters, mask the rest. Never print a whole secret."""
    return value[:8] + "*" * min(max(len(value) - 8, 0), 16)


def existing(root: Path, names):
    """The named files that exist under root, in the order given."""
    return [root / n for n in names if (root / n).is_file()]


def distinct(paths):
    """Drop paths that resolve to the same file, keeping the first of each."""
    seen = set()
    out = []
    for path in paths:
        key = path.resolve()
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def claude_surface(root: Path):
    """What Claude Code loads by default: CLAUDE files, else AGENTS files, plus rules."""
    # Rule from Claude Code's memory docs: AGENTS.md loads only when no CLAUDE.md
    # exists, unless a CLAUDE file imports it with @AGENTS.md.
    claude = existing(root, CLAUDE_FILES)
    if claude:
        files = list(claude)
        if any(AGENTS_IMPORT.search(read_text(p)) for p in claude):
            files += existing(root, AGENTS_FILES)
    else:
        files = existing(root, AGENTS_FILES)
    rules_dir = root / ".claude" / "rules"
    if rules_dir.is_dir():
        files.extend(sorted(p for p in rules_dir.glob("*.md") if p.is_file()))
    return distinct(files)


def agents_surface(root: Path):
    """What another agent that reads AGENTS.md loads at the root."""
    return distinct(existing(root, ("AGENTS.md",)))


def parse_frontmatter(text: str):
    """Line-parse a leading `---` block into a flat field map.

    Deliberately not a YAML parser: a linter that a stranger runs must not need
    a third-party dependency, and the two fields this cares about are plain
    scalars in every real skill and agent file. Returns None if the file has no
    terminated frontmatter block.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields: dict = {}
    key = None
    for raw in lines[1:]:
        if raw.strip() == "---":
            return fields
        if key and raw[:1] in (" ", "\t") and raw.strip():
            fields[key] = (fields[key] + " " + raw.strip()).strip()
            continue
        if ":" in raw and not raw.startswith(" "):
            name, _, value = raw.partition(":")
            key = name.strip()
            value = value.strip()
            if value in (">", "|", ">-", "|-", "-"):
                value = ""
            fields[key] = value.strip("'\"")
        else:
            key = None
    return None


def load_settings(root: Path):
    """Parse both settings files. Returns [(path, parsed_or_None, error_or_None)]."""
    out = []
    for name in ("settings.json", "settings.local.json"):
        path = root / ".claude" / name
        if not path.is_file():
            continue
        try:
            out.append((path, json.loads(read_text(path)), None))
        except json.JSONDecodeError as exc:
            out.append((path, None, f"line {exc.lineno}: {exc.msg}"))
    return out


# =============================================================================
# Checks A + B — the instruction surface (pattern 9)
# =============================================================================
def check_instruction_file(root: Path) -> Check:
    found = existing(root, CLAUDE_FILES + AGENTS_FILES)
    if not found:
        return Check(
            "instruction-file-present",
            FAIL,
            "no CLAUDE.md or AGENTS.md at the workspace root, the two instruction "
            "files this reads",
            9,
        )
    if len(found) > 1 and len(distinct(found)) == 1:
        names = " and ".join(rel(root, p) for p in found)
        detail = f"{names} are one file, {kb(found[0].stat().st_size)} KB"
    else:
        detail = ", ".join(f"{rel(root, p)} {kb(p.stat().st_size)} KB" for p in found)
    return Check("instruction-file-present", PASS, detail, 9)


def _total_bytes(files) -> int:
    return sum(f.stat().st_size for f in files)


def check_context_budget(root: Path) -> Check:
    claude = claude_surface(root)
    agents = agents_surface(root)
    files = agents if _total_bytes(agents) > _total_bytes(claude) else claude
    if not files:
        return Check("context-budget", NA, "no instruction files to measure", 9)
    total_kb = kb(_total_bytes(files))
    detail = f"{total_kb} KB across {len(files)} always-loaded file(s)"
    if (
        claude
        and agents
        and {p.resolve() for p in claude} != {p.resolve() for p in agents}
    ):
        detail += (
            f", the larger of Claude Code's load ({kb(_total_bytes(claude))} KB) "
            f"and an AGENTS.md reader's ({kb(_total_bytes(agents))} KB)"
        )
    if total_kb > 40:
        return Check("context-budget", FAIL, f"{detail}, over the 40 KB ceiling", 9)
    if total_kb >= 15:
        return Check("context-budget", WARN, f"{detail}, past the 15 KB target", 9)
    return Check("context-budget", PASS, detail, 9)


# =============================================================================
# Checks C + D — settings and hook shape (pattern 7)
# =============================================================================
def check_settings_parse(root: Path, settings) -> Check:
    if not settings:
        return Check(
            "settings-parse",
            WARN,
            "no .claude/settings.json or settings.local.json found (Claude Code "
            "settings are the only config this reads)",
            7,
        )
    broken = [(p, err) for p, _, err in settings if err]
    if broken:
        path, err = broken[0]
        extra = f" (+{len(broken) - 1} more)" if len(broken) > 1 else ""
        return Check("settings-parse", FAIL, f"{rel(root, path)} {err}{extra}", 7)
    names = ", ".join(rel(root, p) for p, _, _ in settings)
    return Check("settings-parse", PASS, f"{names} parse as JSON", 7)


def _hook_entry_defect(entry) -> str:
    """Return a defect string for one event entry, or an empty string if sound."""
    if not isinstance(entry, dict):
        return "entry is not an object"
    if "matcher" in entry and not isinstance(entry["matcher"], str):
        return "matcher is not a string"
    inner = entry.get("hooks")
    if not isinstance(inner, list) or not inner:
        return "entry has no hooks list"
    for hook in inner:
        if not isinstance(hook, dict):
            return "hook is not an object"
        if not isinstance(hook.get("type"), str):
            return "hook has no type"
        if not isinstance(hook.get("command"), str) or not hook["command"].strip():
            return "hook has no command"
    return ""


def check_hooks_guard(root: Path, settings) -> Check:
    parsed = [(p, data) for p, data, err in settings if isinstance(data, dict)]
    if not parsed:
        return Check(
            "hooks-guard", WARN, "no parseable settings file to read hooks from", 7
        )

    events: dict = {}
    for path, data in parsed:
        block = data.get("hooks")
        if block is None:
            continue
        if not isinstance(block, dict):
            return Check(
                "hooks-guard",
                FAIL,
                f"{rel(root, path)} hooks is not an object of event keys",
                7,
            )
        for event, entries in block.items():
            if not isinstance(entries, list):
                return Check(
                    "hooks-guard",
                    FAIL,
                    f"{rel(root, path)} hooks.{event} is not a list",
                    7,
                )
            for entry in entries:
                defect = _hook_entry_defect(entry)
                if defect:
                    return Check(
                        "hooks-guard",
                        FAIL,
                        f"{rel(root, path)} hooks.{event}: {defect}",
                        7,
                    )
            events.setdefault(event, 0)
            events[event] += len(entries)

    if not events:
        return Check("hooks-guard", WARN, "no hooks block in settings", 7)
    if not events.get("PreToolUse"):
        configured = ", ".join(sorted(events))
        return Check(
            "hooks-guard",
            WARN,
            f"hooks configured for {configured} but no PreToolUse guard",
            7,
        )
    return Check(
        "hooks-guard",
        PASS,
        f"{events['PreToolUse']} well-formed PreToolUse entry(s) across "
        f"{len(events)} hook event(s)",
        7,
    )


# =============================================================================
# Check E — the permission floor (pattern 4)
# =============================================================================
BLANKET_ALLOW = {"*", "Bash(*)"}


def check_permissions_floor(root: Path, settings) -> Check:
    parsed = [(p, data) for p, data, err in settings if isinstance(data, dict)]
    blocks = []
    for path, data in parsed:
        perms = data.get("permissions")
        if isinstance(perms, dict):
            blocks.append((path, perms))

    for path, perms in blocks:
        allow = perms.get("allow")
        if isinstance(allow, list):
            blanket = [
                r for r in allow if isinstance(r, str) and r.strip() in BLANKET_ALLOW
            ]
            if blanket:
                return Check(
                    "permissions-floor",
                    FAIL,
                    f"{rel(root, path)} allows {blanket[0]!r}, which is no floor at all",
                    4,
                )

    if not parsed:
        return Check(
            "permissions-floor",
            WARN,
            "no parseable settings file to read permissions from",
            4,
        )
    if not blocks:
        return Check("permissions-floor", WARN, "no permissions block in settings", 4)

    total_deny = 0
    for _, perms in blocks:
        deny = perms.get("deny")
        if isinstance(deny, list):
            total_deny += len([r for r in deny if isinstance(r, str) and r.strip()])
    if total_deny:
        return Check(
            "permissions-floor",
            PASS,
            f"{total_deny} deny rule(s) across {len(blocks)} settings file(s)",
            4,
        )
    return Check(
        "permissions-floor",
        WARN,
        "permissions block present but the deny list is empty",
        4,
    )


# =============================================================================
# Check F — credential shapes in files (pattern 6)
# =============================================================================
def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTS:
        return False
    try:
        with path.open("rb") as fh:
            return b"\x00" not in fh.read(4096)
    except OSError:
        return False


def check_secrets(root: Path) -> Check:
    hits = []
    scanned = 0
    oversize = 0
    for path in walk_files(root):
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                oversize += 1
                continue
        except OSError:
            continue
        if not is_probably_text(path):
            continue
        scanned += 1
        text = read_text(path)
        if not text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, rgx in CRED_PATTERNS:
                match = rgx.search(line)
                if match:
                    hits.append((rel(root, path), lineno, label, mask(match.group(0))))
                    break
        if len(hits) > 50:
            break

    if not hits:
        if not scanned:
            return Check("secrets-in-files", NA, "no text files to scan", 6)
        detail = f"no credential-shaped strings in {scanned} scanned text file(s)"
        if oversize:
            detail += f", {oversize} file(s) over {MAX_SCAN_BYTES // 1024} KB not read"
        return Check("secrets-in-files", PASS, detail, 6)
    shown = ", ".join(f"{p}:{n} {label} {snip}" for p, n, label, snip in hits[:3])
    extra = f" (+{len(hits) - 3} more)" if len(hits) > 3 else ""
    return Check("secrets-in-files", FAIL, f"{len(hits)} hit(s): {shown}{extra}", 6)


# =============================================================================
# Check G — .env coverage (pattern 6)
# =============================================================================
def gitignore_covers(root: Path, target: Path) -> bool:
    """Approximate `git check-ignore` using only the .gitignore files on the path.

    Handles the forms that matter here: bare globs matched against any path
    component, anchored patterns, directory suffixes, and `!` negation with
    last-match-wins. It does not read .git/info/exclude or a global ignore file,
    so a false FAIL is possible when the rule lives outside the tree.
    """
    try:
        parts = target.relative_to(root).parts
    except ValueError:
        return False

    covered = False
    for depth in range(len(parts)):
        base = root.joinpath(*parts[:depth]) if depth else root
        ignore_file = base / ".gitignore"
        if not ignore_file.is_file():
            continue
        rel_path = "/".join(parts[depth:])
        for raw in read_text(ignore_file).splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            negated = line.startswith("!")
            if negated:
                line = line[1:]
            line = line.rstrip("/")
            if not line:
                continue
            anchored = line.startswith("/") or "/" in line.rstrip("/")
            pattern = line.lstrip("/")
            if anchored:
                matched = fnmatch.fnmatchcase(rel_path, pattern) or rel_path.startswith(
                    pattern + "/"
                )
            else:
                matched = any(
                    fnmatch.fnmatchcase(part, pattern) for part in rel_path.split("/")
                )
            if matched:
                covered = not negated
    return covered


def check_env_ignored(root: Path) -> Check:
    env_files = [
        p for p in walk_files(root) if p.name == ".env" or p.name.startswith(".env.")
    ]
    if not env_files:
        return Check("env-ignored", NA, "no .env files in the tree", 6)
    uncovered = [p for p in env_files if not gitignore_covers(root, p)]
    if uncovered:
        names = ", ".join(rel(root, p) for p in uncovered[:3])
        extra = f" (+{len(uncovered) - 3} more)" if len(uncovered) > 3 else ""
        return Check(
            "env-ignored",
            FAIL,
            f"{len(uncovered)} of {len(env_files)} .env file(s) not gitignored: "
            f"{names}{extra}",
            6,
        )
    return Check(
        "env-ignored",
        PASS,
        f"all {len(env_files)} .env file(s) covered by a .gitignore rule",
        6,
    )


# =============================================================================
# Checks H + I — skill and agent frontmatter (patterns 10 and 1)
# =============================================================================
MIN_DESCRIPTION = 40


def check_skills_frontmatter(root: Path) -> Check:
    skills_dir = root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return Check("skills-frontmatter", NA, "no .claude/skills directory", 10)
    files = sorted(p for p in skills_dir.glob("*/SKILL.md") if p.is_file())
    if not files:
        return Check(
            "skills-frontmatter", NA, ".claude/skills holds no SKILL.md files", 10
        )

    weak = []
    for path in files:
        fields = parse_frontmatter(read_text(path))
        if fields is None:
            weak.append((rel(root, path), "no frontmatter block"))
            continue
        if not fields.get("name"):
            weak.append((rel(root, path), "no name"))
            continue
        description = fields.get("description", "")
        if not description:
            weak.append((rel(root, path), "no description"))
        elif len(description) < MIN_DESCRIPTION:
            weak.append((rel(root, path), f"description {len(description)} chars"))

    if not weak:
        return Check(
            "skills-frontmatter",
            PASS,
            f"all {len(files)} skill(s) carry name + description "
            f">= {MIN_DESCRIPTION} chars",
            10,
        )
    shown = ", ".join(f"{p} ({why})" for p, why in weak[:3])
    extra = f" (+{len(weak) - 3} more)" if len(weak) > 3 else ""
    return Check(
        "skills-frontmatter",
        WARN,
        f"{len(files) - len(weak)}/{len(files)} skill(s) sound; weak: {shown}{extra}",
        10,
    )


def check_agents_frontmatter(root: Path) -> Check:
    agents_dir = root / ".claude" / "agents"
    if not agents_dir.is_dir():
        return Check("agents-frontmatter", NA, "no .claude/agents directory", 1)
    files = sorted(p for p in agents_dir.glob("*.md") if p.is_file())
    if not files:
        return Check("agents-frontmatter", NA, ".claude/agents holds no .md files", 1)

    weak = []
    for path in files:
        fields = parse_frontmatter(read_text(path))
        if fields is None:
            weak.append((rel(root, path), "no frontmatter block"))
        elif not fields.get("name"):
            weak.append((rel(root, path), "no name"))
        elif not fields.get("description"):
            weak.append((rel(root, path), "no description"))

    if not weak:
        return Check(
            "agents-frontmatter",
            PASS,
            f"all {len(files)} agent binding(s) carry name + description",
            1,
        )
    shown = ", ".join(f"{p} ({why})" for p, why in weak[:3])
    extra = f" (+{len(weak) - 3} more)" if len(weak) > 3 else ""
    return Check(
        "agents-frontmatter",
        WARN,
        f"{len(files) - len(weak)}/{len(files)} binding(s) sound; weak: {shown}{extra}",
        1,
    )


# =============================================================================
# Check J — MCP config (pattern 6)
# =============================================================================
def _env_values(node):
    """Yield every string value that sits inside an `env` mapping."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "env" and isinstance(value, dict):
                for env_key, env_value in value.items():
                    if isinstance(env_value, str):
                        yield env_key, env_value
            else:
                for found in _env_values(value):
                    yield found
    elif isinstance(node, list):
        for item in node:
            for found in _env_values(item):
                yield found


def check_mcp_config(root: Path) -> Check:
    path = root / ".mcp.json"
    if not path.is_file():
        return Check("mcp-config", NA, "no .mcp.json", 6)
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        return Check("mcp-config", FAIL, f".mcp.json line {exc.lineno}: {exc.msg}", 6)
    for env_key, env_value in _env_values(data):
        for label, rgx in CRED_PATTERNS:
            match = rgx.search(env_value)
            if match:
                return Check(
                    "mcp-config",
                    FAIL,
                    f".mcp.json env.{env_key} holds a {label} ({mask(match.group(0))})",
                    6,
                )
    servers = data.get("mcpServers")
    count = len(servers) if isinstance(servers, dict) else 0
    return Check(
        "mcp-config",
        PASS,
        f".mcp.json parses, {count} server(s), no credential values inline",
        6,
    )


# =============================================================================
# Check K — duplicated blocks across instruction files (pattern 17)
# =============================================================================
MIN_PARAGRAPH = 240


def instruction_files(root: Path):
    """Every CLAUDE.md and AGENTS.md in the tree, plus .claude/rules/*.md, deduplicated."""
    seen = {}
    for path in walk_files(root):
        if path.name in ("CLAUDE.md", "AGENTS.md"):
            seen[path.resolve()] = path
    rules_dir = root / ".claude" / "rules"
    if rules_dir.is_dir():
        for path in rules_dir.glob("*.md"):
            if path.is_file():
                seen[path.resolve()] = path
    return [seen[k] for k in sorted(seen)]


def check_duplicate_blocks(root: Path) -> Check:
    files = instruction_files(root)
    if not files:
        return Check("duplicate-blocks", NA, "no instruction files to compare", 17)
    if len(files) == 1:
        return Check(
            "duplicate-blocks",
            NA,
            f"{rel(root, files[0])} is the only instruction file, so nothing to compare",
            17,
        )

    index: dict = {}
    for path in files:
        name = rel(root, path)
        for block in re.split(r"\n\s*\n", read_text(path)):
            normalized = " ".join(block.split())
            if len(normalized) >= MIN_PARAGRAPH:
                index.setdefault(normalized, set()).add(name)

    dupes = {text: names for text, names in index.items() if len(names) >= 2}
    if not dupes:
        return Check(
            "duplicate-blocks",
            PASS,
            f"no paragraph >= {MIN_PARAGRAPH} chars shared across "
            f"{len(files)} instruction file(s)",
            17,
        )
    pairs = sorted({" + ".join(sorted(names)) for names in dupes.values()})
    shown = "; ".join(pairs[:3])
    extra = f" (+{len(pairs) - 3} more)" if len(pairs) > 3 else ""
    return Check(
        "duplicate-blocks",
        WARN,
        f"{len(dupes)} paragraph(s) duplicated across {shown}{extra}",
        17,
    )


# =============================================================================
# Check L — memory index size (pattern 5)
# =============================================================================
MEMORY_LINE_CEILING = 200


def check_memory_index(root: Path) -> Check:
    path = root / "MEMORY.md"
    if not path.is_file():
        return Check("memory-index", NA, "no MEMORY.md at the workspace root", 5)
    lines = len(read_text(path).splitlines())
    if lines > MEMORY_LINE_CEILING:
        return Check(
            "memory-index",
            WARN,
            f"MEMORY.md is {lines} lines, over the {MEMORY_LINE_CEILING}-line ceiling",
            5,
        )
    return Check(
        "memory-index",
        PASS,
        f"MEMORY.md is {lines} lines, within the {MEMORY_LINE_CEILING}-line ceiling",
        5,
    )


# =============================================================================
# Runner, scoring, report
# =============================================================================
def run_checks(root: Path):
    settings = load_settings(root)
    return [
        check_instruction_file(root),
        check_context_budget(root),
        check_settings_parse(root, settings),
        check_hooks_guard(root, settings),
        check_permissions_floor(root, settings),
        check_secrets(root),
        check_env_ignored(root),
        check_skills_frontmatter(root),
        check_agents_frontmatter(root),
        check_mcp_config(root),
        check_duplicate_blocks(root),
        check_memory_index(root),
    ]


def score_checks(checks):
    scored = [c for c in checks if c.status != NA]
    if not scored:
        return 0.0, "exposed", 0
    earned = sum(SCORE_WEIGHTS[c.status] for c in scored)
    value = round(10.0 * earned / len(scored), 1)
    if value >= 8:
        band = "disciplined"
    elif value >= 5:
        band = "maturing"
    else:
        band = "exposed"
    return value, band, len(scored)


CTA = (
    "Compare notes: the patterns behind each check are at\n"
    f"{PATTERNS_URL}\n"
    "Want a second read on your workspace? Ask in Review my workspace:\n"
    f"{REVIEW_URL}\n"
    "Found something this missed, or disagree with a check? Open an issue:\n"
    f"{ISSUES_URL}"
)


def render_report(root: Path, checks) -> str:
    value, band, scored = score_checks(checks)
    out = [f"workspace check — {root}", ""]
    for check in checks:
        out.append(
            f"[{check.status}] {check.id} — {check.evidence} (pattern {check.pattern})"
        )
    skipped = len(checks) - scored
    tail = f", {skipped} not applicable" if skipped else ""
    out += ["", f"Score {value}/10 — {band} ({scored} scored{tail})", "", CTA]
    return "\n".join(out)


# =============================================================================
# Self-test — fixture trees in a temp dir, asserted status by status
# =============================================================================
def _build_passing_workspace(root: Path) -> None:
    (root / ".claude" / "rules").mkdir(parents=True)
    (root / ".claude" / "skills" / "orient").mkdir(parents=True)
    (root / ".claude" / "agents").mkdir(parents=True)

    (root / "CLAUDE.md").write_text(
        "# Workspace\n\nBranch before you commit. One focused change per PR.\n",
        encoding="utf-8",
    )
    (root / ".claude" / "rules" / "style.md").write_text(
        "# Style\n\nTerse and structural. No performative politeness.\n",
        encoding="utf-8",
    )
    (root / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "permissions": {
                    "deny": ["Read(./.env)"],
                    "allow": ["Bash(git status)"],
                },
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Write|Edit",
                            "hooks": [
                                {"type": "command", "command": "python guard.py"}
                            ],
                        }
                    ]
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / ".claude" / "skills" / "orient" / "SKILL.md").write_text(
        "---\nname: orient\ndescription: Brief the operator on active state, "
        "in-flight work, and open questions at session start.\n---\n\nProcedure.\n",
        encoding="utf-8",
    )
    (root / ".claude" / "agents" / "researcher.md").write_text(
        "---\nname: researcher\ndescription: Outside-evidence research with "
        "graded sources.\n---\n\nRole binding.\n",
        encoding="utf-8",
    )
    (root / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"docs": {"command": "npx", "env": {}}}}),
        encoding="utf-8",
    )
    (root / "MEMORY.md").write_text("# Memory index\n\n- pointer\n", encoding="utf-8")
    (root / ".gitignore").write_text(".env*\n__pycache__/\n", encoding="utf-8")
    (root / ".env").write_text("PORT=8080\n", encoding="utf-8")


_SHARED_PARAGRAPH = (
    "The same rule written in two places is correct on the day it is "
    "written and wrong the first time one copy is edited, with nothing "
    "breaking to signal it. One canonical location, and every other file "
    "points at it rather than restating it in its own words.\n"
)


def _build_failing_workspace(root: Path) -> None:
    (root / ".claude" / "rules").mkdir(parents=True)

    (root / "CLAUDE.md").write_text(
        "# Workspace\n\n" + _SHARED_PARAGRAPH, encoding="utf-8"
    )
    (root / ".claude" / "rules" / "canonical.md").write_text(
        "# Canonical\n\n" + _SHARED_PARAGRAPH, encoding="utf-8"
    )
    # Push the always-loaded surface past the 40 KB ceiling.
    (root / ".claude" / "rules" / "bloat.md").write_text(
        "Accreted guidance that nobody has pruned.\n" * 1200, encoding="utf-8"
    )
    (root / ".claude" / "settings.json").write_text(
        '{"permissions": {"deny": ["Read(./.env)"],}\n', encoding="utf-8"
    )
    # Obvious fakes, assembled at runtime so this source file carries no
    # contiguous credential-shaped string for any scanner to trip on.
    (root / "notes.md").write_text(
        "token " + "ghp_" + "x" * 36 + "\nkey " + "sk-ant-" + "x" * 24 + "\n",
        encoding="utf-8",
    )
    (root / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (root / ".env").write_text("PORT=8080\n", encoding="utf-8")


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _prose(tag: str, size: int) -> str:
    """One paragraph of about `size` bytes that no other tag's paragraph matches."""
    sentence = f"{tag} guidance, written once and kept short enough to read. "
    return sentence * (size // len(sentence) + 1) + "\n"


def _build_lone(name: str):
    def build(root: Path) -> None:
        _write(
            root,
            name,
            "# Workspace\n\nBranch before you commit. One focused change per PR.\n",
        )

    return build


def _build_agents_nested(root: Path) -> None:
    _write(root, "AGENTS.md", "# Workspace\n\n" + _SHARED_PARAGRAPH)
    _write(root, "packages/api/AGENTS.md", "# API\n\n" + _SHARED_PARAGRAPH)


def _build_both(root: Path) -> None:
    for name, tag in (("CLAUDE.md", "alpha"), ("AGENTS.md", "beta")):
        _write(
            root,
            name,
            f"# {tag}\n\n{_prose(tag, 10 * 1024)}\n{_SHARED_PARAGRAPH}",
        )


def _build_import(root: Path) -> None:
    lines = ["# Claude", "", _prose("alpha", 8 * 1024), "@AGENTS.md", ""]
    _write(root, "CLAUDE.md", "\n".join(lines))
    _write(root, "AGENTS.md", f"# Agents\n\n{_prose('beta', 8 * 1024)}")


def _build_agents_rules(root: Path) -> None:
    _write(root, "AGENTS.md", f"# Agents\n\n{_prose('alpha', 8 * 1024)}")
    _write(root, ".claude/rules/style.md", f"# Style\n\n{_prose('beta', 8 * 1024)}")


def _build_symlink(root: Path) -> None:
    _write(root, "CLAUDE.md", f"# Workspace\n\n{_prose('alpha', 10 * 1024)}")
    os.symlink("CLAUDE.md", root / "AGENTS.md")


def _build_empty(root: Path) -> None:
    pass


PASSING_EXPECTED = {
    "instruction-file-present": PASS,
    "context-budget": PASS,
    "settings-parse": PASS,
    "hooks-guard": PASS,
    "permissions-floor": PASS,
    "secrets-in-files": PASS,
    "env-ignored": PASS,
    "skills-frontmatter": PASS,
    "agents-frontmatter": PASS,
    "mcp-config": PASS,
    "duplicate-blocks": PASS,
    "memory-index": PASS,
}

FAILING_EXPECTED = {
    "instruction-file-present": PASS,
    "context-budget": FAIL,
    "settings-parse": FAIL,
    "hooks-guard": WARN,
    "permissions-floor": WARN,
    "secrets-in-files": FAIL,
    "env-ignored": FAIL,
    "skills-frontmatter": NA,
    "agents-frontmatter": NA,
    "mcp-config": NA,
    "duplicate-blocks": WARN,
    "memory-index": NA,
}


def _lone_expected(override=None) -> dict:
    """Expected statuses for a tree that holds instruction files and nothing else."""
    expected = {
        "instruction-file-present": PASS,
        "context-budget": PASS,
        "settings-parse": WARN,
        "hooks-guard": WARN,
        "permissions-floor": WARN,
        "secrets-in-files": PASS,
        "env-ignored": NA,
        "skills-frontmatter": NA,
        "agents-frontmatter": NA,
        "mcp-config": NA,
        "duplicate-blocks": NA,
        "memory-index": NA,
    }
    expected.update(override or {})
    return expected


EMPTY_EXPECTED = {check_id: NA for check_id in PASSING_EXPECTED}
EMPTY_EXPECTED.update(
    {
        "instruction-file-present": FAIL,
        "settings-parse": WARN,
        "hooks-guard": WARN,
        "permissions-floor": WARN,
    }
)

# (label, builder, expected statuses, expected band, evidence substrings, optional)
SELF_TEST_FIXTURES = [
    ("passing", _build_passing_workspace, PASSING_EXPECTED, "disciplined", {}, False),
    ("failing", _build_failing_workspace, FAILING_EXPECTED, "exposed", {}, False),
    (
        "agents-only",
        _build_lone("AGENTS.md"),
        _lone_expected(),
        "maturing",
        {
            "instruction-file-present": "AGENTS.md",
            "duplicate-blocks": "AGENTS.md",
            "settings-parse": "Claude Code settings are the only config",
        },
        False,
    ),
    (
        "claude-only",
        _build_lone("CLAUDE.md"),
        _lone_expected(),
        "maturing",
        {},
        False,
    ),
    (
        "agents-nested",
        _build_agents_nested,
        _lone_expected({"duplicate-blocks": WARN}),
        "maturing",
        {},
        False,
    ),
    (
        "both",
        _build_both,
        _lone_expected({"duplicate-blocks": WARN}),
        "maturing",
        {"context-budget": "AGENTS.md reader"},
        False,
    ),
    (
        "import",
        _build_import,
        _lone_expected({"context-budget": WARN, "duplicate-blocks": PASS}),
        "maturing",
        {},
        False,
    ),
    (
        "agents-rules",
        _build_agents_rules,
        _lone_expected({"context-budget": WARN, "duplicate-blocks": PASS}),
        "maturing",
        {"context-budget": "AGENTS.md reader"},
        False,
    ),
    (
        "symlink",
        _build_symlink,
        _lone_expected(),
        "maturing",
        {"instruction-file-present": "one file"},
        True,
    ),
    ("empty", _build_empty, EMPTY_EXPECTED, "exposed", {}, False),
]


def run_self_test() -> int:
    import tempfile

    failures = []
    ran = 0
    skipped = []
    results = {}
    with tempfile.TemporaryDirectory() as td:
        for label, build, expected, want_band, evidence, optional in SELF_TEST_FIXTURES:
            root = Path(td) / label
            root.mkdir()
            try:
                build(root)
            except (OSError, NotImplementedError):
                if not optional:
                    raise
                skipped.append(label)
                continue
            ran += 1

            checks = run_checks(root)
            got = {c.id: c.status for c in checks}
            value, band, _ = score_checks(checks)
            results[label] = (got, value)
            if set(got) != set(expected):
                failures.append(f"{label}: check set was {sorted(got)}")
                continue
            for check_id, want in expected.items():
                if got[check_id] != want:
                    detail = next(c.evidence for c in checks if c.id == check_id)
                    failures.append(
                        f"{label}/{check_id}: expected {want}, got {got[check_id]}"
                        f" ({detail})"
                    )
            for check_id, needle in evidence.items():
                detail = next(c.evidence for c in checks if c.id == check_id)
                if needle not in detail:
                    failures.append(
                        f"{label}/{check_id}: evidence lacks {needle!r} ({detail})"
                    )
            if band != want_band:
                failures.append(
                    f"{label}: expected band {want_band}, got {band} ({value}/10)"
                )
            for check in checks:
                if check.pattern not in PATTERN_SLUGS:
                    failures.append(f"{label}/{check.id}: unknown pattern anchor")

        # Renaming the instruction file must not change the score.
        if results["agents-only"] != results["claude-only"]:
            failures.append(
                f"rename: agents-only {results['agents-only']} differs from "
                f"claude-only {results['claude-only']}"
            )

        # An empty tree has nothing to credit.
        passes = [k for k, v in results["empty"][0].items() if v == PASS]
        if passes:
            failures.append(f"empty: reported PASS for {passes}")

        # A masked finding must never reprint the whole fake token.
        secret_check = next(
            c for c in run_checks(Path(td) / "failing") if c.id == "secrets-in-files"
        )
        if "x" * 36 in secret_check.evidence:
            failures.append("masking: evidence line reprinted a full token")

        # A backticked mention is not an import, a bare one is.
        ticks = Path(td) / "ticks"
        ticks.mkdir()
        _write(ticks, "CLAUDE.md", "Do not write `@AGENTS.md` here.\n")
        _write(ticks, "AGENTS.md", "# Agents\n")
        names = [rel(ticks, p) for p in claude_surface(ticks)]
        if names != ["CLAUDE.md"]:
            failures.append(f"import: backticked mention counted, surface was {names}")
        imp = Path(td) / "import"
        names = [rel(imp, p) for p in claude_surface(imp)]
        if names != ["CLAUDE.md", "AGENTS.md"]:
            failures.append(
                f"import: bare @AGENTS.md not followed, surface was {names}"
            )

    if failures:
        print(f"self-test: FAIL ({len(failures)})")
        for line in failures:
            print(f"  - {line}")
        return 1
    tail = ", symlink fixture skipped" if "symlink" in skipped else ""
    print(
        f"self-test: PASS (12 checks over {ran} fixture workspaces, CLAUDE.md and "
        f"AGENTS.md layouts, bands disciplined + maturing + exposed, secrets "
        f"masked{tail})"
    )
    return 0


# =============================================================================
# CLI
# =============================================================================
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="workspace_check.py",
        description="Score an agent workspace against the checkable patterns.",
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="workspace directory (default: .)"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit JSON to stdout and nothing else"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run fixture-based assertions and exit 0/1",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    root = root.resolve()

    checks = run_checks(root)
    if args.json:
        value, band, _ = score_checks(checks)
        payload = {
            "score": value,
            "band": band,
            "checks": [c.as_dict() for c in checks],
        }
        print(json.dumps(payload, indent=2))
        return 0
    print(render_report(root, checks))
    return 0


if __name__ == "__main__":
    # UTF-8-safe stdout on a legacy-codepage console, so the report's dashes
    # never turn a clean run into a UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    raise SystemExit(main())
