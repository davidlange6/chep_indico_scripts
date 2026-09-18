"""
Assign one or more judges to one or more CHEP 2026 paper submissions.

Usage:
    python3 assign_judge.py <friendly_id> [<friendly_id> ...] --email <email> [<email> ...]

Example:
    python3 assign_judge.py 690 77 --email david.lange@cern.ch joe@example.com
"""
import argparse
import json
import sys
import requests

with open("indico_token.json") as f:
    TOKEN = json.load(f)["chep_write_token"]
with open("config.json") as f:
    _cfg = json.load(f)

BASE = _cfg["base_url"]
EVENT_ID = _cfg["event_id"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def load_maps():
    data = requests.get(
        f"{BASE}/event/{EVENT_ID}/manage/papers/assignment-list/export-json",
        headers=HEADERS,
    ).json()

    friendly_to_contrib = {}
    email_to_user = {}

    # Seed from local cache if present
    try:
        with open("users.json") as f:
            for email, info in json.load(f).items():
                email_to_user[email] = info["id"]
    except FileNotFoundError:
        pass

    for paper in data["papers"]:
        c = paper["contribution"]
        friendly_to_contrib[c["friendly_id"]] = c["id"]
        for rev in paper["revisions"]:
            for u in (
                [rev.get("judge"), rev.get("submitter")]
                + [r["user"] for r in rev.get("reviews", [])]
                + [c2["user"] for c2 in rev.get("comments", [])]
            ):
                if u and u.get("email"):
                    email_to_user[u["email"].lower()] = u["id"]

    return friendly_to_contrib, email_to_user


def assign(role, contrib_ids, user_ids):
    url = f"{BASE}/event/{EVENT_ID}/manage/papers/assignment-list/assign/{role}"
    ok = []
    for contrib_id in contrib_ids:
        for user_id in user_ids:
            r = requests.post(url, headers=HEADERS,
                              data={"contribution_id": str(contrib_id),
                                    "user_id": str(user_id)})
            success = r.status_code == 200 and r.json().get("success")
            status = "OK" if success else f"FAILED ({r.status_code})"
            print(f"  contrib {contrib_id} / user {user_id}: {status}")
            if success:
                ok.append((contrib_id, user_id))
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="+", type=int,
                        metavar="FRIENDLY_ID", help="Paper number(s)")
    parser.add_argument("--email", nargs="+", required=True,
                        metavar="EMAIL", help="Email address(es) of judge(s)")
    args = parser.parse_args()

    print("Loading paper and user data from Indico...")
    friendly_to_contrib, email_to_user = load_maps()

    # Resolve friendly IDs
    contrib_ids = []
    for fid in args.ids:
        if fid not in friendly_to_contrib:
            print(f"ERROR: paper #{fid} not found", file=sys.stderr)
            sys.exit(1)
        contrib_ids.append(friendly_to_contrib[fid])

    # Resolve emails
    user_ids = []
    for email in args.email:
        uid = email_to_user.get(email.lower())
        if uid is None:
            print(f"ERROR: no user found for {email}. The user must already be "
                  f"participating in the event as a judge, reviewer, submitter, "
                  f"or commenter before they can be assigned via this script.",
                  file=sys.stderr)
            sys.exit(1)
        user_ids.append(uid)

    papers_str = ", ".join(f"#{fid}" for fid in args.ids)
    users_str  = ", ".join(args.email)
    print(f"Assigning judge(s) [{users_str}] to paper(s) [{papers_str}]...")
    assign("judge", contrib_ids, user_ids)


if __name__ == "__main__":
    main()
