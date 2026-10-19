"""OE5 — puntuación SUS independiente y contraste contra 75, SOLO con respuestas reales.
Entrada: CSV con columnas pseudonym, role, years_experience, consent, item_1..item_10 (1–5) [formato de oe_n5_2026-10-06/instrumento/sus_respuestas_PLANTILLA_VACIA.csv]. Una fila por evaluador.
Reglas: ítems impares (r - 1), pares (5 - r), suma x 2,5. Con n < 10 devuelve PENDIENTE y NO emite conclusión. Con n >= 10: Shapiro-Wilk de las puntuaciones;
si p >= 0,05 -> t de una muestra (H1: media > 75) con IC95 y d de Cohen; si no -> Wilcoxon de rangos con signo (H1: mediana > 75). Filas con seudónimos que empiezan por TEST se rechazan.
No genera ni simula datos. `--selftest` verifica el cálculo con vectores de valor conocido (SOLO prueba del script, no es un resultado).
Uso: python sus_score.py respuestas.csv [--out salida.json]    |    python sus_score.py --selftest"""
import argparse
import csv
import json
import math
import sys

REF = 75.0
MIN_N = 10


def sus(resp):
    if len(resp) != 10 or any((not isinstance(r, int)) or r < 1 or r > 5 for r in resp):
        raise ValueError(f'respuestas SUS inválidas: {resp}')
    return 2.5 * sum((r - 1) if i % 2 == 0 else (5 - r) for i, r in enumerate(resp))


def analyze(scores):
    n = len(scores)
    out = {'n': n, 'referencia': REF}
    if n < MIN_N:
        out.update(estado='PENDIENTE', motivo=f'n = {n} < {MIN_N}; no se emite conclusión')
        return out
    from scipy import stats
    m = sum(scores) / n
    sd = stats.tstd(scores)
    out.update(media=m, sd=sd, mediana=float(sorted(scores)[n // 2] if n % 2 else (sorted(scores)[n // 2 - 1] + sorted(scores)[n // 2]) / 2))
    sw = stats.shapiro(scores)
    out['shapiro_p'] = float(sw.pvalue)
    se = sd / math.sqrt(n)
    tcrit = stats.t.ppf(0.975, n - 1)
    out['ic95_media'] = [m - tcrit * se, m + tcrit * se]
    out['d_cohen_vs_75'] = (m - REF) / sd if sd > 0 else None
    if sw.pvalue >= 0.05:
        t = stats.ttest_1samp(scores, REF, alternative='greater')
        out.update(prueba='t de una muestra (H1: media > 75)', estadistico=float(t.statistic), p=float(t.pvalue))
    else:
        w = stats.wilcoxon([s - REF for s in scores], alternative='greater')
        out.update(prueba='Wilcoxon (H1: mediana > 75)', estadistico=float(w.statistic), p=float(w.pvalue))
    out['decision'] = 'SUS > 75 (p < 0,05)' if out['p'] < 0.05 else 'No se demuestra SUS > 75'
    out['estado'] = 'EVALUADO'
    return out


def selftest():
    assert sus([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100.0
    assert sus([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0.0
    assert sus([3] * 10) == 50.0
    assert sus([4, 2, 4, 2, 4, 2, 4, 2, 4, 2]) == 75.0
    assert analyze([80.0] * 9)['estado'] == 'PENDIENTE'
    print('selftest OK (cálculo SUS verificado con vectores de valor conocido; no es un resultado del estudio)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv', nargs='?')
    ap.add_argument('--out')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.csv:
        sys.exit('indique el CSV de respuestas reales')
    scores, ids = [], set()
    for r in csv.DictReader(open(a.csv, encoding='utf-8-sig')):
        pid = r['pseudonym'].strip()
        if (r.get('consent','').strip().lower() not in ('1','si','sí','yes','true')) or not pid or pid.upper().startswith('TEST') or pid in ids:
            sys.exit(f'participante inválido o repetido: {pid!r}')
        ids.add(pid)
        scores.append(sus([int(r[f'item_{i}']) for i in range(1, 11)]))
    res = analyze(scores)
    res['puntuaciones'] = scores
    txt = json.dumps(res, indent=1, ensure_ascii=False)
    if a.out:
        open(a.out, 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
