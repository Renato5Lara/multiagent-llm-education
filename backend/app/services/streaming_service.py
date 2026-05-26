import json
import logging
import asyncio
from typing import AsyncGenerator, Optional

import os

logger = logging.getLogger(__name__)


class StreamingService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.use_openai = bool(self.api_key)

    async def stream_tutor_response(
        self,
        message: str,
        system_prompt: str,
        context: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        if not self.use_openai:
            yield f"data: {json.dumps({'type': 'text', 'content': self._fallback_response(message)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)

            messages = [
                {"role": "system", "content": system_prompt},
            ]

            if context and context.get("conversation_history"):
                for msg in context["conversation_history"][-6:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    })

            messages.append({"role": "user", "content": self._build_contextual_message(message, context)})

            stream = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True,
                timeout=30,
            )

            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    def _build_contextual_message(self, message: str, context: Optional[dict] = None) -> str:
        parts = [f"Mensaje del estudiante: {message}"]

        if context:
            if context.get("weaknesses"):
                parts.append(f"\nDebilidades conocidas: {', '.join(w['topic'] for w in context['weaknesses'][:3])}")
            if context.get("strengths"):
                parts.append(f"\nFortalezas conocidas: {', '.join(s['topic'] for s in context['strengths'][:3])}")
            if context.get("course_context"):
                cc = context["course_context"]
                parts.append(f"\nContexto del curso: {cc.get('course_name', '')} - Progreso: {cc.get('progress_percentage', 0)}%")
            if context.get("risk_status"):
                parts.append(f"\nRiesgo académico: {context['risk_status']}")

        return "\n".join(parts)

    def _fallback_response(self, message: str) -> str:
        msg_lower = message.lower()
        if "qué" in msg_lower or "que es" in msg_lower or "explica" in msg_lower:
            return "¡Excelente pregunta! Este concepto es fundamental. Te recomiendo revisar el material del módulo actual con atención. ¿Hay algo específico que te gustaría que te explique con más detalle?"
        return "Gracias por tu mensaje. Para ayudarte mejor, ¿podrías ser más específico sobre qué tema te gustaría que te explique? Puedo ayudarte con teoría, ejemplos prácticos o ejercicios."


streaming_service = StreamingService()
