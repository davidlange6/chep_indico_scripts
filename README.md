# CHEP 2026 Paper Assignment Scripts

> **These scripts have moved to https://github.com/davidlange6/chep_indico_scripts**



Two scripts for assigning judges and content reviewers to CHEP 2026 paper submissions via the Indico API.

## Prerequisites

- Python 3 with `requests` installed
- `indico_token.json` in the working directory with the following format:
  ```json
  {
    "chep_read_token":  "indp_...",
    "chep_write_token": "indp_..."
  }
  ```
  Tokens are created at https://indico.cern.ch/user/tokens/. You can use a single token with the write scope for both keys if preferred.

  | Key | Used by | Required scope |
  |---|---|---|
  | `chep_read_token` | `list_comments.py`, `build_user_cache.py` | Everything (only GET) |
  | `chep_write_token` | `assign_judge.py`, `assign_reviewer.py`, `add_comment.py` | Everything (all methods) |

## Scripts

### `list_comments.py`

Lists all comments made in the last N days, with optional filters.

```
python3 list_comments.py [--days N] [--id ID [ID ...]]
                         [--judge EMAIL] [--reviewer EMAIL] [--mine]
```

**Examples:**

```bash
# All comments in the last 7 days (default)
python3 list_comments.py

# Last 48 hours
python3 list_comments.py --days 2

# Papers where you are assigned as judge or reviewer
python3 list_comments.py --mine

# Specific papers only
python3 list_comments.py --id 77 449 690

# Papers assigned to a specific judge
python3 list_comments.py --judge david.lange@cern.ch
```

### `add_comment.py`

Posts a comment to one or more paper submissions.

```
python3 add_comment.py <friendly_id> [<friendly_id> ...] --comment "Your comment text"
```

**Examples:**

```bash
# Comment on one paper
python3 add_comment.py 690 --comment "Please address reviewer feedback before resubmitting."

# Comment on multiple papers at once
python3 add_comment.py 690 77 42 --comment "Reminder: deadline is October 1."
```

### `judge_paper.py`

Issues a judgment on one or more paper submissions. Works for event managers regardless of judge assignment.

```
python3 judge_paper.py <friendly_id> [<friendly_id> ...]
                       --judgment {accept,reject,to_be_corrected}
                       [--comment "Optional comment for the submitter"]
```

The paper must be in `submitted` state to accept a new judgment.

**Examples:**

```bash
python3 judge_paper.py 690 --judgment accept
python3 judge_paper.py 77 --judgment to_be_corrected --comment "Please revise per guidelines."
python3 judge_paper.py 77 449 --judgment reject --comment "Does not meet proceedings requirements."
```

### `assign_judge.py`

Assigns one or more judges to one or more paper submissions. Requires `users.json` (see [User cache](#user-cache-usersjson) below).

```
python3 assign_judge.py <friendly_id> [<friendly_id> ...] --email <email> [<email> ...]
```

**Examples:**

```bash
# Assign one judge to one paper
python3 assign_judge.py 690 --email david.lange@cern.ch

# Assign one judge to multiple papers
python3 assign_judge.py 690 77 42 --email david.lange@cern.ch

# Assign multiple judges to multiple papers (all combinations)
python3 assign_judge.py 690 77 --email alice@cern.ch bob@cern.ch
```

### `assign_reviewer.py`

Assigns one or more content reviewers to one or more paper submissions. Identical interface to `assign_judge.py`. Also requires `users.json`.

```
python3 assign_reviewer.py <friendly_id> [<friendly_id> ...] --email <email> [<email> ...]
```

## User cache (`users.json`)

The assignment scripts resolve email addresses to Indico user IDs using `users.json`. On each run they load the cache as a baseline, augment it with participants found in the live papers export, and save it back — so the cache grows automatically over time. If an email address cannot be resolved from either source, the script exits with an error.

`users.json` is optional: it will be created on the first successful run. A pre-built cache covering all abstract submitters gives broader coverage from the start; ask David for guidance on obtaining one.

To build or update the cache from the live Indico data, run `build_user_cache.py`:

```bash
python3 build_user_cache.py
```

## Notes

- Friendly IDs are the small sequential numbers shown in the CHEP paper management UI (e.g. 690), not the large internal contribution IDs.
- The scripts exit with an error if any supplied paper number or email address cannot be resolved.
- Assigning the same person twice to the same paper is a no-op on the Indico side (returns success).
- Both scripts read the event ID and base URL from `config.json`. Edit that file to use with a different event or Indico instance.
