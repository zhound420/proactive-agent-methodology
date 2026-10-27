#!/usr/bin/env python3
"""Secondary-agent change detector (dots-style). Deterministic digest:
no change -> empty stdout -> monitor skips the agent run entirely.
change -> prints changed-file lines -> wakes the secondary agent pass.

Workspace location: PROACTIVE_HOME env var (default ~/.hermes/proactive).
Requires <workspace>/watch_config.json to exist — created by the human/primary,
never auto-generated (nothing gets watched without human approval)."""
import hashlib
import json
import os
import subprocess

HOME = os.path.expanduser("~")
WORK = os.environ.get("PROACTIVE_HOME", os.path.join(HOME, ".hermes/proactive"))
CONFIG = os.path.join(WORK, "watch_config.json")
SNAPSHOT = os.path.join(WORK, ".watch_snapshot.json")
MAX_DETAIL = 10


def sha(data):
    if isinstance(data, str):
        data = data.encode("utf-8", "replace")
    return hashlib.sha256(data).hexdigest()[:12]


def scan_file(path):
    try:
        with open(path, "rb") as f:
            return sha(f.read())
    except OSError:
        return "gone"


def scan_dir(path):
    """Content-hashed per file (no same-second mtime blind spot)."""
    details = {}
    for root, _dirs, files in os.walk(path):
        for name in files:
            if name.startswith("."):
                continue
            fp = os.path.join(root, name)
            details[fp] = scan_file(fp)
    agg = sha("\n".join(f"{k}:{v}" for k, v in sorted(details.items())))
    return agg, details


def scan_repo(path):
    try:
        head = subprocess.run(
            ["git", "-C", path, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        status = subprocess.run(
            ["git", "-C", path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=10).stdout
        return f"repo:{head}:{sha(status)}", {}
    except Exception:
        return "repo:unavailable", {}


def scan(path):
    if os.path.isdir(path):
        if os.path.exists(os.path.join(path, ".git")):
            return scan_repo(path)
        return scan_dir(path)
    d = scan_file(path)
    return d, {path: d}


def main():
    if not os.path.isfile(CONFIG):
        print(f"NO CONFIG at {CONFIG} — create watch_config.json (see reference/templates.md); nothing is watched yet")
        return

    with open(CONFIG) as f:
        cfg = json.load(f)

    state, detail = {}, {}
    for p in cfg.get("repos", []) + cfg.get("dirs", []) + cfg.get("files", []):
        digest, details = scan(p)
        state[p] = digest
        if details:
            detail[p] = details

    old = {}
    if os.path.exists(SNAPSHOT):
        with open(SNAPSHOT) as f:
            old = json.load(f)
    old_state = old.get("state", old)  # tolerate v1 flat snapshots once
    old_detail = old.get("detail", {})

    changed = sorted(k for k in state if old_state.get(k) != state[k])
    removed = sorted(k for k in old_state if k not in state)

    with open(SNAPSHOT, "w") as f:
        json.dump({"state": state, "detail": detail}, f, indent=2, sort_keys=True)

    if not old:
        print("baseline established")
        return
    for k in changed:
        tag = "NEW" if k not in old_state else "CHANGED"
        print(f"{tag} {k} -> {state[k]}")
        # name the changed files inside watched dirs, so wakes stay scoped
        prev, cur = old_detail.get(k, {}), detail.get(k, {})
        if prev and cur:
            mods = sorted(p for p in set(prev) & set(cur) if prev[p] != cur[p])
            adds = sorted(set(cur) - set(prev))
            dels = sorted(set(prev) - set(cur))
            for p in mods[:MAX_DETAIL]:
                print(f"  modified: {p}")
            for p in adds[:MAX_DETAIL]:
                print(f"  added: {p}")
            for p in dels[:MAX_DETAIL]:
                print(f"  removed: {p}")
    for k in removed:
        print(f"REMOVED {k}")


if __name__ == "__main__":
    main()
