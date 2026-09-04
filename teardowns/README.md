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
```

Body structure, in order: **What it is** (two or three sentences, neutral) · **What works** (the strongest choices, credited) · **The trade-offs** (what the design pays for those choices) · **What's conspicuously absent** (patterns the design would benefit from, and why their absence shows) · **What this teaches** (what transfers to other workspaces, which is the reason the page exists).

## Distribution

Pages here are the canonical copies. Sharing on aggregator venues (with each venue's own etiquette) is a manual act; teardown-sweep's `suggested_venues` field proposes where each subject's audience already is, and its ledger records where a finished teardown actually ran.

## Published

| Date | Subject | Revision read |
|---|---|---|
| 2026-09-05 | [DeepSeek Harness](2026-09-05-deepseek-harness.md) | `d347e703908d` |
| 2026-08-28 | [herdr](2026-08-28-herdr.md) | `7b675f42af35` |
| 2026-08-28 | [LifeOS](2026-08-28-lifeos.md) | `ce046f26495c` |
| 2026-08-27 | [12-Factor Agents](2026-08-27-12-factor-agents.md) | `d20c728` |
