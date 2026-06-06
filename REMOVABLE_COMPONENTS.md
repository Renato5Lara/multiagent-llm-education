# REMOVABLE COMPONENTS

Esta documentación cataloga archivos y directorios que **pueden ser eliminados de forma segura** de `backend/app/` sin afectar la aplicación en producción. Cada entrada incluye verificación pre-remoción, acción recomendada y verificación post-remoción.

---

## ORPHAN — Sin imports desde producción

### 1. `backend/app/core/agent_health/` (9 files, 1463 LOC)

| File | LOC |
|------|-----|
| `__init__.py` | 0 |
| `adaptive_degradation.py` | 188 |
| `behavioral_baseline.py` | 107 |
| `collective_stability.py` | 212 |
| `health_scorer.py` | 150 |
| `health_score_voter.py` | 80 |
| `meta_monitor.py` | 265 |
| `models.py` | 184 |
| `monitor.py` | 277 |

- **Reason:** ORPHAN — todas las importaciones de `app.core.agent_health` son internas al módulo o desde `tests/test_agent_health.py`. Ningún código de producción (`app/`) lo importa.
- **Confidence:** HIGH
- **Action:** DELETE
- **Pre-removal verification:**
  ```bash
  rg -l "agent_health" backend/app/ --type py | grep -v "backend/app/core/agent_health/"
  # → debe retornar vacío (ningún import externo desde producción)
  ```
- **Post-removal verification:**
  ```bash
  python -c "import app.main"  # debe importar sin error
  pytest tests/test_agent_health.py -x  # fallará esperado (se elimina junto con el módulo)
  ```

---

### 2. `backend/app/sandbox/` (8 files, 1410 LOC)

| File | LOC |
|------|-----|
| `__init__.py` | 45 |
| `ast_policy.py` | 345 |
| `cleanup.py` | 109 |
| `docker_manager.py` | 384 |
| `exceptions.py` | 94 |
| `executor.py` | 291 |
| `metrics.py` | 57 |
| `security_monitor.py` | 85 |

- **Reason:** ORPHAN — todas las importaciones de `app.sandbox` son internas al módulo o desde `tests/test_sandbox_attack.py`. Ningún código de producción lo importa.
- **Confidence:** HIGH
- **Action:** DELETE
- **Pre-removal verification:**
  ```bash
  rg -l "from app\.sandbox\|import app\.sandbox" backend/app/ --type py | grep -v "backend/app/sandbox/"
  # → debe retornar vacío
  ```
- **Post-removal verification:**
  ```bash
  python -c "import app.main"  # debe importar sin error
  ```

---

### 3. `backend/app/swarm_diagnostics/middleware/fastapi.py` (80 LOC)

- **Reason:** ORPHAN — el middleware `SwarmDiagnosticsMiddleware` está definido pero nunca registrado en `main.py` ni en ningún otro lugar. La función `instrument_app()` nunca es llamada. La única referencia a esta clase está dentro de su propio docstring como ejemplo de uso.
- **Confidence:** HIGH
- **Action:** DELETE
- **Pre-removal verification:**
  ```bash
  rg "SwarmDiagnosticsMiddleware" backend/ --type py
  # → solo debe mostrar matches dentro del propio archivo fastapi.py
  rg "swarm_diagnostics\.middleware" backend/app/ --type py
  # → debe retornar vacío (nadie importa este módulo)
  ```
- **Post-removal verification:**
  ```bash
  python -c "from app.swarm_diagnostics import diagnostics_engine; print('OK')"
  pytest tests/test_diagnostics_integration.py -x
  ```

---

### 4. `backend/app/swarm_diagnostics/alerts/` (1 file, 28 LOC)

`alerts/__init__.py`

- **Reason:** ORPHAN — el subpackage `alerts` no es importado por ningún código. Ni `swarm_diagnostics/__init__.py`, ni `core.py`, ni ningún otro archivo lo referencia. Sus reglas de alerta y función `should_alert()` son código muerto.
- **Confidence:** HIGH
- **Action:** DELETE
- **Pre-removal verification:**
  ```bash
  rg "swarm_diagnostics\.alerts\|from.*alerts" backend/ --type py
  # → debe retornar vacío
  ```
- **Post-removal verification:**
  ```bash
  python -c "from app.swarm_diagnostics import diagnostics_engine; print('OK')"
  ```

---

## SUPERSEDED / DUPLICATE — Reemplazado por implementación más nueva

### 5. `backend/app/api/routes/estudiantes.py` (145 LOC)

- **Reason:** SUPERSEDED / DUPLICATE — `estudiantes.py` (prefix `/api/estudiante`) es una versión legacy y menos completa de `students.py` (prefix `/api/students`). Ambos están registrados en `main.py` (líneas 288–289). `students.py` cubre todos los endpoints de `estudiantes.py` (diagnóstico, ruta, módulos, evaluación) más funcionalidad adicional (onboarding, perfil, progreso, tutor IA, análisis de errores).
- **Confidence:** HIGH
- **Action:** DELETE (después de verificar que el frontend no dependa de rutas `/api/estudiante`)
- **Pre-removal verification:**
  ```bash
  # Verificar que ningún endpoint legacy sea llamado por el frontend
  rg "/api/estudiante/" frontend/ 2>/dev/null || echo "No frontend references found"
  rg "estudiantes\.router" backend/app/main.py
  # → Líneas 26 y 288 deben ser las únicas referencias
  ```
- **Post-removal verification:**
  ```bash
  # Comentar líneas 26 y 288 de main.py, luego:
  python -c "import app.main; print('OK')"
  pytest tests/test_courses.py tests/test_consensus_timeouts.py -x
  ```

---

### 6. `backend/app/middleware/idempotency.py` (130 LOC)

- **Reason:** SUPERSEDED — este archivo implementa un sistema de idempotencia legacy con funciones sueltas (`get_idempotency_key`, `check_idempotency`, `complete_idempotency`, `discard_idempotency`). El nuevo sistema de idempotencia vive en `app/events/` con una arquitectura basada en middleware (`app/events/middleware.py`) y servicios dedicados (`app/events/idempotency.py`, `app/events/dedup.py`, `app/events/replay.py`, etc.). Ningún código de producción importa `app.middleware.idempotency`; solo lo usa `tests/test_concurrency.py`.
- **Confidence:** HIGH
- **Action:** DELETE
- **Pre-removal verification:**
  ```bash
  rg "from app\.middleware\.idempotency\|app\.middleware\.idempotency" backend/app/ --type py
  # → debe retornar vacío (solo tests lo usan)
  ```
- **Post-removal verification:**
  ```bash
  python -c "import app.main; print('OK')"
  pytest tests/test_idempotency.py tests/test_idempotency_distributed.py -x
  ```

---

## ARCHIVE CANDIDATES — Útiles como referencia, no parte de producción

### 7. `backend/app/experiment/` (17 files, ~6872 LOC)

- **Reason:** STANDALONE RESEARCH CODE — todo el package `app.experiment` solo es importado por:
  - Su propio código interno
  - Scripts standalone en `backend/scripts/` (no parte de la app)
  - Archivos de test

  Ningún archivo de producción (`app/main.py`, servicios, API routes, agentes) importa `app.experiment`. Este código fue diseñado para ejecutar experimentos académicos/benchmarks y no está conectado al flujo principal.
- **Confidence:** MEDIUM (podría quererse mantener para investigación reproducible)
- **Action:** ARCHIVE (mover a `experiments/` en la raíz del proyecto o a un repo separado)
- **Verification:**
  ```bash
  rg "from app\.experiment" backend/app/ --type py | grep -v "backend/app/experiment/"
  # → debe retornar vacío
  ```

### 8. `backend/scripts/` (6 files, ~1524 LOC)

- **Reason:** UTILITY SCRIPTS — estos scripts ejecutan benchmarks, experimentos y validación de entorno. No son parte de la aplicación en producción. Se ejecutan manualmente desde CLI.
- **Confidence:** MEDIUM
- **Action:** ARCHIVE or KEEP (legítimamente útiles para desarrollo/investigación)

---

## VERIFICADO: NO REMOVIBLE

| Componente | Estado | Evidencia |
|-----------|--------|-----------|
| `app/swarm_diagnostics/` | **EN USO** | Importado por `main.py`, `observability/`, `core/consensus.py`, `agents/base.py`, `memory/shared_memory.py`, `experiment/`, `swarm/synchronization.py`, `db/locks.py`, etc. (246 matches) |
| `app/core/consensus_timeouts.py` | **EN USO** | Importado por `core/consensus.py` (lazy), `core/consensus_timeout_middleware.py`, `swarm_diagnostics/detectors/consensus_timeout.py` |
| `app/core/consensus_timeout_middleware.py` | **EN USO** | Importado por `tests/test_consensus_timeouts.py` y `core/consensus.py` (lazy) |
| `app/core/consensus_timeout_metrics.py` | **EN USO** | Importado por `core/consensus_timeout_middleware.py` y `tests/test_consensus_timeouts.py` |
| `app/core/consensus_cancellation.py` | **EN USO** | Importado por `core/consensus.py` (lazy), `core/consensus_timeout_middleware.py`, `core/consensus_timeout_metrics.py` |
| `app/core/specialization.py` | **EN USO** | Importado por `services/adaptive_service.py`, `core/consensus.py`, `core/weighting.py`, `swarm/orchestrator.py`, `experiment/` |
| `app/core/trust.py` | **EN USO** | Importado por `services/adaptive_service.py`, `core/weighting.py`, `experiment/` |
| `app/core/weighting.py` | **EN USO** | Importado por `core/consensus.py` (lazy), `swarm/orchestrator.py` |
| `app/core/security.py` | **EN USO** | Importado por `services/auth_service.py`, `api/deps.py`, `services/user_service.py` |
| `app/events/replay.py` | **EN USO** | Importado por `events/__init__.py` y `api/routes/idempotency.py` |
| `app/events/risk_detectors.py` | **EN USO** | Importado por `events/__init__.py` y `api/routes/idempotency.py` |
| `app/events/propagation_ttl.py` | **EN USO** | Importado por `events/__init__.py` |
| `app/events/types.py` | **EN USO** | Importado por 5 servicios diferentes |
| `app/tracing/propagation.py` | **EN USO** | `TraceLoggingFilter` usado en `main.py` línea 73–74; `propagation_guard`, `sanitize_inbound_headers`, `sanitize_outbound_headers` re-exportados desde `tracing/__init__.py` |
| `app/models/deprecated/prerequisite.py` | **NO EXISTE** | El path `app/models/deprecated/` no existe en el código base |

---

## RESUMEN

| Acción | Componente | LOC | Ahorro |
|--------|-----------|-----|--------|
| DELETE | `app/core/agent_health/` | 1,463 | ~1.5K |
| DELETE | `app/sandbox/` | 1,410 | ~1.4K |
| DELETE | `app/api/routes/estudiantes.py` | 145 | ~0.1K |
| DELETE | `app/middleware/idempotency.py` | 130 | ~0.1K |
| DELETE | `app/swarm_diagnostics/middleware/fastapi.py` | 80 | ~0.1K |
| DELETE | `app/swarm_diagnostics/alerts/` | 28 | ~0.03K |
| ARCHIVE | `app/experiment/` | ~6,872 | ~6.9K |
| **TOTAL removible (DELETE)** | | **~3,256** | **~3.3K** |
| **TOTAL archiveable** | | **~6,872** | **~6.9K** |

> **Nota:** Los scripts en `backend/scripts/` (~1,524 LOC) son utilidades CLI independientes; no se recomienda eliminarlos pero están fuera del alcance de producción.
