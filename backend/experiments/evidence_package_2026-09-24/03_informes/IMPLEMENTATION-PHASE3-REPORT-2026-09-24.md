# Fase 3 — Cierre de ingeniería y preparación de evidencia (2026-09-24)

Sin commits, sin reset/clean, sin tocar F1/gold/pesos/PSO/regla de parada. `corrida-poc-1` y `corrida-poc-2` intactas (pruebas `test_corrida_poc_1_preserved` y hashes del paquete).

## Estados
| Punto del plan | Estado | Evidencia |
|---|---|---|
| Concepto sin C++ | **VERIFICADO** — `lib-v10-5dd83cd4`: C++ 90/90 (hint `std::variant` para parámetros de tipos mixtos); `verify` OK | manifiesto `lib-v10` |
| Duplicación biblioteca/caché | **IMPLEMENTADO (dry-run)** — `tools/dedupe_library`: ahorro potencial ≈768 MB por enlaces duros verificados por hash. **No aplicado**: requiere aprobación | `python -m adaptation_swarm.tools.dedupe_library` |
| Entorno reproducible | **VERIFICADO** — `REPRODUCIBILITY.md`, `repro_db_bootstrap.sh`, `pip freeze` en el paquete | |
| Versionado del stack CMG + migraciones previas | **PLAN escrito, NO ejecutado** — `GIT-COMMIT-PLAN-2026-09-24.md` | |
| poc-1/poc-2 congeladas | **VERIFICADO** — sha256 en `MANIFEST.sha256`; pruebas de congelación | |
| Paquete de evidencia limpio | **VERIFICADO** — `backend/experiments/evidence_package_2026-09-23/` (127 archivos; no se sobrescribe; `--verify`) | |
| F1 / gold / pesos / PSO / parada | **NO TOCADOS** (F1_adapt = 0.8031, RNF03 no cumplido) | |
| Infra SUS/panel para ≥10 evaluadores | **IMPLEMENTADO** — instrumento ES, guion v1, protocolo del panel, consentimiento, plantillas CSV (SUS y 20 celdas gold), `sus_cli import-sus/import-gold` (todo o nada, exige consentimiento y rol válido). Plantillas vacías importan 0 filas | `adaptation_swarm/human_eval/`, `test_sus_panel.py` |
| Datos SUS / panel | **PENDIENTE DE RECOLECCIÓN HUMANA** (0 participantes, 0 valoraciones; nada inventado) | |
| Suite | **VERIFICADO**: `tests/adaptation_swarm` 201 passed | |

## Demostrado vs dependiente de personas
- **Demostrado (ejecutado, medido):** arquitectura AG0–AG4 sobre Redis+LangGraph; PSO literal; 100/100 ciclos, CR=1.00; F1_adapt 0.8031 (IC95 0.711–0.877) idéntico en dos bibliotecas; carga: 4 workers ≈41 req/s, P95@25 ≈1.1 s, 0 % errores; biblioteca M1 real (Python, C++, Mermaid+SVG, texto, TTS); reproducción desde BD vacía.
- **No cumplido:** RNF03 (0.803 < 0.85); RNF01/RNF04 solo con 4 workers; RNF02 tautológico (k_max=15).
- **Depende de humanos:** RNF05 (SUS, n≥10, media>75), validación del gold por panel (κ), toda conclusión sobre utilidad percibida.

## Observaciones / limitaciones
- El guion de tareas no tiene visor HTML dedicado (se usa `run_slice --json` + artefactos de la biblioteca); declarado como pendiente, no implementado.
- La versión ES del SUS y el consentimiento son plantillas sin validar (DEC-16).
- El paquete de evidencia fue construido antes de añadir `human_eval/` y el plan de commits; si se requiere que los contenga, generar un paquete nuevo con otro nombre (nunca sobrescribir).

## Necesita tu aprobación explícita
1. `dedupe_library --apply` (hardlinks, no borra contenido).
2. Ejecutar los commits del plan (y decidir biblioteca: LFS/externo/ignore).
3. Cualquier archivo/versión a archivar (`lib-v2`, `lib-v3`, etc.).
4. Cualquier cambio de F1/regla de parada → decisión formal nueva y corrida nueva, declarada como post-hoc.
