"""
Build a local email -> user ID cache from CHEP 2026 Indico paper data.

Extracts all unique users (submitters, judges, reviewers, commenters) from
the papers assignment export and merges them into users.json. Run this
periodically to pick up new participants.

Usage:
    python3 build_user_cache.py
"""
import json
import requests

with open("indico_token.json") as f:
    TOKEN = json.load(f)["chep_read_token"]
with open("config.json") as f:
    _cfg = json.load(f)

BASE = _cfg["base_url"]
EVENT_ID = _cfg["event_id"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

try:
    with open("users.json") as f:
        existing = json.load(f)
except FileNotFoundError:
    existing = {}

users = dict(existing)

print("Fetching paper data from Indico...")
data = requests.get(
    f"{BASE}/event/{EVENT_ID}/manage/papers/assignment-list/export-json",
    headers=HEADERS,
).json()

for paper in data["papers"]:
    for rev in paper["revisions"]:
        candidates = (
            [rev.get("judge"), rev.get("submitter")]
            + [r["user"] for r in rev.get("reviews", [])]
            + [c["user"] for c in rev.get("comments", [])]
        )
        for u in candidates:
            if u and u.get("email") and u.get("id"):
                users[u["email"].lower()] = {
                    "id": u["id"],
                    "full_name": u.get("full_name", ""),
                }

after = len(users)
with open("users.json", "w") as f:
    json.dump(users, f, indent=2, sort_keys=True)

print(f"Done — {after} users cached ({after - len(existing)} new), saved to users.json")
