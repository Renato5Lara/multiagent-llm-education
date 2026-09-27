# Protocolo del panel por ARQUETIPO — gold-v2 (decisiones PX1–PX7 del asesor, 2026-09-26)

Fuente: `ADDENDUM-DECISIONES-ASESOR-RULE-VERSION-2026-09-26.md` (PX1–PX11) y su transcripción literal (con la reserva de procedencia: el original del asesor no está anexado). Sustituye, para gold-v2, a `PANEL_PROTOCOL.md`
(gold-v1, 20 celdas, «modalidad dominante», Fleiss κ), que se conserva solo como historial. Los mismos ≥ 10 evaluadores del SUS. Especificación ejecutable: `gold/rubric_v2.PANEL_PROTOCOL` (versión `panel-arq-ac1-maj-tie0-v2`;
su huella forma parte de la `rule_version` aprobada y NO se edita); cálculo: `metrics/gold_panel.py`.

**Material.** Para cada uno de los 4 arquetipos, el conjunto COMPLETO esperado (solo del arquetipo; audio solo en Balanced): Visual-Dominant → {diagram} · Logical-Syntactic → {code} · Explanatory-Conceptual → {text} ·
Balanced-Multimodal → {code, diagram, text, audio}. Plantilla: `templates/gold_panel_archetype_template.csv`.

**Tarea.** Aprobar / Rechazar la validez del paquete multimodal propuesto para ese arquetipo (`approves` = yes/no). n ≥ 10 evaluadores; el mismo n en los 4 arquetipos.

**Estadístico ÚNICO (PX1, PX5): Gwet AC1 multi-evaluador para respuestas binarias** (Gwet, 2008, *Br. J. Math. Stat. Psychol.* 61(1), 29-48). Fleiss κ queda descartado: no se calcula ni se consulta en la ruta oficial.
Se reporta siempre la **matriz absoluta de votos** (`archetype | approve | reject | total | approval_rate | majority_status`).

## Condiciones de validez (PX2, PX3, PX3-bis, PX6)

El panel es válido (`panel_valid`) solo si se cumplen **las cinco** a la vez:

1. **AC1 > 0.70** (estricto: AC1 = 0.70 NO pasa).
2. **Acuerdo crudo ≥ 0.85** (inclusivo).
3. **Mayoría aprobatoria en cada arquetipo**: aprobaciones > n/2 (n = 10: mínimo 6; 5–5 y 4–6 NO aprueban).
4. **Ningún rechazo mayoritario**: rechazos > n/2 en ningún arquetipo.
5. **Ningún empate exacto** (aprobaciones = rechazos) en ningún arquetipo. Un empate no es aprobación.

**Revisión (`rule_version_review`).** Es `True` si falla CUALQUIERA de las cinco (`= not panel_valid`): algún arquetipo sin mayoría aprobatoria, algún rechazo mayoritario o empate, AC1 ≤ 0.70 o acuerdo crudo < 0.85 —
**aunque los cuatro arquetipos tengan mayoría de aprobación**: un gold requiere aprobación del contenido y confiabilidad del juicio. Nunca es `null`. Si la regla se revisa, el gold nuevo vuelve al panel antes de repetir la
corrida. **La tabla no se modifica en función de las respuestas**: un cambio es una `rule_version` nueva. Las fronteras 0.70 y 0.85 se deciden en aritmética racional exacta (no en floats).

## Denominadores y acuerdo crudo (PX4, PX7)

- Toda proporción global se calcula sobre **4·n** juicios (nunca 40 fijo): el acuerdo crudo y la proporción global de aprobación (esta última solo descriptiva). La proporción de un arquetipo concreto usa n.
- **Acuerdo crudo** = juicios que coinciden con la categoría MAYORITARIA de su arquetipo / (4·n).
- **Empate (PX7):** en un empate exacto no existe categoría mayoritaria, así que los juicios de ese arquetipo **quedan fuera del numerador** del acuerdo crudo (no cuentan como coincidencias); **el denominador sigue siendo 4·n**.
  Con n = 10 y un empate 5–5 en un arquetipo, el acuerdo crudo máximo es 30/40 = 0.75 < 0.85. Un empate además activa la revisión por la condición 5.

## Evidencia y verificación

- **Evidencia obligatoria** (`sus_cli export-archetype --out-dir DIR_NUEVO`): resultado completo (JSON), matriz absoluta (CSV) y votos por evaluador (CSV).
- **Verificación de AC1 (PX8): PENDIENTE.** Hoy hay un contraste cruzado con un port independiente en Python de `irrCAC` (`tests/adaptation_swarm/fixtures/ac1_reference/`). La certificación con **R + irrCAC** es obligatoria
  antes del cierre del documento final: `verify_with_R_irrCAC.R` está preparado (no ejecutado) y el test de certificación permanece SKIPPED hasta que exista `r_irrCAC_results.json`.

Estado: **PENDIENTE DE RECOLECCIÓN HUMANA** (0 valoraciones). Registrar juicios no aprueba la regla ni autoriza la corrida oficial.
