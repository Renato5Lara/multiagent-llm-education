# Paquetes de OE2-B, versión 3 (segunda anonimización)

Sustituyen, **para los notebooks de la etiqueta `repro-etapa26-v3`**, a `oe2b_colab_paquete.zip` y `oe2b_http_p1.zip` de `../../etapa23_oe1_oe5/paquetes/`, que se conservan sin modificar como versión histórica.

Diferencia: en el campo `error` de cinco líneas de `intentos.jsonl` (los cinco intentos con salida 1 de Locust) se sustituyeron rutas locales truncadas por `<RUTA_LOCAL_ANONIMIZADA>`. No cambia ningún otro campo: se comprobó línea a línea (180 líneas, 5 modificadas) y los análisis dan resultados idénticos byte a byte. Detalle: `../docs/anonimizacion_oe2b_v3/MATRIZ_CAMBIOS_ANONIMIZACION_OE2B_V3.xlsx`.

Los demás diez paquetes no cambian y se siguen descargando del commit `3c8953a58909c48929093ef1524eb7d0ad317378`.

Importante: las versiones anteriores de estos dos paquetes siguen en el historial público del repositorio (commit `3c8953a` y etiquetas anteriores); esta versión no las elimina.
