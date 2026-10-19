# Informe de cierre documental (privacidad, correcciones del DOCX y verificación manual)

Rama `repro/auditoria-integral-2026-10-19`, partiendo de `265a4f4`. **Actualización posterior:** el autor decidió mantener el repositorio público y conservar `informe_D2.9.7_tablas.json` (necesario para la automatización); por eso el §1 queda como registro del riesgo y de la decisión, y estos cambios se publican en la rama de auditoría junto con los de la fase siguiente.

## 1. Privacidad: hallazgo que requiere decisión antes de seguir publicando
El repositorio es **público** (comprobado: respuesta HTTP 200 sin sesión). `data/metadata/informe_D2.9.7_tablas.json` transcribe las **46 tablas** del DOCX, entre ellas la tabla 0 de la dedicatoria (nombre completo del autor; DNI y ORCID vacíos), los resultados de todas las campañas, la síntesis bibliográfica de las Tablas 32/44 (cifras de estudios de terceros) y los ítems del SUS. Está en dos ramas remotas y en su historial. Mi informe anterior lo trató como riesgo bajo («el autor puede retirarlo»): lo corrijo, el contenido es más amplio de lo que dije.

Matriz completa (archivo, contenido, riesgo, dependientes, consecuencias de retirarlo y medida recomendada): [`MATRIZ_PRIVACIDAD.csv`](MATRIZ_PRIVACIDAD.csv). Puntos clave:
- Retirar el JSON del árbol **no lo borra del historial**; purgarlo exige reescribir historia (no autorizado). Lo más inmediato y reversible es **pasar el repositorio a privado** hasta la defensa y después decidir.
- El JSON lo usan los seis notebooks y `reproduce_results.py`; sustituirlo por una versión reducida exige regenerar el manifiesto y volver a ejecutar en Colab.
- `.codex_work/` (acta y charter con el nombre del autor) ya estaba en 6 ramas remotas antes de esta auditoría; no está en `origin/main`.
- No encontré correos, rutas locales ni claves (búsqueda por patrones).

**No se publicará nada más hasta que el autor decida.** No retiré ni alteré archivos.

## 2. Correcciones de la Tabla 13 en la copia del DOCX
| | sha256 |
|---|---|
| Original D2.9.7 (intacto) | `a6bb2934de7fd5123ca18229cfc02acf17a555aaa87f509706fd98ab3c396edf` |
| Copia corregida `…2026-10-19 - D2.9.7-CORREGIDO-REDONDEO-TABLA13.docx` (misma carpeta, no publicada) | `1bd0894c9586e4330b2f5d61851cf33eb8c6a5242187906f4564752ac4ae13c3` |

La copia ya existía; en esta fase la **volví a comprobar** (no la rehice):
1. Comparación ZIP: solo difiere `word/document.xml`; el resto de las entradas es idéntico.
2. Comparación de los 3 879 párrafos: cambian exactamente 5, y el cambio en cada uno es solo la cifra: η² 0,50→0,49 (Tabla 13), `k_stop` 1,51→1,50 (Tabla 13 y §6.5.4), T_conv de PSO 76,5→76,4 (Tabla 13 y la tabla de estructura del análisis del OE3 en §6.5.5).
3. Apariciones restantes: «76,5» no queda en ningún párrafo; los «1,51» restantes son la razón de throughput 1,13–1,51 y un límite de IC, **otro indicador**, y no se tocaron; «0,50» solo aparece en «0,505».
4. **Renderizado con Word** (apertura en solo lectura, exportación a PDF; 267 páginas; el original no se modificó): inspeccioné visualmente las páginas **105** (Tabla 13: se ve 0,49 · 1,50 / 1,91 · 76,4 / 76,3 / 63,3 con el formato intacto) y **111** (tabla con «mecanismo PSO 76,4»). La página 109 (frase de §6.5.4) la verifiqué solo por texto extraído del PDF, no visualmente. No revisé el resto del documento (paginación, campos, índices): afirmo solo lo que vi.
5. Con las tablas de la copia, el verificador da 1 005 coincidencias, 0 diferencias explicables y 6 no reproducibles (informe anterior); no lo repetí en esta fase.

**Hallazgo adicional (error mío, corregido).** `AUDITORIA_REDONDEO_TABLA13.md` decía «1 000 permutaciones»; el código usa `n_perm = 999` (p = (exceso + 1)/1 000) y la tesis dice 999. Corregido en el documento. No afecta a ninguna cifra.

**Correcciones propuestas que requieren decisión del autor** (no aplicadas):
- La tesis afirma que «El OE3 queda demostrado experimentalmente bajo las condiciones ejecutadas» (§7.1) aunque el OE3 no tiene hipótesis estadística formulada y la campaña es no oficial: la redacción es más fuerte que la evidencia; el asesor podría pedir «se observa» o «se evidencia en».
- La conclusión «OE1 … se cumple de forma parcial» y la descripción de RNF01/RNF04 son coherentes con los datos (ver §3).

## 3. Verificación manual de afirmaciones (prioridad científica: resumen, §6.5.4, §7.1, §8)
Script `scripts/verificacion_manual_conclusiones.py`; resultado por afirmación en [`VERIFICACION_MANUAL.csv`](VERIFICACION_MANUAL.csv) (ubicación, texto mínimo, fuente primaria, cálculo, valor recalculado, tolerancia, resultado, limitaciones). Recalculadas desde `runs.csv` y `runs_oe3.csv`:

| id | Afirmación | Recalculado | Resultado |
|---|---|---|---|
| M1 | 419 corridas HTTP válidas, sin errores ni timeouts | 419; 0 errores; 0 timeouts (N4 60 + N8 120 + N8b 60 + N11 179) | coincide |
| M2 | 20 req/s solo en 18 corridas, todas de N = 10 | 18, todas N11, N = 10, tramo B | coincide |
| M3 | P95 < 2 s hasta 10 usuarios en todas las corridas | 210 corridas, máx 1 954,4 ms | coincide |
| M4 | 25 usuarios: solo N = 10 en tramo B (8 de 9) | 8 de 9; en las otras 61 corridas con 25 usuarios, 0 | coincide |
| M5 | despacho concurrente reduce T_conv ≈ 37 % | 37,4 % (el secuencial +59,7 %) | coincide |
| M6 | difusión de g_best: ≈ 13 ms y 11 mensajes | 12,94 ms; 10,83 mensajes | coincide |
| M7 | sin difusión, ≈ 21 % más rápido (referencia) | 20,9 % | coincide |
| M8 | 16 % en promedio marginal | 15,8 % | coincide |
| M9 | 100 perfiles sintéticos | `n_profiles` = 100 | coincide |
| M10 | campañas del 5 al 15 de octubre de 2026 | `started_utc` de las campañas HTTP: 6 a 15 oct (UTC) | **parcial**: el 5 de octubre no está respaldado en esos registros |

Efecto en la conciliación: 30 filas de prosa con valor coincidente pasaron a `COINCIDE_*`; en ninguna se afirma la oración completa (cada fila lleva en `verificacion_manual_nota` lo que falta: «sin mejorar la calidad», «régimen del equipo», «sintéticos», etc.). Recuento actual de prosa: 576 pendientes, 876 parciales, 64 coinciden (36 exactas + 28 con redondeo), 347 no aplica.

**No verificado todavía** (sigue pendiente): el resto de las 576 + 876 afirmaciones, en especial: otras estadísticas y valores p de la prosa de §6.5.3–6.5.6, tamaños de efecto, porcentajes de brecha («80 % peor»), el «≈ ×1,62 en throughput» entre tramos, el «n = 14» de la Tabla 6, los antecedentes bibliográficos y los parámetros que solo se comprobaron como «el nivel existe en `runs.csv`».

## 4. Los cinco objetivos
OE1–OE5 se mantienen (texto literal en `OBJETIVOS_LITERALES.json`, un notebook por objetivo más el índice). OE5 no se presenta como validado: F1_adapt v3 provisional 0,8156 (IC95 % 0,8111–0,8201) y v2 0,6407 quedan por debajo de 0,85, no hay SUS ni panel de expertos y no se generó ningún dato sintético. La tesis lo dice igual (§7.1: «RNF03 no alcanza 0,85… RNF05 no se midió»).

## 5. Limitaciones que deben comunicarse al asesor
Las del README (§4), más: el triaje automático de la fase anterior es heurístico; la verificación de los parámetros de diseño es débil; la copia del DOCX solo se revisó visualmente en 2 de las páginas afectadas; el repositorio público contiene el texto de las tablas de la tesis y el nombre del autor (§1); los registros por petición son del propio arnés (no hay prueba externa de que las campañas se ejecutaran como se declara).

## 6. Estado
Documentalmente **no cerrado**: falta la decisión de privacidad, la revisión visual completa del DOCX en Word y la verificación de las afirmaciones restantes.
