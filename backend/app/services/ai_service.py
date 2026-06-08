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

    def _fallback_tutor_response(self, message: str) -> str:
        message_lower = message.lower()
        if "qué" in message_lower or "que es" in message_lower or "explica" in message_lower:
            return (
                "¡Excelente pregunta! Este concepto es fundamental en tu formación. "
                "Te recomiendo revisar el material del módulo actual con atención. "
                "Si después de revisarlo tienes dudas más específicas, no dudes en preguntar. "
                "Recuerda que la práctica constante es clave para dominar estos conceptos."
            )
        if "cómo" in message_lower or "como" in message_lower:
            return (
                "Para aplicar este concepto, te sugiero seguir estos pasos:\n\n"
                "1. Revisa la teoría en el material del curso\n"
                "2. Observa los ejemplos prácticos proporcionados\n"
                "3. Intenta resolver los ejercicios paso a paso\n"
                "4. Si te trabas, repasa la sección anterior\n\n"
                "¿Quieres que te ayude con algún ejemplo específico?"
            )
        if "ayuda" in message_lower:
            return (
                "¡Claro que sí! Estoy aquí para ayudarte. 😊\n\n"
                "Dime exactamente qué parte del módulo te está costando trabajo y te explicaré "
                "de forma sencilla. También puedo sugerirte recursos adicionales si los necesitas."
            )
        return (
            "Gracias por tu mensaje. Para poder ayudarte mejor, ¿podrías ser más específico "
            "sobre qué tema o concepto del curso te gustaría que te explique? "
            "Puedo ayudarte con teoría, ejemplos prácticos o ejercicios."
        )


ai_service = AIService()
