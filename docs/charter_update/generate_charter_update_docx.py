from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Actualizacion_y_Refinamiento_del_Project_Charter.docx"


TITLE = "Actualización y Refinamiento del Project Charter"
SUBTITLE = (
    "Proyecto de tesis de Ingeniería de Sistemas: plataforma multiagente pedagógica "
    "observable para adaptación educativa en Fundamentos de Programación"
)


@dataclass
class SectionBlock:
    heading: str
    paragraphs: list[str]
    bullets: list[str] | None = None


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_table_borders(table) -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        elem = OxmlElement(f"w:{edge}")
        elem.set(qn("w:val"), "single")
        elem.set(qn("w:sz"), "6")
        elem.set(qn("w:space"), "0")
        elem.set(qn("w:color"), "DADCE0")
        borders.append(elem)
    tbl_pr.append(borders)


def apply_base_styles(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.49)
    section.footer_distance = Inches(0.49)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15

    for style_name, size, color, before, after in [
        ("Heading 1", 20, RGBColor(0, 0, 0), 20, 6),
        ("Heading 2", 16, RGBColor(0, 0, 0), 18, 6),
        ("Heading 3", 14, RGBColor(67, 67, 67), 16, 4),
    ]:
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = False
        style.font.color.rgb = color
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)

    if "Body Tight" not in doc.styles:
        style = doc.styles.add_style("Body Tight", WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = doc.styles["Normal"]
        style.font.name = "Arial"
        style.font.size = Pt(11)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.1


def add_title_block(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(TITLE)
    run.font.name = "Arial"
    run.font.size = Pt(26)
    run.font.bold = False
    run.font.color.rgb = RGBColor(0, 0, 0)

    p2 = doc.add_paragraph(style="Body Tight")
    p2.add_run(SUBTITLE)

    meta = doc.add_paragraph(style="Body Tight")
    meta.add_run("Fecha: 19 de julio de 2026\n")
    meta.add_run("Naturaleza del documento: actualización formal del alcance, objetivos y criterios de validación\n")
    meta.add_run("Propósito: alinear el Project Charter original con la implementación real observada durante los Sprint 1 y Sprint 2")


def add_paragraphs(doc: Document, paragraphs: list[str], style: str = "Normal") -> None:
    for text in paragraphs:
        p = doc.add_paragraph(style=style)
        p.add_run(text)


def add_bullets(doc: Document, bullets: list[str]) -> None:
    for text in bullets:
        p = doc.add_paragraph(style="Normal")
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(4)
        p.add_run("• ")
        p.add_run(text)


def add_alignment_table(doc: Document) -> None:
    doc.add_heading("2. Diagnóstico de alineación entre el charter original y la aplicación actual", level=1)
    add_paragraphs(
        doc,
        [
            "La revisión del repositorio y de los artefactos técnicos muestra que la aplicación sí conserva la intención estratégica del charter original, pero lo hace desde una formulación más concreta: la generación educativa ya no se plantea como una producción multimodal directa, amplia y poco acotada, sino como una orquestación pedagógica observable, explicable y experimentalmente trazable.",
            "En consecuencia, el proyecto no requiere reemplazar su charter original; requiere refinarlo para que el documento institucional describa con precisión lo que hoy constituye el verdadero objeto de tesis."
        ],
    )

    table = doc.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    widths = [Inches(1.7), Inches(1.2), Inches(1.8), Inches(1.8)]
    headers = ["Componente original", "Estado", "Situación actual", "Decisión recomendada"]
    hdr = table.rows[0].cells
    for idx, text in enumerate(headers):
        hdr[idx].width = widths[idx]
        hdr[idx].text = text
        hdr[idx].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_shading(hdr[idx], "F2F4F7")

    rows = [
        ("Arquitectura multiagente híbrida", "Cumple", "Implementada con FastAPI, LangGraph, consenso, memoria compartida y servicios pedagógicos.", "Mantener y precisar."),
        ("Generación multimodal educativa", "Cumple parcialmente", "La implementación privilegia prompts multimodales estructurados y continuidad narrativa, más que generación directa irrestricta de medios.", "Reformular para reflejar orquestación multimodal."),
        ("Agentes especializados", "Cumple", "Se observan agentes y servicios especializados para consenso, retrieval, replay, revisión, explicación y adaptación.", "Mantener."),
        ("Benchmarking académico", "Cumple", "Existen datasets pedagógicos, runner reproducible y artefactos exportados de benchmark.", "Mantener con foco reproducible."),
        ("Validación técnica", "Cumple", "La solución cuenta con pruebas, validación E2E, degraded mode y endurecimiento de sandbox.", "Mantener."),
        ("Sandbox de ejecución", "Cumple", "Se implementó sandbox Docker seguro con validaciones y políticas restrictivas.", "Mantener."),
        ("Consenso multiagente", "Cumple", "El consenso quedó consolidado como núcleo de decisión pedagógica observable.", "Mantener y enfatizar."),
        ("Evaluación pedagógica", "Cumple parcialmente", "Existe explicación Bloom, trazas y métricas; la evidencia más fuerte es técnico-experimental antes que pedagógica con población real.", "Acotar al alcance del Taller y tesis prototipo."),
        ("Dos LLMs de frontera y comparación amplia", "Evidencia parcial", "El repositorio prioriza robustez, fallback y reproducibilidad por encima de depender de múltiples proveedores en toda la plataforma.", "Reducir exigencia prescriptiva y dejarlo como capacidad opcional."),
        ("Generación de diagramas como eje central", "Evolucionado", "Lo central dejó de ser el diagrama aislado y pasó a ser la trazabilidad pedagógica integral.", "Despriorizar en el charter actualizado."),
    ]

    for component, status, current, decision in rows:
        cells = table.add_row().cells
        for idx, value in enumerate((component, status, current, decision)):
            cells[idx].width = widths[idx]
            cells[idx].text = value
            cells[idx].vertical_alignment = WD_ALIGN_VERTICAL.TOP

    set_table_borders(table)


def add_objectives_table(doc: Document) -> None:
    doc.add_heading("8. Actualización de objetivos, alcance y criterios", level=1)
    add_paragraphs(
        doc,
        [
            "La actualización propuesta no contradice el charter original; lo aterriza. El cambio principal consiste en pasar de una formulación orientada a generación multimodal amplia hacia un diseño de plataforma experimental que demuestra adaptación pedagógica, consenso y trazabilidad."
        ],
    )

    doc.add_heading("8.1 Objetivo general refinado", level=2)
    add_paragraphs(
        doc,
        [
            "Diseñar, implementar y validar técnicamente una plataforma multiagente pedagógica observable, basada en LangGraph y servicios de IA, capaz de adaptar contenido educativo para Fundamentos de Programación mediante consenso multiagente, retrieval contextual, memoria compartida, replay cognitivo, explicabilidad pedagógica y benchmarking reproducible."
        ],
    )

    doc.add_heading("8.2 Objetivos específicos refinados", level=2)
    add_bullets(
        doc,
        [
            "Implementar una arquitectura multiagente con agentes y servicios especializados para adaptación pedagógica, deliberación, revisión, retrieval y explicación de decisiones.",
            "Integrar mecanismos de observabilidad de extremo a extremo mediante eventos SSE, trazabilidad distribuida, métricas de consenso y dashboards de evidencia.",
            "Construir un entorno seguro de validación de código basado en sandbox Docker con políticas restrictivas y modo degradado documentado.",
            "Desarrollar un sistema de memoria compartida y replay cognitivo que permita reconstruir el razonamiento pedagógico y la continuidad narrativa de las sesiones.",
            "Incorporar retrieval contextual educativo y prompts multimodales estructurados para mejorar grounding, coherencia y personalización.",
            "Ejecutar benchmarking reproducible con datasets pedagógicos y exportación de resultados para comparación entre variantes arquitectónicas.",
            "Documentar técnicamente el comportamiento del sistema para sustentar una defensa académica basada en evidencia verificable."
        ],
    )

    doc.add_heading("8.3 Alcance refinado", level=2)
    add_bullets(
        doc,
        [
            "Dentro del alcance: adaptación pedagógica en Fundamentos de Programación, observabilidad multiagente, replay, explainability, retrieval, benchmark, sandbox y dashboards de evidencia.",
            "Fuera de alcance: validación con población estudiantil real a escala, LMS institucional completo, expansión multisectorial, producción comercial y generación audiovisual avanzada como eje principal del artefacto."
        ],
    )

    doc.add_heading("8.4 Entregables refinados", level=2)
    add_bullets(
        doc,
        [
            "Plataforma funcional con backend FastAPI y frontend React para rutas adaptativas y paneles de evidencia.",
            "Repositorio con arquitectura multiagente, servicios pedagógicos, módulos de explainability, replay, benchmark y sandbox.",
            "Datasets y artefactos reproducibles de evaluación académica.",
            "Documentación técnica, evidencia Scrum, guías de demo y reporte de readiness para sustentación.",
            "Documento formal de actualización del Project Charter que justifique la evolución del proyecto."
        ],
    )

    doc.add_heading("8.5 Restricciones refinadas", level=2)
    add_bullets(
        doc,
        [
            "Tiempo limitado del Taller Integrador y disponibilidad de un único investigador-desarrollador.",
            "Dependencia parcial de servicios externos de IA y, por tanto, necesidad de degraded mode.",
            "Limitaciones de cómputo local y necesidad de Docker para validación completa del sandbox.",
            "Necesidad de mantener reproducibilidad experimental pese a cambios frecuentes en modelos y proveedores."
        ],
    )

    doc.add_heading("8.6 Métricas refinadas", level=2)
    metrics_table = doc.add_table(rows=1, cols=3)
    metrics_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    metrics_table.autofit = False
    widths = [Inches(2.2), Inches(2.1), Inches(2.2)]
    for idx, text in enumerate(("Dimensión", "Indicador sugerido", "Sentido académico")):
        cell = metrics_table.rows[0].cells[idx]
        cell.width = widths[idx]
        cell.text = text
        set_cell_shading(cell, "F2F4F7")
    metric_rows = [
        ("Adaptación pedagógica", "Alineación Bloom, impacto de adaptación, cobertura de misconceptions", "Demuestra adecuación educativa."),
        ("Observabilidad", "Disponibilidad de trazas, eventos SSE, replay y decision trace", "Demuestra transparencia del sistema."),
        ("Reproducibilidad", "Benchmarks re-ejecutables, exportación y consistencia de resultados", "Fortalece la validez experimental."),
        ("Seguridad", "Tasa de validación de sandbox y bloqueos de políticas", "Demuestra robustez técnica."),
        ("Consenso", "Confianza de consenso, estabilidad del flujo y longitud de trayectoria", "Mide coordinación multiagente."),
        ("Operación resiliente", "Funcionamiento en degraded mode y tolerancia a dependencias faltantes", "Demuestra continuidad operativa."),
    ]
    for row in metric_rows:
        cells = metrics_table.add_row().cells
        for idx, value in enumerate(row):
            cells[idx].width = widths[idx]
            cells[idx].text = value
    set_table_borders(metrics_table)


def build_document() -> Document:
    doc = Document()
    apply_base_styles(doc)
    add_title_block(doc)

    intro = [
        "El presente documento formaliza la actualización y refinamiento del Project Charter del proyecto de tesis desarrollado en el marco de Ingeniería de Sistemas. Su propósito no es sustituir el charter original, sino justificar técnicamente la evolución del proyecto a partir de la evidencia acumulada durante los Sprint de desarrollo y alinear el alcance oficial con la implementación real del sistema.",
        "La revisión del charter inicial, de la arquitectura implementada y de los artefactos de evidencia técnica permite concluir que el proyecto sí mantiene coherencia con su objetivo académico original. No obstante, el producto construido consolidó un foco más sólido: una plataforma multiagente pedagógica observable, explicable y reproducible, orientada a la adaptación educativa en Fundamentos de Programación."
    ]
    doc.add_heading("1. Introducción", level=1)
    add_paragraphs(doc, intro)

    doc.add_heading("2. Justificación del cambio", level=1)
    add_paragraphs(
        doc,
        [
            "El charter original definió una visión ambiciosa y conceptualmente rica, pero varios de sus componentes fueron redactados con un nivel de amplitud que dificultaba su evaluación objetiva. Expresiones como arquitectura híbrida, generación multimodal verificada o coherencia pedagógica multimodal describían una intención válida, aunque todavía no delimitaban con precisión los mecanismos observables que debían construirse ni los criterios concretos para defenderlos en una tesis.",
            "Durante la ejecución iterativa del proyecto, la implementación reveló que la viabilidad académica y técnica dependía menos de agregar más capacidades nominales y más de consolidar cuatro propiedades estructurales: estabilidad operativa, observabilidad de decisiones, reproducibilidad experimental y acotación pedagógica del dominio. Esta transición no representa una desviación del problema de investigación, sino una maduración del mismo.",
            "Las iteraciones Scrum permitieron identificar qué elementos aportaban evidencia real al objetivo de tesis y cuáles introducían complejidad difícil de sostener con rigor en el contexto del Taller Integrador. A partir de ello, la tesis evolucionó desde una promesa amplia de generación educativa multimodal hacia una plataforma de orquestación pedagógica adaptativa, capaz de explicar por qué decide, cómo decide y con qué evidencia decide.",
            "Por esta razón, la actualización del charter debe reconocer oficialmente que la prioridad del sistema dejó de ser la amplitud funcional y pasó a ser la demostración defendible del comportamiento multiagente en un dominio educativo específico."
        ],
    )

    add_alignment_table(doc)

    doc.add_heading("3. Evolución del proyecto por Sprint", level=1)
    add_paragraphs(
        doc,
        [
            "La evolución del sistema puede describirse cronológicamente como un proceso de convergencia entre visión académica e implementación verificable."
        ],
    )
    doc.add_heading("3.1 Sprint 1: fundación arquitectónica y producto base", level=2)
    add_paragraphs(
        doc,
        [
            "El Sprint 1 se concentró en construir la base operativa del artefacto: backend con FastAPI y PostgreSQL, frontend React, autenticación JWT, módulos académicos, dashboards y onboarding, además del primer grafo multiagente con LangGraph y agentes especializados iniciales. Esta fase permitió disponer de un flujo funcional docente-estudiante y asegurar que el proyecto no quedara restringido a un prototipo conceptual sin soporte de producto.",
            "Desde el punto de vista metodológico, Sprint 1 validó la necesidad de contar con una arquitectura aplicativa completa para sostener el experimento pedagógico. La experiencia mostró que la tesis requería no solo agentes, sino un contexto de uso observable donde la adaptación pudiera demostrarse."
        ],
    )
    doc.add_heading("3.2 Sprint 2: endurecimiento experimental y foco de tesis", level=2)
    add_paragraphs(
        doc,
        [
            "El Sprint 2 reorientó el proyecto hacia su núcleo defendible. En esta fase se consolidaron el swarm pedagógico, el retrieval contextual, la explainability, el replay cognitivo, el sandbox Docker, el benchmark académico y la observabilidad SSE. También se integraron memoria compartida, consenso más robusto, diagnósticos del enjambre y dashboards de trazabilidad.",
            "Esta segunda etapa es la que redefine el verdadero alcance del sistema: una plataforma donde las decisiones pedagógicas del enjambre pueden seguirse, reproducirse y evaluarse. El aporte del sprint no consistió solo en añadir funcionalidades, sino en convertir la arquitectura en un objeto de investigación auditable."
        ],
    )

    doc.add_heading("4. Problemas identificados durante la implementación", level=1)
    add_paragraphs(
        doc,
        [
            "El refinamiento del charter surge también de problemas concretos detectados en el desarrollo. Estos hallazgos justifican la reformulación oficial de objetivos y entregables."
        ],
    )
    add_bullets(
        doc,
        [
            "Consumo excesivo de tokens en flujos multiagente amplios. La experiencia del proyecto evidenció que prompts muy largos y trayectorias extensas afectaban costo, latencia y estabilidad.",
            "Complejidad de la generación multimodal directa. Se comprobó que producir texto, código y recursos visuales de forma totalmente automática no era el eje más defendible del sistema si no estaba respaldado por trazabilidad.",
            "Necesidad de prompts estructurados. El sistema evolucionó hacia una estrategia de orquestación de prompts multimodales, más controlable que la generación libre.",
            "Importancia del degraded mode. La dependencia de APIs y de Docker hizo indispensable diseñar rutas de operación degradada para sostener demos, pruebas y validación técnica.",
            "Necesidad de trazabilidad pedagógica. La tesis exigía demostrar no solo resultados, sino el proceso interno de decisión, de allí la incorporación de replay, decision trace y observabilidad.",
            "Importancia de la validación reproducible. La investigación requería artefactos exportables, datasets estables y benchmark re-ejecutable.",
            "Limitaciones de ejecución local. El entorno local condicionó la estrategia de sandbox, despliegue y endurecimiento del sistema.",
            "Necesidad de simplificar objetivos iniciales. Algunos enunciados originales debían acotarse para evitar promesas más amplias que la evidencia realmente obtenida."
        ],
    )

    doc.add_heading("5. Nuevo enfoque consolidado del proyecto", level=1)
    add_paragraphs(
        doc,
        [
            "El enfoque consolidado del proyecto puede formularse como el diseño de una plataforma multiagente pedagógica observable orientada a la adaptación educativa inteligente. Su propuesta de valor académica ya no descansa únicamente en generar contenido, sino en coordinar, justificar y registrar decisiones pedagógicas multiagente en un entorno experimental controlado.",
            "En esta formulación, la adaptación pedagógica inteligente se apoya en señales del estudiante, retrieval contextual y memoria compartida; la observabilidad multiagente se materializa en SSE, tracing, métricas y dashboards; la explicación de decisiones se expresa mediante explainability y replay cognitivo; y la validación del artefacto se fortalece con benchmarking reproducible y mecanismos de endurecimiento técnico como sandbox y degraded mode.",
            "Así, la coherencia narrativa y multimodal del sistema no se presenta como un resultado espontáneo del modelo, sino como un efecto buscado de la orquestación pedagógica, la continuidad de memoria y la estructuración de prompts."
        ],
    )

    doc.add_heading("6. Componentes implementados", level=1)
    doc.add_heading("6.1 Backend", level=2)
    add_bullets(
        doc,
        [
            "FastAPI como base del backend y de los endpoints para autenticación, módulos pedagógicos, replay, benchmark y sandbox.",
            "LangGraph como marco de orquestación de agentes y flujos multiagente.",
            "SSE para transmisión en tiempo real de eventos del swarm y de memoria observable.",
            "Tavily Retrieval y estrategias de recuperación contextual para grounding educativo.",
            "Shared Memory y persistencia de observaciones útiles para consenso y continuidad narrativa.",
            "Replay cognitivo y exportación de sesiones para análisis temporal del razonamiento.",
            "Módulos de explainability pedagógica y análisis Bloom.",
            "Framework de benchmark académico reproducible con exportación de resultados.",
            "Sandbox Docker con políticas de seguridad, validación y endurecimiento."
        ],
    )
    doc.add_heading("6.2 Frontend", level=2)
    add_bullets(
        doc,
        [
            "React como base de la interfaz de usuario.",
            "Dashboards observables para demo del swarm, evidencia y monitoreo de estado.",
            "Replay visual y controles de reproducción de sesiones.",
            "Explainability visual y paneles de razonamiento adaptativo.",
            "Timeline cognitivo y componentes de trazabilidad de decisiones.",
            "Métricas pedagógicas, vistas de consenso, retrieval y validación de sandbox."
        ],
    )
    doc.add_heading("6.3 Inteligencia artificial y lógica pedagógica", level=2)
    add_bullets(
        doc,
        [
            "Arquitectura Swarm con consenso multiagente como mecanismo de coordinación.",
            "Retrieval pedagógico para grounding contextual.",
            "Prompts multimodales estructurados en lugar de generación irrestricta.",
            "Adaptación cognitiva basada en perfil del estudiante, Bloom y señales de progreso.",
            "Memoria narrativa para continuidad pedagógica y coherencia entre sesiones."
        ],
    )

    doc.add_heading("7. Justificación académica del refinamiento", level=1)
    add_paragraphs(
        doc,
        [
            "Desde el punto de vista académico, el nuevo enfoque es más defendible porque reduce ambigüedad conceptual y aumenta verificabilidad. Una tesis de Ingeniería de Sistemas no solo debe proponer una idea innovadora, sino demostrar que la arquitectura diseñada puede observarse, evaluarse y reproducirse bajo criterios explícitos.",
            "El refinamiento mejora la reproducibilidad al incorporar benchmark exportable, datasets versionados, trazas de ejecución y replay de sesiones. También fortalece la investigación porque desplaza el énfasis desde la promesa de creatividad ilimitada del modelo hacia la ingeniería del proceso decisional: cómo se recupera contexto, cómo se delibera, cómo se justifica la adaptación y cómo se mide su consistencia.",
            "Asimismo, el enfoque actualizado fortalece el benchmarking académico al permitir comparar variantes arquitectónicas y no solo respuestas finales. Esto es metodológicamente valioso porque posibilita analizar impacto del retrieval, de la memoria o del reviewer sobre métricas observables.",
            "Finalmente, el proyecto mantiene plena alineación con Ingeniería de Sistemas e IA aplicada a educación, dado que integra diseño arquitectónico, servicios distribuidos, observabilidad, seguridad, validación experimental y adaptación pedagógica sobre un dominio de aprendizaje concreto."
        ],
    )

    add_objectives_table(doc)

    doc.add_heading("9. Análisis técnico de evidencia existente", level=1)
    add_paragraphs(
        doc,
        [
            "La evidencia técnica disponible respalda el refinamiento propuesto. El repositorio documenta una arquitectura FastAPI + LangGraph + React con módulos explícitos de observabilidad, replay, benchmark, sandbox y explainability. Los reportes Scrum muestran que Sprint 1 consolidó la base aplicativa y que Sprint 2 concentró el endurecimiento experimental mediante consenso, memoria compartida, diagnósticos, SSE y herramientas de investigación.",
            "Los artefactos de benchmark exportados evidencian un runner reproducible con 60 observaciones en el resultado revisado, una trayectoria promedio breve y métricas asociadas a consenso, retrieval y validación de sandbox. Los reportes de readiness registran degraded mode operativo sin API keys, validaciones de sandbox endurecidas y suites de pruebas en escala amplia. Esta combinación de código, pruebas y reportes es consistente con la tesis de una plataforma observable y defendible.",
            "En términos de interpretación institucional, ello implica que la aplicación sí cumple con los objetivos sustantivos del charter original, pero lo hace bajo una forma más madura. Por tanto, la recomendación no es declarar incumplimiento, sino formalizar la evolución del alcance para que el documento rector coincida con el sistema implementado."
        ],
    )

    doc.add_heading("10. Conclusiones", level=1)
    add_paragraphs(
        doc,
        [
            "Primera, el proyecto sí mantiene continuidad con el charter original en su propósito central: demostrar el valor de una arquitectura multiagente aplicada a educación en Fundamentos de Programación.",
            "Segunda, la implementación real revela una evolución metodológicamente positiva: el sistema pasó de una formulación amplia de generación multimodal a una plataforma de orquestación pedagógica observable, explicable y reproducible.",
            "Tercera, el cambio no debe entenderse como desviación del proyecto, sino como refinamiento técnico legítimo derivado del desarrollo iterativo, la validación de restricciones y la necesidad de defender el artefacto con evidencia sólida.",
            "Cuarta, en consecuencia, la aplicación no exige reescribir desde cero el Project Charter, pero sí requiere una actualización formal de objetivos, alcance, entregables y métricas para reflejar con precisión el estado actual del sistema."
        ],
    )

    doc.add_heading("11. Recomendaciones", level=1)
    add_bullets(
        doc,
        [
            "Aprobar institucionalmente una versión refinada del charter que conserve el problema original, pero reoriente el énfasis hacia adaptación pedagógica observable y benchmarking reproducible.",
            "Usar el término orquestación pedagógica multimodal en lugar de generación multimodal automática cuando se describa el núcleo del sistema.",
            "Presentar la observabilidad, el replay cognitivo y la explainability como contribuciones diferenciales de la tesis, no como accesorios secundarios.",
            "Mantener el dominio de validación acotado a Fundamentos de Programación para preservar profundidad metodológica.",
            "Reservar la validación con estudiantes reales, comparaciones ecológicas y expansión institucional como trabajo futuro de tesis o de siguientes fases."
        ],
    )

    doc.add_heading("Anexo A. Fuentes de evidencia revisadas", level=1)
    add_bullets(
        doc,
        [
            "Project Charter original en formato .docx.",
            "README y documentación arquitectónica del repositorio.",
            "Reportes de Sprint 1 y Sprint 2.",
            "THESIS_SCOPE_FREEZE, THESIS_NARRATIVE y documentos de reproducibilidad.",
            "Artefactos de benchmark exportados y reportes de final readiness."
        ],
    )

    return doc


def main() -> None:
    doc = build_document()
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
