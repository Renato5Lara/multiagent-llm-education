# Resumen por objetivo (N6) — detalle en los `RESULTADO_OE*.md` de cada carpeta; aquí no se duplican datos

| OE | Estado | Resumen en una línea | Detalle |
|---|---|---|---|
| OE1 | Parcialmente demostrado | RF 5/6 (RF03 falla solo en la ablación `sequential`), confiabilidad 2/2, RNF01/02 sí (RNF01 agregado), RNF04 no (14,98 req/s en proceso), RNF03 no (F1 v2 0,6407), RNF05 sin medir | `oe_n1_2026-10-05/RESULTADO_OE1.md` |
| OE2 | Parcialmente demostrado | Swarm peor que `decision_table` en latencia (×5–22) y throughput (×0,06–0,16), 8/8 significativas tras Holm; tiempo hasta configuración final ×7 668; `T_conv` no comparable | `oe_n2_2026-10-05/RESULTADO_OE2.md` |
| OE3 | Demostrado | Efectos grandes del despacho y del mecanismo, moderados de la heurística, ≈ nulo de las réplicas; la referencia no es la mejor configuración | `oe_n3_2026-10-06/RESULTADO_OE3.md` |
| OE4 | Demostrado | Estable hasta 100 usuarios, meseta ≈ 15–16 req/s desde 5 usuarios, P95 > 2 s entre 10 y 25 usuarios, mayor degradación a 100 | `oe_n4_2026-10-06/RESULTADO_OE4.md` |
| OE5 | Parcialmente demostrado | F1 v3 provisional 0,8156 (< 0,85); SUS pendiente (0 evaluadores) | `oe_n5_2026-10-06/RESULTADO_OE5.md` |
