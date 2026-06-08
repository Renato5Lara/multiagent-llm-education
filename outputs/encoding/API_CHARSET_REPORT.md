# API CHARSET REPORT

## Issue
FastAPI/Starlette `StreamingResponse` and `Response` objects default to media types without explicit charset. While JSON is UTF-8 by specification (RFC 8259), text content types (SSE, CSV, Markdown, HTML, LaTeX) should declare charset explicitly to prevent browser encoding guessing.

## Endpoints audited

### SSE endpoints (text/event-stream)
All SSE endpoints now include `charset=utf-8` in the Content-Type:

| File | Endpoint | Before | After |
|------|----------|--------|-------|
| `routes/swarm.py` | `GET /api/swarm/monitor/{student_id}` | `text/event-stream` | `text/event-stream; charset=utf-8` |
| `routes/swarm.py` | `GET /api/swarm/adaptation/{student_id}` | `text/event-stream` | `text/event-stream; charset=utf-8` |
| `routes/swarm.py` | `GET /api/swarm/demo/replay/{session_id}/cognitive` | `text/event-stream` | `text/event-stream; charset=utf-8` |
| `routes/swarm_demo.py` | `GET /api/swarm/demo/replay/{session_id}/stream` | `text/event-stream` | `text/event-stream; charset=utf-8` |
| `routes/swarm_demo.py` | `GET /api/swarm/demo/events/{session_id}` | `text/event-stream` | `text/event-stream; charset=utf-8` |
| `routes/sandbox.py` | `GET /api/sandbox/stream` | `text/event-stream` | `text/event-stream; charset=utf-8` |
| `routes/replay.py` | `GET /api/replay/stream/{student_id}` | `text/event-stream` | `text/event-stream; charset=utf-8` |
| `routes/tutor.py` | `POST /api/tutor/chat/stream` | `text/event-stream` | `text/event-stream; charset=utf-8` |

### Export endpoints

| File | Endpoint | Content-Type | Before | After |
|------|----------|-------------|--------|-------|
| `routes/replay.py` | `GET /api/replay/student/{student_id}/export?fmt=json` | JSON | `application/json` | `application/json; charset=utf-8` |
| `routes/replay.py` | `GET /api/replay/student/{student_id}/export?fmt=csv` | CSV | `text/csv` | `text/csv; charset=utf-8` |
| `routes/replay.py` | `GET /api/replay/student/{student_id}/export?fmt=markdown` | Markdown | `text/markdown` | `text/markdown; charset=utf-8` |
| `routes/replay.py` | `GET /api/replay/student/{student_id}/export?fmt=latex` | LaTeX | `application/x-latex` | `application/x-latex; charset=utf-8` |
| `routes/swarm_demo.py` | `GET /api/swarm/demo/replay/{session_id}?fmt=json` | JSON | `application/json` | `application/json; charset=utf-8` |
| `routes/swarm_demo.py` | `GET /api/swarm/demo/replay/{session_id}?fmt=markdown` | Markdown | `text/markdown` | `text/markdown; charset=utf-8` |
| `routes/swarm_demo.py` | `GET /api/swarm/demo/replay/{session_id}?fmt=html` | HTML | `text/html` | `text/html; charset=utf-8` |
| `routes/swarm_demo.py` | `GET /api/swarm/demo/replay/{session_id}?fmt=summary` | JSON | `application/json` | `application/json; charset=utf-8` |

## Example SSE response headers (after fix)
```
HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

## Example CSV export response headers (after fix)
```
HTTP/1.1 200 OK
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename=replay_123.csv
```

## Frontend compatibility
The frontend uses `EventSource` for SSE and `fetch` for API calls. Both honor the Content-Type charset from the server. No frontend changes were needed.

## Verificación
- All 14 text/* endpoints now include `charset=utf-8`
- No JSON responses were changed (JSON is implicitly UTF-8 per RFC 8259)
- No regressions in tests (1338 passed)
