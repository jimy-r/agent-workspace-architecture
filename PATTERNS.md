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

**Pattern.** Treat skill and instruction text as *optimizable weights*, and put a gate between a proposed edit and the live file. In this workspace the gate is a human: a proposed change is built speculatively in a sandbox, lodged for review, and applied only once approved; the memory-consolidation pass runs four-operation discipline (add, update, delete, no-op) instead of blind appends; the file-protection hook (Pattern 7) keeps even an approved edit from reaching a protected file by an unwatched path. Staging, then review, then adopt. The edit is a proposal until a check clears it.

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

## 13. Challenge half-formed ideas with a different lens — and hold a sample back to prove it helps

**Problem.** Every tool that critiques an agent's work assumes a finished artifact: a draft to red-team, a decision to rank, a result to verify. None help during the messy part, where you're exploring a design or framing a problem and nothing is built yet and no test exists to check against. The tempting fix is to bolt a second agent onto the thinking itself and let it challenge every idea as it forms, always on, in the background. Two traps spring at once. The challenge is usually the same model re-reading its own frame, which rationalizes more than it challenges and can degrade the answer while burning tokens. And once it runs on everything, you have lost the one thing that would prove it helps: a comparison against not running it.

**Pattern.** Make it a single *divergent* lens rather than a debate, and hold a sample back so you can still measure it. When a real fork appears in open-ended thinking, fire one challenge from a deliberately different frame: the strongest objection to this direction, the assumption being baked in, the option not being considered. Ground it in a stated criterion, a retrieved fact, or a checkpoint with the human, who stays the arbiter. It widens the option set; it never argues toward a winner. Then the measurement move: roll on each eligible fork and deliberately skip the challenge on a fraction (say one in three), logging both the fired and held-out forks. The human tags each fired challenge as changed-the-call, real-but-didn't, or noise. At review the noise rate and the fired-versus-held-out comparison say whether it earns its place; a noise-dominant result cuts it.

**Why this beats the obvious.** The obvious move is two agents bouncing an idea back and forth until something better falls out, and the evidence is hostile to exactly that shape: same-model same-prompt debate loses to plain majority voting at equal compute, ungrounded self-critique with no external signal typically fails to help and often degrades, and *assigned* devil's advocacy is reliably weaker than dissent that carries real information, a finding that predates LLMs by decades in the group-decision literature. What survives is the narrow form: a different lens not a louder echo, aimed at divergence not convergence, grounded not assertion-trading. The measurement is not optional either. An always-on aid is unmeasurable by construction: if it fires on everything, every decision got it, and you never see the one without it. Holding out a sample keeps the counterfactual alive, the same instinct as a control group applied to a behavioral aid in production.

**Cost.** A behavioral trigger that depends on the agent actually firing it, since no hook can detect "this is a real fork," so adherence has to be watched (the log's own fire count doubles as that watch). The held-out sample means deliberately skipping the aid on work it might have improved, to buy the ability to measure at all. And a tagging step for the human on each firing, the only honest source of the verdict, because a model grading its own challenges inherits a measured self-preference bias.

**Where it lives:** [`samples/scripts/ideation_spar_log.py`](samples/scripts/ideation_spar_log.py), the roll / hold-out / log / report engine that keeps an always-on-feeling aid measurable. It is the production-side cousin of the offline golden set in Pattern 11: there a held-out *case set* certifies a scaffold; here a held-out *slice of live firings* certifies a behavioral aid that has no offline test.

## 14. Delegation is a queue you fill, not work the agent finds

**Problem.** A background project-manager agent that finds its own work has to guess what you meant by it. This workspace ran one on a two-hourly cycle: it read the task list and classified each item, then either built the safe-by-default work or posted a clarifying question. The questions were the flaw. They went to a file nobody opened, thirteen of them piled up unanswered, and every task sitting behind one stopped moving. The second failure was operational. The scheduled runtime rode an ambient credential that expired without raising anything, so the cycles failed dark for about five weeks, and the dead-man's-switch alarms of Pattern 3 fired into channels whose only readers were the dead systems themselves.

**Pattern.** Invert the direction of authorization. Work reaches the agent only when the operator marks a card on the task board as delegated, and marking it runs a short intake interview while the intent is still in the operator's head. What does done look like, which folders may be written, what constrains the approach, and how should the one or two foreseeable decision points be ruled if the work hits them. A drain skill actions the queue on demand inside an ordinary interactive session, validating a template floor per card first: a literal next action, a link to a folder that exists, a checkable done-when, an effort size. When the work reaches a fork the intake didn't pre-rule, the question goes onto the card itself. No cron sits behind any of it.

**Why this beats the obvious.** The obvious design is the one that failed. Let the agent discover work, classify it, and ask when it isn't sure. Discovery makes authorization ambiguous, so the agent's first job becomes inferring intent from a line written for a human reader, and that inference is where the thirteen questions came from. A queued card is the mandate, stated by the person who holds the intent at the moment they hold it. The same move fixes the question channel. A fork written on the card gets read because the board is where work gets picked up; a dedicated questions file is a channel with no reader. Running on demand in a live session then removes the whole class of unattended-runtime failure. The credential is the session's own, the operator is present, and a broken drain is visible in the moment instead of five weeks later. This is Pattern 12's four-box test applied to the agent's own coordinator, and the honest answer is *surface* rather than *loop* — the work recurs, but the judgment per instance is high.

**Cost.** Nothing happens while you're away. The queue is inert until someone runs the drain, so a queue nobody drains goes stale as quietly as a dead scheduler; the mitigation is the session-start briefing, which reports the queue count and offers to drain it. Delegation also costs a minute of attention per card at the moment you would rather move on, and that minute is where the quality comes from, so a card queued in a hurry buys plausible-wrong work later. Early evidence is thin but positive. The first drain closed two of two cards with no rework.

**Where it lives:** [`samples/board/agent-queue.SKILL.example.md`](samples/board/agent-queue.SKILL.example.md) (the intake interview and the drain protocol it feeds), with the card schema and the succession reasoning in [`samples/board/README.md`](samples/board/README.md). Pattern 2 is the predecessor it replaced; the classification logic there holds wherever the mandate is already unambiguous, and discovery is the half that failed.

## 15. Price the lane before you migrate it

**Problem.** Token consumption climbs even after efficiency work, because every saving gets reinvested in more agent work — Jevons, applied to your own subscription. At the ceiling, the instinctive fix is structural: migrate the execution tier to cheaper open-weight models, buy a GPU, stand up a second inference stack. Plans of that shape are expensive to be wrong about, and the headline per-token price lists that motivate them hide everything that decides the outcome.

**Pattern.** Instrument before migrating. Walk the transcripts and split consumption three ways: by lane (orchestrator versus dispatched subagents), by token class (fresh input, cache writes, cache reads, output), and by model. Then pull the configuration levers the measurement exposes, cheapest first, one variable at a time, each as a registered trial with a kill criterion and an instrument the weekly audit reads. In this workspace that meant three moves before any migration: always-on orchestration became opt-in (the evidence for selective triggering over always-on is strong), maximum reasoning effort was scoped to judgment lanes only (output was ~11% of cost, so effort is a quality dial, not a cost lever), and execution dropped one rung within the provider's own ladder as a measured trial. The migration project stays gated on the re-measure: it opens only if spend still exhausts after the cheap levers land.

**Why this beats the obvious.** The obvious move nearly shipped here. Measurement killed it in an afternoon, three ways. The workload's cost was 88% input-side and ran at a 95% cache-hit rate, with cache reads priced at a tenth of input — a subsidy the migration would silently forfeit, since open-weight endpoints cache weakly or not at all. The local GPU could not serve a single day's execution volume. And the per-subagent provider routing the design assumed did not exist in the harness, so the split would have required an unaudited third-party proxy in front of a live session credential. None of those facts is visible on a price list; all of them came out of a two-second transcript walk. The measured configuration changes captured most of the saving with zero integration risk, and the trial that remained changes one variable behind the existing review gate, with rework marked in the session record so the kill metric cannot be quietly rationalised away.

**Cost.** The instrument itself, and the honesty it demands: a rework marker convention that only works if every escalation is recorded, a baseline that must be re-verified rather than remembered, and one-variable-at-a-time patience, which means the full ladder takes weeks. The meter that proves the upgrade worked is the same meter that will prove it didn't.

**Where it lives:** [`samples/scripts/tier_metrics.py`](samples/scripts/tier_metrics.py) (the lane-split instrument with its four advisory checks and selftest), consumed by the audit's checks-as-code the same way as the Pattern 11 machinery. Pattern 9 is the parent instinct (context as a budget) applied here to the model ladder; Pattern 11 supplies the trial discipline: falsifiable hypothesis, review date, kill criterion.

## 16. A claim carries its provenance, or it is a guess

**Problem.** An agent writes a paragraph in which "the config sets `X`", "the docs recommend `Y`" and "this is probably `Z`" are typographically identical. A verified fact and a plausible invention render the same. The reader either checks everything, which defeats the point of delegating, or checks nothing, which is how a fabrication becomes a decision. The failure is not that the agent guessed. It is that the guess arrived wearing the same clothes as the fact.

**Pattern.** Three mechanisms, applied to load-bearing claims only.

*Cite the location, not the recollection.* For any claim about system state (a file's contents, a path, a config flag, a status, a line number), read the source and cite `path:line` before asserting. "Not found in `<file>`" is a complete and useful answer. A guess dressed as a finding is not.

*Grade on two axes, visibly.* Source reliability (A authoritative to E anecdotal) and claim credibility (1 confirmed by multiple sources to 5 unverified), tagged inline as `A1` or `B3`. Then label each load-bearing claim `[observed]` (quotable from a source), `[inferred]` (reasoned from evidence) or `[unverified]`. Two axes, because a reliable source can still make a weak claim.

*Record what would falsify it.* A durable brief carries the date it was last verified and an explicit list of the checks that would confirm or break its conclusions. This is what lets a stale document announce its own staleness instead of quietly lying to the next reader.

Scope matters. Tag load-bearing workspace-state claims, not general reasoning or well-known facts. An `[unverified]` on everything carries the same information as an `[unverified]` on nothing.

**Why this beats the obvious.** The obvious instruction is "be accurate," which is unenforceable, unmeasurable, and already what the agent was trying to do. Grading is mechanical. It survives handover, it degrades gracefully (a wrong grade is still a visible grade), and it makes uncertainty legible to the *next* reader, including the next agent, which cannot ask what you meant and will otherwise inherit a guess as a premise. That inheritance is the real cost: an unmarked guess does not stay one claim wrong, it becomes the foundation of the next three.

The pattern also fails usefully. When a claim turns out wrong, the grade shows whether the process failed or the source did, which is the difference between fixing a habit and distrusting a document.

**Cost.** Friction at write time, on every claim, forever. A reader who learns the grades and then finds them applied carelessly trusts them less than no grades at all, so the discipline is all-or-nothing per document. And it does not catch the confident wrong answer drawn from a real source that says something else. For that, see Pattern 8, which measures rather than labels.

**Where it lives:** [`samples/roles/researcher.md`](samples/roles/researcher.md) carries the full two-axis grading scheme and the claim-evidence-inference separation it sits inside. [`samples/CLAUDE.md.example`](samples/CLAUDE.md.example) carries the `path:line` rule that extends it from research tasks to ordinary answers.

**Boundary with its neighbours.** Pattern 5 governs what memory *stores*; this governs what an assertion *carries at the moment it is made*. Pattern 8 measures whether the workspace is drifting; this makes a single claim auditable without measuring anything. The three are separable: a workspace can store pointers faithfully, audit itself weekly, and still hand you a confident sentence with nothing behind it.

## 17. One canonical copy, and pointers from everywhere else

**Problem.** The same rule ends up written in three places: the user-global instructions, the workspace instructions, and a project file. All three were correct on the day they were written. Then one gets edited. Now an agent loading all three reads two versions of the rule and silently picks one, and a reader checking the project file gets an answer that the workspace file contradicts. Nobody notices, because each copy looks authoritative on its own. Duplication does not announce itself as duplication; it announces itself as a wrong answer, months later, with no obvious cause.

**Pattern.** Each fact has exactly one canonical location. Everywhere else points at it and states that it is a pointer.

Three mechanics make that hold. *Delete the copy, keep the pointer.* When the same rule appears twice, the second instance becomes a one-line reference naming the canonical file and section, not a summary of it, because a summary is a copy that drifts more slowly. *Banner what is superseded.* A document that has been replaced says so at the top, names its replacement, and stays on disk, so the reader learns which copy governs from the document itself rather than from folder archaeology. *Measure the duplication mechanically.* Always-loaded files accumulate shared boilerplate that no single edit introduced, so something has to scan across them and report the overlap.

**Why this beats the obvious.** The obvious fix is to keep the copies synchronised, which is a promise to do unbounded manual work forever, made by whoever is least likely to remember. It also fails silently: nothing breaks when a copy drifts, so nothing prompts the fix.

The pointer approach has a property the sync approach lacks. A pointer cannot disagree with its target. It can be *stale* (pointing at something moved or renamed), but stale-and-broken is loud, whereas stale-and-plausible is not. Trading a silent failure for a noisy one is most of the value.

This workspace's own instructions carry a worked instance, left in place deliberately: a communication-standards section that had been duplicated into the workspace file was cut back to a pointer after the inline copy was found to have drifted from its source. Two bullets had diverged and one had gone missing entirely. Neither file looked wrong.

**Cost.** Indirection. A reader following a pointer needs a second lookup, which is a real tax on comprehension, and pointer chains longer than one hop become their own problem. Canonical placement also has to be decided rather than discovered, and the wrong choice is expensive to reverse once other files reference it. Duplication is genuinely cheaper right up until the first edit.

**Where it lives:** [`samples/scripts/claudemd_audit.py`](samples/scripts/claudemd_audit.py) inventories every always-loaded instruction file and flags size, staleness, broken imports, and boilerplate duplicated across files. Pattern 5 is the same instinct applied to memory; this is it applied to instructions, which are loaded on every session and so cost on every session.

## How they compose

These are not independent. The credential law and the file-protection hook are the same instinct (keep damage out of durable surfaces) applied at two layers. The roles library and memory hygiene are the same instinct (one source of truth, referenced rather than copied) applied in two domains. Classify-then-act, tier-by-impact, the skill-as-weights gate, and loop-selection are the same instinct (route by consequence, not by confidence) applied to incoming tasks, to audit findings, to the agent's edits of its own instructions, and to the choice of what gets automated at all — the edit-your-own-instructions case is the riskiest, because the thing being changed is the controlling text itself, and loop-selection is the instinct turned upstream: it asks which work should reach an autonomous loop before any of the other gates get a say. And the context budget is the audit's instinct (notice drift before it bites) pointed at the one resource every other pattern spends. The scaffold-as-hypothesis gate is that same audit instinct again, pointed inward at the workspace's own additions: the self-edit gate (Pattern 10) certifies a change to the instructions, and the reasoning-regression suite certifies a change to the capability layer — both refuse to adopt on the strength of how good the change sounds. Pattern 13 turns the same gate on a critic for unfinished thinking, and adds the twist the offline checks miss: an always-on aid erases its own control group, so it holds out a slice of live firings the way Pattern 11 holds out a case set.

Pattern 15 is Pattern 9's budget instinct meeting Pattern 11's trial discipline at the model ladder: measure the lane, register the hypothesis, and let the same instrument that motivated the change adjudicate it. Pattern 14 is that same route-by-consequence family turned on the coordinator itself, and it is the one place where the answer came back negative. The classify-then-act loop of Pattern 2 ran here for months and was retired, because discovery left authorization ambiguous and the unattended runtime failed silently. What replaced it moves authorization to the human, and the question channel onto the board the human already reads.

Pattern 16 is the audit instinct compressed to a single sentence. Where Pattern 8 measures the workspace periodically and Pattern 11 gates an addition on evidence, Pattern 16 asks the same question of every load-bearing claim at the moment it is written: what is this standing on, and would the reader be able to tell if the answer were nothing. It pairs with Pattern 5 the way a citation pairs with a library: 5 keeps the source of truth singular and pointed-at, while 16 makes each individual assertion say which source it came from and how far it is from one. The two failure modes it addresses are the same failure at different distances: memory that quietly contradicts its source, and a sentence that quietly contradicts the file it claims to describe.

Pattern 17 completes a family that runs through 5, 9 and 16. Pattern 5 keeps memory pointing rather than mirroring; 17 does the same for the instruction surface, where the cost is paid on every session rather than every recall. Pattern 9 measures what that surface costs; 17 removes the part of the cost that buys nothing, because a duplicated rule spends context twice and can contradict itself. And 16 is the same discipline at sentence scale: cite where a claim comes from rather than restating it from memory. The through-line is one idea at four sizes: a fact should exist once, be referenced from everywhere it applies, and carry a visible route back to its source.

Adopt them when you feel the friction each one removes. Not before.

---

*Last verified against the repo structure on 2026-08-26.*
