# Attribution

The patterns in this repo were not invented here. They were borrowed, adapted, and combined from the repos below. Credit where it's due — and a useful reading list for anyone going deeper on any of these ideas.

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

## Frameworks and conventions

| Convention | Source |
|---|---|
| Code of Conduct | [Contributor Covenant 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) (by reference) |
| Commit message format | [Conventional Commits](https://www.conventionalcommits.org/) |
| Changelog format | [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/) |
| Docs quadrant framing | [Diátaxis](https://diataxis.fr/) — tutorials / how-to / reference / explanation |
| Licensing clarity | [Choose an Open Source License](https://choosealicense.com/) (chose MIT) |

## Reuse policy

This repo's content is MIT-licensed — borrow back freely. If you adapt patterns here into your own public artifact, a link back is appreciated but not required. The more people run variations of these patterns, the better the collective understanding gets.

---

*Last verified against the repo structure on **2026-04-19**.*
