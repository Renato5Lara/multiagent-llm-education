"""Sistema convencional INDEPENDIENTE `decision_table` (OE2): adaptación por TABLA DE DECISIÓN ESTÁTICA sobre los campos DECLARADOS del perfil.

QUÉ HACE. Para un `ProfileRequest` (la misma entrada que la propuesta) decide la configuración S = (e_m, v_m) de las 4 modalidades con una tabla fija de reglas, como lo haría un motor de reglas de un
sistema de gestión del aprendizaje: «presentar primero el estilo declarado; apoyar con los estilos secundarios; ajustar la profundidad al nivel y a la tasa de error». Sin búsqueda, sin función objetivo, sin iteración.

REGLAS (versión `decision-table-v1`, constantes de este módulo; no se calibran con datos):
    énfasis e_m   modalidad PRIMARIA (mayor preferencia declarada en `estilo`; empate → orden de prioridad código > diagrama > texto > audio): e = 2.
                  Demás modalidades: e = 1 si su preferencia declarada ≥ `SECONDARY_STYLE_MIN` (0,25); si no, e = 0.
    variante v_m  profundidad por nivel: nivel < 1/3 → 0 (básica); < 2/3 → 1; en otro caso 2 (profunda); si `tasa_error_previa` > `REMEDIATION_ERROR_MIN` (0,5) se baja un nivel
                  (remediación: realización más simple). La misma profundidad para las 4 modalidades.

ENTRADA. `ProfileRequest` (RF01), idéntico al de la propuesta. SALIDA. `Configuration` S válida (8 enteros en {0,1,2}, las 4 modalidades presentes): el mismo espacio y el mismo contrato que la propuesta;
el paquete multimodal lo ensambla y valida `ConventionalAdapter` con la misma biblioteca y la misma validación que la propuesta.

INDEPENDENCIA DEL ENJAMBRE. Este módulo NO importa ni usa: PSO (`pso.engine`, `pso.decode`, `pso.params`), `profiles.w_mapping` (ni `compute_weights` ni `heuristic_start`), `fitness`, agentes AG0–AG4,
el bus ni el estado de partículas. Solo lee `estilo`, `nivel` y `tasa_error_previa` del perfil y usa el ESPACIO de configuración (`pso.space`: la definición del problema, compartida por todos los sistemas). A diferencia de
`rules` —que decodifica el punto de arranque heurístico de AG1 (el enjambre sin búsqueda)—, aquí no hay normalización por el máximo, ni modulación por error sobre los pesos, ni reutilización de W.

MÉTRICAS. Tiempo de decisión (`decision_ms`; en el endpoint baseline también `t_conv_ms` por compatibilidad: ver `conventional.py`), tiempo total en proceso, 𝓕 de la configuración elegida (evaluada FUERA del
cronómetro con el mismo 𝓕 para comparar calidad) y validez del paquete.

QUÉ NO REPRESENTA. No es un LMS real ni reproduce uno de la literatura; no es un LLM monolítico; no optimiza; no es el óptimo de referencia (`bruteforce`) ni la ablación del enjambre (`rules`). Es la implementación
convencional por reglas estáticas que este estudio define para la comparación. Su tiempo de decisión NO es un tiempo de convergencia iterativa: no hay convergencia.
"""

from __future__ import annotations

from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.pso.space import MODALITIES, N_DIMS, Configuration, dim_index

RULE_VERSION = "decision-table-v1"
SECONDARY_STYLE_MIN = 0.25
REMEDIATION_ERROR_MIN = 0.5
_LEVEL_THIRDS = (1 / 3, 2 / 3)
_STYLE_FIELD = {"code": "w_c", "diagram": "w_v", "text": "w_t", "audio": "w_a"}      # modalidad → preferencia declarada en `estilo`


def _depth(nivel: float, tasa_error_previa: float) -> int:
    depth = 0 if nivel < _LEVEL_THIRDS[0] else (1 if nivel < _LEVEL_THIRDS[1] else 2)
    return max(0, depth - 1) if tasa_error_previa > REMEDIATION_ERROR_MIN else depth


def decide(profile: ProfileRequest) -> Configuration:
    """Configuración S por la tabla estática. Determinista: misma entrada → mismo S."""
    pref = {m: float(getattr(profile.estilo, _STYLE_FIELD[m])) for m in MODALITIES}
    primary = max(MODALITIES, key=lambda m: (pref[m], -MODALITIES.index(m)))             # mayor preferencia; empate → prioridad código > diagrama > texto > audio
    depth = _depth(profile.nivel, profile.tasa_error_previa)
    vec = [0] * N_DIMS
    for m in MODALITIES:
        vec[dim_index("e", m)] = 2 if m == primary else (1 if pref[m] >= SECONDARY_STYLE_MIN else 0)
        vec[dim_index("v", m)] = depth
    return Configuration(tuple(vec))
