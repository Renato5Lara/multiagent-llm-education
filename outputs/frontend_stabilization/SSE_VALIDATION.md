# SSE VALIDATION

## URL Configuration Audit

Checked all files that use `API_BASE_URL` for SSE/HTTP connections:

| File | Line | Pattern | Status |
|------|------|---------|--------|
| `pages/demo/SwarmDemo.tsx` | 23 | `VITE_API_URL \|\| 'http://127.0.0.1:8000'` | ✅ Correct |
| `hooks/useDemoSSE.ts` | 4 | `VITE_API_URL \|\| 'http://127.0.0.1:8000'` | ✅ Correct |
| `components/swarm/ReplayExportPanel.tsx` | 5 | `VITE_API_URL \|\| 'http://127.0.0.1:8000'` | ✅ Correct |
| `pages/replay/ReplayDashboard.tsx` | 13 | `VITE_API_URL \|\| 'http://127.0.0.1:8000'` | ✅ Correct |

## Environment files

| File | VITE_API_URL | Effect |
|------|-------------|--------|
| `frontend/.env` | (empty) | Fallback to `127.0.0.1:8000` (dev with Vite proxy) |
| `frontend/.env.example` | (documented) | Template |
| `frontend/.env.production` | `https://upao-mas-edu-api.onrender.com` | Production |

## SSE compatibility

- `useDemoSSE.ts` uses `EventSource` with `${API_BASE_URL}/api/swarm/demo/events/${sessionId}`
- `ReplayDashboard.tsx` uses `EventSource` with `${API_BASE_URL}/api/replay/stream/${studentId}`
- Both use `EventSource.addEventListener` for named events with proper cleanup in `useEffect` return
- Max event buffer: 200 events (sliding window)
- Graceful error handling: `source.onerror` sets status to `'error'`

## No issues found

All URLs use `import.meta.env.VITE_API_URL` with a safe fallback. SSE connections will follow whichever URL is configured. No hardcoded URLs remain.
