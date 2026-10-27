# ARCHITECTURE.md — Design, threat model, failure modes

## The two-agent split

Mirrors what third-party analysis of dots observed (Geordie): every dot runs a **primary** agent that interacts with the user and a **secondary** that continuously runs in the background collecting data, plus short-lived subagents per task.

Here:

- **Primary** = the interactive conversational agent. Owns: approvals, execution, verification, memory updates, proposing permission promotions.
- **Secondary** = a scheduled background pass with (a) a **deterministic change detector** in front of it and (b) a leashed toolset behind it. Owns: reading, journaling, proposing, digesting.

The split is what makes "always-on" affordable: the detector ticks cheaply (no model), the model only wakes on real change.

## Monitor gating (the event-driven approximation)

Dots internally use persistent loops + event triggers ("a bug appears in Slack, dots immediately investigate"). Without a permanent daemon, the equivalent shape is:

```
scheduler tick (every N min, $0)
   → change-detector script runs (deterministic digest of watched state)
      → digest identical to last tick  → run suppressed entirely ($0)
      → digest changed                → agent wakes, diff injected into prompt
```

Requirements for the detector:
- **Deterministic output** — no timestamps, sorted keys, stable hashes — or every tick looks "changed" and you pay full price every tick.
- Empty/stable stdout must mean "sleep" in the scheduler semantics.
- Must watch only things the secondary **never writes** (see self-wake trap below).
- Should **name the changed files** inside watched surfaces (content-hashed dirs, capped detail) so the wake can stay scoped to the diff — a dir-level hash alone forces the agent to re-scan to find out what happened.
- Must **not auto-create its own watch config**: the watched set exists only because a human approved it; no config = watches nothing.

## Why not a true daemon?

Options ranked by cost/complexity:

1. **Monitor-gated cadence job** (this repo's default) — event-driven behavior, zero idle cost, survives restarts via the scheduler. Best default.
2. **Persistent watcher process** — real daemon, immediate wake on pattern match, but dies on reboot unless persisted and can't reason until it wakes the agent. Good for one or two high-value signals.
3. **Always-on reasoning loop** (true dot shape) — durable loop deciding its own next action. Highest cost and risk; the dots ecosystem's own incident reports (self-spawned subagents, unplanned token spend) are the warning label. Only build with explicit human sign-off, budgets, and a watchdog.

## Threat model

| Threat | Mitigation |
|---|---|
| **Prompt injection via watched content** (a watched file/page/webpage contains "instructions") | Watched content is data, never instructions. Secondary's prompt declares this. Journal entries quote-attribute, never obey. |
| **Self-wake loop** (secondary writes a watched file → wakes itself forever) | The secondary's writable set (journal, proposals) is disjoint from the watched set (config, threads, skills, memories, repos). Enforced by prohibition + the writable set being tiny. |
| **Self-noise loop** (primary constantly edits watched memories/skills → noisy gated wakes) | Expected churn, not findings: secondary logs one line, replies quiet, never proposes about self-edits. If gated wakes exceed ~10/day the surface set is too noisy — renegotiate surfaces/ceiling with the human. |
| **Scope creep / self-directed tasks** | Hard prohibitions § METHODOLOGY 2; scheduler entries are fixed prompts; secondary may not edit its own config or scheduler. No subagents. |
| **Token runaway** | Detector gate + "scope to the diff" rule + cadence caps + human-readable journal for audit. |
| **Unwanted consequential action** | Background runs physically lack the tools (toolset allowlist). Only the primary, in an interactive turn, after explicit approval, may act. |
| **Credential exposure** | Nothing in the watched set contains secrets; detectors record hashes/paths, never file bodies. |

## State files (the "activity view")

```
~/.hermes/proactive/          (or equivalent workspace)
├── journal.md        append-only findings log        [secondary writes, NOT watched]
├── proposals.md      proposal lifecycle ledger       [secondary writes, NOT watched]
├── open_threads.md   what matters right now          [human/primary write; watched]
├── watch_config.json watched repos/dirs/files        [human/primary write; watched]
└── .watch_snapshot.json  detector state              [detector only]
```

## Failure modes seen in the wild (dots ecosystem, Oct 2026)

- **300K+ tokens/day, 155 traces, zero prompts** (Geordie test): the secondary went full survey mode on an unconnected system — inventorying repos and data it hadn't been asked about. Countermeasure: scope-to-diff rule; the detector should watch a *chosen* surface, not "everything reachable".
- **Mistimed proactivity**: dots flagging a calendar conflict 3 minutes before it. Proactive timing needs tuning per event class; don't over-promise lead times.
- **Invisible subagents**: Geordie saw subagents spawn whose access grants were opaque to the user. Countermeasure: no background subagents at all (our rule), or every spawn journaled with its grants.
