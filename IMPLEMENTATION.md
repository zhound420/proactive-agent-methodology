# IMPLEMENTATION.md — Proven wiring + porting guide

## A. Hermes wiring (live, proven 2026-10-27)

### Components

| Piece | Where |
|---|---|
| Umbrella rule | user memory profile (compact, always loaded) |
| Methodology skill | `~/.hermes/skills/proactive-work/SKILL.md` (full spec + pitfalls) |
| Workspace | `~/.hermes/proactive/` — journal, proposals, open_threads, watch_config |
| Detector | `~/.hermes/scripts/dot_watch.py` |
| Secondary | cron job (`cronjob_manage`), schedule `every 30m`, `monitor: dot_watch.py`, `enabled_toolsets: [file]` (no shell, no messaging), `continuity: true`, `skills: [proactive-work]`, deliver: origin chat |

### Scheduler specifics that mattered

- **monitor field** = change detector: script runs each tick, output hashed as exact bytes; unchanged → agent run suppressed (silent tick, $0); changed → `MONITOR CHANGE DETECTED` diff injected into the agent prompt. First tick always runs (baseline).
- **`enabled_toolsets: [file]`** — no messaging, no network, no shell. This is the tightest leash the platform gives, and it is what the *rules* should be backed by: prohibitions mostly correspond to missing tools. **Honest residual:** the file toolset can still write anywhere on disk, so write *scope* (journal/proposals only) is instructed + audited via the journal, not enforced. An independent fresh-agent audit caught an earlier version of this doc overstating the leash as fully enforced — if you port this, drop every shell/network toolset and disclose the residual to your human before enabling.
- **`continuity: true`** lets each pass see the previous pass's output → dedupe, no repeat proposals for the same change.
- **Deliver = human's own chat.** The digest is the only outbound channel. **Quiet runs must deliver nothing:** Hermes suppresses delivery when the final response is `[SILENT]` (whole response or own first/last line; `NO_REPLY` variants also recognized). If your platform lacks a silence convention, fall back to a one-line 'quiet' digest and tell your human that's a fallback, not a feature.
- Kill switch: `cronjob_manage action=pause job_id=…` (one call).

### Pitfalls hit (fix them in your port)

1. **Monitor script path must be relative** to the scripts dir (`dot_watch.py`, not `~/.hermes/scripts/dot_watch.py`) — absolute paths rejected.
2. **Self-wake loop**: the secondary appends to journal.md — journal must NOT be in the watched set. Our watched set: skills dir, memories dir, open_threads.md. Writable set: journal.md, proposals.md. Disjoint by construction.
3. **Deterministic digest or pay-per-tick**: dir scans sort entries and content-hash every file (`path:sha(content)`); file scans hash content. Any nondeterminism (timestamps, map order) makes every tick "changed". Content hashing also kills the same-second/same-size mtime blind spot.
4. Skill frontmatter descriptions >~57 chars get truncated in the routing index — keep the trigger line short, put detail in the body.
5. **Self-noise:** watched memories/skills dirs are written constantly by the *primary* (memory updates, skill edits). Gated wakes from these are expected churn, not findings — the secondary prompt must reply quiet with one logged line and never propose about them. If gated wakes exceed ~10/day, the surface set is too noisy: renegotiate surfaces/ceiling with the human.
6. **Workspace relocation:** `dot_watch.py` takes `PROACTIVE_HOME=<dir>`; without it defaults to `~/.hermes/proactive`. The watcher never auto-creates a watch config — an empty/no-config workspace watches nothing until a human-approved `watch_config.json` exists.

### Test protocol (run this on any install before trusting it)

Test on **scratch surfaces only** — human surface-confirmation governs *production* surfaces; this test watches nothing but throwaway temp files:

```bash
S=/tmp/pw_test; mkdir -p $S/watched
echo '{"repos":[],"dirs":["'$S'/watched"],"files":[]}' > $S/watch_config.json
echo "# scratch" > $S/watched/scratch.md
PROACTIVE_HOME=$S python3 dot_watch.py             # → "baseline established"
PROACTIVE_HOME=$S python3 dot_watch.py             # → (empty)  quiet confirmed
echo "mutation $(date +%s%N)" >> $S/watched/scratch.md
PROACTIVE_HOME=$S python3 dot_watch.py             # → CHANGED + "modified: …/scratch.md"
PROACTIVE_HOME=$S python3 dot_watch.py             # → (empty)  quiet again
rm -rf $S
```

## B. Porting to other agent frameworks

The methodology is framework-agnostic; only the scheduling + toolset-leash mechanism swaps:

| Concept | Hermes (here) | Generic equivalents |
|---|---|---|
| Cadence tick | cron job | any scheduler: cron, systemd timer, task queue, loop in a persistent process |
| Change gate | `monitor` field | pre-step script; skip model call if digest unchanged |
| Read-only leash | toolset allowlist | tool whitelist / permission profile / sandboxed policy config |
| Human gate | approval in chat turn | any interactive channel; approval must be human-originated |
| Activity view | journal/proposals md files | any append-only log + ledger |
| Rule persistence (memory/skill store) | user memory profile + skills dir | any store that auto-loads at every session start — verify by re-reading it back, not by remembering you added it |
| Blacklist / Custom Rules | proposals.md + memory profile | append-only ledger, queried before every new proposal |
| Kill switch | pause job | disable scheduler entry / SIGTERM daemon |

### Port checklist

- [ ] Memory/skill rule loaded (three buckets + hard prohibitions) — verify it survives restart
- [ ] Workspace files created; watched set ∩ writable set = ∅
- [ ] Detector installed and passes the 4-step test above
- [ ] Secondary scheduled behind the gate, narrowest possible toolset
- [ ] Digest delivers to the human's channel only
- [ ] Proposal lifecycle wired: approval → execute → verify-by-readback → mark DONE
- [ ] Human confirmed surface + cadence explicitly before first enable
- [ ] Kill switch rehearsed once (pause, verify silence, resume)
