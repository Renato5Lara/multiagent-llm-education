"""
Tests para el servicio de streaming SSE del tutor.
"""

import json
import pytest


class TestFallbackResponse:
    def test_explanation_fallback(self):
        from app.services.streaming_service import streaming_service
        resp = streaming_service._fallback_response("¿Qué es un algoritmo?")
        assert "excelente" in resp.lower() or "fundamental" in resp.lower()

    def test_generic_fallback(self):
        from app.services.streaming_service import streaming_service
        resp = streaming_service._fallback_response("hola")
        assert "específico" in resp.lower() or "ayudarte" in resp.lower()


class TestBuildContextualMessage:
    def test_no_context(self):
        from app.services.streaming_service import streaming_service
        msg = streaming_service._build_contextual_message("hello")
        assert "Mensaje del estudiante: hello" in msg

    def test_with_weaknesses(self):
        from app.services.streaming_service import streaming_service
        context = {"weaknesses": [{"topic": "recursion"}, {"topic": "sorting"}]}
        msg = streaming_service._build_contextual_message("help", context)
        assert "recursion" in msg
        assert "sorting" in msg

    def test_with_strengths(self):
        from app.services.streaming_service import streaming_service
        context = {"strengths": [{"topic": "python"}, {"topic": "loops"}]}
        msg = streaming_service._build_contextual_message("help", context)
        assert "python" in msg
        assert "loops" in msg

    def test_with_course_context(self):
        from app.services.streaming_service import streaming_service
        context = {"course_context": {"course_name": "Algorithms", "progress_percentage": 60}}
        msg = streaming_service._build_contextual_message("help", context)
        assert "Algorithms" in msg
        assert "60%" in msg

    def test_with_risk_status(self):
        from app.services.streaming_service import streaming_service
        context = {"risk_status": "medio"}
        msg = streaming_service._build_contextual_message("help", context)
        assert "medio" in msg

    def test_with_all_context(self):
        from app.services.streaming_service import streaming_service
        context = {
            "weaknesses": [{"topic": "w1"}],
            "strengths": [{"topic": "s1"}],
            "course_context": {"course_name": "C1", "progress_percentage": 50},
            "risk_status": "bajo",
        }
        msg = streaming_service._build_contextual_message("help", context)
        assert "w1" in msg
        assert "s1" in msg
        assert "C1" in msg
        assert "50%" in msg
        assert "bajo" in msg


class TestStreamTutorResponse:
    @pytest.mark.asyncio
    async def test_fallback_stream(self):
        from app.services.streaming_service import streaming_service
        streaming_service.use_openai = False
        events = []
        async for event in streaming_service.stream_tutor_response(
            message="¿Qué es sorting?",
            system_prompt="Eres un tutor.",
        ):
            events.append(event)
        assert len(events) >= 2
        first = json.loads(events[0].replace("data: ", "").strip())
        assert first["type"] == "text"
        last = json.loads(events[-1].replace("data: ", "").strip())
        assert last["type"] == "done"

    @pytest.mark.asyncio
    async def test_fallback_stream_with_context(self):
        from app.services.streaming_service import streaming_service
        streaming_service.use_openai = False
        context = {"weaknesses": [{"topic": "recursion"}]}
        events = []
        async for event in streaming_service.stream_tutor_response(
            message="help",
            system_prompt="Eres un tutor.",
            context=context,
        ):
            events.append(event)
        assert len(events) >= 2
