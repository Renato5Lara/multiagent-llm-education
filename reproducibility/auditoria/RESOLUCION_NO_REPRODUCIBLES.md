# Resolución de los ocho elementos no reproducibles

Cada elemento por separado. Distinciones: **no calculado** (la tesis no publica la cifra), **no disponible** (el dato o archivo no existe en el paquete), **no reproducible** (existe la cifra pero no puede recalcularse con lo publicado) y **no cumple** (el resultado existe y no alcanza la meta). Nada se reconstruye con estimaciones ni se simula.

| # | Elemento | Categoría | ¿Existen los datos? | ¿Se resuelve técnicamente? | Qué debe mantenerse en la tesis |
|---|---|---|---|---|---|
| 1 | Tabla 6, Kendall τb de «usuarios» frente al puntaje | **no calculado** (la tesis dice «no calculado») | Sí: el puntaje por condición y los usuarios están en `oe1_report.json` (derivado del propio arnés) y en los nombres de las 14 condiciones | **Sí, y se calculó de forma suplementaria:** τb = −0,506 (p = 0,043), coherente con el ρ = −0,608 ya publicado. **No se añadió a la tesis ni al verificador** porque la cifra no está publicada; sería una decisión del autor | «no calculado» es una afirmación verdadera; puede mantenerse o sustituirse por −0,51 (p = 0,043) con la salvedad de que el puntaje carece de definición aprobada |
| 2 | Tabla 27, puntuación SUS | **no disponible** | No: 0 evaluadores | No | Mantener «Sin datos: 0 evaluadores reales» |
| 3 | Tabla 35, instrumento SUS | **no disponible** (instrumento sin aplicar; los ítems sí figuran) | Ítems en `SUS_INSTRUMENT_ES.md`; sin respuestas | No | Mantener «instrumento sin aplicar» |
| 4 | Tabla 37, RF06 (persistencia de 20 ciclos) | **no reproducible** | La cifra consta en el informe del propio arnés; el registro de la sonda no está publicado | Solo si se localiza y publica ese registro (puede estar en `backend/experiments/oe_n1_*` local) | La conclusión «RF06 cumplido» se apoya en el informe del arnés; indicarlo |
| 5 | Tabla 37, REL-D (20 pares con la misma semilla) | **no reproducible** | Consta en `oe1_report.json` («20 de 20 idénticos»); no están los 20 pares | Parcial: N3-S demuestra el determinismo a mayor escala (240 corridas con las mismas semillas, calidad idéntica); no sustituye la sonda de N1 | Mantener el cumplimiento, citando la sonda del arnés y la comprobación de N3-S como evidencia complementaria |
| 6 | Tabla 37, RNF04 (mediana del throughput por lote en proceso de N1: 14,98 req/s) | **no reproducible** | No: falta el `batches.json` de N1 | Solo si se localiza ese archivo local y se publica con su hash | «No cumplido en proceso» es coherente con el conjunto (la carga HTTP sí se recalcula: 18 de 419 corridas ≥ 20 req/s), pero la cifra 14,98 no se verifica |
| 7 | Tabla 37, RNF05 (SUS) | **no disponible** | No | No | Mantener «No medido» |
| 8 | Tablas 32 y 44 (síntesis bibliográfica) | **no reproducible** con datos del estudio | Texto de la tesis; las fuentes son externas | Parcialmente, con acceso a cada fuente original (Crossref/OpenAlex/editor) | Mantener como contextual; no es resultado del estudio |

**Resueltos técnicamente en esta fase** (ya no figuran como no reproducibles): la fila «usuarios» de la Tabla 6, las estadísticas por perfil de la Tabla 27 y los valores y estados de RF01–RF05, REL-C, RNF01, RNF02 y RNF03 de la Tabla 37.

**Quedan bloqueados por archivos que no están en el paquete:** RF06, REL-D, RNF04 (acción: localizar y publicar `batches.json` y las sondas de N1). **Por datos humanos inexistentes:** SUS (Tablas 27, 35, RNF05). **Por fuentes externas:** Tablas 32/44.
