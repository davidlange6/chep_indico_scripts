"""
List all comments on CHEP 2026 paper submissions made in the last N days.

Usage:
    python3 list_comments.py [--days N] [--id ID [ID ...]]
                             [--judge EMAIL] [--reviewer EMAIL]
                             [--mine]

Filters (combinable):
    --id       Only show comments on these paper friendly IDs
    --judge    Only show comments on papers where EMAIL is a judge
    --reviewer Only show comments on papers where EMAIL is a reviewer
    --mine     Only show comments on papers where you (token owner) are
               assigned as judge or reviewer

Examples:
    python3 list_comments.py                      # last 7 days, all papers
    python3 list_comments.py --days 2             # last 48 hours
    python3 list_comments.py --mine               # papers assigned to me
    python3 list_comments.py --id 77 449 690      # specific papers
    python3 list_comments.py --judge david.lange@cern.ch
"""
import argparse
import json
import requests
from datetime import datetime, timedelta, timezone

with open("indico_token.json") as f:
    TOKEN = json.load(f)["chep_read_token"]
with open("config.json") as f:
    _cfg = json.load(f)

BASE = _cfg["base_url"]
EVENT_ID = _cfg["event_id"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def get_my_user_id():
    r = requests.get(f"{BASE}/api/user/", headers=HEADERS)
    return r.json()["id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=float, default=7,
                        help="Show comments from the last N days (default: 7)")
    parser.add_argument("--id", nargs="+", type=int, metavar="ID",
                        help="Only show comments on these paper IDs")
    parser.add_argument("--judge", metavar="EMAIL",
                        help="Only papers where EMAIL is a judge")
    parser.add_argument("--reviewer", metavar="EMAIL",
                        help="Only papers where EMAIL is a reviewer")
    parser.add_argument("--mine", action="store_true",
                        help="Only papers where you are assigned as judge or reviewer")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)

    my_id = get_my_user_id() if args.mine else None

    print("Fetching paper data from Indico...")
    data = requests.get(
        f"{BASE}/event/{EVENT_ID}/manage/papers/assignment-list/export-json",
        headers=HEADERS,
    ).json()

    results = []
    for paper in data["papers"]:
        contrib = paper["contribution"]
        fid = contrib["friendly_id"]

        if args.id and fid not in args.id:
            continue

        if not paper["revisions"]:
            continue
        last_rev = max(paper["revisions"], key=lambda r: r["number"])

        if args.judge:
            judge = last_rev.get("judge")
            if not judge or judge.get("email", "").lower() != args.judge.lower():
                continue

        if args.reviewer:
            reviewers = [r["user"].get("email", "").lower()
                         for r in last_rev.get("reviews", [])]
            if args.reviewer.lower() not in reviewers:
                continue

        if args.mine:
            judge = last_rev.get("judge")
            reviewer_ids = [r["user"].get("id") for r in last_rev.get("reviews", [])]
            judge_id = judge.get("id") if judge else None
            if my_id not in reviewer_ids and my_id != judge_id:
                continue

        for rev in paper["revisions"]:
            for comment in rev["comments"]:
                dt = datetime.fromisoformat(comment["created_dt"])
                if dt >= cutoff:
                    results.append({
                        "dt": dt,
                        "paper_id": fid,
                        "title": contrib["title"],
                        "revision": rev["number"],
                        "author": comment["user"]["full_name"],
                        "visibility": comment["visibility"]["title"],
                        "text": comment["text"],
                    })

    results.sort(key=lambda r: r["dt"])

    if not results:
        print(f"No comments found matching the given criteria.")
        return

    print(f"\n{len(results)} comment(s) in the last {args.days} day(s):\n")
    print("=" * 72)
    for r in results:
        print(f"[{r['dt'].strftime('%Y-%m-%d %H:%M UTC')}]  "
              f"Paper #{r['paper_id']} rev {r['revision']}  —  {r['author']}")
        print(f"  {BASE}/event/{EVENT_ID}/papers/{r['paper_id']}/")
        print(f"  Visibility: {r['visibility']}")
        print(f"  {r['title']}")
        print()
        for line in r["text"].splitlines():
            print(f"    {line}")
        print("=" * 72)


if __name__ == "__main__":
    main()
