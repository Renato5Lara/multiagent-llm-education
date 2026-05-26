import json
import logging
from typing import Optional

import os
from app.services.multimodal_service import MultimodalExplanation, ContentChunk

logger = logging.getLogger(__name__)


class ExplanationBuilder:
    def __init__(self, title: str):
        self.explanation = MultimodalExplanation(title=title)

    def add_intro(self, text: str):
        self.explanation.add_text(text)
        return self

    def add_code(self, code: str, language: str = "python", caption: Optional[str] = None):
        if caption:
            self.explanation.add_text(caption)
        self.explanation.add_code(code, language)
        return self

    def add_step(self, number: int, description: str, code: Optional[str] = None, language: str = "python"):
        self.explanation.add_text(f"**Paso {number}:** {description}")
        if code:
            self.explanation.add_code(code, language)
        return self

    def add_comparison(self, title: str, left_label: str, left_content: str, right_label: str, right_content: str):
        self.explanation.add_chunk(ContentChunk("comparison", {
            "title": title,
            "left_label": left_label,
            "left_content": left_content,
            "right_label": right_label,
            "right_content": right_content,
        }))
        return self

    def add_formula(self, latex: str, description: Optional[str] = None):
        if description:
            self.explanation.add_text(description)
        self.explanation.add_chunk(ContentChunk("formula", {"latex": latex}))
        return self

    def add_table(self, headers: list[str], rows: list[list[str]], caption: Optional[str] = None):
        if caption:
            self.explanation.add_text(caption)
        self.explanation.add_chunk(ContentChunk("table", {"headers": headers, "rows": rows}))
        return self

    def add_bullet_list(self, title: str, items: list[str]):
        self.explanation.add_text(f"**{title}**")
        for item in items:
            self.explanation.add_text(f"• {item}")
        return self

    def build(self) -> dict:
        return self.explanation.to_dict()


class AlgorithmExplainer:
    @staticmethod
    def explain_sorting(algorithm: str = "quicksort") -> dict:
        builder = ExplanationBuilder(f"Algoritmo: {algorithm.title()}")
        if algorithm == "quicksort":
            builder.add_intro(
                "Quicksort es un algoritmo de ordenamiento eficiente que utiliza la estrategia "
                "de divide y vencerás para ordenar elementos."
            )
            builder.add_step(1, "Seleccionar un elemento como pivote (generalmente el último elemento).",
                             code="pivot = arr[high]")
            builder.add_step(2, "Particionar el arreglo: colocar elementos menores que el pivote a la izquierda, mayores a la derecha.",
                             code="""def partition(arr, low, high):
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1""")
            builder.add_step(3, "Aplicar recursivamente Quicksort en las sublistas izquierda y derecha.",
                             code="""def quicksort(arr, low, high):
    if low < high:
        pi = partition(arr, low, high)
        quicksort(arr, low, pi - 1)
        quicksort(arr, pi + 1, high)""")
            builder.add_comparison(
                "Complejidad Algorítmica",
                "Mejor Caso", "O(n log n) — cuando el pivote divide equitativamente",
                "Peor Caso", "O(n²) — cuando el pivote es el mínimo o máximo",
            )
        return builder.build()

    @staticmethod
    def explain_binary_search() -> dict:
        builder = ExplanationBuilder("Búsqueda Binaria")
        builder.add_intro(
            "La búsqueda binaria encuentra un elemento en un arreglo ordenado "
            "dividiendo repetidamente el intervalo de búsqueda a la mitad."
        )
        builder.add_step(1, "Definir los límites izquierdo (low) y derecho (high) del arreglo.")
        builder.add_step(2, "Calcular el punto medio: mid = (low + high) // 2")
        builder.add_step(3, "Comparar el elemento en mid con el objetivo. Si coincide, retornar mid.",
                         code="""def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1""")
        builder.add_intro("Complejidad: O(log n) — mucho más rápido que búsqueda lineal O(n) para arreglos grandes.")
        return builder.build()


class ExplanationGenerator:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.use_openai = bool(self.api_key)

    async def generate_explanation(self, topic: str, context: Optional[dict] = None) -> dict:
        if self.use_openai:
            try:
                return await self._ai_explanation(topic, context)
            except Exception as e:
                logger.warning(f"AI explanation failed: {e}")
        return self._template_explanation(topic, context)

    async def _ai_explanation(self, topic: str, context: Optional[dict] = None) -> dict:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key)

        sys_prompt = """Eres un tutor experto que genera explicaciones multimodales estructuradas.
Genera una explicación educativa en formato JSON con chunks de diferentes tipos.

DEBES incluir:
- Al menos 1 chunk "text" introductorio
- Al menos 1 chunk "code" con ejemplo de código real
- Si aplica: chunk "formula" con LaTeX
- Si aplica: chunk "table" para comparaciones
- Chunks "step" para procesos paso a paso

Responde SOLO con JSON válido con esta estructura:
{
  "title": "Título de la explicación",
  "description": "Resumen del tema",
  "chunks": [
    {"type": "text", "data": {"content": "..."}},
    {"type": "code", "data": {"code": "...", "language": "python"}},
    {"type": "step", "data": {"number": 1, "description": "...", "code": "..."}},
    {"type": "formula", "data": {"latex": "..."}},
    {"type": "table", "data": {"headers": [...], "rows": [[...]]}}
  ]
}"""

        user_content = f"Explica el tema: {topic}"
        if context:
            user_content += f"\nContexto: {json.dumps(context, ensure_ascii=False)}"

        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
            max_tokens=2000,
            response_format={"type": "json_object"},
            timeout=30,
        )

        content = resp.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("AI explanation not valid JSON, using template")

        return self._template_explanation(topic, context)

    def _template_explanation(self, topic: str, context: Optional[dict] = None) -> dict:
        builder = ExplanationBuilder(topic)
        builder.add_intro(f"**{topic}** — Concepto fundamental en ciencias de la computación.")
        builder.add_step(1, "Comprender la definición conceptual del tema.")
        builder.add_step(2, "Analizar ejemplos prácticos de aplicación.",
                         code=f"# Ejemplo práctico de {topic}\n# Implementación de referencia\npass")
        builder.add_step(3, "Practicar con ejercicios para reforzar el aprendizaje.")
        builder.add_bullet_list("Puntos clave", [
            "Concepto fundamental para el desarrollo profesional",
            "Aplicación en múltiples contextos",
            "Base para temas avanzados",
        ])
        return {"title": topic, "description": f"Explicación estructurada de {topic}", "chunks": builder.build()["chunks"]}


explanation_generator = ExplanationGenerator()
algorithm_explainer = AlgorithmExplainer()
