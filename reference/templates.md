# reference templates

## journal.md
```markdown
# Journal
<!-- append-only. format: date + watch source, change, why it matters, evidence, action -->
```

## proposals.md
```markdown
# Proposals
<!-- format: date — title; Finding (+evidence); Proposed action; Status: NEEDS APPROVAL | DONE | REJECTED -->
```

## open_threads.md
```markdown
# Open threads
<!-- what matters right now; maintained by human + primary agent; WATCHED surface -->
- <thread>: <current state / what would count as a change worth noticing>
```

## watch_config.json
```json
{
  "repos": [],
  "dirs": ["/home/user/.hermes/skills", "/home/user/.hermes/memories"],
  "files": ["/home/user/.hermes/proactive/open_threads.md"]
}
```
Rules: the detector never creates this file — it defines the human-approved watched set, populate it only after that answer. Never add anything the secondary writes (journal/proposals). Add git repo roots as they appear; add connector-backed poller outputs (not the connectors themselves) when apps are linked. Expect memories/skills churn from the primary agent — that's self-noise (see ARCHITECTURE threat model), handled by the secondary's quiet-reply rule.

## dot_watch.py
See [`dot_watch.py`](dot_watch.py) — tested reference implementation (stdlib only). Workspace location via `PROACTIVE_HOME=<dir>` (default `~/.hermes/proactive`). Output contract: no config → single "NO CONFIG" line (watches nothing); first run `baseline established`; no change → empty stdout; change → one `CHANGED/NEW/REMOVED <path> -> <digest>` line per surface plus `modified:/added:/removed:` lines naming changed files inside watched dirs (cap 10 each). Dir digests are content-hashes (no same-second mtime blind spot).
