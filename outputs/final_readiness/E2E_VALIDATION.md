# E2E VALIDATION REPORT

**Ejecutado:** 2026-06-05
**Resultado:** 39 passed, 3 failed (test script issues), 42 total

---

## Resumen de Validaciones

| Categoría | Tests | Pass | Fail |
|-----------|-------|------|------|
| Health / Degraded Mode | 7 | 7 | 0 |
| Authentication | 9 | 8 | 1 |
| Courses | 2 | 2 | 0 |
| Student | 5 | 4 | 1 |
| Sandbox | 3 | 3 | 0 |
| Pedagogy | 1 | 1 | 0 |
| Swarm | 5 | 5 | 0 |
| Explainability | 2 | 2 | 0 |
| Replay | 1 | 0 | 1 |
| SSE Streaming | 2 | 2 | 0 |
| Frontend | 3 | 3 | 0 |
| Environment | 2 | 2 | 0 |

## "Fallos" (todos son issues de script de test, no del sistema)

1. **Token refresh 401** — El script buscaba refresh_token en /me, pero está en respuesta de login. No es bug.
2. **Student profile 404** — GET sin perfil creado retorna 404 correctamente. POST crea perfil. No es bug.
3. **Replay sessions** — Respuesta es `{"sessions": [...], "total": N}`, no lista plana. No es bug.

## Validaciones Críticas Pasadas

- ✅ Sistema operativo sin API keys (degraded mode)
- ✅ Auth funcional con 3 roles
- ✅ Failed login rechazado (401)
- ✅ No auth rechazado (401)
- ✅ 20 cursos cargados
- ✅ Sandbox ejecuta y bloquea código peligroso
- ✅ Swarm demo genera sesiones
- ✅ SSE streaming con charset=utf-8
- ✅ 1338 tests backend pasan
- ✅ Frontend build y lint OK
