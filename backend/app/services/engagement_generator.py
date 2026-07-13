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

from app.services.pedagogical_identity import PEDAGOGICAL_IDENTITY

logger = logging.getLogger(__name__)

# ── Mapa de tipos prioritarios por perfil de aprendizaje ────────────────────

PRIORITY_MAP: dict[str, list[str]] = {
    "visual":      ["did_you_know", "prior_knowledge", "real_news", "detonating_question", "short_challenge", "mini_quiz"],
    "auditory":    ["did_you_know", "prior_knowledge", "detonating_question", "real_news", "mini_quiz", "short_challenge"],
    "kinesthetic": ["did_you_know", "prior_knowledge", "short_challenge", "mini_quiz", "detonating_question", "real_news"],
    "reading":     ["did_you_know", "prior_knowledge", "detonating_question", "real_news", "mini_quiz", "short_challenge"],
}

DEFAULT_PRIORITY = PRIORITY_MAP["reading"]

# ── Prompts ──────────────────────────────────────────────────────────────────

_SYSTEM = f"""
Eres el diseñador pedagógico de la fase "Engage" (metodología 5E) de un curso
universitario de Fundamentos de la Programación.  Tu misión es activar la
curiosidad del estudiante ANTES de que vea el contenido del módulo.

{PEDAGOGICAL_IDENTITY}

REGLAS ESPECÍFICAS DE ENGAGE:
- Cada recurso debe romper una expectativa concreta del estudiante o abrir un
  conflicto que el módulo resolverá — nunca validar la importancia del tema.
- Patrones narrativos permitidos (usa uno DISTINTO por recurso, nunca repitas
  patrón en el mismo lote): error histórico costoso, origen accidental,
  ironía tecnológica, experimento mental, paradoja entre lenguaje cotidiano y
  literalidad de la máquina, escala humanizada.
- El mini_quiz debe tener UNA respuesta correcta clara; cada distractor debe
  encarnar un error conceptual (misconception) real y documentado del tema.
- El short_challenge debe poder resolverse en 2-3 minutos sin material
  adicional y garantizar un momento "ajá" verificable.
- En "did_you_know", la fuente debe ser real y verificable. Nunca inventes una
  URL — si no estás seguro del dominio exacto, omite el campo "domain" en vez
  de inventarlo.

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
      "content": "<historia real con giro en máx 3 oraciones: persona, fecha y consecuencia concreta que rompe una expectativa del estudiante, más una frase puente hacia {module_title}. PROHIBIDO abrir con un porcentaje, una cifra o una encuesta>",
      "is_interactive": false,
      "resource_metadata": {{
        "explanation": "<1 oración: por qué este dato importa para {module_title}>",
        "source": {{
          "label": "<nombre real de la fuente (encuesta, paper, blog técnico, informe)>",
          "domain": "<dominio real de la fuente, ej. stackoverflow.com>",
          "year": "<año aproximado>"
        }},
        "evidence": "<1 frase: qué evidencia concreta respalda el dato (tamaño de muestra, método, alcance)>"
      }}
    }},
    {{
      "resource_type": "prior_knowledge",
      "title": "¿Qué tanto conocías este tema antes de hoy?",
      "content": "<una frase breve y motivadora sobre el punto de partida de cada estudiante en relación a {module_title}>",
      "is_interactive": true,
      "resource_metadata": {{}}
    }},
    {{
      "resource_type": "detonating_question",
      "title": "Antes de comenzar...",
      "content": "<dilema que se responde en 5 segundos con pura intuición y luego resulta incómodo: paradoja, dilema binario con trampa o experimento mental — nivel intermedio. PROHIBIDO '¿Cómo explicarías...?', '¿Qué sabes de...?', '¿Por qué es importante...?'>",
      "is_interactive": false,
      "resource_metadata": {{
        "beginner_question":     "<misma pregunta en versión simple para quien nunca ha visto el tema>",
        "intermediate_question": "<la pregunta original — nivel intermedio>",
        "advanced_question":     "<versión técnica y profunda para quien ya tiene experiencia>"
      }}
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
      "content": "<pregunta sobre un caso concreto con resultado verificable (ej. predecir el valor de una variable), no sobre la importancia del tema>",
      "is_interactive": true,
      "resource_metadata": {{
        "question": "<la pregunta completa>",
        "options": ["<opción A>", "<opción B>", "<opción C>", "<opción D>"],
        "correct_index": 0,
        "explanation": "<por qué esa opción es correcta, máx 2 oraciones>",
        "option_feedback": ["<una frase por opción, en el mismo orden: para cada distractor, nombra la intuición razonable que lleva a elegirlo (ej. 'Eso pasa cuando lees = como una ecuación'); para la correcta, nombra qué dominó quien la eligió>"]
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
                    "En 1947, la ingeniera Grace Hopper pegó con cinta adhesiva una polilla real "
                    "en su bitácora: la habían encontrado aplastada dentro de un relé del computador "
                    "Harvard Mark II, y debajo escribió \"primer caso real de un bug encontrado\". "
                    "Años después, Hopper inventó el primer compilador porque le parecía absurdo que "
                    "los humanos tuvieran que hablar el idioma de las máquinas — y no al revés."
                ),
                "is_interactive":  False,
                "resource_metadata": {
                    "explanation": (
                        f"Todo lo que vas a ver en {module_title} existe para lo mismo que empezó "
                        f"con Hopper: acortar la distancia entre cómo piensas tú y cómo \"piensa\" la máquina."
                    ),
                    "source": {
                        "label":  "Bitácora del Harvard Mark II — Computer History Museum",
                        "domain": "computerhistory.org",
                        "year":   "1947",
                    },
                    "evidence": (
                        "La página original de la bitácora, con la polilla aún adherida, se conserva "
                        "en el Museo Nacional de Historia Americana del Smithsonian."
                    ),
                },
            },
            {
                "resource_type":   "prior_knowledge",
                "title":           "¿Qué tanto conocías este tema antes de hoy?",
                "content":         (
                    f"Antes de explorar {module_title}, cuéntanos cuál es tu punto de partida. "
                    f"No hay respuestas correctas — solo queremos adaptar mejor tu experiencia."
                ),
                "is_interactive":  True,
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
                "resource_metadata": {
                    "beginner_question":      f"¿Qué crees que podría ser {module_title}?",
                    "intermediate_question":  f"¿Cómo le explicarías a alguien qué es {module_title}?",
                    "advanced_question":      f"¿Qué aspectos técnicos del funcionamiento de {module_title} destacarías en una explicación profunda?",
                },
            },
            {
                "resource_type":   "real_news",
                "title":           "El error de código que costó 440 millones de dólares en 45 minutos",
                "content":         (
                    "En agosto de 2012, la firma financiera Knight Capital desplegó una actualización "
                    "reutilizando una vieja bandera de configuración — y olvidó actualizar uno de sus "
                    "ocho servidores. Durante 45 minutos, ese servidor compró y vendió acciones sin "
                    "control hasta perder 440 millones de dólares, más de lo que valía la empresa. "
                    "La causa no fue un algoritmo exótico: fue código ordinario que nadie leyó con cuidado."
                ),
                "is_interactive":  False,
                "resource_metadata": {
                    "source_hint": "SEC — informe administrativo del caso Knight Capital",
                    "year": "2012",
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
