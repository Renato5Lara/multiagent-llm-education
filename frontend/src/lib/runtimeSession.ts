// session_id determinista por estudiante+curso — espejo exacto de
// `_sesion_del_curso` en app/services/runtime_bridge.py (RFC-0010 no fija
// ningún esquema; siempre reconstruible igual, regla de derivación). Permite
// al frontend consultar la traza de SU PROPIA sesión sin que el backend
// tenga que devolver el id explícitamente.
export function sesionDelCurso(courseId: string, studentId: string): string {
  return `curso:${courseId}:estudiante:${studentId}`
}
