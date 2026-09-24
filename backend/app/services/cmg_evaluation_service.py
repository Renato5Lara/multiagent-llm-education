"""P1 — CMG Evaluation Service.

Evalúa exclusivamente D1 (adherencia curricular), D2 (corrección
técnica) y D3 (coherencia estructural/terminológica) de un CMG ya
generado. Regla dura de no-circularidad (§14 del encargo, verificada
por `tests/test_cmg_no_contamination.py`): ninguna función de este
módulo lee, recibe ni depende de `dominada`, `items_incorrectos`,
`student_id`, la decisión de Remediar/Orientar, ni la configuración
experimental/control — solo observa `Concept` + `LearningObjective` +
`CMG`. La evidencia que activó el mecanismo (Diagnosticar/Remediar/
Orientar) no puede contaminar la evaluación del contenido generado.

Rol de cada dimensión en la VD (R22→R26, deliberación metodológica
cerrada — documentación técnica, no reemplaza el documento
metodológico de tesis):

- **D1 = dimensión graduada** de la VD — cobertura léxica curricular de
  la explicación, `nivel ∈ {0,1,2}` (`evaluar_d1_graduado`, promovida
  desde el piloto validado en R23/R24). Límite de constructo aceptado
  explícitamente (R25): mide presencia léxica de vocabulario
  curricular, no corrección semántica ni calidad pedagógica plena.
- **D2 = filtro de validez técnica** (pass/fail vía `SandboxRunner`) —
  nunca graduado, nunca combinado aritméticamente con D1.
- **D3 = filtro de coherencia intermodal** (pass/fail) — nunca
  graduado, nunca combinado aritméticamente con D1.

Ningún composite score existe ni se calcula (`d1 + d2 + d3` o
equivalente) — `EvaluacionCMG` ya lo documenta como decisión explícita
(§16, dimensiones separadas, sin índice compuesto); esta ronda no lo
cambia.

No implementa pertinencia pedagógica, engagement, aprendizaje ni
rendimiento del estudiante (§10) — fuera de alcance por diseño.

Independencia de evaluadores (§15): hoy el repositorio no tiene ningún
mecanismo de "LLM-as-judge" ni rúbrica (auditoría previa, cero
coincidencias de "judge"/"rubric" en `app/`) — no se fabrica uno nuevo
para esta pieza. Cada dimensión se etiqueta con `evaluator_id`
("checklist-v1" para D1/D3, "sandbox-v1" para D2) para dejar el punto
de extensión declarado y documentado, no implementado (decisión
explícita, §15: "si la independencia requiere infraestructura
adicional no existente: implementar solamente el mínimo, documentar la
decisión").
"""

from __future__ import annotations

import dataclasses
import re
import unicodedata
from typing import Any

from app.sandbox.runner import SandboxRunner
from app.sandbox.schemas import SandboxRequest, SandboxStatus
from app.services.cmg_generation_service import CMG
from app.models.concept import Concept
from app.models.learning_objective import LearningObjective

_STOPWORDS = frozenset({
    "el", "la", "los", "las", "de", "del", "en", "y", "a", "un", "una",
    "para", "con", "que", "su", "sus", "es", "son", "al",
})


def _normalizar(texto: str) -> str:
    """Minúsculas + sin acentos — mismo criterio que `_norm` de
    `module_orchestration_service.py` (reutilizado, no reinventado)."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return sin_acentos


def _formas(palabra: str) -> frozenset[str]:
    """Singular/plural determinista (sufijo -s/-es, la inflexión más
    común del español) — NO un lematizador (§FASE 4: "no conviertas D1
    en una evaluación subjetiva compleja"). Corrige el falso negativo
    real encontrado al verificar el catálogo de 32 conceptos contra el
    evaluador: "variables" (título) vs. "variable" (texto del
    ejercicio) no coincidían por un simple desajuste de número
    gramatical, no por ausencia real de correspondencia curricular."""
    formas = {palabra}
    if len(palabra) > 4:
        if palabra.endswith("es"):
            formas.add(palabra[:-2])
        elif palabra.endswith("s"):
            formas.add(palabra[:-1])
        else:
            formas.add(palabra + "s")
            formas.add(palabra + "es")
    return frozenset(formas)


def _contiene_alguna_forma(texto: str, palabra_clave: str) -> bool:
    return any(forma in texto for forma in _formas(palabra_clave))


def _palabras_clave(texto: str, minimo_len: int = 4) -> tuple[str, ...]:
    normalizado = _normalizar(texto).replace(":", " ").replace("-", " ").replace("(", " ").replace(")", " ")
    return tuple(
        w for w in re.findall(r"[a-z0-9]+", normalizado)
        if len(w) >= minimo_len and w not in _STOPWORDS
    )


# ─────────────────────────────  D1 — Adherencia curricular  ─────────────────
#
# D1 es la ÚNICA dimensión graduada de la VD (R25/R26, deliberación
# cerrada) — D2 y D3 son FILTROS de validez/coherencia (pass/fail), no
# dimensiones graduadas: nunca se combinan aritméticamente con D1
# (ningún `d1 + d2 + d3`, ningún índice compuesto — `EvaluacionCMG` ya
# lo documenta explícitamente, sin cambios en esta ronda).

_D1_NIVEL_DEFINICION = {
    0: "sin cobertura léxica del Concept en la explicación",
    1: "cobertura del Concept sin cobertura del LearningObjective",
    2: "cobertura del Concept y del LearningObjective",
}


@dataclasses.dataclass(frozen=True, slots=True)
class D1GraduadoResultado:
    """Instrumento D1 graduado (R23→R26): cobertura léxica curricular de
    la explicación, 3 niveles ordinales (0/1/2). Promovido desde el
    piloto validado (R23: discriminación/monotonicidad/determinismo en
    2 pares independientes; R24: límite de constructo confirmado
    adversarialmente — mide presencia léxica, no calidad semántica —
    límite aceptado explícitamente por R25 como parte de la definición
    operacional). Firma ciega por diseño: solo 3 strings curriculares,
    nunca `condition`/`configuration`/evidencia/`student_id`."""

    nivel: int
    cobertura_concepto: bool
    cobertura_objetivo: bool
    claves_concepto: tuple[str, ...]
    claves_objetivo: tuple[str, ...]


def evaluar_d1_graduado(
    concept_title: str, learning_objective_title: str, explanation: str
) -> D1GraduadoResultado:
    claves_concepto = _palabras_clave(concept_title)
    claves_objetivo = _palabras_clave(learning_objective_title)
    texto = _normalizar(explanation)

    cobertura_concepto = bool(claves_concepto) and any(
        _contiene_alguna_forma(texto, k) for k in claves_concepto
    )
    cobertura_objetivo = bool(claves_objetivo) and any(
        _contiene_alguna_forma(texto, k) for k in claves_objetivo
    )

    if not cobertura_concepto:
        nivel = 0
    elif not cobertura_objetivo:
        nivel = 1
    else:
        nivel = 2

    return D1GraduadoResultado(
        nivel=nivel,
        cobertura_concepto=cobertura_concepto,
        cobertura_objetivo=cobertura_objetivo,
        claves_concepto=claves_concepto,
        claves_objetivo=claves_objetivo,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class D1Resultado:
    evaluator_id: str
    concept_keyword_in_explanation: bool
    concept_keyword_in_exercise: bool
    bloom_target_compatible_with_objective: bool
    issues: tuple[str, ...]
    # R26: dimensión graduada promovida — campos con default para no
    # romper la construcción posicional de 5 argumentos ya existente
    # (`tests/test_cmg_experiment_persistence.py`).
    nivel: int = 0
    nivel_definicion: str = ""
    nivel_cobertura_concepto: bool = False
    nivel_cobertura_objetivo: bool = False

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self) | {"issues": list(self.issues), "passed": self.passed}


def evaluar_d1(concept: Concept, learning_objective: LearningObjective, cmg: CMG) -> D1Resultado:
    """Checklist determinista — sin datos de estudiante, sin `dominada`.
    Detecta: (a) contenido/objetivo fuera de alcance (ninguna palabra
    clave del concepto aparece en la explicación o el ejercicio);
    (b) nivel cognitivo incompatible (`bloom_target` del CMG mayor que
    el `bloom_level` real del objetivo — el generador nunca debe pedir
    MÁS de lo que el objetivo exige). Además (R26) calcula la dimensión
    graduada `nivel` (0/1/2, `evaluar_d1_graduado`) — misma
    implementación validada en R23/R24, reutilizada aquí, no copiada."""
    claves = _palabras_clave(concept.title)
    issues: list[str] = []

    texto_explicacion = _normalizar(cmg.explanation)
    en_explicacion = bool(claves) and any(_contiene_alguna_forma(texto_explicacion, k) for k in claves)
    if not en_explicacion:
        issues.append("ninguna palabra clave del concepto aparece en la explicación")

    texto_ejercicio = _normalizar(cmg.exercise.prompt)
    en_ejercicio = bool(claves) and any(_contiene_alguna_forma(texto_ejercicio, k) for k in claves)
    if not en_ejercicio:
        issues.append("ninguna palabra clave del concepto aparece en el ejercicio")

    bloom_compatible = cmg.bloom_target <= (learning_objective.bloom_level or cmg.bloom_target)
    if not bloom_compatible:
        issues.append(
            f"bloom_target del CMG ({cmg.bloom_target}) excede el bloom_level "
            f"del objetivo ({learning_objective.bloom_level})"
        )

    graduado = evaluar_d1_graduado(concept.title, learning_objective.title, cmg.explanation)

    return D1Resultado(
        evaluator_id="checklist-v1",
        concept_keyword_in_explanation=en_explicacion,
        concept_keyword_in_exercise=en_ejercicio,
        bloom_target_compatible_with_objective=bloom_compatible,
        issues=tuple(issues),
        nivel=graduado.nivel,
        nivel_definicion=_D1_NIVEL_DEFINICION[graduado.nivel],
        nivel_cobertura_concepto=graduado.cobertura_concepto,
        nivel_cobertura_objetivo=graduado.cobertura_objetivo,
    )


# ─────────────────────────────  D2 — Corrección técnica  ────────────────────

@dataclasses.dataclass(frozen=True, slots=True)
class D2Resultado:
    evaluator_id: str
    execution_valid: bool
    status: str
    infrastructure_available: bool
    stderr_preview: str
    traceback_preview: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


async def evaluar_d2(cmg: CMG, *, sandbox: SandboxRunner | None = None) -> D2Resultado:
    """Reutiliza `SandboxRunner` tal cual (§12: "reutilizar si es seguro
    y compatible") — ejecución aislada real, sin permitir ejecución
    arbitraria fuera del sandbox existente. `INFRASTRUCTURE_ERROR`
    (Docker no disponible en el entorno) se distingue explícitamente de
    "código incorrecto" — mismo criterio que `ReviewerAgent._metrics`."""
    sandbox = sandbox or SandboxRunner()
    resultado = await sandbox.run(SandboxRequest(
        code=cmg.code,
        test_code=cmg.tests,
        metadata={"evaluador": "cmg_evaluation_service", "concept_id": cmg.concept_id},
    ))
    infra_disponible = resultado.status is not SandboxStatus.INFRASTRUCTURE_ERROR
    return D2Resultado(
        evaluator_id="sandbox-v1",
        execution_valid=resultado.success,
        status=resultado.status.value,
        infrastructure_available=infra_disponible,
        stderr_preview=resultado.stderr[:500],
        traceback_preview=resultado.traceback[:500],
    )


# ─────────────────────────────  D3 — Coherencia estructural  ────────────────

@dataclasses.dataclass(frozen=True, slots=True)
class D3Resultado:
    evaluator_id: str
    texto_codigo_coherente: bool
    texto_ejercicio_coherente: bool
    texto_diagrama_coherente: bool
    codigo_ejercicio_coherente: bool
    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self) | {"issues": list(self.issues), "passed": self.passed}


def evaluar_d3(concept: Concept, cmg: CMG) -> D3Resultado:
    """Coherencia terminológica mínima (§13/§D3 del encargo — nunca
    "calidad pedagógica"): las mismas palabras clave del concepto deben
    aparecer, de forma consistente, en texto, código (nombres/
    comentarios), ejercicio y diagrama. No mide aprendizaje ni
    satisfacción — solo consistencia estructural entre componentes del
    mismo CMG."""
    claves = _palabras_clave(concept.title)
    if not claves:
        # Concepto sin palabras clave extraíbles (título muy corto):
        # no hay base para evaluar coherencia — se reporta como issue
        # explícito, nunca como "aprobado" por defecto.
        return D3Resultado(
            evaluator_id="checklist-v1",
            texto_codigo_coherente=False,
            texto_ejercicio_coherente=False,
            texto_diagrama_coherente=False,
            codigo_ejercicio_coherente=False,
            issues=("no se pudieron extraer palabras clave del título del concepto",),
        )

    texto = _normalizar(cmg.explanation)
    codigo = _normalizar(cmg.code)
    # Solo el PROMPT del ejercicio cuenta como evidencia (§FASE 5: "el
    # título del ejercicio no debe ser la única evidencia de
    # coherencia" — una plantilla genérica podría llevar el nombre del
    # concepto en el título sin contenido real; el título queda fuera
    # de este cómputo a propósito).
    ejercicio = _normalizar(cmg.exercise.prompt)
    diagrama = _normalizar(cmg.diagram_mermaid)

    texto_codigo = any(_contiene_alguna_forma(codigo, k) for k in claves) or any(_contiene_alguna_forma(texto, k) for k in claves)
    texto_ejercicio = any(_contiene_alguna_forma(ejercicio, k) for k in claves)
    texto_diagrama = any(_contiene_alguna_forma(diagrama, k) for k in claves)
    codigo_ejercicio = texto_codigo and texto_ejercicio

    issues: list[str] = []
    if not texto_ejercicio:
        issues.append("el ejercicio no comparte terminología con el concepto")
    if not texto_diagrama:
        issues.append("el diagrama no referencia el concepto ni el objetivo por nombre")

    return D3Resultado(
        evaluator_id="checklist-v1",
        texto_codigo_coherente=texto_codigo,
        texto_ejercicio_coherente=texto_ejercicio,
        texto_diagrama_coherente=texto_diagrama,
        codigo_ejercicio_coherente=codigo_ejercicio,
        issues=tuple(issues),
    )


# ─────────────────────────────  Agregación mecánica  ────────────────────────

@dataclasses.dataclass(frozen=True, slots=True)
class EvaluacionCMG:
    """Agregación determinista (§16): dimensiones separadas, SIN índice
    compuesto — no hay ninguna justificación pedagógica registrada para
    pesos entre D1/D2/D3, así que no se inventa uno (regla explícita
    del encargo: "si el diseño actual no permite todavía fijar un score
    global válido: guardar dimensiones separadas")."""

    d1: D1Resultado
    d2: D2Resultado
    d3: D3Resultado

    @property
    def todas_las_dimensiones_pasan(self) -> bool:
        return self.d1.passed and self.d2.execution_valid and self.d3.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "d1": self.d1.to_dict(),
            "d2": self.d2.to_dict(),
            "d3": self.d3.to_dict(),
            "todas_las_dimensiones_pasan": self.todas_las_dimensiones_pasan,
        }


async def evaluar_cmg(
    concept: Concept,
    learning_objective: LearningObjective,
    cmg: CMG,
    *,
    sandbox: SandboxRunner | None = None,
) -> EvaluacionCMG:
    """Punto único de entrada de P1 — evaluación separada de la
    generación (P0), sin dependencia circular: recibe el CMG ya
    construido, nunca lo genera ni lo modifica."""
    d1 = evaluar_d1(concept, learning_objective, cmg)
    d2 = await evaluar_d2(cmg, sandbox=sandbox)
    d3 = evaluar_d3(concept, cmg)
    return EvaluacionCMG(d1=d1, d2=d2, d3=d3)
