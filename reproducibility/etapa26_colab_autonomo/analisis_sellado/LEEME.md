# Scripts de análisis sellados (copia legible)

Copia, byte a byte, de los scripts que viajan dentro de los paquetes publicados (`../../etapa23_oe1_oe5/paquetes/*.zip`) y que los notebooks ejecutan. Están aquí **solo para poder leerlos sin descomprimir**; los notebooks siguen usando los de dentro de cada paquete (cuyo hash verifican). Los nueve scripts de análisis son idénticos a los sellados en `04_ANALISIS_ESTADISTICO` de la tesis (verificado el 2026-11-16); `recomputo_http.py` solo existe en los paquetes.

Hashes: `SHA256SUMS.txt`. La prueba `tests/test_repro.py` comprueba que coinciden con el contenido de los zip.

| Script | Objetivo | Qué hace |
|---|---|---|
| `analisis_oe1.py` | OE1 | Puntaje de cumplimiento S, confiabilidad I-13 (Wilson), eficiencia, F1_adapt, contrastes pareados, correlaciones intrabloque, interferencia |
| `analisis_oe2a.py` | OE2-A | Convergencia I-02 (media geométrica por perfil, IC t y bootstrap), tasa de convergencia, latencia y throughput en proceso, estabilidad |
| `analisis_oe2b.py`, `analisis_exploratorio_oe2b.py` | OE2-B | Indicadores por carga con IC (pre-registrado) y estratificación exploratoria |
| `analisis_oe3.py` | OE3 | Efectos principales, factorial con interacciones, Friedman, deriva, sensibilidad, entorno |
| `analisis_oe4.py`, `exploratorio_interferencia_oe4.py` | OE4 | ANOVA por bloques, contrastes con Holm, celdas; exploratorio de interferencia |
| `analisis_oe5.py`, `analisis_oe5_enmienda1.py` | OE5 | F1_adapt por perfil, IC, pruebas frente a 0,85; dependencia entre réplicas (enmienda 1) |
| `recomputo_http.py` | OE1, OE2-B, OE4 | Recalcula los 12 indicadores por corrida desde cada petición HTTP registrada |
