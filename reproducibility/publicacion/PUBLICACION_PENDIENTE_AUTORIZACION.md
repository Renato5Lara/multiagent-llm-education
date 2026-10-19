# Publicación pendiente de autorización

**Estado: NADA está publicado.** No se ha hecho `git push`, no se cambió la visibilidad del repositorio y no se subió nada a ningún servicio externo. Este documento enumera lo que se pretende publicar y lo que debe resolverse antes.

El repositorio remoto `Renato5Lara/multiagent-llm-education` es **público** y **no declara licencia** (comprobado con la API anónima de GitHub). Cualquier `push` de esta rama lo haría visible a cualquiera.

## 1. Qué se pretende publicar
Clasificación completa, archivo por archivo: [`CLASIFICACION_ARCHIVOS.csv`](CLASIFICACION_ARCHIVOS.csv) (resumen en `CLASIFICACION_RESUMEN.json`).

| Cat. | Contenido | Archivos | Tamaño |
|---|---|---|---|
| A | Código y pruebas de reproducibilidad (`scripts/`, `tests/`, `environment/`, scripts de análisis del proyecto bajo `data/experiments/oe_n8_2026-10-13/scripts/`) | 30 | 0,16 MB |
| B | Documentación, notebook, citación, informes `.md` de campaña | 37 | 0,28 MB |
| C | Datos experimentales y derivados (`runs.csv`, `runs_oe3.csv`, tablas, figuras, `analysis.json`, `outputs/`, transcripción de las tablas del informe) | 104 | 9,1 MB |
| D | Logs y metadatos de ejecución (`provenance.json`, `manifest.json`, `plan.json`, diarios, `SHA256SUMS`, logs) | 71 | 7,0 MB |
| E | **Todo lo anterior mientras la licencia y la autorización de redistribución no estén confirmadas** | — | — |

Además, publicar la rama subiría **10 commits previos de código experimental** (48 archivos bajo `backend/`, sin hallazgos de secretos ni rutas en su diff) que aún no están en ningún remoto.

## 2. Qué materiales contienen datos experimentales
Categorías C y D: 12 campañas (N1–N8, N8b, N9 abortada, N9b, N11). Son resultados de **mediciones sobre un servidor propio con perfiles de estudiante sintéticos** (`datasets/synthetic_profiles`); no contienen respuestas de personas, SUS ni evaluaciones de expertos. Sin embargo, los resultados son parte del contenido de la tesis aún no sustentada.

## 3. Licencias: opciones, sin elección
No se ha elegido ni declarado ninguna. Opciones habituales, **a decidir por el autor con el asesor/universidad**:
- **Código** (A): licencias permisivas habituales, como MIT o Apache-2.0, o ninguna (todos los derechos reservados).
- **Datos** (C, D): licencias de datos habituales, como CC BY 4.0 o CC0, o ninguna.
- **Documentación** (B): suele seguir a una de las anteriores.
La licencia del código y la de los datos pueden ser distintas. Mientras no se decida, `LICENSE-DATA.md` dice que **no se concede ninguna licencia de reutilización**. Ojo: sin licencia, publicar en un repositorio público permite ver y bifurcar en GitHub, pero no autoriza otros usos.

## 4. Autorizaciones que deben confirmarse (asesor / universidad)
1. ¿La normativa de la universidad permite hacer públicos los datos experimentales y los registros **antes de la sustentación**?
2. ¿El asesor autoriza que se publiquen las campañas **no oficiales** N1–N11 y el hecho de que son resultados parcialmente desfavorables o limitados?
3. ¿Existe alguna restricción de propiedad intelectual de la universidad sobre el código o los datos?
4. ¿Prefiere repositorio **privado** con acceso concedido al asesor, o un repositorio público separado (como se hizo con el trabajo experimental), o un archivo con DOI (p. ej. Zenodo) en una versión congelada?
5. ¿Los nombres de directorio, fechas y la autoría (`CITATION.cff`, portada del informe) pueden ser públicos?

## 5. Excluido de forma permanente de la copia publicable
Ya fuera del paquete (motivo en `data/metadata/STAGING_REPORT.csv`): registros por petición (~222 MB; sus hashes siguen en cada `manifest.json`), observaciones de gran tamaño de N1–N4, scripts de búsqueda bibliográfica que incorporan el correo personal del autor, metadatos bibliográficos de terceros con correos, registros de pytest con rutas locales, `.env`, `.venv`, cachés.

## 6. Qué debe quedar excluido hasta resolver la autorización
Todo el contenido de `data/experiments/` (categorías C y D) y `outputs/`. Podría publicarse antes **solo el código y la documentación** (A y B) con el notebook apuntando a datos que se distribuyen por otra vía autorizada. Sin los datos, el notebook **no se ejecuta externamente** (ver `INFORME_CIERRE_SEGURO.md`, §5).

## 7. Riesgos de redistribución y privacidad
- **Rutas locales y usuario de Windows.** Se encontraron en 14 archivos (logs, diarios, `provenance.json`). Se publican **copias sanitizadas** con las rutas sustituidas (`<RAIZ_REPO>`, `<RUTA_USUARIO>`); los originales permanecen fuera del paquete. Las copias **no son idénticas** a los originales y sus hashes difieren: ver `data/metadata/SANITIZACION.csv` (hash del original y de la copia por separado) y la columna `sha256_original` del manifiesto.
- **El historial de Git local contiene los originales sin sanitizar** (commit `7315cac`). Un `push` de la rama `repro/publicacion-reproducible-2026-10-19` los subiría aunque el árbol final esté limpio. Por eso se preparó una rama alternativa **sin esos objetos** (`repro/publicable-2026-10-19`, ver el informe). No se reescribió ningún historial.
- **Nombre del autor.** Aparece en `CITATION.cff` y en la transcripción de la portada del informe (`informe_D2.9.7_tablas.json`). Es la autoría de la tesis; confirmar que puede ser pública.
- **Irreversibilidad.** Lo que se sube a un repositorio público puede ser copiado o indexado aunque después se borre.
- **Interpretación.** Publicar datos no oficiales no los convierte en oficiales; el README y el notebook lo declaran.
- **Búsqueda automática de secretos:** sin coincidencias en el paquete. Es una heurística, no una garantía; se recomienda una revisión humana de los 71 archivos de la categoría D.

## 8. Pasos que faltan para autorizar el `push`
1. Respuesta del asesor/universidad a las preguntas del punto 4.
2. Elección de licencias (código, datos, documentación) por el autor; añadirlas y actualizar `LICENSE-DATA.md`, `CITATION.cff` y el README.
3. Decidir el destino: repositorio público existente, repositorio nuevo, privado o archivo con DOI.
4. Elegir la rama a subir (`repro/publicable-2026-10-19`, sin originales sin sanitizar) y una etiqueta de versión.
5. Revisión humana de la categoría D.
6. Autorización explícita para `git push`.
7. Tras el push: comprobar en el remoto que la rama existe y ejecutar el notebook desde Colab con un entorno limpio; solo entonces declarar reproducibilidad pública.
