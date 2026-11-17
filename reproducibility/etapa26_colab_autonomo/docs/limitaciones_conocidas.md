# Limitaciones conocidas de los datos y de la verificación

## Cobertura del monitor en OE2-A (interferencia)

Recuentos reproducidos desde los datos publicados (`oe2a_colab_paquete`; criterio de `analisis_oe2a.py`: interferencia **fuerte** = algún proceso ajeno por encima del 25 % de un núcleo en algún segundo del ciclo):

| Grupo | Ciclos | Qué se puede afirmar |
|---|---|---|
| Interferencia fuerte observada | **2 770** | Coinciden con al menos un segundo de interferencia fuerte registrado |
| Sin interferencia fuerte observada, con cobertura del monitor | 1 928 | El monitor los cubre y no muestra interferencia fuerte (sí hay procesos ajenos por encima del 10 % en todos ellos) |
| Sin interferencia fuerte registrada, **sin cobertura del monitor** | 302 | No tienen ningún segundo de monitor (el monitor tiene 460 muestras para unos 491 s: 31 segundos sin muestra). **No se puede afirmar que estuvieran libres de interferencia** |

Los 2 230 ciclos del análisis de sensibilidad («sin los ciclos con interferencia fuerte», T_conv 63,92 ms) son 1 928 + 302. **No debe describirse a esos 2 230 como ciclos que «corrieron en reposo»**: las compuertas de reposo fallaron al inicio y al cierre y, en los 1 928 con monitor, siempre hubo procesos ajenos por encima del 10 %. La cifra de 2 770 no cambia. Detalle por ciclo reproducible con `scripts_auditoria/resolver_oe2a.py` (carpeta de auditoría, no incluida aquí).

## Resto de limitaciones

Las campañas OE1, OE2-A, OE2-B, OE3 y OE4 no son controladas: hay interferencia ambiental registrada (OE1, OE2-B y OE4, en el 100 % de las corridas). RNF03 no se cumple (F1_adapt 0,8044 < 0,85). La campaña OE2A-02 no se ejecutó. Ver `reproduction_guide.md` §3 y §7.

## Verificación

La validación de los notebooks se hizo en local (descargando de GitHub), no en Google Colab. La reproducibilidad en Colab real **no está verificada** hasta que se ejecuten allí.
