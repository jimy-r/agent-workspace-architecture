"""
PreToolUse shell hook -- close the shell gap in Edit/Write file protection
and block dangerous git operations.

Background: the existing PreToolUse hook at `~/.claude/settings.json`
gates `Edit` and `Write` tool calls against a list of protected path
substrings. But shell-level filesystem operations (`mv`, `cp`, `sed -i`,
`rm`, output redirection `>` / `>>`, PowerShell's `Remove-Item` /
`Set-Content` / `Out-File`) bypass that hook because they go through the
`Bash` or `PowerShell` tool, not `Edit`/`Write`. Discovered during the
heartbeat-as-PR-agent cutover on 2026-04-22 (see `tasks/lessons.md`).

Wire this hook as a PreToolUse entry on the matcher `Bash|PowerShell`.
Both tools send the command as `tool_input.command`, so one script serves
both, and a tool that no matcher names reaches no hook at all. It refuses
three categories of command:

    1. File writes to protected paths -- a write whose target contains a
       protected substring (case-insensitive, normalised to forward
       slashes). The list is PROTECTED_SUBSTRINGS below, and a target
       inside a tree named in ALLOWLIST_SUBSTRINGS is skipped.
       Two layers find the targets:
         - text patterns: `>` / `>>` / `2>`, `rm`, `mv <dest>`,
           `cp <dest>`, `sed -i`, `tee`, `touch`, `chmod`, `chown`,
           `truncate`;
         - parsed commands (shlex): every operand of `rm` and `mv` (a
           protected file moved away is gone from its path, so the `mv`
           source counts as a write), `git rm` / `git mv`, and the
           PowerShell write cmdlets with their aliases: Remove-Item (ri,
           del, erase, rd, rmdir), Move-Item (mi, move), Rename-Item
           (rni, ren), Copy-Item (cpi, copy; destination only),
           Set-Content (sc), Add-Content (ac), Clear-Content (clc),
           Out-File, New-Item (ni), Tee-Object.

    2. Dangerous git operations -- any force push (`-f`, `--force*`,
       `+refspec`), a push whose destination is `main` or `master`
       (`origin main`, `HEAD:main`, `refs/heads/main`, `feature:main`,
       `:main`, `--all`, `--mirror`, or a bare `git push` / `git push
       origin` while the current branch is main or master), and
       `git reset --hard` against main/master. `git -C <dir>` is followed.
       Two layers find a push, as they do a write:
         - parsed commands (shlex): the push a statement starts with,
           read word by word, which is where every form above is seen;
         - text patterns: `git push` followed in the same statement
           (before any `;`, `&`, `|` or line break) by a force flag
           (`-f`, `--force`, `--force-with-lease`) or by `main` or
           `master` as a word of its own, `main:main` and
           `main:master` included.

    3. Exec-hijacking env-var assignments -- an inline `VAR=value cmd`
       prefix for a denylist of env vars (`GIT_SSH_COMMAND`,
       `NODE_OPTIONS`, `LD_PRELOAD`, `PYTHONSTARTUP`, ...) that make an
       otherwise-allowed command execute attacker-chosen code.

Where a command sits in a statement does not change the answer. A shell
keyword in front of it is skipped (`if ...; then rm x; fi`, `do rm x`,
`! rm x`). Each statement inside braces is checked on its own (`{ rm x; }`,
`if ($ok) { Remove-Item x }`). Comment text is kept as part of the
command, because a comment line must not hide the command below it. Each
statement is read again without its trailing comment, because a note must
not soften the command in front of it. The whole command is read twice
more. Once with each line cut at a `#` that opens a word outside quotes,
because a quote mark inside a comment would otherwise count as a quote.
And once as only the text in front of the first such `#`, because a line
further down that leaves a quote open must not change how that text
reads. A quoted script is read with its comments cut out as well. A line
continued with a trailing backslash (Bash) or backtick (PowerShell) is
read again with the lines joined. A quoted target is read to its closing
quote, so
`> "my secrets/out.txt"` is seen whole.

That holds for the first two categories, and it has limits. The guard
reads the command each statement starts with and the paths written out
beside it, so a write or a push that takes a longer route gets past.
These classes are known to pass:

    - a redirect, `tee`, `touch` or `chmod` whose path is quoted only in
      part (`> "$HOME"/.env`);
    - a path built by a `$(...)` that holds a space, or by a
      parenthesised PowerShell expression (`rm $(git rev-parse
      --show-toplevel)/.env`, `Remove-Item (Join-Path $PWD '.env')`);
    - a file name that arrives through a pipe (`echo .env | xargs rm`);
    - a command behind a prefix the parser has no rule for (`timeout 5`,
      `eval`, `sudo -u root`, `coproc`);
    - a command handed unquoted to another shell (`cmd /c`, `wsl`,
      `powershell -Command`) or run inside backticks;
    - an operand past a comma that continues a PowerShell list onto the
      next line;
    - a writer with no rule here at all: the redirects `&>` and `>|`,
      `dd of=`, `install`, `ln -sf`, `find -delete`, `git checkout --`,
      `git clean`, cmdlets outside the list above (`Clear-Item`,
      `Export-Csv`), a `sed -i` whose script holds a space, and a
      `truncate`, `chmod`, `chown` or `tee` with one more word in front
      of the path than its pattern expects (`truncate -s 0 .env`).

Quotes and comments set limits of their own. These pass as well:

    - the first command of a quoted argument, or a command behind a
      quoted value with a space in it, when the lexer finds a quote
      left open anywhere in the text. It gives up on the whole text
      and a plain split on whitespace takes over, which does not
      follow quotes. A later line that leaves a quote open does it,
      while Bash still runs every line above that one:
      `bash -c "git push origin main"` passes with `echo it's done`
      on the next line, because the closing quote stands straight
      after `main` and the push text pattern wants a space, a
      separator or the end of the text there. A quote mark that the shell
      reads as plain text does it too, and then the shell runs every
      line. The lexer pairs quote marks as they come and knows no
      escape character, no here-document and no nesting. So it counts
      an apostrophe in a here-document or a here-string, a quote
      behind a backslash (Bash) or a backtick (PowerShell), and a
      quote inside a `$(...)` that stands inside quotes. Two such
      marks can also pair with a command's own quotes and pull it
      apart.
    - the same command with comments in the text, in all but two
      cases. The readings that drop comments bring it back when the
      mark that leaves the quote open stands inside a comment, and
      when the command stands in front of the first comment in the
      text and that mark behind it. A comment line above the command
      with the mark on a line below is neither, and passes. A `#`
      inside a word opens no comment and brings nothing back
      (`bash -c "git push origin main" x#y`, then a line that leaves
      a quote open).
    - a quoted command that follows a `${#name}` on its line, with a
      quote mark in a note after it. The cut takes a `#` straight after
      a brace for a comment, which is right for PowerShell and wrong
      for Bash, so the two readings that drop comments stop there.
    - a command in a quoted script that has a quote mark in the
      script's own comment lines. The line breaks of the script are
      separators by the time it is read, so a comment in it is cut to
      the end of the script. A script whose three lines are `# don't`,
      `rm 'a b' .env` and `# it's` passes.
    - in PowerShell, a command behind a block comment on the same line
      (`<# note #> Remove-Item .env`), and a command behind a lone
      carriage return, which the guard reads as a space where
      PowerShell ends the line.

The `rm`, `mv` and push text patterns read the text as sent, whatever
quotes and prefixes stand around it. In each class that hides a command
from the parser they still see the first operand of an `rm`, the
destination of an `mv`, a push with a force flag written out (`timeout
60 git push --force origin feature`, `bash -c "git push -f origin
feature"` above a line that leaves a quote open) and a push with `main`
or `master` as a word of its own (`eval git push origin main`). They do
not see a PowerShell cmdlet, `del`, or the source of an `mv`. Of the
pushes the parser refuses, they miss the ones that name the branch
another way: `main` with a quote mark straight after it, `HEAD:main`,
`feature:main`, `refs/heads/main`, a `+refspec`, `--all`, `--mirror`,
and a push with no refspec from main. Behind a prefix or a broken quote
those still pass. So does a push whose own words hold a `;`, `&` or `|`
in front of the branch or the flag (`timeout 5 git push origin feature
2>&1 --force`), because the patterns stop there.

The push patterns are not the earlier sample's patterns word for word.
Those read from `git push` to the end of the text. These stop at the
end of the statement, take `main:` only when main or master is the
destination too, and skip a `git` straight after a carriage return. The
comment above DANGEROUS_GIT gives the reason for each.

The third category is a text pattern and reads less. It sees an assignment
at the start of the command, on a new line, or straight after `;`, `&` or
`|`. It misses one that sits behind a keyword (`then`), a wrapper (`env`,
`sudo`), a parenthesis or a brace. It reads the POSIX form only, so
PowerShell's `$env:NAME = ...` is outside it.

This is *defence-in-depth*, not paranoia. The bar is "catch casual
mistakes," not "stop a determined adversary." Processes that open files
internally (`open(path, 'w')`) are out of scope -- the hook can't
inspect process behaviour.

Known sharp edge: quoted arguments are checked as commands too, so
`bash -c "rm .env"` is caught. The cost is that a commit message which
itself reads as a blocked command (`-m "git push origin main"`) is
refused. Reword the message rather than bypassing the hook. Text inside
braces is read the same way, so a hashtable or JSON body whose key is
named like a delete or a move and whose value is a protected path
(`@{ del = '.env' }`) is refused as well. So is comment text: a note
after a delete, a move or a push that names a protected path, `main` or
a force flag (`rm old.log  # not .env`), and a comment that holds a
blocked command of its own after a `;`, a `|` or a brace
(`# cleanup; rm .env`).
The `rm` and `mv` text patterns go one step further. They refuse any
line that puts `rm` or `mv` in front of a protected path, even when it
is only a comment (`# rm .env`), another tool's subcommand
(`docker rm credentials-db`) or an index-only `git rm .env --cached`
with the flag last.

The push text patterns stop at the end of the statement, so a feature
push followed by a command that names main is allowed (`git push origin
feature && git checkout main`, or the same push with `gh pr create
--base main` on the next line). What they still refuse is a line that
only prints or comments the words (`echo git push origin main`,
`# git push origin main`) and a commit message that holds a force push
or a push to main as plain words with no separator between them.

Two more edges come from the way quotes are read. A message that only
quotes a blocked command is refused, with or without a `#` tail after
the quoted words (`-m "say 'git push origin main' is refused"`). And
the plain split costs a harmless command now and then. A quoted value
with a space in it falls into two words there, so the apostrophe in
the note of `Set-Content notes.txt -Value "my secrets/out.txt"  # don't`
gets that command refused, where the same command without the note is
allowed.

Claude Code hook protocol:
    - stdin: JSON payload {"tool_name": "Bash" | "PowerShell",
      "tool_input": {"command": "..."}, "cwd": "..."}
    - exit 0: allow
    - exit 2: block (stderr message is surfaced to the agent; JSON on
      stdout with {"decision": "block", "reason": "..."} is the
      structured form)

If the hook script itself errors, it fails open (exit 0, no block) so a
bug here does NOT brick the agent's ability to run shell commands.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys

# ---------------------------------------------------------------------------
# Protected-path substrings (case-insensitive, match after normalising
# backslashes to forward slashes in the target).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Allowlist — path substrings where protected filenames are intentional
# copies (sample/mirror files, not the live protected file). If a target
# contains any ALLOWLIST substring, the protection check is skipped.
# ---------------------------------------------------------------------------

ALLOWLIST_SUBSTRINGS: list[str] = [
    "agent-workspace-architecture/samples/",
    # Add further sample/mirror roots here if more public repos get cloned in.
]


PROTECTED_SUBSTRINGS: list[str] = [
    # Credentials / secrets
    ".env",
    "credentials",
    "secrets",
    ".key",
    ".pem",
    # Lock files the agent shouldn't hand-edit
    "renv.lock",
    # Heartbeat agent's own files
    "heartbeat.md",
    "heartbeat_rejections.md",  # append-only log — never edit existing blocks
    # Health data
    # Placeholders: list your own sensitive folders here. A folder prefix
    # covers everything beneath it.
    "private/health/",
    # Financial data
    "private/finance/",
    # Google OAuth
    "/.claude/google-auth/",
    "google-auth/",
]

# ---------------------------------------------------------------------------
# Write-intent text patterns. Each captures the target path in whichever of
# _PATH's three groups matched. A quoted target is read to its closing quote,
# so a path with a space in it is seen whole. An unquoted one ends at
# whitespace, pipe, semicolon, ampersand, a redirect or end of string.
# rm and mv are parsed as well (below), because a pattern sees one operand.
# Their two patterns stay because a pattern finds the verb anywhere in the
# line, and the parser reads only the command a statement starts with. A
# prefix it does not unwrap hides the rest (`eval rm x`, `timeout 5 rm x`,
# `sudo -u root mv a x`). The cost is a refusal when another tool's `rm`
# subcommand names something that holds a protected substring
# (`docker rm credentials-db`).
# ---------------------------------------------------------------------------

_PATH = r"(?:\"([^\"]+)\"|'([^']+)'|([^\s'\"|&;<>]+))"

WRITE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"(?<![2&])>\s*{_PATH}"), "shell redirection '>'"),
    (re.compile(rf">>\s*{_PATH}"), "shell append '>>'"),
    (re.compile(rf"2>\s*{_PATH}"), "stderr redirection '2>'"),
    (re.compile(rf"\brm\s+(?:-[rRfv]+\s+)*{_PATH}"), "rm"),
    (re.compile(rf"\bmv\s+\S+\s+{_PATH}"), "mv (destination)"),
    (re.compile(rf"\bcp\s+(?:-\S+\s+)*\S+\s+{_PATH}"), "cp (destination)"),
    (re.compile(rf"\bsed\s+-i\S*\s+.+?\s+{_PATH}"), "sed -i (in-place edit)"),
    (re.compile(rf"\btee\s+(?:-[aA]\s+)?{_PATH}"), "tee"),
    (re.compile(rf"\btouch\s+{_PATH}"), "touch"),
    (re.compile(rf"\bchmod\s+\S+\s+{_PATH}"), "chmod"),
    (re.compile(rf"\bchown\s+\S+\s+{_PATH}"), "chown"),
    (re.compile(rf"\btruncate\s+\S+\s+{_PATH}"), "truncate"),
]

# ---------------------------------------------------------------------------
# Dangerous git text patterns. `check_push` below reads a push word by word
# and is the more exact of the two layers, but it reads only the command a
# statement starts with. A prefix the parser does not unwrap hides the push
# from it (`timeout 60 git push --force origin feature`, `eval git push
# origin main`), and so does a quote left open somewhere else in the text.
# The three push patterns read the text as sent, as the `rm` and `mv`
# patterns do, so they stay beside the parser.
#
# They are the patterns of the earlier sample, narrowed in three ways so
# that they stop refusing harmless commands the parser reads correctly:
#   - the words between `git push` and the branch or the flag may not
#     hold a `;`, `&` or `|` and may not cross a line break, so the match
#     ends with the statement. The earlier patterns read on to the end of
#     the text and refused a feature push with `main` anywhere after it
#     (`git push origin feature && git checkout main`);
#   - `main:` and `master:` count only when the destination is main or
#     master as well, so `git push origin main:feature`, which sends main
#     to a feature branch, is allowed. In exchange `main` or `master` may
#     now end at a `;`, `&`, `|` or `)` as well as at a space;
#   - a `git` that stands straight after a carriage return is not read.
#     Bash takes a lone carriage return as part of a word, so that `git`
#     is no command there, and where it follows a comment it is comment
#     text. PowerShell does end a line at one, and the parser reads that.
# ---------------------------------------------------------------------------

_GAP = r"[^\S\r\n]+"  # spaces and tabs, never a line break
_WORDS = rf"(?:[^\s;&|]+{_GAP})*"  # words of the same statement
_PUSH = rf"(?<!\r)\bgit{_GAP}push{_GAP}{_WORDS}"
_BRANCH_END = r"(?::(?:main|master))?(?=[\s;&|)]|$)"

DANGEROUS_GIT: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(rf"{_PUSH}(?:origin{_GAP})?main{_BRANCH_END}"),
        "git push to 'main' is forbidden -- use a feature branch + PR",
    ),
    (
        re.compile(rf"{_PUSH}(?:origin{_GAP})?master{_BRANCH_END}"),
        "git push to 'master' is forbidden -- use a feature branch + PR",
    ),
    (
        re.compile(rf"{_PUSH}(?:-f\b|--force\b|--force-with-lease\b)"),
        "git force-push is forbidden",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\s+(?:origin/)?(?:main|master)\b"),
        "git reset --hard on main/master is forbidden",
    ),
]

# ---------------------------------------------------------------------------
# Dangerous environment-variable assignments prefixed to a command.
# A shell line like `GIT_SSH_COMMAND='evil' git fetch` or
# `NODE_OPTIONS='--require ./evil' npm test` runs attacker-chosen code
# through an otherwise-allowed command — the verb check never sees it.
# Block a curated denylist of exec-hijacking env vars when they appear as
# an inline assignment at a command position (start of line, or after
# ; | & && ||). Pattern credit: OpenClaw env-control hardening campaign
# (2026-06, PRs #91619/#91618/#91615/#92007). Added 2026-06-11 (audit
# finding bbb1f3e4). Provenance external → surfaced as Tier 3, not auto-applied.
# ---------------------------------------------------------------------------

# Env vars that cause a child process to load/execute caller-controlled
# code or redirect tooling. Not exhaustive of all env, just the ones that
# turn an allowed command into arbitrary code execution.
DANGEROUS_ENV_VARS: list[str] = [
    "GIT_SSH_COMMAND",
    "GIT_SSH",
    "GIT_PROXY_COMMAND",
    "GIT_EXTERNAL_DIFF",
    "GIT_PAGER",
    "CORE_EDITOR",  # git core.editor via env
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "NODE_OPTIONS",
    "PYTHONSTARTUP",
    "PYTHONPATH",
    "BASH_ENV",
    "ENV",
    "PERL5OPT",
    "RUBYOPT",
    "RUSTUP_TOOLCHAIN",
    "RUSTC_WRAPPER",
    "CARGO",
]

# Inline assignment at a command position: line start or after a shell
# separator (; | & newline), optional whitespace, VAR=...  The negative
# lookbehind on `=`/`!`/`<`/`>` avoids matching comparisons.
_ENV_ASSIGN = re.compile(
    r"(?:^|[;&|\n]|&&|\|\|)\s*([A-Za-z_][A-Za-z0-9_]*)\s*=",
)

# ---------------------------------------------------------------------------
# Parsed commands. Names are matched lower-case, without a directory or a
# trailing .exe, so `Remove-Item`, `remove-item` and `/bin/rm` all resolve.
# ---------------------------------------------------------------------------

# Every operand is a target: delete, move or rename, and the content cmdlets.
REMOVE = {"rm", "remove-item", "ri", "del", "erase", "rd", "rmdir"}
MOVE = {"mv", "move-item", "mi", "move", "rename-item", "rni", "ren"}
CONTENT = {"set-content", "sc", "add-content", "ac", "clear-content", "clc"}
CREATE = {"out-file", "new-item", "ni", "tee-object"}
ALL_OPERANDS = REMOVE | MOVE | CONTENT | CREATE
DESTINATION_ONLY = {"cp", "copy-item", "cpi", "copy"}
CONTENT_PARAMS = {"-value", "-inputobject"}  # file content, not a path
WRAPPERS = {"sudo", "env", "command", "exec", "nohup", "time", "nice", "xargs"}
# Shell keywords that sit in front of a command in the same statement
# (`then rm x`, `do rm x`, `else rm x`, `if rm x`, `! rm x`). Skipped the way
# wrappers are, so the command behind them is the one that gets checked.
KEYWORDS = {"if", "then", "else", "elif", "do", "while", "until", "!"}
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
PUSH_VALUE_OPTS = {"-o", "--push-option", "--receive-pack", "--exec"}
PROTECTED_BRANCHES = {"main", "master"}
_SEPARATOR = set(";&|()")
_REDIRECT = set("<>&")


def _normalise_target(target: str) -> str:
    return target.replace("\\", "/").lower()


def _protected_reason(verb: str, target: str, protected: list[str]) -> str:
    normalised = _normalise_target(target)
    # Allowlist check: a target inside a known sample / mirror tree is an
    # intentional copy of a protected file, not the live file itself.
    if any(allow in normalised for allow in ALLOWLIST_SUBSTRINGS):
        return ""
    for entry in protected:
        if entry in normalised:
            return (
                f"{verb} targets protected path '{target}' "
                f"(matches '{entry}'). If legitimate, use the "
                f"Edit/Write tool (hook allowlist decides) or ask "
                f"the user to stage manually. See lessons.md "
                f"entry for 2026-04-22 (Bash hook gap)."
            )
    return ""


def check_protected_writes(command: str, protected: list[str]) -> tuple[bool, str]:
    """Return (blocked, reason) if a text pattern writes to a protected path."""
    for pattern, verb in WRITE_PATTERNS:
        for match in pattern.finditer(command):
            target = next(group for group in match.groups() if group is not None)
            reason = _protected_reason(verb, target, protected)
            if reason:
                return True, reason
    return False, ""


def check_dangerous_git(command: str) -> tuple[bool, str]:
    """Return (blocked, reason) if the command matches a git text pattern."""
    for pattern, reason in DANGEROUS_GIT:
        if pattern.search(command):
            return True, reason
    return False, ""


def check_dangerous_env(command: str) -> tuple[bool, str]:
    """Return (blocked, reason) if a known exec-hijacking env var is
    assigned inline at a command position."""
    denyset = {v.upper() for v in DANGEROUS_ENV_VARS}
    for match in _ENV_ASSIGN.finditer(command):
        var = match.group(1)
        if var.upper() in denyset:
            return True, (
                f"inline assignment of '{var}' prefixes a command — this can "
                f"execute attacker-chosen code through an allowed verb "
                f"(exec-hijacking env var). If legitimate, set it via the "
                f"session environment or a wrapper script, not inline. "
                f"(audit bbb1f3e4 / OpenClaw env-control pattern)"
            )
    return False, ""


def _tokens(command: str) -> list[str]:
    """Split a command into words and separators. A newline ends a statement.

    Comments stay in. Left to itself the lexer drops everything from the
    first unquoted `#` to the end of the text, which is every later line as
    well once the newlines are separators, so a comment line above a command
    would hide the command. `_statement` reads each statement a second time
    without its trailing comment. A quote mark inside a comment counts as a
    quote here, so `_readings` also sends the command through with its
    comments cut out.

    A quote left open makes the lexer give up, and the plain split that
    takes over knows nothing about quotes. A command inside them is then
    no longer read as a command of its own, on that line or on any other.
    So `_readings` also sends the text in front of the first comment
    through alone, where a later line cannot reach it.
    """
    text = command.replace("\n", " ; ")
    lex = shlex.shlex(text, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.escape = ""  # backslash is a path separator on Windows, keep it
    lex.commenters = ""
    try:
        return list(lex)
    except ValueError:  # unbalanced quote: fall back to a plain split
        return [t.strip("'\"") for t in re.findall(r"[;&|()]+|[^\s;&|()]+", text)]


def _brace_parts(tok: str) -> list[str | None]:
    """Split a token at each unbalanced brace. None marks where one stood.

    `{` and `}` open and close a block in both shells (`{ rm x; }`,
    `if ($ok) { Remove-Item x }`), and PowerShell lets them touch the words
    inside (`{Remove-Item x}`). A balanced pair inside one token is something
    else (`${HOME}`, `file{1,2}`, find's `{}`) and is left alone.
    """
    open_at: list[int] = []
    lone: set[int] = set()
    for i, char in enumerate(tok):
        if char == "{":
            open_at.append(i)
        elif char == "}":
            if open_at:
                open_at.pop()
            else:
                lone.add(i)
    lone.update(open_at)
    if not lone:
        return [tok]
    parts: list[str | None] = []
    piece = ""
    for i, char in enumerate(tok):
        if i in lone:
            if piece:
                parts.append(piece)
            parts.append(None)
            piece = ""
        else:
            piece += char
    if piece:
        parts.append(piece)
    return parts


def _blocks(tokens: list[str]):
    """Yield each statement that follows a brace as a token list of its own.

    The caller has already yielded `tokens` whole, so this only adds
    readings and never takes one away: an operand such as `${X:-a b}/y`,
    which splits into tokens with a lone brace each, is still checked as the
    operand it is.
    """
    current: list[str] = []
    inside = False
    for tok in tokens:
        for part in _brace_parts(tok):
            if part is None:
                if inside and current:
                    yield current
                current = []
                inside = True
            else:
                current.append(part)
    if inside and current:
        yield current


def _statement(tokens: list[str]):
    """Yield one statement as written, then without its trailing comment.

    Comment text is kept so that it cannot hide what follows it. Read that
    way alone, though, a note could pass for arguments and soften the
    command in front of it (`git rm x  # --cached`). A word that starts with
    `#` opens a comment in both shells, so the statement is read a second
    time cut short at that word. The whole statement is yielded first, so
    this only adds readings: an operand that merely starts with a `#`
    (`rm "#old" x`) keeps the operands after it.
    """
    yield tokens
    yield from _blocks(tokens)
    for i, tok in enumerate(tokens):
        if tok.startswith("#"):
            if i:
                yield tokens[:i]
                yield from _blocks(tokens[:i])
            break


def _segments(command: str, depth: int = 0):
    """Yield each simple command as a token list. A quoted argument that
    holds whitespace (`bash -c "..."`, `pwsh -Command "..."`) is checked as
    a command of its own as well, and so is each statement inside braces.

    A quoted script is read as written and then with its comments cut out,
    for the reason `_readings` gives. Its newlines are separators by the
    time it gets here, so a comment in it is cut to the end of the script
    or to a carriage return. The script as written is read first, so the
    cut only adds a reading.
    """
    current: list[str] = []
    for tok in _tokens(command):
        if set(tok) <= _SEPARATOR:
            if current:
                yield from _statement(current)
            current = []
            continue
        if set(tok) <= _REDIRECT:
            continue
        if depth < 3 and any(c.isspace() for c in tok):
            for text in dict.fromkeys((tok, _without_comments(tok, ""))):
                yield from _segments(text, depth + 1)
        current.append(tok)
    if current:
        yield from _statement(current)


def _name(token: str) -> str:
    base = token.lstrip("`").replace("\\", "/").rsplit("/", 1)[-1].lower()
    return base.removesuffix(".exe")


def _command(tokens: list[str]) -> tuple[str, list[str]]:
    """Skip shell keywords (then, do, else...), wrappers (sudo, env,
    xargs...), their flags and VAR=value assignments; return the command
    name and its arguments."""
    for i, tok in enumerate(tokens):
        if (
            tok.lower() in KEYWORDS
            or _name(tok) in WRAPPERS
            or tok.startswith("-")
            or re.match(r"[A-Za-z_]\w*=", tok)
        ):
            continue
        return _name(tok), tokens[i + 1 :]
    return "", []


def _split_flag(tok: str) -> tuple[str, str | None]:
    """`--flag=value` and PowerShell `-Param:value` carry their value inline."""
    match = re.match(r"(-[^=:]*)[=:](.+)", tok)
    return (match.group(1).lower(), match.group(2)) if match else (tok.lower(), None)


def _operands(
    args: list[str], content_params: frozenset[str] | set[str] = frozenset()
) -> list[str]:
    """Every argument that could be a path: non-flag tokens plus inline flag
    values. The token after a content parameter (`-Value`) is skipped."""
    out: list[str] = []
    skip = after_dashdash = False
    for tok in args:
        if skip:
            skip = False
        elif after_dashdash or not tok.startswith("-") or tok == "-":
            out.append(tok)
        elif tok == "--":
            after_dashdash = True
        else:
            flag, value = _split_flag(tok)
            if flag in content_params:
                skip = value is None
            elif value is not None:
                out.append(value)
    return out


def _copy_destination(args: list[str]) -> list[str]:
    for i, tok in enumerate(args):
        flag, value = _split_flag(tok)
        is_dest = flag in ("-t", "--target-directory") or (
            len(flag) >= 4 and "-destination".startswith(flag)
        )
        if tok.startswith("-") and is_dest:
            return [value] if value is not None else args[i + 1 : i + 2]
    positional = _operands(args)
    return positional[-1:] if len(positional) > 1 else []


def _write_targets(name: str, args: list[str]) -> list[str]:
    if name in ALL_OPERANDS:
        return _operands(args, CONTENT_PARAMS)
    if name in DESTINATION_ONLY:
        return _copy_destination(args)
    return []


def _current_branch(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "symbolic-ref", "--short", "-q", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def _git(args: list[str], cwd: str) -> tuple[str, list[str], str]:
    """Split git's global options from its subcommand, following every -C."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-C" and i + 1 < len(args):
            cwd = os.path.join(cwd, args[i + 1])
        i += 2 if args[i] in GIT_VALUE_OPTS else 1
    if i >= len(args):
        return "", [], cwd
    return args[i], args[i + 1 :], cwd


def check_push(args: list[str], cwd: str) -> tuple[bool, str]:
    """Return (blocked, reason) for a force push or a push that lands on
    main/master. A push with no refspec sends the current branch."""
    positional: list[str] = []
    force = every_branch = tags = repo_flag = False
    skip = False
    for tok in args:
        if skip:
            skip = False
        elif not tok.startswith("-"):
            positional.append(tok)
            force = force or tok.startswith("+")
        elif tok.startswith("--force") or re.fullmatch(r"-\w*f\w*", tok):
            force = True
        elif tok in ("--all", "--mirror", "--branches"):
            every_branch = True
        elif tok == "--tags":
            tags = True
        elif tok.startswith("--repo"):
            repo_flag = True
            skip = "=" not in tok
        elif tok in PUSH_VALUE_OPTS:
            skip = True

    if force:
        return True, "git force-push is forbidden"
    if every_branch:
        return (
            True,
            "git push --all/--mirror includes main/master -- push one feature branch",
        )

    refspecs = positional if repo_flag else positional[1:]
    if not refspecs and not tags:
        refspecs = ["HEAD"]
    for spec in refspecs:
        dest = spec.lstrip("+").rsplit(":", 1)[-1]
        if dest in ("HEAD", "@"):
            dest = _current_branch(cwd)
        dest = dest.removeprefix("refs/heads/")
        if dest in PROTECTED_BRANCHES:
            return (
                True,
                f"git push to '{dest}' is forbidden -- use a feature branch + PR",
            )
    return False, ""


def check_parsed(command: str, protected: list[str], cwd: str) -> tuple[bool, str]:
    """Return (blocked, reason) from the shlex-parsed commands."""
    for tokens in _segments(command):
        name, args = _command(tokens)
        label = tokens[len(tokens) - len(args) - 1]
        if name == "git":
            sub, args, git_cwd = _git(args, cwd)
            if sub == "push":
                blocked, reason = check_push(args, git_cwd)
                if blocked:
                    return True, reason
                continue
            if sub not in ("rm", "mv") or (sub == "rm" and "--cached" in args):
                continue
            name, label = sub, f"git {sub}"
        for target in _write_targets(name, args):
            reason = _protected_reason(label, target, protected)
            if reason:
                return True, reason
    return False, ""


# One quoted string, or one comment (the group), or a run of anything else. A
# comment opens at a `#` that starts a word: at the start of a line, or after
# whitespace, a separator, a redirect or a brace. It ends with its line.
_COMMENT = r"'[^']*'?|\"[^\"]*\"?|((?<![^\s;&|()<>{}])#[^%s]*)|[^'\"#]+|#"
_COMMENT_TO_NEWLINE = re.compile(_COMMENT % r"\n")
_COMMENT_TO_LINE_END = re.compile(_COMMENT % r"\r\n")


def _without_comments(command: str, tool: str) -> str:
    """Cut each line at a `#` that opens a word outside quotes.

    A word opens at the start of the text and after whitespace, a separator,
    a redirect or a brace. PowerShell starts a comment in each of those
    places. Bash does not start one after a brace, so `${#x}` is cut here
    although Bash reads it as a length, and the rest of that line is then
    missing from this reading. The reading is only ever added to the
    others, so that takes no refusal away. It can add one: the index-only
    `git rm .env.d/${#n} --cached` loses its `--cached` here and is
    refused. A hash inside a word (`a#b`, a URL fragment) or inside quotes
    stays. Quotes are followed the way `_tokens` follows them, with no
    escape character, and a quoted string may run over several lines. Bash
    ends a comment at a newline. PowerShell ends a line at a lone carriage
    return as well, so every other tool gets the wider rule.
    """
    pattern = _COMMENT_TO_NEWLINE if tool == "Bash" else _COMMENT_TO_LINE_END
    return pattern.sub(lambda m: "" if m.group(1) is not None else m.group(), command)


def _head(command: str, tool: str) -> str:
    """The text in front of the first comment, or all of it without one."""
    pattern = _COMMENT_TO_NEWLINE if tool == "Bash" else _COMMENT_TO_LINE_END
    for match in pattern.finditer(command):
        if match.group(1) is not None:
            return command[: match.start()]
    return command


def _readings(command: str, tool: str) -> list[str]:
    """The command as sent, without its comments, and up to its first
    comment, each with lines joined.

    A newline ends a statement, so `rm -f \\` followed by `.env` on the next
    line reads as two statements and the delete loses its operand. Bash
    drops a backslash-newline and PowerShell reads a backtick-newline as a
    space. The join is added beside the original and never replaces it, and
    each shell gets only its own continuation character: a PowerShell path
    that ends in a backslash must not swallow the line below it.

    `_tokens` keeps comment text, and a quote mark in that text counts as a
    quote. One apostrophe in a note leaves the quotes unbalanced, and the
    plain split that follows no longer sees a command inside quotes. Two of
    them, in comments above and below a command, pair with the command's
    own quotes and pull it apart. So the command is read again with its
    comments cut out, which is how the shell reads it. That reading gets its
    own join, because a backslash at the end of a comment continues nothing.

    A quote left open on a later line still takes every line to the plain
    split, though Bash runs the lines above the broken one before it stops.
    So the text in front of the first comment is read alone as well, and
    nothing that follows it can change how it reads there. Without a
    comment that reading is the command itself and adds nothing.

    Every reading is checked, and any one of them can refuse.
    """
    readings = [command]
    for text in (command, _without_comments(command, tool), _head(command, tool)):
        joined = text
        if tool != "PowerShell":
            joined = re.sub(r"\\\r?\n", "", joined)
        if tool != "Bash":
            joined = re.sub(r"`\r?\n", " ", joined)
        for reading in (text, joined):
            if reading not in readings:
                readings.append(reading)
    return readings


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    if not isinstance(command, str) or not command:
        return 0
    cwd = payload.get("cwd") or os.getcwd()
    tool = payload.get("tool_name")

    protected = PROTECTED_SUBSTRINGS
    blocked, reason = False, ""
    for reading in _readings(command, tool if isinstance(tool, str) else ""):
        blocked, reason = check_protected_writes(reading, protected)
        if not blocked:
            blocked, reason = check_parsed(reading, protected, cwd)
        if not blocked:
            blocked, reason = check_dangerous_git(reading)
        if not blocked:
            blocked, reason = check_dangerous_env(reading)
        if blocked:
            break

    if blocked:
        print(
            json.dumps({"decision": "block", "reason": f"[bash-safety-hook] {reason}"})
        )
        print(f"[bash-safety-hook] BLOCKED: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 -- intentional fail-open
        print(f"[bash-safety-hook] hook error (failing open): {exc}", file=sys.stderr)
        sys.exit(0)
