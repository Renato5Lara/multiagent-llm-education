# FIXED FILES

## Files modified

| File | Change | Reason |
|------|--------|--------|
| `backend/requirements.txt` | UTF-16LE → UTF-8 | pip freeze saved with Windows encoding |
| `backend/requirements-lock.txt` | UTF-16LE → UTF-8 | pip freeze saved with Windows encoding |
| `backend/app/api/routes/swarm.py` | Added `; charset=utf-8` to 3 SSE endpoints | Missing charset in Content-Type headers |
| `backend/app/api/routes/swarm_demo.py` | Added `; charset=utf-8` to 2 SSE endpoints | Missing charset in Content-Type headers |
| `backend/app/api/routes/sandbox.py` | Added `; charset=utf-8` to 1 SSE endpoint | Missing charset in Content-Type headers |
| `backend/app/api/routes/replay.py` | Added `; charset=utf-8` to content_type_map and SSE endpoint | Missing charset in CSV, JSON, Markdown, LaTeX exports and SSE |
| `backend/app/api/routes/tutor.py` | Added `; charset=utf-8` to 1 SSE endpoint | Missing charset in Content-Type headers |
| `backend/app/replay/export.py` | Added `; charset=utf-8` to all 4 export media types | Exporter returned media types without charset |
| `backend/tests/test_cognitive_replay.py` | Updated assertions to match new media_type strings | Test expected old media types without charset |

## Files NOT modified (clean)

All source files were verified clean and left untouched:
- All `.tsx` and `.ts` files in `frontend/src/`
- All `.py` files in `backend/app/` (except charset header changes above)
- All `.json`, `.md`, `.csv`, `.env` files
- Benchmark datasets, snapshots, and outputs

## Verification

| Check | Result |
|-------|--------|
| `python -m pytest` | 1338 passed, 0 failed |
| `npm run build` | 0 errors, 908ms |
| `npm run lint` | 0 errors (1 pre-existing warning) |
| `python -c "open('backend/requirements.txt', 'rb').read().decode('utf-8')"` | Valid UTF-8 |
| `python -c "open('backend/requirements-lock.txt', 'rb').read().decode('utf-8')"` | Valid UTF-8 |
