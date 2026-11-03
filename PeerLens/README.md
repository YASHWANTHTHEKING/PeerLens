# PeerLens

PeerLens answers questions from Infosys annual filings and returns the filing and
page for each retrieved excerpt. The current corpus contains five SEC Form 20-F
filings for fiscal years 2022–2026.

## Problem

Annual filings are long and difficult to search for a specific financial or
business disclosure. PeerLens indexes filing text by its source page and uses
retrieved excerpts to answer questions. Answers include document and page
citations so readers can verify the source.

## Who it is for

Readers researching Infosys's annual filings.

## Signature feature

Page-aware retrieval that keeps document, page number, and heading attached to
each indexed excerpt and exposes them as citations in `/ask`.

## Hardest engineering problem

Preserving page-level citations while extracting text from SEC filing HTML.
PeerLens uses the filing's explicit page-break markers and carries each page
number and most recent heading through chunking, embedding, retrieval, and the
API response.

## Dataset

Five Infosys Form 20-F filings from SEC EDGAR, covering fiscal years 2022–2026.
The parser detects more than 1,200 explicit page-break markers across the
filings. These are source HTML page boundaries, not a claim about printed PDF
pagination. See [DATASET.md](DATASET.md) for links and per-file counts.

## Run locally

1. Install Python 3.11 or later and copy `.env.example` to `.env`.
2. Set `LLM_API_KEY` in `.env`. Model calls and ingestion use the configured
   OpenAI-compatible chat-completions and embeddings endpoints.
3. Start Postgres with pgvector and set `DATABASE_URL` in `.env`.
4. Install dependencies and initialize the schema:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   .\.venv\Scripts\python.exe -m app.db
   .\.venv\Scripts\uvicorn.exe app.main:app --reload
   ```

   On macOS/Linux, activate `.venv` and use `python -m pip`, `python -m app.db`,
   and `uvicorn app.main:app --reload`.
5. To index the local SEC filings, run `python -m app.ingest` from the project
   root. The files in `data/raw/` are intentionally not committed.

Alternatively, use Docker Compose (development credentials are defined in the
Compose file):

```powershell
Copy-Item .env.example .env
# Set LLM_API_KEY in .env, then:
docker compose up --build -d
docker compose exec api python -m app.ingest
```

`GET /health` is a liveness check and does not depend on the database or model
provider. Model-backed endpoints return a clear service error if credentials or
the database are unavailable. For cost estimates, optionally set the three
`*_COST_PER_1M` values in `.env`; without rates, PeerLens still logs token usage
and reports the cost as `null`.

## API

- `GET /health` — process liveness.
- `POST /chat` — non-streaming model response as structured JSON.
- `POST /chat/stream` — server-sent events (`delta`, `usage`, or `error`).
- `POST /ask` — filing-grounded answer with citation objects.
- `GET /usage?days=30` — request and token totals, grouped by request type and
  model, with estimated costs when rates are configured.

Example:

```json
{
  "question": "What risk factors does Infosys disclose?",
  "top_k": 5
}
```

The `/ask` response includes citations with `document`, page number, heading,
and vector similarity. Citations identify retrieved excerpts; verify the
underlying filing when making consequential decisions.

## Tests and lint

```powershell
.\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\ruff.exe check app tests
```

## Deployment

Not deployed yet.
