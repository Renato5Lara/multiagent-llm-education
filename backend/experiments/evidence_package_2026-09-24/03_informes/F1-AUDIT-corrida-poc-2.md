# Auditoría de F1_adapt — corrida-poc-2 (solo diagnóstico; no modifica nada)

Biblioteca: `lib-v9-a0231e9b` · casos completados: 100

## 1. ¿Implementación incorrecta?
- Recomputo de la etiqueta predicha desde S: **0 discrepancias**.
- Etiqueta gold vs tabla preregistrada: **0 discrepancias**.
- Matriz de confusión recomputada por otro camino: **idéntica**; F1_adapt recomputado = 0.8031.

## 2. Matriz (filas gold, columnas predicción: code, diagram, text, audio)
```
[[42, 5, 3, 0], [5, 20, 0, 0], [4, 2, 19, 0], [0, 0, 0, 0]]
```
| clase | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|
| code | 42 | 9 | 8 | 0.824 | 0.840 | 0.832 |
| diagram | 20 | 7 | 5 | 0.741 | 0.800 | 0.769 |
| text | 19 | 3 | 6 | 0.864 | 0.760 | 0.809 |
| audio | 0 | 0 | 0 | — | — | — |

## 3. Errores por segmento

| arquetipo | n | errores | tasa |
|---|---|---|---|
| balanced_multimodal | 25 | 8 | 0.32 |
| explanatory_conceptual | 25 | 6 | 0.24 |
| logical_syntactic | 25 | 0 | 0.0 |
| visual_dominant | 25 | 5 | 0.2 |

| dificultad | n | errores | tasa |
|---|---|---|---|
| arrays_vectors | 20 | 3 | 0.15 |
| conditional | 20 | 4 | 0.2 |
| functions | 20 | 5 | 0.25 |
| repetitive | 20 | 5 | 0.25 |
| sequential | 20 | 2 | 0.1 |

| concepto | n | errores | tasa |
|---|---|---|---|
| Algoritmo | 2 | 1 | 0.5 |
| Bucle for | 5 | 2 | 0.4 |
| Bucle while | 5 | 1 | 0.2 |
| Bucles anidados | 5 | 2 | 0.4 |
| Búsqueda (in, .index()) | 4 | 2 | 0.5 |
| Condicionales básicos | 10 | 4 | 0.4 |
| Definición e invocación de funciones | 5 | 1 | 0.2 |
| Estructura y sintaxis básica de un programa en Python | 2 | 1 | 0.5 |
| Indexación | 4 | 1 | 0.25 |
| Parámetros y argumentos | 5 | 1 | 0.2 |
| Valores de retorno | 5 | 1 | 0.2 |
| Ámbito de variables | 5 | 2 | 0.4 |

| modalidad predicha | n | equivocadas |
|---|---|---|
| code | 51 | 9 |
| diagram | 27 | 7 |
| text | 22 | 3 |
| audio | 0 | 0 |

## 4. Atribución de los errores

| causa | casos |
|---|---|
| acierto | 81 |
| el óptimo global de 𝓕 no incluye la etiqueta gold (Coher/Redund/CostT dominan sobre Simil) | 6 |
| W(perfil) no favorece la modalidad gold (gold ≠ argmax W) | 13 |

## 5. Cotas de referencia (mismo gold, misma definición)

- F1 si la predicción fuese `argmax W` (con el desempate declarado): **0.615**
- F1 si la predicción fuese el **óptimo global de 𝓕** (fuerza bruta): **0.803**
- F1 medido: **0.803**
- Casos donde el gold ≠ argmax(W): 19 (ruido del muestreo de W / modulación frente al centroide del arquetipo)
- Casos donde ninguna configuración óptima de 𝓕 produce la etiqueta gold: 19
