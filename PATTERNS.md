# Patterns

The architectural decisions behind this workspace, stated as patterns: the problem each solves, the shape of the solution, why it beats the obvious alternative, and what it costs. The file conventions are Claude Code's; the patterns travel to any agent runtime.

Read this when you want the *why*. [META_ARCHITECTURE.md](META_ARCHITECTURE.md) is the *what* (the structural map), and [ADOPTION.md](ADOPTION.md) is the *how* (where to start). Each pattern ends with a pointer to the sample files that implement it, so every claim here is inspectable.

## 1. Pure roles, composed with project facts

**Problem.** Run security review across five projects and you end up with five near-identical 500-line prompts that drift apart the moment one is edited.

**Pattern.** Keep the expert persona *pure*. A `security-auditor` role file holds method, constraints, and red flags, with zero entity facts. Project specifics live in a `CONTEXT.md`. A thin binding (`@project-security`) composes the two at invocation.

**Why this beats the obvious.** The obvious move is one big prompt per project. Extraction means a fix to the auditor's method reaches every project at once, and a new project gets an expert reviewer by writing one `CONTEXT.md` instead of cloning a prompt that immediately starts to rot.

**Cost.** Indirection (two files, not one) plus a validator to catch bindings that reference a role or context that moved. Worth it past about three projects; overkill for one.

**Where it lives:** [`samples/roles/`](samples/roles/) (17 roles + the template) and [`samples/example-project/`](samples/example-project/) (a binding composing role + context).

## 2. Classify-then-act, not ask-then-wait

**Problem.** An autonomous background agent has two failure modes: it nags for input on everything, or it acts confidently on tasks it doesn't understand.

**Pattern.** Classify every incoming task first: `has-default` (an obvious correct action exists), `needs-intent` (genuinely ambiguous), or `out-of-scope`. Build the `has-default` work speculatively in a sandbox, lodge it for review, and act only on approval. Log every rejection as a short decision record the agent greps before classifying anything similar again.

**Why this beats the obvious.** A pure question-queue stalls on the user. A pure autonomous loop ships things you didn't want. Classification routes each task to the safe handling, and the rejection log stops the same bad idea coming back next cycle.

**Cost.** A sandbox, a review queue, and a rejection history to maintain. The agent does speculative work that sometimes gets discarded.

**Where it lives:** [`samples/scripts/heartbeat/classify_task.py`](samples/scripts/heartbeat/classify_task.py) and [`samples/tasks/HEARTBEAT.md`](samples/tasks/HEARTBEAT.md).

## 3. Make silent failure loud (the dead-man's switch)

**Problem.** A scheduled task that stops firing fails silently. You find out weeks later, when the thing it was supposed to produce is missing.

**Pattern.** Each task emits a success sentinel to its log. A watchdog scans for that sentinel inside a staleness window and raises a finding when it is missing or stale. Self-hosted, no external uptime service required.

**Why this beats the obvious.** "I'll notice if it breaks" is the alternative, and it is false. The whole point of a background task is that nobody is watching it. A sentinel converts absence-of-success into a visible, dated finding.

**Cost.** Per-task staleness configuration, plus a tolerance flag for tasks that run on demand rather than on a clock.

**Where it lives:** [`samples/scripts/security/check_task_freshness.py`](samples/scripts/security/check_task_freshness.py).

## 4. Tier by mechanical impact, not by tone

**Problem.** A system that auto-applies its own findings needs a line between "apply automatically" and "ask a human first." Drawing that line from how confident a finding *sounds* is a trap.

**Pattern.** Classify each change by mechanical reversibility. A typo fix and a deleted file sit in different tiers regardless of how the finding is worded. Low-impact, trivially reversible changes auto-apply; anything that deletes, publishes, or spends money gets a human gate.

**Why this beats the obvious.** Tone-based heuristics ("the finding says critical") are gameable and drift over time. Mechanical impact is a property of the action itself, not the language describing it.

**Cost.** An explicit impact table, kept current as new action types appear.

**Where it lives:** [`samples/.claude/agents/audit.md`](samples/.claude/agents/audit.md) (the tier-classification table).

## 5. Memory points, it doesn't mirror

**Problem.** Agent memory that copies your source documents goes stale the moment a source changes, then quietly contradicts it.

**Pattern.** Memory holds an index plus typed notes (`user` / `feedback` / `project` / `reference`) that *point at* the source of truth instead of duplicating it. Every write is one of four operations (add, update, delete, no-op), never a blind append. Check a memory claim against current state before asserting it as fact.

**Why this beats the obvious.** Dumping everything into memory feels safe and rots fast. A pointer cannot contradict its source; a copy eventually always does.

**Cost.** Discipline at write time, plus a periodic consolidation pass to merge duplicates and prune the index.

**Where it lives:** [`samples/.claude/scheduled-tasks/consolidate-memory/SKILL.md`](samples/.claude/scheduled-tasks/consolidate-memory/SKILL.md) and [`samples/scripts/memory_lint.py`](samples/scripts/memory_lint.py).

## 6. Credentials live in one place, never in files

**Problem.** A secret written to a file leaks: into git history, into a backup, into an agent's context window, into a screenshot.

**Pattern.** A password manager is the single store. Files reference the item *name*, never the value. Running code resolves the secret at runtime and scrubs it afterward. Allow one narrow, audited exception per genuine need (a self-only email sender, say), not a general waiver.

**Why this beats the obvious.** A `.env` file and "I'll just paste it for now" are how secrets end up in transcripts forever. One store with runtime resolution keeps the value out of every durable surface.

**Cost.** A runtime lookup step, and the discipline to refuse the convenient shortcut.

**Where it lives:** [`samples/scripts/backup-restic.ps1`](samples/scripts/backup-restic.ps1) (runtime resolution + scrub) and [`samples/scripts/send_self_email.py`](samples/scripts/send_self_email.py) (the one narrow, audited exception).

## 7. A cheap hook beats a careful agent

**Problem.** An agent that has misread the task can overwrite your `.env`, delete a record, or force-push. "Be more careful" does not scale.

**Pattern.** A `PreToolUse` hook intercepts file writes and shell commands against a blocklist (sensitive paths, destructive verbs, pushes to protected branches) and blocks them before they run. It fails *open*: a bug in the guard must never wedge the session.

**Why this beats the obvious.** Trusting the model to never err is a hope, not a control. A ten-line deterministic check catches the large majority of accidental damage for almost nothing.

**Cost.** Occasional false positives (a legitimately named file that matches a protected substring), best resolved by naming around them rather than widening the gap.

**Where it lives:** [`samples/scripts/security/check_bash_command.py`](samples/scripts/security/check_bash_command.py) and the hook config in [`samples/.claude/settings.example.json`](samples/.claude/settings.example.json).

## 8. Audit the workspace like a fitness function

**Problem.** A workspace degrades. Context bloats, configs drift, a hook stops firing, memory contradicts reality, and nobody's job is to notice.

**Pattern.** A scheduled auditor sweeps configs, the security envelope, and drift on a cadence, writing findings to the task list. Synthetic canaries verify the audit still detects known-bad fixtures every run. A finding ledger tracks accept and dismiss rates. There is deliberately **no single numeric score**: a self-improving audit that emits its own grade optimises for the grade (Goodhart's law).

**Why this beats the obvious.** "I'll clean it up when it bothers me" loses to a cadence with canaries, because drift is gradual and invisible right up until it isn't.

**Cost.** The audit is itself a system to maintain, and it can cry wolf, so findings are tiered and tracked rather than dumped raw into the queue.

**Where it lives:** [`samples/.claude/agents/audit.md`](samples/.claude/agents/audit.md) and [`samples/tests/audit_canaries/`](samples/tests/audit_canaries/).

## 9. Context is a budget, not a constant

**Problem.** Everything auto-loaded into a session — instruction files, the memory index, skill descriptions, hook strings — costs tokens on every turn, in every session. No single addition is large, so the total grows a few percent a week, and unattended agents spend with nobody watching. Quality erodes before any cost alarm fires.

**Pattern.** Meter it like money. A baseline counter measures every always-loaded source individually and keeps history. A trend alarm fires when the baseline beats its rolling median by a set margin, because accretion is the common failure, not the blowout. Unattended runs carry hard spend ceilings sized as belts (10–50x a normal cycle), multi-agent fan-outs are bounded by construction, index files carry explicit size ceilings, and a standing note tells the runtime what must survive context compaction.

**Why this beats the obvious.** The obvious control is a size warning on the main instruction file: one source, one absolute threshold. The real failure is distributed (a dozen sources each growing slightly) and relative (this month versus last), so per-source measurement with trend detection catches what a static ceiling misses. Attribution is the payoff: a total says something grew; the breakdown says what to trim.

**Cost.** A counter and its history to maintain, estimates that drift from true tokenizer counts, and ceilings that need sizing judgment — a cap set as a governor instead of a belt aborts legitimately heavy runs.

**Where it lives:** [`samples/scripts/ghost_token_counter.py`](samples/scripts/ghost_token_counter.py) (the per-source baseline) and [`samples/scripts/token_report.py`](samples/scripts/token_report.py) (spend telemetry feeding the audit's trend rule).

## How they compose

These are not independent. The credential law and the file-protection hook are the same instinct (keep damage out of durable surfaces) applied at two layers. The roles library and memory hygiene are the same instinct (one source of truth, referenced rather than copied) applied in two domains. Classify-then-act and tier-by-impact are the same instinct (route by consequence, not by confidence) applied to tasks and to findings. And the context budget is the audit's instinct (notice drift before it bites) pointed at the one resource every other pattern spends.

Adopt them when you feel the friction each one removes. Not before.

---

*Last verified against the repo structure on 2026-06-11.*
