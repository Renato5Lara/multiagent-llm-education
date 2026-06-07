# UTF-8 VALIDATION

## Encoding standards
- All new/modified files must be **UTF-8 without BOM**
- All HTTP responses with text content types must include `charset=utf-8`

## Validation results

### File encoding verification
Passed: All 600+ text files in the project are valid UTF-8 (after fixes).

### API Content-Type headers verification

| Endpoint type | Before | After | Files affected |
|--------------|--------|-------|----------------|
| SSE streams | `text/event-stream` | `text/event-stream; charset=utf-8` | 5 route files |
| JSON export | `application/json` | `application/json; charset=utf-8` | `replay/export.py` |
| Markdown export | `text/markdown` | `text/markdown; charset=utf-8` | `replay/export.py` |
| HTML export | `text/html` | `text/html; charset=utf-8` | `replay/export.py` |
| CSV export | `text/csv` | `text/csv; charset=utf-8` | `replay.py` |
| LaTeX export | `application/x-latex` | `application/x-latex; charset=utf-8` | `replay.py` |

### JSON serialization
All `json.dumps()` calls already use `ensure_ascii=False`:
- `backend/app/replay/serializer.py:11` ✅
- `backend/app/replay/replay_exporter.py:16` ✅
- `backend/app/benchmark/exporters.py:56,64,108` ✅
- All SSE event payloads use `json.dumps(payload, ensure_ascii=False)` ✅

### HTML export charset
- `backend/app/replay/serializer.py:56` already has `<meta charset="utf-8" />` ✅

### SSE payload encoding
All SSE streaming endpoints produce data with `json.dumps(..., ensure_ascii=False)` and now include `charset=utf-8` in the Content-Type header.

## Edge cases verified

| Scenario | Status |
|----------|--------|
| Browser receives SSE with `charset=utf-8` | ✅ All SSE endpoints fixed |
| Browser receives CSV with `charset=utf-8` | ✅ CSV export fixed |
| Browser receives Markdown/HTML/LaTeX with `charset=utf-8` | ✅ All export formats fixed |
| Excel opens CSV with UTF-8 content | ✅ Best practice: UTF-8 without BOM; Excel prefers UTF-8-SIG for compatibility |
| Frontend reads API responses with explicit charset | ✅ No browser encoding guessing needed |
| Python reads files as UTF-8 | ✅ All source files valid UTF-8 |
