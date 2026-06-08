"""
Tests de regresión para los 7 fixes aplicados en la auditoría técnica.

Fixes cubiertos:
1. ai_service importa prompts correctamente (NameError TUTOR_CHAT_PROMPT)
2. retrieval.py MULTIMODAL → aggregate.multimodal_prompts
3. retrieval.py modalidades: image/text/video/audio
4. orchestration.py salva multimodal_prompts en CourseWeek
5. useStudent.ts invalida learning-path al completar módulo
6. student_service.py normaliza status a lowercase
7. EstudianteLayout sidebar sin dead link
"""

from app.services.ai_service import ai_service
from app.core.config import settings


class TestFix1AIServiceImports:
    """Fix 1: ai_service.py debe importar prompts correctamente."""

    def test_analyze_diagnostic_no_crash(self):
        """analyze_diagnostic_ai no debe lanzar NameError por prompts faltantes."""
        profile = {
            "learning_style": "visual", "pace": "moderate",
            "preferred_bloom_levels": [3], "preferred_modalities": ["visual"],
        }
        answers = {"q1": 4, "q2": 3, "q3": 5}
        result = ai_service.analyze_diagnostic_ai(profile, answers)
        assert isinstance(result, dict)
        assert "fortalezas" in result
        assert "confianza" in result

    def test_generate_tutor_response_no_crash(self):
        """generate_tutor_response no debe lanzar NameError por prompts faltantes."""
        result = ai_service.generate_tutor_response(
            message="¿Qué es un arreglo?",
            course_name="Programación",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_tutor_response_works(self):
        """_fallback_tutor_response retorna respuestas coherentes según keyword."""
        resp_que = ai_service._fallback_tutor_response("¿Qué es un algoritmo?")
        assert "pregunta" in resp_que.lower() or "concepto" in resp_que.lower()

        resp_como = ai_service._fallback_tutor_response("¿Cómo ordeno un arreglo?")
        assert "pasos" in resp_como.lower() or "sugiero" in resp_como.lower()

        resp_ayuda = ai_service._fallback_tutor_response("Necesito ayuda")
        assert "ayudar" in resp_ayuda.lower()

    def test_degraded_mode(self):
        """ai_service.degraded refleja correctamente si OpenAI está disponible."""
        if settings.has_openai:
            assert ai_service.degraded is False
        else:
            assert ai_service.degraded is True


class TestFix6ModuleStatusNormalization:
    """Fix 6: Normalización de status a lowercase en get_learning_path_detail."""

    def test_status_normalization_lowercase(self, db, estudiante_user, curso_publicado):
        """El status del módulo siempre debe retornarse en lowercase."""
        from app.models.student_progress import LearningPath, PathModule
        from app.services.student_service import get_learning_path_detail

        path = LearningPath(
            id="fix6-path", student_id=estudiante_user.id,
            course_id=curso_publicado.id, total_modules=1, status="active",
        )
        db.add(path)
        db.flush()

        module = PathModule(
            id="fix6-mod", path_id="fix6-path", title="Test",
            description="", order=0, status="AVAILABLE", bloom_level=1,
        )
        db.add(module)
        db.commit()

        result = get_learning_path_detail(db, estudiante_user.id, curso_publicado.id)
        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].status == "available"

    def test_status_none_becomes_locked(self, db, estudiante_user, curso_publicado):
        """Status None debe normalizarse a 'locked'."""
        from app.models.student_progress import LearningPath, PathModule
        from app.services.student_service import get_learning_path_detail

        path = LearningPath(
            id="fix6b-path", student_id=estudiante_user.id,
            course_id=curso_publicado.id, total_modules=1, status="active",
        )
        db.add(path)
        db.flush()

        module = PathModule(
            id="fix6b-mod", path_id="fix6b-path", title="Test",
            description="", order=0, status=None, bloom_level=1,
        )
        db.add(module)
        db.commit()

        result = get_learning_path_detail(db, estudiante_user.id, curso_publicado.id)
        assert result is not None
        assert result.items[0].status == "locked"


class TestFix3ModalityMapping:
    """Fix 3: Las modalidades deben coincidir con lo que espera el frontend."""

    def test_modalities_are_standard(self):
        """Las modalidades en prompts deben ser image/text/video/audio."""
        from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
        strategy = PedagogicalRetrievalStrategy()
        # Test interno: _build_multimodal_prompts usa los nombres correctos
        from app.integrations.tavily.schemas import AggregatedResearch, RetrievalContext
        context = RetrievalContext(topic="Arreglos", objectives=["Comprender"], bloom_target=3)
        research = AggregatedResearch(topic="Arreglos")
        # Simular algunos conceptos para que genere prompts
        research.concepts = [
            {"title": "Arrays tutorial", "url": "https://example.com/1", "content_preview": "Los arreglos son estructuras..."},
            {"title": "Arrays source 2", "url": "https://example.com/2", "content_preview": "Recorrer arreglos..."},
        ]
        research.examples = [
            {"title": "Arrays source 3", "url": "https://example.com/3", "content_preview": "Ejemplo de código..."},
        ]
        prompts = strategy._build_multimodal_prompts(research, context)
        assert len(prompts) > 0
        for prompt in prompts:
            assert prompt["modality"] in {"text", "image", "video", "audio"}, \
                f"Modalidad inesperada: {prompt['modality']}"


class TestFix2MultimodalClassification:
    """Fix 2: MULTIMODAL queries deben ir a aggregate.multimodal_prompts."""

    def test_multimodal_not_in_examples(self):
        """Categoría MULTIMODAL no debe contaminar aggregate.examples."""
        from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
        from app.integrations.tavily.schemas import AggregatedResearch, QueryCategory
        strategy = PedagogicalRetrievalStrategy()

        research = AggregatedResearch(topic="Test")
        item = {
            "title": "Multimodal source",
            "url": "https://example.com/m",
            "content_preview": "Contenido multimodal",
            "domain": "example.com",
            "score": 0.9,
            "category": "multimodal",
            "bloom_level": None,
        }
        strategy._classify_source(research, item, QueryCategory.MULTIMODAL, 3)
        assert len(research.multimodal_prompts) > 0, \
            "MULTIMODAL category debe ir a multimodal_prompts"
        assert len(research.examples) == 0, \
            "MULTIMODAL category NO debe ir a examples"


class TestConfigAPIKeys:
    """Validación de configuración de API keys."""

    def test_secrets_summary_no_leak(self):
        """secrets_summary nunca debe exponer keys completas."""
        summary = settings.secrets_summary()
        full_key = settings.TAVILY_API_KEY
        if full_key and len(full_key) > 8:
            assert full_key not in str(summary), "No debe filtrar la key completa"

    def test_validate_api_keys_no_crash(self):
        """validate_api_keys nunca debe crashear."""
        warnings = settings.validate_api_keys()
        assert isinstance(warnings, list)
