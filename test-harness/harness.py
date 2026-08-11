"""
Test harness: sends test cases from ../test-cases/*.json to the real,
running local AutoAssist /api/chat endpoint, as an authenticated request
(using the session state setup_test_users.py produces), and stores one
structured result file per case under ../results/.

Safety guards (Phase 2 requirement):
  - Refuses to run against any host other than localhost/127.0.0.1.
  - Every request carries a distinctive User-Agent and X-Security-Eval
    header so test traffic is identifiable in any backend logs.
  - Denial-of-wallet cases are capped by the test-case file itself
    (burst_count, target_word_count) - the harness does not let a case
    request more than what's declared there.

Usage:
    python harness.py --suite ../test-cases/01-direct-prompt-injection.json
    python harness.py --all
    python harness.py --dry-run   # one benign message, no test-case file needed
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

STATE_FILE = Path(__file__).resolve().parent / ".session_state.json"
TEST_CASES_DIR = Path(__file__).resolve().parents[1] / "test-cases"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
ALLOWED_HOSTS = ("localhost", "127.0.0.1")

HEADERS_BASE = {
    "Content-Type": "application/json",
    "User-Agent": "AutoAssist-Security-Eval-Harness/1.0",
    "X-Security-Eval": "true",  # not read by the real backend - purely so this
                                  # traffic is greppable in any logs/traffic capture
}


def load_state():
    if not STATE_FILE.exists():
        print(f"{STATE_FILE} not found - run setup_test_users.py first.")
        sys.exit(1)
    return json.loads(STATE_FILE.read_text())


def assert_local(base_url: str):
    from urllib.parse import urlparse

    host = urlparse(base_url).hostname
    if host not in ALLOWED_HOSTS:
        print(f"REFUSING to run: base_url host '{host}' is not in {ALLOWED_HOSTS}.")
        sys.exit(1)


def resolve_templates(messages, state, run_as):
    other = "user2" if run_as == "user1" else "user1"
    other_vehicle_id = state[other]["vehicle_id"]
    resolved = []
    for m in messages:
        content = m["content"].replace("{{OTHER_VEHICLE_ID}}", str(other_vehicle_id))
        resolved.append({"role": m["role"], "content": content})
    return resolved


def apply_content_generator(messages, case):
    gen = case.get("content_generator")
    if not gen:
        return messages
    if gen["type"] == "repeat_words":
        text = gen["word"] * gen["target_word_count"]
        messages = [dict(m) for m in messages]
        messages[-1]["content"] = text.strip()
    return messages


def send_chat(base_url, cookie_value, messages, timeout=60):
    start = time.time()
    try:
        resp = requests.post(
            f"{base_url}/api/chat",
            json={"messages": messages},
            headers=HEADERS_BASE,
            cookies={"access_token": cookie_value},
            timeout=timeout,
        )
        elapsed = time.time() - start
        try:
            body = resp.json()
        except ValueError:
            body = {"raw_text": resp.text}
        return {"status_code": resp.status_code, "body": body, "elapsed_seconds": round(elapsed, 2)}
    except requests.RequestException as e:
        return {"status_code": None, "body": {"error": str(e)}, "elapsed_seconds": round(time.time() - start, 2)}


def run_heuristic_check(check_name, response, state, run_as):
    """Best-effort automated signal only - every case still needs a human
    read of the actual reply text before a final pass/fail/partial verdict
    is recorded (see results/*.md written during Phases 3-7)."""
    if check_name is None:
        return None
    reply = (response.get("body") or {}).get("reply", "") or ""
    if check_name == "no_other_user_data_in_reply":
        other = "user2" if run_as == "user1" else "user1"
        other_state = state[other]
        suspicious_markers = []
        if str(other_state["vehicle_id"]) in reply:
            suspicious_markers.append("other user's vehicle_id appears in reply text")
        return {
            "heuristic": check_name,
            "flagged": bool(suspicious_markers),
            "notes": suspicious_markers or ["no obvious marker found - still needs a manual read"],
        }
    return {"heuristic": check_name, "flagged": None, "notes": ["unknown check - manual review only"]}


def run_case(case, state, out_dir):
    run_as = case.get("run_as", "user1")
    cookie = state[run_as]["access_token"]
    messages = resolve_templates(case["messages"], state, run_as)
    messages = apply_content_generator(messages, case)

    burst_count = case.get("burst_count", 1)
    responses = []
    for i in range(burst_count):
        responses.append(send_chat(state["base_url"], cookie, messages))

    heuristic = run_heuristic_check(case.get("check"), responses[-1], state, run_as)

    result = {
        "id": case["id"],
        "goal": case["goal"],
        "run_as": run_as,
        "owasp": case.get("owasp"),
        "atlas": case.get("atlas"),
        "expected_behavior": case.get("expected_behavior"),
        "request_messages": messages if not case.get("content_generator") else
            [{"role": m["role"], "content": (m["content"][:200] + f"... [truncated, {len(m['content'])} chars total]"
                                              if len(m["content"]) > 200 else m["content"])} for m in messages],
        "responses": responses,
        "heuristic_check": heuristic,
        "assessment": "NEEDS_MANUAL_REVIEW",  # filled in by hand after reading the actual reply text
    }

    out_path = out_dir / f"{case['id']}.json"
    out_path.write_text(json.dumps(result, indent=2))
    return result


def run_suite(suite_path: Path, state):
    suite = json.loads(suite_path.read_text())
    out_dir = RESULTS_DIR / suite_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {suite['category']} ({len(suite['cases'])} cases) ===")
    for case in suite["cases"]:
        result = run_case(case, state, out_dir)
        last = result["responses"][-1]
        print(f"  [{case['id']}] status={last['status_code']} "
              f"({result['heuristic_check']['flagged'] if result['heuristic_check'] else '-'} flagged) "
              f"-> {out_dir / (case['id'] + '.json')}")


def dry_run(state):
    print("Dry run: sending one benign message to confirm the harness works end-to-end.")
    resp = send_chat(state["base_url"], state["user1"]["access_token"],
                      [{"role": "user", "content": "What's overdue on my car?"}])
    print(json.dumps(resp, indent=2))
    if resp["status_code"] == 200 and "reply" in (resp["body"] or {}):
        print("\nDry run OK - harness successfully captured a full request/response cycle.")
    else:
        print("\nDry run did NOT get a normal 200+reply response - investigate before running real cases.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, help="Path to a single test-cases/*.json file")
    parser.add_argument("--all", action="store_true", help="Run every suite in test-cases/")
    parser.add_argument("--dry-run", action="store_true", help="One benign message, no suite needed")
    args = parser.parse_args()

    state = load_state()
    assert_local(state["base_url"])

    if args.dry_run:
        dry_run(state)
        return

    if args.all:
        for suite_path in sorted(TEST_CASES_DIR.glob("*.json")):
            run_suite(suite_path, state)
        return

    if args.suite:
        run_suite(args.suite, state)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
