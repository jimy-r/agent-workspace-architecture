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

**Pattern.** A `PreToolUse` hook intercepts file writes and shell commands against a blocklist (sensitive paths, destructive verbs, pushes to protected branches, exec-hijacking env-var prefixes like `GIT_SSH_COMMAND='…' git fetch`) and blocks them before they run. It fails *open*: a bug in the guard must never wedge the session.

**Why this beats the obvious.** Trusting the model to never err is a hope, not a control. A ten-line deterministic check catches the large majority of accidental damage for almost nothing.

**Cost.** Occasional false positives (a legitimately named file that matches a protected substring), best resolved by naming around them rather than widening the gap.

**Where it lives:** [`samples/scripts/security/check_bash_command.py`](samples/scripts/security/check_bash_command.py) and the hook config in [`samples/.claude/settings.example.json`](samples/.claude/settings.example.json).

## 8. Audit the workspace like a fitness function

**Problem.** A workspace degrades while the ecosystem around it improves. Context bloats, configs drift, a hook stops firing, memory contradicts reality, better patterns ship every week — and nobody's job is to notice either direction.

**Pattern.** A scheduled auditor runs on a cadence with two jobs. The first is finding improvements: research public sources for what the ecosystem has learned, and critique the workspace module-by-module against current best practice. The second is housekeeping: sweep configs, the security envelope, and drift. Findings land in the task list. Synthetic canaries verify the audit still detects known-bad fixtures every run. A finding ledger tracks accept and dismiss rates. There is deliberately **no single numeric score**: a self-improving audit that emits its own grade optimises for the grade (Goodhart's law).

**Why this beats the obvious.** "I'll clean it up when it bothers me" loses to a cadence with canaries, because drift is gradual and invisible right up until it isn't; "I'll look for upgrades when I have time" never fires at all.

**Cost.** The audit is itself a system to maintain, and it can cry wolf, so findings are tiered and tracked rather than dumped raw into the queue.

**Where it lives:** [`samples/.claude/agents/audit.md`](samples/.claude/agents/audit.md) and [`samples/tests/audit_canaries/`](samples/tests/audit_canaries/).

## 9. Context is a budget, not a constant

**Problem.** Everything auto-loaded into a session — instruction files, the memory index, skill descriptions, hook strings — costs tokens on every turn, in every session. No single addition is large, so the total grows a few percent a week, and unattended agents spend with nobody watching. Quality erodes before any cost alarm fires.

**Pattern.** Meter it like money. A baseline counter measures every always-loaded source individually and keeps history. A trend alarm fires when the baseline beats its rolling median by a set margin, because accretion is the common failure, not the blowout. Unattended runs carry hard spend ceilings sized as belts (10–50x a normal cycle), multi-agent fan-outs are bounded by construction, index files carry explicit size ceilings, and a standing note tells the runtime what must survive context compaction.

**Why this beats the obvious.** The obvious control is a size warning on the main instruction file: one source, one absolute threshold. The real failure is distributed (a dozen sources each growing slightly) and relative (this month versus last), so per-source measurement with trend detection catches what a static ceiling misses. Attribution is the payoff: a total says something grew; the breakdown says what to trim.

**Cost.** A counter and its history to maintain, estimates that drift from true tokenizer counts, and ceilings that need sizing judgment — a cap set as a governor instead of a belt aborts legitimately heavy runs.

**Where it lives:** [`samples/scripts/ghost_token_counter.py`](samples/scripts/ghost_token_counter.py) (the per-source baseline) and [`samples/scripts/token_report.py`](samples/scripts/token_report.py) (spend telemetry feeding the audit's trend rule).

## 10. A skill is editable weights — never adopt a self-edit without a gate

**Problem.** Instruction files are the part of the system that most invites quiet self-improvement. A `CLAUDE.md` or a skill doc is plain text the agent can rewrite, and an agent that watches its own transcripts can propose better wording every day. Let that loop close on itself and you have a system editing its own controlling instructions with nobody checking whether each edit actually helped.

**Pattern.** Treat skill and instruction text as *optimizable weights*, and put a gate between a proposed edit and the live file. In this workspace the gate is a human: the heartbeat builds a change speculatively in a sandbox, lodges it for review, and applies nothing until approval; the memory-consolidation pass runs four-operation discipline (add, update, delete, no-op) instead of blind appends; the file-protection hook (Pattern 7) keeps even an approved edit from reaching a protected file by an unwatched path. Staging, then review, then adopt. The edit is a proposal until a check clears it.

**Why this beats the obvious.** The obvious move is to let the agent fold its own lessons straight back into its instructions, and that is exactly the move with a measured failure mode. Microsoft Research's SkillOpt (arXiv:2605.23904, ~7.9k GitHub stars, MIT, v0.1.0 alpha) frames a skill doc as the trainable weights of a frozen model and optimizes it against a scored benchmark, accepting an edit only when a held-out split *strictly* improves. Their cautionary single-seed run shows why the gate is the load-bearing piece: an *ungated* self-edit loop on a weak model with a degraded signal collapsed from 0.554 to 0.026 (a 52.8-point drop) by learning to answer with the document-title string verbatim, while the gated twin rejected every bad edit and stayed flat. That figure is a single-seed research result, not a constant, and the published gains land only where tasks recur with a checkable correctness signal, going flat on saturated or noisy ones. The transferable lesson survives all those caveats: a self-edit loop without an accept/reject check can optimize itself straight off a cliff. This workspace runs the human-gated cousin of that loop. It does not run a trajectory-scored training gradient or a held-out-validation gate; the discipline it borrows is the refusal to adopt an edit on the strength of the edit alone.

**Cost.** The gate is the slow part. A human in the staging loop means instruction improvements land in days, not seconds, and the speculative work behind a rejected edit is thrown away. That latency is the price of never waking up to a controlling file that an unsupervised loop quietly rewrote.

**Where it lives:** [`samples/tasks/HEARTBEAT.md`](samples/tasks/HEARTBEAT.md) (classify → sandbox → stage → review → adopt) and [`samples/.claude/scheduled-tasks/consolidate-memory/SKILL.md`](samples/.claude/scheduled-tasks/consolidate-memory/SKILL.md) (four-operation write discipline). SkillOpt itself is credited in [ATTRIBUTION.md](ATTRIBUTION.md).

## 11. A scaffold is a hypothesis — gate it behind a measurable signal

**Problem.** The tempting way to make an agent smarter is to keep adding to the layer around it: another skill, another always-loaded directive, another reasoning rule, another self-critique pass. Most of it feels like an upgrade and never gets checked. Two failure modes hide in that habit. The first is the scaffold that does nothing (a second same-model pass over the same prompt, an ungrounded "now critique your answer" step) and can even degrade the result while costing tokens. The second is accretion: every always-loaded line dilutes the signal of every other, so a workspace can get measurably dumber by growing.

**Pattern.** Treat the workspace itself as fixed weights and everything around it as the trainable part, then borrow the discipline that makes training honest: a held-out check. A change earns its place only when it adds a *checkable external signal* (a golden expectation, a re-fetched source, a deterministic lint, a test) or *genuine divergence* (a critic working from a different rubric, parallel attempts seeded from genuinely different strategies). More same-model compute is neither, so it doesn't count. Operationally: register every scaffold with a falsifiable hypothesis and a review date; measure with a small golden-set reasoning-regression suite replayed under a variance floor (each case run several times, scored as a pass-rate ± stddev, never a single number); and at the review date, beat baseline on that suite or get cut. Removal is a first-class outcome, not an admission of failure. Trimming the always-loaded surface is itself a way to raise effective intelligence.

**Why this beats the obvious.** The obvious move is to add the thing that sounds smart and trust that it helped. That trust is exactly what a self-improving layer can't afford, because the same plausibility that sells a good scaffold sells a useless one. A correctness signal scores the answer, not the story; a variance floor stops a single lucky run from masquerading as a gain. And the remove-bias names the asymmetry an upgrade pass always has: it is wired to add, so it under-weights the cut that would help more.

**Cost.** The suite is a system to build and maintain, and a meaningful one needs real cases with deterministically-checkable answers, which take effort to write. The variance floor multiplies every measurement by the re-run count. And the register only works if it is actually consulted at the review date rather than becoming another stale list. The discipline is the load-bearing part, not the file.

**Where it lives:** the same fitness-function machinery as [`samples/.claude/agents/audit.md`](samples/.claude/agents/audit.md) (Pattern 8). The reasoning-regression suite runs on the audit's cadence and reports like its other coded checks, and it is the measurement-gated cousin of the self-edit gate in Pattern 10: a correctness signal certifying a *scaffold* the way a human gate certifies a *self-edit*.

## 12. Loop selection: not everything should be a loop

**Problem.** Give an agent real capability and the tempting response is to automate everything: put a loop on every recurring task, "remove yourself as the bottleneck." But most real work is judgment-heavy, irreversible, or unverifiable. Loop the judgment work and you remove the value (the judgment was the point). Loop the irreversible work and you ship damage unattended. Autonomy gets treated as a pure good, and the question of *which* tasks earn it never gets asked.

**Pattern.** A four-box test. A task earns an **autonomous loop** only when it is *all* of: (1) **recurring**, a cadence or repeated event, not a one-off; (2) **mechanically verifiable**, where a script, exit code, schema, or diff confirms it worked, not human taste; (3) **low-judgment-per-instance**, the same decision every time, not a fork on context only you hold; (4) **headless-executable**, able to run unattended with no interactive credential, no GUI, no human mid-step. An **irreversibility override** caps any outward or destructive act (email sent, comment posted, money moved, history pruned) at *surface* even when all four boxes pass: verifiability gates correctness, it does not gate consequence. Three buckets fall out. **Loop:** all four boxes and reversible/inward, runs autonomously on a trigger, the verifier is the gate. **Surface:** recurring and verifiable but judgment-heavy or irreversible, so a read-only nudge or an approval-gated act, never silent autonomy. **Keep manual:** fails recurring or carries high judgment per instance — you drive, tooling assists. A worked surfacing case: a close-out routine that, the moment a task finishes, runs a read-only scan and shows what drifted across the workspace (stale context docs, fired strategic triggers, aging backups, open questions going cold) for the operator to action while still in context. It adds no new autonomy; it widens the operator's view at the moment state changed.

**Why this beats the obvious.** The obvious move is to automate everything and treat the human as the bottleneck to engineer out. But an autonomous loop only pays where the work is verifiable and low-judgment; pointed at judgment work it either strips the value or acts wrongly with nobody watching. This is the same route-by-consequence instinct as classify-then-act (Pattern 2), tier-by-impact (Pattern 4), the skill-as-weights gate (Pattern 10), and the scaffold-as-hypothesis gate (Pattern 11): gate by what an action *costs if wrong*, not by how automatable it feels. For a solo operator whose own judgment is the product, the restraint is the point — the loops exist to protect attention for the judgment-heavy work, not to hand that work to the machine.

**Cost.** A test you have to actually run, honestly, against the pull to automate. And a verification step before it: check the target against the *code*, not its description, on three axes. Does it exist on the relevant branch (`git ls-tree`, never a working-tree glob alone)? Does it do what its description claims (read the script: an "additive backup" turned out to be a destructive `--prune`)? Can it run headless? A task can pass every quality box and still fail box 4. Scoring from descriptions instead of code manufactured three wrong "loop this" calls in a single design pass.

**Where it lives:** [`samples/scripts/wrap_drift_scan.py`](samples/scripts/wrap_drift_scan.py) (the read-only close-out surfacing scan — the worked *surface* case).

## How they compose

These are not independent. The credential law and the file-protection hook are the same instinct (keep damage out of durable surfaces) applied at two layers. The roles library and memory hygiene are the same instinct (one source of truth, referenced rather than copied) applied in two domains. Classify-then-act, tier-by-impact, the skill-as-weights gate, and loop-selection are the same instinct (route by consequence, not by confidence) applied to incoming tasks, to audit findings, to the agent's edits of its own instructions, and to the choice of what gets automated at all — the edit-your-own-instructions case is the riskiest, because the thing being changed is the controlling text itself, and loop-selection is the instinct turned upstream: it asks which work should reach an autonomous loop before any of the other gates get a say. And the context budget is the audit's instinct (notice drift before it bites) pointed at the one resource every other pattern spends. The scaffold-as-hypothesis gate is that same audit instinct again, pointed inward at the workspace's own additions: the self-edit gate (Pattern 10) certifies a change to the instructions, and the reasoning-regression suite certifies a change to the capability layer — both refuse to adopt on the strength of how good the change sounds.

Adopt them when you feel the friction each one removes. Not before.

---

*Last verified against the repo structure on 2026-06-11.*
