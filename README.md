# BlueKnight — Collaborative Market Research Reports

A FastAPI + PostgreSQL backend adding real-time collaborative editing to market research reports.
Multi-user section editing with optimistic concurrency, a full audit trail, and AI-assisted rewrites.

---

## Setup

### Prerequisites
- Docker (for the database)
- Python 3.11+

### Quick start

```bash
# 1. Start the database
docker compose up -d db

# 2. Install the package (editable)
pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env

# 4. Run migrations and seed
alembic upgrade head
python seed.py

# 5. Start the server
uvicorn app.main:app --reload

# 6. Run the test suite
pytest -v
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`.

### Seeded test users

| user_id | org_id | role on report 1 |
|---------|--------|-----------------|
| 1       | 1      | owner            |
| 2       | 1      | (share to grant) |
| 3       | 1      | (share to grant) |
| 4       | 2      | cross-org (403)  |
| 5       | 2      | cross-org        |
| 6       | 2      | cross-org        |

Generate a JWT for any user:
```python
from app.auth.jwt_helper import encode_token
print(encode_token(user_id=1, org_id=1))
```

---

## Schema

### Tables added by this project (migration `0001`)

| Table | Purpose |
|-------|---------|
| `report_sections` | One row per `(report_id, section_key)`. Holds current `content` (JSONB) and `version` counter. |
| `report_section_edits` | Append-only audit log. Records `content_before`, `content_after`, `source` (`human` / `ai_rewrite` / `revert`), and `editor_user_id`. |
| `report_shares` | Active shares of a report to another user with `view` or `edit` permission. Partial unique index on `(report_id, target_user_id) WHERE revoked_at IS NULL`. |

### Bonus table (migration `0002`)

| Table | Purpose |
|-------|---------|
| `idempotency_keys` | Caches `(key, user_id) → (request_hash, status_code, response_body)` for safe POST replay. |

### Parent tables (pre-existing, created `IF NOT EXISTS` in migration)

`users(id, org_id, email)` · `market_research_reports(id, user_id, title, sections, created_at)`

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/reports/{id}/sections/{key}` | Fetch a section; response includes `ETag: "{version}"` |
| `PATCH` | `/reports/{id}/sections/{key}` | Optimistic update; requires `If-Match: "{version}"` |
| `GET` | `/reports/{id}/sections/{key}/history` | Paginated edit history with cursor; each edit includes a `diff` field |
| `POST` | `/reports/{id}/sections/{key}/revert/{edit_id}` | Revert to a previous version |
| `POST` | `/reports/{id}/sections/{key}/ai-rewrite` | AI-assisted rewrite (rate-limited 10/min; supports `Idempotency-Key`) |
| `POST` | `/reports/{id}/shares` | Grant view/edit access (supports `Idempotency-Key`) |
| `DELETE` | `/reports/{id}/shares/{share_id}` | Revoke a share |
| `GET` | `/reports/{id}/shares` | List active shares |

---

## Design notes

### Auth
All requests carry a JWT (`Authorization: Bearer <token>`) decoded by `RequestIDMiddleware`-adjacent `get_current_user` dependency into a lightweight `CurrentUser(user_id, org_id)` value object. Access level (owner / editor / viewer / none) is computed once per request via a single SQL query against `report_shares` and `market_research_reports.user_id`. The four-way access enum drives every endpoint guard — no per-row ACL lookups in service code.

### Concurrency
Optimistic concurrency via the HTTP `If-Match` header carrying the client's known version. The write path is a **single CTE** that atomically `UPDATE`s `report_sections` (with `AND version = :expected`) and `INSERT`s into `report_section_edits` in one round-trip. A zero-row `UPDATE` (stale version) causes the CTE's `INSERT` to also produce zero rows; the service detects this and returns 412 with the current version in the response body so the client can refetch and retry. Two concurrent writers with the same `If-Match` version are serialised by PostgreSQL row-locking — exactly one succeeds with 200, the other gets 412.

### Audit log
`report_section_edits` is strictly append-only: no `UPDATE` or `DELETE` ever touches it. Reverts write a new row with `source = 'revert'` and `content_after = original_content_before`; history is never rewritten. The table is indexed on `(report_id, section_key, ts DESC)` for efficient cursor-paginated history queries. Diffs (`added`, `removed`, `changed`) are computed at read time from the stored `content_before`/`content_after` JSONB columns — no diff data is persisted.

---

## Bonus features

### 1 · Idempotency-Key (Stripe pattern)
`POST /shares` and `POST /ai-rewrite` accept an optional `Idempotency-Key: <uuid>` header. The server computes `SHA256(method + path + sorted_body)` as the request fingerprint and stores `(key, user_id) → (fingerprint, status, response)` in the `idempotency_keys` table. Replaying the same key+body returns the cached response. Replaying the same key with a **different** body returns 422.

### 2 · Per-user rate limit on AI rewrite
In-memory sliding window: 10 calls / 60 seconds per `user_id`. Exceeding the limit returns `429 Too Many Requests` with a `Retry-After: <seconds>` header. The bucket lives in process memory — swap for a Redis sorted-set sliding window in production.

### 3 · Diff in history responses
Every edit returned by `GET /history` includes a `diff` object:
```json
{
  "added":   { "new_key": "value" },
  "removed": { "old_key": "value" },
  "changed": { "text": { "before": "old", "after": "new" } }
}
```
Computed at read time from `content_before` / `content_after`; never stored.

---

## What I cut for time

- No OpenAPI `example` values on every request/response schema
- Rate limiter is in-process; would use a Redis sorted-set sliding window in production
- No retry / exponential backoff on LLM calls
- No real LLM provider wired in (uses `InMemoryLLMClient` stub — swap in the `app/llm/` package)
- No per-section role-based access (e.g. "only finance team can edit `financials`")
- No `Prometheus /metrics` endpoint
- Migration test truncates and re-runs migrations; a dedicated test database would be cleaner

---

## What I'd do next

- **SSE / WebSockets** for real-time collaborative cursors
- **Redis sliding window** to replace the in-memory rate limiter
- **Real LLM provider** (OpenAI / Anthropic) behind a circuit breaker with retry
- **Per-section RBAC** — extend `report_shares` with an optional `section_key` scope
- **`/metrics` endpoint** (Prometheus + Grafana) tracking edit latency, LLM call duration, 412 rate

---

## Log format

stdlib `logging` + custom JSON formatter — chosen over `structlog` to keep dependencies minimal; same observable behaviour (`request_id`, `level`, `msg`, `ts` in every line).

---

## Architecture layers (enforced)

```
routers/   — HTTP in/out only. No SQLAlchemy imports.
services/  — Business logic. No FastAPI / SQLAlchemy imports.
repository/ — SQL. No FastAPI imports.
```

Verified pre-commit:
```bash
grep -r 'sqlalchemy' app/routers/       # must return nothing
grep -r 'openai\|anthropic' app/routers/ app/services/  # must return nothing
```
