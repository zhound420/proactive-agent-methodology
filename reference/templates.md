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
Rules: never add anything the secondary writes (journal/proposals). Add git repo roots as they appear; add connector-backed poller outputs (not the connectors themselves) when apps are linked.

## dot_watch.py
See [`dot_watch.py`](dot_watch.py) — tested reference implementation (stdlib only, portable). Exit output contract: first run `baseline established`; no change → empty stdout; change → one `CHANGED/NEW/REMOVED <path> -> <digest>` line per path.
