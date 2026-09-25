# Teardowns

Written analyses of published agent architectures: what a design gets right, what it trades off, and what it conspicuously lacks, measured against the [eighteen patterns](../PATTERNS.md) this repository documents.

## Why teardowns

A pattern says what tends to work. A teardown shows the pattern meeting a real, published system built by someone else, and that meeting is where the interesting evidence lives. Which patterns show up independently, which are absent even in strong designs, and where a design makes a trade the patterns don't anticipate. Each page here is one such reading.

Subjects are found by [teardown-sweep](https://github.com/signal-sweep/signal-sweep/tree/main/modules/teardown_sweep), which ranks published architectures by how much a teardown would have to say. A system implementing several patterns while conspicuously lacking others beats one that matches everything or nothing.

## Ground rules

These are conditions for a page existing here, not style preferences.

1. **Published, credited work only.** The subject chose to publish; the teardown links back prominently and names what works before what doesn't.
2. **The artefact is the subject, never the author.** Critique the design and its trade-offs. No speculation about intent, skill, or effort.
3. **Proportionality.** A well-resourced published reference invites a different depth of scrutiny than a small personal project by an unknown author. Punch sideways or up.
4. **Never delivered to the subject's own space.** A teardown is published here and shared on neutral ground. It is never posted into the subject's repo, tracker, or forum. A private heads-up to the author is a courtesy worth considering; it is a judgment call, not a step.
5. **Verifiable claims.** Every observation cites the file or doc it reads from, at the revision read. If it can't be cited, it isn't claimed.

## Page conventions

One file per teardown: `YYYY-MM-DD-<subject-slug>.md`, opening with a header block:

```markdown
# Teardown: <subject name>

- **Subject:** <repo or publication URL>
- **Revision read:** <commit sha or date of the material>
- **Patterns present:** <numbers, e.g. 1, 7, 9>
- **Patterns absent worth noting:** <numbers>
- **Date:** YYYY-MM-DD
- **Status:** current | ageing | superseded  <!-- as at YYYY-MM-DD -->
- **Re-check by:** YYYY-MM-DD
- **Verified:** <date>, <N> citations re-read
- **Maintainer heads-up:** sent <date> / not sent (rule 4)
```

`Revision read` dates the source. `Status` and `Re-check by` date the reading, which is what a visitor a year later actually needs. A confidently-worded present-tense analysis of a subject that has since moved on looks identical to a current one. Set `Re-check by` to the read date plus six months, or plus three for a pre-1.0 or preview subject whose half-life the page itself describes. The date is load-bearing rather than decorative. `scripts/check_freshness.py` fails once a page passes it, and the remedy is to re-read the subject and restamp, or to mark the page `ageing` or `superseded` and say what replaced it.

`Verified` records the last pass in which the page's citations were re-read against the revision, with the count, so a restamp says what was checked and not only when. `Maintainer heads-up` records whether the private courtesy note in ground rule 4 went to the subject's author, and the date if it did. Under rule 4 that note stays a judgment call, not a step, so `not sent` is a complete answer. Both fields apply to new pages from now on. Existing pages are backfilled later.

Body structure, in order: **What it is** (two or three sentences, neutral) · **What works** (the strongest choices, credited) · **The trade-offs** (what the design pays for those choices) · **What's conspicuously absent** (patterns the design would benefit from, and why their absence shows) · **What this teaches** (what transfers to other workspaces, which is the reason the page exists) · **What changed here** (the concrete edit this reading produced in *this* workspace, cited to a commit, PR or CHANGELOG entry, or an explicit "nothing yet" with the reason).

Two more rules the pages hold to:

- **Every pattern number is a link.** In the header block and in the body, a pattern number resolves to its anchor in [`../PATTERNS.md`](../PATTERNS.md). A reader arriving from an aggregator lands mid-page and needs one click to the reasoning.
- **The last section is the action item.** A teardown that ends on an abstract lesson has no way of being wrong later. "What changed here" is the field that keeps the practice honest, and "nothing yet, and here is why" is a legitimate answer.

## Distribution

Pages here are the canonical copies. Sharing on aggregator venues (with each venue's own etiquette) is a manual act; teardown-sweep's `suggested_venues` field proposes where each subject's audience already is, and its ledger records where a finished teardown actually ran.

## What five readings show

Each page's header records its verdict against the [eighteen patterns](../PATTERNS.md). Read down a column for one subject, across a row for how one pattern fares in the wild. The table is generated from those headers by [`scripts/teardown_matrix.py`](../scripts/teardown_matrix.py) and checked in CI, so it cannot drift from the pages.

<!-- teardown-matrix:start -->
| Pattern | [12-Factor Agents](2026-08-27-12-factor-agents.md) | [herdr](2026-08-28-herdr.md) | [LifeOS](2026-08-28-lifeos.md) | [DeepSeek Harness](2026-09-05-deepseek-harness.md) | [GPT-RAG](2026-09-06-azure-gpt-rag.md) |
|---|---|---|---|---|---|
| [1. Pure roles](../PATTERNS.md#1-pure-roles-composed-with-project-facts) | ✓ | — | ✓ | ✓ | ~ |
| [2. Classify-then-act](../PATTERNS.md#2-classify-then-act-not-ask-then-wait) | ✓ | ~ | — | — | ~ |
| [3. Make silent failure loud](../PATTERNS.md#3-make-silent-failure-loud-the-dead-mans-switch) | ✗ | ✗ | ✗ | ✓ | ~ |
| [4. Tier by mechanical impact](../PATTERNS.md#4-tier-by-mechanical-impact-not-by-tone) | — | — | — | ✓ | ✓ |
| [5. Memory points](../PATTERNS.md#5-memory-points-it-doesnt-mirror) | ✗ | — | — | ✗ | ~ |
| [6. Credentials live in one place](../PATTERNS.md#6-credentials-live-in-one-place-never-in-files) | ✗ | — | — | ✓ | ✓ |
| [7. A cheap hook beats a careful agent](../PATTERNS.md#7-a-cheap-hook-beats-a-careful-agent) | ✗ | — | ✓ | ✓ | ✓ |
| [8. Audit the workspace like a fitness function](../PATTERNS.md#8-audit-the-workspace-like-a-fitness-function) | ✗ | ✗ | — | ~ | ~ |
| [9. Context is a budget](../PATTERNS.md#9-context-is-a-budget-not-a-constant) | ✓ | ✗ | ✗ | ✓ | ~ |
| [10. A skill is editable weights](../PATTERNS.md#10-a-skill-is-editable-weights--never-adopt-a-self-edit-without-a-gate) | — | — | — | ~ | ~ |
| [11. A scaffold is a hypothesis](../PATTERNS.md#11-a-scaffold-is-a-hypothesis--gate-it-behind-a-measurable-signal) | ✗ | — | ✗ | ✓ | ✓ |
| [12. Loop selection](../PATTERNS.md#12-loop-selection-not-everything-should-be-a-loop) | ✓ | ✓ | — | ~ | ~ |
| [13. Challenge half-formed ideas with a different lens](../PATTERNS.md#13-challenge-half-formed-ideas-with-a-different-lens--and-hold-a-sample-back-to-prove-it-helps) | — | — | — | ✗ | ~ |
| [14. Delegation is a queue you fill](../PATTERNS.md#14-delegation-is-a-queue-you-fill-not-work-the-agent-finds) | — | ~ | — | ✗ | ~ |
| [15. Price the lane before you migrate it](../PATTERNS.md#15-price-the-lane-before-you-migrate-it) | — | — | — | ~ | ✗ |
| [16. A claim carries its provenance](../PATTERNS.md#16-a-claim-carries-its-provenance-or-it-is-a-guess) | ✗ | ✗ | ✗ | ✓ | ✓ |
| [17. One canonical copy](../PATTERNS.md#17-one-canonical-copy-and-pointers-from-everywhere-else) | ✓ | — | ~ | ✓ | ~ |
| [18. Position is price](../PATTERNS.md#18-position-is-price--a-token-costs-more-the-earlier-you-add-it) | — | — | — | ✓ | ~ |

✓ present · ~ partial · ✗ absent, and named as worth noting · — not assessed. Derived from each page's header by [`scripts/teardown_matrix.py`](../scripts/teardown_matrix.py). Edit the pages, not this table.

What each reading changed here, first line of its own answer:

| Reading | What changed here |
|---|---|
| [12-Factor Agents](2026-08-27-12-factor-agents.md) | No pattern changed, because every absence named above was already running in this workspace. |
| [herdr](2026-08-28-herdr.md) | none |
| [LifeOS](2026-08-28-lifeos.md) | none |
| [DeepSeek Harness](2026-09-05-deepseek-harness.md) | This repo gained a root [`AGENTS.md`](../AGENTS.md) on 2026-09-06, after this reading. |
| [GPT-RAG](2026-09-06-azure-gpt-rag.md) | Nothing at publication. |
<!-- teardown-matrix:end -->

Five readings, and no pattern is present in all five. Pure roles come closest, present in three subjects and partial in a fourth, and a cheap hook in the execution path is present in three of the four subjects where it was assessed. Six patterns are fully present in no subject, and they are the judgment and measurement patterns rather than the mechanical ones: the workspace audit, pointer memory, gated self-edits, the held-out divergent lens, the delegation queue and lane pricing. The two most recent subjects carry provenance on every claim and tier their gates by mechanical impact, and still have none of the six in full. The split that surprised most runs the other way. The dead man's switch, the cheapest control in the set, is absent from the three earlier subjects and named as worth noting on each, so the pattern most often missing is the one that costs an afternoon.

## Published

| Date | Subject | Revision read |
|---|---|---|
| 2026-09-05 | [DeepSeek Harness](2026-09-05-deepseek-harness.md) | `d347e703908d` |
| 2026-09-06 | [GPT-RAG](2026-09-06-azure-gpt-rag.md) | `76a8a4d6fd88` |
| 2026-08-28 | [herdr](2026-08-28-herdr.md) | `7b675f42af35` |
| 2026-08-28 | [LifeOS](2026-08-28-lifeos.md) | `ce046f26495c` |
| 2026-08-27 | [12-Factor Agents](2026-08-27-12-factor-agents.md) | `d20c728` |

## Disagree with a reading?

Say so in [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions) — that's the canonical Q&A home, and it is the right venue for a subject's maintainers too, since ground rule 4 keeps these pages out of anyone else's tracker. Corrections are appended to the page, dated. Factual errors can also go to [issues](https://github.com/jimy-r/agent-workspace-architecture/issues).

---

*Patterns adapted to your stack: [jamesross.ai](https://jamesross.ai/?utm_source=github&utm_medium=teardown&utm_campaign=flagship) · New teardowns, patterns and tools ship irregularly: [Agent Workspaces](https://jimyr.substack.com) · The guided track over the patterns: [learn/](../learn/README.md)*
