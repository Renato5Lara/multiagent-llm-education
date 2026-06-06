# RELEASE v1.0.0 — UPAO-MAS-EDU

**Fecha:** 2026-06-01
**Versión:** 1.0.0
**Estado:** ESTABLE — Sustentación Académica

---

## 1. Release Checklist

### 1.1 Código
- [x] `main` branch congelado
- [x] Todos los tests pasan: `pytest tests/ -q` → 1566 passed, 89 propagation TTL
- [x] Linting limpio: `ruff check .`
- [x] Sin dependencias rotas
- [x] Sin credenciales hardcodeadas
- [x] `.env.example` refleja todas las variables
- [x] `requirements.txt` frozen en `requirements.lock`

### 1.2 Base de Datos
- [x] Migraciones Alembic aplicadas: `alembic upgrade head`
- [x] Seed data ejecutable: `python seed.py`
- [x] Schema actualizado (13 migrations)
- [x] Rollback probado: `alembic downgrade -1`

### 1.3 Docker
- [x] `docker-compose.yml` funcional
- [x] `Dockerfile` build exitoso
- [x] Health checks configurados
- [x] Volúmenes persistentes

### 1.4 Frontend
- [x] Build production: `npm run build`
- [x] TypeScript check: `tsc -b`
- [x] Lint: `eslint .`
- [x] Static assets servidos correctamente

### 1.5 Despliegue
- [x] `render.yaml` configurado
- [x] Variables de entorno documentadas
- [x] CORS configurado para producción
- [x] HTTPS/TLS funcional

### 1.6 Documentación
- [x] `RELEASE.md` — este archivo
- [x] `DEPLOYMENT.md` — guía de despliegue
- [x] `REPRODUCIBILITY.md` — reproducibilidad
- [x] `SYSTEM_OVERVIEW.md` — visión general
- [x] `ARCHITECTURE.md` — arquitectura detallada
- [x] `DEMO_GUIDE.md` — guía de demostración

---

## 2. Descripción

UPAO-MAS-EDU es un sistema multi-agente con inteligencia de enjambre
para educación personalizada en programación. Utiliza LangGraph para
orquestar agentes pedagógicos, consenso determinista para toma de
decisiones, y memoria compartida para aprendizaje colectivo.

### 2.1 Capacidades Principales

| Capacidad | Estado |
|-----------|--------|
| Swarm pedagógico orquestado | ✅ Estable |
| Consenso determinista multi-voto | ✅ Estable |
| Memoria compartida con TTL | ✅ Estable |
| Tracing distribuido W3C | ✅ Estable |
| Diagnóstico automático (22 detectores) | ✅ Estable |
| Eventos idempotentes | ✅ Estable |
| Replay de eventos | ✅ Estable |
| Sandbox de evaluación | ✅ Estable |
| SSE streaming en tiempo real | ✅ Estable |
| Benchmark reproducible | ✅ Estable |
| Retrieval pedagógico (Tavily) | ✅ Estable |
| Explainability endpoints | ✅ Estable |
| Bug reports automáticos | ✅ Estable |

### 2.2 Framework de Agentes

- **5 nodos**: diagnostic_analyzer → path_planner → content_recommender
  → evaluation_generator → risk_analyzer
- **3 nodos programación**: pseudocode_analyzer → debug_analyzer → ct_assessor
- **Swarm real**: 9 fases with 10+ tipos de agente pedagógico

---

## 3. Artefactos de la Release

```
RELEASE.md                  # Este archivo
DEPLOYMENT.md              # Guía de despliegue
REPRODUCIBILITY.md         # Protocolo de reproducibilidad
SYSTEM_OVERVIEW.md         # Visión general del sistema
ARCHITECTURE.md            # Arquitectura detallada
DEMO_GUIDE.md              # Guía de demostración
backend/requirements.lock  # Dependencias congeladas
backend/scripts/validate_environment.py  # Validación de entorno
docker-compose.yml         # Docker compose desarrollo
docker-compose.prod.yml    # Docker compose producción
```

---

## 4. Versiones de Dependencias

| Componente | Versión |
|-----------|---------|
| Python | 3.12+ |
| FastAPI | 0.136.1 |
| SQLAlchemy | 2.0.49 |
| LangGraph | 1.2.0 |
| PostgreSQL | 16 |
| React | 19.2.6 |
| Vite | 8.0.12 |
| TypeScript | 6.0.2 |
| Node.js | 22+ |

---

## 5. Notas de la Release

### 5.1 Cambios desde versión anterior
- 1169+ tests implementados y pasando
- Sistema de propagación TTL completamente auditado y corregido
- 22 detectores de anomalías en diagnóstico de enjambre
- Consenso determinista con 4+ voters
- Memoria compartida con lineage tracing

### 5.2 Limitaciones Conocidas
- PostgreSQL required (no SQLite en producción)
- Tavily API key opcional (retrieval externo)
- OpenAI/Anthropic API key requerida para LLM
- Rate limiting básico por IP (no Redis distribuido)

### 5.3 Seguridad
- JWT con refresh token rotation
- Idempotency-Key para mutaciones
- Rate limiting por endpoint de autenticación
- CORS restringido a orígenes configurados
- Tokens con iat, nbf, jti, type claims
