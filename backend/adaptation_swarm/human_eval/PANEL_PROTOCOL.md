# Protocolo del panel de expertos para validar el gold (DECISION-CLOSURE §7.2)

Los mismos ≥ 10 expertos del SUS valoran las **20 celdas** (arquetipo × dificultad) de la tabla gold preregistrada `gold-v1`: «¿la modalidad dominante esperada
es razonable para ese perfil y esa dificultad?» (sí/no) y, opcionalmente, una valoración 1–5 y un comentario. Plantilla: `templates/gold_panel_template.csv`.
Resultado: % de acuerdo y κ de Fleiss por celda y global (`sus_cli status`). **La tabla NO se modifica en función de las respuestas** dentro de esta corrida:
un desacuerdo se reporta y, si se decide cambiar la tabla, será una `rule_version` nueva y una nueva corrida (nunca una edición).
Estado actual: **PENDIENTE DE RECOLECCIÓN HUMANA** (0 valoraciones).
