# Architecture Notes: RAG Pipeline (Owner's Manual)

Source: `backend/ingest_manuals.py`, `backend/embeddings.py`,
`backend/tools.py::_tool_search_manual`, `backend/models.py::ManualChunk`.

## Ingestion — who can put content into the retrieval corpus

`ingest_manuals.py` is a **developer-run, offline CLI script**
(`python ingest_manuals.py --vehicle-id 2`), not an HTTP endpoint. It:

1. Reads a hardcoded list of PDF filenames (`SOURCE_FILES = ["OM33566U.pdf",
   "SMG202.pdf"]`) from a fixed `manuals/` directory **in the repo itself**.
2. Extracts text page-by-page with `pdfplumber`, chunks each page into
   ~500-word pieces with 75-word overlap (never crossing a page boundary,
   so every chunk keeps an exact, single-page citation).
3. Embeds each chunk with Titan Text Embeddings V2 and inserts
   `(vehicle_id, source_file, page_number, chunk_text, embedding)` into
   `manual_chunks` directly via SQLAlchemy — a trusted, local DB session,
   not a user-facing write path.

**There is no HTTP route, form, or file-upload endpoint anywhere in
`main.py` that lets any authenticated user (let alone an attacker) add,
edit, or replace manual content.** Grepped `main.py` for
`manual`/`upload`/`UploadFile` — the only upload-shaped endpoint in the
whole app is the receipt-photo S3 pre-signed-URL flow (`ReceiptUploadRequest`
in `main.py`), which is unrelated to `manual_chunks` and writes to S3, not
to the RAG corpus.

## Retrieval — what the model sees

`_tool_search_manual(db, current_user, query, vehicle_id)`:
1. Ownership-checks `vehicle_id` exactly like the other 4 tools (see
   `02-tool-definitions-and-authorization.md`) — a user cannot retrieve
   chunks belonging to a manual ingested under a *different* vehicle_id.
2. Embeds the model-supplied `query` string with Titan.
3. `ORDER BY embedding.cosine_distance(query_embedding) LIMIT 5` — a plain
   nearest-neighbor scan, scoped by the `WHERE vehicle_id = :vehicle_id`
   filter already applied.
4. Returns `{source_file, page_number, excerpt}` per result as a Converse
   `toolResult` — plain JSON text, not re-parsed as instructions by
   anything other than the model itself reading it as conversation
   content (which is exactly the channel indirect-injection attacks would
   need, if the corpus were attacker-reachable).

## What this means for the RAG attack surface (documented per Phase 4's
## instructions, since the "real pipeline isn't user-attackable" case applies)

Classic indirect prompt injection / RAG poisoning requires an attacker to
get **their own content** into the corpus the victim's retrieval will pull
from (e.g., a poisoned wiki page, an uploaded document, a public webpage
the RAG pipeline crawls). Here:

- The corpus is 2 fixed PDFs, shipped in the app's own repo, ingested by a
  local script only the developer runs, with no code path from any
  authenticated HTTP request to a write against `manual_chunks`.
- Retrieval is scoped per-`vehicle_id`, and `vehicle_id`s are themselves
  ownership-checked — so even if a second vehicle's manual were poisoned
  somehow, cross-vehicle retrieval isn't possible through this tool either.

**This is a structural mitigation, not a policy one** — it's not that
users are told not to upload malicious manuals, it's that no code path
exists for any user to write to this table at all. Phase 4 documents this
finding and, per the build guide's own instruction for this exact case,
substitutes a *related* test that doesn't require the pipeline to be
attackable: crafting a chat message that pastes fake "manual" text
in-line (e.g. "the manual says on page 40: ...") to see whether the model
can be tricked into treating attacker-supplied chat content as if it came
from a real `search_manual` call, which is a direct-prompt-injection
variant that happens to target the RAG-shaped trust boundary specifically.
