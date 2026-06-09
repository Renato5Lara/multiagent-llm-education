"""
Unit of Work pattern para consistencia transaccional.

Centraliza commit/rollback y registro de eventos.
Elimina partial commits y asegura atomicidad.

Uso:
    uow = UnitOfWork(SessionLocal)
    try:
        service.do_stuff(uow, ...)
        uow.commit()
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UnitOfWorkError(RuntimeError):
    """Raised when a UoW operation is attempted in an invalid state."""


class UnitOfWork:
    """Unidad de trabajo transaccional.

    - Una sesion SQLAlchemy envuelta
    - Registro de eventos para future outbox
    - Commit centralizado
    - Rollback seguro
    - Savepoints para recuperacion parcial
    - Tracing por request
    """

    def __init__(self, session_factory: Callable[[], Session]):
        self._id = str(uuid.uuid4())[:8]
        self._session_factory = session_factory
        self._session: Session | None = None
        self._events: list = []
        self._committed = False
        self._rolled_back = False
        self._savepoint_stack: list = []

    # ── Lifecycle guards ─────────────────────────────────────────

    def _assert_writable(self, operation: str) -> None:
        """Raise if write operations are not safe."""
        if self._rolled_back:
            raise UnitOfWorkError(
                f"Cannot {operation} on UoW[{self._id}]: already rolled back"
            )

    @property
    def id(self) -> str:
        return self._id

    @property
    def db(self) -> Session:
        """Acceso a la sesion SQLAlchemy subyacente.

        Permite acceso incluso despues de commit/rollback
        para consultas de lectura o limpieza.
        La sesion se crea lazy en el primer acceso.
        """
        if self._session is None:
            logger.debug("UoW[%s]: Creating DB session", self._id)
            self._session = self._session_factory()
        if self._committed:
            logger.debug("UoW[%s]: Accessing db after commit (read)", self._id)
        return self._session

    # ── Savepoint support ────────────────────────────────────────

    def begin_savepoint(self) -> None:
        """Create a nested savepoint for partial rollback recovery.

        Use with savepoint_rollback() to revert only the operations
        performed since this savepoint, without aborting the entire
        transaction.

        Critical for patterns like:
            try:
                db.add(record)
                uow.flush()
            except IntegrityError:
                uow.savepoint_rollback()
                # handle gracefully without losing parent TX
        """
        if self._committed:
            raise UnitOfWorkError(
                f"Cannot begin savepoint on UoW[{self._id}]: already committed"
            )
        self._assert_writable("begin savepoint")
        db = self.db
        nested = db.begin_nested()
        nested.__enter__()
        self._savepoint_stack.append(nested)
        logger.debug("UoW[%s]: Savepoint created (depth=%d)", self._id, len(self._savepoint_stack))

    def savepoint_rollback(self) -> None:
        """Roll back to the most recent savepoint.

        The savepoint is consumed (popped). After this call, the
        parent transaction remains active and usable.
        """
        if self._committed:
            raise UnitOfWorkError(
                f"Cannot rollback savepoint on UoW[{self._id}]: already committed"
            )
        self._assert_writable("rollback savepoint")
        if not self._savepoint_stack:
            raise UnitOfWorkError(
                f"UoW[{self._id}]: no savepoint to roll back"
            )
        nested = self._savepoint_stack.pop()
        try:
            # Use .rollback() to issue ROLLBACK TO SAVEPOINT.
            # Calling nested.__exit__(None, None, None) would attempt a commit,
            # which raises InvalidRequestError if flush() already failed and
            # SQLAlchemy auto-rolled back the nested transaction.
            nested.rollback()
        except Exception as exc:
            logger.warning(
                "UoW[%s]: Savepoint rollback failed (session may already have "
                "auto-rolled-back to savepoint): %s",
                self._id, exc,
            )
            # Do NOT set _rolled_back = True here: SQLAlchemy 2.x auto-rolls
            # back the nested transaction on flush() failure and restores the
            # outer session to pre-savepoint state.  The session is usable.
        logger.debug("UoW[%s]: Savepoint rolled back (depth=%d)", self._id, len(self._savepoint_stack))

    # -- Event Outbox Pattern --

    def add_event(
        self,
        event_type: str,
        aggregate_id: str,
        payload: dict | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ):
        """Registra un evento de dominio en el outbox.

        El evento se persiste en la MISMA transaccion que los datos
        de negocio (mismo session.add()). Si el commit falla,
        el evento tambien se revierte.

        Si no se proporciona correlation_id, se auto-pobla desde el
        PropagationContext activo (distributed tracing). Esto asegura
        que la cadena de causation se mantenga automaticamente.

        Args:
            event_type:  Tipo de evento (ej: 'module.completed')
            aggregate_id: ID de la entidad origen
            payload:     Datos del evento (serializable)
            correlation_id: Para tracing de causa raiz. Auto-poblado
                           desde el contexto de tracing activo si es None.
            causation_id: ID del evento que causo este
        """
        if correlation_id is None:
            try:
                from app.tracing import correlation_engine as _ce
                current = _ce.get_current()
                if current is not None:
                    correlation_id = current.correlation.correlation_id
            except Exception:
                pass

        from app.models.event_outbox import EventOutbox

        if self._committed:
            raise UnitOfWorkError(
                f"Cannot add event on UoW[{self._id}]: already committed"
            )
        self._assert_writable("add event")
        event = EventOutbox(
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=payload or {},
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=causation_id,
        )
        self.db.add(event)
        self._events.append(event)
        logger.debug(
            "UoW[%s]: Event persisted: %s[%s] (id=%s, correlation=%s)",
            self._id, event_type, aggregate_id, event.id, event.correlation_id,
        )
        return event

    @property
    def pending_events(self) -> list:
        return list(self._events)

    def clear_events(self) -> list:
        events = list(self._events)
        self._events.clear()
        return events

    # -- Transaction management --

    def flush(self) -> None:
        """Flush pending changes to DB without committing.

        Useful for getting generated IDs before commit.
        Safe to call after commit (SQLAlchemy auto-starts new TX).
        Raises if called after rollback.
        """
        if self._rolled_back:
            raise UnitOfWorkError(
                f"Cannot flush on UoW[{self._id}]: already rolled back"
            )
        if self._session is not None:
            logger.debug("UoW[%s]: Flushing session", self._id)
            self._session.flush()

    def commit(self) -> None:
        """Commit the transaction atomically.

        All changes accumulated in the session are persisted.
        No partial commits possible.

        Raises UnitOfWorkError if called after rollback.
        Safe to call multiple times — each call commits the current
        transaction. SQLAlchemy auto-starts a new implicit TX after commit.
        """
        self._assert_writable("commit")
        if self._session is None:
            self._committed = True
            logger.debug("UoW[%s]: commit() — no session (marked committed)", self._id)
            return
        try:
            dirty = len(self._session.dirty)
            new = len(self._session.new)
            deleted = len(self._session.deleted)
            logger.info(
                "UoW[%s]: Committing (%d dirty, %d new, %d deleted, %d events)",
                self._id, dirty, new, deleted, len(self._events),
            )
            self._session.commit()
            self._committed = True
            logger.info("UoW[%s]: Commit successful", self._id)
        except Exception as exc:
            logger.error(
                "UoW[%s]: Commit failed: %s", self._id, str(exc), exc_info=True,
            )
            try:
                self._session.rollback()
            except Exception as rb_exc:
                logger.error(
                    "UoW[%s]: Rollback after commit failure also failed: %s",
                    self._id, rb_exc,
                )
            self._rolled_back = True
            raise

    def rollback(self) -> None:
        """Rollback the transaction safely.

        Idempotent: only rolls back if the transaction is active.
        If called after commit, it is a no-op (transaction already finalised).
        Also pops any remaining savepoints.
        """
        if self._rolled_back:
            raise UnitOfWorkError(
                f"Cannot rollback on UoW[{self._id}]: already rolled back"
            )
        if self._committed:
            logger.debug("UoW[%s]: rollback() called after commit (no-op)", self._id)
            return
        if self._session is None:
            self._rolled_back = True
            logger.debug("UoW[%s]: rollback() — no session (marked rolled back)", self._id)
            return
        logger.warning("UoW[%s]: Rolling back (%d pending events)", self._id, len(self._events))
        self._savepoint_stack.clear()
        try:
            self._session.rollback()
        except Exception as exc:
            logger.error("UoW[%s]: Rollback failed: %s", self._id, str(exc))
        self._rolled_back = True
        self._events.clear()

    def close(self) -> None:
        """Close the underlying session."""
        if self._session is not None:
            logger.debug("UoW[%s]: Closing session", self._id)
            try:
                self._session.close()
            except Exception as exc:
                logger.warning(
                    "UoW[%s]: Error closing session: %s", self._id, str(exc),
                )
            self._session = None

    @property
    def is_active(self) -> bool:
        """True if the transaction is active and can be committed.

        A UoW with no session yet (lazy creation) is considered active.
        """
        return not self._committed and not self._rolled_back

    # -- Context manager support --

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Guard against double-rollback: commit() already rolls back internally
        # on failure and sets _rolled_back=True, which would cause rollback()
        # to raise UnitOfWorkError and shadow the original exception.
        if exc_type is not None and self.is_active:
            self.rollback()
        self.close()

    def __repr__(self) -> str:
        return (
            f"<UnitOfWork[{self._id}] "
            f"session={'open' if self._session is not None else 'none'} "
            f"committed={self._committed} "
            f"rolled_back={self._rolled_back} "
            f"savepoints={len(self._savepoint_stack)} "
            f"events={len(self._events)}>"
        )


class AsyncUnitOfWorkError(RuntimeError):
    """Raised when an async UoW operation is attempted in an invalid state."""


class AsyncUnitOfWork:
    """Async version of UnitOfWork for use with AsyncSession.

    Same transaction semantics as UnitOfWork but with async commit/rollback/flush.
    Critical for DB-002: eliminates event-loop blocking from sync Session calls.

    Usage:
        uow = AsyncUnitOfWork(AsyncSessionLocal)
        async with uow:
            ...
            await uow.commit()
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self._id = str(uuid.uuid4())[:8]
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._events: list = []
        self._committed = False
        self._rolled_back = False
        self._savepoint_stack: list = []

    # ── Lifecycle guards ─────────────────────────────────────────

    def _assert_writable(self, operation: str) -> None:
        if self._rolled_back:
            raise AsyncUnitOfWorkError(
                f"Cannot {operation} on AsyncUoW[{self._id}]: already rolled back"
            )

    @property
    def id(self) -> str:
        return self._id

    @property
    def db(self) -> AsyncSession:
        if self._session is None:
            logger.debug("AsyncUoW[%s]: Creating DB session", self._id)
            self._session = self._session_factory()
        if self._committed:
            logger.debug("AsyncUoW[%s]: Accessing db after commit (read)", self._id)
        return self._session

    # ── Savepoint support ────────────────────────────────────────

    async def begin_savepoint(self) -> None:
        if self._committed:
            raise AsyncUnitOfWorkError(
                f"Cannot begin savepoint on AsyncUoW[{self._id}]: already committed"
            )
        self._assert_writable("begin savepoint")
        db = self.db
        nested = await db.begin_nested()
        await nested.__aenter__()
        self._savepoint_stack.append(nested)
        logger.debug("AsyncUoW[%s]: Savepoint created (depth=%d)", self._id, len(self._savepoint_stack))

    async def savepoint_rollback(self) -> None:
        if self._committed:
            raise AsyncUnitOfWorkError(
                f"Cannot rollback savepoint on AsyncUoW[{self._id}]: already committed"
            )
        self._assert_writable("rollback savepoint")
        if not self._savepoint_stack:
            raise AsyncUnitOfWorkError(
                f"AsyncUoW[{self._id}]: no savepoint to roll back"
            )
        nested = self._savepoint_stack.pop()
        try:
            # Use .rollback() to issue ROLLBACK TO SAVEPOINT.
            # Calling nested.__aexit__(None, None, None) would attempt a commit,
            # which raises InvalidRequestError if flush() already failed and
            # SQLAlchemy auto-rolled back the nested transaction.
            await nested.rollback()
        except Exception as exc:
            logger.warning(
                "AsyncUoW[%s]: Savepoint rollback failed (session may already have "
                "auto-rolled-back to savepoint): %s",
                self._id, exc,
            )
            # Do NOT set _rolled_back = True: SQLAlchemy 2.x auto-restores the outer
            # session to pre-savepoint state on flush() failure.
        logger.debug("AsyncUoW[%s]: Savepoint rolled back (depth=%d)", self._id, len(self._savepoint_stack))

    # -- Event Outbox Pattern --

    def add_event(
        self,
        event_type: str,
        aggregate_id: str,
        payload: dict | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ):
        if correlation_id is None:
            try:
                from app.tracing import correlation_engine as _ce
                current = _ce.get_current()
                if current is not None:
                    correlation_id = current.correlation.correlation_id
            except Exception:
                pass

        from app.models.event_outbox import EventOutbox

        if self._committed:
            raise AsyncUnitOfWorkError(
                f"Cannot add event on AsyncUoW[{self._id}]: already committed"
            )
        self._assert_writable("add event")
        event = EventOutbox(
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=payload or {},
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=causation_id,
        )
        self.db.add(event)
        self._events.append(event)
        logger.debug(
            "AsyncUoW[%s]: Event persisted: %s[%s] (id=%s, correlation=%s)",
            self._id, event_type, aggregate_id, event.id, event.correlation_id,
        )
        return event

    @property
    def pending_events(self) -> list:
        return list(self._events)

    def clear_events(self) -> list:
        events = list(self._events)
        self._events.clear()
        return events

    # -- Async transaction management --

    async def flush(self) -> None:
        if self._rolled_back:
            raise AsyncUnitOfWorkError(
                f"Cannot flush on AsyncUoW[{self._id}]: already rolled back"
            )
        if self._session is not None:
            logger.debug("AsyncUoW[%s]: Flushing session", self._id)
            await self._session.flush()

    async def commit(self) -> None:
        self._assert_writable("commit")
        if self._session is None:
            self._committed = True
            logger.debug("AsyncUoW[%s]: commit() — no session (marked committed)", self._id)
            return
        try:
            dirty = len(self._session.dirty)
            new = len(self._session.new)
            deleted = len(self._session.deleted)
            logger.info(
                "AsyncUoW[%s]: Committing (%d dirty, %d new, %d deleted, %d events)",
                self._id, dirty, new, deleted, len(self._events),
            )
            await self._session.commit()
            self._committed = True
            logger.info("AsyncUoW[%s]: Commit successful", self._id)
        except Exception as exc:
            logger.error(
                "AsyncUoW[%s]: Commit failed: %s", self._id, str(exc), exc_info=True,
            )
            try:
                await self._session.rollback()
            except Exception as rb_exc:
                logger.error(
                    "AsyncUoW[%s]: Rollback after commit failure also failed: %s",
                    self._id, rb_exc,
                )
            self._rolled_back = True
            raise

    async def rollback(self) -> None:
        if self._rolled_back:
            raise AsyncUnitOfWorkError(
                f"Cannot rollback on AsyncUoW[{self._id}]: already rolled back"
            )
        if self._committed:
            logger.debug("AsyncUoW[%s]: rollback() called after commit (no-op)", self._id)
            return
        if self._session is None:
            self._rolled_back = True
            logger.debug("AsyncUoW[%s]: rollback() — no session (marked rolled back)", self._id)
            return
        logger.warning("AsyncUoW[%s]: Rolling back (%d pending events)", self._id, len(self._events))
        self._savepoint_stack.clear()
        try:
            await self._session.rollback()
        except Exception as exc:
            logger.error("AsyncUoW[%s]: Rollback failed: %s", self._id, str(exc))
        self._rolled_back = True
        self._events.clear()

    async def close(self) -> None:
        if self._session is not None:
            logger.debug("AsyncUoW[%s]: Closing session", self._id)
            try:
                await self._session.close()
            except Exception as exc:
                logger.warning(
                    "AsyncUoW[%s]: Error closing session: %s", self._id, str(exc),
                )
            self._session = None

    @property
    def is_active(self) -> bool:
        return not self._committed and not self._rolled_back

    # -- Async context manager support --

    async def __aenter__(self) -> "AsyncUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # Guard against double-rollback: commit() already rolls back internally
        # on failure and sets _rolled_back=True, which would cause rollback()
        # to raise AsyncUnitOfWorkError and shadow the original exception.
        if exc_type is not None and self.is_active:
            await self.rollback()
        await self.close()

    def __repr__(self) -> str:
        return (
            f"<AsyncUnitOfWork[{self._id}] "
            f"session={'open' if self._session is not None else 'none'} "
            f"committed={self._committed} "
            f"rolled_back={self._rolled_back} "
            f"savepoints={len(self._savepoint_stack)} "
            f"events={len(self._events)}>"
        )
