# IMPLEMENTATION.md — Proven wiring + porting guide

## A. Hermes wiring (live, proven 2026-10-27)

### Components

| Piece | Where |
|---|---|
| Umbrella rule | user memory profile (compact, always loaded) |
| Methodology skill | `~/.hermes/skills/proactive-work/SKILL.md` (full spec + pitfalls) |
| Workspace | `~/.hermes/proactive/` — journal, proposals, open_threads, watch_config |
| Detector | `~/.hermes/scripts/dot_watch.py` |
| Secondary | cron job (`cronjob_manage`), schedule `every 30m`, `monitor: dot_watch.py`, `enabled_toolsets: [file, terminal]`, `continuity: true`, `skills: [proactive-work]`, deliver: origin chat |

### Scheduler specifics that mattered

- **monitor field** = change detector: script runs each tick, output hashed as exact bytes; unchanged → agent run suppressed (silent tick, $0); changed → `MONITOR CHANGE DETECTED` diff injected into the agent prompt. First tick always runs (baseline).
- **`enabled_toolsets: [file, terminal]`** is the real read-only leash: the secondary has no messaging/posting/network-write toolsets at all — prohibitions are backed by missing tools, not just instructions.
- **`continuity: true`** lets each pass see the previous pass's output → dedupe, no repeat proposals for the same change.
- **Deliver = human's own chat.** The digest is the only outbound channel.
- Kill switch: `cronjob_manage action=pause job_id=…` (one call).

### Pitfalls hit (fix them in your port)

1. **Monitor script path must be relative** to the scripts dir (`dot_watch.py`, not `~/.hermes/scripts/dot_watch.py`) — absolute paths rejected.
2. **Self-wake loop**: the secondary appends to journal.md — journal must NOT be in the watched set. Our watched set: skills dir, memories dir, open_threads.md. Writable set: journal.md, proposals.md. Disjoint by construction.
3. **Deterministic digest or pay-per-tick**: dir scans sort entries and hash `path:size:mtime`; file scans hash content. Any nondeterminism (timestamps, map order) makes every tick "changed".
4. Skill frontmatter descriptions >~57 chars get truncated in the routing index — keep the trigger line short, put detail in the body.

### Test protocol (run this on any install before trusting it)

```bash
python3 dot_watch.py                     # → "baseline established"
python3 dot_watch.py                     # → (empty)  quiet confirmed
echo test >> watched_file                # mutate something watched
python3 dot_watch.py                     # → "CHANGED <path> -> <digest>"
python3 dot_watch.py                     # → (empty)  quiet again
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
