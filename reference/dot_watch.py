#!/usr/bin/env python3
"""Secondary-agent change detector (dots-style). Deterministic digest:
no change -> empty stdout -> monitor skips the agent run entirely.
change -> prints diff lines -> wakes the secondary agent pass."""
import hashlib
import json
import os
import subprocess

HOME = os.path.expanduser("~")
PROACTIVE = os.path.join(HOME, ".hermes/proactive")
CONFIG = os.path.join(PROACTIVE, "watch_config.json")
SNAPSHOT = os.path.join(PROACTIVE, ".watch_snapshot.json")

DEFAULT_CONFIG = {
    "repos": [],
    "dirs": [
        os.path.join(HOME, ".hermes/skills"),
        os.path.join(HOME, ".hermes/memories"),
    ],
    "files": [
        os.path.join(PROACTIVE, "open_threads.md"),
    ],
}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def scan_file(path):
    try:
        with open(path, "rb") as f:
            return "f:" + sha(f.read().decode("utf-8", "replace"))
    except OSError:
        return "gone"


def scan_dir(path):
    parts = []
    for root, _dirs, files in os.walk(path):
        for name in files:
            if name.startswith("."):
                continue
            fp = os.path.join(root, name)
            try:
                st = os.stat(fp)
                parts.append(f"{fp}:{st.st_size}:{int(st.st_mtime)}")
            except OSError:
                pass
    return "d:" + sha("\n".join(sorted(parts)))


def scan_repo(path):
    try:
        head = subprocess.run(
            ["git", "-C", path, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        status = subprocess.run(
            ["git", "-C", path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=10).stdout
        return f"repo:{head}:{sha(status)}"
    except Exception:
        return "repo:unavailable"


def main():
    if not os.path.exists(CONFIG):
        os.makedirs(PROACTIVE, exist_ok=True)
        with open(CONFIG, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
    with open(CONFIG) as f:
        cfg = json.load(f)

    state = {}
    for p in cfg.get("repos", []):
        state[p] = scan_repo(p)
    for p in cfg.get("dirs", []):
        if os.path.isdir(p):
            state[p] = scan_dir(p)
    for p in cfg.get("files", []):
        if os.path.isfile(p):
            state[p] = scan_file(p)

    old = {}
    if os.path.exists(SNAPSHOT):
        with open(SNAPSHOT) as f:
            old = json.load(f)

    changed = sorted(k for k in state if old.get(k) != state[k])
    removed = sorted(k for k in old if k not in state)

    with open(SNAPSHOT, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)

    if not old:
        print("baseline established")
        return
    for k in changed:
        tag = "NEW" if k not in old else "CHANGED"
        print(f"{tag} {k} -> {state[k]}")
    for k in removed:
        print(f"REMOVED {k}")


if __name__ == "__main__":
    main()
