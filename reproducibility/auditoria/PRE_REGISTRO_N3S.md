# Pre-registro de N3-S (escrito ANTES de ejecutar; 2026-10-19)

**Pregunta.** ¿Por qué el T_conv absoluto de N3-R (2026-10-19) es ≈ 16,5 % menor que el de N3 (2026-10-06) si el código, el hardware, numpy, Python, la biblioteca, el dataset y Redis son los mismos?

**Hechos ya comprobados con los registros (no hipótesis).** Los fingerprints de módulos del arnés coinciden en todos los archivos; el único cambio de código entre `cec0e06` y `265a4f4` en `adaptation_swarm` no toca la ruta en proceso (`factorial_anova` omite factores de un nivel; el resto es `http_campaign.py`). El cociente N3-R/N3 por condición es casi constante (mediana 0,84; rango 0,79–0,89; 48 condiciones), con la excepción de que el despacho secuencial se acelera más (0,81) que el de lotes (0,875).

**Diseño.** N3-S repite N3 con **las mismas semillas** (`batch_seed` 26093001, mismo diseño: 48 condiciones × 5 lotes × 100 perfiles, bloques aleatorizados, `--seed-per-batch`, N = 20, 1 usuario, calentamiento 10) en la sesión actual, con el código actual, y registra la carga del sistema cada 5 s (CPU, memoria, frecuencia) en un archivo aparte.

**Hipótesis y predicciones, fijadas antes de ver N3-S.**
- **H_sesión:** la velocidad depende de la sesión/momento (estado del equipo), no de las semillas. Predicción: el T_conv medio de N3-S ≈ el de N3-R (cociente N3-S/N3 en [0,79; 0,89]) y los indicadores de calidad (brecha, `k_stop`, mensajes) idénticos a N3.
- **H_semilla:** la velocidad depende de las semillas/perfiles de cada lote. Predicción: el T_conv medio de N3-S ≈ el de N3 (cociente en [0,95; 1,05]).
- **H_código:** el código actual es más rápido que `cec0e06`. Predicción: igual que H_sesión; **no se puede separar de ella con N3-S** (se declara). Se acota con los fingerprints (sin diferencias) y con que la ruta en proceso no cambió.
- **Calidad (brecha, `k_stop`, `n_messages`, `F`):** al fijar las semillas deben reproducirse **exactamente** (determinismo). Si no coinciden, el arnés no es determinista y eso se reporta.
- Un cociente entre 0,89 y 0,95, o fuera de [0,79; 1,05], se informa como **no concluyente**.

**Criterio de decisión.** Cociente de medias geométricas de T_conv N3-S/N3 con IC95 entre lotes (t, 4 gl). No se combinan campañas; N3, N3-R y N3-S se informan por separado. Cada lote es un bloque (no cinco observaciones independientes del mismo fenómeno).
**Limitación.** Un solo equipo; la carga previa de N3 (6 oct) no se registró, así que su causa no puede recuperarse a posteriori; N3-S solo puede discriminar semilla frente a sesión.

---
# Resultado (añadido DESPUÉS de ejecutar; el texto anterior no se modificó)
N3-S: 240 corridas, 24 000 observaciones, 0 fallos; la cadena observaciones→corridas coincide (dif. máx. 7,1·10⁻¹⁵). Se ejecutó el 2026-10-19 con el código `265a4f4` y el muestreo de carga del sistema (`carga_sistema.csv`: CPU total media 16,6 %, máx. 23 %; memoria libre mínima 8,1 GB).
- **T_conv (media geométrica):** N3 71,72 ms; N3-R 60,37 ms; **N3-S 60,29 ms**.
- **Cociente N3-S/N3 = 0,841 (IC95 entre lotes 0,820–0,862; por lote 0,87, 0,85, 0,83, 0,83, 0,83)** ⇒ dentro de [0,79; 0,89] ⇒ **H_sesión**. **N3-S/N3-R = 0,999 (IC95 0,976–1,022).**
- **Calidad (brecha, `k_stop`, mensajes, F): idéntica a N3 en las 240 corridas (diferencia máxima 0)** ⇒ el arnés es determinista con las mismas semillas.
- **Veredicto preregistrado: H_sesión.** Con las mismas semillas, la velocidad de hoy es la de N3-R, no la de N3. H_semilla queda rechazada.
- **Lo que sigue sin saberse:** si la diferencia se debe al estado del equipo el 6 de octubre (carga, temperatura, procesos en segundo plano; no se registró) o a la versión del código. Los fingerprints de módulos son idénticos y la ruta en proceso no cambió entre `cec0e06` y `265a4f4`, lo que hace poco probable la segunda, pero no la excluye formalmente. Esa causa no es recuperable con los datos de N3.
- **Consecuencia para la tesis:** los valores absolutos de T_conv de N3 (Tablas 13, 14 y 40) son válidos como mediciones de aquella sesión, pero **no son una constante del arnés**: dependen de la sesión. Los efectos **relativos** y la calidad sí replican. No se modifica la tesis.
