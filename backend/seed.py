"""
Script de seed institucional UPAO.
Crea malla curricular completa, competencias, usuarios y datos de prueba.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.base import Base
from app.db.session import engine
from app.models import (
    User, UserRole,
    Course, CourseStatus,
    LearningObjective,
    Resource, ResourceType,
    Enrollment, EnrollmentStatus,
    Competency, CompetencyType,
    CourseCompetency,
    InstitutionalCourse, InstitutionalCoursePrerequisite,
)
from app.core.security import get_password_hash

MALLA_CURRICULAR = {
    1: [
        {"code": "MAT101", "name": "Matemática Básica", "objectives": [
            {"title": "Números reales y operaciones", "description": "Conjuntos numéricos, propiedades y operaciones", "bloom_level": 1, "order": 1},
            {"title": "Funciones y gráficas", "description": "Tipos de funciones, dominio y rango", "bloom_level": 2, "order": 2},
            {"title": "Límites y continuidad", "description": "Concepto de límite, propiedades y cálculo", "bloom_level": 3, "order": 3},
        ]},
        {"code": "SIS101", "name": "Introducción a la Ingeniería de Sistemas", "objectives": [
            {"title": "Fundamentos de sistemas", "description": "Conceptos básicos de sistemas y tecnología", "bloom_level": 1, "order": 1},
            {"title": "Historia y evolución", "description": "Evolución de la computación y sistemas", "bloom_level": 1, "order": 2},
            {"title": "Perfil profesional", "description": "Campo laboral del ingeniero de sistemas", "bloom_level": 2, "order": 3},
        ]},
        {"code": "COM101", "name": "Comunicación I", "objectives": [
            {"title": "Comunicación efectiva", "description": "Principios de comunicación oral y escrita", "bloom_level": 1, "order": 1},
            {"title": "Redacción académica", "description": "Estructura de textos académicos", "bloom_level": 2, "order": 2},
            {"title": "Oratoria básica", "description": "Técnicas de presentación oral", "bloom_level": 3, "order": 3},
        ]},
        {"code": "MET101", "name": "Metodología del Aprendizaje Universitario", "objectives": [
            {"title": "Técnicas de estudio", "description": "Métodos efectivos de aprendizaje", "bloom_level": 1, "order": 1},
            {"title": "Gestión del tiempo", "description": "Planificación y organización académica", "bloom_level": 2, "order": 2},
            {"title": "Investigación básica", "description": "Introducción a la investigación académica", "bloom_level": 3, "order": 3},
        ]},
        {"code": "FIS101", "name": "Física General", "objectives": [
            {"title": "Mecánica clásica", "description": "Leyes de Newton y movimiento", "bloom_level": 2, "order": 1},
            {"title": "Energía y trabajo", "description": "Conceptos de energía cinética y potencial", "bloom_level": 3, "order": 2},
            {"title": "Ondas y sonido", "description": "Propiedades de las ondas", "bloom_level": 2, "order": 3},
        ]},
        {"code": "DES101", "name": "Desarrollo Personal y Liderazgo", "objectives": [
            {"title": "Autoconocimiento", "description": "Inteligencia emocional y autoestima", "bloom_level": 1, "order": 1},
            {"title": "Liderazgo", "description": "Estilos de liderazgo y trabajo en equipo", "bloom_level": 2, "order": 2},
            {"title": "Proyecto de vida", "description": "Planificación de metas personales", "bloom_level": 3, "order": 3},
        ]},
    ],
    2: [
        {"code": "MAT201", "name": "Matemática Aplicada", "objectives": [
            {"title": "Álgebra lineal", "description": "Matrices, determinantes y sistemas", "bloom_level": 2, "order": 1},
            {"title": "Cálculo diferencial", "description": "Derivadas y aplicaciones", "bloom_level": 3, "order": 2},
            {"title": "Cálculo integral", "description": "Integrales y aplicaciones", "bloom_level": 3, "order": 3},
        ]},
        {"code": "PRO201", "name": "Programación I", "objectives": [
            {"title": "Fundamentos de programación", "description": "Algoritmos, variables y tipos de datos", "bloom_level": 1, "order": 1},
            {"title": "Estructuras de control", "description": "Condicionales y bucles", "bloom_level": 2, "order": 2},
            {"title": "Funciones y módulos", "description": "Modularización del código", "bloom_level": 3, "order": 3},
        ]},
        {"code": "ARQ201", "name": "Arquitectura de Computadoras", "objectives": [
            {"title": "Componentes del computador", "description": "CPU, memoria y periféricos", "bloom_level": 1, "order": 1},
            {"title": "Representación de datos", "description": "Sistemas numéricos y codificación", "bloom_level": 2, "order": 2},
            {"title": "Ensamblador básico", "description": "Introducción al lenguaje ensamblador", "bloom_level": 3, "order": 3},
        ]},
        {"code": "COM201", "name": "Comunicación II", "objectives": [
            {"title": "Comunicación profesional", "description": "Redacción de informes y reportes", "bloom_level": 2, "order": 1},
            {"title": "Presentaciones efectivas", "description": "Diseño y exposición de presentaciones", "bloom_level": 3, "order": 2},
            {"title": "Comunicación digital", "description": "Herramientas de comunicación virtual", "bloom_level": 2, "order": 3},
        ]},
        {"code": "EST201", "name": "Estadística General", "objectives": [
            {"title": "Estadística descriptiva", "description": "Medidas de tendencia central y dispersión", "bloom_level": 2, "order": 1},
            {"title": "Probabilidad", "description": "Conceptos básicos de probabilidad", "bloom_level": 2, "order": 2},
            {"title": "Distribuciones", "description": "Distribuciones de probabilidad", "bloom_level": 3, "order": 3},
        ]},
        {"code": "CIU201", "name": "Ciudadanía y Responsabilidad Social", "objectives": [
            {"title": "Ciudadanía activa", "description": "Derechos y deberes ciudadanos", "bloom_level": 1, "order": 1},
            {"title": "Responsabilidad social", "description": "Impacto social de la tecnología", "bloom_level": 2, "order": 2},
            {"title": "Desarrollo sostenible", "description": "Objetivos de desarrollo sostenible", "bloom_level": 2, "order": 3},
        ]},
    ],
    3: [
        {"code": "IS301", "name": "Fundamentos de Programación", "objectives": [
            {"title": "Fundamentos de Python", "description": "Variables, tipos de datos, operadores", "bloom_level": 1, "order": 1},
            {"title": "Estructuras de control", "description": "If, for, while, comprensiones", "bloom_level": 2, "order": 2},
            {"title": "Funciones y módulos", "description": "Definición, parámetros, retorno, importación", "bloom_level": 3, "order": 3},
            {"title": "Programación orientada a objetos", "description": "Clases, objetos, herencia, polimorfismo", "bloom_level": 4, "order": 4},
        ]},
        {"code": "MAT301", "name": "Matemática Discreta", "objectives": [
            {"title": "Lógica proposicional", "description": "Tablas de verdad y demostraciones", "bloom_level": 2, "order": 1},
            {"title": "Teoría de conjuntos", "description": "Operaciones y relaciones entre conjuntos", "bloom_level": 2, "order": 2},
            {"title": "Grafos y árboles", "description": "Estructuras discretas fundamentales", "bloom_level": 3, "order": 3},
        ]},
        {"code": "EST301", "name": "Estructuras Digitales", "objectives": [
            {"title": "Sistemas digitales", "description": "Puertas lógicas y circuitos", "bloom_level": 1, "order": 1},
            {"title": "Álgebra booleana", "description": "Simplificación de funciones lógicas", "bloom_level": 3, "order": 2},
            {"title": "Circuitos secuenciales", "description": "Flip-flops y registros", "bloom_level": 4, "order": 3},
        ]},
        {"code": "BD301", "name": "Base de Datos I", "objectives": [
            {"title": "Modelo relacional", "description": "Tablas, claves y relaciones", "bloom_level": 2, "order": 1},
            {"title": "SQL básico", "description": "Consultas SELECT, INSERT, UPDATE, DELETE", "bloom_level": 3, "order": 2},
            {"title": "Normalización", "description": "Formas normales y diseño", "bloom_level": 4, "order": 3},
        ]},
        {"code": "SO301", "name": "Sistemas Operativos", "objectives": [
            {"title": "Fundamentos de SO", "description": "Funciones y tipos de sistemas operativos", "bloom_level": 1, "order": 1},
            {"title": "Gestión de procesos", "description": "Planificación y sincronización", "bloom_level": 3, "order": 2},
            {"title": "Gestión de memoria", "description": "Paginación y segmentación", "bloom_level": 3, "order": 3},
        ]},
        {"code": "INV301", "name": "Investigación Académica", "objectives": [
            {"title": "Métodos de investigación", "description": "Diseño metodológico", "bloom_level": 2, "order": 1},
            {"title": "Revisión bibliográfica", "description": "Búsqueda y análisis de fuentes", "bloom_level": 3, "order": 2},
            {"title": "Artículo científico", "description": "Estructura y redacción de artículos", "bloom_level": 4, "order": 3},
        ]},
    ],
    4: [
        {"code": "POO401", "name": "Programación Orientada a Objetos", "objectives": [
            {"title": "Principios OOP", "description": "Encapsulamiento, herencia, polimorfismo", "bloom_level": 2, "order": 1},
            {"title": "Patrones de diseño", "description": "Singleton, Factory, Observer", "bloom_level": 4, "order": 2},
            {"title": "Desarrollo avanzado", "description": "Excepciones, genéricos, colecciones", "bloom_level": 3, "order": 3},
        ]},
        {"code": "BD401", "name": "Base de Datos II", "objectives": [
            {"title": "SQL avanzado", "description": "Joins, subconsultas, procedimientos", "bloom_level": 3, "order": 1},
            {"title": "Optimización", "description": "Índices y planes de ejecución", "bloom_level": 4, "order": 2},
            {"title": "Bases de datos NoSQL", "description": "MongoDB, Redis, Cassandra", "bloom_level": 3, "order": 3},
        ]},
        {"code": "RED401", "name": "Redes y Comunicaciones", "objectives": [
            {"title": "Modelo OSI y TCP/IP", "description": "Capas y protocolos de red", "bloom_level": 2, "order": 1},
            {"title": "Configuración de redes", "description": "Routers, switches y firewalls", "bloom_level": 3, "order": 2},
            {"title": "Seguridad de redes", "description": "Criptografía y protección", "bloom_level": 4, "order": 3},
        ]},
        {"code": "REQ401", "name": "Ingeniería de Requisitos", "objectives": [
            {"title": "Elicitación", "description": "Técnicas de recopilación de requisitos", "bloom_level": 2, "order": 1},
            {"title": "Especificación", "description": "Documentación de requisitos funcionales", "bloom_level": 3, "order": 2},
            {"title": "Validación", "description": "Verificación y gestión de cambios", "bloom_level": 4, "order": 3},
        ]},
        {"code": "ALG401", "name": "Diseño de Algoritmos", "objectives": [
            {"title": "Análisis de complejidad", "description": "Notación Big-O y análisis asintótico", "bloom_level": 3, "order": 1},
            {"title": "Algoritmos de ordenamiento", "description": "QuickSort, MergeSort, HeapSort", "bloom_level": 3, "order": 2},
            {"title": "Algoritmos greedy y DP", "description": "Programación dinámica", "bloom_level": 4, "order": 3},
        ]},
        {"code": "ETI401", "name": "Ética Profesional", "objectives": [
            {"title": "Ética en TI", "description": "Código de ética profesional", "bloom_level": 1, "order": 1},
            {"title": "Privacidad de datos", "description": "Protección de información personal", "bloom_level": 2, "order": 2},
            {"title": "Impacto social", "description": "Responsabilidad ética del ingeniero", "bloom_level": 3, "order": 3},
        ]},
    ],
    5: [
        {"code": "IS501", "name": "Ingeniería de Software", "objectives": [
            {"title": "Ciclo de vida del software", "description": "Modelos de desarrollo y metodologías", "bloom_level": 2, "order": 1},
            {"title": "Metodologías ágiles", "description": "Scrum, Kanban, XP", "bloom_level": 3, "order": 2},
            {"title": "Arquitectura de software", "description": "Patrones y estilos arquitectónicos", "bloom_level": 4, "order": 3},
        ]},
        {"code": "IA501", "name": "Inteligencia Artificial", "objectives": [
            {"title": "Fundamentos de IA", "description": "Historia, agentes y búsqueda", "bloom_level": 1, "order": 1},
            {"title": "Machine Learning", "description": "Algoritmos supervisados y no supervisados", "bloom_level": 3, "order": 2},
            {"title": "Redes neuronales", "description": "Perceptrón, backpropagation, deep learning", "bloom_level": 4, "order": 3},
        ]},
        {"code": "WEB501", "name": "Desarrollo Web", "objectives": [
            {"title": "Frontend moderno", "description": "HTML5, CSS3, JavaScript, frameworks", "bloom_level": 2, "order": 1},
            {"title": "Backend y APIs", "description": "REST, autenticación, bases de datos", "bloom_level": 3, "order": 2},
            {"title": "Despliegue", "description": "Docker, CI/CD, cloud", "bloom_level": 4, "order": 3},
        ]},
        {"code": "PM501", "name": "Gestión de Proyectos TI", "objectives": [
            {"title": "Planificación", "description": "WBS, cronograma y presupuesto", "bloom_level": 2, "order": 1},
            {"title": "Gestión de riesgos", "description": "Identificación y mitigación", "bloom_level": 3, "order": 2},
            {"title": "Seguimiento", "description": "KPIs y métricas de proyecto", "bloom_level": 4, "order": 3},
        ]},
        {"code": "ADS501", "name": "Análisis y Diseño de Sistemas", "objectives": [
            {"title": "Modelado UML", "description": "Diagramas de clases, casos de uso, secuencia", "bloom_level": 2, "order": 1},
            {"title": "Diseño de sistemas", "description": "Arquitectura y componentes", "bloom_level": 3, "order": 2},
            {"title": "Prototipado", "description": "Wireframes y prototipos interactivos", "bloom_level": 4, "order": 3},
        ]},
        {"code": "IHC501", "name": "Interacción Humano Computadora", "objectives": [
            {"title": "Principios de UX", "description": "Usabilidad y accesibilidad", "bloom_level": 2, "order": 1},
            {"title": "Diseño centrado en usuario", "description": "Research y testing de usuarios", "bloom_level": 3, "order": 2},
            {"title": "Evaluación de interfaces", "description": "Heurísticas y métricas de UX", "bloom_level": 4, "order": 3},
        ]},
    ],
    6: [
        {"code": "CY601", "name": "Ciberseguridad", "objectives": [
            {"title": "Fundamentos de seguridad", "description": "Amenazas, vulnerabilidades y controles", "bloom_level": 2, "order": 1},
            {"title": "Criptografía aplicada", "description": "Algoritmos y protocolos seguros", "bloom_level": 3, "order": 2},
            {"title": "Auditoría de seguridad", "description": "Pentesting y análisis de riesgos", "bloom_level": 4, "order": 3},
        ]},
        {"code": "CD601", "name": "Ciencia de Datos", "objectives": [
            {"title": "Análisis exploratorio", "description": "Visualización y estadística aplicada", "bloom_level": 2, "order": 1},
            {"title": "Machine Learning aplicado", "description": "Modelos predictivos y evaluación", "bloom_level": 3, "order": 2},
            {"title": "Big Data", "description": "Hadoop, Spark y procesamiento distribuido", "bloom_level": 4, "order": 3},
        ]},
        {"code": "MOB601", "name": "Desarrollo Móvil", "objectives": [
            {"title": "Plataformas móviles", "description": "Android e iOS", "bloom_level": 2, "order": 1},
            {"title": "Frameworks cross-platform", "description": "React Native, Flutter", "bloom_level": 3, "order": 2},
            {"title": "Publicación", "description": "App stores y monetización", "bloom_level": 4, "order": 3},
        ]},
    ],
    7: [
        {"code": "CC701", "name": "Computación en la Nube", "objectives": [
            {"title": "Modelos de servicio", "description": "IaaS, PaaS, SaaS", "bloom_level": 2, "order": 1},
            {"title": "AWS/Azure", "description": "Servicios cloud principales", "bloom_level": 3, "order": 2},
            {"title": "Arquitectura cloud", "description": "Serverless, microservicios", "bloom_level": 4, "order": 3},
        ]},
        {"code": "NLP701", "name": "Procesamiento de Lenguaje Natural", "objectives": [
            {"title": "Fundamentos de NLP", "description": "Tokenización, stemming, POS tagging", "bloom_level": 2, "order": 1},
            {"title": "Modelos de lenguaje", "description": "Transformers y LLMs", "bloom_level": 3, "order": 2},
            {"title": "Aplicaciones", "description": "Chatbots, análisis de sentimientos", "bloom_level": 4, "order": 3},
        ]},
        {"code": "CV701", "name": "Visión por Computadora", "objectives": [
            {"title": "Procesamiento de imágenes", "description": "Filtros, detección de bordes", "bloom_level": 2, "order": 1},
            {"title": "Redes convolucionales", "description": "CNNs y transferencia de aprendizaje", "bloom_level": 3, "order": 2},
            {"title": "Aplicaciones", "description": "Detección de objetos, segmentación", "bloom_level": 4, "order": 3},
        ]},
    ],
    8: [
        {"code": "IOT801", "name": "Internet de las Cosas", "objectives": [
            {"title": "Arquitectura IoT", "description": "Sensores, actuadores y protocolos", "bloom_level": 2, "order": 1},
            {"title": "Plataformas IoT", "description": "MQTT, CoAP, plataformas cloud", "bloom_level": 3, "order": 2},
            {"title": "Proyectos IoT", "description": "Diseño e implementación de sistemas", "bloom_level": 4, "order": 3},
        ]},
        {"code": "DL801", "name": "Deep Learning", "objectives": [
            {"title": "Redes profundas", "description": "Arquitecturas avanzadas", "bloom_level": 3, "order": 1},
            {"title": "Frameworks", "description": "TensorFlow, PyTorch", "bloom_level": 3, "order": 2},
            {"title": "Proyectos avanzados", "description": "GANs, RL, modelos generativos", "bloom_level": 5, "order": 3},
        ]},
        {"code": "DEV801", "name": "DevOps", "objectives": [
            {"title": "CI/CD", "description": "Integración y entrega continua", "bloom_level": 3, "order": 1},
            {"title": "Infraestructura como código", "description": "Terraform, Ansible", "bloom_level": 3, "order": 2},
            {"title": "Monitoreo", "description": "Logging, alerting, observabilidad", "bloom_level": 4, "order": 3},
        ]},
    ],
    9: [
        {"code": "SEM901", "name": "Seminario de Investigación I", "objectives": [
            {"title": "Estado del arte", "description": "Revisión sistemática de literatura", "bloom_level": 4, "order": 1},
            {"title": "Propuesta de investigación", "description": "Formulación de hipótesis y metodología", "bloom_level": 5, "order": 2},
            {"title": "Prototipo inicial", "description": "Desarrollo de prueba de concepto", "bloom_level": 5, "order": 3},
        ]},
        {"code": "EMP901", "name": "Emprendimiento Tecnológico", "objectives": [
            {"title": "Modelos de negocio", "description": "Lean Canvas, Business Model Canvas", "bloom_level": 2, "order": 1},
            {"title": "Validación", "description": "MVP y validación con usuarios", "bloom_level": 3, "order": 2},
            {"title": "Pitch y financiamiento", "description": "Presentación a inversores", "bloom_level": 4, "order": 3},
        ]},
        {"code": "GOB901", "name": "Gobierno de TI", "objectives": [
            {"title": "Frameworks", "description": "ITIL, COBIT, ISO 27001", "bloom_level": 2, "order": 1},
            {"title": "Alineación estratégica", "description": "TI y objetivos de negocio", "bloom_level": 3, "order": 2},
            {"title": "Gestión de servicios", "description": "SLA, KPI, mejora continua", "bloom_level": 4, "order": 3},
        ]},
    ],
    10: [
        {"code": "TES1001", "name": "Tesis de Grado", "objectives": [
            {"title": "Desarrollo de investigación", "description": "Ejecución del proyecto de tesis", "bloom_level": 5, "order": 1},
            {"title": "Análisis de resultados", "description": "Evaluación y validación", "bloom_level": 5, "order": 2},
            {"title": "Sustentación", "description": "Defensa del trabajo de investigación", "bloom_level": 6, "order": 3},
        ]},
        {"code": "PRA1001", "name": "Prácticas Pre-Profesionales", "objectives": [
            {"title": "Inmersión laboral", "description": "Integración en equipo de trabajo", "bloom_level": 2, "order": 1},
            {"title": "Proyecto profesional", "description": "Contribución real en la empresa", "bloom_level": 4, "order": 2},
            {"title": "Informe final", "description": "Documentación de experiencias", "bloom_level": 5, "order": 3},
        ]},
    ],
}

COURSE_COMPETENCY_MAP = {
    1: {
        "MAT101": ["Pensamiento Lógico Matemático", "Pensamiento Computacional"],
        "SIS101": ["Desarrollo de Software", "Pensamiento Computacional", "Gestión de la Información"],
        "COM101": ["Comunicación"],
        "MET101": ["Aprendizaje e Investigación", "Autonomía y Adaptación"],
        "FIS101": ["Pensamiento Lógico Matemático"],
        "DES101": ["Emprendimiento y Liderazgo", "Responsabilidad Social"],
    },
    2: {
        "MAT201": ["Pensamiento Lógico Matemático"],
        "PRO201": ["Desarrollo de Software", "Pensamiento Computacional"],
        "ARQ201": ["Arquitectura de Sistemas", "Pensamiento Computacional"],
        "COM201": ["Comunicación"],
        "EST201": ["Pensamiento Lógico Matemático", "Gestión de la Información"],
        "CIU201": ["Responsabilidad Social", "Ética y Diversidad"],
    },
    3: {
        "IS301": ["Desarrollo de Software", "Pensamiento Computacional"],
        "MAT301": ["Pensamiento Lógico Matemático"],
        "EST301": ["Arquitectura de Sistemas", "Pensamiento Computacional"],
        "BD301": ["Bases de Datos", "Gestión de la Información"],
        "SO301": ["Arquitectura de Sistemas"],
        "INV301": ["Aprendizaje e Investigación"],
    },
    4: {
        "POO401": ["Desarrollo de Software"],
        "BD401": ["Bases de Datos", "Gestión de la Información"],
        "RED401": ["Redes y Comunicaciones"],
        "REQ401": ["Ingeniería de Requisitos"],
        "ALG401": ["Pensamiento Computacional", "Pensamiento Lógico Matemático"],
        "ETI401": ["Ética y Diversidad"],
    },
    5: {
        "IS501": ["Desarrollo de Software", "Arquitectura de Sistemas"],
        "IA501": ["Inteligencia Artificial", "Ciencia de Datos"],
        "WEB501": ["Desarrollo de Software"],
        "PM501": ["Emprendimiento y Liderazgo", "Gestión de la Información"],
        "ADS501": ["Arquitectura de Sistemas", "Ingeniería de Requisitos"],
        "IHC501": ["Desarrollo de Software", "Comunicación"],
    },
    6: {
        "CY601": ["Arquitectura de Sistemas", "Gestión de la Información"],
        "CD601": ["Ciencia de Datos", "Inteligencia Artificial"],
        "MOB601": ["Desarrollo de Software"],
    },
    7: {
        "CC701": ["Arquitectura de Sistemas", "Redes y Comunicaciones"],
        "NLP701": ["Inteligencia Artificial", "Sistemas Inteligentes"],
        "CV701": ["Inteligencia Artificial", "Sistemas Inteligentes"],
    },
    8: {
        "IOT801": ["Arquitectura de Sistemas", "Analítica y Automatización"],
        "DL801": ["Inteligencia Artificial", "Ciencia de Datos"],
        "DEV801": ["Desarrollo de Software", "Arquitectura de Sistemas"],
    },
    9: {
        "SEM901": ["Aprendizaje e Investigación"],
        "EMP901": ["Emprendimiento y Liderazgo"],
        "GOB901": ["Arquitectura de Sistemas", "Gestión de la Información"],
    },
    10: {
        "TES1001": ["Aprendizaje e Investigación"],
        "PRA1001": ["Emprendimiento y Liderazgo", "Responsabilidad Social"],
    },
}


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ===== CURRÍCULUM INSTITUCIONAL (MALLA ISIA 2025) =====
        seed_institutional_courses(db)

        # ===== USUARIOS =====
        admin = db.query(User).filter(User.email == "admin@upao.edu.pe").first()
        if not admin:
            admin = User(
                email="admin@upao.edu.pe",
                hashed_password=get_password_hash("Admin2026!"),
                first_name="Admin",
                last_name="Sistema",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            print("[OK] Admin: admin@upao.edu.pe / Admin2026!")

        docente = db.query(User).filter(User.email == "docente@upao.edu.pe").first()
        if not docente:
            docente = User(
                email="docente@upao.edu.pe",
                hashed_password=get_password_hash("Docente2026!"),
                first_name="Juan",
                last_name="Pérez",
                role=UserRole.DOCENTE,
                institutional_code="DOC001",
                area="Ingeniería de Software",
                is_active=True,
            )
            db.add(docente)
            print("[OK] Docente: docente@upao.edu.pe / Docente2026!")

        estudiante3 = db.query(User).filter(User.email == "estudiante3@upao.edu.pe").first()
        if not estudiante3:
            estudiante3 = User(
                email="estudiante3@upao.edu.pe",
                hashed_password=get_password_hash("Student2026!"),
                first_name="Maria",
                last_name="Garcia",
                role=UserRole.ESTUDIANTE,
                institutional_code="202312345",
                current_cycle=3,
                is_active=True,
            )
            db.add(estudiante3)
            print("[OK] Estudiante ciclo 3: estudiante3@upao.edu.pe / Student2026!")

        estudiante5 = db.query(User).filter(User.email == "estudiante5@upao.edu.pe").first()
        if not estudiante5:
            estudiante5 = User(
                email="estudiante5@upao.edu.pe",
                hashed_password=get_password_hash("Student2026!"),
                first_name="Carlos",
                last_name="Rodriguez",
                role=UserRole.ESTUDIANTE,
                institutional_code="202254321",
                current_cycle=5,
                is_active=True,
            )
            db.add(estudiante5)
            print("[OK] Estudiante ciclo 5: estudiante5@upao.edu.pe / Student2026!")

        db.commit()

        # ===== COMPETENCIAS INSTITUCIONALES UPAO =====
        institutional_competencies = [
            ("Comunicación", "Utiliza comunicación oral y escrita de forma efectiva."),
            ("Pensamiento Lógico Matemático", "Resuelve problemas usando estrategias matemáticas y computacionales."),
            ("Gestión de la Información", "Busca, procesa y utiliza información usando TIC."),
            ("Responsabilidad Social", "Actúa con compromiso ciudadano y desarrollo sostenible."),
            ("Ética y Diversidad", "Actúa con compromiso ético y respeto cultural."),
            ("Aprendizaje e Investigación", "Desarrolla aprendizaje autónomo e investigación interdisciplinaria."),
            ("Autonomía y Adaptación", "Aprende autónomamente y se adapta a cambios."),
            ("Emprendimiento y Liderazgo", "Demuestra liderazgo, creatividad e innovación."),
        ]

        inst_comp_map = {}
        for name, desc in institutional_competencies:
            existing = db.query(Competency).filter(
                Competency.name == name,
                Competency.competency_type == CompetencyType.INSTITUTIONAL,
            ).first()
            if not existing:
                comp = Competency(
                    name=name,
                    description=desc,
                    competency_type=CompetencyType.INSTITUTIONAL,
                    active=True,
                )
                db.add(comp)
                db.flush()
                inst_comp_map[name] = comp.id
                print(f"  [OK] Competencia institucional: {name}")
            else:
                inst_comp_map[name] = existing.id

        # ===== COMPETENCIAS DE CARRERA =====
        career_competencies = [
            "Desarrollo de Software",
            "Inteligencia Artificial",
            "Ciencia de Datos",
            "Arquitectura de Sistemas",
            "Ingeniería de Requisitos",
            "Bases de Datos",
            "Redes y Comunicaciones",
            "Pensamiento Computacional",
            "Sistemas Inteligentes",
            "Analítica y Automatización",
        ]

        career_comp_map = {}
        for name in career_competencies:
            existing = db.query(Competency).filter(
                Competency.name == name,
                Competency.competency_type == CompetencyType.CAREER,
            ).first()
            if not existing:
                comp = Competency(
                    name=name,
                    competency_type=CompetencyType.CAREER,
                    active=True,
                )
                db.add(comp)
                db.flush()
                career_comp_map[name] = comp.id
                print(f"  [OK] Competencia de carrera: {name}")
            else:
                career_comp_map[name] = existing.id

        db.commit()

        # ===== MALLA CURRICULAR =====
        course_map = {}
        for cycle, courses_data in MALLA_CURRICULAR.items():
            for cd in courses_data:
                existing = db.query(Course).filter(Course.code == cd["code"]).first()
                if existing:
                    course_map[cd["code"]] = existing
                    continue

                course = Course(
                    code=cd["code"],
                    name=cd["name"],
                    description=f"Curso del ciclo {cycle} de Ingeniería de Sistemas e Inteligencia Artificial",
                    cycle=cycle,
                    year=2026,
                    teacher_id=docente.id,
                    status=CourseStatus.PUBLICADO,
                )
                db.add(course)
                db.flush()
                course_map[cd["code"]] = course
                print(f"[OK] Curso: {cd['code']} {cd['name']} (ciclo {cycle})")

                for obj_data in cd["objectives"]:
                    obj = LearningObjective(
                        course_id=course.id,
                        title=obj_data["title"],
                        description=obj_data["description"],
                        bloom_level=obj_data["bloom_level"],
                        order=obj_data["order"],
                    )
                    db.add(obj)

                comp_names = COURSE_COMPETENCY_MAP.get(cycle, {}).get(cd["code"], [])
                for comp_name in comp_names:
                    comp_id = career_comp_map.get(comp_name) or inst_comp_map.get(comp_name)
                    if comp_id:
                        cc = CourseCompetency(course_id=course.id, competency_id=comp_id)
                        db.add(cc)

        db.commit()

        # ===== INSCRIPCIONES AUTOMÁTICAS =====
        ciclo_students = {3: estudiante3, 5: estudiante5}
        for cycle, student in ciclo_students.items():
            if not student:
                continue
            courses_in_cycle = [c for c in course_map.values() if c.cycle == cycle]
            for course in courses_in_cycle:
                existing_enroll = (
                    db.query(Enrollment)
                    .filter(
                        Enrollment.course_id == course.id,
                        Enrollment.student_id == student.id,
                    )
                    .first()
                )
                if not existing_enroll:
                    enrollment = Enrollment(
                        course_id=course.id,
                        student_id=student.id,
                        status=EnrollmentStatus.ACTIVO,
                    )
                    db.add(enrollment)

        db.commit()

        print(f"\n[OK] Seed institucional completado exitosamente")
        print(f"\n[INFO] Usuarios de prueba:")
        print(f"  Admin:         admin@upao.edu.pe / Admin2026!")
        print(f"  Docente:       docente@upao.edu.pe / Docente2026!")
        print(f"  Estudiante 3:  estudiante3@upao.edu.pe / Student2026!")
        print(f"  Estudiante 5:  estudiante5@upao.edu.pe / Student2026!")
        print(f"\n[INFO] Cursos por ciclo:")
        for cycle in range(1, 11):
            count = sum(1 for c in course_map.values() if c.cycle == cycle)
            if count > 0:
                print(f"  Ciclo {cycle}: {count} cursos")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error en seed: {e}")
        raise
    finally:
        db.close()


def seed_institutional_courses(db):
    """Siembra los cursos institucionales desde la malla curricular oficial ISIA 2025."""
    existing = db.query(InstitutionalCourse).first()
    if existing:
        return

    ISIA_2025_CYCLES = {
        1: [
            ("MAT101", "Matemática Básica", 4, 2, 2, 0),
            ("SIS101", "Introducción a la Ingeniería de Sistemas e IA", 3, 2, 2, 0),
            ("COM101", "Comunicación I", 3, 2, 2, 0),
            ("MET101", "Metodología del Aprendizaje Universitario", 2, 1, 2, 0),
            ("FIS101", "Física General", 4, 2, 2, 2),
        ],
        2: [
            ("MAT102", "Cálculo Diferencial", 4, 2, 2, 0),
            ("SIS102", "Programación I", 4, 2, 2, 2),
            ("COM102", "Comunicación II", 3, 2, 2, 0),
            ("MAT103", "Álgebra Lineal", 3, 2, 2, 0),
            ("SIS103", "Fundamentos de Computación", 3, 2, 2, 0),
        ],
        3: [
            ("MAT201", "Cálculo Integral", 4, 2, 2, 0),
            ("SIS201", "Programación II", 4, 2, 2, 2),
            ("EST201", "Estadística I", 3, 2, 2, 0),
            ("SIS202", "Base de Datos I", 4, 2, 2, 2),
            ("SIS203", "Sistemas Operativos", 3, 2, 2, 0),
        ],
        4: [
            ("MAT301", "Ecuaciones Diferenciales", 4, 2, 2, 0),
            ("SIS301", "Programación III (POO)", 4, 2, 2, 2),
            ("SIS302", "Base de Datos II", 4, 2, 2, 2),
            ("SIS303", "Redes y Comunicación", 3, 2, 2, 0),
            ("SIS304", "Diseño de Algoritmos", 3, 2, 2, 0),
        ],
        5: [
            ("SIS401", "Ingeniería de Software I", 4, 2, 2, 0),
            ("SIS402", "Inteligencia Artificial I", 4, 2, 2, 2),
            ("SIS403", "Desarrollo Web", 4, 2, 2, 2),
            ("SIS404", "Base de Datos III", 3, 2, 2, 0),
            ("SIS405", "Investigación de Operaciones", 3, 2, 2, 0),
        ],
        6: [
            ("SIS501", "Ciberseguridad", 3, 2, 2, 0),
            ("SIS502", "Ciencia de Datos I", 4, 2, 2, 2),
            ("SIS503", "Desarrollo Móvil", 4, 2, 2, 2),
            ("SIS504", "Ingeniería de Software II", 3, 2, 2, 0),
            ("SIS505", "Inteligencia Artificial II", 4, 2, 2, 2),
        ],
        7: [
            ("SIS601", "Cloud Computing", 3, 2, 2, 0),
            ("SIS602", "Procesamiento de Lenguaje Natural", 4, 2, 2, 2),
            ("SIS603", "Visión Computacional", 4, 2, 2, 2),
            ("SIS604", "Ciencia de Datos II", 3, 2, 2, 0),
            ("SIS605", "DevOps", 3, 2, 2, 0),
        ],
        8: [
            ("SIS701", "Internet de las Cosas", 3, 2, 2, 0),
            ("SIS702", "Deep Learning", 4, 2, 2, 2),
            ("SIS703", "DevOps Avanzado", 3, 2, 2, 0),
            ("SIS704", "Robótica", 3, 2, 2, 0),
            ("SIS705", "Ética Legal y Profesional", 2, 2, 0, 0),
        ],
        9: [
            ("SIS801", "Seminario de Investigación I", 3, 2, 2, 0),
            ("SIS802", "Gestión de Proyectos TI", 3, 2, 2, 0),
            ("SIS803", "Emprendimiento Digital", 3, 2, 2, 0),
            ("SIS804", "Ciberseguridad Avanzada", 3, 2, 2, 0),
            ("SIS805", "Análisis de Datos Masivos (Big Data)", 3, 2, 2, 0),
        ],
        10: [
            ("SIS901", "Seminario de Investigación II (Tesis)", 4, 2, 4, 0),
            ("SIS902", "Prácticas Pre-Profesionales", 6, 0, 6, 0),
            ("SIS903", "Evaluación de Proyectos", 3, 2, 2, 0),
            ("SIS904", "Gestión de la Innovación", 3, 2, 2, 0),
            ("SIS905", "Auditoría de Sistemas", 3, 2, 2, 0),
        ],
    }

    PREREQUISITES = {
        "SIS102": ["MAT101"],
        "MAT102": ["MAT101"],
        "MAT201": ["MAT102"],
        "MAT301": ["MAT201"],
        "SIS201": ["SIS102"],
        "SIS301": ["SIS201"],
        "SIS302": ["SIS202"],
        "SIS303": ["SIS203"],
        "SIS304": ["SIS201"],
        "SIS401": ["SIS301"],
        "SIS402": ["SIS301", "EST201"],
        "SIS403": ["SIS301"],
        "SIS404": ["SIS302"],
        "SIS405": ["EST201"],
        "SIS501": ["SIS303"],
        "SIS502": ["EST201", "SIS404"],
        "SIS503": ["SIS403"],
        "SIS504": ["SIS401"],
        "SIS505": ["SIS402", "SIS502"],
        "SIS601": ["SIS303"],
        "SIS602": ["SIS505"],
        "SIS603": ["SIS505"],
        "SIS604": ["SIS502"],
        "SIS605": ["SIS203"],
        "SIS701": ["SIS601"],
        "SIS702": ["SIS505", "SIS603"],
        "SIS703": ["SIS605"],
        "SIS704": ["SIS301", "MAT301"],
        "SIS801": ["SIS504"],
        "SIS802": ["SIS504"],
        "SIS803": ["SIS405"],
        "SIS804": ["SIS501"],
        "SIS805": ["SIS604"],
        "SIS901": ["SIS801"],
        "SIS903": ["SIS802"],
        "SIS904": ["SIS803"],
        "SIS905": ["SIS501"],
    }

    course_map = {}
    for cycle, courses in ISIA_2025_CYCLES.items():
        for code, name, credits, ht, hp, hl in courses:
            inst_course = InstitutionalCourse(
                code=code,
                name=name,
                credits=credits,
                cycle=cycle,
                hours_theory=ht,
                hours_practice=hp,
                hours_lab=hl,
            )
            db.add(inst_course)
            db.flush()
            course_map[code] = inst_course

    for code, prereq_codes in PREREQUISITES.items():
        course = course_map.get(code)
        if not course:
            continue
        for prereq_code in prereq_codes:
            prereq = course_map.get(prereq_code)
            if prereq:
                assoc = InstitutionalCoursePrerequisite(
                    course_id=course.id,
                    prerequisite_id=prereq.id,
                )
                db.add(assoc)

    db.commit()
    print(f"[OK] {len(course_map)} cursos institucionales sembrados desde la malla ISIA 2025")


if __name__ == "__main__":
    seed()
