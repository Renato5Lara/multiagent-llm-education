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
