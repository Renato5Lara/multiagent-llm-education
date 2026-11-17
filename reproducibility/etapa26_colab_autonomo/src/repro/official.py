"""Comparacion con las cifras oficiales de la tesis (manifests/valores_oficiales.json).

Cada comprobacion lee un valor del resultado REPRODUCIDO (ruta dentro de un JSON, celda de un CSV o numero de lineas de un
JSONL) y lo compara con la cifra oficial dentro de una tolerancia (el redondeo con que la tesis la presenta)."""
import json
import os
import pandas as pd

VALORES_RELATIVO = os.path.join(os.path.dirname(__file__), '..', '..', 'manifests', 'valores_oficiales.json')


def cargar_valores(path=None):
    return json.load(open(path or VALORES_RELATIVO, encoding='utf-8'))


def _leer(c, rutas):
    p = rutas[c['archivo']]
    if c['tipo'] == 'json':
        x = json.load(open(p, encoding='utf-8'))
        for k in c['ruta'].split('/'):
            x = x[int(k)] if isinstance(x, list) else x[k]
        return x
    if c['tipo'] == 'csv':
        d = pd.read_csv(p)
        for col, val in c['filtro'].items():
            d = d[d[col] == val]
        return float(d.iloc[0][c['columna']])
    if c['tipo'] == 'jsonl_count':
        return sum(1 for l in open(p, encoding='utf-8') if l.strip())
    raise ValueError(c['tipo'])


def evaluar(oe, rutas, valores=None):
    """Devuelve una tabla con esperado, obtenido, diferencia y estado de cada cifra oficial de 'oe'."""
    v = valores or cargar_valores()
    filas = []
    for c in v['comprobaciones']:
        if c['oe'] != oe:
            continue
        try:
            got = _leer(c, rutas)
            esp = c['esperado']
            if isinstance(esp, bool) or isinstance(got, bool):
                ok = got == esp
                dif = 0.0 if ok else float('nan')
            else:
                dif = abs(float(got) - float(esp))
                ok = dif <= c.get('tol', 0.0)
            estado = ('COINCIDE' if dif == 0 else 'COINCIDE_REDONDEO') if ok else 'DIFIERE'
        except Exception as e:  # falta de archivo o ruta: nunca se continua en silencio
            got, dif, estado = repr(e), float('nan'), 'NO_EVALUABLE'
        filas.append(dict(id=c['id'], descripcion=c['descripcion'], esperado=c['esperado'], obtenido=got, dif=dif, tolerancia=c.get('tol', 0.0), estado=estado,
                          cifra_en_tesis=c.get('texto_tesis', ''), fuente=c.get('fuente', '')))
    return pd.DataFrame(filas)
