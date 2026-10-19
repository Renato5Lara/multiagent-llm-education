# Informe de cierre seguro previo a la publicación

Fecha: 2026-10-19. **No se publicó nada**: sin `git push`, sin cambio de visibilidad, sin subir datos a ningún servicio. El repositorio remoto es público y sin licencia.

## 1. Estado de Git y commits locales
Solo local. Ninguna de estas ramas existe en el remoto (`git ls-remote` devuelve 0 ramas `repro/*`; `git clone --branch repro/publicable-2026-10-19` desde GitHub falla con «Remote branch … not found»).

| Rama | Contenido | Uso |
|---|---|---|
| `exp/oe-validation-2026-10-13` (`65e8c97`) | base experimental, sin tocar | intacta |
| `repro/publicacion-reproducible-2026-10-19` | trabajo original: 5 commits + sanitización + ignorar exportaciones | **conservada como respaldo**; su historial contiene los logs **sin sanitizar** (commit `7315cac`) → **no subir esta rama** |
| `repro/publicable-2026-10-19` | mismo árbol final reconstruido en 4 commits sobre `f4687e4`, sin los originales sin sanitizar en el historial | candidata a publicar |

Commits de la rama publicable sobre `65e8c97`: `f4687e4` (código `http_campaign`: diario, `--resume`, `--start-margin`; 11 pruebas) → `fdeef8a` (datos y manifiesto) → `60ea01e` (scripts, pruebas, notebook) → `25d3980` (documentación) → `29ef5f0` (`.gitignore`).
Los árboles de `reproducibility/` de ambas ramas son idénticos (`git diff` vacío).
Tags públicos (`demo-certification-v1`, `thesis-d6-consolidated`, …) y `origin/*` no se tocaron. No hubo reescritura de historial ni force push; la rama publicable es una rama **nueva**.

Un `push` de la rama publicable subiría **14 commits** que no están en ningún remoto: 10 previos de código experimental (48 archivos en `backend/`, escaneados: sin secretos ni rutas en su diff) y 4 de este trabajo, más el commit de `.gitignore`.

Hashes de los archivos principales (rama publicable):
```
152e1987c15ccf62…  EVIDENCE_MANIFEST.csv
2a0e1142c1d8233d…  RESULTS_TRACEABILITY.csv
19948eca8ae7abe3…  notebooks/reproducibilidad_tesis.ipynb
176142bd5e5c16f7…  outputs/verification_report.json
e7c332a5ab31d40b…  data/metadata/SANITIZACION.csv
d72e03b56e5e9fe8…  environment/requirements.txt
a6bb2934de7fd5123ca…  D2.9.7….docx (informe; sin cambios)
```
Los originales de campaña (`backend/experiments/oe_*`) siguen **sin rastrear y sin modificar**: 1251 de 1251 entradas de sus `SHA256SUMS` coinciden.

## 2. Inventario de lo que se publicaría
Ver [`CLASIFICACION_ARCHIVOS.csv`](CLASIFICACION_ARCHIVOS.csv): A código y pruebas 30 archivos (0,16 MB) · B documentación y notebook 37 (0,28 MB) · C datos y derivados 104 (9,1 MB) · D logs y metadatos 71 (7,0 MB). Total ≈ 16,6 MB, sin Git LFS. Detalle de qué se excluye y por qué: `data/metadata/STAGING_REPORT.csv`.

## 3. Pendiente de autorización
Todo C y D (y, en rigor, A y B por la licencia). Ver [`PUBLICACION_PENDIENTE_AUTORIZACION.md`](PUBLICACION_PENDIENTE_AUTORIZACION.md). No se eligió ninguna licencia.

## 4. Riesgos de privacidad
- **Rutas locales con el nombre de usuario de Windows:** 14 archivos (logs de N9, N9b y N11; diarios; ocho `provenance.json`). Solución aplicada: copias sanitizadas (`<RAIZ_REPO>`, `<RUTA_USUARIO>`), originales fuera del paquete, hashes de original y copia por separado en `data/metadata/SANITIZACION.csv`. **Las copias no son idénticas a los originales** y el manifiesto lo marca (columna `sha256_original`). Consecuencia: los `SHA256SUMS` y `manifest.json` internos de cada campaña ya no pueden verificar esos 14 archivos; `verify_hashes.py` los cuenta como «sanitizados», no como coincidentes ni como errores.
- **Segunda pasada de escaneo** sobre todo el paquete (rutas Windows/Unix, correos, tokens, hostnames, MAC, IP): sin hallazgos, salvo el apellido del autor en `CITATION.cff` y en la transcripción de la portada del informe (autoría de la tesis). Es una heurística; se recomienda revisión humana de la categoría D (71 archivos).
- Los correos del autor y de terceros que aparecían en scripts y metadatos bibliográficos se **excluyeron** del paquete.
- El historial de la rama de respaldo contiene los originales sin sanitizar: no publicarla.

## 5. Notebook en un entorno externo limpio
Prueba hecha en un clon local limpio (ruta corta, solo `reproducibility/`), venv nuevo con únicamente `environment/requirements-dev.txt`, **sin** `REPRO_LOCAL_ROOT`, ejecutando el notebook desde su carpeta:
- 18/18 pruebas pasan; el notebook se ejecuta de principio a fin (10 celdas de código) y da 328 `COINCIDE`, 13 `NO_REPRODUCIBLE`, 0 discrepancias. No usó rutas de mi equipo, credenciales ni archivos fuera del clon.
- **Lo que no está demostrado:** que funcione desde GitHub. La celda C clona `https://github.com/Renato5Lara/multiagent-llm-education` en `REF`, y esa rama **no existe en el remoto**; hoy fallaría con un error claro. Faltaría, por tanto, publicar la rama (o entregar la carpeta `reproducibility/` por otra vía autorizada). **No se debe presentar el notebook como públicamente reproducible hasta comprobarlo tras el push.** Tampoco se ejecutó en Google Colab real.
- Datos que faltan para una auditoría completa y que **no están en el paquete**: registros por petición (`raw/*.csv`, ≈222 MB), observaciones in-process y de N1–N4 (necesarias para `k_stop` y para N1/N3 celda a celda). Se conservan localmente con sus hashes en los `manifest.json`.

## 6. Resultados (sin cambios)
328 comprobaciones coinciden a la precisión publicada (Tablas 8, 9, 10, 11, 18, 19, 20 y la 17 salvo `k_stop`); 13 cifras declaradas no reproducibles (con motivo); 0 discrepancias; 10 de 10 CSV derivados regenerados byte a byte. Siguen sin recalcular celda a celda las Tablas 5–7, 13–14, 21–25, 27–29, 32, 37, 39–41 y 44. Esto **no** es una validación total de la tesis ni de las hipótesis.

## 7. Cambios hechos en esta fase
Sanitización de 14 archivos; exclusión de `build_conciliacion.py` (ruta local); `verify_hashes.py` trata las copias sanitizadas; columna `sha256_original` en el manifiesto; clasificación A–E; documento de autorización pendiente; `.gitignore` para exportaciones del notebook; rama publicable sin originales sin sanitizar.

## 8. Pasos que faltan para autorizar el `push`
1. Respuesta del asesor/universidad (permiso de redistribución, momento de publicación, público/privado).
2. Elección de licencias por el autor; actualizar `LICENSE-DATA.md`, `CITATION.cff`, README.
3. Decidir destino y rama (recomendada: `repro/publicable-2026-10-19`; **no** la de respaldo).
4. Revisión humana de la categoría D y de las copias sanitizadas.
5. Autorización explícita para `git push`.
6. Tras el push: verificar la rama en el remoto, ejecutar el notebook en Colab limpio y solo entonces declarar reproducibilidad pública; valorar etiqueta de versión y archivo con DOI.
