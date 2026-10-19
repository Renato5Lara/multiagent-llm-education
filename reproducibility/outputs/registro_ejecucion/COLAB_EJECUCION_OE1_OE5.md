# Ejecución real de los cinco notebooks por objetivo en Google Colab

Fecha: 2026-10-19. Cada notebook se abrió desde `https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/<nombre>.ipynb`, con «Ejecutar todas», aceptando el aviso estándar de Colab para cuadernos de GitHub, en un entorno nuevo cada vez, sin montar Drive ni usar credenciales. Commit clonado por los notebooks: `2fb5c0465f4fa8742b735d3cd273831429c4c88b`. Python 3.13.16; numpy 2.5.4, pandas 3.0.6, scipy 1.18.1, statsmodels 0.15.0, matplotlib 3.11.2 (versiones fijadas por el notebook).

**Naturaleza de la evidencia.** Es una **transcripción manual** de las salidas visibles en pantalla y de la línea de estado de Colab (no una exportación automática; no se guardó el `.ipynb` ejecutado). Es automática solo la ejecución misma; lo que figura aquí lo leyó y copió Claude desde la interfaz. Una ejecución local con nbclient (sin Colab) precede a esta, pero no se cuenta como Colab.

| Objetivo | Cifras | Por estado (salida de la celda G) | Hashes | Prueba negativa | Pruebas rápidas | Discrepancias |
|---|---|---|---|---|---|---|
| OE1 | 18 | VERIFICADO_DESDE_DATOS 16; NO_REPRODUCIBLE 2 | 1545/1545 | detectada (T6, `DISCREPANCIA`) | 10 passed | 0 |
| OE2 | 240 | VERIFICADO_DESDE_DATOS 240 | 1545/1545 | detectada (T8) | 10 passed | 0 |
| OE3 | 131 | VERIFICADO_DESDE_DATOS 131 (COINCIDE 128 + DIFERENCIA_EXPLICABLE 3) | 1545/1545 | detectada (T15) | 10 passed | 0 |
| OE4 | 491 | DESDE_DATOS 481; DESDE_DERIVADO 10 (COINCIDE 491) | 1545/1545 | detectada (T17) | 10 passed | 0 |
| OE5 | 86 | DESDE_DATOS 79; NO_REPRODUCIBLE 3; DESDE_DERIVADO 4 (COINCIDE 83) | 1545/1545 | detectada (T27) | 10 passed | 0 |

- Hashes: la salida `1545/1545 coinciden; difieren=0` se leyó en pantalla en OE1, OE2 y OE3. En OE4 y OE5 no se leyó esa salida; se deduce de que la celda C lanza error y detiene el notebook si algún hash no coincide, y las celdas siguientes (D–G) se ejecutaron.
- Suma por objetivo: 966 de las 1 011 comprobaciones del paquete; el resto no está en estos cinco notebooks. No se atribuye aquí.
- OE1 y OE5 no se reprodujeron enteros: quedan los `NO_REPRODUCIBLE` listados en `CONTEO_CIFRAS.md`.
- OE1: el final de las celdas H/I (línea `RESUMEN_COLAB`) no se leyó en pantalla; sí las celdas D–G. En OE2–OE5 la celda I contiene `files.download`, que descarga un ZIP en el navegador.
- El cuaderno índice `reproducibilidad_tesis.ipynb` **no** se volvió a ejecutar en Colab en este commit; su última ejecución en Colab fue en `439eb4c` (ver `COLAB_EJECUCION_REAL.md`).

## Segunda ronda en Colab: commit `2c2ae3e` (2026-10-19)
Tras añadir la réplica N3-R (OE3), los cinco notebooks se **reejecutaron** en Colab sobre `2c2ae3e402cac5dd2aa5a388fea30c954b678e7b` (transcripción manual de pantalla, igual que la primera ronda).
- **Un fallo real, detectado por la propia integridad del paquete:** la ejecución del OE3 en `36a3380` se detuvo en la celda C con `manifiesto: 1559/1560 coinciden; faltan=1`. El archivo ausente era `data/experiments/oe_n3r_2026-10-19/run/logs/run.log`, ignorado por `.gitignore` (`logs/`): existía en local pero no en el clon. Se eliminó (su contenido ya está en `run.log`), se regeneró el manifiesto (1 559 archivos) y se añadió la prueba `test_todo_archivo_del_manifiesto_esta_versionado_en_git`.
- OE3 en `2c2ae3e`: manifiesto 1559/1559; cadena N3-R coincide; efectos que replican 21 de 21; 131 cifras (128 + 3 con diferencia explicada); sin discrepancias.
- OE1: 16 desde datos y 2 no reproducibles; OE2: 240 coinciden; OE4: 491 (481 + 10); OE5: «Sin discrepancias». 0 discrepancias en los cinco.
- El índice transversal `reproducibilidad_tesis` **no** se volvió a ejecutar en Colab; su última ejecución sigue siendo `439eb4c`.

## Tercera ronda en Colab: commit `acaa19c` (2026-10-19)
Tras añadir N3-S y la eficiencia del OE3, y recalcular la Tabla 6 «usuarios» y la Tabla 27 por perfil, se ejecutaron en Colab **los cinco notebooks por objetivo y el notebook transversal** sobre `acaa19c23e18410a2a0360a03f0397b8f47f866a` (transcripción manual de pantalla). Todos terminaron sin error.
- OE1: 18 desde datos + 2 no reproducibles, 10 pruebas rápidas pasan, «Sin discrepancias». OE2: 240 coinciden. OE4: «Sin discrepancias» (491 en la ronda anterior; no leí el diccionario completo esta vez). OE5: 84 desde datos + 2 no reproducibles (+ derivados), «Sin discrepancias».
- OE3: ejecutó las celdas de N3-R, N3-S y eficiencia (6 de 6 contrastes con el mismo veredicto) y terminó con «Sin discrepancias»; las aserciones de cadena de N3-R y N3-S (`coincide`) pasaron, pues de otro modo la celda habría fallado.
- Notebook transversal: terminó sin error, tabla de trazabilidad con 5 elementos no reproducibles listados. Su texto introductorio estaba desactualizado («unas 870 cifras») y se corrigió **después** de esta ejecución (solo markdown; el código no cambió).
- **Incidencia de Colab:** al abrir el sexto notebook Colab respondió «Demasiadas sesiones» (cuatro sesiones inactivas de las rondas anteriores); se finalizaron esas sesiones desde «Gestionar sesiones» y se ejecutó con normalidad.

## Cuarta ronda en Colab: commit `d986b75` (2026-10-19)
Tras recalcular los estados de la Tabla 37, añadir los rangos del OE2 y la sensibilidad de N3-S, se ejecutaron en Colab los **cinco notebooks por objetivo y el notebook transversal** sobre `d986b75bc722759ad6c25a77be722133dbb3625c` (transcripción manual de capturas de pantalla). Todos terminaron sin error; en cada notebook por objetivo la celda G muestra «Sin discrepancias» y «10 passed».
- OE1: 34 desde datos + 2 desde derivado + 5 no reproducibles. OE2: 240. OE3: 131 (128 + 3 explicadas). OE4: 491 (481 + 10). OE5: 84 + 4 derivados + 2 no reproducibles. Notebook transversal: terminó y mostró la trazabilidad con los elementos no reproducibles listados.
- **Lección sobre el método de lectura:** una búsqueda automática de texto en la página devolvió «Sin discrepancias» para OE4 aun cuando esa ejecución había sido bloqueada por «Demasiadas sesiones» (el texto era el del código fuente de la celda). Por eso todas las lecturas de esta ronda se confirmaron con capturas de pantalla de la salida; las rondas anteriores que usaron esa búsqueda como única comprobación (OE2, OE5 y OE4 de la ronda `acaa19c`) quedan respaldadas por estas capturas de la ronda `d986b75`, pero no por sí mismas.

## Quinta ronda en Colab (2026-10-19): `793c58c` (OE1) y `14febc2` (notebook transversal)
- **OE1 en `793c58c`:** terminó sin error: 36 desde datos + 2 desde derivado + 4 no reproducibles; 10 pruebas pasan; «Sin discrepancias» (captura de pantalla). RNF04 (14,98 req/s) se recalcula ya con los `batches.json` de N1 publicados con el hash de los originales.
- **Notebook transversal en `14febc2`:** terminó sin error; la trazabilidad muestra la Tabla 37 como PARCIAL (23 comprobaciones). Una primera ejecución en `793c58c` mostró una fila obsoleta («Tablas 5 y 37: 0 cifras»), por lo que se corrigió `build_traceability.py` y se repitió.
- **OE2–OE5 NO se reejecutaron** tras `d986b75`. Justificación por diff (`git diff d986b75 14febc2`): solo cambian los `batches.json` de N1 y el manifiesto, la rama OE1 de `reproduce_results.py`, scripts nuevos de auditoría y el notebook índice; ningún dato, script o dependencia que esos cuatro notebooks ejecutan. Es una justificación, no una ejecución: no existe evidencia de Colab para ellos sobre el HEAD.

## Sexta ronda en Colab (2026-10-19): los seis notebooks sobre `c68a746`
Los **cinco notebooks por objetivo y el transversal** se ejecutaron sobre `c68a7469bc3ba3c6349e1e5423050612dbf3bde6` (HEAD publicado en ese momento; los commits posteriores solo cambian documentación). Todos terminaron sin error y el resultado se confirmó con capturas de pantalla de la salida (no con búsqueda de texto): OE1 36 desde datos + 2 derivados + 4 no reproducibles; OE2 240; OE3 131 (128 + 3 explicadas); OE4 491; OE5 84 + 4 + 2 no reproducibles; todos con «Sin discrepancias» y 10 pruebas rápidas aprobadas; el transversal terminó con su tabla de trazabilidad. El cambio de `8d2c681` a `c68a746` no afecta a lo que ejecutan los notebooks (solo scripts de auditoría); la ejecución se hizo igualmente para dejar evidencia sobre el HEAD. Se finalizaron las sesiones inactivas de Colab al aparecer «Demasiadas sesiones» (OE5).

## Corrección de trazabilidad (auditoría posterior, 2026-10-19)
- La frase de la sexta ronda «los commits posteriores solo cambian documentación» es imprecisa: tras `c68a746` cambian además un script auxiliar (`registro_afirmaciones_prioritarias.py`) y pruebas que los notebooks no seleccionan. Ningún archivo que ejecuten los notebooks cambió (árboles de Git idénticos; salidas de `outputs/` idénticas byte a byte en clones limpios de `c68a746` y `7fe0f3c`).
- Las seis ejecuciones son transcripciones manuales de pantalla: no se guardó el `.ipynb` ejecutado, su hash es NO_VERIFICABLE y la hora exacta no está documentada. Detalle y enlaces en `auditoria/AUDITORIA_TRAZABILIDAD_COLAB.md`.
