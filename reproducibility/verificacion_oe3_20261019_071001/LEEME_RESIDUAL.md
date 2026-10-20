# Archivos residuales: no son evidencia vigente

Esta carpeta y su `.zip` (`verificacion_oe3_20261019_071001.zip`) son la exportación de la celda final del notebook del OE3 de **una ejecución local** (nbclient) del 2026-10-19 hacia las 07:10, antes de añadir N3-S, la eficiencia y los estados recalculados de la Tabla 37. Se subieron por error al repositorio en el commit `36a3380`.

- **Ningún notebook ni script los lee.** No figuran en `EVIDENCE_MANIFEST.csv`.
- **Están desactualizados:** sus cifras corresponden al código de aquel momento; la verificación vigente se regenera en `outputs/` (`verification_report_oe3.json`) y se resume en `auditoria/`.
- **No se han borrado** para no eliminar evidencia sin decisión del autor; el historial de Git no se ha modificado. Si se decide retirarlos, basta un commit normal.
- Referencia: `auditoria/AUDITORIA_TRAZABILIDAD_COLAB.md`.
