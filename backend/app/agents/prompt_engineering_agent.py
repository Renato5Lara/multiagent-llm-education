"""PromptEngineeringAgent — genera prompts especializados adaptados al perfil del aprendiz y nivel Bloom."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.pedagogical_orchestration import GeneratedPrompt

logger = logging.getLogger(__name__)

# Bloom taxonomy verbs per level (Spanish)
_BLOOM_VERBS: dict[int, str] = {
    1: "recordar",
    2: "comprender",
    3: "aplicar",
    4: "analizar",
    5: "evaluar",
    6: "crear",
}

# Bloom taxonomy action verbs for prompt instructions
_BLOOM_ACTION_VERBS: dict[int, list[str]] = {
    1: ["identificar", "listar", "definir", "nombrar", "reconocer"],
    2: ["explicar", "describir", "resumir", "interpretar", "clasificar"],
    3: ["aplicar", "demostrar", "resolver", "usar", "ejecutar"],
    4: ["analizar", "comparar", "diferenciar", "examinar", "descomponer"],
    5: ["evaluar", "justificar", "criticar", "valorar", "argumentar"],
    6: ["diseñar", "crear", "construir", "sintetizar", "formular"],
}

# Complexity and vocabulary notes per difficulty level
_DIFFICULTY_VOCAB: dict[str, dict[str, Any]] = {
    "beginner": {
        "vocabulary": "vocabulario básico y cotidiano, evitar tecnicismos sin definir",
        "tone": "cálido, paciente, paso a paso",
        "analogy_emphasis": "alta — conectar con experiencias del mundo real",
        "explanation_style": "expandida, con ejemplos múltiples antes del concepto abstracto",
        "target_length_multiplier": 1.4,
        "accessibility_notes": [
            "No asumir conocimiento previo del tema",
            "Definir cada término técnico la primera vez que aparece",
            "Incluir comparación con algo cotidiano",
            "Estructurar en pasos numerados y pequeños",
        ],
    },
    "intermediate": {
        "vocabulary": "mezcla de términos técnicos y coloquiales, con aclaraciones contextuales",
        "tone": "académico accesible, dialógico",
        "analogy_emphasis": "moderada — para anclar conceptos complejos",
        "explanation_style": "balanceada, con contexto y ejemplos aplicados",
        "target_length_multiplier": 1.0,
        "accessibility_notes": [
            "Puede referenciarse terminología conocida sin definición extensa",
            "Conectar con conocimientos previos del área",
        ],
    },
    "advanced": {
        "vocabulary": "terminología técnica precisa, densidad conceptual alta",
        "tone": "conciso, técnico, profesional",
        "analogy_emphasis": "baja — el aprendiz construye sus propias conexiones",
        "explanation_style": "densa y directa, con referencias a literatura o práctica profesional",
        "target_length_multiplier": 0.7,
        "accessibility_notes": [
            "Aprendiz autónomo — minimizar scaffolding",
            "Enfatizar matices, excepciones y casos límite",
        ],
    },
}


class PromptEngineeringAgent(BaseAgent):
    """Genera prompts especializados para cada modalidad, adaptados al perfil del aprendiz y Bloom.

    Responsabilidades:
    - Generar prompts cinematográficos (video/storyboard) con instrucciones pedagógicas
    - Generar prompts visuales (imágenes/diagramas) con calibración cognitiva
    - Generar prompts narrativos (texto) adaptados a dificultad y profundidad
    - Generar prompts de audio con tono y ritmo apropiados al perfil
    - Generar prompts interactivos con dificultad calibrada por Bloom y perfil
    - Mantener consistencia estilística y trazabilidad de orquestación

    Lee de state:
    - pedagogical_structure.sections[].bloom_level → calibración cognitiva por sección
    - adaptation_plan.difficulty_level → vocabulario y profundidad
    - adaptation_plan.explanation_depth → expansión del prompt
    - adaptation_plan.bloom_range → rango cognitivo del aprendiz
    - adaptation_plan.modality_preferences → señales de preferencia inyectadas
    - research_result → ejemplos, analogías, aplicaciones reales
    - multimodal_plan.prompt_sections → qué tipo de prompt genera cada sección

    Escribe en shared memory:
    - prompts:generated (con metadata pedagógica por prompt)
    - prompts:narrative_thread
    - prompts:adaptation_trace
    """

    @property
    def agent_type(self) -> str:
        return "prompt_engineering"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        pedagogical = state.get("pedagogical_structure", {})
        sections = pedagogical.get("sections", []) if isinstance(pedagogical, dict) else []
        multimodal_plan = state.get("multimodal_plan", {})
        prompt_sections = multimodal_plan.get("prompt_sections", {}) if isinstance(multimodal_plan, dict) else {}

        # ── Read adaptation plan (the core of learner-context injection) ──
        adaptation = state.get("adaptation_plan", {}) if isinstance(state.get("adaptation_plan"), dict) else {}
        difficulty_level = adaptation.get("difficulty_level", "intermediate")
        explanation_depth = adaptation.get("explanation_depth", "standard")
        bloom_range = adaptation.get("bloom_range", [1, 4])
        modality_prefs = adaptation.get("modality_preferences", [])
        reinforcement = adaptation.get("reinforcement_frequency", "normal")

        # ── Read research context ──────────────────────────────────────────
        research = state.get("research_result", {})
        examples = research.get("examples", []) if isinstance(research, dict) else []
        analogies = research.get("analogies", []) if isinstance(research, dict) else []
        concepts = research.get("concepts", []) if isinstance(research, dict) else []
        misconceptions = research.get("misconceptions", []) if isinstance(research, dict) else []
        real_applications = research.get("real_applications", []) if isinstance(research, dict) else []
        sources = research.get("sources", []) if isinstance(research, dict) else []
        learning_objectives = state.get("learning_objectives", [])

        topic = state.get("topic", "")

        orchestration_trace: list[str] = [
            f"topic='{topic}'",
            f"difficulty={difficulty_level}",
            f"explanation_depth={explanation_depth}",
            f"bloom_range={bloom_range}",
            f"modality_preferences={modality_prefs or 'default'}",
            f"reinforcement={reinforcement}",
            f"research_examples={len(examples)}",
            f"research_analogies={len(analogies)}",
            f"misconceptions_available={len(misconceptions)}",
        ]

        learner_context = self._build_learner_context(
            difficulty_level=difficulty_level,
            explanation_depth=explanation_depth,
            bloom_range=bloom_range,
            modality_prefs=modality_prefs,
            reinforcement=reinforcement,
        )

        prompts = []
        section_bloom_map: dict[str, int] = {}

        for section in sections:
            section_type = section.get("section_type", "unknown")
            section_title = section.get("title", "")
            section_desc = section.get("description", "")
            bloom_level = int(section.get("bloom_level", 2))
            section_bloom_map[section_type] = bloom_level

            prompt_type = prompt_sections.get(section_type)
            if not prompt_type:
                continue

            prompt = self._generate_prompt(
                prompt_type=prompt_type,
                section_type=section_type,
                title=section_title,
                description=section_desc,
                topic=topic,
                bloom_level=bloom_level,
                difficulty_level=difficulty_level,
                explanation_depth=explanation_depth,
                modality_prefs=modality_prefs,
                learning_objectives=learning_objectives,
                examples=examples,
                analogies=analogies,
                concepts=concepts,
                misconceptions=misconceptions,
                real_applications=real_applications,
                sources=sources,
                learner_context=learner_context,
                reinforcement=reinforcement,
            )
            prompts.append(prompt)
            orchestration_trace.append(
                f"section={section_type} bloom={bloom_level} → {prompt_type}_prompt generated"
            )

        narrative_thread = self._build_narrative_thread(
            topic=topic,
            sections=sections,
            difficulty_level=difficulty_level,
            bloom_range=bloom_range,
        )
        visual_continuity = self._build_visual_continuity(
            topic=topic,
            prompts=prompts,
            difficulty_level=difficulty_level,
        )
        audio_atmosphere = self._suggest_audio_atmosphere(
            topic=topic,
            sections=sections,
            difficulty_level=difficulty_level,
        )

        adaptation_metadata = {
            "difficulty_level": difficulty_level,
            "explanation_depth": explanation_depth,
            "bloom_range": bloom_range,
            "modality_preferences": modality_prefs,
            "reinforcement_frequency": reinforcement,
            "section_bloom_map": section_bloom_map,
            "prompts_generated": len(prompts),
            "learner_context_injected": True,
            "research_context_injected": len(examples) + len(analogies) > 0,
        }

        result = {
            "prompts": [p.model_dump() for p in prompts],
            "narrative_thread": narrative_thread,
            "visual_continuity": visual_continuity,
            "audio_atmosphere": audio_atmosphere,
            "prompt_count": len(prompts),
            "orchestration_trace": orchestration_trace,
            "adaptation_metadata": adaptation_metadata,
        }

        await self.publish_observation(
            f"{self.context_key}:prompts:generated",
            result,
            memory_type="inference",
            confidence=0.85,
        )

        return result

    # ── Learner context builder ───────────────────────────────────────────

    def _build_learner_context(
        self,
        difficulty_level: str,
        explanation_depth: str,
        bloom_range: list[int],
        modality_prefs: list[str],
        reinforcement: str,
    ) -> dict[str, Any]:
        vocab_config = _DIFFICULTY_VOCAB.get(difficulty_level, _DIFFICULTY_VOCAB["intermediate"])
        return {
            "difficulty_level": difficulty_level,
            "explanation_depth": explanation_depth,
            "bloom_range": bloom_range,
            "modality_preferences": modality_prefs or ["visual", "reading"],
            "reinforcement_frequency": reinforcement,
            "vocabulary_guidance": vocab_config["vocabulary"],
            "tone_guidance": vocab_config["tone"],
            "accessibility_notes": vocab_config["accessibility_notes"],
        }

    # ── Core prompt dispatcher ────────────────────────────────────────────

    def _generate_prompt(
        self,
        prompt_type: str,
        section_type: str,
        title: str,
        description: str,
        topic: str,
        bloom_level: int,
        difficulty_level: str,
        explanation_depth: str,
        modality_prefs: list[str],
        learning_objectives: list[str],
        examples: list[str],
        analogies: list[str],
        learner_context: dict[str, Any],
        reinforcement: str,
        concepts: list[str] | None = None,
        misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None,
        sources: list[dict] | None = None,
    ) -> GeneratedPrompt:
        bloom_verb = _BLOOM_VERBS.get(bloom_level, "comprender")
        action_verbs = _BLOOM_ACTION_VERBS.get(bloom_level, ["comprender", "explicar"])
        vocab_config = _DIFFICULTY_VOCAB.get(difficulty_level, _DIFFICULTY_VOCAB["intermediate"])

        generators = {
            "cinematic": self._generate_cinematic_prompt,
            "visual": self._generate_visual_prompt,
            "narrative": self._generate_narrative_prompt,
            "audio": self._generate_audio_prompt,
            "interactive": self._generate_interactive_prompt,
        }

        generator = generators.get(prompt_type, self._generate_narrative_prompt)
        content, params = generator(
            title=title,
            desc=description,
            topic=topic,
            bloom_level=bloom_level,
            difficulty_level=difficulty_level,
            explanation_depth=explanation_depth,
            vocab_config=vocab_config,
            action_verbs=action_verbs,
            examples=examples,
            analogies=analogies,
            concepts=concepts,
            misconceptions=misconceptions,
            real_applications=real_applications,
            sources=sources,
            reinforcement=reinforcement,
        )

        model_map = {
            "cinematic": "Sora / Runway Gen-3",
            "visual": "DALL-E 3 / Midjourney",
            "narrative": "GPT-4o / Claude",
            "audio": "ElevenLabs / TTS-1",
            "interactive": "Web / HTML5",
        }

        # Modality rationale: why THIS modality for THIS learner at THIS section
        modality_rationale = self._build_modality_rationale(
            prompt_type=prompt_type,
            section_type=section_type,
            bloom_level=bloom_level,
            difficulty_level=difficulty_level,
            modality_prefs=modality_prefs,
        )

        pedagogical_metadata = {
            "bloom_level": bloom_level,
            "bloom_verb": bloom_verb,
            "bloom_action_verbs": action_verbs[:3],
            "section_type": section_type,
            "difficulty_calibration": difficulty_level,
            "explanation_depth": explanation_depth,
            "learning_objectives_count": len(learning_objectives),
            "learning_objectives_sample": learning_objectives[:2],
            "vocabulary_guidance": vocab_config["vocabulary"],
            "analogy_emphasis": vocab_config["analogy_emphasis"],
            "target_length_multiplier": vocab_config["target_length_multiplier"],
            "accessibility_notes": vocab_config["accessibility_notes"],
            "reinforcement_frequency": reinforcement,
        }

        orchestration_trace = [
            f"PromptEngineeringAgent → {prompt_type}_prompt",
            f"section={section_type} | bloom={bloom_level}({bloom_verb})",
            f"difficulty={difficulty_level} | depth={explanation_depth}",
            f"vocab={vocab_config['vocabulary'][:40]}...",
            f"model={model_map.get(prompt_type, 'GPT-4o')}",
            f"research_grounded: examples={len(examples)}, analogies={len(analogies)}",
        ]

        return GeneratedPrompt(
            prompt_type=prompt_type,
            target_section=section_type,
            content=content,
            parameters=params,
            model_recommendation=model_map.get(prompt_type, "GPT-4o"),
            bloom_level=bloom_level,
            bloom_verb=bloom_verb,
            difficulty_calibration=difficulty_level,
            modality_rationale=modality_rationale,
            learner_context=learner_context,
            pedagogical_metadata=pedagogical_metadata,
            orchestration_trace=orchestration_trace,
        )

    def _build_modality_rationale(
        self,
        prompt_type: str,
        section_type: str,
        bloom_level: int,
        difficulty_level: str,
        modality_prefs: list[str],
    ) -> str:
        bloom_verb = _BLOOM_VERBS.get(bloom_level, "comprender")
        pref_str = f"(preferencia del aprendiz: {', '.join(modality_prefs)})" if modality_prefs else "(sin preferencia explícita de modalidad)"
        rationale_map = {
            "cinematic": (
                f"Prompt cinematográfico para '{section_type}' (Bloom {bloom_level}: {bloom_verb}). "
                f"La narrativa visual inmersiva maximiza la transferencia contextual "
                f"para un aprendiz de nivel {difficulty_level}. {pref_str}. "
                f"Se genera storyboard pedagógico para sistema generativo de video."
            ),
            "visual": (
                f"Prompt visual para '{section_type}' (Bloom {bloom_level}: {bloom_verb}). "
                f"La representación diagramática estructura relaciones conceptuales "
                f"apropiadas para el nivel cognitivo del aprendiz ({difficulty_level}). "
                f"{pref_str}. Se genera prompt para sistema generativo de imagen."
            ),
            "narrative": (
                f"Prompt narrativo para '{section_type}' (Bloom {bloom_level}: {bloom_verb}). "
                f"La narración textual estructurada permite calibrar vocabulario y profundidad "
                f"exactamente al nivel del aprendiz ({difficulty_level}). {pref_str}."
            ),
            "audio": (
                f"Prompt de audio para '{section_type}' (Bloom {bloom_level}: {bloom_verb}). "
                f"La narración oral con ritmo y tono calibrados facilita la comprensión "
                f"auditiva para aprendices de nivel {difficulty_level}. {pref_str}."
            ),
            "interactive": (
                f"Prompt interactivo para '{section_type}' (Bloom {bloom_level}: {bloom_verb}). "
                f"La actividad interactiva alineada con Bloom {bloom_level} fuerza la "
                f"activación cognitiva adecuada para aprendiz {difficulty_level}. {pref_str}."
            ),
        }
        return rationale_map.get(prompt_type, f"Modalidad {prompt_type} seleccionada para {section_type}.")

    # ── Cinematic prompt generator ────────────────────────────────────────

    def _generate_cinematic_prompt(
        self,
        title: str,
        desc: str,
        topic: str,
        bloom_level: int,
        difficulty_level: str,
        explanation_depth: str,
        vocab_config: dict,
        action_verbs: list[str],
        examples: list[str],
        analogies: list[str],
        concepts: list[str] | None = None,
        misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None,
        sources: list[dict] | None = None,
        reinforcement: str = "normal",
    ) -> tuple[str, dict]:
        bloom_verb = _BLOOM_VERBS.get(bloom_level, "comprender")
        primary_verb = action_verbs[0] if action_verbs else "demostrar"

        # Bloom-calibrated scene durations
        if bloom_level <= 2:
            durations = {"apertura": 20, "explicacion": 35, "ejemplo": 20, "cierre": 10}
            scene_depth = "con énfasis en claridad y repetición de conceptos clave"
        elif bloom_level <= 4:
            durations = {"apertura": 15, "explicacion": 30, "ejemplo": 25, "cierre": 15}
            scene_depth = "con demostración paso a paso y conexión a aplicaciones reales"
        else:
            durations = {"apertura": 10, "explicacion": 20, "ejemplo": 30, "cierre": 20}
            scene_depth = "con análisis crítico, casos límite y síntesis conceptual"

        storyboard = (
            f"CINEMATIC PROMPT — PEDAGOGICAL STORYBOARD\n"
            f"{'='*50}\n\n"
            f"TEMA: {topic}\n"
            f"SECCIÓN: {title}\n"
            f"DESCRIPCIÓN: {desc}\n\n"
            f"OBJETIVO COGNITIVO (Bloom {bloom_level} — {bloom_verb}):\n"
            f"  El aprendiz debe poder {primary_verb} {topic} al finalizar.\n\n"
            f"PERFIL DEL APRENDIZ:\n"
            f"  - Nivel: {difficulty_level}\n"
            f"  - Vocabulario: {vocab_config['vocabulary']}\n"
            f"  - Tono narrativo: {vocab_config['tone']}\n\n"
            f"ESTRUCTURA DE ESCENAS {scene_depth}:\n\n"
            f"ESCENA 1 — APERTURA CONTEXTUAL ({durations['apertura']} seg)\n"
            f"  - Plano general del entorno de aplicación de {topic}\n"
            f"  - Voz en off: presentación del objetivo cognitivo al aprendiz\n"
            f"  - Texto en pantalla: '{action_verbs[0].upper()} {topic}'\n"
            f"  - Ritmo: {'lento y pausado' if difficulty_level == 'beginner' else 'moderado' if difficulty_level == 'intermediate' else 'ágil y técnico'}\n\n"
            f"ESCENA 2 — EXPOSICIÓN DEL CONCEPTO ({durations['explicacion']} seg)\n"
            f"  - Animación de conceptos clave con gráficos en movimiento\n"
            f"  - Texto emergente con definiciones {'expandidas paso a paso' if difficulty_level == 'beginner' else 'con contexto técnico'}\n"
            f"  - Énfasis en: {', '.join(action_verbs[:2])}\n\n"
            f"ESCENA 3 — {'EJEMPLO BÁSICO' if bloom_level <= 2 else 'DEMOSTRACIÓN APLICADA' if bloom_level <= 4 else 'ANÁLISIS CRÍTICO'} ({durations['ejemplo']} seg)\n"
            f"  - {'Demostración visual simple paso a paso' if bloom_level <= 2 else 'Split screen: teoría vs. aplicación real' if bloom_level <= 4 else 'Análisis comparativo de casos y trade-offs'}\n"
            f"  - Conexión explícita con objetivos de aprendizaje\n\n"
            f"ESCENA 4 — CIERRE Y REFLEXIÓN ({durations['cierre']} seg)\n"
            f"  - Resumen visual de puntos clave\n"
            f"  - Pregunta reflexiva: '¿Cómo podrías {action_verbs[-1]} {topic} en tu contexto?'\n"
            f"  - Call to action: {'ejercicio guiado' if difficulty_level == 'beginner' else 'práctica autónoma' if difficulty_level == 'advanced' else 'actividad de aplicación'}\n\n"
            f"ESTILO VISUAL (calibrado para {difficulty_level}):\n"
            f"  - Paleta: {'colores primarios claros, alto contraste' if difficulty_level == 'beginner' else 'paleta académica profesional' if difficulty_level == 'intermediate' else 'paleta técnica minimalista'}\n"
            f"  - Tipografía: sans-serif, {'tamaño grande' if difficulty_level == 'beginner' else 'tamaño estándar'}\n"
            f"  - Ritmo: {'pausado, con tiempo para asimilar' if difficulty_level == 'beginner' else 'dinámico y técnico'}\n"
            f"  - Transiciones: suaves, fundidos\n"
            f"  - Subtítulos: requeridos ({'con glosario integrado' if difficulty_level == 'beginner' else 'terminología estándar'})\n"
        )

        if analogies and vocab_config["analogy_emphasis"] != "baja":
            storyboard += f"\nANALOGÍA VISUAL:\n  - {analogies[0]}\n"

        if misconceptions:
            storyboard += f"\nERROR CONCEPTUAL A REPRESENTAR (CORRECCIÓN EXPLÍCITA):\n  - {misconceptions[0]}\n"

        if real_applications:
            storyboard += f"\nAPLICACIÓN REAL CONTEXTUALIZADA:\n  - {real_applications[0]}\n"

        if concepts:
            storyboard += f"\nCONCEPTOS CLAVE A VISUALIZAR:\n"
            for c in concepts[:3]:
                storyboard += f"  - {c}\n"

        if sources:
            storyboard += f"\nRESPALDO ACADÉMICO:\n"
            for s in sources[:2]:
                storyboard += f"  - {s.get('title', '')} ({s.get('domain', '')})\n"

        total_duration = sum(durations.values())
        params = {
            "aspect_ratio": "16:9",
            "style": "educational_documentary",
            "duration_seconds": total_duration,
            "difficulty_level": difficulty_level,
            "bloom_level": bloom_level,
            "bloom_verb": bloom_verb,
            "narration_required": True,
            "subtitles_required": True,
            "pace": "slow" if difficulty_level == "beginner" else "moderate" if difficulty_level == "intermediate" else "fast",
            "glossary_required": difficulty_level == "beginner",
        }

        return storyboard, params

    # ── Visual prompt generator ───────────────────────────────────────────

    def _generate_visual_prompt(
        self,
        title: str,
        desc: str,
        topic: str,
        bloom_level: int,
        difficulty_level: str,
        explanation_depth: str,
        vocab_config: dict,
        action_verbs: list[str],
        examples: list[str],
        analogies: list[str],
        concepts: list[str] | None = None,
        misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None,
        sources: list[dict] | None = None,
        reinforcement: str = "normal",
    ) -> tuple[str, dict]:
        bloom_verb = _BLOOM_VERBS.get(bloom_level, "comprender")
        primary_verb = action_verbs[0] if action_verbs else "identificar"

        # Diagram complexity scales with Bloom level
        diagram_type_map = {
            1: "diagrama de definición simple (término → significado → ejemplo visual)",
            2: "mapa conceptual de relaciones (nodo central con ramas explicativas)",
            3: "diagrama de proceso o flujo (pasos de aplicación numerados)",
            4: "diagrama comparativo o de descomposición (análisis de componentes)",
            5: "gráfico de evaluación con criterios (rúbrica visual o escala de valoración)",
            6: "diagrama de síntesis o blueprint (diseño de nuevo artefacto o solución)",
        }
        diagram_type = diagram_type_map.get(bloom_level, "diagrama educativo")

        visual_complexity = {
            "beginner": "simple, con abundantes etiquetas explicativas y colores codificados",
            "intermediate": "equilibrado, con relaciones entre conceptos y anotaciones clave",
            "advanced": "denso en información, con detalles técnicos y referencias precisas",
        }

        prompt = (
            f"VISUAL PROMPT — PEDAGOGICAL IMAGE GENERATION\n"
            f"{'='*50}\n\n"
            f"TEMA: {topic}\n"
            f"SECCIÓN: {title}\n"
            f"DESCRIPCIÓN: {desc}\n\n"
            f"OBJETIVO COGNITIVO (Bloom {bloom_level} — {bloom_verb}):\n"
            f"  El aprendiz debe poder {primary_verb} {topic} al observar esta imagen.\n\n"
            f"TIPO DE DIAGRAMA: {diagram_type}\n\n"
            f"PERFIL DEL APRENDIZ:\n"
            f"  - Nivel: {difficulty_level}\n"
            f"  - Complejidad visual: {visual_complexity.get(difficulty_level, 'equilibrado')}\n\n"
            f"INSTRUCCIONES PARA GENERACIÓN:\n"
            f"  1. Concepto central de {topic} en el centro o encabezado\n"
            f"  2. {'Definiciones con flechas simples' if bloom_level <= 2 else 'Relaciones entre sub-conceptos con etiquetas' if bloom_level <= 4 else 'Análisis estructural con nodos de evaluación'}\n"
            f"  3. Iconos representativos del contexto de programación\n"
            f"  4. Etiquetas con vocabulario de nivel {difficulty_level}\n"
            f"  5. {'Glosario lateral con términos clave definidos' if difficulty_level == 'beginner' else 'Notación técnica estándar'}\n\n"
            f"ESTILO VISUAL:\n"
            f"  - Estilo: {diagram_type.split('(')[0].strip()}, clean, educativo\n"
            f"  - Colores: {'primarios brillantes, alto contraste para legibilidad' if difficulty_level == 'beginner' else 'azul académico, blanco, tonos suaves' if difficulty_level == 'intermediate' else 'gris técnico, azul oscuro, verde para éxito'}\n"
            f"  - Composición: organizada, {'jerárquica y simple' if difficulty_level == 'beginner' else 'jerárquica y relacional'}\n"
            f"  - Tipografía: clara, sans-serif, {'tamaño grande' if difficulty_level == 'beginner' else 'tamaño estándar'}\n"
        )

        if analogies and vocab_config["analogy_emphasis"] != "baja":
            prompt += f"\nANALOGÍA VISUAL A REPRESENTAR:\n  - {analogies[0]}\n"

        if misconceptions:
            prompt += (
                f"\nERROR CONCEPTUAL A ILUSTRAR (REPRESENTACIÓN ANTES/DESPUÉS):\n"
                f"  - Concepto erróneo: {misconceptions[0]}\n"
                f"  - Mostrar corrección visual explícita\n"
            )

        if concepts:
            prompt += f"\nCONCEPTOS A DIAGRAMAR ({len(concepts[:5])} en total):\n"
            for c in concepts[:5]:
                prompt += f"  - {c}\n"

        if real_applications:
            prompt += f"\nCONTEXTO DE APLICACIÓN REAL:\n  - {real_applications[0]}\n"

        if sources:
            prompt += f"\nFUENTES ACADÉMICAS DE REFERENCIA:\n"
            for s in sources[:2]:
                prompt += f"  - {s.get('title', '')}\n"

        params = {
            "format": "16:9",
            "style": diagram_type.split("(")[0].strip().replace(" ", "_"),
            "difficulty_level": difficulty_level,
            "bloom_level": bloom_level,
            "bloom_verb": bloom_verb,
            "color_palette": "high_contrast_educational" if difficulty_level == "beginner" else "academic_blue" if difficulty_level == "intermediate" else "technical_minimal",
            "detail_level": "low" if difficulty_level == "beginner" else "high" if difficulty_level == "advanced" else "medium",
            "glossary_overlay": difficulty_level == "beginner",
            "accessibility_alt_text_required": True,
        }

        return prompt, params

    # ── Narrative prompt generator ────────────────────────────────────────

    def _generate_narrative_prompt(
        self,
        title: str,
        desc: str,
        topic: str,
        bloom_level: int,
        difficulty_level: str,
        explanation_depth: str,
        vocab_config: dict,
        action_verbs: list[str],
        examples: list[str],
        analogies: list[str],
        concepts: list[str] | None = None,
        misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None,
        sources: list[dict] | None = None,
        reinforcement: str = "normal",
    ) -> tuple[str, dict]:
        bloom_verb = _BLOOM_VERBS.get(bloom_level, "comprender")
        primary_verb = action_verbs[0] if action_verbs else "comprender"

        base_word_count = 500
        word_count = int(base_word_count * vocab_config["target_length_multiplier"])

        # Narrative structure adapts to Bloom level
        if bloom_level <= 2:
            structure_instructions = (
                f"  1. Gancho inicial: conectar con experiencia cotidiana del estudiante\n"
                f"  2. Definición clara y directa del concepto con lenguaje accesible\n"
                f"  3. Analogía concreta: '{analogies[0] if analogies else 'comparación con objeto del mundo real'}'\n"
                f"  4. Ejemplo básico paso a paso (numerado, sin ambigüedad)\n"
                f"  5. Verificación: pregunta de comprensión directa\n"
            )
        elif bloom_level <= 4:
            structure_instructions = (
                f"  1. Gancho: problema o escenario que requiere aplicar {topic}\n"
                f"  2. Exposición del concepto con conexión a conocimientos previos\n"
                f"  3. Ejemplo aplicado con proceso completo documentado\n"
                f"  4. Caso real: '{real_applications[0] if real_applications else 'contexto profesional de programación'}'\n"
                f"  5. Transición: ¿cómo generalizar este patrón a otros contextos?\n"
            )
        else:
            structure_instructions = (
                f"  1. Planteamiento de tensión o trade-off en {topic}\n"
                f"  2. Análisis de enfoques alternativos con criterios de evaluación\n"
                f"  3. Caso crítico que desafía la solución obvia\n"
                f"  4. Síntesis: propuesta de solución con justificación argumentada\n"
                f"  5. Reflexión metacognitiva: ¿qué cambiaste en tu forma de pensar?\n"
            )

        prompt = (
            f"NARRATIVE PROMPT — PEDAGOGICAL TEXT GENERATION\n"
            f"{'='*50}\n\n"
            f"TEMA: {topic}\n"
            f"SECCIÓN: {title}\n"
            f"DESCRIPCIÓN: {desc}\n\n"
            f"OBJETIVO COGNITIVO (Bloom {bloom_level} — {bloom_verb}):\n"
            f"  Guiar al lector a {primary_verb} {topic}.\n\n"
            f"PERFIL DEL APRENDIZ:\n"
            f"  - Nivel: {difficulty_level}\n"
            f"  - Tono: {vocab_config['tone']}\n"
            f"  - Vocabulario: {vocab_config['vocabulary']}\n"
            f"  - Analogías: {vocab_config['analogy_emphasis']}\n\n"
            f"INSTRUCCIONES DE GENERACIÓN:\n"
            f"  - Extensión objetivo: {word_count} palabras\n"
            f"  - Audiencia: estudiante de Fundamentos de Programación (nivel {difficulty_level})\n"
            f"  - Verbos cognitivos Bloom {bloom_level}: {', '.join(action_verbs[:3])}\n\n"
            f"ESTRUCTURA NARRATIVA:\n"
            f"{structure_instructions}\n"
            f"RESTRICCIONES LINGÜÍSTICAS:\n"
        )

        for note in vocab_config["accessibility_notes"]:
            prompt += f"  - {note}\n"

        prompt += f"\nREQUERIMIENTOS PEDAGÓGICOS:\n"

        if reinforcement == "high":
            prompt += (
                f"  - Incluir resumen de puntos clave al final (refuerzo alto)\n"
                f"  - Repetir términos clave 2-3 veces con contexto variado\n"
                f"  - Ejercicio de autoevaluación integrado\n"
            )
        elif reinforcement == "normal":
            prompt += (
                f"  - Terminar con pregunta que active pensamiento crítico\n"
                f"  - Incluir pausas reflexivas entre secciones\n"
            )
        else:
            prompt += (
                f"  - Orientar hacia investigación autónoma adicional\n"
                f"  - Plantear preguntas abiertas de nivel avanzado\n"
            )

        if analogies and vocab_config["analogy_emphasis"] != "baja":
            prompt += f"\nANALOGÍA A INTEGRAR NATURALMENTE:\n  - {analogies[0]}\n"

        if real_applications:
            prompt += f"\nAPLICACIÓN REAL A CONTEXTUALIZAR:\n  - {real_applications[0]}\n"

        if misconceptions:
            prompt += f"\nCONCEPCIÓN ERRÓNEA A ACLARAR:\n  - {misconceptions[0]}\n"

        if concepts:
            prompt += f"\nCONCEPTOS A ABORDAR (en orden pedagógico):\n"
            for c in concepts[:3]:
                prompt += f"  - {c}\n"

        params = {
            "target_word_count": word_count,
            "tone": vocab_config["tone"],
            "complexity": difficulty_level,
            "bloom_level": bloom_level,
            "bloom_verb": bloom_verb,
            "requires_critical_thinking": bloom_level >= 4,
            "requires_analogy": vocab_config["analogy_emphasis"] != "baja",
            "reinforcement_style": reinforcement,
            "language": "es",
        }

        return prompt, params

    # ── Audio prompt generator ────────────────────────────────────────────

    def _generate_audio_prompt(
        self,
        title: str,
        desc: str,
        topic: str,
        bloom_level: int,
        difficulty_level: str,
        explanation_depth: str,
        vocab_config: dict,
        action_verbs: list[str],
        examples: list[str],
        analogies: list[str],
        concepts: list[str] | None = None,
        misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None,
        sources: list[dict] | None = None,
        reinforcement: str = "normal",
    ) -> tuple[str, dict]:
        bloom_verb = _BLOOM_VERBS.get(bloom_level, "comprender")

        narration_seconds = int(75 * vocab_config["target_length_multiplier"])
        pace = "lento (0.85x) con pausas largas" if difficulty_level == "beginner" else "moderado (1.0x)" if difficulty_level == "intermediate" else "ágil (1.1x) con densidad informativa alta"
        voice_style = {
            "beginner": "cálida, paciente, entusiasta — como un tutor comprensivo",
            "intermediate": "profesional, clara, dialógica — como un docente universitario",
            "advanced": "técnica, concisa, precisa — como un conferenciante experto",
        }.get(difficulty_level, "profesional y clara")

        prompt = (
            f"AUDIO PROMPT — PEDAGOGICAL NARRATION\n"
            f"{'='*50}\n\n"
            f"TEMA: {topic}\n"
            f"SECCIÓN: {title}\n"
            f"DESCRIPCIÓN: {desc}\n\n"
            f"OBJETIVO COGNITIVO (Bloom {bloom_level} — {bloom_verb}):\n"
            f"  Facilitar que el oyente pueda {action_verbs[0]} {topic}.\n\n"
            f"PERFIL DEL APRENDIZ:\n"
            f"  - Nivel: {difficulty_level}\n"
            f"  - Estilo de voz: {voice_style}\n"
            f"  - Ritmo: {pace}\n\n"
            f"ESTRUCTURA DE AUDIO:\n"
            f"  - Introducción musical suave (5 seg)\n"
            f"  - Presentación del objetivo: 'En esta sección vas a {action_verbs[0]} {topic}' (10 seg)\n"
            f"  - Narración principal ({narration_seconds} seg):\n"
            f"    {'• Definir cada término antes de usarlo en contexto' if difficulty_level == 'beginner' else '• Desarrollar el concepto con densidad técnica apropiada'}\n"
            f"    {'• Repetir conceptos clave al menos 2 veces con variación' if reinforcement == 'high' else '• Una exposición clara y progresiva'}\n"
            f"    • Énfasis prosódico en: {', '.join((concepts or [topic])[:3])}\n"
            f"  - Pausa reflexiva (3 seg) — silencio intencional\n"
            f"  - Pregunta de cierre: '¿Podrías {action_verbs[-1]} {topic} ahora?' (5 seg)\n"
            f"  - Cierre musical (5 seg)\n\n"
            f"INSTRUCCIONES DE PRODUCCIÓN:\n"
            f"  - Eliminar tecnicismos {'— o definirlos inmediatamente' if difficulty_level == 'beginner' else 'sin contexto'}\n"
            f"  - Pausas de 0.5s después de cada término clave nuevo\n"
            f"  - Tono ascendente al introducir analogías, descendente al cerrar ideas\n"
        )

        if analogies and vocab_config["analogy_emphasis"] != "baja":
            prompt += f"\nANALOGÍA ORAL A INTEGRAR:\n  - '{analogies[0]}'\n  - Narrar con énfasis especial para facilitar la imagen mental\n"

        if misconceptions:
            prompt += f"\nERROR CONCEPTUAL A CORREGIR ORALMENTE:\n  - Presentar el error primero, luego la corrección con tono seguro\n  - '{misconceptions[0]}'\n"

        params = {
            "voice": voice_style.split("—")[0].strip(),
            "speed": "0.85x" if difficulty_level == "beginner" else "1.0x" if difficulty_level == "intermediate" else "1.1x",
            "background_music": "educational_ambient_soft",
            "format": "mp3",
            "estimated_duration_seconds": 28 + narration_seconds,
            "difficulty_level": difficulty_level,
            "bloom_level": bloom_level,
            "bloom_verb": bloom_verb,
            "pause_emphasis": reinforcement == "high",
            "glossary_audio_callouts": difficulty_level == "beginner",
        }

        return prompt, params

    # ── Interactive prompt generator ──────────────────────────────────────

    def _generate_interactive_prompt(
        self,
        title: str,
        desc: str,
        topic: str,
        bloom_level: int,
        difficulty_level: str,
        explanation_depth: str,
        vocab_config: dict,
        action_verbs: list[str],
        examples: list[str],
        analogies: list[str],
        concepts: list[str] | None = None,
        misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None,
        sources: list[dict] | None = None,
        reinforcement: str = "normal",
    ) -> tuple[str, dict]:
        bloom_verb = _BLOOM_VERBS.get(bloom_level, "comprender")
        primary_verb = action_verbs[0] if action_verbs else "aplicar"

        # Interaction type scales with Bloom level
        interaction_types = {
            1: ("reconocimiento de definiciones", "Relacionar términos con definiciones correctas"),
            2: ("explicación con palabras propias", "Completar un párrafo de explicación con las palabras correctas"),
            3: ("ejercicio de aplicación guiada", "Resolver un problema paso a paso con andamiaje"),
            4: ("análisis comparativo", "Comparar dos enfoques y justificar cuál es más adecuado"),
            5: ("evaluación de soluciones", "Identificar el criterio de error en una solución dada y proponer la corrección"),
            6: ("diseño libre", "Diseñar desde cero una solución al problema propuesto"),
        }
        interaction_name, interaction_instruction = interaction_types.get(
            bloom_level, ("ejercicio guiado", "Completar la actividad propuesta")
        )

        max_attempts = 3 if difficulty_level == "beginner" else 2 if difficulty_level == "intermediate" else 1
        feedback_style = {
            "beginner": "correctivo y constructivo — explicar el error con detalle y guiar hacia la respuesta correcta",
            "intermediate": "conciso y orientador — señalar el error y dar una pista sobre la corrección",
            "advanced": "mínimo — solo confirmar o rechazar, el aprendiz deduce el ajuste",
        }.get(difficulty_level, "constructivo")

        prompt = (
            f"INTERACTIVE PROMPT — PEDAGOGICAL EXERCISE\n"
            f"{'='*50}\n\n"
            f"TEMA: {topic}\n"
            f"SECCIÓN: {title}\n"
            f"DESCRIPCIÓN: {desc}\n\n"
            f"OBJETIVO COGNITIVO (Bloom {bloom_level} — {bloom_verb}):\n"
            f"  El aprendiz debe poder {primary_verb} {topic} a través de esta actividad.\n\n"
            f"TIPO DE ACTIVIDAD: {interaction_name}\n"
            f"INSTRUCCIÓN PRINCIPAL: {interaction_instruction}\n\n"
            f"PERFIL DEL APRENDIZ:\n"
            f"  - Nivel: {difficulty_level}\n"
            f"  - Intentos máximos: {max_attempts}\n"
            f"  - Feedback: {feedback_style}\n\n"
            f"ESTRUCTURA DE LA ACTIVIDAD:\n"
            f"  1. INSTRUCCIÓN: Presentar el objetivo en términos de {bloom_verb}\n"
            f"     - Usar verbos Bloom {bloom_level}: {', '.join(action_verbs[:3])}\n"
            f"  2. CONTEXTO: {'Escenario familiar y cotidiano para principiantes' if difficulty_level == 'beginner' else 'Escenario aplicado con contexto técnico' if difficulty_level == 'intermediate' else 'Problema técnico complejo con ambigüedad intencional'}\n"
            f"  3. ACTIVIDAD PRINCIPAL:\n"
            f"     - {interaction_instruction}\n"
            f"     {'- Andamiaje: pistas progresivas disponibles' if difficulty_level == 'beginner' else '- Sin andamiaje: el aprendiz trabaja de forma autónoma' if difficulty_level == 'advanced' else '- Andamiaje mínimo disponible bajo solicitud'}\n"
            f"  4. VALIDACIÓN:\n"
            f"     - Criterios de éxito definidos explícitamente\n"
            f"     - Retroalimentación inmediata calibrada para nivel {difficulty_level}\n"
            f"  5. REFLEXIÓN FINAL:\n"
            f"     - '¿Qué estrategia usaste para {primary_verb} {topic}?'\n\n"
            f"REQUERIMIENTOS PEDAGÓGICOS:\n"
            f"  - Dificultad: {'calibrada para principiante, con scaffolding' if difficulty_level == 'beginner' else 'intermedia con aplicación real' if difficulty_level == 'intermediate' else 'avanzada con ambigüedad y casos límite'}\n"
            f"  - Refuerzo positivo en aciertos: {'detallado y motivacional' if reinforcement == 'high' else 'breve y confirmatorio'}\n"
            f"  - Explicación en errores: {feedback_style}\n"
            f"  - Nivel Bloom objetivo alcanzado si el aprendiz completa con < {max_attempts} intentos\n"
        )

        if misconceptions:
            prompt += (
                f"\nCONCEPCIÓN ERRÓNEA A INTEGRAR EN LA ACTIVIDAD:\n"
                f"  - Diseñar una opción de respuesta incorrecta basada en: {misconceptions[0]}\n"
                f"  - Feedback especial al seleccionar esa opción\n"
            )

        if real_applications:
            prompt += f"\nCONTEXTO DE APLICACIÓN REAL:\n  - {real_applications[0]}\n"

        params = {
            "interaction_type": interaction_name.replace(" ", "_"),
            "difficulty": difficulty_level,
            "bloom_level": bloom_level,
            "bloom_verb": bloom_verb,
            "feedback_style": feedback_style.split("—")[0].strip(),
            "max_attempts": max_attempts,
            "scaffolding": difficulty_level == "beginner",
            "hint_system": difficulty_level != "advanced",
            "adaptive_difficulty": True,
        }

        return prompt, params

    # ── Cohesion builders ─────────────────────────────────────────────────

    def _build_narrative_thread(
        self,
        topic: str,
        sections: list[dict],
        difficulty_level: str,
        bloom_range: list[int],
    ) -> str:
        section_bloom = " → ".join(
            f"{s.get('title', s.get('section_type', ''))}"
            f"(Bloom {s.get('bloom_level', '?')})"
            for s in sections
        )
        bloom_min = min(bloom_range) if bloom_range else 1
        bloom_max = max(bloom_range) if bloom_range else 4
        return (
            f"Hilo narrativo para '{topic}' | perfil={difficulty_level} | "
            f"rango Bloom aprendiz=[{bloom_min},{bloom_max}]:\n"
            f"  {section_bloom}\n"
            f"  Progresión cognitiva: de {_BLOOM_VERBS.get(bloom_min, 'recordar')} "
            f"a {_BLOOM_VERBS.get(bloom_max, 'analizar')}.\n"
            f"  Vocabulario: consistente con nivel {difficulty_level} en toda la secuencia.\n"
            f"  Tono: {_DIFFICULTY_VOCAB.get(difficulty_level, {}).get('tone', 'académico accesible')}."
        )

    def _build_visual_continuity(
        self,
        topic: str,
        prompts: list[GeneratedPrompt],
        difficulty_level: str,
    ) -> str:
        palette = {
            "beginner": "colores primarios, alto contraste, tipografía grande",
            "intermediate": "azul académico, blanco, tonos suaves, tipografía estándar",
            "advanced": "gris técnico, azul oscuro, mínimo decorativo, tipografía densa",
        }.get(difficulty_level, "paleta académica estándar")
        return (
            f"Continuidad visual para '{topic}' (perfil={difficulty_level}):\n"
            f"  - Paleta consistente: {palette}\n"
            f"  - Misma tipografía en todos los elementos visuales\n"
            f"  - Iconografía de programación coherente entre secciones\n"
            f"  - Complejidad visual escalada con Bloom: "
            f"{', '.join(f'Bloom{p.bloom_level}={p.prompt_type}' for p in prompts)}"
        )

    def _suggest_audio_atmosphere(
        self,
        topic: str,
        sections: list[dict],
        difficulty_level: str,
    ) -> str:
        atmosphere = {
            "beginner": "música educativa suave y cálida, ritmo lento, pausa entre puntos",
            "intermediate": "música ambiental académica, ritmo moderado, transiciones suaves",
            "advanced": "música minimalista de fondo, ritmo ágil, sin distracciones sonoras",
        }.get(difficulty_level, "música educativa ambiental")
        return (
            f"Atmósfera de audio para '{topic}' (perfil={difficulty_level}):\n"
            f"  - {atmosphere}\n"
            f"  - Volumen de fondo: {'muy bajo, nunca compite con la voz' if difficulty_level == 'beginner' else 'bajo'}\n"
            f"  - Tono de voz: {_DIFFICULTY_VOCAB.get(difficulty_level, {}).get('tone', 'profesional y pausado')}"
        )
