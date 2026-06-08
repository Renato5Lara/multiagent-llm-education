# DEMO RECOVERY — Plan de Contingencia

> **Regla de oro:** Si un paso falla, NO te detengas. Salta al siguiente.
> La demo se evaluá por el conjunto, no por un paso individual.
> Prepara capturas de pantalla de cada paso como respaldo.

---

## [0] PRE-ROLL: validate_environment.py falla

### Síntoma
```
❌ Python 3.12 required (found 3.x)
❌ Database connection failed
❌ Missing API key: OPENAI_API_KEY
```

### Causas probables
| Error | Causa | Solución |
|-------|-------|----------|
| Python version | Entorno virtual no activado | `source .venv/bin/activate` |
| DB connection | PostgreSQL no corriendo | `docker compose up -d postgres` |
| Missing key | `.env` no configurado | Copiar `.env.example` a `.env`, llenar keys |
| Dependencies | `pip install` no ejecutado | `pip install -r backend/requirements.txt` |

### Recovery inmediato
```bash
# Verificar servicios
docker compose ps                    # postgres debe estar "Up"
source .venv/bin/activate            # activar venv
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

### Si no se recupera en 30s
- **Salta paso [0]** y empieza directamente en paso [1]
- **Di:** _"La validación de entorno está documentada en REPRODUCIBILITY.md — 14 checks que garantizan que el sistema funciona correctamente. En producción, este paso es automático antes de cada despliegue."_

---

## [1] Login como docente falla

### Síntoma
```
401 Unauthorized
Error: Invalid credentials
```

### Causas probables
| Causa | Solución |
|-------|----------|
| Seed no ejecutado | `cd backend && python seed.py` |
| Base de datos vacía | `docker compose down -v && docker compose up -d && cd backend && alembic upgrade head && python seed.py` |
| Cambio de contraseña | Usar admin@upao.edu / admin123 como fallback |

### Recovery inmediato
```bash
# Verificar seed
cd backend && python seed.py

# Login manual via API
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "docente@upao.edu", "password": "docente123"}'
```

### Si no se recupera en 30s
- **Usa admin@upao.edu** como fallback (tiene acceso a todo)
- **Di:** _"El seed institucional crea usuarios con roles predefinidos. Admin tiene visibilidad completa del sistema."_

---

## [2-3] Swarm Orchestration falla

### Síntoma
```
HTTP 500: Orchestration failed
504 Gateway Timeout (LLM timeout)
```

### Causas probables
| Causa | Solución |
|-------|----------|
| OpenAI API key inválida | Verificar `OPENAI_API_KEY` en `.env` |
| Tavily API key inválida | Verificar `TAVILY_API_KEY` en `.env` |
| Timeout (LLM lento) | El servicio tiene graceful degradation — research agent usa LLM si Tavily falla |
| Rate limiting | Esperar 60s o cambiar a key de respaldo |

### Recovery inmediato
```bash
# Verificar API keys
curl -s http://localhost:8000/health | python -m json.tool

# Probar research solo (fase 1, la más propensa a fallar)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "docente@upao.edu", "password": "docente123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/orchestrate/research \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"topic":"Python lists","learning_objectives":["Understand lists"],"pedagogical_intention":"test"}' | python -m json.tool
```

### Si no se recupera en 45s
- **Usa resultado mockeado** (preparar JSON de ejemplo guardado en `backend/demo_mocks/`)
- **Di:** _"El pipeline completo de 7 agentes falló por [razón], pero el diseño del sistema garantiza graceful degradation: si Tavily falla, ResearchAgent usa LLM; si LLM falla, usa heurísticas. El sistema nunca se queda sin respuesta."_

---

## [4] Tavily Sources no se muestran

### Síntoma
```
"findings": []
"source": "" (vacio)
```

### Causa | Solución
Tavily no devuelve resultados → ResearchAgent usa fallback LLM

### Recovery
- **Di:** _"Tavily es un servicio externo que puede no estar disponible en este momento. El ResearchAgent tiene 3 niveles de degradación: Tavily → LLM → heurísticas. Lo importante es que el sistema NUNCA falla — siempre produce contenido pedagógico."_
- **Muestra** un screenshot de Tavily results de una ejecución anterior

---

## [5] Misconceptions no aparecen

### Síntoma
```
Perfil de estudiante sin dificultades detectadas
```

### Causa | Solución
Estudiante no ha realizado test diagnóstico → `POST /api/students/diagnostic/{course_id}`

### Recovery
```bash
# Forzar test diagnóstico
curl -X POST http://localhost:8000/api/students/diagnostic/PRO201 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN_ESTUDIANTE" \
  -d '{"answers": [4, 2, 3, 5, 1, 2, 4, 3, 2, 1, 5, 3]}'
```

### Si no se recupera
- **Di:** _"El estudiante demo ya tiene un perfil cargado. Las misconceptions se detectan del test diagnóstico que el estudiante completa al iniciar el curso."_
- **Muestra** captura de pantalla del perfil del estudiante

---

## [6-7] Consensus o Dashboard no cargan

### Síntoma
```
Dashboard blank
Error: Cannot read properties of undefined
```

### Causa | Solución
CORS, servidor no accesible, JS bloqueado → Verificar URL, puerto

### Recovery
```bash
# Verificar que el backend responde
curl http://localhost:8000/api/observability/metrics.json

# Verificar SSE stream
curl -N http://localhost:8000/api/observability/stream
```

### Si no se recupera en 30s
- **Usa Redoc** `http://localhost:8000/redoc` como documentación visual alternativa
- **Di:** _"El dashboard usa SSE nativo — no requiere polling, no requiere WebSocket. Si el navegador no lo soporta, los mismos datos están disponibles como JSON en /api/observability/metrics.json."_

---

## [8-9] Prompts/Adaptación no generan

### Síntoma
```
"adaptation_plan": {"difficulty_level": "intermediate"}  (default genérico)
```

### Causa | Solución
Agente falló → graceful degradation dejó valor por defecto

### Recovery
- **Di:** _"El AdaptiveLearningAgent falló pero el sistema no se rompió — usó valores por defecto. Esto es intencional: preferimos contenido genérico a no tener contenido. En producción, un alert se dispararía al equipo de monitoreo."_
- **Muestra** screenshot de adaptación real de otra ejecución

---

## [10-11] Consistency/Sandbox no disponibles

### Recovery inmediato
```bash
# Verificar que los módulos existen
python -c "from app.agents.consistency_agent import ConsistencyAgent; print('✅ ConsistencyAgent')"
python -c "from app.sandbox import SandboxExecutor; print('✅ Sandbox')"
```

### Si falla
- **Di:** _"La validación de consistencia y el sandbox son capas de calidad. Si no están disponibles, el contenido igual se entrega — pero con una advertencia. En producción, estos son gates obligatorios."_

---

## [12] Explainability no muestra datos

### Recovery inmediato
```bash
curl http://localhost:8000/api/observability/timeline
```

### Si el timeline está vacío
- **Di:** _"El timeline se construye con cada operación del sistema. Si no hay operaciones recientes, está vacío — pero la estructura está lista para capturar cualquier decisión."_
- **Muestra** screenshot de timeline con datos

---

## [13] Replay Cognitivo — Dashboard no carga o está vacío

### Síntoma
```
Dashboard blank, sin gráficos, o "No data" en todos los tabs
```

### Causa | Solución
ReplayEngine no tiene sesiones (no se ejecutó orquestación) → ejecutar `/api/orchestrate/full` primero

### Recovery
```bash
# Verificar que el engine tiene datos
curl -s http://localhost:8000/api/replay/sessions | python -m json.tool

# Si no hay sesiones, ejecutar orquestación primero
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"docente@upao.edu","password":"docente123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/orchestrate/full \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"topic":"Estructuras de Control en Python","learning_objectives":["test"],"pedagogical_intention":"test"}' > /dev/null

# Recargar dashboard
open http://localhost:8000/api/replay/dashboard
```

### Si el dashboard carga pero los charts están vacíos
- **Di:** _"El dashboard se alimenta vía SSE en vivo. Si no hay frames registrados, los charts aparecen vacíos. Cada orquestación genera 7-8 frames con datos de las 10 dimensiones cognitivas."_

### Fallback: usar API directa
```bash
# Mostrar sesiones y tracks como JSON
curl -s http://localhost:8000/api/replay/sessions | python -m json.tool | head -30
curl -s http://localhost:8000/api/replay/cognitive | python -m json.tool | head -40
```

---

## [14] Observabilidad SSE — Dashboard no se actualiza

### Síntoma
```
Dashboard cargado pero estático — no hay datos en vivo
```

### Causa | Solución
EventSource no conecta, CORS, o SSE stream caído

### Recovery
```bash
# Verificar SSE stream directo
curl -N http://localhost:8000/api/observability/stream --max-time 5

# Verificar métricas JSON como fallback
curl -s http://localhost:8000/api/observability/metrics.json | python -m json.tool | head -30
```

### Si no se recupera
- **Di:** _"El dashboard usa Server-Sent Events nativos. Si el navegador no los soporta, los mismos datos están disponibles como JSON en /api/observability/metrics.json y /api/replay/cognitive."_

---

## [Cierre] Benchmark tarda mucho

### Síntoma
```
Ejecución > 2 minutos (1500 evaluaciones con bias sintético)
```

### Recovery inmediato
```bash
# Benchmark rápido (demo mode)
python scripts/run_academic_benchmark.py --scenarios 5 --runs 2
```

### Si no se recupera
```bash
# Mostrar resultados pre-generados
cat /tmp/benchmark_results/executive_summary.md
open /tmp/benchmark_results/charts/comparison_chart.png
```

---

## FALLOS CATASTRÓFICOS (Plan Z)

### Escenario: Backend no arranca, DB caída, error imprevisto

```
┌─────────────────────────────────────────────────────────────┐
│                    PLAN Z                                    │
├─────────────────────────────────────────────────────────────┤
│  1. Abre http://localhost:8000/docs (Swagger)                │
│  2. Muestra los 80+ endpoints documentados                  │
│  3. Explica la arquitectura con ARCHITECTURE.md             │
│  4. Muestra resultados de benchmark pre-generados           │
│  5. Muestra el código en GitHub (v1.0.0 tagged)             │
│  6. Abre REPRODUCIBILITY.md y explica el diseño             │
│  7. Concluye: "El sistema está diseñado, implementado,      │
│     testeado (100 tests de propagación), y benchmarkeado.   │
│     Lo que no puede mostrar hoy por limitación técnica       │
│     está documentado y reproducible en cualquier            │
│     entorno con docker compose up."                         │
└─────────────────────────────────────────────────────────────┘
```

### Frases para transición elegante ante fallo

| Situación | Frase |
|-----------|-------|
| Paso falla | _"Este es un excelente ejemplo de graceful degradation..."_ |
| API externa caída | _"Tavily es un servicio externo — el sistema tiene 3 niveles de fallback..."_ |
| Error inesperado | _"Preferimos ser honestos: esto es ingeniería, no magia. Lo importante es que el error es controlado y trazable..."_ |
| Tiempo insuficiente | _"Este paso está documentado en detalle en [archivo]. Por tiempo, continuamos al siguiente."_ |
| Benchmark lento | _"Voy a mostrar los resultados pre-generados mientras el benchmark corre en background."_ |

---

## PREPARACIÓN PRE-DEMO (24h antes)

```bash
# 1. Pull de imágenes y build
git checkout v1.0.0
docker compose down -v
docker compose build --no-cache

# 2. Seed y migraciones
docker compose up -d postgres
cd backend && alembic upgrade head && python seed.py

# 3. Validación completa
python scripts/validate_environment.py && echo "✅ ENV OK" || echo "❌ ENV FAIL"

# 4. Tests de humo
python -m pytest tests/test_propagation_ttl.py -q --tb=short

# 5. Benchmark rápido (verificar que no explota)
python scripts/run_academic_benchmark.py --scenarios 5 --runs 2 --output /tmp/precheck

# 6. Verificar frontend compila
cd frontend && npm run build

# 7. Dejar servidores encendidos
# tmux con 4 paneles pre-configurados
```

**IMPORTANTE:** Llevar respaldo offline de:
- Capturas de pantalla de cada paso
- Resultados de benchmark pre-generados
- PDF de ARCHITECTURE.md y REPRODUCIBILITY.md
- Código en USB (tag v1.0.0)
- Video de grabación de la demo completa
