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

## Commit 3 — Wiring + migración del frontend
✔ `91e7ea4` (3a) — `/cycle-evidence` llama a `seleccionar_forma()`, aditivo
  puro; `CycleEvidenceSubmit.formas_ya_mostradas` nuevo, aún vacío desde el
  frontend en este punto. El módulo del Commit 1 deja de estar inerte.
✔ `b45c9ae` (3b) — `experienceOrchestrator.ts` consume
  `runtime_decision.forma.tipo` como fuente primaria;
  `REINFORCEMENT_BY_MODALITY`/`resolveReinforcementPriority` quedan solo de
  fallback (Boundary sin recomendación reconocible, o sin contenido
  autorado para la forma recomendada). `visitedReinforcements` ahora viaja
  como `formas_ya_mostradas` en cada request — cierra el círculo con la
  corrección funcional del commit `7c9f8d3`.
✔ Orden invertido respecto al plan original (wiring antes que frontend) por
  seguridad: evita un adaptador frontend apuntando a un campo que el
  backend todavía no envía.
✔ 17/17 tests backend, tsc limpio, eslint sin errores nuevos, build de
  producción exitoso. Sin cambio de comportamiento observable: misma
  prioridad, ahora en el Boundary en vez de en el cliente.

## Deuda técnica registrada (no se resuelve ahora)
□ `REINFORCEMENT_BY_MODALITY`/`resolveReinforcementPriority`
  (`experienceOrchestrator.ts`) quedan como fallback local desde el Commit 3.
  Cuando el Boundary pueda recomendar todas las formas del catálogo de PP4 y
  todos los ciclos estén completamente adaptados con contenido autorado para
  cada una, evaluar eliminar definitivamente el fallback — no antes.

## Commit 4 — Infraestructura de la Adenda B (no "Adenda B completa")
□ [NOTA-INTERACCION-CONSENTIMIENTO.md](NOTA-INTERACCION-CONSENTIMIENTO.md) ya
  cerró las 2 decisiones que faltaban — desbloqueado.
□ Ámbito: contrato, persistencia (Memoria del rechazo), eventos, pruebas —
  aunque ningún caso real del runtime la active todavía (ninguna prioridad
  de `_PRIORIDAD_POR_MODALIDAD` selecciona `codigo_guiado`/`narracion_tutor`
  hoy; ver NOTA §3). Misma situación en la que estuvo
  `adaptive_form_selection.py` entre el Commit 1 y el Commit 3 — construir
  la infraestructura ahora evita tener que tocar varias capas a la vez
  cuando una prioridad futura sí la active.
□ Oferta proactiva (esto) y solicitud voluntaria (botón Ayuda) quedan
  desacopladas por diseño — un rechazo nunca bloquea la segunda (NOTA §7).

## Commit 5 — Validación funcional
□ Repetir el stress-test de escenarios, ahora contra código real
□ Cada escenario debe terminar en el comportamiento que especifican los
  documentos, no en uno inventado durante la implementación
