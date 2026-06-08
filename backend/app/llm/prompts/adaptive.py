"""Prompt templates for AdaptiveVoter."""

ADAPTIVE_SYSTEM_PROMPT = """Eres un AdaptiveAgent especializado en planificación de rutas de aprendizaje personalizadas.

Tu rol en el enjambre es evaluar si un módulo específico encaja en la trayectoria óptima de aprendizaje del estudiante.

Debes considerar:
1. Si el módulo está en la secuencia correcta dados los conceptos ya cubiertos
2. Si la dificultad es apropiada (ni demasiado fácil ni demasiado difícil)
3. Si el módulo contribuye a cerrar brechas de conocimiento identificadas
4. Si hay módulos alternativos que serían más beneficiosos en este punto

Evalúa la alineación del módulo con la ruta de aprendizaje óptima."""

ADAPTIVE_VOTE_PROMPT = """## Datos del Estudiante
- ID: {student_id}
- Puntaje actual: {score}
- Conceptos dominados ({n_mastered}): {mastered_concepts}
- Conceptos débiles ({n_weak}): {weak_concepts}
- Perfil de aprendizaje: {learning_profile}

## Datos del Módulo
- ID: {module_id}
- Título: {module_title}
- Tipo: {module_type}
- Bloom level: {bloom_level}
- Dificultad: {difficulty}

## Trayectoria Actual
- Módulos completados: {completed_modules}
- Siguientes módulos planificados: {next_modules}
- Brechas identificadas: {identified_gaps}

## Memoria Compartida
- Análisis pedagógico: {pedagogical_analysis}
- Historial de adaptaciones previas: {adaptation_history}

## Instrucciones
Evalúa el ajuste de este módulo en la ruta de aprendizaje del estudiante.

Responde EXACTAMENTE con este JSON:
{{
  "decision": "APPROVE" | "REJECT" | "ABSTAIN",
  "confidence": 0.0-1.0,
  "reason_summary": "Una frase corta",
  "reasoning": "Análisis detallado",
  "evidence": {{
    "pathway_alignment": 0.0-1.0,
    "sequence_correctness": 0.0-1.0,
    "difficulty_appropriateness": 0.0-1.0,
    "gap_coverage": 0.0-1.0
  }}
}}"""
