import json
import logging
from typing import Optional

from app.agents.prompts import (
    DIAGNOSTIC_ANALYSIS_PROMPT,
    DIAGNOSTIC_SYSTEM_PROMPT,
    TUTOR_CHAT_PROMPT,
    TUTOR_SYSTEM_PROMPT,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Contexto pedagógico decidido por el Runtime LangGraph (runtime_bridge.
# contexto_pedagogico_tutor). El tutor REDACTA sobre estas decisiones;
# jamás las toma: la modalidad, la profundidad, la ruta y la deuda las
# decidió el runtime multiagente (RFC-0002: ninguna capacidad redacta
# mensajes al estudiante; ninguna capa de plataforma decide adaptación).
TUTOR_RUNTIME_PROMPT = """Contexto del estudiante, decidido por el sistema multiagente:
- Curso: {course_name}
- Módulo actual: {module_title}
- Adaptación vigente: {adaptacion}
- Señales de conducta detectadas en la sesión: {senales}
- Ruta de aprendizaje actual: {ruta}
- Deuda de aprendizaje abierta: {deuda}

Usa este contexto para calibrar tu respuesta (modalidad, profundidad y
tono), sin mencionarlo de forma literal ni técnica al estudiante.

Pregunta del estudiante: {message}

Responde en JSON: {{"respuesta": "tu respuesta aquí"}}"""


class AIService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.use_openai = settings.has_openai
        self.client = None
        if self.use_openai:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.warning("Failed to initialize OpenAI: %s", e)
                self.use_openai = False

    @property
    def degraded(self) -> bool:
        """True when the service is running without real LLM capabilities."""
        return not self.use_openai

    def _call_openai(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> Optional[str]:
        if not self.use_openai or not self.client:
            return None
        try:
            from openai import OpenAI
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=1500,
                response_format={"type": "json_object"},
                timeout=30,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            return None

    def analyze_diagnostic_ai(self, profile: dict, raw_answers: dict) -> dict:
        scores_str = json.dumps(raw_answers, ensure_ascii=False)
        bloom_levels = profile.get("preferred_bloom_levels", [3])
        modalities = profile.get("preferred_modalities", ["visual", "reading"])

        prompt = DIAGNOSTIC_ANALYSIS_PROMPT.format(
            learning_style=profile.get("learning_style", "reading"),
            pace=profile.get("pace", "moderate"),
            bloom_levels=bloom_levels,
            modalities=modalities,
            scores=scores_str,
        )

        result = self._call_openai(DIAGNOSTIC_SYSTEM_PROMPT, prompt)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.warning("AI response was not valid JSON")
        return self._fallback_diagnostic_analysis(profile, raw_answers)

    def _fallback_diagnostic_analysis(self, profile: dict, raw_answers: dict) -> dict:
        values = list(raw_answers.values()) if isinstance(raw_answers, dict) else []
        int_values = [int(v) for v in values if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit())]
        avg = sum(int_values) / len(int_values) if int_values else 3.0

        bloom_map = {1: 1, 2: 1, 3: 2, 4: 3, 5: 4}
        estimated_bloom = bloom_map.get(round(avg), 2)

        return {
            "fortalezas": ["Buena disposición al aprendizaje"],
            "debilidades": ["Áreas por explorar según el diagnóstico"],
            "recomendaciones": [
                "Continúa con el diagnóstico completo para un análisis más preciso",
                "Revisa los materiales recomendados para tu estilo de aprendizaje",
                "Establece metas claras para cada módulo del curso",
            ],
            "nivel_bloom_estimado": estimated_bloom,
            "confianza": 0.5,
        }

    def generate_tutor_response(
        self,
        message: str,
        course_name: str,
        module_title: str = "",
        progress: int = 0,
        learning_style: str = "visual",
        bloom_level: int = 2,
        course_code: str = "",
        prerequisites: str = "",
    ) -> str:
        prompt = TUTOR_CHAT_PROMPT.format(
            course_name=course_name,
            course_code=course_code,
            module_title=module_title or "Módulo actual",
            progress=progress,
            learning_style=learning_style,
            bloom_level=bloom_level,
            prerequisites=prerequisites,
            message=message,
        )

        result = self._call_openai(TUTOR_SYSTEM_PROMPT, prompt, temperature=0.7)
        if result:
            try:
                data = json.loads(result)
                return data.get("respuesta", data.get("response", result))
            except json.JSONDecodeError:
                return result
        return self._fallback_tutor_response(message)

    def generate_tutor_response_desde_runtime(
        self,
        message: str,
        course_name: str,
        module_title: str,
        contexto: dict,
    ) -> str:
        """Redacta la respuesta del tutor sobre el contexto que el
        Runtime ya decidió (`runtime_bridge.contexto_pedagogico_tutor`).
        Con contexto vacío (estudiante sin evidencia todavía) el tutor
        responde igual, declarando internamente que aún no hay
        adaptación — un estado válido, no un error."""
        diseno = contexto.get("diseno") or {}
        adaptacion = (
            f"{contexto.get('asunto')} → modalidad {diseno.get('modalidad', '?')}, "
            f"profundidad {diseno.get('profundidad', '?')}"
            if contexto.get("asunto")
            else "sin evidencia todavía (aún no hay adaptación decidida)"
        )
        memoria = contexto.get("memoria") or {}
        prompt = TUTOR_RUNTIME_PROMPT.format(
            course_name=course_name or "Fundamentos de la Programación",
            module_title=module_title or "no especificado",
            adaptacion=adaptacion,
            senales=", ".join(contexto.get("senales", ())) or "ninguna todavía",
            ruta=memoria.get("ruta") or "inicio del curso",
            deuda=", ".join(map(str, memoria.get("deuda_abierta", ()))) or "ninguna",
            message=message,
        )
        result = self._call_openai(TUTOR_SYSTEM_PROMPT, prompt, temperature=0.7)
        if result:
            try:
                data = json.loads(result)
                return data.get("respuesta", data.get("response", result))
            except json.JSONDecodeError:
                return result
        return self._fallback_tutor_response(message)

    def _fallback_tutor_response(self, message: str) -> str:
        message_lower = message.lower()
        if "qué" in message_lower or "que es" in message_lower or "explica" in message_lower:
            return (
                "Ahora mismo estoy en modo limitado y no quiero darte una explicación a medias. "
                "Cuéntame qué parte exacta te hace ruido: ¿el término en sí, un ejemplo que no "
                "cuadra, o un código que no hace lo que esperabas? Con ese detalle te respondo "
                "algo que de verdad te sirva."
            )
        if "cómo" in message_lower or "como" in message_lower:
            return (
                "Para ayudarte con el 'cómo' necesito ver tu intento. Escríbeme qué hiciste "
                "(aunque esté a medias), qué esperabas que pasara y qué pasó en realidad. "
                "Esa diferencia entre lo esperado y lo ocurrido es casi siempre donde vive "
                "la respuesta."
            )
        if "ayuda" in message_lower:
            return (
                "Aquí estoy. Dime el punto exacto donde te trabaste: el último paso que sí "
                "entendiste y el primero que no. Desde ahí lo desarmamos juntos."
            )
        return (
            "Para responderte algo útil necesito un poco más de precisión: ¿sobre qué concepto "
            "o ejercicio del módulo es tu duda? Si es código, pégalo junto con lo que esperabas "
            "que hiciera."
        )


ai_service = AIService()
