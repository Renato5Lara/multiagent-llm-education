# Informe de cierre de cobertura (fase final)

Rama `repro/auditoria-integral-2026-10-19`. Todo lo que sigue se recalculó desde los archivos actuales (`CONCILIACION_TESIS_DATOS.csv`, `outputs/verification_report.json`), no se copió del informe anterior. El triaje lo hace `scripts/cierre_cobertura.py` (ejecutar después de `build_conciliacion.py`); es **heurístico**, trabaja con el fragmento de ±35 caracteres ya publicado y **no verifica oraciones completas**.

## 1. Conteos recalculados
| Concepto | Valor | Cómo se obtiene |
|---|---|---|
| Comprobaciones numéricas de tablas | 1 011 | `verification_report.json`: 991 desde datos + 14 desde derivado + 6 no reproducibles; 0 discrepancias |
| …dentro de los cinco notebooks | 966 | OE1 18 + OE2 240 + OE3 131 + OE4 491 + OE5 86 |
| …fuera de ellos | 45 | **Tabla 36 (33) + Tabla 45 (11) + Tablas 32 y 44 (1)**; 966 + 45 = 1 011 |
| Afirmaciones en prosa (fila por valor) | 1 863 | 347 `NO_APLICA`, 34 coinciden (23 exactas, 11 con redondeo), el resto abiertas |
| Prosa `PENDIENTE_DE_EVIDENCIA` | 812 → **595** | 217 pasaron a parcial (ver §3) |
| Prosa `VERIFICACION_PARCIAL` | 670 → **887** | 670 + 217 |
| Celdas de tabla sin comprobación | 1 057 | 982 `NO_APLICA` (etiquetas, parámetros, bibliografía, hashes citados), 65 parciales (Tablas 5/37), 6 pendientes, 4 no reproducibles |

Los 812 y 670 del informe anterior **se reprodujeron exactamente** antes de aplicar este triaje.

## 2. Las 45 comprobaciones fuera de los notebooks
Son **transversales** y se dejan así: la Tabla 36 (trazabilidad de evidencias del Anexo 2) y la 45 verifican que el prefijo SHA-256 citado coincide con el archivo publicado; cada fila cita evidencias de varios objetivos, y asignarlas a uno duplicaría observaciones para aparentar cobertura. Se añadieron al mapa como `transversal` (`MAPA_OBJETIVOS_EVIDENCIAS.csv`). Las verifica el notebook índice `reproducibilidad_tesis` (no reejecutado en Colab en este commit).

## 3. Triaje de las prosa abiertas (1 482 = 595 + 887)
Categoría asignada a cada una en `categoria_cierre`, con `fuente_requerida` y `accion_cierre` (`CIERRE_COBERTURA.csv` lista solo las abiertas):
| Categoría | Prosa abiertas | Qué falta |
|---|---|---|
| `RESULTADO_CUANTITATIVO` | 447 | revisar la oración completa contra el valor recalculado (condiciones, comparación, interpretación): **trabajo manual** |
| `PARAMETRO_DE_DISENO` | 381 | contrastar con `provenance.json`, `runs.csv`, `environment.json` o el código |
| `EXTRACTO_DE_REGISTRO` | 226 | localizar la línea en los logs/journals publicados (Anexos) |
| `OTRO_REVISAR` | 428 | sin patrón reconocible: revisión manual |

**Reclasificación a parcial (217).** Pasa de pendiente a `VERIFICACION_PARCIAL` solo si el valor es un parámetro de diseño que existe en un registro del paquete: 20 vCPU, 31,75 GiB y Python 3.12.10 (`environment.json`), 6 561 configuraciones (`K_LEVELS ** N_DIMS` en el código), 48 condiciones (`runs_oe3.csv`), y los niveles de usuarios, N, calentamiento y timeout presentes en `runs.csv`. **Es la forma más débil de verificación**: dice que el valor existe en la especificación, no que la frase sea cierta. Ninguna prosa pasó a `COINCIDE`. Las 8 vCPU / 32 GB objetivo figuran en la tesis como condición **no ejecutada** y no se verifican.

**Bibliografía.** No se comprobó ninguna referencia externa (no hay acceso a las fuentes originales desde el paquete): las cifras de la literatura permanecen `NO_APLICA` o pendientes. No se inventan páginas ni citas.

## 4. Celdas pendientes (6) y no reproducibles (10 elementos)
- 6 pendientes: criterios de las Tablas 15 y 30 (umbrales como «≥ 98 %», «α = 0,05»). Son criterios de hipótesis, no resultados; se pueden contrastar con `OBJETIVOS_LITERALES.json` (acción pendiente, no hecha).
- 65 parciales (Tablas 5/37): estados MET/NOT_MET copiados de `oe1_report.json`; recomputarlos exige una regla aprobada del puntaje (acción: decisión del autor/asesor).
- No reproducibles: Tabla 6 «usuarios» (cálculo no localizado), Tabla 27 por perfil (no recalculado), SUS sin evaluadores, Tablas 32/44 (bibliografía), Tabla 35 (instrumento sin aplicar).

## 5. Objetivos y notebooks (auditoría de cada uno)
Los cinco objetivos se mantienen: coinciden con D2.9.7 y V7.1, y el notebook de cada uno muestra el texto literal en la celda A (prueba `test_objetivos_literales_son_los_cinco_vigentes`). Cada notebook declara sus campañas, que sí aportan los datos que usa, calcula desde `runs.csv`/registros, exhibe sus limitaciones y no afirma confirmación de hipótesis.
- **OE1:** 8 cifras en prosa recalculadas desde N1; estados MET/NOT_MET no recalculados; RNF01 solo en proceso.
- **OE5, lo que se sostiene con los datos:** F1_adapt v3 provisional ≈ 0,816 con IC95 superior < 0,85 y v2 histórico ≈ 0,641: **la meta F1 ≥ 0,85 no se alcanza**. Lo que **no** se sostiene: cualquier afirmación sobre SUS > 75 o validación por expertos (0 evaluadores; no se simulan). La especificación v3 es provisional y los resultados son exploratorios, no confirmatorios.
- OE1–OE3 no tienen hipótesis estadística formulada en la tesis; los notebooks no la inventan.

## 6. Commits ejecutados frente a publicados
Colab ejecutó los cinco notebooks sobre `2fb5c046`. Entre `2fb5c04` y `2d06690` cambian **solo** `auditoria/ESTADO_NOTEBOOKS_COLAB.csv`, `auditoria/INFORME_AUDITORIA_FINAL.md` y `outputs/registro_ejecucion/COLAB_EJECUCION_OE1_OE5.md` (`git diff --stat`); ni notebooks, ni scripts, ni datos, ni dependencias, ni manifiesto. Las salidas de Colab siguen siendo válidas para ese contenido **ejecutable**, pero **el commit final publicado no fue ejecutado en Colab** y no se afirma lo contrario. No hizo falta reejecutar. El índice transversal sigue correspondiendo a `439eb4c` en su última ejecución en Colab.

## 7. Publicación y privacidad (sin cambios en lo publicado)
Revisión de los archivos publicados: sin correos, rutas locales ni claves/tokens (búsqueda por patrones). Riesgos a decidir por el autor, **no modificados**:
1. `data/metadata/informe_D2.9.7_tablas.json` (141 KB) transcribe el texto de las 45 tablas de la tesis (propia, no publicada en otra parte). Medida: mantener si se acepta exponer los cuadros de resultados antes de la defensa; si no, retirarlo y dejar solo el hash y las cifras comparadas (los notebooks lo usan, habría que regenerarlo desde el DOCX).
2. Tablas 32/44 (síntesis bibliográfica) y Tabla 35 (ítems del SUS) contienen cifras y texto de terceros: citar la fuente y comprobar la licencia del cuestionario.
3. `data/metadata/SANITIZACION.csv` documenta los 14 archivos sanitizados con el hash de ambas versiones.
4. Sigue sin licencia declarada: el repositorio es legible pero no reutilizable explícitamente.

## 8. Qué se necesita para cerrar lo pendiente
- Revisión manual asistida de ~447 resultados cuantitativos y 428 «otros» (no se resuelve con una regla automática).
- Una regla aprobada del puntaje de cumplimiento para recomputar los estados de las Tablas 5/37.
- Localizar el cálculo de «usuarios» de la Tabla 6 y las estadísticas por perfil de la 27.
- Acceso a las fuentes originales para las Tablas 32/44 y las referencias.
- Datos reales de SUS y de expertos (no existen).
- Aplicar las 5 correcciones de la Tabla 13 a la copia del DOCX y revisarla visualmente en Word (no se renderizó).

**No se declara la tesis verificada por completo.**
