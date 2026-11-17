# -*- coding: utf-8 -*-
"""Ejecuta un notebook de principio a fin en un directorio de trabajo VACIO (equivalente local a «Ejecutar todo» en un Colab limpio).
No es una ejecucion en Google Colab: sirve para comprobar el flujo (descarga publica -> hash -> analisis -> figuras -> pruebas) antes de abrirlo en Colab.
Uso: python tools/ejecutar_local.py <notebook.ipynb> <directorio_de_trabajo_vacio> <salida_ejecutado.ipynb>
El codigo se toma del arbol local (REPRO_LOCAL_REPO); los datos se descargan de GitHub, como en Colab."""
import os
import sys
import time
import nbformat
from nbclient import NotebookClient

nb_path, work, out = sys.argv[1:4]
os.makedirs(work, exist_ok=True)
if os.listdir(work):
    sys.exit(f'El directorio de trabajo debe estar vacio: {work}')
repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
os.environ['REPRO_LOCAL_REPO'] = repo
nb = nbformat.read(nb_path, as_version=4)
t0 = time.time()
cli = NotebookClient(nb, timeout=1800, kernel_name='python3', resources={'metadata': {'path': work}}, allow_errors=False)
try:
    cli.execute()
    estado = 'SIN ERRORES'
except Exception as e:  # se guarda lo ejecutado hasta el fallo
    estado = 'CON ERROR: ' + type(e).__name__
    print(str(e)[-3000:])
nbformat.write(nb, out)
print(f'{os.path.basename(nb_path)}: {estado} en {time.time() - t0:.0f} s -> {out}')
sys.exit(0 if estado == 'SIN ERRORES' else 1)
