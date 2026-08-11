# Threat Model

## Attackers considered

1. **A malicious authenticated user of the real app.** Has a valid
   AutoAssist account, a valid session cookie, and full control over what
   they type into the chat widget — and, since `/api/chat` is a normal
   HTTP endpoint, full control over the raw HTTP request too (not limited
   to what the React `ChatWidget.jsx` would ever send). This is the
   primary attacker for this review: everything in Phases 3, 5, 6, 7
   assumes this attacker.
2. **An attacker who can influence RAG-retrieved content.** Only relevant
   if the manual corpus were writable by anything other than the
   developer's offline ingestion script. Per
   `architecture-notes/03-rag-pipeline.md`, no such path exists in the
   real app today — this attacker is analyzed as a documented structural
   non-issue in Phase 4, not tested against a live exploit (there's
   nothing live to exploit).
3. **A second authenticated user attempting to reach the first user's
   data through the assistant.** A specific instance of attacker #1,
   broken out separately because it's the highest-consequence category
   given the app's ownership-scoped design — this is what Phase 5 is for.

**Not modeled** (per the build guide's explicit scope): unauthenticated
attackers hitting `/api/chat` directly (auth itself — JWT validity,
cookie theft, session fixation — is traditional web-app surface, out of
scope), attackers with infrastructure/cloud access (AWS account
compromise, RDS access), and physical/social attackers targeting the
project owner rather than the running system.

## What the attacker is trying to achieve

- Read another user's vehicle data, service history, or spending (the
  single highest-impact goal, given this is a real, if small, PII-shaped
  dataset).
- Get the assistant to take or imply an unauthorized action, or to treat
  attacker-supplied text as if it were trusted system/tool output
  (excessive agency / injection).
- Extract the system prompt, tool schemas, or internal error detail not
  meant to be user-facing (useful reconnaissance for a follow-on attack,
  and a disclosure in its own right).
- Get the assistant to state maintenance advice that isn't actually
  grounded in the vehicle's real data or manual (safety-relevant if
  acted on — the app's core value proposition is *accurate* data, so
  hallucination is a functional-trust failure even without a
  "traditional" security impact).
- Run up real Bedrock API cost against the app owner via cheap, repeated,
  or oversized requests.

## Trust boundary (from the architecture notes, not assumed)

| Input | Who controls it | Reaches the model as |
|---|---|---|
| Chat message text (`ChatMessage.content`) | The authenticated caller, fully | Conversation `user`/other-role turn content |
| `ChatMessage.role` | The authenticated caller, fully (schema allows any string) | Converse API `role` field directly |
| `vehicle_id` / other tool parameters the model *requests* | The model itself proposes these based on conversation content — which the attacker influences, but the model chooses the literal value | A tool call the backend independently authorizes |
| The user's actual vehicle list injected into the system prompt | The backend, from the DB, scoped to `current_user` | System prompt text |
| `search_manual` retrieved excerpts | The backend, from a fixed developer-ingested corpus, not attacker-writable | Tool result content |
| `current_user` identity used for every ownership check | The backend, derived from the JWT cookie — **never** a chat/tool parameter | N/A — not exposed to the model at all |

The single most important line in this table for Phase 5: **identity is
not a model-visible or model-suppliable value anywhere in this system.**
Any cross-user attack has to work by getting the *model* to emit a
different `vehicle_id`, and then getting the *backend* to honor it despite
`current_user` not owning it. That's two independent things that both
have to fail for the attack to succeed — which is exactly what Phase 5's
"which layer stopped it" analysis is designed to pull apart.
