"""IT-06 -- Integracion ResearchAgent <-> Memoria Compartida (SharedMemoryStore).

Componentes reales: app/services/research_agent.py (ResearchAgent, escritor
via _publish_memory) y app/memory/shared_memory.py (SharedMemoryStore,
lector via query_sync), colaborando a traves de la tabla real
shared_memory_records en PostgreSQL -- dentro del mismo proceso pero con
una sesion SQLAlchemy real (app/db/session.SessionLocal), no SQLite.

No se invoca via HTTP porque ninguna ruta expone ResearchAgent.analyze()
directamente (confirmado en la auditoria de Fase 1); se invoca el
componente real de servicio, igual que lo haria el orquestador semanal
real (weekly_pedagogy_service), preservando el mismo contrato.
"""
import uuid

from app.db.session import SessionLocal
from app.memory.shared_memory import memory_store_from_session
from app.services.research_agent import ResearchAgent


def test_researchagent_publica_y_shared_memory_store_lee_la_misma_fila_real():
    db = SessionLocal()
    try:
        student_id = f"it06-{uuid.uuid4().hex[:8]}"
        store = memory_store_from_session(db)
        agent = ResearchAgent(shared_memory_store=store)

        state = {
            "topic": "Bucles for en Python",
            "objectives": ["Comprender la sintaxis de un bucle for", "Identificar casos de uso"],
            "bloom_target": 3,
            "language": "es",
            "student_id": student_id,
            "module_id": "modulo-it06",
            "cache_only": True,  # evita depender de la disponibilidad de red de Tavily para ESTE caso
        }

        print(f"[IT-06] ResearchAgent.analyze() para student_id={student_id} (via asyncio.run, componente real)")
        import asyncio
        resultado = asyncio.run(agent.analyze(state))
        print(f"[IT-06] memory_ids devueltos por ResearchAgent: {resultado.get('memory_ids')}")
        db.commit()

        assert resultado.get("memory_ids"), "ResearchAgent debio publicar al menos un registro en la memoria compartida"

        print(f"[IT-06] SharedMemoryStore.query_sync(student_id={student_id}) -- lectura por un componente distinto al escritor")
        registros = store.query_sync(student_id=student_id, voter_name="research_agent")
        print(f"[IT-06] registros leidos: {len(registros)}")
        for r in registros:
            print(f"[IT-06]   key={r.key} confidence={r.confidence} voter={r.voter_name}")

        assert len(registros) > 0, "SharedMemoryStore debio leer, desde una consulta independiente, lo que ResearchAgent escribio"
        claves = {r.key for r in registros}
        assert "research:summary" in claves
    finally:
        db.close()
