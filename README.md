# AutoAssist AI Security Evaluation

A structured AI red-teaming exercise against the real **AutoAssist AI
Assistant** — the LLM-powered chat feature (Amazon Bedrock, Claude Sonnet
4.5, function calling + RAG) built into
[AutoAssist](https://github.com/Muneeraothman/autoassist), a full-stack
vehicle maintenance tracker. This is a separate, standalone deliverable
that extends that project with a formal security assessment, rather than
new app features.

**Status:** in progress — being built phase-by-phase per
`AUTOASSIST_AI_SECURITY_EVALUATION_BUILD_GUIDE.md`. See `SECURITY_ASSESSMENT.md`
for the full report (filled in as later phases complete) and
`architecture-notes/` for the factual basis every test and finding
references.

## Why this exists

To demonstrate the ability to both **build** and **security-test** an AI
system — designing realistic attack scenarios against a system's *actual*
tool definitions, system prompt, authorization logic, and RAG pipeline
(not a generic/imagined LLM app), executing them against a real running
instance, and turning the results into a professional security report
mapped to industry frameworks (OWASP Top 10 for LLM Applications, MITRE
ATLAS).

## Scope

**In scope:** the AI assistant's attack surface specifically — direct
prompt injection, indirect injection / RAG poisoning, cross-user data
access via the assistant, tool/parameter misuse, sensitive data leakage
via the assistant, denial-of-wallet via chat, and hallucination/ungrounded
advice.

**Out of scope (v1):** traditional web-app vulnerabilities unrelated to
the AI surface (SQL injection, XSS, CSRF, CORS misconfig in the core CRUD
app), physical/social engineering, testing against any real production
deployment with real user data, automated fuzzing at scale. See
`SECURITY_ASSESSMENT.md`'s methodology section for the full rationale.

## Environment tested

A local development instance of AutoAssist (`docker compose`), running
against a local Postgres+pgvector container with seeded test data — **not**
the project's occasionally-deployed AWS instance (which is destroyed
between work sessions and was confirmed not running at the time of this
review). The AI assistant itself calls real Amazon Bedrock APIs (Claude
Sonnet 4.5 + Titan Embeddings) even in local dev, since Bedrock isn't
mocked in this project — see `architecture-notes/01-system-overview.md`.

## Reproducing the tests locally

```bash
# 1. Have the real AutoAssist app running locally (see its own README):
#    cd ../autoassist && docker compose up --build

# 2. Set up this repo's test harness
cd test-harness
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Create the two isolated test accounts used by the cross-user tests
python setup_test_users.py

# 4. Run a given phase's test cases
python harness.py --suite test-cases/03-cross-user-access.json
```

Raw results land in `results/`, one file per test case, plus a per-phase
summary — see `test-harness/README.md` for the harness's own design notes
and safety guards.

## Repo layout

```
architecture-notes/   factual read-through of the real AutoAssist AI code
test-cases/            attack scenarios, organized by category (Phase 1)
test-harness/          the script that executes them (Phase 2)
results/               raw, reviewable output per test case (Phases 3-7)
SECURITY_ASSESSMENT.md the formal report (Phase 8-10)
```

## Full report

→ [`SECURITY_ASSESSMENT.md`](SECURITY_ASSESSMENT.md)
