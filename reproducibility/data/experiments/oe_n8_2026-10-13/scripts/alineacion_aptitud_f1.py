"""Diagnóstico de alineación función de aptitud F vs F1 por caso (N5, réplicas guardadas). Solo lectura. Uso: ../../../.venv/Scripts/python.exe alineacion_aptitud_f1.py"""
import json,glob
from scipy.stats import spearmanr
from collections import defaultdict,Counter
F=[];Y=[];A=defaultdict(lambda:([],[]));perf=Counter();tot=Counter()
for f in sorted(glob.glob('../oe_n5_2026-10-06/f1_v3_provisional/replica_*.json')):
    for c in json.load(open(f))['cases']:
        F.append(c['F']);Y.append(c['f1']);A[c['archetype']][0].append(c['F']);A[c['archetype']][1].append(c['f1'])
        tot[c['archetype']]+=1; perf[c['archetype']]+= c['f1']==1.0
r=spearmanr(F,Y); res={'spearman_F_vs_F1_all':[float(r.statistic),float(r.pvalue),len(F)]}
for a,(x,y) in A.items():
    rr=spearmanr(x,y); res[a]={'spearman':float(rr.statistic),'p':float(rr.pvalue),'share_f1_eq_1':perf[a]/tot[a]}
json.dump(res,open('oe5_f1_repro/alineacion_aptitud_f1.json','w'),indent=1); print(json.dumps(res,indent=1))
