"""Exploratorio (no pre-registrado, no sellado) de OE4: relación entre los segundos de uso ajeno y el residuo de cada corrida respecto a su celda.
Uso: python -I -X utf8 exploratorio_interferencia_oe4.py RUNS_JSONL RESULTADOS_JSON SALIDA_JSON"""
import sys, json, math, numpy as np
from collections import defaultdict
from scipy.stats import spearmanr
runs=[json.loads(l) for l in open(sys.argv[1],encoding="utf8")]
det=json.load(open(sys.argv[2],encoding="utf8"))["interferencia_detalle"]
cel=defaultdict(list)
for r in runs: cel[(r["load"],r["n_particles"],r["workers"])].append(r)
rows=[]
for k,rs in cel.items():
    lp=np.mean([math.log(r["latency_p95_ms"]) for r in rs]); lt=np.mean([math.log(r["throughput_rps"]) for r in rs]); lc=np.mean([math.log(r["t_conv_ms_mean"]) for r in rs])
    for r in rs:
        d=det[r["run_id"]]; p=d["procesos"]
        rows.append(dict(rid=r["run_id"],maxs=d["max_s_un_proceso"],tot=sum(p.values()),claude=p.get("claude.exe",0),
          rp=math.log(r["latency_p95_ms"])-lp, rt=math.log(r["throughput_rps"])-lt, rc=math.log(r["t_conv_ms_mean"])-lc))
out={"n":len(rows),"nota":"exploratorio; asociación, no causalidad; no cambia la definición sellada de interferencia"}
for xn in("maxs","tot","claude"):
    for yn,lab in(("rp","log_P95"),("rt","log_thr"),("rc","log_Tconv")):
        rho,p=spearmanr([r[xn] for r in rows],[r[yn] for r in rows]); out[f"{xn}|{lab}"]={"rho":round(float(rho),3),"p":float(p)}
# terciles de max_s
m=np.array([r["maxs"] for r in rows]); q=np.quantile(m,[1/3,2/3])
for nm,sel in(("bajo",m<=q[0]),("medio",(m>q[0])&(m<=q[1])),("alto",m>q[1])):
    out["tercil_"+nm]={"n":int(sel.sum()),"max_s_rango":[int(m[sel].min()),int(m[sel].max())],
       "media_residuo_logP95":round(float(np.mean([r["rp"] for r,s in zip(rows,sel) if s])),4),
       "media_residuo_logthr":round(float(np.mean([r["rt"] for r,s in zip(rows,sel) if s])),4)}
json.dump(out,open(sys.argv[3],"w",encoding="utf8"),indent=1,ensure_ascii=False); print(json.dumps(out,indent=1,ensure_ascii=False))
