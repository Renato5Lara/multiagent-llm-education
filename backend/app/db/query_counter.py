import logging
import re
import threading
from collections import defaultdict
from contextvars import ContextVar
from typing import Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger("query_counter")

_request_query_log: ContextVar[Optional[list[dict]]] = ContextVar("_request_query_log", default=None)
_request_n1_warnings: ContextVar[list[str]] = ContextVar("_request_n1_warnings", default=[])


class QueryCounter:
    """Tracks SQL queries per request and detects N+1 patterns.

    Usage:
        counter = QueryCounter()
        counter.attach(engine)
        counter.start()
        # ... run queries ...
        print(counter.count)  # total queries
        print(counter.n1_warnings)  # potential N+1 patterns
        counter.stop()
        counter.detach(engine)
    """

    def __init__(self):
        self.count = 0
        self._queries: list[dict] = []
        self._n1_warnings: list[str] = []
        self._active = False
        self._listen_args: Optional[tuple] = None

    def _before_execute(self, conn, clause, multiparams, params, execution_options):
        if not self._active:
            return
        self.count += 1
        sql = str(clause)
        self._queries.append({
            "sql": sql[:500],
            "params": params,
        })

    def _after_execute(self, conn, clause, multiparams, params, execution_options, result):
        pass

    def attach(self, engine: Engine):
        event.listen(engine, "before_execute", self._before_execute, retval=False)

    def detach(self, engine: Engine):
        try:
            event.remove(engine, "before_execute", self._before_execute)
        except Exception:
            pass

    def start(self):
        self.count = 0
        self._queries = []
        self._n1_warnings = []
        self._active = True
        _request_query_log.set(self._queries)
        _request_n1_warnings.set(self._n1_warnings)

    def stop(self):
        self._active = False
        self._detect_n1_patterns()

    def reset(self):
        self.count = 0
        self._queries = []
        self._n1_warnings = []

    def _detect_n1_patterns(self):
        """Analyze query log for potential N+1 patterns.

        Heuristic: if the same table is queried >3 times in a loop-like
        pattern (alternating with other queries or in sequence), flag it.
        """
        if len(self._queries) < 4:
            return

        table_counts: dict[str, int] = defaultdict(int)
        for q in self._queries:
            table = self._extract_table(q["sql"])
            if table:
                table_counts[table] += 1

        for table, cnt in table_counts.items():
            if cnt > 3:
                msg = f"Potential N+1: {table} queried {cnt} times"
                self._n1_warnings.append(msg)
                logger.warning("[N+1 DETECTION] %s", msg)

    @staticmethod
    def _extract_table(sql: str) -> Optional[str]:
        m = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'\bUPDATE\s+(\w+)', sql, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'\bINTO\s+(\w+)', sql, re.IGNORECASE)
        if m:
            return m.group(1)
        return None


def get_request_query_log() -> list[dict]:
    log = _request_query_log.get()
    return log or []


def get_n1_warnings() -> list[str]:
    return _request_n1_warnings.get() or []


_counter_instance: Optional[QueryCounter] = None


def get_global_counter() -> Optional[QueryCounter]:
    return _counter_instance


def install_query_counter(engine: Engine) -> QueryCounter:
    global _counter_instance
    counter = QueryCounter()
    counter.attach(engine)
    _counter_instance = counter
    logger.info("QueryCounter installed on engine %s", engine)
    return counter
