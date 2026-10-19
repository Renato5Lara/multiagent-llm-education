"""Construye ESTADO_DEL_ARTE_MATRIZ.csv a partir de _metadatos_candidatos.json (Crossref+OpenAlex) y anotaciones manuales.
Las cifras de 'resultados_publicados' se transcriben SOLO del resumen verificado; si el resumen no trae cifras se deja 'Sin cifras en el resumen'.
Uso (desde oe_n8_2026-10-13/): python scripts/build_state_of_art_matrix.py"""
import csv
import html
import json
from collections import Counter

M = json.load(open('state_of_art/_metadatos_candidatos.json', encoding='utf-8'))
TH = {'10.7717/peerj-cs.857', '10.1007/s10489-009-0186-7', '10.1145/1389095.1389099', '10.48084/etasr.3905', '10.3390/app16031323',
      '10.1007/s00500-021-05836-9', '10.3390/app15137579', '10.11591/ijece.v13i2.pp1964-1978', '10.3390/math11132792', '10.1016/j.caeai.2022.100057',
      '10.1016/j.heliyon.2024.e39088', '10.1016/j.caeai.2024.100280', '10.1109/TLT.2025.3561332', '10.3390/info16121045', '10.1109/4235.985692',
      '10.1007/s11831-021-09694-4', '10.1109/JAS.2021.1004129', '10.1016/j.learninstruc.2005.07.001', '10.1080/10494820.2020.1808794',
      '10.3389/fcomp.2026.1777749', '10.1186/s40561-024-00292-y', '10.1145/3501385.3543957', '10.1080/10447310802205776', '10.1016/j.heliyon.2024.e39630',
      '10.1007/s10639-016-9472-2', '10.1016/j.sasc.2024.200091', '10.3390/math12162497', '10.1016/j.heliyon.2024.e32628'}
CTX = 'Contextual, no directamente comparable'
RES = 'Comparable con reservas'
MET = 'Metodológica (no comparativa)'
SC = 'Sin cifras en el resumen'
# doi: (objetivo, comparabilidad, problema, método/sistema, muestra, métricas, resultados publicados, limitaciones)
A = {
    '10.1109/ICSMC.1997.637339': ('OE3', MET, 'Extender PSO a variables binarias', 'PSO binario', 'Funciones de prueba', 'Convergencia', SC, 'Base del PSO discreto; el espacio de la tesis es ternario {0,1,2}'),
    '10.1080/10447318.2018.1455307': ('OE5', MET, 'Revisión del SUS', 'Revisión narrativa', '—', 'SUS', SC, 'Revisión; sin meta numérica en el resumen'),
    '10.1145/2408776.2408794': ('OE2/OE4', MET, 'Variabilidad de latencia en servicios web a gran escala', 'Técnicas de tolerancia a la latencia de cola', '—', 'Latencia de cola', SC, 'Justifica reportar percentiles (P95) y no solo la media; contexto de grandes servicios, no un MAS educativo'),
    '10.1007/s10462-020-09864-z': ('OE2/OE3', CTX, 'Secuenciación curricular adaptativa con metaheurísticas', 'Revisión sistemática y mapeo', 'Estudios de la revisión', '—', 'Resumen no disponible en OpenAlex (solo metadatos Crossref)', 'Solo se verificó el registro; no se leyó el texto'),
    '10.1109/ACCESS.2022.3142859': ('OE3', MET, 'Revisión de PSO y variantes', 'Revisión (PSO binario, topologías de vecindad, híbridos)', '—', '—', SC, 'Respalda topologías/difusión de g_best como mecanismo (OE3)'),
    '10.25046/aj060161': ('OE3/OE5', CTX, 'Ruta de aprendizaje por clase cognitiva (Bloom revisado)', 'PSO híbrido (BPSO+DPSO), función Connection Weight', 'Tres clases cognitivas', 'Similitud de la secuencia de la ruta', 'Similitud 87,5 % (CL), 75 % (CM), 87,5 % (CH)', 'Similitud de secuencias, no F1 multimodal; sin tiempos ni baseline convencional'),
    '10.1109/TKDE.2013.39': ('OE5', MET, 'Revisión de aprendizaje multietiqueta y sus métricas', 'Revisión', '—', 'Métricas multietiqueta', SC, 'Sustenta F1 por muestra (samples) para conjuntos de modalidades'),
    '10.3389/fpsyg.2013.00863': ('OE1-OE5', MET, 'Cálculo y reporte de tamaños de efecto', 'Guía práctica (t, ANOVA, diseños intra/entre)', '—', 'd, eta cuadrado', SC, 'Referencia metodológica de tamaños de efecto'),
    '10.19173/irrodl.v16i2.1955': ('OE5', RES, 'Usabilidad percibida de LMS con SUS', '11 estudios con SUS', '769 estudiantes; LMS eClass y Moodle', 'SUS', 'SUS medio = 76,27; SUS robusto incluso con muestras pequeñas', 'Estudiantes y LMS genéricos; no expertos evaluando un MAS de adaptación'),
    '10.3991/ijim.v14i09.13123': ('OE5', CTX, 'Usabilidad de un sitio para aprender programación', 'SUS', '162 encuestados (81 familiarizados, 81 no)', 'SUS', 'SUS 72,1 (familiarizados) y 70 (no familiarizados)', 'Sitio de programación con usuarios finales; no un sistema adaptativo evaluado por expertos'),
    '10.1287/opre.9.3.383': ('OE4', MET, 'Relación entre cola, tasa de llegada y tiempo en el sistema', 'Teoría de colas (L = lambda W)', '—', '—', 'Resumen no disponible', 'Explica la meseta de throughput y el crecimiento lineal de la latencia en carga cerrada'),
    '10.1111/j.2517-6161.1995.tb02031.x': ('OE2/OE3', MET, 'Control de la tasa de falsos descubrimientos', 'FDR (Benjamini–Hochberg)', '—', '—', 'Resumen no disponible', 'Alternativa a Holm (FWER); no usada como principal'),
    '10.1093/biomet/34.1-2.28': ('OE2', MET, 'Comparación de dos medias con varianzas desiguales', 'Prueba t de Welch', '—', '—', 'Resumen no disponible', 'Base de la prueba primaria de N2'),
    '10.1080/01621459.1952.10483441': ('OE4', MET, 'Comparación de k grupos por rangos', 'Kruskal–Wallis', '—', '—', 'Resumen no disponible', 'Base de la prueba de efecto de la carga (N4)'),
    '10.1214/aoms/1177730491': ('OE2', MET, 'Comparación de dos muestras por rangos', 'Mann–Whitney', '—', '—', 'Resumen no disponible', 'Prueba complementaria de N2'),
    '10.1214/aos/1176344552': ('OE1-OE5', MET, 'Métodos de remuestreo', 'Bootstrap', '—', '—', 'Resumen no disponible', 'Intervalos de confianza no paramétricos'),
    '10.1207/S15326985EP3801_6': ('OE5', CTX, 'Teoría cognitiva del aprendizaje multimedia', 'Marco teórico + resumen de experimentos', '—', '—', SC, 'Respalda la pertinencia pedagógica de combinar modalidades; no mide el artefacto'),
    '10.1016/j.heliyon.2024.e32628': ('OE5', CTX, 'Rutas de aprendizaje personalizadas con aprendizaje profundo', 'Experimento controlado con plataforma adaptativa', '300 estudiantes, 4 cursos', 'Notas, puntajes, participación', 'Mejora del 25 % en notas, puntajes y participación; p = 0,00045', 'Mide resultados de aprendizaje, no precisión de adaptación ni desempeño computacional'),
    '10.7717/peerj-cs.857': ('OE3', CTX, 'Predicción de equipos de bajo desempeño con inteligencia de enjambre', 'Modelo basado en enjambre', '—', 'Predicción', 'Cifras no incluidas en el fragmento verificado del resumen', 'Dominio distinto (ingeniería de software educativa)'),
    '10.1007/s10489-009-0186-7': ('OE3', RES, 'Composición personalizada de e-cursos', 'PSO (PC2PSO)', '—', '—', 'Resumen no disponible en OpenAlex', 'Antecedente directo de PSO en composición de cursos; sin cifras verificadas'),
    '10.1145/1389095.1389099': ('OE3', RES, 'Secuenciación de objetos de aprendizaje como CSP', 'Agente PSO con metadatos y competencias', '—', 'Éxito al resolver; manejo de explosión combinatoria', 'Cualitativo: el agente resuelve el problema y maneja razonablemente la explosión combinatoria', 'Sin cifras en el resumen; no mide latencia ni compara con reglas'),
    '10.48084/etasr.3905': ('OE1/OE3', CTX, 'Sistema e-learning adaptativo multiagente', 'Q-learning; estilo Felder–Silverman', '—', '—', SC, 'Diseño sin evaluación cuantitativa en el resumen'),
    '10.3390/app16031323': ('OE1/OE5', CTX, 'Arquitectura multiagente adaptativa con RL e IA generativa en Moodle', 'Meta-agente RL, LLM, n8n, Django', 'Caso real y simulado; cuestionario a estudiantes', 'Mann–Whitney, Kruskal–Wallis', 'Sin cifras en el fragmento del resumen verificado', 'Percepción de estudiantes; no mide convergencia ni throughput'),
    '10.1007/s00500-021-05836-9': ('OE3', RES, 'Comparación de metaheurísticas en secuenciación curricular adaptativa', 'Comparación de metaheurísticas', '—', '—', 'Resumen no disponible en OpenAlex', 'Comparable en diseño (compara metaheurísticas); texto no verificado'),
    '10.3390/app15137579': ('OE1/OE3', CTX, 'Personalización de textos STEM con agentes LLM', 'Dos agentes GPT-4 (Profiler, Rewrite) con paso de mensajes', 'n = 23 (ECA piloto)', 'Preferencia de texto; regresión logística ordinal', 'Sin cifras; los resultados "sugieren" que los estudiantes prefieren textos alineados con su perfil', 'Piloto pequeño; solo texto'),
    '10.11591/ijece.v13i2.pp1964-1978': ('OE3', CTX, 'Enfoque agente-orientado con algoritmo genético', 'Algoritmo genético con estrategias de inmigración', 'Experimento real con alumnos de primaria', 'Comparación con otros métodos de optimización', 'Alta tasa de éxito y compromiso (sin cifra en el resumen)', 'Sin cifras verificables'),
    '10.3390/math11132792': ('OE3', CTX, 'Recomendación de rutas con ACO de evolución saltatoria', 'SEACO', 'Datos de Open University', 'Convergencia y precisión', 'Resumen indica mejor convergencia y precisión (cifra no incluida en el fragmento)', 'Verificar cifras en el texto completo'),
    '10.1016/j.caeai.2022.100057': ('OE1/OE2', CTX, 'Mejora de la educación en línea con enfoque multiagente', 'Agentes ECA; agente organizador adaptativo', 'Casos de estudio con herramienta de validación', 'Concordancia del currículo con la preferencia', SC, 'Simulación; no mide latencia'),
    '10.1016/j.heliyon.2024.e39088': ('OE1', CTX, 'Recomendación de objetos de aprendizaje con SMA', 'Cuatro agentes; CNN y MLP', '—', '—', SC, 'Sin evaluación numérica en el resumen'),
    '10.1016/j.caeai.2024.100280': ('OE5', CTX, 'Ruta personalizada con ACO + TRI', 'ACO-IRT', '80 estudiantes (40+40)', 'Pretest/postest', 'Mejora de puntajes de 60,8 % a 127,8 %; p = 0,002', 'Resultado de aprendizaje, no de precisión de adaptación'),
    '10.1109/TLT.2025.3561332': ('OE1/OE3', CTX, 'Diseño instruccional con SMA basado en LLM', 'Evaluador, optimizador, analista; árbol de habilidades', 'Lecciones de matemáticas', 'CIDDP (5 dimensiones)', 'Sin cifras en el fragmento del resumen', 'Sin métricas de rendimiento computacional'),
    '10.3390/info16121045': ('OE1/OE5', CTX, 'Tutoría de programación con LLM', 'Arquitectura multimódulo', '—', 'Dominio, resolución de problemas', 'El resumen afirma que supera significativamente a los enfoques convencionales (sin cifras)', 'Sin cifras verificables'),
    '10.1109/4235.985692': ('OE3', MET, 'Estabilidad y convergencia de PSO', 'Análisis algebraico y analítico; coeficientes generalizados', 'Funciones de prueba', 'Convergencia', SC, 'Origen de los coeficientes de constricción w, c1, c2 usados por el artefacto'),
    '10.1007/s11831-021-09694-4': ('OE3', MET, 'Revisión sistemática de PSO', 'Revisión', 'Literatura 2017–2019', '—', SC, 'Contexto general'),
    '10.1109/JAS.2021.1004129': ('OE3', MET, 'Revisión de algoritmos de enjambre', 'Revisión de 127 trabajos', '127 referencias', '—', '127 referencias revisadas', 'Contexto general'),
    '10.1016/j.learninstruc.2005.07.001': ('OE5', CTX, 'Meta-análisis del efecto de modalidad', 'Meta-análisis', '—', 'Tamaño de efecto', 'Resumen no disponible en OpenAlex', 'Fundamento del valor de combinar modalidades; no evalúa el artefacto'),
    '10.1080/10494820.2020.1808794': ('OE5', CTX, 'Aprendizaje adaptativo vs enseñanza dirigida', 'Dos ECA; Squirrel AI', 'Octavo grado, dos provincias', 'Mejora en prueba de matemáticas', 'Mayores ganancias con el sistema adaptativo (sin cifra en el resumen)', 'Mide aprendizaje, no precisión de adaptación'),
    '10.3389/fcomp.2026.1777749': ('OE1/OE4', CTX, 'STI con grafos de conocimiento multimodales y RAG', 'FFmpeg, Whisper, OCR, RAG', '—', 'Precisión de QA, satisfacción, rendimiento del sistema', 'Sin cifras en el fragmento del resumen', 'Pipeline multimodal de ingesta, no adaptación por perfil'),
    '10.1186/s40561-024-00292-y': ('OE5', CTX, 'Herramienta de aprendizaje adaptativo en curso universitario', 'CogBooks en curso en línea/presencial', '—', 'Logro y satisfacción', 'El aprendizaje adaptativo mejora el logro en ambas modalidades (sin cifra en el resumen)', 'Contexto de aprendizaje, no técnico'),
    '10.1145/3501385.3543957': ('OE1', CTX, 'Generación de ejercicios y explicaciones de código con LLM', 'OpenAI Codex', '—', 'Evaluación cualitativa y cuantitativa', 'La mayoría del contenido generado es novedoso y sensato (sin cifra en el resumen)', 'Sin latencia ni throughput'),
    '10.1080/10447310802205776': ('OE5', RES, 'Evaluación empírica del SUS', 'Casi 10 años de datos SUS', 'Numerosos productos', 'SUS; escala de adjetivos', 'El resumen describe qué constituye un SUS aceptable y la escala de adjetivos (cifras no incluidas en el resumen)', 'Base de la referencia SUS >= 75 usada como meta; verificar valores en el texto completo'),
    '10.1016/j.heliyon.2024.e39630': ('OE5', CTX, 'Aprendizaje adaptativo personalizado en educación superior', 'Scoping review', '69 estudios', '—', '69 estudios elegibles', 'Revisión'),
    '10.3390/fi17120564': ('OE5', CTX, 'Marco STREAM de adaptación multimodal en tiempo real', 'Pipeline ASR+NLP; regeneración en formatos alternativos', 'Piloto de un video de 5 minutos', 'Cobertura de enlaces de procedencia; ablación', 'Piloto de viabilidad con un único video de 5 minutos (sin cifras de desempeño en el resumen)', 'Piloto muy acotado; sin latencia ni F1 de selección de modalidades'),
    '10.1016/j.caeai.2022.100110': ('OE1', CTX, 'Generación de contenido y rutas con IA para engagement', 'Fragmentos narrativos con GPT-2', '—', 'ROUGE', 'Evaluación con ROUGE frente a baselines (sin cifra en el fragmento)', 'Métricas textuales, no de arquitectura'),
    '10.1007/s10639-016-9472-2': ('OE3', CTX, 'STI con ACO', 'ACO; parámetros dinámicos', '—', '—', 'Mejora respecto a STI previos (sin cifra en el resumen)', 'Sin cifras'),
    '10.1016/j.sasc.2024.200091': ('OE3', CTX, 'Planeación de rutas con ACO y variabilidad', 'DTW + K-means + ACO', '—', 'Pérdida, exactitud, clasificación, finalización de objetivos', 'Pérdida mínima 0,1; exactitud hasta 0,9; clasificación 96,6 %; finalización de objetivos estable en 90 % (~20 % más que la comparación)', 'Cifras del autor; condiciones no verificadas; no es F1 multimodal'),
    '10.3390/math12162497': ('OE3', CTX, 'Recomendación diversa con ACO continuo', 'AcoRec', 'MovieLens, Pinterest, Netflix', 'Calidad top-N', 'Supera a modelos de referencia (sin cifra en el resumen)', 'Dominio de recomendación general'),
    '10.1007/s10639-017-9637-7': ('OE3', RES, 'Recomendación de rutas con GA de longitud variable', 'GA modificado', '—', '—', 'Resumen no disponible en OpenAlex', 'Comparable metodológicamente; texto no verificado'),
}
rows = []
for doi, v in A.items():
    if doi not in M:
        continue
    m = M[doi]
    oe, comp, prob, met, mues, metr, res, lim = v
    au = '; '.join(m.get('authors', []))
    ref = f"{au} ({m.get('year')}). {m.get('title')}. {m.get('container')}"
    ref += (f", {m['volume']}" if m.get('volume') else '') + (f"({m['issue']})" if m.get('issue') else '') + (f", {m['page']}" if m.get('page') else '') + f". https://doi.org/{doi}"
    rows.append(dict(referencia=html.unescape(ref), doi=doi, anio=m.get('year'), venue=html.unescape(m.get('container') or ''), problema=prob, metodo_sistema=met,
                     muestra_ejecuciones=mues, metricas=metr, resultados_publicados=res,
                     condiciones='Las del estudio original; no equivalentes a las de la tesis (perfiles sintéticos, un host, Redis/Python)', limitaciones=lim,
                     objetivo_tesis=oe, comparabilidad=comp, verificacion='Resumen verificado (OpenAlex)' if m.get('abstract') else 'Solo metadatos (Crossref); sin resumen',
                     doi_crossref='OK', en_bibliografia_tesis='Sí' if doi in TH else 'No (candidata)'))
rows.append(dict(referencia='Wu, Z., Li, J., & Huang, H. (2025). MAGMA-Edu: Multi-Agent Generative Multimodal Framework for Text-Diagram Educational Question Generation. arXiv:2511.18714. https://doi.org/10.48550/arXiv.2511.18714',
                 doi='10.48550/arXiv.2511.18714', anio=2025, venue='arXiv (preprint; sin revisión por pares verificada)', problema='Generación multimodal texto–diagrama de preguntas educativas',
                 metodo_sistema='SMA autorreflexivo con ciclo generación–verificación–reflexión', muestra_ejecuciones='No indicada en el resumen',
                 metricas='Métricas textuales promedio; consistencia imagen–texto (ITC)',
                 resultados_publicados='Texto: 57,01 a 92,31 frente a GPT-4o (+35,3 pp); ITC: 13,20 a 85,24 (+72 pp); máximos entre backbones: texto 96,20, ITC 99,12',
                 condiciones='Comparación contra GPT-4o; condiciones del preprint', limitaciones='Preprint; mide calidad de generación, no latencia ni throughput; no es selección de modalidades por perfil',
                 objetivo_tesis='OE5', comparabilidad=CTX, verificacion='Resumen verificado (WebFetch arXiv)', doi_crossref='DOI de arXiv', en_bibliografia_tesis='No (candidata)'))
with open('state_of_art/ESTADO_DEL_ARTE_MATRIZ.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(len(rows), Counter(r['comparabilidad'] for r in rows), Counter(r['en_bibliografia_tesis'] for r in rows), Counter(r['verificacion'] for r in rows))
