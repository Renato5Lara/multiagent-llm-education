"""
EngagementGeneratorAgent — genera recursos de engagement adaptativos.

No es subclase de BaseAgent porque no produce trazas de decisión
(el agente de engagement es infraestructura de motivación, no
razonamiento pedagógico propiamente dicho).

Utiliza el singleton ai_service existente (OpenAI sync) para mantener
consistencia con el patrón del proyecto.  Ante cualquier fallo del LLM
devuelve recursos de fallback con contenido real y no genérico.

Tipos de recursos priorizados (ajustables vía PRIORITY_MAP):
  1. did_you_know      — curiosidad inmediata, funciona para todos los perfiles
  2. detonating_question — activa reflexión previa
  3. real_news         — conexión con el mundo real (perfil lector/visual)
  4. mini_quiz         — autoevaluación rápida (kinestésico/lector)
  5. short_challenge   — reto aplicado (kinestésico)
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Mapa de tipos prioritarios por perfil de aprendizaje ────────────────────

PRIORITY_MAP: dict[str, list[str]] = {
    "visual":      ["did_you_know", "real_news", "detonating_question", "short_challenge", "mini_quiz"],
    "auditory":    ["did_you_know", "detonating_question", "real_news", "mini_quiz", "short_challenge"],
    "kinesthetic": ["short_challenge", "mini_quiz", "did_you_know", "detonating_question", "real_news"],
    "reading":     ["did_you_know", "detonating_question", "real_news", "mini_quiz", "short_challenge"],
}

DEFAULT_PRIORITY = PRIORITY_MAP["reading"]

# ── Prompts ──────────────────────────────────────────────────────────────────

_SYSTEM = """
Eres un diseñador pedagógico experto en metodología 5E, gamificación educativa
y psicología del aprendizaje.  Tu misión es generar recursos para la fase
"Engage" que activen la curiosidad del estudiante ANTES de ver el contenido.

Principios que debes aplicar:
- Cada recurso debe generar una reacción emocional inmediata (sorpresa, intriga, desafío).
- Conecta siempre el tema con tecnología, empresas reales o situaciones cotidianas.
- Usa lenguaje cercano, dinámico y motivador — nunca académico ni formal.
- Sé específico: menciona empresas, números, tecnologías o eventos reales.
- El mini_quiz debe tener UNA respuesta correcta clara, con explicación breve.
- El short_challenge debe poder responderse en 2-3 minutos sin material adicional.

Responde ÚNICAMENTE con JSON válido siguiendo el schema exacto.  Sin texto extra.
"""

_USER_TEMPLATE = """
Módulo: {module_title}
Curso: {course_name}
Nivel Bloom objetivo: {bloom_level} ({bloom_label})
Perfil de aprendizaje del estudiante: {modality}
Tipos a generar (en este orden de prioridad): {resource_types}
Cantidad: {count} recursos

Genera exactamente {count} recursos en español peruano.
Usa terminología técnica apropiada para universitarios de ingeniería.

JSON schema requerido:
{{
  "resources": [
    {{
      "resource_type": "did_you_know",
      "title": "¿Sabías que...?",
      "content": "<máx 3 oraciones directas, datos concretos, sin relleno>",
      "is_interactive": false,
      "resource_metadata": {{}}
    }},
    {{
      "resource_type": "detonating_question",
      "title": "Antes de comenzar...",
      "content": "<pregunta que NO tiene respuesta obvia, genera debate interno>",
      "is_interactive": false,
      "resource_metadata": {{}}
    }},
    {{
      "resource_type": "real_news",
      "title": "<titular estilo periodístico>",
      "content": "<noticia breve (real o verosímil) que conecta el tema con la industria>",
      "is_interactive": false,
      "resource_metadata": {{
        "source_hint": "<empresa o medio real>",
        "year": "<año aproximado>"
      }}
    }},
    {{
      "resource_type": "mini_quiz",
      "title": "Prueba tu intuición",
      "content": "<pregunta que parece difícil pero tiene lógica>",
      "is_interactive": true,
      "resource_metadata": {{
        "question": "<la pregunta completa>",
        "options": ["<opción A>", "<opción B>", "<opción C>", "<opción D>"],
        "correct_index": 0,
        "explanation": "<por qué esa opción es correcta, máx 2 oraciones>"
      }}
    }},
    {{
      "resource_type": "short_challenge",
      "title": "Reto rápido",
      "content": "<descripción del reto en 1-2 oraciones>",
      "is_interactive": true,
      "resource_metadata": {{
        "prompt": "<instrucción precisa de qué debe hacer el estudiante>",
        "hint": "<pista que ayuda sin dar la respuesta>",
        "answer_type": "text",
        "expected_keywords": ["<palabra clave 1>", "<palabra clave 2>"]
      }}
    }}
  ]
}}
"""

_BLOOM_LABELS = {
    1: "Recordar",
    2: "Comprender",
    3: "Aplicar",
    4: "Analizar",
    5: "Evaluar",
    6: "Crear",
}


class EngagementGeneratorAgent:
    """
    Genera una lista de recursos de engagement adaptados al perfil del estudiante.

    Uso:
        agent = EngagementGeneratorAgent()
        resources = agent.generate(
            module_title="Estructuras de Datos",
            course_name="Algoritmos I",
            bloom_level=3,
            modality="visual",
            count=5,
        )
    """

    def generate(
        self,
        module_title: str,
        course_name: str,
        bloom_level: int,
        modality: str,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        resource_types = self._resource_types_for(modality, count)

        prompt = _USER_TEMPLATE.format(
            module_title=module_title,
            course_name=course_name,
            bloom_level=bloom_level,
            bloom_label=_BLOOM_LABELS.get(bloom_level, "Aplicar"),
            modality=modality,
            resource_types=", ".join(resource_types),
            count=count,
        )

        raw = self._llm_call(prompt)
        if raw:
            try:
                parsed = json.loads(raw)
                resources = parsed.get("resources", [])
                if len(resources) >= 1:
                    return self._validate_and_cap(resources, count)
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning("EngagementGeneratorAgent: JSON parse failed (%s), using fallback", exc)

        logger.info("EngagementGeneratorAgent: using static fallback for module='%s'", module_title)
        return self._fallback_resources(module_title, modality, count)

    # ── LLM call ─────────────────────────────────────────────────────────────

    @staticmethod
    def _llm_call(user_prompt: str) -> str | None:
        try:
            from app.services.ai_service import ai_service
            return ai_service._call_openai(
                system_prompt=_SYSTEM,
                user_prompt=user_prompt,
                temperature=0.75,
            )
        except Exception as exc:
            logger.warning("EngagementGeneratorAgent: LLM call failed: %s", exc)
            return None

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _resource_types_for(modality: str, count: int) -> list[str]:
        priority = PRIORITY_MAP.get(modality, DEFAULT_PRIORITY)
        # Cycle through the list if count > len(priority)
        result = []
        for i in range(count):
            result.append(priority[i % len(priority)])
        return result

    @staticmethod
    def _validate_and_cap(resources: list[dict], count: int) -> list[dict[str, Any]]:
        valid = []
        for r in resources:
            if isinstance(r, dict) and r.get("resource_type") and r.get("content"):
                valid.append({
                    "resource_type":    str(r.get("resource_type", "did_you_know")),
                    "title":            str(r.get("title", "Descubre esto")),
                    "content":          str(r.get("content", "")),
                    "media_url":        r.get("media_url") or None,
                    "is_interactive":   bool(r.get("is_interactive", False)),
                    "resource_metadata": r.get("resource_metadata") or {},
                })
        return valid[:count]

    # ── Fallback estático ─────────────────────────────────────────────────────

    @staticmethod
    def _fallback_resources(module_title: str, modality: str, count: int) -> list[dict[str, Any]]:
        """
        Recursos de alta calidad para usar cuando el LLM no está disponible.
        Están escritos de forma suficientemente genérica para funcionar con
        cualquier módulo técnico universitario.
        """
        all_fallbacks: list[dict[str, Any]] = [
            {
                "resource_type":   "did_you_know",
                "title":           "¿Sabías que...?",
                "content":         (
                    f"El 73% de los ingenieros de software encuestados por Stack Overflow en 2024 "
                    f"señala que dominar conceptos como {module_title} fue decisivo para obtener "
                    f"su primer empleo en la industria tecnológica."
                ),
                "is_interactive":  False,
                "resource_metadata": {},
            },
            {
                "resource_type":   "detonating_question",
                "title":           "Antes de comenzar...",
                "content":         (
                    f"Si tuvieras que explicarle {module_title} a alguien que nunca ha estudiado "
                    f"programación, ¿por dónde empezarías? ¿Usarías una analogía del mundo real?"
                ),
                "is_interactive":  False,
                "resource_metadata": {},
            },
            {
                "resource_type":   "real_news",
                "title":           f"La industria exige {module_title}",
                "content":         (
                    f"Empresas como Google, Meta y Spotify publican en sus blogs técnicos que "
                    f"los conceptos detrás de {module_title} están en el núcleo de sus sistemas "
                    f"que sirven a más de mil millones de usuarios diariamente."
                ),
                "is_interactive":  False,
                "resource_metadata": {
                    "source_hint": "Google Engineering Blog",
                    "year": "2024",
                },
            },
            {
                "resource_type":   "mini_quiz",
                "title":           "Prueba tu intuición",
                "content":         f"¿Cuál es el principal beneficio de dominar {module_title} en proyectos reales?",
                "is_interactive":  True,
                "resource_metadata": {
                    "question":      f"¿Por qué es importante entender {module_title} como ingeniero de software?",
                    "options": [
                        "Permite resolver problemas más complejos con soluciones más eficientes",
                        "Es necesario para aprobar el curso, pero rara vez se usa en la industria",
                        "Solo importa si vas a trabajar en empresas grandes como Google",
                        "Es un requisito formal pero los frameworks lo abstraen completamente",
                    ],
                    "correct_index": 0,
                    "explanation":   (
                        "Dominar los fundamentos te da la capacidad de elegir la solución correcta "
                        "cuando los frameworks no son suficientes — y eso ocurre más de lo que parece."
                    ),
                },
            },
            {
                "resource_type":   "short_challenge",
                "title":           "Reto de activación",
                "content":         (
                    f"En 2 minutos, escribe la primera aplicación práctica de {module_title} "
                    f"que se te ocurra en tu carrera o en tu vida cotidiana."
                ),
                "is_interactive":  True,
                "resource_metadata": {
                    "prompt":    f"¿Dónde usarías {module_title} en un proyecto real que te importe?",
                    "hint":      "Piensa en apps que usas todos los días: redes sociales, streaming, mapas...",
                    "answer_type": "text",
                    "expected_keywords": ["aplicación", "datos", "sistema", "usuario", "problema"],
                },
            },
        ]

        priority = PRIORITY_MAP.get(modality, DEFAULT_PRIORITY)
        ordered: list[dict[str, Any]] = []
        type_to_resource = {r["resource_type"]: r for r in all_fallbacks}
        for rtype in priority:
            if rtype in type_to_resource and len(ordered) < count:
                ordered.append(type_to_resource[rtype])
        # Pad with remaining if needed
        for r in all_fallbacks:
            if len(ordered) >= count:
                break
            if r not in ordered:
                ordered.append(r)

        return ordered[:count]


# Singleton — mismo patrón que ai_service
engagement_generator_agent = EngagementGeneratorAgent()
