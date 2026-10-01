# Reproducibilidad del PoC `adaptation_swarm` (procedimiento desde cero)

Todo se ejecuta desde `backend/` salvo indicación. Versiones de Python (no confundirlas):
- **Backend en contenedor** (`backend/Dockerfile`): `python:3.12-slim`. Es el runtime de despliegue del backend.
- **Sandbox de Python** (`backend/app/sandbox/docker/Dockerfile`): `python:3.11-slim` (ejecuta el código de los artefactos; no comparte intérprete con el backend).
- **Entorno local con el que se produjeron `corrida-poc-1/2`, la biblioteca y las cargas:** Python **3.14.7** (Fedora), podman 5.8.7, Node 22, g++ 16, Google Chrome 151, 8 CPU / ~7 GB
  (registrado en `06_entorno/environment.json` del paquete de evidencia). **3.14 no es un requisito del proyecto**; tampoco se ha verificado que las
  dependencias fijadas (`numpy==2.5.3`, `scipy==1.18.1`, …) se instalen y pasen las pruebas bajo 3.12: hasta comprobarlo, la reproducción exacta de los números publicados se
  garantiza con el entorno local descrito.
- Se requiere además: podman ≥ 5 (o docker), Node ≥ 18, Google Chrome/Chromium.

Lo que **no** es determinista y cómo se controla: el LLM/TTS (por eso la biblioteca M1 se genera **una vez**, se versiona por hash y
el PSO solo la lee); la latencia de red del proveedor (CostT usa tiempos **congelados** en el manifiesto).

## 1. Servicios
```
podman-compose up -d postgres redis        # raíz del repo (docker compose up -d igual)
podman build -t upao-python-repl-sandbox:latest app/sandbox/docker       # sandbox de Python (D2 / AG2)
podman build -t upao-cpp-sandbox:latest tools/cpp_sandbox                # sandbox de C++   (AG2)
export SWARM_SANDBOX_BIN=podman            # por defecto ya es podman; usar docker si corresponde
```
## 2. Dependencias
```
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-loadtest.txt
(cd tools/mermaid_render && PUPPETEER_SKIP_DOWNLOAD=1 npm ci)        # render real de Mermaid (usa el Chrome del sistema; MERMAID_CHROME)
export OPENAI_API_KEY=...                  # solo para GENERAR/EXTENDER la biblioteca; ejecutar el PoC sobre una biblioteca existente no llama a OpenAI
```
> Usar siempre `python -m pip` y `python -m alembic` (los ejecutables sueltos de `.venv/bin/` —`pip`, `alembic`— pueden llevar un shebang que apunta a otra copia del repo y usar otro intérprete).
> `scripts/repro_db_bootstrap.sh` ya invoca `.venv/bin/python -m alembic`.
## 3. Base de datos (cadena Alembic completa desde una base vacía)
```
createdb upao_mas_edu     # o crear la base vacía por otro medio
bash scripts/repro_db_bootstrap.sh "postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu"
```
El script es necesario porque la migración **preexistente** `d6e7f8a9b0c1` (datos: IS301 → 8 módulos) presupone el curso IS301 y 4 objetivos
legados con ids fijos y genera al azar los 32 `concepts.id`. `bootstrap_preconditions` crea esas precondiciones mínimas y `concept_ids restore`
realinea los ids con `datasets/synthetic_profiles/concepts-v1.json` (dataset y biblioteca las referencian). Verificado: 61 tablas, head `b2f4c9d10a02`.
Cadena: `… → d6e7f8a9b0c1 → e7f8a9b0c1d2 → f101101bc75d → 928a10b002db → a17c0de5a001 → b2f4c9d10a02`. Head: `python -m alembic heads` (debe dar una sola cabeza, `b2f4c9d10a02`).
**Estado de versionado a 2026-09-24:** `f101101bc75d` y `928a10b002db` (CMG) y las dos del PoC siguen **sin versionar** en Git (ver el plan de commits en la auditoría pre-commit); un clon del último commit actual no las contiene.
## 4. Datos versionados
```
python -m adaptation_swarm.multimodal.verify                          # hash del manifiesto + sha256 de TODOS los artefactos + cadenas + cobertura
python -m adaptation_swarm.profiles.build_dataset                     # (opcional) regenera el dataset: mismo seed ⇒ mismo sha256 (manifest-v1.json)
```
La biblioteca (`datasets/adaptation_library/lib-vN-hash`) y el dataset (`datasets/synthetic_profiles/`) son **artefactos versionados por hash**: no se regeneran
para reproducir resultados. Para ampliarla: `python -m adaptation_swarm.multimodal.extend --base lib-vN-hash` (crea una versión NUEVA; nunca modifica las selladas).
## 5. Ejecución
```
python -m adaptation_swarm.run_slice                                   # vertical slice (Visual-Dominant × Bucles)
python -m pytest tests/adaptation_swarm -q                             # pruebas propias (Redis, Postgres, sandbox, Chrome; algunas llaman a OpenAI)
python -m adaptation_swarm.run_experiment --sweep                      # sensibilidad pre-registrada
python -m adaptation_swarm.run_experiment --run-label corrida-poc-N --library-version lib-vN-hash
python -m adaptation_swarm.analysis.f1_audit  --run-label corrida-poc-N   # diagnóstico de F1 (solo lectura)
python -m adaptation_swarm.analysis.pso_audit --run-label corrida-poc-N   # diagnóstico del PSO (solo lectura)
```
La corrida es **determinista** para (semilla, `config_hash`, `library_version`, dataset): mismas trayectorias y mismo `g_best` bit a bit.
## 6. Carga (Locust y JMeter; escenarios 1/10/25/50/100)
```
SWARM_API_KEY=k SWARM_API_RUN_LABEL=<run creado con start_run> python -m uvicorn app.main:app --port 8765 --workers 4
SWARM_API_KEY=k SCENARIO_LABEL=w4 BACKEND_PID=<pid> bash loadtest/run_scenarios.sh http://localhost:8765 30
SWARM_API_KEY=k JMETER_BIN=<.../bin/jmeter> SCENARIO_LABEL=w4 BACKEND_PID=<pid> bash loadtest/run_jmeter_scenarios.sh http://localhost:8765 30
```
Declarar siempre en el reporte: nº de workers, `SWARM_API_PERSIST`, versión de biblioteca, hardware, y que el generador de carga comparte host con el servidor.
## 7. Evaluación humana (pendiente de recolección)
`python -m adaptation_swarm.sus_cli status` → mientras haya < 10 evaluadores reales muestra **PENDIENTE DE RECOLECCIÓN HUMANA** (SUS y validación del gold).

## 8. Variables de entorno (defaults en `adaptation_swarm/config.py`, `api/router.py`, `multimodal/render.py`, `app/core/config.py`)

**Obligatorias** (según lo que se ejecute):

| Variable | Cuándo | Nota |
|---|---|---|
| `DATABASE_URL` | Alembic, `run_experiment` con persistencia, pruebas de integración, endpoint con persistencia | default de `app/core/config.py`: `postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu`; el bootstrap la recibe como argumento y la exporta |
| `OPENAI_API_KEY` | **solo** para generar/extender la biblioteca (LLM y TTS) y para las pruebas que llaman a OpenAI | sin valor por defecto (cadena vacía → funciones de generación fallan). Ejecutar el PoC sobre una biblioteca existente no llama a OpenAI |
| `SWARM_API_KEY` | solo para el endpoint `POST /api/adaptation` | sin valor: el endpoint responde 503 (seguro por defecto) |

**Opcionales** (con su valor por defecto):

| Variable | Default | Efecto |
|---|---|---|
| `SWARM_REDIS_URL` | `redis://localhost:6379/0` | Redis es obligatorio como servicio (DEC-05), la variable solo cambia su dirección |
| `SWARM_REDIS_PREFIX` | `swarm:` | prefijo de claves/streams |
| `SWARM_REDIS_MAX_CONNECTIONS` | `1024` | pool de conexiones (con menos, aparece «Too many connections» bajo carga) |
| `SWARM_STREAM_MAXLEN` | `5000` | recorte de streams |
| `SWARM_SEEN_TTL_SECONDS` | `3600` | TTL de la marca de idempotencia |
| `SWARM_LOG_TTL_SECONDS` | `86400` | TTL del log de auditoría en Redis |
| `SWARM_REQUEST_TIMEOUT` | `30` (s) | espera por respuesta de un agente |
| `SWARM_LIBRARY_ROOT` | `<repo>/datasets/adaptation_library` | raíz de la biblioteca |
| `SWARM_SANDBOX_BIN` | `podman` | motor de contenedores del sandbox de C++ (imagen `upao-cpp-sandbox:latest`) |
| `SWARM_API_PERSIST` | `1` | `0` desactiva la persistencia del endpoint (declararlo en toda medición) |
| `SWARM_API_RUN_LABEL` | sin valor | `run_label` con el que el endpoint persiste sus ciclos (la carga usa un run creado con `start_run`) |
| `MERMAID_CHROME` | `/usr/bin/google-chrome` | ruta del Chrome/Chromium para renderizar Mermaid → SVG |
| `SCENARIO_LABEL`, `BACKEND_PID`, `JMETER_BIN` | — | solo scripts de carga (`loadtest/`) |

## 9. Qué NO está autocontenido en un clon limpio (Decisión C — estrategia D híbrida cerrada; mecanismo externo del audio PENDIENTE)

Estrategia (DECISION-CLOSURE §14): **en Git** irán los manifiestos de las 10 versiones y todos los artefactos **no-audio** (`.py`, `.cpp`, `.mmd`, `.txt`, `.svg`); **fuera de Git** el audio (mp3) y `_tts_cache/`
(`.gitignore` ya lo refleja). Los manifiestos conservan el sha256 de cada mp3. Estado a 2026-09-24: la biblioteca **aún no se ha commiteado** (nada de ella está en Git).

- **Un clon (cuando la biblioteca esté commiteada) traerá manifiestos y artefactos no-audio, pero NO el audio.** Verificar resultados congelados no requiere la biblioteca; **volver a ejecutar ciclos exige audio y SVG presentes**
  (la validación del paquete es obligatoria al entregar). Para reproducir las corridas hacen falta como mínimo `lib-v5-9ae9ffdd` (`corrida-poc-1`) y `lib-v9-a0231e9b` (`corrida-poc-2`); la última versión es `lib-v10-5dd83cd4`.
- **El mecanismo de recuperación del audio está PENDIENTE** (no se ha elegido proveedor, ni Git LFS, ni almacenamiento institucional). Hoy el audio existe en el disco del propietario y en una **copia sellada local**
  (`Biblioteca sellada 2026-09-24/`, fuera del repo; `SHA256SUMS`; **no** es preservación institucional).
- **Herramientas:** `python -m adaptation_swarm.tools.library_inventory [--check [--require-complete]] [--out DIR]` (presencia/integridad por versión; «ausente» ≠ «hash incorrecto»);
  `python -m adaptation_swarm.multimodal.verify lib-vN-hash` (exit 0 íntegra · 1 hash incorrecto · 2 solo faltan archivos); `python -m adaptation_swarm.tools.seal_audio --dest DIR | --verify DIR`.
- **Pruebas:** las que dependen físicamente del audio están marcadas `requires_library_audio` (`tests/adaptation_swarm/LIBRARY_TESTS.md`): con la biblioteca completa se ejecutan; si faltan archivos se omiten con la razón explícita;
  `SWARM_REQUIRE_LIBRARY=1` las hace fallar en ausencia; un archivo presente con hash incorrecto siempre hace fallar.
- **Base de datos:** las pruebas `test_corrida_poc_1_preserved` y la exportación del paquete de evidencia leen filas reales de `swarm_runs`/`swarm_cycles` (`corrida-poc-1/2`); una base creada con el bootstrap está vacía de corridas.
  Las corridas se reconstruyen con `run_experiment` sobre la biblioteca correspondiente o se comparan con los JSON congelados (`experiments/results/adaptation_swarm_corrida-poc-*.json`).
- **Servicios y binarios externos al repositorio:** Postgres, Redis, podman, Node, Chrome, JMeter (`JMETER_BIN`) y las imágenes de sandbox (`podman build` de §1).
- Los resultados de las corridas registran `git.dirty = true` sobre `d31d29c`: el commit no describe por sí solo el árbol que las produjo; la identidad experimental es (semilla, `config_hash`, `library_version`, dataset) + el paquete de evidencia con `MANIFEST.sha256`.
