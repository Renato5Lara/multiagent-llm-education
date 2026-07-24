# Bitácora de Migración — Arquitectura Pedagógica v1.0 → Implementación

No es arquitectura. Es registro de avance: qué se implementó, en qué commit, y qué
falta. Una o dos líneas por entrada — el detalle vive en el propio commit y en
[ESTADO.md](ESTADO.md)/[ANEXO-A](ANEXO-A-MATRIZ-TRAZABILIDAD.md) para trazabilidad
de principios.

## Commit 1 — Boundary: Política de Selección de Forma (Adenda A)
✔ `backend/app/services/adaptive_form_selection.py` — `1ba66ed`
✔ Corrección funcional (insumo de Memoria, `formas_ya_mostradas`) — `7c9f8d3`
✔ 13/13 tests, backend importa limpio, cero wiring todavía (módulo inerte)

## Commit 2 — Higiene del repositorio (~8 días integrados en 7 commits)
✔ `d4ccf65` fix(replay): fix de evidencia abandonada (STAB-01)
✔ `9129c53` chore: except silenciosos → logging
✔ `9ebd873` style: tokens de tema oscuro
✔ `503b160` fix(auth): redirect de rol investigador
✔ `b322da0` feat(learning): bloqueo del Post-Test sin ruta completa (IMPL-01)
✔ `c990e74` refactor(docente): retiro de Comparación Swarm (IMPL-02/03)
✔ `a694f3b` fix(users): desacople de Ciclo del pipeline legado
✔ `429f543` refactor(dashboard): recomposición en 4 componentes
✔ `9f2b94e` feat(experience): sub-pasos + botón Ayuda en ModuleExperienceView
✔ Backend importa limpio, frontend build de producción limpio tras cada grupo
□ Pendiente de decisión del usuario, fuera de esta bitácora:
  `backend/scripts/seed_demo_swarm.py` (¿sigue en uso?), `PENDING_FIXES_M1.md`
  y `frontend/--full-page` (descartables, no son trabajo real)

## Commit 3 — Migración del frontend
□ `experienceOrchestrator.ts` deja de decidir la forma; consume
  `seleccionar_forma()` vía el Boundary
□ Conserva solo: renderizado, copywriting, selección de contenido autorado para
  la forma recibida (determinista, sin decisión pedagógica nueva)

## Commit 4 — Wiring
□ `runtime_bridge.py` expone el contrato en la respuesta de cycle-evidence
□ El módulo deja de ser inerte

## Commit 5 — Adenda B (Semántica del Rechazo)
□ Requiere que exista una superficie de consentimiento real (no existe hoy)
□ Solo después de que el wiring esté en producción

## Commit 6 — Validación funcional
□ Repetir el stress-test de escenarios, ahora contra código real
□ Cada escenario debe terminar en el comportamiento que especifican los
  documentos, no en uno inventado durante la implementación
