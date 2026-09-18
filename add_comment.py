"""
Add a comment to one or more CHEP 2026 paper submissions.

Usage:
    python3 add_comment.py <friendly_id> [<friendly_id> ...] --comment "Your comment text"
                           [--visibility {contributors,reviewers,judges}]

Visibility options (default: contributors):
    contributors  Visible to contributors, reviewers, and judges
    reviewers     Visible to reviewers and judges only
    judges        Visible to judges only

Examples:
    python3 add_comment.py 690 77 --comment "Please address reviewer feedback before resubmitting."
    python3 add_comment.py 690 --comment "Internal note." --visibility judges
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


def load_contrib_map():
    data = requests.get(
        f"{BASE}/event/{EVENT_ID}/manage/papers/assignment-list/export-json",
        headers=HEADERS,
    ).json()
    return {p["contribution"]["friendly_id"]: p["contribution"]["id"]
            for p in data["papers"]}


def post_comment(contrib_id, comment_text, visibility):
    url = f"{BASE}/event/{EVENT_ID}/papers/api/{contrib_id}/comment"
    r = requests.post(url, headers=HEADERS,
                      data={"comment": comment_text, "visibility": visibility})
    return r.status_code in (200, 204)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="+", type=int,
                        metavar="FRIENDLY_ID", help="Paper number(s)")
    parser.add_argument("--comment", required=True,
                        help="Comment text to post")
    parser.add_argument("--visibility", default="contributors",
                        choices=["contributors", "reviewers", "judges"],
                        help="Comment visibility (default: contributors)")
    args = parser.parse_args()

    print("Loading paper data from Indico...")
    friendly_to_contrib = load_contrib_map()

    contrib_ids = []
    for fid in args.ids:
        if fid not in friendly_to_contrib:
            print(f"ERROR: paper #{fid} not found", file=sys.stderr)
            sys.exit(1)
        contrib_ids.append((fid, friendly_to_contrib[fid]))

    papers_str = ", ".join(f"#{fid}" for fid, _ in contrib_ids)
    print(f"Posting comment [{args.visibility}] to paper(s) [{papers_str}]...")
    failed = False
    for fid, contrib_id in contrib_ids:
        ok = post_comment(contrib_id, args.comment, args.visibility)
        status = "OK" if ok else "FAILED"
        print(f"  #{fid} (contrib {contrib_id}): {status}")
        if not ok:
            failed = True
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
