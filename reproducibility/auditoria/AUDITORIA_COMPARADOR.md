# Auditoría del comparador de resultados

Hay **dos** comparaciones distintas y sus tolerancias no deben confundirse:

## 1. Cifras del informe frente a lo recalculado (`repro_lib.compare`) — la que decide si una cifra «coincide»
- **Regla:** tolerancia = **media unidad del último decimal publicado** (la precisión de la propia cifra), sobre el valor *sin redondear*. `COINCIDE` ≤ ½ unidad; ≤ 1 unidad solo si se **demuestra doble redondeo** (valor sin redondear → intermedio con más decimales → precisión del cuadro, mitad hacia arriba): `DIFERENCIA_EXPLICABLE`; si no se demuestra, `DIFERENCIA_SIN_EXPLICAR` (cuenta como discrepancia); más de 1 unidad, `DISCREPANCIA`.
- **No es una tolerancia universal:** depende de la cifra. Ejemplos: P95 con 1 decimal → 0,05 ms; throughput con 1 decimal → 0,05 req/s; un recuento entero → 0,5 (es decir, igualdad exacta); un p con notación `a × 10ⁿ` → media unidad de la mantisa (≈ 1 % relativo para 2 cifras significativas); η² con 2 decimales → 0,005.
- **Por qué es la correcta:** una cifra publicada con *d* decimales solo contiene información hasta *d* decimales; exigir más sería falso y aceptar menos ocultaría errores de transcripción. La tolerancia **nunca se amplía** para conseguir coincidencias (se midió: las 1 002 coincidencias están dentro de ½ unidad; las 3 de 1 unidad se explican con evidencia).
- **Qué detecta (probado en `tests/`):** una cifra publicada alterada (`test_control_negativo_un_valor_publicado_alterado_es_discrepancia` y, por objetivo, `test_control_negativo_por_objetivo[oe1…oe5]`: el verificador del objetivo devuelve el código 5), un registro por petición alterado (la cadena petición→corrida deja de coincidir), un archivo alterado o ausente (código 2), esquemas rotos y duplicados (códigos 3 y 4).
- **Qué no oculta:** filas o celdas del informe que el verificador no cubre **no desaparecen**: aparecen en `CONCILIACION_TESIS_DATOS.csv` como `PENDIENTE_DE_EVIDENCIA`, `NO_APLICA` o `VERIFICACION_PARCIAL`. Cada cifra se localiza por **fila, columna y encabezado** exactos del DOCX (no por búsqueda de texto), de modo que valores intercambiados entre celdas no coinciden.
- **Límite:** el comparador no juzga la *validez estadística* del indicador ni que la unidad sea la correcta (p. ej. ms frente a s); esa responsabilidad es del script que calcula el valor, cuya fórmula consta en la conciliación.

## 2. Archivos regenerados frente a archivos publicados (`repro_lib.comparar_archivos`) — control secundario
Sirve para comprobar que los scripts del proyecto, ejecutados sin modificar, reproducen sus propias salidas publicadas. **El estado de una cifra del informe nunca depende de esta comparación.** Niveles:
1. `COINCIDE_BYTE_A_BYTE`.
2. `COINCIDE_SALVO_FINALES_DE_LINEA`: iguales tras normalizar CRLF/LF. Origen: los publicados se generaron en Windows; Linux/Colab escribe LF. **Hallazgo de la ejecución real en Colab** (17 archivos).
3. `COINCIDE_NUMERICO`: mismo contenido y tipos, con números iguales dentro de **tolerancia relativa 1e-6** y **absoluta 1e-12**, y, en JSON, barras `\` y `/` de rutas equivalentes. Origen: ruido de punto flotante entre plataformas (valores teóricamente cero como `sum_sq` ≈ 1e-30 en `oe3_anova.csv`) y una ruta con barras de Windows en `oe2_reanalysis.json` (20 archivos en Colab).
4. `DIFIERE`: cualquier otra cosa.

**Salvaguardas contra ocultar diferencias reales.**
- La tolerancia **absoluta** 1e-12 **no se aplica a probabilidades** (columnas/claves `p`, `p_holm`, `PR(>F)`, `*_p`…): `1e-184` y `3e-184` son distintos (relativo 2) y se detectan; solo el ruido cerca de cero de magnitudes no probabilísticas se tolera. Prueba: `test_comparador_no_oculta_diferencias_en_probabilidades`.
- Los números de las tablas que valen para las conclusiones (P95, throughput, razones, IC, p, η², F1…) se comparan además a su precisión publicada (apartado 1), mucho más exigente que el ruido de 1e-6 relativo de los derivados.
- Se detecta un cambio de columnas, de forma (filas × columnas) y de texto.
- Sin tolerancia: orden de filas (las salidas del proyecto son deterministas y conservan el orden) y valores no numéricos.

**Riesgo residual.** Una diferencia real entre 1e-12 y 1e-6 relativo en un derivado no probabilístico pasaría como `COINCIDE_NUMERICO`. No afecta a las cifras del informe (que se recalculan y comparan aparte) y el resultado real en Colab fue 0 archivos `DIFIERE` y 0 discrepancias.
