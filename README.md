# CHEP 2026 Paper Assignment Scripts

> **These scripts have moved to https://github.com/davidlange6/chep_indico_scripts**



Two scripts for assigning judges and content reviewers to CHEP 2026 paper submissions via the Indico API.

## Prerequisites

- Python 3 with `requests` installed
- `indico_token.json` in the working directory containing a write-capable Indico personal API token:
  ```json
  { "chep_write_token": "indp_..." }
  ```
- The token must be created at https://indico.cern.ch/user/tokens/ with the **"Everything (all methods)"** scope

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

### `assign_judge.py`

Assigns one or more judges to one or more paper submissions.

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

Assigns one or more content reviewers to one or more paper submissions. Identical interface to `assign_judge.py`.

```
python3 assign_reviewer.py <friendly_id> [<friendly_id> ...] --email <email> [<email> ...]
```

## User cache (`users.json`)

The assignment scripts resolve email addresses to Indico user IDs using a local cache (`users.json`) seeded from known event participants. For a pre-built cache, ask David for guidance.

To build or update the cache from the live Indico data, run `build_user_cache.py` (requires the `chep_read_token` personal API token):

```bash
python3 build_user_cache.py
```

## How it works

Both scripts:

1. Load `users.json` (email → user ID) as a baseline, then augment it live from the Indico papers assignment export
2. Resolve the supplied friendly IDs to internal contribution IDs via the same export
3. POST to the Indico paper assignment endpoint for each (paper, user) combination

The email → user ID mapping relies on the local cache and live paper participants rather than a user search API, since the Indico user search endpoint requires a different authentication context not accessible via personal API tokens.

## Notes

- Friendly IDs are the small sequential numbers shown in the CHEP paper management UI (e.g. 690), not the large internal contribution IDs.
- The scripts exit with an error if any supplied paper number or email address cannot be resolved.
- Assigning the same person twice to the same paper is a no-op on the Indico side (returns success).
- Both scripts read the event ID and base URL from `config.json`. Edit that file to use with a different event or Indico instance.
