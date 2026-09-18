"""
Issue a judgment on one or more CHEP 2026 paper submissions.

Usage:
    python3 judge_paper.py <friendly_id> [<friendly_id> ...]
                           --judgment {accept,reject,to_be_corrected}
                           [--comment "Optional comment for the submitter"]

The paper must be in 'submitted' state to accept a new judgment. The script
works for any event manager regardless of judge assignment.

Examples:
    python3 judge_paper.py 690 --judgment accept
    python3 judge_paper.py 77 --judgment to_be_corrected --comment "Please revise per guidelines."
    python3 judge_paper.py 77 449 --judgment reject --comment "Does not meet proceedings requirements."
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


def judge(contrib_id, judgment, comment):
    url = f"{BASE}/event/{EVENT_ID}/manage/papers/assignment-list/judge"
    r = requests.post(url, headers=HEADERS, data={
        "judgment": judgment,
        "contribution_id": str(contrib_id),
        "submitted": "1",
        "judgment_comment": comment,
    })
    return r.status_code == 200 and "filter_statistics" in r.text


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="+", type=int,
                        metavar="FRIENDLY_ID", help="Paper number(s)")
    parser.add_argument("--judgment", required=True,
                        choices=["accept", "reject", "to_be_corrected"],
                        help="Judgment to issue")
    parser.add_argument("--comment", default="",
                        help="Optional comment for the submitter")
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
    print(f"Issuing judgment '{args.judgment}' on paper(s) [{papers_str}]...")
    for fid, contrib_id in contrib_ids:
        ok = judge(contrib_id, args.judgment, args.comment)
        status = "OK" if ok else "FAILED"
        print(f"  #{fid} (contrib {contrib_id}): {status}")


if __name__ == "__main__":
    main()
