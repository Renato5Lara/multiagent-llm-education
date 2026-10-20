# Auditoría de trazabilidad de las ejecuciones en Colab

Fecha: 2026-10-19. Commit de referencia de la última ejecución documentada: `c68a7469bc3ba3c6349e1e5423050612dbf3bde6` (sexta ronda). HEAD examinado: `7fe0f3c`. Generador: [`scripts/trazabilidad_colab.py`](../scripts/trazabilidad_colab.py).

## 1. Diagnóstico

| Pregunta | Respuesta |
|---|---|
| ¿`ESTADO_NOTEBOOKS_COLAB.csv` estaba desfasado? | **Sí, y era un error mío.** Seguía mostrando los commits de rondas anteriores (`793c58c`, `d986b75`, `14febc2`) y la frase «sin evidencia de ejecución en Colab sobre el HEAD», aunque la sexta ronda (`c68a746`) constaba en `COLAB_EJECUCION_OE1_OE5.md`. El intento de actualizarlo en la fase 13 no se guardó y lo di por hecho en un resumen. Las cifras del CSV (42, 240, 131, 491, 90) sí coincidían con la sexta ronda. |
| ¿Cambiaron después de `c68a746` el código, los datos o las dependencias que ejecutan los notebooks? | **No.** Los árboles de Git de `data/`, `notebooks/`, `outputs/tables/`, `EVIDENCE_MANIFEST.csv`, `RESULTS_TRACEABILITY.csv`, `backend/adaptation_swarm`, `backend/official_runs`, `backend/loadtest` y `datasets/` son idénticos en `c68a746` y `7fe0f3c` (mismo hash de árbol). Los seis notebooks tienen el mismo SHA-256 en ambos commits. |
| ¿Algún script que ejecutan los notebooks lee `auditoria/`? | **No** (búsqueda en los ocho scripts invocados: `verify_hashes`, `validate_data`, `reproduce_results`, `repro_lib`, `oe3_robustez`, `oe3_replicacion`, `oe3_sesion`, `oe3_eficiencia`). `oe3_sesion.py` solo cita `auditoria/PRE_REGISTRO_N3S.md` en texto. |
| ¿Es suficiente la comparación de nombres de archivo? | No se usó solo eso. Se ejecutaron **los mismos comandos que los notebooks** en dos clones limpios (`c68a746` y `7fe0f3c`, con `sparse-checkout` como el notebook): los 13 comandos terminan con código 0 en ambos, **43 archivos de `outputs/` idénticos byte a byte** (ninguno solo en un lado) y `pytest -k` (filtro de los notebooks) da `10 passed, 40 deselected` en ambos. |
| ¿Se conserva el notebook ejecutado en Colab? | **No.** Los `.ipynb` publicados no llevan salidas y no se guardó el ejecutado: su hash es **NO_VERIFICABLE**. Lo que existe es una transcripción manual de las pantallas; las capturas no están en el repositorio. |
| ¿Se puede comprobar el commit que clonó Colab? | **No de forma independiente.** Los notebooks clonan la **rama** (`REF = "repro/auditoria-integral-2026-10-19"`) y la salida muestra el commit, pero no hay captura conservada ni exportación. La sexta ronda cae entre el commit `c68a746` (14:06) y el siguiente (`5ddc6ab`, 14:27, hora local UTC−5): es una ventana inferida, no la hora de ejecución. |

**Otros defectos hallados y corregidos o registrados**
- Mis parches de las fases 13 y 14 cambiaron los finales de línea (CRLF → LF) de `tests/test_reproducibility.py` y `INFORME_CIERRE_FINAL.md`, lo que inflaba el diff (1 012 y 248 líneas). Se restauró CRLF; el diff real de las pruebas es de 3 líneas.
- `COLAB_EJECUCION_OE1_OE5.md` decía que los commits posteriores a `c68a746` «solo cambian documentación»: es **impreciso**. Cambian además un script auxiliar (`registro_afirmaciones_prioritarias.py`) y pruebas no seleccionadas por los notebooks; ninguno afecta a lo que ejecutan.
- Residuo: `verificacion_oe3_20261019_071001/` y su `.zip` (6 archivos) se subieron por error en `36a3380` (exportación de la celda final de una ejecución local previa a N3-S). Ningún notebook ni script los usa, pero **no deben leerse como evidencia vigente**. No se han borrado (quedan para decisión del autor).

## 2. Los seis notebooks

Detalle por ronda (33 filas, con hash del notebook en cada commit ejecutado frente al actual): [`TRAZABILIDAD_COLAB_POR_RONDA.csv`](TRAZABILIDAD_COLAB_POR_RONDA.csv). Estado actual: [`ESTADO_NOTEBOOKS_COLAB.csv`](ESTADO_NOTEBOOKS_COLAB.csv) (el valor anterior de `commit_ejecutado` se conserva en `commit_ejecutado_anterior_registrado`).

| Objetivo | Última ejecución documentada | SHA-256 del notebook (commit ejecutado = actual) | Resultado transcrito | Certeza |
|---|---|---|---|---|
| OE1 | `c68a746` | `29045697…` | 36 desde datos + 2 derivados + 4 no reproducibles | PARCIAL |
| OE2 | `c68a746` | `ad1a4244…` | 240 coinciden | PARCIAL |
| OE3 | `c68a746` | `ed044588…` | 131 (128 + 3 explicadas) | PARCIAL |
| OE4 | `c68a746` | `61bd2607…` | 491 (481 + 10) | PARCIAL |
| OE5 | `c68a746` | `6a6b7cf8…` | 84 + 4 + 2 no reproducibles | PARCIAL |
| Transversal | `c68a746` | `cdbcf6ef…` | terminó; tabla de trazabilidad | PARCIAL |

En todos: 0 discrepancias y «10 passed» según la transcripción. Niveles usados: *comprobada* (exportación o hash conservados: **ninguna**), *parcial* (transcripción manual de pantalla: **las seis**), *no verificable* (hash y hora de ejecución).

## 3. Cambios posteriores a `c68a746`

[`MATRIZ_CAMBIOS_POSTERIORES.csv`](MATRIZ_CAMBIOS_POSTERIORES.csv): cada archivo con su categoría y si lo consume algún notebook. **0 archivos consumidos por los notebooks**; los demás son documentación y registros de auditoría, un script auxiliar no invocado y pruebas no seleccionadas por el filtro `-k`. Ningún objetivo (OE1–OE5 ni el transversal) queda afectado y **no hace falta repetir Colab**; si se tocara cualquier archivo de la lista «consumido», la matriz marca `requiere_reejecucion = SI`.

## 4. Enlaces de Colab

Los notebooks apuntan a la **rama**, no a un commit: abrirlos hoy carga la rama actual y clona su punta actual.

| Objetivo | Enlace vigente (rama) |
|---|---|
| OE1 | https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_1_requisitos_y_desempeno.ipynb |
| OE2 | https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_2_enjambre_vs_convencional.ipynb |
| OE3 | https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_3_configuracion_interna.ipynb |
| OE4 | https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_4_carga_y_tamano_del_enjambre.ipynb |
| OE5 | https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_5_precision_y_usabilidad.ipynb |
| Transversal | https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/reproducibilidad_tesis.ipynb |

**Enlace histórico.** Se comprobó en el navegador con OE1: la URL `…/blob/c68a7469bc3ba3c6349e1e5423050612dbf3bde6/reproducibility/notebooks/objetivo_1_requisitos_y_desempeno.ipynb` **abre** el notebook de ese commit, pero su celda `REF` sigue siendo la rama, de modo que **al ejecutarlo clona la punta actual de la rama y no `c68a746`**. Por tanto **no existe hoy un enlace de Colab que garantice ejecutar el código histórico**. No se comprobaron las URL equivalentes de los otros cinco notebooks.

**Alternativas reproducibles (sin tocar los notebooks):**
1. *Local, verificada para los scripts:* `git clone https://github.com/Renato5Lara/multiagent-llm-education.git && cd multiagent-llm-education && git checkout c68a7469bc3ba3c6349e1e5423050612dbf3bde6`, y ejecutar desde `reproducibility/scripts` los comandos de las celdas (los usados en esta auditoría: `verify_hashes.py`, `validate_data.py`, `reproduce_results.py [--oe oeN]`, `oe3_*.py`). Los notebooks aceptan `REPRO_LOCAL_ROOT` para usar un clon local.
2. *En Colab, pendiente de decisión:* crear una **etiqueta** en `c68a746` y cambiar `REF` a esa etiqueta (`git clone --branch` acepta ramas y etiquetas, no SHA). Es un cambio del notebook (alteraría su SHA-256) y una referencia nueva en el repositorio público; no se ha hecho.

## 5. Limitaciones abiertas
- Las seis ejecuciones de Colab son transcripciones manuales: no hay `.ipynb` ejecutado, hash del ejecutado, hora exacta ni captura conservada.
- La correspondencia ejecución ↔ código/datos se apoya en (a) el registro del auditor y (b) la identidad demostrada de entradas y salidas entre `c68a746` y `7fe0f3c`; la segunda es sólida, la primera es parcial.
- Las rondas 1–5 se conservan como historial; no equivalen a evidencia sobre el HEAD.

## 6. Conclusión
Con lo disponible **se puede vincular cada resultado con el código y los datos de `c68a746` con certeza alta** (árboles de Git idénticos, salidas byte a byte iguales, pruebas iguales) **y la ejecución en Colab de ese commit con certeza parcial** (transcripción, no verificable de forma independiente). El CSV estaba desactualizado por un fallo de registro, no porque los notebooks o sus datos hubieran cambiado.

## 7. Adenda de la fase 15
- **Salidas versionadas desfasadas.** Las comparaciones de la sección 1 usan salidas regeneradas en clones limpios, por lo que siguen siendo válidas. Pero los archivos de `outputs/` **versionados** para OE1 (desde `d986b75`) y OE5 (desde `2fb5c04`) no coincidían con lo que genera el código vigente; se regeneraron y se commitearon. No son entradas de los notebooks.
- **Archivos residuales.** `verificacion_oe3_20261019_071001/` y su ZIP llevan ahora un `LEEME_RESIDUAL.md`: exportación local previa a N3-S, no leída por ningún notebook ni script, no vigente. No se han borrado ni se ha tocado el historial.
- **Enlaces.** No se ha creado ninguna etiqueta ni se ha cambiado ninguna referencia pública; la alternativa local sigue siendo la verificada.
