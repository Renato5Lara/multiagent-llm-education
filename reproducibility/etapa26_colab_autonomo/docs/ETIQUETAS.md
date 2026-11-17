# Etiquetas y rama de esta etapa

| Referencia | Estado | Qué usar |
|---|---|---|
| `repro-etapa26-v3` | **VIGENTE** | Es la que cargan los seis notebooks. Sus datos de OE2-B tienen una segunda anonimización (rutas locales del campo `error` de cinco intentos). |
| `repro-etapa26-v2` | **HISTÓRICA — no es la fuente activa** | Notebooks idénticos salvo la etiqueta que cargan y los dos paquetes de OE2-B (versión sin la segunda anonimización). Se conserva sin modificar; ningún notebook de la v3 la usa. |
| `repro-etapa26-v1` | **DESCARTADA — no usar** | Sus notebooks clonaban el repositorio completo (unos 9 000 archivos) y fallaban en Windows por la longitud de ruta. |
| `repro/etapa26-colab-autonomo` (rama) | Cabeza de trabajo | Puede ir por delante de la etiqueta vigente (documentación posterior). Para reproducir, use la etiqueta, no la rama. |
| `repro/etapa23-oe1-oe5-colab-limpia` (rama) y `etapa23_oe1_oe5/notebooks/` | **SUPERADO** | Notebooks anteriores que piden subir los ZIP a mano. Se conservan como antecedente. |

## Datos

Diez paquetes: commit `3c8953a58909c48929093ef1524eb7d0ad317378`. Dos paquetes de OE2-B (v3): commit `5622bf50d7a757446fd76c19fe78938831a4c7fa`, carpeta `paquetes_v3/`. El manifiesto (`manifests/data_manifest.json`) fija la URL, el tamaño y el SHA-256 de cada uno, y conserva en `sustituye_a` los de las versiones anteriores.

## Historial

Las versiones anteriores de los dos paquetes de OE2-B (con las rutas locales en el campo `error`) siguen en el historial público del repositorio y en `etapa23_oe1_oe5/paquetes/`; esta versión no las elimina porque no se reescribe la historia.
