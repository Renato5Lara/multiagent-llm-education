# adaptation_swarm

PoC de la asesoría del 23/09/2026: arquitectura multiagente (AG0–AG4) con PSO para adaptar contenido multimodal.
Especificación: `DECISION-CLOSURE-2026-09-23.md`. Decisiones técnicas y limitaciones: `docs/architecture/ADR/ADR-0019-*.md`.

```
perfil JSON ─▶ AG0 (LangGraph) ─Redis Streams─▶ AG1 W · AG2 código · AG3 diagrama · AG4 texto+audio(TTS)
                     │  PSO (pso/) → 𝓕 (fitness/) → p_best/g_best → convergencia → MultimodalPackage
                     └─▶ PostgreSQL (swarm_*, agent_messages, multimodal_*)
```

## Requisitos
Redis (`podman-compose up -d redis` / `docker compose up -d redis`), PostgreSQL con `alembic upgrade head`,
`OPENAI_API_KEY` (generación de la biblioteca y TTS), sandbox podman/docker (`SWARM_SANDBOX_BIN`, por defecto `podman`).

## Comandos (desde `backend/`)
```
python -m adaptation_swarm.profiles.build_dataset          # 100 perfiles + gold (datasets/synthetic_profiles/)
python -m adaptation_swarm.multimodal.builder --all-mapped # biblioteca M1 real (LLM + sandbox + TTS)
python -m adaptation_swarm.run_slice                       # vertical slice (Visual-Dominant × Bucles)
python -m adaptation_swarm.run_experiment --sweep          # sensibilidad pre-registrada
python -m adaptation_swarm.run_experiment --run-label X    # 100 casos + F1/CR/calidad de búsqueda
pytest tests/adaptation_swarm                              # 130+ pruebas (Redis/Postgres/OpenAI/sandbox reales)
```
Carga (Locust/JMeter): ver `backend/loadtest/README.md`.
