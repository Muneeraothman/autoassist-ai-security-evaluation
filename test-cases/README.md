# Test Cases

24 concrete test cases across 7 attack categories, each grounded in the
real tool names, system prompt text, and seeded data documented in
`../architecture-notes/`. Every file below is both the Phase 1 design
record and the machine-readable input the harness (`../test-harness/`)
consumes.

| File | Category | # cases | OWASP (primary) |
|---|---|---|---|
| `01-direct-prompt-injection.json` | Direct prompt injection | 4 | LLM01:2025 |
| `02-indirect-injection-rag.json` | Indirect injection / RAG poisoning | 2 | LLM04:2025 / LLM08:2025 |
| `03-cross-user-access.json` | Cross-user data access | 4 | LLM06:2025 |
| `04-tool-misuse.json` | Tool misuse / parameter manipulation | 5 | LLM06:2025 |
| `05-data-leakage.json` | Sensitive data / system leakage | 3 | LLM07:2025 |
| `06-denial-of-wallet.json` | Excessive / denial-of-wallet | 3 | LLM10:2025 |
| `07-hallucination.json` | Hallucination / ungrounded advice | 3 | LLM09:2025 |

Full framework mapping and rationale per case is inline in each JSON file
(`owasp`, `atlas`, `rationale`, `expected_behavior` fields) — see
`../architecture-notes/05-frameworks-reference.md` for the framework
versions/sources this uses, and `../architecture-notes/06-threat-model.md`
for the attacker model these were designed against.

## Why these categories and not others

The build guide's 7 suggested categories map cleanly onto this app's real
architecture (5 fixed tools + RAG + per-user auth), so no category was
dropped. Two were scoped down from their generic form once the real
architecture was known:

- **RAG poisoning** has no live exploit path in the real app (manual
  ingestion is an offline developer script, not a user-reachable write) —
  documented as a structural mitigation rather than skipped, per the
  build guide's own instruction for this case, with 2 adjacent tests that
  probe the same trust boundary through a reachable channel instead.
- **Denial-of-wallet** cases are deliberately bounded (≤5 requests per
  case) since `/api/chat` calls real, billed Amazon Bedrock APIs even in
  local dev — enough to observe whether any throttling exists, not a real
  load campaign (out of scope per the top-level README).
