"""Comparacion numerica entre el resultado reproducido y el de referencia, con clasificacion explicita.

Categorias (de mejor a peor):
  EXACTA                 todas las hojas numericas iguales bit a bit y las no numericas identicas
  DENTRO_DE_TOLERANCIA   hay diferencias numericas pero ninguna supera 1e-9 (absoluta y relativa)
  EXPLICADA_POR_VERSION  la unica diferencia > tolerancia son p de Wilcoxon y la version de scipy difiere de la de referencia
  NO_EXPLICADA           diferencia > tolerancia sin explicacion documentada
  NO_REPRODUCIBLE        la estructura (claves/columnas/forma) difiere
La tolerancia es un umbral de informe, no un umbral del protocolo."""
import json
import pandas as pd

TOL_ABS = 1e-9
TOL_REL = 1e-9
SCIPY_REFERENCIA = '1.18.1'   # version con la que se calcularon los resultados oficiales locales (freeze 2026-11-13)


def hojas(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from hojas(v, p + '/' + str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from hojas(v, p + '/' + str(i))
    else:
        yield p, x


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def compare_json(ruta_a, ruta_b):
    A = dict(hojas(json.load(open(ruta_a, encoding='utf8'))))
    B = dict(hojas(json.load(open(ruta_b, encoding='utf8'))))
    r = dict(estructura_igual=set(A) == set(B), n_hojas=len(A), n_numericas=0, n_con_diferencia=0, max_abs=0.0, max_rel=0.0, peor=None, fuera_tol=[])
    for k, va in A.items():
        if k not in B:
            continue
        vb = B[k]
        if _num(va) and _num(vb):
            r['n_numericas'] += 1
            d = abs(va - vb)
            if d > 0:
                r['n_con_diferencia'] += 1
                rel = d / max(abs(vb), 1e-300)
                if d > r['max_abs']:
                    r['max_abs'] = d
                    r['peor'] = (k, va, vb)
                r['max_rel'] = max(r['max_rel'], rel)
                if d > TOL_ABS and rel > TOL_REL:
                    r['fuera_tol'].append((k, va, vb))
        elif va != vb:
            r['fuera_tol'].append((k, va, vb))
            r['n_con_diferencia'] += 1
    return r


def compare_csv(ruta_a, ruta_b):
    a = pd.read_csv(ruta_a)
    b = pd.read_csv(ruta_b)
    r = dict(estructura_igual=list(a.columns) == list(b.columns) and a.shape == b.shape, n_hojas=int(a.size), n_numericas=0, n_con_diferencia=0, max_abs=0.0, max_rel=0.0, peor=None, fuera_tol=[])
    if not r['estructura_igual']:
        return r
    for c in a.columns:
        if pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c]) and not pd.api.types.is_bool_dtype(a[c]):
            dif = (a[c] - b[c]).abs().fillna(0)
            r['n_numericas'] += int(a[c].notna().sum())
            nd = int((dif > 0).sum())
            r['n_con_diferencia'] += nd
            if nd:
                rel = (dif / b[c].abs().clip(lower=1e-300)).where(dif > 0, 0.0)
                r['max_abs'] = max(r['max_abs'], float(dif.max()))
                r['max_rel'] = max(r['max_rel'], float(rel.max()))
                bad = (dif > TOL_ABS) & (rel > TOL_REL)
                for i in a.index[bad][:20]:
                    r['fuera_tol'].append((f'{c}[{i}]', float(a.at[i, c]), float(b.at[i, c])))
        else:
            sa = a[c].astype(object).where(a[c].notna(), '<NA>').astype(str)
            sb = b[c].astype(object).where(b[c].notna(), '<NA>').astype(str)
            bad = sa != sb
            nd = int(bad.sum())
            r['n_con_diferencia'] += nd
            for i in a.index[bad][:20]:
                r['fuera_tol'].append((f'{c}[{i}]', sa[i], sb[i]))
    return r


def clasificar(r, scipy_version=None):
    if not r['estructura_igual']:
        return 'NO_REPRODUCIBLE', 'la estructura de claves/columnas difiere'
    if r['n_con_diferencia'] == 0:
        return 'EXACTA', 'sin diferencia numerica'
    if not r['fuera_tol']:
        return 'DENTRO_DE_TOLERANCIA', f"diferencia maxima {r['max_abs']:.2e} (<= {TOL_ABS:g} o relativa <= {TOL_REL:g})"
    solo_wilcoxon = all(str(k).endswith('/p_wilcoxon') for k, _, _ in r['fuera_tol'])
    if solo_wilcoxon and scipy_version is not None and scipy_version != SCIPY_REFERENCIA:
        return 'EXPLICADA_POR_VERSION', f"p de Wilcoxon con diferencias nulas: depende de scipy ({scipy_version} frente a {SCIPY_REFERENCIA} de referencia)"
    return 'NO_EXPLICADA', f"{len(r['fuera_tol'])} hojas fuera de tolerancia; primera: {r['fuera_tol'][0]}"


class Registro:
    """Acumula las comparaciones de un notebook y produce la tabla y el veredicto final."""
    ORDEN = ['EXACTA', 'DENTRO_DE_TOLERANCIA', 'EXPLICADA_POR_VERSION', 'NO_EXPLICADA', 'NO_REPRODUCIBLE']

    def __init__(self, scipy_version=None):
        self.filas = []
        self.scipy_version = scipy_version

    def comparar(self, etiqueta, ruta_a, ruta_b):
        r = (compare_csv if str(ruta_a).endswith('.csv') else compare_json)(ruta_a, ruta_b)
        cat, why = clasificar(r, self.scipy_version)
        self.filas.append(dict(comparacion=etiqueta, categoria=cat, explicacion=why, hojas=r['n_hojas'], numericas=r['n_numericas'], con_diferencia=r['n_con_diferencia'],
                               dif_abs_max=r['max_abs'], dif_rel_max=r['max_rel'], peor=str(r['peor']) if r['peor'] else '', fuera_de_tolerancia=len(r['fuera_tol'])))
        print(f"[{cat}] {etiqueta}: hojas {r['n_hojas']} | dif abs max {r['max_abs']:.2e} | fuera de tolerancia {len(r['fuera_tol'])} | {why}")
        for k, x, y in r['fuera_tol'][:8]:
            print('    ', k, 'reproducido', x, '| referencia', y)
        return cat

    def tabla(self):
        return pd.DataFrame(self.filas)

    def veredicto(self):
        cats = [f['categoria'] for f in self.filas]
        peor = max(cats, key=self.ORDEN.index) if cats else 'NO_REPRODUCIBLE'
        return peor, {c: cats.count(c) for c in self.ORDEN if c in cats}
