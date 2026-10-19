# Registro de ejecución (separado del notebook)

Ejecución real del notebook y de las 26 pruebas en un **clon limpio** (clon parcial de la rama `repro/publicable-2026-10-19`, entorno virtual nuevo con solo `environment/requirements-dev.txt`, Python 3.13.5, sin variables de entorno del autor).

- `notebook_ejecutado_en_clon_limpio.sanitizado.ipynb`: el notebook con las salidas de esa ejecución. El notebook de `notebooks/` se conserva **sin salidas**.
- `pytest_en_clon_limpio.sanitizado.txt`: `pytest -v`, 26 pruebas pasadas.
- Ambos tienen las rutas locales sustituidas (`<RAIZ_CLON>`, `<RUTA_USUARIO>`); **no son idénticos** a los originales: `SANITIZACION_REGISTROS.json` guarda ambos hashes.
