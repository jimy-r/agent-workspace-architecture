# Attribution

The patterns in this repo were not invented here. They were borrowed, adapted, and combined from the repos below. Credit where it's due, and a useful reading list for anyone going deeper on any of these ideas.

## Governance and contribution patterns

| Pattern | Borrowed from |
|---|---|
| Ops-mode vs dev-mode separation, citation system, confidence ladder, freshness footers, Conventional Commits | A peer's internal data-analytics project (private) |
| Curated-list PR-contract style, scope-gating language in PR template | [sindresorhus/awesome](https://github.com/sindresorhus/awesome) |
| Path-based auto-labeller, PR-size labeller, lock-closed workflow, issue-form YAML style, multi-link `contact_links` | [mdn/content](https://github.com/mdn/content) |
| Structured label taxonomy (prefix system), deflection-links in `contact_links` | [rust-lang/rust](https://github.com/rust-lang/rust) |
| Path-specific `CODEOWNERS` pattern, `SUPPORT.md` as traffic router | [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes) |
| Minimal curated-list discipline (scripts folder, link validation, README-as-product) | [public-apis/public-apis](https://github.com/public-apis/public-apis) |

## Claude-Code-specific patterns

| Pattern | Borrowed from |
|---|---|
| `verify-completion` skill, `systematic-debugging` skill, rationalization-resistant role design, CSO skill descriptions, SDD review-gate templates, anti-sycophancy section | [obra/superpowers](https://github.com/obra/superpowers) |
| Sample validation workflow pattern, auto-categorised release notes via label matching, Dependabot-for-Actions setup, PR-size disciplines | [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) |
| Production-quality subagent layout, `plugin.json`/`marketplace.json` validation ideas | [wshobson/agents](https://github.com/wshobson/agents) |
| Role-as-first-class-object, CONTEXT.md binding pattern, repo shape | Reviewed [antfu/skills](https://github.com/antfu/skills), [wshobson/commands](https://github.com/wshobson/commands), [jqueryscript/awesome-claude-code](https://github.com/jqueryscript/awesome-claude-code) |

## Audit-system patterns

The weekly upgrade-audit (`samples/.claude/agents/audit.md`) and its supporting tooling map onto established public industry patterns. When extending or tuning a phase, return to these sources rather than reinventing.

| Pattern | Borrowed from |
|---|---|
| *Continual holistic fitness function*: multi-phase periodic audit with tiered remediation | Ford, Parsons, Kua, Sadalage, [*Building Evolutionary Architectures*](https://www.oreilly.com/library/view/building-evolutionary-architectures/9781491986356/ch02.html) (O'Reilly, 2nd ed. 2023). Concrete code-level analogues: [ArchUnit](https://www.archunit.org/) (Java), [NetArchTest](https://github.com/BenMorris/NetArchTest) (.NET), jQAssistant (graph-based, Neo4j). |
| *Scorecard per catalog entry*: per-project health dimensions producing pass/fail signals (Phase 2) | [Backstage Soundcheck](https://backstage.spotify.com/plugins/soundcheck/) (Spotify). |
| *Drift detection*: compare declared state to actual state, surface delta (Phase 2.5a MCP/plugin bloat) | [Terraform drift detection](https://developer.hashicorp.com/terraform/tutorials/cloud/drift-and-policy), [driftctl](https://github.com/snyk/driftctl), AWS Config Rules. |
| *Tiered automated-vs-human evidence collection*: Tier 1/2/3 auto-apply | [Vanta SOC2](https://www.vanta.com/products/soc-2) (1,200+ hourly tests), [Drata](https://drata.com/compliance) (80% evidence automation). |
| *Atomic security checks* (Phase 2.6) | [OpenSSF Scorecard](https://scorecard.dev/) (18+ automated checks). **Deliberately do NOT emit a numeric audit score**: Goodhart's Law risk for a self-improving audit. |
| *Dead-man's-switch*: check whether a task *checked in*, not whether it failed | [Healthchecks.io](https://healthchecks.io/) pattern + Pont, *Patterns for Time-Triggered Embedded Systems* (2002). Self-hosted implementation: `samples/scripts/security/check_task_freshness.py`. |
| *Alert fatigue mitigation*: opposing-metric pair (find rate + accept rate); finding ledger w/ acceptance tracking | "Alert Fatigue in Security Operations Centres," [ACM Computing Surveys 2025 (DOI:10.1145/3723158)](https://dl.acm.org/doi/10.1145/3723158); Trend Micro SOC survey (51% overwhelmed, >25% time on false positives). Implementation: `samples/scripts/audit_ledger.py`. |
| *Goodhart's Law / metric gaming*: why no numeric audit score | Charles Goodhart (1975); [David Manheim on metric gaming](https://kpitree.co/guides/frameworks/goodharts-law); ["Goodhart's Law Is Now an AI Agent Problem"](https://tianpan.co/blog/2026-04-20-goodharts-law-ai-agents-eval-gaming) (TianPan.co, April 2026). |
| *Two-auditor pattern*: periodic independent second-opinion audit | Financial auditing convention; also Vanta/Drata's independent-third-party-assessment requirements. Implementation: `samples/.claude/agents/audit-second-opinion.md`. |
| *Memory drift vs staleness*: semantic drift is distinct from file-age staleness | [arxiv:2603.10062](https://arxiv.org/pdf/2602.22406) (March 2026), "Towards Autonomous Memory Agents"; [A-MEM](https://arxiv.org/abs/2502.12110) (Zettelkasten-style re-indexing); [Letta](https://docs.letta.com/) (production MemGPT, three-tier memory). |
| *Compliance test injections*: known-bad fixtures to verify the audit hasn't regressed | SOC2/security-testing practice. Implementation: `samples/tests/audit_canaries/`. |
| *Agent observability*: runtime layer (token usage, latency, error rates, traces) | [LangSmith](https://www.langchain.com/langsmith/observability), [Langfuse](https://langfuse.com/), Arize Phoenix. Inspires Phase 2.6b runtime health (lighter than full observability, scoped to log-artefact + MCP-probe checks). |
| *Eval-driven development for agents*: measuring agent quality with synthetic test harnesses | [DeepEval](https://www.confident-ai.com/), [Promptfoo](https://promptfoo.dev/), [UK AISI Inspect AI](https://inspect.aisi.org.uk/). Not yet implemented in the workspace; flagged as a future direction. |

Full research brief grounding these citations: [Reference/Research/2026-05-28_audit-upgrade-best-practices.md](https://github.com/jimy-r/agent-workspace-architecture/) (private workspace; the brief itself is not mirrored here, only the public-anchor sources).

## Frameworks and conventions

| Convention | Source |
|---|---|
| Code of Conduct | [Contributor Covenant 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) (by reference) |
| Commit message format | [Conventional Commits](https://www.conventionalcommits.org/) |
| Changelog format | [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/) |
| Docs quadrant framing | [Diátaxis](https://diataxis.fr/): tutorials / how-to / reference / explanation |
| Licensing clarity | [Choose an Open Source License](https://choosealicense.com/) (chose MIT) |

## Reuse policy

This repo's content is MIT-licensed, so borrow back freely. If you adapt patterns here into your own public artifact, a link back is appreciated but not required. The more people run variations of these patterns, the better the collective understanding gets.

---

*Last verified against the repo structure on **2026-05-30**.*
