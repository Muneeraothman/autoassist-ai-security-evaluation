# Architecture Notes: Tool Definitions and Authorization

Source: `backend/tools.py` (all 5 tools + their execution), `backend/main.py`
(`get_current_user`, `get_owned_vehicle_or_404` — the REST-route equivalent
of the same pattern).

## The 5 tools exposed to the model (exact names/params, from `TOOL_SPECS`)

| Tool | Required params | Optional params | Reads |
|---|---|---|---|
| `get_vehicle_info` | `vehicle_id: int` | — | make/model/year/mileage/avg miles-per-day |
| `get_upcoming_maintenance` | `vehicle_id: int` | — | due/overdue schedule items |
| `get_service_history` | `vehicle_id: int` | `service_name: str`, `since_date: str (ISO)` | past service records |
| `get_spending_summary` | `vehicle_id: int` | `category: str`, `year: int` | spend totals/breakdowns |
| `search_manual` | `query: str`, `vehicle_id: int` | — | RAG over the owner's manual |

Each is described to the model **only** as a name + JSON Schema parameter
description (`inputSchema.json`) — never as executable code, a query
string, or anything the model could use to express an arbitrary read. This
is the literal mechanism behind the README's "the AI never sees SQL" claim,
verified by reading `tools.py` directly rather than taking the claim at
face value.

## The authorization pattern — where it actually lives

```python
def _get_owned_vehicle(db, current_user, vehicle_id) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if vehicle is None or vehicle.user_id != current_user.id:
        raise ToolError(f"No vehicle with id {vehicle_id} found for this user.")
    return vehicle
```

Every one of the 5 tool functions calls this (or, for `search_manual`,
calls it before running the vector query) **before** touching any
vehicle-scoped data. Critically:

- `current_user` is not something the model provides — it's the same
  `current_user` object FastAPI's `Depends(get_current_user)` derived from
  the caller's JWT cookie at the top of the request, threaded down through
  `run_chat(messages, db, current_user, vehicles)` →
  `execute_tool(name, tool_input, db, current_user)` → each `_tool_*`
  function. **The model can request any `vehicle_id` integer it wants; it
  cannot request any `current_user`.** The ownership check is therefore
  structurally independent of anything in the model's output — a
  compromised/jailbroken model literally cannot pass a different identity
  to the backend, because identity isn't a parameter the tool schema
  exposes at all.
- The failure mode on a mismatched `vehicle_id` is a generic `ToolError`
  ("No vehicle with id {id} found for this user") — same message whether
  the vehicle doesn't exist at all or exists but belongs to someone else.
  This is a deliberate non-distinguishing error (same pattern as
  `get_owned_vehicle_or_404`'s 404-not-403 choice on the REST side) — it
  avoids confirming/denying that a given vehicle ID exists for another
  account, which matters for the cross-user test design in Phase 5 (an
  enumeration-resistance property worth testing, not just an
  authorization property).
- This exact pattern — re-derive ownership server-side from the session,
  never trust an ID's implied ownership — is used in 3 places in the real
  codebase per the main README's "Design decisions" section: REST routes
  (`get_owned_vehicle_or_404`), S3 key namespacing, and here. This review
  only tests the AI-tool instance of it, per the stated out-of-scope list
  for traditional web-app surface.

## What validates tool call *parameters* (not just ownership)

- `vehicle_id`, `year`: typed `int` in the JSON Schema — Bedrock's Converse
  API enforces the schema before the backend ever sees a call, so a
  non-integer `vehicle_id` should not reach `execute_tool` as a tool call
  in the first place (testable: Phase 6).
  Test evidence for this — see `results/phase6-tool-misuse.md` — is a
  Bedrock-normalization example, not proof of Pydantic/JSON-Schema
  strictness in general; log tool-call payloads at execution time if this
  needs re-confirming after a Bedrock/SDK version change.
- `since_date` (in `get_service_history`): passed through
  `date.fromisoformat()` in a `try/except`, raising a `ToolError` (not an
  unhandled 500) on a malformed string — application-level validation, not
  schema-level (the schema only declares it as `"type": "string"`, no
  format constraint).
- `service_name`, `category`: free-text, used only as a case-insensitive
  Python substring filter (`in name.lower()`) against already
  ownership-scoped rows — never interpolated into SQL, so classic
  injection isn't applicable here; worst case is an unexpected substring
  match, not a boundary violation.
- No explicit upper bound on `query` length for `search_manual` — it's
  embedded via Titan and used in a `pgvector` `ORDER BY cosine_distance`
  against an already vehicle-scoped row set, so an oversized query costs
  more (Bedrock embedding call, DB compute) but cannot expand the result
  set outside that vehicle's own manual chunks.

## Conversation loop bound (relevant to both tool misuse and DoW)

`MAX_TOOL_ITERATIONS = 5` in `bedrock_utils.run_chat` caps the number of
model↔tool round trips **per `/api/chat` call**. This bounds a single
request's cost/looping but does **not** bound how many separate `/api/chat`
requests a client can send — there is no rate limiting at the route level
(confirmed absent in `01-system-overview.md`). This distinction — bounded
per-call, unbounded across calls — is exactly what Phase 7's
denial-of-wallet tests are designed to probe.
