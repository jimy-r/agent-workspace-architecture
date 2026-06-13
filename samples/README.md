# Samples

Adopter-reference content illustrating each layer described in [META_ARCHITECTURE.md](../META_ARCHITECTURE.md). Two tiers:

1. **Minimal scaffold.** Three worked files for a 5-step adoption. Start here if you want to build.
2. **Full library.** A broader snapshot of a real working workspace (roles, skills, agents, scheduled tasks, Python helpers). Browse when you want concrete implementations to fork.

All paths use generic placeholders (`<workspace>`, `<home>`, `<project>`). Substitute your own.

## Layout

```
samples/
├── CLAUDE.md.example                 # workspace-level always-loaded context
├── CONTEXT.md.example                # generic project CONTEXT.md template
├── example-project/                  # a project that consumes the role library
│   ├── CONTEXT.md                    # filled-in CONTEXT.md (counterpart to the template)
│   └── .claude/agents/
│       └── example-security.md       # thin binding: role + CONTEXT.md
│
├── roles/                            # 17 canonical role definitions + template + validator
│   ├── _template.md                  # role skeleton
│   ├── _validate.py                  # schema + binding validator
│   ├── accountant.md                 # tax / deductions / compliance (Australian-flavoured; localise)
│   ├── backend-developer.md … wealth-manager.md   (see the folder for the full set)
│
├── .claude/
│   ├── settings.example.json         # hook configuration (PreToolUse + PostToolUse + SessionStart)
│   │
│   ├── skills/                       # 9 invokable workspace skills
│   │   ├── orient/SKILL.md           # session-start briefing
│   │   ├── wrap/SKILL.md             # task close-out ritual (updates registries)
│   │   ├── tasks/SKILL.md            # task-queue readout
│   │   ├── review-queue/SKILL.md     # drain the heartbeat's built-work review queue
│   │   ├── audit-workthrough/SKILL.md# drain the audit's pending-findings ledger
│   │   ├── terse-mode/SKILL.md       # session-long output compression
│   │   ├── verify-completion/SKILL.md
│   │   ├── systematic-debugging/SKILL.md
│   │   └── role-pressure-test/SKILL.md
│   │
│   ├── agents/                       # 4 workspace custom subagents
│   │   ├── audit.md                  # weekly upgrade auditor (multi-phase setup review)
│   │   ├── audit-second-opinion.md   # quarterly independent second-opinion auditor
│   │   ├── heartbeat.md              # 2-hourly project manager
│   │   └── researcher.md             # auto-routed evidence-based investigator
│   │
│   └── scheduled-tasks/              # SKILL.md files fired by OS-level scheduler
│       ├── morning-brief/SKILL.md    # daily brief orchestrator
│       ├── consolidate-memory/SKILL.md
│       ├── heartbeat-monitor/SKILL.md
│       └── upgrade-audit/SKILL.md
│
├── scripts/                          # Python + PowerShell helpers
│   ├── ai_news.py                    # RSS/Atom fetcher + SQLite dedup
│   ├── appointments.py               # calendar-event formatter + dedup token
│   ├── audit-second-opinion.bat      # manual launcher for the second-opinion auditor
│   ├── audit_cost.py                 # per-audit-run token/duration tracker
│   ├── audit_ledger.py               # append-only finding ledger (emit/mark/stats)
│   ├── backup-restic.ps1             # encrypted incremental backup to object storage
│   ├── bill_tracker.py               # bill matcher + variance alerts
│   ├── email_rules.py                # YAML-based email-triage rules engine
│   ├── ghost_token_counter.py        # always-loaded-context baseline counter
│   ├── memory_lint.py                # path-reference validator for the memory system
│   ├── receipts_pipeline.py          # receipt ingestion → finance workbook
│   ├── restic-verify.ps1             # backup integrity + restore round-trip
│   ├── run-scheduled-skill.ps1       # OS-scheduler wrapper: gate → model map → claude --print
│   ├── send_self_email.py            # narrow self-send SMTP helper (the one audited exception)
│   ├── token_report.py               # daily spend telemetry (Token Budget module)
│   │
│   ├── audit_checks/
│   │   └── run_all.py                # coded audit assertions (checks-as-code)
│   ├── heartbeat/
│   │   ├── classify_task.py          # has-default / needs-intent / out-of-scope classifier
│   │   ├── check_rejections.py       # rejection-log grep + 3-strike circuit breaker
│   │   ├── create_staging.py         # worktree-or-folder sandbox selector (slug-validated)
│   │   ├── idle_observations.py      # idle-cycle local-pattern surfacing
│   │   ├── preflight_gate.py         # Stage-0 dirty-check gate (skip the LLM when nothing changed)
│   │   └── review_queue.py           # review-queue cap counter
│   └── security/
│       ├── check_bash_command.py     # PreToolUse Bash guard (protected paths + git safety + env-var hijacks)
│       └── check_task_freshness.py   # dead-man's switch over scheduled-task logs
│
├── tests/
│   └── audit_canaries/               # known-bad fixtures the audit must keep detecting
│
└── tasks/                            # task-coordination layer
    ├── README.md                     # how the coordination layer works
    ├── To-Do-Notes.example.md        # sample master task list
    ├── HEARTBEAT.md                  # heartbeat agent operational instructions
    ├── HEARTBEAT_REVIEWS.md          # review queue for sandbox-built work
    └── HEARTBEAT_REJECTIONS.md       # ADR-style rejection log the agent greps
```

## How to read these

### Start here (minimal scaffold, enough for 5-step adoption)

- [`CLAUDE.md.example`](CLAUDE.md.example): root-level context that Claude auto-loads.
- [`CONTEXT.md.example`](CONTEXT.md.example): blank project-entity template. Filled counterpart: [`example-project/CONTEXT.md`](example-project/CONTEXT.md).
- [`roles/_template.md`](roles/_template.md): role skeleton + fields.
- [`.claude/settings.example.json`](.claude/settings.example.json): hook configuration.
- [`.claude/skills/orient/SKILL.md`](.claude/skills/orient/SKILL.md): example skill.
- [`tasks/README.md`](tasks/README.md): async Q&A coordination layer.

Follow [`ADOPTION.md`](../ADOPTION.md); the 5-step walkthrough maps these samples to concrete setup steps.

### Full library (reference implementations, fork to adapt)

- [`roles/`](roles/): **17 canonical roles**. Each is pure (no entity facts), composed with a project `CONTEXT.md` via a thin binding in `<project>/.claude/agents/`. Domain-specific roles (e.g. `accountant.md` is Australian-CPA flavoured) may need localisation; treat as template.
- [`.claude/skills/`](.claude/skills/): **9 workspace skills** for session management, queue-draining (heartbeat reviews + audit findings), output discipline, and verification.
- [`.claude/agents/`](.claude/agents/): **4 custom subagents**: the weekly auditor, its quarterly second-opinion counterpart, a task-queue project manager, and an auto-routed researcher.
- [`.claude/scheduled-tasks/`](.claude/scheduled-tasks/): **4 SKILL.md files** fired by an OS-level scheduler (Windows Task Scheduler / cron / launchd) via the `run-scheduled-skill.ps1` wrapper — which since 2026-06-10 runs a deterministic preflight gate and a per-skill model map before any model is invoked. The `morning-brief/SKILL.md` shows the full daily-orchestrator pattern.
- [`scripts/`](scripts/): **~25 helpers** consumed by the scheduled tasks and the audit. Each is standalone, stdlib-first where possible. The newest cluster is the Token Budget module: `token_report.py` (spend telemetry), `heartbeat/preflight_gate.py` (spend avoidance), `audit_checks/run_all.py` (coded assertions).
- [`tests/audit_canaries/`](tests/audit_canaries/): the known-bad fixtures the audit must keep flagging — detection is asserted end-of-run, not by checking the fixtures exist.

## Notes on redactions

- Concrete project names substituted with placeholders (`<project>`, `example-project`).
- Personal identifiers, emails, locations, vendor relationships generalised.
- Data files (actual email rules, actual services registry, actual task content) are **not** shipped; only the schemas and code that consume them.
- Some domain-flavoured content remains (Australian tax terms in `accountant.md`, Brisbane-shaped weather fetch in `morning-brief/SKILL.md`). Treat these as templates to localise.

## Adoption path

See the root [ADOPTION.md](../ADOPTION.md) for the 5-step walkthrough.

---

*Last verified against the repo structure on **2026-06-10**.*
