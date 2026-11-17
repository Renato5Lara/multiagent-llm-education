# Etiquetas y rama de esta etapa

| Referencia | Estado | Qué usar |
|---|---|---|
| `repro-etapa26-v2` | **VIGENTE** | Es la que cargan los seis notebooks. Código y notebooks inmutables. |
| `repro-etapa26-v1` | **DESCARTADA — no usar** | Sus notebooks clonaban el repositorio completo (unos 9 000 archivos) y fallaban en Windows por la longitud de ruta. No contiene ningún dato distinto: los datos son los mismos (commit `3c8953a`). Se conserva sin modificar porque las etiquetas publicadas no se reescriben. |
| `repro/etapa26-colab-autonomo` (rama) | Cabeza de trabajo | Puede ir por delante de la etiqueta v2 (documentación posterior). Para reproducir, use la etiqueta, no la rama. |
| `repro/etapa23-oe1-oe5-colab-limpia` (rama) y `etapa23_oe1_oe5/notebooks/` | **SUPERADO** | Notebooks anteriores que piden subir los ZIP a mano. Se conservan como antecedente; para reproducir sin subir archivos use los de `etapa26_colab_autonomo/notebooks/`. |

Los datos de todas las referencias son los 12 paquetes del commit `3c8953a58909c48929093ef1524eb7d0ad317378`.
