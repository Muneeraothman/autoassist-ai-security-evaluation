# Test Harness

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python setup_test_users.py   # creates .session_state.json (gitignored)
python harness.py --dry-run  # confirms a full request/response cycle works
```

`setup_test_users.py` requires the real `autoassist` repo checked out as a
sibling directory (`../../autoassist`) with its local `docker compose`
stack running — see the top-level `README.md`'s "Reproducing the tests
locally" section. It never touches or needs the real account's password —
see the script's docstring for why.

## Running test cases

```bash
python harness.py --suite ../test-cases/03-cross-user-access.json
python harness.py --all   # every suite in test-cases/
```

Each case's full request/response is written to
`../results/<suite-name>/<case-id>.json`. `assessment` is deliberately left
as `"NEEDS_MANUAL_REVIEW"` by the harness itself — an automated heuristic
(`heuristic_check`) is a first-pass signal only (e.g. "does the reply
literally contain the other user's vehicle_id"), not a substitute for
actually reading the model's reply text, which is done by hand for every
case before it's recorded as pass/fail/partial in the phase results
writeups (`../results/phaseN-*.md`).

## Safety guards

- `setup_test_users.py` and `harness.py` both refuse to run against
  anything other than `localhost`/`127.0.0.1` (checked against
  `AUTOASSIST_BASE_URL`/the saved `base_url`, hostname-parsed, not just
  string-matched).
- Every request sends `User-Agent: AutoAssist-Security-Eval-Harness/1.0`
  and `X-Security-Eval: true` so this traffic is identifiable in any
  backend logs, separate from real usage.
- Denial-of-wallet cases (`06-denial-of-wallet.json`) are capped by the
  test-case file itself (`burst_count`, `target_word_count`) — the
  harness doesn't let a case exceed what's declared there, and those
  values were deliberately kept small (see that file's `cost_safety_note`)
  since `/api/chat` calls real, billed Bedrock APIs.

## Why two test accounts, and why user1 isn't a "real" login

See `setup_test_users.py`'s module docstring. Short version: user1 is the
real seeded local account (so hallucination tests have real grounded
data to probe), accessed via a locally-minted JWT rather than its actual
password; user2 is a brand-new, clearly-fake account created fresh by
this script purely to give the cross-user tests a second, genuinely
different `vehicle_id` to attempt to reach.
