# Samples

Adopter-reference content illustrating each layer described in [META_ARCHITECTURE.md](../META_ARCHITECTURE.md). Two tiers:

1. **Minimal scaffold.** Three worked files for a 5-step adoption. Start here if you want to build.
2. **Full library.** A broader snapshot of a real working workspace (roles, skills, agents, scheduled tasks, Python helpers). Browse when you want concrete implementations to fork.

All paths use generic placeholders (`<workspace>`, `<home>`, `<project-*>`). Substitute your own.

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
│   ├── accountant.md                 # tax / deductions / compliance (Australian-flavoured; adopt or localise)
│   ├── backend-developer.md
│   ├── bookkeeper.md
│   ├── data-engineer.md
│   ├── developmental-editor.md       # diagnostic creative-writing reviewer
│   ├── developmental-reviser.md      # voice-preserving revision writer
│   ├── frontend-developer.md
│   ├── health-data-analyst.md
│   ├── learning-strategist.md
│   ├── llm-engineer.md
│   ├── nutritionist.md
│   ├── platform-engineer.md
│   ├── product-thinker.md
│   ├── researcher.md                 # evidence-based investigator with fabrication guards
│   ├── security-auditor.md
│   ├── tester.md
│   └── wealth-manager.md
│
├── .claude/
│   ├── settings.example.json         # hook configuration (PreToolUse + PostToolUse + SessionStart)
│   │
│   ├── skills/                       # invokable workspace skills
│   │   ├── orient/SKILL.md           # session-start briefing
│   │   ├── wrap/SKILL.md             # task close-out ritual (updates registries)
│   │   ├── tasks/SKILL.md            # task-queue readout
│   │   ├── terse-mode/SKILL.md       # session-long output compression
│   │   ├── verify-completion/SKILL.md
│   │   ├── systematic-debugging/SKILL.md
│   │   └── role-pressure-test/SKILL.md
│   │
│   ├── agents/                       # workspace custom subagents
│   │   ├── audit.md                  # weekly upgrade auditor (Phase 1–3 setup review)
│   │   ├── heartbeat.md              # 2-hourly project manager
│   │   └── researcher.md             # auto-routed evidence-based investigator
│   │
│   └── scheduled-tasks/              # SKILL.md files fired by OS-level scheduler
│       ├── morning-brief/SKILL.md    # daily email + receipt + bill + appointment + news orchestrator
│       ├── consolidate-memory/SKILL.md
│       ├── heartbeat-monitor/SKILL.md
│       └── upgrade-audit/SKILL.md
│
├── scripts/                          # Python + PowerShell helpers
│   ├── ai_news.py                    # RSS/Atom fetcher + SQLite dedup (AI-news section)
│   ├── memory_lint.py                # path-reference validator for the memory system
│   ├── email_rules.py                # YAML-based email-triage rules engine
│   ├── receipts_pipeline.py          # receipt ingestion → FY workbook
│   ├── bill_tracker.py               # bill matcher + variance alerts
│   ├── appointments.py               # calendar-event formatter + dedup token
│   ├── send_self_email.py            # narrow self-send SMTP helper (morning brief only)
│   ├── run-scheduled-skill.ps1       # OS-scheduler wrapper that pipes SKILL.md → `claude --print`
│   ├── backup-restic.ps1             # encrypted incremental backup to object storage
│   └── restic-verify.ps1             # backup integrity + restore round-trip
│
└── tasks/                            # task-coordination layer
    ├── README.md                     # how the coordination layer works
    ├── To-Do-Notes.example.md        # sample master task list
    └── HEARTBEAT.md                  # heartbeat agent operational instructions
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
- [`.claude/skills/`](.claude/skills/): **7 workspace skills** for session management, output discipline, and verification.
- [`.claude/agents/`](.claude/agents/): **3 custom subagents**: a periodic setup auditor, a task-queue project manager, and an auto-routed researcher.
- [`.claude/scheduled-tasks/`](.claude/scheduled-tasks/): **4 SKILL.md files** fired by OS-level scheduler (Windows Task Scheduler / cron / launchd) via the `run-scheduled-skill.ps1` wrapper. The `morning-brief/SKILL.md` shows the full daily-orchestrator pattern (email triage → receipt capture → bill matching → appointment extraction → news → compose + deliver).
- [`scripts/`](scripts/): **10 helpers** consumed by the scheduled tasks. Each is standalone, stdlib-first where possible.

## Notes on redactions

- Concrete project names substituted with placeholders (`<project-platform>`, `<project-finance>`, `<project-health>`, `<project-creative>`, etc.).
- Personal identifiers, emails, locations, vendor relationships generalised.
- Data files (actual email rules, actual services registry, actual task content) are **not** shipped; only the schemas and code that consume them.
- Some domain-flavoured content remains (Australian tax terms in `accountant.md`, Brisbane-shaped weather fetch in `morning-brief/SKILL.md`). Treat these as templates to localise.

## Adoption path

See the root [ADOPTION.md](../ADOPTION.md) for the 5-step walkthrough.
