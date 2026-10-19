# Publicación y licencia

## Decisión del autor
El autor declara que las corridas y registros son suyos y que su intención expresa es **publicar la evidencia** para demostrar la procedencia de los datos y la reproducibilidad de los resultados. No se trata de un requisito de permiso previo: se publica salvo restricción concreta de privacidad, confidencialidad, licencia de terceros, credenciales o seguridad.

## Restricciones concretas encontradas y cómo se resolvieron
| Hallazgo | Resolución |
|---|---|
| Rutas locales con el nombre de usuario en 14 archivos de texto | copias sanitizadas, originales fuera del paquete, hashes de ambos (`data/metadata/SANITIZACION.csv`) |
| Correo personal del autor en 6 scripts de búsqueda bibliográfica y correos de terceros en metadatos bibliográficos | excluidos del paquete |
| `.env`, `.venv`, cachés | nunca copiados (el `.env` está ignorado por Git) |
| Historial local con los originales sin sanitizar | rama nueva `repro/publicable-2026-10-19` construida sin esos objetos; la rama de respaldo no se publica |
| Tamaño (≈250 MB de datos) | por debajo del límite de GitHub por archivo (el mayor, 10 MB); sin Git LFS; clon parcial en Colab |
| Licencia no declarada | se documenta; **no se inventa ninguna** (`LICENSE-DATA.md`) |

No se encontraron secretos (búsqueda de patrones de claves, tokens, contraseñas, correos, rutas y hostnames; es una heurística).

## Licencia
Sin licencia declarada (comprobado en el remoto). Opciones habituales, a elegir por el autor: código MIT/Apache-2.0; datos CC BY 4.0/CC0. No se ha atribuido ninguna. La licencia del código y la de los datos pueden diferir.

## Clasificación de archivos
`CLASIFICACION_ARCHIVOS.csv`: A código y pruebas · B documentación y notebook · C datos y derivados · D logs y metadatos. Una publicación futura podría separar los datos (≈250 MB) del código si se prefiere distribuirlos por otra vía (Release, Zenodo).

## Riesgos de redistribución
- Lo publicado en un repositorio público puede copiarse o indexarse aunque se borre después.
- Los resultados son parciales y no oficiales; el README y el notebook lo declaran.
- La autoría (apellido) figura en `CITATION.cff` y en la transcripción de la portada del informe.
