# -*- coding: utf-8 -*-
"""Genera los seis notebooks autonomos (OE1, OE2-A, OE2-B, OE3, OE4, OE5) a partir de los notebooks de comprobacion ya publicados
(../etapa23_oe1_oe5/notebooks/) y de la biblioteca repro. Las celdas de verificacion, recalculo HTTP y analisis se REUTILIZAN tal cual
(salvo que '!comando' pasa a sh(...) y se elimina la subida manual de archivos); se anaden las celdas de descarga, cifras de la tesis,
clasificacion de diferencias, tablas, figuras, pruebas automaticas y resumen.
Uso: python tools/generar_notebooks.py   (requiere nbformat)"""
import json
import os
import re
import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(AQUI)
ORIGEN = os.path.join(os.path.dirname(BASE), 'etapa23_oe1_oe5', 'notebooks')
DESTINO = os.path.join(BASE, 'notebooks')
REPO_URL = 'https://github.com/Renato5Lara/multiagent-llm-education.git'
REPO_REF = 'repro-etapa26-v1'


def src(nb, i):
    return ''.join(nb['cells'][i]['source'])


def convertir_shell(texto):
    """'!cmd' -> sh(f"cmd"); '!tail' se sustituye por impresion de las colas de los registros."""
    out = []
    for l in texto.split('\n'):
        m = re.match(r'^(\s*)!(.*)$', l)
        if not m:
            out.append(l)
        elif m.group(2).startswith('tail'):
            logs = m.group(2).split()[2:]
            out.append(m.group(1) + 'for _l in %r: print(_l, "->", open(_l, encoding="utf-8", errors="replace").read()[-300:])' % logs)
        else:
            out.append(m.group(1) + 'sh(f"%s")' % m.group(2).replace('"', '\\"'))
    return '\n'.join(out)


SETUP = '''import os, sys, platform, subprocess, json
IN_COLAB = 'google.colab' in sys.modules
REPO_URL = '%(url)s'
REPO_REF = '%(ref)s'            # etiqueta inmutable del codigo; los datos estan fijados por commit en manifests/data_manifest.json
if os.environ.get('REPRO_LOCAL_REPO'):   # solo para pruebas locales antes de publicar la etiqueta
    REPO_DIR = os.environ['REPRO_LOCAL_REPO']
else:
    REPO_DIR = 'repo_repro'
    if not os.path.isdir(REPO_DIR):
        subprocess.run(['git', 'clone', '--quiet', '--depth', '1', '--branch', REPO_REF, REPO_URL, REPO_DIR], check=True)
sys.path.insert(0, os.path.join(REPO_DIR, 'reproducibility', 'etapa26_colab_autonomo', 'src'))
import repro
from repro import sh
print('Codigo de analisis:', REPO_URL, '@', REPO_REF)
'''

ENTORNO = '''%(instalar)simport %(imp)s
ENTORNO = dict(python=platform.python_version(), plataforma=platform.platform(), numpy=numpy.__version__, scipy=scipy.__version__, pandas=pandas.__version__, matplotlib=matplotlib.__version__, cpu=os.cpu_count()%(extra)s)
print(ENTORNO)
'''
INSTALAR = '''try:
    import statsmodels
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', '-q', 'install', 'statsmodels'], check=True)
    import statsmodels
'''

DESCARGA = '''# Descarga automatica desde GitHub (commit fijado) y verificacion SHA-256 contra el manifiesto. No hay que subir nada.
# Si falta un archivo, no se puede descargar o su hash no coincide, se detiene con el archivo, la URL y el hash esperado.
PAQUETES = %(paquetes)r
repro.fetch_packages(PAQUETES, dest=%(dest)r)
'''

OFICIAL = '''from repro import official, validation, tables, figures
from repro.data_loading import sha256_file
import pandas as pd
RUTAS = %(rutas)s
cifras = official.evaluar(%(oe)r, RUTAS)
print(cifras[['id', 'descripcion', 'esperado', 'obtenido', 'dif', 'estado']].to_string(index=False))
'''

REGISTRO = '''import scipy
REG = validation.Registro(scipy_version=scipy.__version__)
COMPARACIONES = %(comp)s
for _e, _a, _b in COMPARACIONES:
    REG.comparar(_e, _a, _b)
'''

TABLAS = '''OUT = 'outputs'
TABLAS = %(tablas)s
tablas_generadas = tables.exportar_tablas(%(oe)r, TABLAS, os.path.join(OUT, 'tables'))
print('Tablas generadas:')
for _t in tablas_generadas:
    print('  ', _t)
'''

FIGURA = '''METAS = official.cargar_valores()['metas_de_diseno']
%(pre)sfig = figures.%(fn)s(%(entrada)s, os.path.join(OUT, 'figures', %(oe)r), metas=METAS)
ref = figures.%(fn)s(%(ref)s, os.path.join(OUT, 'figures_ref_desde_resultado_local', %(oe)r), metas=METAS)
REG.comparar('Serie de la %(titulo)s reproducida frente a la serie dibujada desde el resultado oficial local', fig['serie_csv'], ref['serie_csv'])
_t = official.cargar_valores()['figuras_tesis'][%(clave)r]
IDENTICA = sha256_file(fig['png']) == _t['sha256_png_tesis']
print('%(titulo)s: PNG identico bit a bit al de la tesis (pagina %%s del indice): %%s' %% (_t['pagina_indice'], IDENTICA))
if not IDENTICA:
    print('  Esperable fuera del entorno de la tesis (matplotlib 3.10.3 y fuente Arial): la imagen puede diferir en pixeles; la comprobacion valida es la de la serie dibujada.')
try:
    from IPython.display import Image, display
    display(Image(fig['png']))
except Exception:
    pass
'''

PRUEBAS = '''fallos = []
if cifras.estado.isin(['DIFIERE', 'NO_EVALUABLE']).any():
    fallos.append('cifras oficiales: ' + str(cifras[cifras.estado.isin(['DIFIERE', 'NO_EVALUABLE'])][['id', 'estado']].values.tolist()))
peor, cuenta = REG.veredicto()
if peor in ('NO_EXPLICADA', 'NO_REPRODUCIBLE'):
    fallos.append('comparacion con el resultado local: ' + peor)
%(extra)sassert not fallos, fallos
print('PRUEBAS AUTOMATICAS DE CONSISTENCIA: todas superadas | cifras oficiales comprobadas:', len(cifras), '| comparaciones:', cuenta)
'''

RESUMEN = '''import shutil
resumen = tables.guardar_resumen(%(oe)r, os.path.join(OUT, 'reports'), REG.tabla(), cifras, ENTORNO, extra=dict(veredicto=peor, conteo=cuenta, paquetes=PAQUETES))
print('RESUMEN DE REPRODUCCION %(oe)s')
print(REG.tabla()[['comparacion', 'categoria', 'dif_abs_max']].to_string(index=False))
print('Veredicto (peor categoria):', peor, cuenta)
print('Cifras de la tesis comprobadas: %%d (%%d coinciden exactamente, %%d dentro del redondeo)' %% (len(cifras), (cifras.estado == 'COINCIDE').sum(), (cifras.estado == 'COINCIDE_REDONDEO').sum()))
print('LIMITACIONES: %(lim)s')
print('Alcance: se reproduce el analisis, no la adquisicion de datos; no se repite ninguna campana.')
_z = shutil.make_archive('resultados_%(oe)s', 'zip', OUT)
print('Salidas empaquetadas en', os.path.basename(_z))
if IN_COLAB:
    from google.colab import files
    files.download(_z)
'''


OE5_FIG = """_of = official.cargar_valores()
CSV_IDENTICO = sha256_file(RUTAS['f1_por_perfil.csv']) == _of['entradas_de_figuras_oficiales']['f1_por_perfil_csv_sha256_oficial']
print('f1_por_perfil.csv reproducido: SHA-256 identico al del resultado oficial que alimento la Figura 5:', CSV_IDENTICO)
_t = _of['figuras_tesis']['fig_oe5']
IDENTICA = sha256_file(fig['png']) == _t['sha256_png_tesis']
print('Figura 5: PNG identico bit a bit al de la tesis (pagina %s del indice): %s' % (_t['pagina_indice'], IDENTICA))
if not IDENTICA:
    print('  Esperable fuera del entorno de la tesis (matplotlib 3.10.3 y fuente Arial); la comprobacion valida es la del CSV de entrada y la serie dibujada.')
try:
    from IPython.display import Image, display
    display(Image(fig['png']))
except Exception:
    pass
"""


def md(s): return new_markdown_cell(s)
def code(s): return new_code_cell(s)


def cabecera(orig, titulo, comprueba_extra=None):
    t = src(orig, 0)
    t = t.replace('Ejecute las celdas en orden en un entorno nuevo de Colab; la carga de datos pide subir los archivos indicados.',
                  'Pulse «Ejecutar todo» en un entorno nuevo de Colab: los datos se descargan solos desde GitHub (commit fijado) y se verifican por SHA-256; no hay que subir ni buscar archivos.')
    t = re.sub(r'\*\*Contenido \(diez pasos\)\.\*\*.*$', '', t, flags=re.S).rstrip()
    t = re.sub(r'^# .*', '# ' + titulo, t, count=1)
    return t + ('\n\n' + comprueba_extra if comprueba_extra else '') + '\n\n' + PASOS


PASOS = ('**Contenido.** 1 descripción · 2 entorno y código (clonado de la etiqueta inmutable) · 3 descarga automática y verificación SHA-256 · 4 validación de integridad y estructura · '
         '5 preprocesamiento y cálculo de indicadores (scripts sellados) · 6 análisis estadístico · 7 comparación con el resultado local y con las cifras de la tesis · 8 tablas · 9 gráficos · '
         '10 pruebas automáticas · 11 resumen. Las diferencias se clasifican como exacta, dentro de tolerancia, explicada por versión, no explicada o no reproducible.')

# (objetivo, archivo, notebook origen, paquetes, dest, estadisticas, celdas reutilizadas (indice o ('md',indice)), config de salida)
SPECS = {
 'OE1': dict(titulo='OE1: reproducción autónoma en Google Colab', origen='OE1', paquetes=['oe1_http_p1'], dest='.', sm=True,
             celdas=[3, 4, 5, 6, 7, 8, 9],
             rutas={'resultados_oe1.json': 'http/oe1/salida/resultados_oe1.json', 'celdas.csv': 'http/oe1/salida/celdas.csv'},
             comp=[('OE1 resultados_oe1.json', 'http/oe1/salida/resultados_oe1.json', 'http/oe1/esperado_local/resultados_oe1.json'),
                   ('OE1 celdas.csv', 'http/oe1/salida/celdas.csv', 'http/oe1/esperado_local/celdas.csv'),
                   ('OE1 corridas_indicadores.csv', 'http/oe1/salida/corridas_indicadores.csv', 'http/oe1/esperado_local/corridas_indicadores.csv'),
                   ('OE1 efectos.csv', 'http/oe1/salida/efectos.csv', 'http/oe1/esperado_local/efectos.csv')],
             tablas={'celdas': 'http/oe1/salida/celdas.csv', 'efectos': 'http/oe1/salida/efectos.csv', 'corridas_indicadores': 'http/oe1/salida/corridas_indicadores.csv'},
             figura=dict(fn='fig_oe1', clave='fig_oe1', titulo='Figura 1', entrada="RUTAS['resultados_oe1.json']", ref="'http/oe1/esperado_local/resultados_oe1.json'", pre=''),
             lim='las 120 corridas tuvieron interferencia ambiental; la confiabilidad cae con la perdida de mensajes; RNF03 no se cumple (F1_adapt 0,8044 < 0,85); campana no controlada.'),
 'OE2-A': dict(nota='**Alcance de este cuaderno.** Solo el componente A del OE2 (medición en proceso, 5 000 ciclos). El componente B (HTTP) está en `OE2B_reproduccion_autonoma.ipynb`.', titulo='OE2-A: reproducción autónoma en Google Colab (convergencia, latencia y throughput en proceso)', origen='OE2', paquetes=['oe2a_colab_paquete'], dest='.', sm=True,
               celdas=[4, 5, 6],
               rutas={'resultados_oe2a.json': 'oe2a/salida_colab/resultados_oe2a.json'},
               comp=[('OE2-A resultados_oe2a.json', 'oe2a/salida_colab/resultados_oe2a.json', 'oe2a/esperado_resultados_oe2a_local.json')],
               tablas={'medias_por_perfil': 'oe2a/salida_colab/medias_por_perfil.csv'},
               figura=dict(fn='fig_oe2a_complementaria', clave=None, titulo='figura complementaria OE2-A', entrada="'oe2a/campana_01/raw_observations.csv', RUTAS['resultados_oe2a.json']", ref=None, pre=''),
               lim='5 000 ciclos en un solo flujo (no mide capacidad); 2 770 ciclos con interferencia fuerte; la campana OE2A-02 (replica controlada) no se ejecuto por cuatro fallos de la compuerta de inicio.'),
 'OE2-B': dict(nota='**Alcance de este cuaderno.** Solo el componente B del OE2 (por HTTP, 120 corridas válidas). El componente A está en `OE2A_reproduccion_autonoma.ipynb`.', titulo='OE2-B: reproducción autónoma en Google Colab (latencia, throughput y convergencia por HTTP)', origen='OE2', paquetes=['oe2b_colab_paquete', 'oe2b_http_p1', 'oe2b_http_p2'], dest='.', sm=True,
               celdas=['md7', 8, 9, 10, 'md11', 12, 'md13', 14, 'md15', 16, 'md17', 18, 'md19', 20, 'md21', 22, 23, 'md24', 25],
               rutas={'resultados_oe2b.json': 'oe2b/salida_colab/preregistrado/resultados_oe2b.json', 'intentos.jsonl': 'oe2b/campana_01/intentos.jsonl'},
               comp=[('OE2-B resultados_oe2b.json', 'oe2b/salida_colab/preregistrado/resultados_oe2b.json', 'oe2b/esperado_local/resultados_oe2b.json'),
                     ('OE2-B resumen_por_carga.csv', 'oe2b/salida_colab/preregistrado/resumen_por_carga.csv', 'oe2b/esperado_local/resumen_por_carga.csv'),
                     ('OE2-B exploratorio_oe2b.json', 'oe2b/salida_colab/exploratorio/exploratorio_oe2b.json', 'oe2b/esperado_local/exploratorio_oe2b.json'),
                     ('OE2-B estratos_por_carga.csv', 'oe2b/salida_colab/exploratorio/estratos_por_carga.csv', 'oe2b/esperado_local/estratos_por_carga.csv')],
               tablas={'resumen_por_carga': 'oe2b/salida_colab/preregistrado/resumen_por_carga.csv', 'estratos_por_carga_exploratorio': 'oe2b/salida_colab/exploratorio/estratos_por_carga.csv'},
               figura=dict(fn='fig_oe2', clave='fig_oe2', titulo='Figura 2', entrada="RUTAS['resultados_oe2b.json']", ref="'oe2b/esperado_local/resultados_oe2b.json'", pre=''),
               lim='los resultados dependen de la carga y de la interferencia (120 de 120 corridas interferidas); no todos los niveles de carga cumplen a la vez las metas; se conservan los 180 intentos (131 correctos, 47 fallos tecnicos, 2 ventanas invalidas).'),
 'OE3': dict(titulo='OE3: reproducción autónoma en Google Colab', origen='OE3', paquetes=['oe3_colab_paquete_v2'], dest='oe3', sm=True,
             celdas=[3, 4, 5],
             rutas={'resultados_oe3.json': 'oe3/salida_colab/resultados_oe3.json', 'contrastes_efectos_principales.csv': 'oe3/salida_colab/contrastes_efectos_principales.csv'},
             comp=[('OE3 resultados_oe3.json', 'oe3/salida_colab/resultados_oe3.json', 'oe3/esperado_resultados_oe3_local.json')],
             tablas={'contrastes_efectos_principales': 'oe3/salida_colab/contrastes_efectos_principales.csv'},
             figura=dict(fn='fig_oe3', clave='fig_oe3', titulo='Figura 3', entrada="RUTAS['contrastes_efectos_principales.csv']", ref="'oe3/esperado_contrastes.csv'",
                         pre="_a = json.load(open('oe3/esperado_resultados_oe3_local.json', encoding='utf8'))\npd.DataFrame([{**c, 'ic95_inf': c['ic95'][0], 'ic95_sup': c['ic95'][1]} for c in _a['contrastes']]).drop(columns='ic95').to_csv('oe3/esperado_contrastes.csv', index=False)\n"),
             lim='campana no controlada con interferencia ambiental; el p de Wilcoxon de «social frente a PSO» depende de la version de scipy (5,1e-4 entre 1.16.3 y 1.18.1) sin afectar a Holm ni a las conclusiones; la version 1 del notebook esta descartada.'),
 'OE4': dict(titulo='OE4: reproducción autónoma en Google Colab', origen='OE4', paquetes=['oe4_colab_paquete', 'oe4_http_p1', 'oe4_http_p2', 'oe4_http_p3', 'oe4_http_p4'], dest='.', sm=True,
             celdas=['md3', 4, 5, 6, 'md7', 8, 'md9', 10, 'md11', 12, 'md13', 14, 'md15', 16, 17, 18, 'md19', 20],
             rutas={'resultados_oe4.json': 'oe4/salida_colab/preregistrado/resultados_oe4.json', 'celdas.csv': 'oe4/salida_colab/preregistrado/celdas.csv', 'intentos.jsonl': 'oe4/campana_01/intentos.jsonl'},
             comp=[('OE4 resultados_oe4.json', 'oe4/salida_colab/preregistrado/resultados_oe4.json', 'oe4/esperado_local/resultados_oe4.json')] +
                  [(f'OE4 {f}.csv', f'oe4/salida_colab/preregistrado/{f}.csv', f'oe4/esperado_local/{f}.csv') for f in ('celdas', 'contrastes', 'anova_p95', 'anova_thr', 'anova_tconv')] +
                  [('OE4 exploratorio_interferencia_oe4.json', 'oe4/salida_colab/exploratorio_interferencia_oe4.json', 'oe4/esperado_local/exploratorio_interferencia_oe4.json')],
             tablas={f: f'oe4/salida_colab/preregistrado/{f}.csv' for f in ('celdas', 'contrastes', 'anova_p95', 'anova_thr', 'anova_tconv')},
             figura=dict(fn='fig_oe4', clave='fig_oe4', titulo='Figura 4', entrada="RUTAS['celdas.csv']", ref="'oe4/esperado_local/celdas.csv'", pre=''),
             lim='216 corridas validas de 220 intentos, todas con interferencia ambiental; analisis por bloques; la campana no es controlada.'),
 'OE5': dict(titulo='OE5: reproducción autónoma en Google Colab', origen='OE5', paquetes=['oe5_colab_paquete'], dest='oe5', sm=False,
             celdas=[3, 4, 5],
             rutas={'resultados_oe5.json': 'oe5/salida_colab/resultados_oe5.json', 'f1_por_perfil.csv': 'oe5/salida_colab/f1_por_perfil.csv'},
             comp=[('OE5 resultados_oe5.json', 'oe5/salida_colab/resultados_oe5.json', 'oe5/esperado_resultados_oe5_local.json'),
                   ('OE5 enmienda 1', 'oe5/salida_colab_enmienda1/resultados_enmienda1.json', 'oe5/esperado_enmienda1_local.json')],
             tablas={'f1_por_perfil': 'oe5/salida_colab/f1_por_perfil.csv'},
             figura=dict(fn='fig_oe5', clave='fig_oe5', titulo='Figura 5', entrada="RUTAS['f1_por_perfil.csv']", ref=None, pre=''),
             lim='F1_adapt 0,8044 (IC95 % 0,7785 a 0,8303) no alcanza el umbral de 0,85 (RNF03 no cumplido); 100 perfiles sinteticos x 10 repeticiones; la dependencia entre repeticiones se analiza en la enmienda 1.'),
}


def construir(oe, sp):
    orig = json.load(open(os.path.join(ORIGEN, sp['origen'] + '_comprobacion_colab.ipynb'), encoding='utf-8'))
    C = [md(cabecera(orig, sp['titulo'], sp.get('nota')))]
    C.append(md('## 1. Entorno y código de análisis\nEl código vive en el repositorio público (módulos legibles en `reproducibility/etapa26_colab_autonomo/src/repro/`); los scripts de análisis sellados vienen dentro de los paquetes de datos, con su hash verificado.'))
    C.append(code(SETUP % dict(url=REPO_URL, ref=REPO_REF)))
    C.append(code(ENTORNO % (dict(instalar=INSTALAR, imp='statsmodels, numpy, scipy, pandas, matplotlib', extra=', statsmodels=statsmodels.__version__') if sp['sm'] else dict(instalar='', imp='numpy, scipy, pandas, matplotlib', extra=''))))
    C.append(md('## 2. Descarga automática y verificación de los paquetes (SHA-256)'))
    C.append(code(DESCARGA % dict(paquetes=sp['paquetes'], dest=sp['dest'])))
    C.append(md('## 3. Verificación interna, cálculo y análisis (celdas del notebook de comprobación publicado, sin cambios salvo la ejecución de scripts)'))
    for c in sp['celdas']:
        if isinstance(c, str):
            C.append(md(src(orig, int(c[2:]))))
        else:
            C.append(code(convertir_shell(src(orig, c))))
    C.append(md('## 4. Comparación con las cifras de la tesis\nCada cifra se lee del resultado **reproducido** y se compara con la que figura en la tesis (versión CIERRE_FINAL) y en el JSON oficial sellado (`manifests/valores_oficiales.json`).'))
    rutas = '{' + ', '.join(f'{k!r}: {v!r}' for k, v in sp['rutas'].items()) + '}'
    C.append(code(OFICIAL % dict(rutas=rutas, oe=oe)))
    C.append(md('## 5. Clasificación de las diferencias frente al resultado local\nExacta · dentro de tolerancia (1e-9) · explicada por versión · no explicada · no reproducible.'))
    comp = '[' + ', '.join(repr(t) for t in sp['comp']) + ']'
    C.append(code(REGISTRO % dict(comp=comp)))
    C.append(md('## 6. Tablas'))
    C.append(code(TABLAS % dict(tablas=repr(sp['tablas']), oe=oe)))
    f = sp['figura']
    C.append(md('## 7. Gráficos\nSe generan desde la salida del análisis ejecutado arriba (no desde valores copiados). Se exportan PNG (300 ppi), SVG y el CSV de la serie dibujada (`figure_data/`).'))
    if f['ref'] is not None:
        C.append(code(FIGURA % dict(pre=f['pre'], fn=f['fn'], entrada=f['entrada'], ref=f['ref'], oe=oe, titulo=f['titulo'], clave=f['clave'])))
    elif oe == 'OE5':
        C.append(code("METAS = official.cargar_valores()['metas_de_diseno']\nfig = figures.fig_oe5(RUTAS['f1_por_perfil.csv'], os.path.join(OUT, 'figures', 'OE5'), metas=METAS)\n" + OE5_FIG))
    else:  # OE2-A: figura complementaria (no esta en la tesis)
        C.append(code("METAS = official.cargar_valores()['metas_de_diseno']\nfig = figures.fig_oe2a_complementaria(%s, os.path.join(OUT, 'figures', 'OE2-A'))\nprint('Figura COMPLEMENTARIA (no figura en la tesis): ' + fig['png'])\ntry:\n    from IPython.display import Image, display\n    display(Image(fig['png']))\nexcept Exception:\n    pass\n" % f['entrada']))
    C.append(md('## 8. Pruebas automáticas de consistencia'))
    extra = ''
    if f['clave']:
        extra = "if not (os.path.getsize(fig['png']) > 0 and os.path.getsize(fig['serie_csv']) > 0):\n    fallos.append('figura vacia')\n"
    else:
        extra = "if not os.path.getsize(fig['png']) > 0:\n    fallos.append('figura vacia')\n"
    if oe == 'OE5':
        extra += "if not (CSV_IDENTICO or (cifras.loc[cifras.id == 'OE5-01', 'estado'] != 'DIFIERE').all()):\n    fallos.append('f1_por_perfil.csv difiere del oficial')\n"
    C.append(code(PRUEBAS % dict(extra=extra)))
    C.append(md('## 9. Resumen final de la reproducción'))
    C.append(code(RESUMEN % dict(oe=oe, lim=sp['lim'].replace("'", ''))))
    nb = new_notebook(cells=C, metadata={'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}, 'language_info': {'name': 'python'},
                                        'colab': {'provenance': [], 'name': f'{oe}_reproduccion_autonoma.ipynb'}})
    nbformat.validate(nb)
    ruta = os.path.join(DESTINO, f"{oe.replace('-', '')}_reproduccion_autonoma.ipynb")
    os.makedirs(DESTINO, exist_ok=True)
    with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
        nbformat.write(nb, fh)
    return ruta


if __name__ == '__main__':
    for oe, sp in SPECS.items():
        print(construir(oe, sp))
