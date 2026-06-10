# Changelog

Human-written record of notable changes — the *why* and the *shape*, not every merged PR. Milestone batches get a tagged release with short notes (from `v1.0.0`, 2026-06-11); entries are grouped by date, newest first. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), adapted to a dated scheme.

## 2026-06-11

- **The README now opens with a 30-second animated pass through the tour.** A scripted recording (layers, modules, a pattern card, the task walkthrough) replaces the static screenshot and links through to the live page. Traffic was reaching the README without converting to the tour; a moving preview is the strongest nudge a README can make. Repo metadata tuned in the same pass: an `llm-orchestration` topic and a keyword-tuned description.
- **The repo now cuts tagged releases**, starting with `v1.0.0`. Milestone batches get a tag and short notes so watchers see changes in their feeds and the changelog gains stable anchors. The ritual lives in `CLAUDE.md`.
- **Tour fixes.** The build-section doc cards still said "eight decisions" after the ninth pattern landed (#57), and rendered their title and description run together (the same display bug #53 fixed for layer rows). Both corrected.

- **Ninth pattern: "Context is a budget, not a constant."** The Token Budget module arrived as a module row in the 2026-06-10 sync; this gives the thinking its `PATTERNS.md` entry (problem → pattern → why → cost, pointing at `ghost_token_counter.py` + `token_report.py` samples), adds the ninth card to the tour, and retires the "eight" count from the README, the tour button and heading, and the social-card description.

## 2026-06-10

- **Workspace-upgrade sync.** The source workspace's latest batch, mirrored in: a twelfth module — **Token Budget** (a deterministic preflight gate that skips no-op scheduled cycles, a model-tier policy for unattended work, daily spend telemetry feeding the audit's trend rule) — plus audit hardening: a coded assertion runner (`samples/scripts/audit_checks/run_all.py` — LLM re-derivation of checks had produced a false positive), canary verification rewritten to assert *detection* end-of-run rather than fixture presence, a provenance gate so externally-sourced findings never auto-apply, a ledger emit-count assertion, the full report relocated out of the task list, and a new `audit-workthrough` skill that drains pending findings. New samples: `preflight_gate.py`, `token_report.py`, the checks runner, and the workthrough skill; the scheduler-wrapper sample gained the gate + a per-skill model map; the tour gained the twelfth module; the samples README inventory corrected (it had drifted well behind the tree). Also fixes the one lychee failure from the consistency pass (a sample-settings link path).
- **Consistency pass across the reader-facing docs** (this entry's PR). META_ARCHITECTURE.md's first-screen "Last updated" paragraph had grown into a multi-thousand-word internal change log; its history now lives here and the header carries a short current summary. PATTERNS.md patterns are numbered and each now points at the sample files that implement it. Fixed: CONTRIBUTING's stale section references, SECURITY's workflow list (the required `redaction` check was missing from its own inventory), leftover `patterns-board` label references in two workflows, an arXiv citation whose text and link disagreed, and stale freshness footers.
- **Social-share pass** ([#53](https://github.com/jimy-r/agent-workspace-architecture/pull/53)). The tour gained `og:*` / `twitter:card` metadata, a 1200×630 social card (committed with its HTML source), a favicon, and a canonical link; the README gained a linked tour screenshot; a real CSS bug fixed (layer titles/subtitles rendered run-together). Repo topics expanded and the About homepage now points at the tour.
- **Residual private identifiers scrubbed** ([#52](https://github.com/jimy-r/agent-workspace-architecture/pull/52)). A full-tree denylist sweep found four pre-CI-gate leaks: an absolute machine path in a sample skill, a private project name in two sample files, and a changelog entry quoting private strategy material. The redaction CI gate scans PR-added lines only, so grandfathered content needs periodic full-tree sweeps.
- **Interactive tour at `docs/`, served via GitHub Pages** ([#49](https://github.com/jimy-r/agent-workspace-architecture/pull/49)). A single-file, dependency-free comprehension layer rendered as a *view* over the markdown sources: a clickable five-layer architecture model, the module grid, the eight patterns as expandable cards, and a six-step "task in motion" walkthrough. Exists because the repo communicated its artifacts better than its value. The same PR fixed a pre-existing leak: a public changelog line had quoted the redaction denylist's own strings while describing the redaction process.

## 2026-06-04

- **Audit external-opportunities source 6b** — a skills-only curated index (~300 entries, 13 categories) added to the weekly audit's Phase 2.5b sweep, alongside the broader awesome-list it complements.

## 2026-05-31

- **Writing-style rules propagated to writer roles and workspace agents.** Subagent prose still carried AI-writing tells because `CLAUDE.md` auto-loads in the main thread only — subagents see their own definition plus `@`-imported roles, nothing else. A reusable Writing Standards block went into 5 writer roles and 2 workspace agents; both `CLAUDE.md` files now state the rule covers subagent output (the main thread audits prose from built-ins that can't be configured). Lesson: workspace-wide behavior rules don't propagate to subagents; bake them into role and agent definitions in the same change.

## 2026-05-30

- **Repositioned as a curated solo showcase.** The repo had a split identity — half curated reference, half aspirational community hub with empty governance tables. The community machinery was stripped: `PATTERNS_BOARD.md` removed and its references scrubbed; README rewritten to lead with the architecture and a clear author attribution (James Ross, practice at jamesross.ai); `CLAUDE.md`, `CONTRIBUTING.md`, `SUPPORT.md` reframed; `STYLE_GUIDE.md` gained the author-attribution exception (public byline permitted; private identity stays redacted).
- **`PATTERNS.md` added** — the eight load-bearing patterns, each as *problem → pattern → why it beats the obvious alternative → cost*, now the README's recommended entry point.
- **Weekly audit run, 5 of 7 findings actioned in-session** — including validation of a bounded research workflow (rebuilt after a v1 over-fan exhausted a session's usage limit) and a memory-drift fix. Canaries 3/3.

## 2026-05-28

- **Repo renamed `claude-workspace-architecture` → `agent-workspace-architecture`.** The patterns port to any agent substrate; the worked example stays Claude Code. Old URL 301-redirects; all internal references updated; conceptual "Claude workspace" phrasing generalised to "agent workspace".
- **Audit-upgrade R1–R9 bundle.** Nine upgrades moved the weekly audit from config inspection to config + runtime + accuracy-tracked inspection: a dead-man's-switch for scheduled tasks (R1), runtime-health phase reading real log artifacts (R2), an append-only finding ledger (R3), synthetic canaries (R4), a mechanical-impact tier table replacing tone heuristics (R5), adaptive source weighting (R6), a second-opinion auditor with a deliberately different prompt (R7), a semantic-drift memory check (R8), and per-run cost tracking (R9). Deliberate non-decision: no numeric audit score (Goodhart). Bibliography in `ATTRIBUTION.md § Audit-system patterns`.
- **Weekly `auto-cleanup` workflow deleted** after 5 weeks of silent failure; its one successful run would have produced a ~1000-line aesthetic-only diff. Three stale dependabot PRs targeting it closed.

## 2026-05-27

- **`wrap` skill gained a post-settings-change verification step** — a permission or hook change isn't done until the next real fire confirms it (config-shape assumptions had silently broken scheduled tasks for days). Encoded as a discrete close-out step.
- **Audit governance retune** — the services-registry check stopped flagging cell-incompleteness that merely duplicates the password manager (point, don't mirror) and stopped flagging age-based credential rotation (NIST SP 800-63B: rotation only on an exposure trigger).

## 2026-05-26

- **Third-party command-safety plugin adopted** (MIT; source-verified before install) — semantic destructive-command interception complementing the in-house Bash hook. Interactive-CLI only; headless environments keep the in-house hooks as the floor. A hook being *configured* is not the same as *loaded* — verified by live fire.
- **PreCompact transcript-backup hook** — backs up the transcript before context compaction (pruned to last 5).
- **HTML-deliverable convention** — human-facing deliverables ship as self-contained HTML where visuals help; markdown stays source of truth for anything the model re-ingests.

## 2026-04-27

- **Containerised heartbeat shipped to runnable state.** The recurring agent runs on an internal-only Docker network with zero egress; an API-proxy sidecar straddles the internal network and an egress network, injecting the real auth header so no credential ever enters the agent container. Read-only workspace mounts, narrow per-file read-write, a pre-flight mount validator, boundary probes, and an `OBSERVATION.md` runbook convention for user-paced observation windows. Two Docker lessons captured: `internal: true` networks block host-gateway routing (sidecar is the fix), and Docker Desktop's host-gateway resolves to IPv6 from inside containers (listeners must dual-stack).

## 2026-04-24

- **Hygiene batch + five skills adopted from upstream.** Stale one-off permissions purged; two dead plugins disabled; an unused MCP server removed. New skills: `context-save` / `context-restore` (session checkpoints, from gstack), `health` (30-second composite score, read-only), `subagent-driven-development` and `dispatching-parallel-agents` (from obra/superpowers). Heartbeat and audit agent descriptions rewritten to match their actual scope.

## 2026-04-22

- **Heartbeat-as-PR-agent cutover.** Question-then-action became *classify-then-act*: every task classifies as `has-default` / `needs-intent` / `out-of-scope`; safe-by-default work builds speculatively in a sandbox and lands in a review queue; rejections append ADR-style records the agent greps before re-attempting (3 strikes force `needs-intent`). New primitives under `samples/scripts/heartbeat/`; new `review-queue` skill; the morning brief surfaces the queue.
- **Security envelope around the new flow.** A PreToolUse Bash hook closed the shell-level gap in file protection (write-verbs against protected paths, pushes to protected branches, force-pushes); HEARTBEAT.md gained rules capping the review queue and honouring a dry-run marker; staging-slug validation guards against branch-name collisions.
- **Idle-cycle observations** — when a cycle has no task-shaped work, the heartbeat surfaces cheap local patterns (rejection clusters, stale staging, stale memory, queue-batching opportunities) under a strict cap.

## 2026-04-21

- **Scheduled tasks actually fire now.** Every firing had been crashing before producing output: `LogonType: Interactive only` gives the Node-based CLI no console handle, and it dies on stdio before writing a byte. Fix: "Run whether user is logged on or not". The heartbeat-monitor task was registered the same day (it had never had a binding); the weekly audit stays deliberately manual.
- **Daily brief: newsletter HTML rendering + AI-news pool 3 → 10 feeds** — a section-aware inline-CSS renderer (zero dependencies) feeds multipart text+HTML self-delivery; per-source caps stop high-volume feeds monopolising the digest. The provider of the worked example has no public RSS; aggregators cover its announcements within hours.
- **Ghost-token baseline counter** — stdlib-only measurement of everything auto-loaded at session start, trended weekly by the audit; findings fire on >10% growth over the rolling median.
- **Trust-gradient auto-apply for audit findings** — Tier 1 (safe, silent) / Tier 2 (applied + prominently surfaced) / Tier 3 (approval required), with a 5-per-run rate limit, validator and recent-edit downgrades, and a reporting invariant after a first-run drift incident: every modified file must appear in the report.
- **`terse-mode` skill; archive splits** for the task-coordination files (open-blocks-only question file, todo archive) cutting ~80k characters from the always-loaded set; `link-check` workflow split into diff-only on PRs + weekly full sweep.
- **`samples/` grew 10 → 52 files** — all 17 roles, the workspace skills, 3 subagents, 4 scheduled tasks, and the helper scripts, each redacted through a staging script and grep-verified against the identifier denylist.

## 2026-04-20

- **OS-level Whisper dictation became the voice path everywhere** (desktop, phone, remote sessions); the planned custom voice-channel rebuild was retired — zero integration code beats one bespoke surface.
- **`researcher` canonical role + auto-routed workspace subagent** — evidence-based investigation with fabrication guards, two-axis source grading, and `[observed]`/`[inferred]`/`[unverified]` claim tags; research-shaped tasks route to it instead of `general-purpose`.
- **Memory architecture hardening** — `episodes/` split for one-off events, verification frontmatter on reference memories, a memory-lint path checker, and a weekly consolidation task holding the index under its ceiling. Four operations per fact: add, update, delete, no-op.
- **`Reference/Research/` convention** — durable research briefs with answer-first synthesis and mandatory appendices ("no brief without appendices").
- **OS-scheduler workaround documented** — a thin wrapper pipes a SKILL.md into the headless CLI, invoked by the OS scheduler, with timestamped logs.
- GitHub Actions version bumps via Dependabot (PRs #1–5).

## 2026-04-19

- **Gmail automation stack** — a daily orchestrator for triage, receipts, bills, appointments, and a self-emailed brief, on ~500 consumer-tagged rules. One narrow Iron-Law exception: a self-only SMTP sender hardcoded to the user's own address; everything else stays drafts-only.
- **Repo hardening in three passes** — link-check, stale, validate-samples, dependabot, release notes, code of conduct, AI-PR checklist, labels; then scope boundaries, commit conventions, freshness footers; then the labeller, PR template with inline examples, lock-closed workflow, `SUPPORT.md`, `STYLE_GUIDE.md`, prettier config.
- **Repo created** — initial redacted snapshot: README, META_ARCHITECTURE with Mermaid diagrams and `[stock]`/`[plugin]`/`[local]`/`[custom]` markers, MIT license, ADOPTION walkthrough, first samples scaffold.

---

*Last verified against the repo structure on **2026-06-10**.*
