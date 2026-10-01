# Índice de evidencia experimental — PoC `adaptation_swarm` (2026-09-23)

Todo lo listado está en este paquete con su sha256 (`MANIFEST.sha256`; verificar con
`python -m adaptation_swarm.tools.build_evidence_package --verify <este_directorio>`). Estados: **DEMOSTRADO** (medido, con evidencia) ·
**DEPENDE DE PERSONAS** (no se puede demostrar con software) · **ABIERTO** (resultado medido que no alcanza el umbral).

## 1. Congelado (no se edita, no se re-ejecuta sobre el mismo `run_label`)
| corrida | biblioteca | casos | F1_adapt | CR | evidencia |
|---|---|---|---|---|---|
| `corrida-poc-1` | lib-v5-9ae9ffdd | 100 | **0.8031** (IC95 0.711–0.877) | 1.00 | `02_corridas_y_auditorias/adaptation_swarm_corrida-poc-1*.json/csv`, `db_corrida-poc-1_*` |
| `corrida-poc-2` | lib-v9-a0231e9b | 100 | **0.8031** (IC95 0.711–0.877) | 1.00 | `…corrida-poc-2*`, `db_corrida-poc-2_*` |
Ambas con la misma configuración (semilla 20260923, N=20, w=0.729, c1=c2=1.494, ε=0.001, k_max=15, α/β/γ/δ=.40/.30/.15/.15, dataset `profiles-v1`).
La única variable que difiere es la versión de biblioteca. **Ninguna etiqueta predicha cambió entre ambas** (0/100): el F1 idéntico no es un ajuste,
es un resultado estable frente a la mejora de artefactos. `lib-v10-5dd83cd4` (C++ 90/90) es posterior y NO se usó en ninguna corrida.

## 2. DEMOSTRADO
- **Arquitectura AG0–AG4 sobre Redis + LangGraph**, ciclo completo por perfil (100/100 ciclos, 0 fallos): `03_informes/IMPLEMENTATION-PHASE1/2-REPORT`.
- **PSO** con las ecuaciones de la asesoría, φ, p_best/g_best, parada literal (ε=0.001, k_max=15): `k_stop` medio 1.65 (poc-1) y 1.79 (poc-2), máx 4 y 5; CR=1.00.
- **Diagnóstico del PSO** (`PSO-AUDIT-corrida-poc-1.md`): g_best no cambia tras la inicialización en 48 % de los ciclos; la búsqueda mejora 𝓕 sobre la mejor partícula inicial en 52 %.
- **Artefactos multimodales reales**: código Python y C++ (compilado y ejecutado en sandbox), diagramas Mermaid **renderizados a SVG** (270/270), texto validado semánticamente, audio TTS real; 100/100 paquetes válidos en poc-2 (`04`/`02`).
- **Validación semántica**: sobre lib-v5 detectó 53/90 código, 6/90 texto, 15/270 diagramas con hallazgos; lib-v9/v10: 0/0/0 (`library_semantic_audit_*.json`).
- **Auditoría de F1** (`F1-AUDIT-corrida-poc-1/2.md`): sin bug; F1 = F1 del óptimo global de 𝓕 (0.803); argmax(W) = 0.615; 13 errores por W≠gold, 6 por Coher/Redund/CostT.
- **Rendimiento** (Locust y JMeter, 5 escenarios × {1, 4 workers}, `04_carga/`): 1 worker ≈ 16 req/s, P95@25 usuarios ≈ 2.2 s; 4 workers ≈ 41 req/s, P95@25 ≈ 1.1 s; 0 % errores. Generador y servidor comparten host (8 CPU).
- **Reproducibilidad**: `05_documentacion/REPRODUCIBILITY.md`; cadena Alembic verificada desde BD vacía con el bootstrap documentado; biblioteca verificable por hash (`multimodal.verify`).

## 3. ABIERTO (medido; no alcanza el umbral con la configuración cerrada)
- **RNF03 F1_adapt ≥ 0.85**: 0.8031 en ambas corridas. Es una propiedad de la definición (gold por centroide vs. W muestreado + 𝓕), no un defecto de implementación.
  No se ajustaron pesos, gold, regla de parada ni distribución para modificarlo; cualquier cambio requiere una decisión formal nueva y se reportaría como post-hoc.
- **RNF01/RNF04 con 1 worker**: no cumplen (P95@25 ≈ 2.2 s; ≈ 16 req/s). Cumplen con 4 workers (configuración declarada).
- **RNF02 T_conv ≤ 15**: satisfecho (máx 5) pero tautológico por `k_max=15`; el CR=1.00 está inflado por la parada literal en plateaus (DEC-10).

## 4. DEPENDE DE PERSONAS (PENDIENTE DE RECOLECCIÓN HUMANA)
- **RNF05 SUS > 75** (n ≥ 10 docentes/ingenieros): infraestructura lista (`sus_cli`, tablas vacías); **0 respuestas**.
- **Validación del gold por el panel** (20 celdas, acuerdo/κ de Fleiss): infraestructura lista; **0 valoraciones**.
- Hasta que existan participantes reales, ni SUS ni el acuerdo del panel pueden reportarse; no se simulan.
