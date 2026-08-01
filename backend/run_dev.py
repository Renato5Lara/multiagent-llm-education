"""Lanzador de desarrollo para Windows.

psycopg (v3) en modo async exige un event loop basado en selectores; el
ProactorEventLoop rompe cualquier query del async engine (app/db/session.py,
usado por las cuatro surfaces de solo lectura de app/api/routes/runtime.py:
traza/estado/memoria/replay).

No basta con fijar `asyncio.set_event_loop_policy(...)`: uvicorn en Windows
ignora la política global y construye el loop con una factory propia
codificada, `asyncio.ProactorEventLoop`, sin excepción salvo
`use_subprocess=True` (uvicorn/loops/asyncio.py::asyncio_loop_factory) — el
`loop="auto"` por defecto termina ahí porque uvloop no existe en Windows.
La única forma soportada de cambiarlo es pasar la propia factory como
import-string (`Config.get_loop_factory`, uvicorn/config.py) en vez de uno
de los cuatro presets ("none"/"auto"/"asyncio"/"uvloop").

En producción (Linux, Procfile) esto no aplica — ProactorEventLoop no
existe fuera de Windows — por eso el Procfile sigue usando
`uvicorn app.main:app` directo con el loop "auto" (ahí resuelve a uvloop).
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, loop="asyncio:SelectorEventLoop")
