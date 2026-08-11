# Architecture Notes: Consolidated Controls and Gaps (pre-testing)

This is a factual inventory only — pulled from reading `01`–`03` — not yet
a findings/severity judgment (that's Phase 8, after empirical testing).
It's the checklist the Phase 1 threat model and test cases are built
against.

## Controls already in place (candidates for "validated defense" findings)

1. **Backend-enforced, per-call ownership re-derivation** on every one of
   the 5 tools (`_get_owned_vehicle`), independent of model input —
   identity comes from the JWT-derived session, never from a tool
   parameter.
2. **Fixed, parameterized tool set** — the model can only name one of 5
   tools with typed JSON-Schema parameters; there is no code path from
   model output to a database query string.
3. **Non-distinguishing failure mode** on ownership mismatch (same
   "not found" message whether a vehicle_id doesn't exist or belongs to
   someone else) — resists ID enumeration via error-message differences.
4. **RAG corpus has no user-reachable write path** — ingestion is an
   offline developer script against fixed, repo-bundled PDFs.
5. **Per-request tool-loop cap** (`MAX_TOOL_ITERATIONS = 5`) bounds a
   single request's model↔tool round trips.
6. **System prompt explicitly scopes the assistant** to the user's own
   vehicle data and instructs tool-grounded (non-guessed) answers, with an
   explicit refusal instruction for out-of-scope requests.
7. **Application-level validation on top of schema typing** in at least
   one tool (`since_date` ISO parsing wrapped in try/except → `ToolError`,
   not a raw exception).

## Gaps observed directly in the code (candidates for "residual risk"
## findings — to be confirmed/refuted empirically in Phases 3–7, not
## assumed true just because the code allows them)

1. **No rate limiting at all** on `/api/chat` (or any route) — no
   `slowapi`/`limits` dependency, no per-user/per-IP throttle. The
   per-request tool-loop cap (#5 above) does not address repeated
   *requests*.
2. **`ChatMessage.role` is an unconstrained `str`**, not a
   `Literal["user", "assistant"]` — combined with the client sending full
   conversation history on every call, this means any direct API caller
   (not just the real frontend) can inject fabricated `role="assistant"`
   turns into the history sent to Bedrock's Converse API. Whether Bedrock
   itself rejects unrecognized roles, and whether this can actually
   influence model behavior, is an empirical question for Phase 3/6, not
   assumed from the schema gap alone.
3. **No length cap** on `ChatMessage.content` or on `messages` list length
   — cost/DoW-relevant, not a correctness bug.
4. **No explicit "don't reveal your system prompt / ignore embedded
   instructions" instruction** in the system prompt text itself — the
   prompt scopes *topic* (vehicle data only) but says nothing about
   resisting instruction-override attempts specifically. Modern
   instruction-tuned models often resist this class of attack by default
   regardless of an explicit meta-instruction; Phase 3 tests this
   empirically rather than assuming the omission is exploitable.
5. **No structured audit log of tool calls** (which tool, which
   parameters, which user, allowed/denied) — only ad hoc `logging.warning`
   calls for email failures. This doesn't weaken any control directly, but
   it means a real attack attempt (including a *blocked* one) wouldn't
   currently show up anywhere queryable for detection/incident response.

These 5 gaps map into Phase 1's threat model and test-case design as the
primary hypotheses under test for the tool-misuse, data-leakage, and
denial-of-wallet categories; cross-user access (#1 control area) is
expected, going in, to hold — see Phase 5 for whether that expectation
survives contact with actual testing.
