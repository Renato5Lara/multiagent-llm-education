"""PromptEngineeringAgent — genera prompts detallados: cinematográficos, visuales, narrativos y de audio."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.pedagogical_orchestration import GeneratedPrompt

logger = logging.getLogger(__name__)


class PromptEngineeringAgent(BaseAgent):
    """Genera prompts especializados para cada modalidad con coherencia pedagógica.

    Responsabilidades:
    - Generar prompts cinematográficos (video/storyboard)
    - Generar prompts visuales (imágenes/diagramas)
    - Generar prompts narrativos (texto estructurado)
    - Generar prompts de audio (narración/atmósfera)
    - Mantener consistencia estilística entre prompts

    Lee de shared memory:
    - pedagogical:structure
    - multimodal:plan
    - research:findings (ejemplos, analogías)

    Escribe en shared memory:
    - prompts:generated
    - prompts:narrative_thread
    """

    @property
    def agent_type(self) -> str:
        return "prompt_engineering"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        pedagogical = state.get("pedagogical_structure", {})
        sections = pedagogical.get("sections", []) if isinstance(pedagogical, dict) else []
        multimodal_plan = state.get("multimodal_plan", {})
        prompt_sections = multimodal_plan.get("prompt_sections", {}) if isinstance(multimodal_plan, dict) else {}
        research = state.get("research_result", {})
        examples = research.get("examples", []) if isinstance(research, dict) else []
        analogies = research.get("analogies", []) if isinstance(research, dict) else []
        concepts = research.get("concepts", []) if isinstance(research, dict) else []
        misconceptions = research.get("misconceptions", []) if isinstance(research, dict) else []
        real_applications = research.get("real_applications", []) if isinstance(research, dict) else []
        sources = research.get("sources", []) if isinstance(research, dict) else []

        topic = state.get("topic", "")
        prompts = []

        for section in sections:
            section_type = section.get("section_type", "unknown")
            section_title = section.get("title", "")
            section_desc = section.get("description", "")

            prompt_type = prompt_sections.get(section_type)
            if not prompt_type:
                continue

            prompt = self._generate_prompt(
                prompt_type=prompt_type,
                section_type=section_type,
                title=section_title,
                description=section_desc,
                topic=topic,
                examples=examples,
                analogies=analogies,
                concepts=concepts,
                misconceptions=misconceptions,
                real_applications=real_applications,
                sources=sources,
            )
            prompts.append(prompt)

        narrative_thread = self._build_narrative_thread(topic, sections)
        visual_continuity = self._build_visual_continuity(topic, prompts)
        audio_atmosphere = self._suggest_audio_atmosphere(topic, sections)

        result = {
            "prompts": [p.model_dump() for p in prompts],
            "narrative_thread": narrative_thread,
            "visual_continuity": visual_continuity,
            "audio_atmosphere": audio_atmosphere,
            "prompt_count": len(prompts),
        }

        await self.publish_observation(
            f"{self.context_key}:prompts:generated",
            result,
            memory_type="inference",
            confidence=0.85,
        )

        return result

    def _generate_prompt(
        self,
        prompt_type: str,
        section_type: str,
        title: str,
        description: str,
        topic: str,
        examples: list[str],
        analogies: list[str],
        concepts: list[str] | None = None,
        misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None,
        sources: list[dict] | None = None,
    ) -> GeneratedPrompt:
        generators = {
            "cinematic": self._generate_cinematic_prompt,
            "visual": self._generate_visual_prompt,
            "narrative": self._generate_narrative_prompt,
            "audio": self._generate_audio_prompt,
            "interactive": self._generate_interactive_prompt,
        }

        generator = generators.get(prompt_type, self._generate_narrative_prompt)
        content, params = generator(
            title, description, topic, examples, analogies,
            concepts=concepts, misconceptions=misconceptions,
            real_applications=real_applications, sources=sources,
        )

        model_map = {
            "cinematic": "Sora / Runway Gen-3",
            "visual": "DALL-E 3 / Midjourney",
            "narrative": "GPT-4o / Claude",
            "audio": "ElevenLabs / TTS-1",
            "interactive": "Web / HTML5",
        }

        return GeneratedPrompt(
            prompt_type=prompt_type,
            target_section=section_type,
            content=content,
            parameters=params,
            model_recommendation=model_map.get(prompt_type, "GPT-4o"),
        )

    def _generate_cinematic_prompt(
        self, title: str, desc: str, topic: str, examples: list[str], analogies: list[str],
        concepts: list[str] | None = None, misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None, sources: list[dict] | None = None,
    ) -> tuple[str, dict]:
        storyboard = (
            f"CINEMATIC PROMPT: {title}\n\n"
            f"TEMA: {topic}\n"
            f"DESCRIPCIÓN: {desc}\n\n"
            f"ESTRUCTURA DE ESCENAS:\n\n"
            f"ESCENA 1 - APERTURA ({topic} en contexto real)\n"
            f"  - Plano general del entorno de aplicación\n"
            f"  - Voz en off: introducción al tema\n"
            f"  - Duración: 15 segundos\n\n"
            f"ESCENA 2 - EXPLICACIÓN DEL CONCEPTO\n"
            f"  - Animación de conceptos clave con gráficos en movimiento\n"
            f"  - Texto emergente con definiciones importantes\n"
            f"  - Duración: 30 segundos\n\n"
            f"ESCENA 3 - EJEMPLO PRÁCTICO\n"
            f"  - Demostración visual paso a paso\n"
            f"  - Split screen: teoría vs. aplicación\n"
            f"  - Duración: 25 segundos\n\n"
            f"ESCENA 4 - CIERRE Y REFLEXIÓN\n"
            f"  - Plano medio del presentador\n"
            f"  - Resumen visual de puntos clave\n"
            f"  - Call to action: invitación a practicar\n"
            f"  - Duración: 15 segundos\n\n"
            f"ESTILO VISUAL:\n"
            f"  - Paleta: colores corporativos educativos\n"
            f"  - Tipografía: sans-serif, legible\n"
            f"  - Ritmo: pausado, didáctico\n"
            f"  - Transiciones: suaves, fundidos\n"
        )

        if analogies:
            storyboard += f"\nANALOGÍA VISUAL:\n  - {analogies[0]}\n"

        if misconceptions:
            storyboard += f"\nERROR COMÚN A REPRESENTAR:\n  - {misconceptions[0]}\n"

        if real_applications:
            storyboard += f"\nAPLICACIÓN REAL:\n  - {real_applications[0]}\n"

        if concepts:
            storyboard += f"\nCONCEPTOS CLAVE:\n"
            for c in concepts[:3]:
                storyboard += f"  - {c}\n"

        if sources:
            storyboard += f"\nREFERENCIAS:\n"
            for s in sources[:2]:
                storyboard += f"  - {s.get('title', '')} ({s.get('domain', '')})\n"

        params = {
            "aspect_ratio": "16:9",
            "style": "educational_documentary",
            "duration_seconds": 85,
            "narration_required": True,
            "subtitles_required": True,
        }

        return storyboard, params

    def _generate_visual_prompt(
        self, title: str, desc: str, topic: str, examples: list[str], analogies: list[str],
        concepts: list[str] | None = None, misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None, sources: list[dict] | None = None,
    ) -> tuple[str, dict]:
        prompt = (
            f"VISUAL PROMPT: {title}\n\n"
            f"DESCRIPCIÓN:\n{desc}\n\n"
            f"ESTILO VISUAL:\n"
            f"  - Estilo: diagrama educativo, clean, profesional\n"
            f"  - Colores: azul académico, blanco, tonos suaves\n"
            f"  - Composición: organizada, jerárquica\n"
            f"  - Tipografía: clara, sans-serif\n\n"
            f"ELEMENTOS A INCLUIR:\n"
            f"  - Concepto central de {topic}\n"
            f"  - Relaciones entre sub-conceptos\n"
            f"  - Iconos representativos\n"
            f"  - Etiquetas explicativas\n"
        )

        if examples:
            prompt += f"\nREFERENCIA VISUAL:\n  - Ejemplo: {examples[0]}\n"

        if analogies:
            prompt += f"\nANALOGÍA VISUAL:\n  - {analogies[0]}\n"

        if misconceptions:
            prompt += f"\nERROR COMÚN A ILUSTRAR:\n  - {misconceptions[0]}\n"

        if concepts:
            prompt += f"\nCONCEPTOS A DIAGRAMAR:\n"
            for c in concepts[:5]:
                prompt += f"  - {c}\n"

        if sources:
            prompt += f"\nFUENTES:\n"
            for s in sources[:2]:
                prompt += f"  - {s.get('title', '')}\n"

        params = {
            "format": "16:9",
            "style": "educational_diagram",
            "color_palette": "academic_blue",
            "detail_level": "high",
        }

        return prompt, params

    def _generate_narrative_prompt(
        self, title: str, desc: str, topic: str, examples: list[str], analogies: list[str],
        concepts: list[str] | None = None, misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None, sources: list[dict] | None = None,
    ) -> tuple[str, dict]:
        prompt = (
            f"NARRATIVE PROMPT: {title}\n\n"
            f"Tono: Académico pero accesible, estilo divulgativo\n"
            f"Audiencia: Estudiantes de educación superior\n"
            f"Extensión: 400-600 palabras\n\n"
            f"ESTRUCTURA NARRATIVA:\n"
            f"  1. Gancho inicial que conecta con experiencia del estudiante\n"
            f"  2. Exposición del concepto con lenguaje claro\n"
            f"  3. Conexión con conocimientos previos\n"
            f"  4. Ejemplo concreto que ilustra el punto\n"
            f"  5. Transición hacia la aplicación práctica\n\n"
            f"REQUERIMIENTOS:\n"
            f"  - Evitar jerga innecesaria\n"
            f"  - Incluir pausas reflexivas\n"
            f"  - Terminar con pregunta que active pensamiento crítico\n"
        )

        if analogies:
            prompt += f"\nANALOGÍA INTEGRADA:\n  - {analogies[0]}\n"

        if real_applications:
            prompt += f"\nAPLICACIÓN REAL:\n  - {real_applications[0]}\n"

        if misconceptions:
            prompt += f"\nACLARAR ERROR COMÚN:\n  - {misconceptions[0]}\n"

        if concepts:
            prompt += f"\nCONCEPTOS A ABORDAR:\n"
            for c in concepts[:3]:
                prompt += f"  - {c}\n"

        params = {
            "target_word_count": 500,
            "tone": "academic_accessible",
            "complexity": "intermediate",
            "requires_critical_thinking": True,
        }

        return prompt, params

    def _generate_audio_prompt(
        self, title: str, desc: str, topic: str, examples: list[str], analogies: list[str],
        concepts: list[str] | None = None, misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None, sources: list[dict] | None = None,
    ) -> tuple[str, dict]:
        prompt = (
            f"AUDIO PROMPT: {title}\n\n"
            f"DESCRIPCIÓN:\n{desc}\n\n"
            f"ESTILO DE NARRACIÓN:\n"
            f"  - Voz: clara, pausada, entusiasta pero profesional\n"
            f"  - Ritmo: moderado, con pausas para reflexión\n"
            f"  - Énfasis: en términos clave y definiciones\n\n"
            f"ESTRUCTURA DE AUDIO:\n"
            f"  - Introducción musical suave (5 seg)\n"
            f"  - Narración principal (60-90 seg)\n"
            f"  - Pausa reflexiva (3 seg)\n"
            f"  - Cierre con música (5 seg)\n\n"
            f"ATMÓSFERA:\n"
            f"  - Música de fondo: educativa, inspiradora, baja intensidad\n"
            f"  - Efectos: subtle transitions entre secciones\n"
        )

        params = {
            "voice": "professional_male_or_female",
            "speed": "1.0x",
            "background_music": "educational_ambient",
            "format": "mp3",
            "estimated_duration_seconds": 90,
        }

        return prompt, params

    def _generate_interactive_prompt(
        self, title: str, desc: str, topic: str, examples: list[str], analogies: list[str],
        concepts: list[str] | None = None, misconceptions: list[str] | None = None,
        real_applications: list[str] | None = None, sources: list[dict] | None = None,
    ) -> tuple[str, dict]:
        prompt = (
            f"INTERACTIVE PROMPT: {title}\n\n"
            f"DESCRIPCIÓN:\n{desc}\n\n"
            f"TIPO DE ACTIVIDAD:\n"
            f"  - Ejercicio interactivo paso a paso\n"
            f"  - Feedback inmediato por respuesta\n"
            f"  - Niveles de dificultad progresivos\n\n"
            f"ESTRUCTURA:\n"
            f"  1. Instrucción clara de la actividad\n"
            f"  2. Escenario o problema contextualizado\n"
            f"  3. Opciones de respuesta o área de entrada\n"
            f"  4. Feedback correctivo constructivo\n"
            f"  5. Explicación de la solución\n\n"
            f"REQUERIMIENTOS PEDAGÓGICOS:\n"
            f"  - Alineado con objetivos de aprendizaje\n"
            f"  - Dificultad adaptativa según respuestas\n"
            f"  - Refuerzo positivo en aciertos\n"
            f"  - Explicación detallada en errores\n"
        )

        params = {
            "interaction_type": "guided_exercise",
            "difficulty": "adaptive",
            "feedback_style": "constructive",
            "max_attempts": 3,
        }

        return prompt, params

    def _build_narrative_thread(self, topic: str, sections: list[dict]) -> str:
        section_names = [s.get("title", "") for s in sections]
        return (
            f"Hilo narrativo transversal para '{topic}': "
            f"{' → '.join(section_names)}. "
            f"Mantener tono consistente, progresión lógica y "
            f"lenguaje accesible en toda la secuencia."
        )

    def _build_visual_continuity(self, topic: str, prompts: list[GeneratedPrompt]) -> str:
        return (
            f"Continuidad visual para '{topic}': "
            f"mantener paleta de colores consistente (azul académico), "
            f"misma tipografía, mismo estilo de diagramas, "
            f"mismos iconos representativos en todo el material visual."
        )

    def _suggest_audio_atmosphere(self, topic: str, sections: list[dict]) -> str:
        return (
            f"Atmósfera de audio sugerida para '{topic}': "
            f"música educativa ambiental de fondo, volumen bajo, "
            f"transiciones suaves entre secciones, "
            f"tono de voz profesional y pausado."
        )
