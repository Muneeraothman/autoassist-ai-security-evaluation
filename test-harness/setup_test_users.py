"""
Phase 2 setup: establishes the two isolated test identities the harness
runs cases as.

- "user1" = the real, already-seeded local dev account (id=2,
  muneera0615@gmail.com) that owns the real seeded 2002 Lexus (vehicle_id
  2) with real schedule/service/manual data - needed so hallucination
  tests (07-hallucination.json) have real grounded data to be tested
  against, and so this review is testing the actual data shape, not an
  empty fixture.
- "user2" = a brand-new, clearly-fake account created here, purely so
  cross-user tests (03-cross-user-access.json) have a second real
  vehicle_id that user1 must never be able to reach.

We deliberately do NOT ask for or use user1's real password. Instead this
script mints a JWT locally using the same JWT_SECRET_KEY the running
backend already trusts (read from ../../autoassist/backend/.env, a local
dev-only file, never printed or committed) - functionally "log in as the
known local test user id" without ever touching a real credential. This
keeps the eval fully decoupled from the project owner's actual login,
which is the safer property for a security-testing tool to have anyway.

Never run this against anything but a local dev instance - see the
BASE_URL safety check below.
"""

import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import dotenv_values
from jose import jwt

BASE_URL = os.environ.get("AUTOASSIST_BASE_URL", "http://localhost:8000")
ALLOWED_HOSTS = ("localhost", "127.0.0.1")

AUTOASSIST_BACKEND_ENV = Path(__file__).resolve().parents[2] / "autoassist" / "backend" / ".env"
STATE_FILE = Path(__file__).resolve().parent / ".session_state.json"

SEEDED_USER1_ID = 2  # the real, already-seeded local account (see docstring)
SEEDED_USER1_VEHICLE_ID = 2  # the real seeded 2002 Lexus ES300

USER2_EMAIL = "security-eval-user2@example.test"  # clearly-fake, local-only test account
JWT_ALGORITHM = "HS256"


def _assert_local_target():
    from urllib.parse import urlparse

    host = urlparse(BASE_URL).hostname
    if host not in ALLOWED_HOSTS:
        print(f"REFUSING to run: BASE_URL host '{host}' is not in {ALLOWED_HOSTS}.")
        print("This harness is only for the local dev instance. Aborting.")
        sys.exit(1)


def _mint_user1_cookie() -> str:
    if not AUTOASSIST_BACKEND_ENV.exists():
        print(f"Could not find {AUTOASSIST_BACKEND_ENV} - is the real autoassist repo")
        print("checked out as a sibling directory? Aborting.")
        sys.exit(1)

    env = dotenv_values(AUTOASSIST_BACKEND_ENV)
    secret = env.get("JWT_SECRET_KEY")
    if not secret:
        print("JWT_SECRET_KEY not found in backend/.env - aborting.")
        sys.exit(1)

    expire = datetime.now(timezone.utc) + timedelta(days=7)
    token = jwt.encode({"sub": str(SEEDED_USER1_ID), "exp": expire}, secret, algorithm=JWT_ALGORITHM)
    # secret goes out of scope here and is never printed/logged/returned
    return token


def _register_user2() -> requests.Session:
    session = requests.Session()
    password = secrets.token_urlsafe(24)  # random, never reused, never needs to be remembered

    resp = session.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": USER2_EMAIL, "password": password},
        headers={"User-Agent": "AutoAssist-Security-Eval-Harness/1.0 (setup)"},
        timeout=10,
    )

    if resp.status_code == 409:
        # Already exists from a prior run of this script - log in instead.
        resp = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": USER2_EMAIL, "password": "UNKNOWN"},
            timeout=10,
        )
        if resp.status_code != 200:
            print(
                "user2 test account already exists from a prior run but this script "
                "doesn't have its (randomly-generated) password. Delete it manually "
                "(psql: DELETE FROM users WHERE email = "
                f"'{USER2_EMAIL}') and re-run."
            )
            sys.exit(1)
    elif resp.status_code != 201:
        print(f"Unexpected response registering user2: {resp.status_code} {resp.text}")
        sys.exit(1)

    user2_id = resp.json()["id"]
    return session, user2_id


def _create_user2_vehicle(session: requests.Session) -> int:
    resp = session.post(
        f"{BASE_URL}/api/vehicles",
        json={
            "make": "Toyota",
            "model": "Camry",
            "year": 2018,
            "vin": None,
            "current_mileage": 42000,
        },
        headers={"User-Agent": "AutoAssist-Security-Eval-Harness/1.0 (setup)"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def main():
    _assert_local_target()

    print(f"Target: {BASE_URL} (confirmed local)")

    user1_token = _mint_user1_cookie()
    print(f"user1: minted session for seeded account id={SEEDED_USER1_ID}, "
          f"vehicle_id={SEEDED_USER1_VEHICLE_ID}")

    session2, user2_id = _register_user2()
    user2_vehicle_id = _create_user2_vehicle(session2)
    user2_token = session2.cookies.get("access_token")
    print(f"user2: created fresh test account id={user2_id} ({USER2_EMAIL}), "
          f"vehicle_id={user2_vehicle_id}")

    state = {
        "base_url": BASE_URL,
        "user1": {
            "user_id": SEEDED_USER1_ID,
            "vehicle_id": SEEDED_USER1_VEHICLE_ID,
            "access_token": user1_token,
            "note": "real seeded account, JWT minted locally - see module docstring",
        },
        "user2": {
            "user_id": user2_id,
            "vehicle_id": user2_vehicle_id,
            "access_token": user2_token,
            "email": USER2_EMAIL,
            "note": "fresh account created by this script, safe to delete/recreate anytime",
        },
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))
    print(f"\nWrote session state to {STATE_FILE} (gitignored - contains live session tokens)")


if __name__ == "__main__":
    main()
