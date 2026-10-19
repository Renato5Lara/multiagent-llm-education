# N9 (`oe_n9_2026-10-13`): campaña ABORTADA y DESCARTADA

- Plan: 160 ejecuciones (`[k/160]` en `campaign.log`). Iniciadas: **38** (la última línea de progreso es `[38/160] n9-oe2-aux-decision_table|u5|N20-r02`; hay 38 pares de CSV crudos). La 38.ª es la que falló, por lo que como máximo 37 terminaron; no hay `runs.csv` que lo confirme.
- Motivo del corte: `subprocess.CalledProcessError` al lanzar Locust (traza al final de `campaign.log`, justo después de la línea 38/160).
- No se escribieron `runs.csv`, `manifest.json` ni `SHA256SUMS`: la campaña nunca se cerró. Los resúmenes por corrida **no existen**; solo hay 38 pares de CSV por petición en `campaign.tmp-raw/`.
- Publicado aquí: únicamente `campaign.sanitizado.log`, copia del registro de la interrupción con las rutas locales sustituidas (`data/metadata/SANITIZACION.csv` da el hash del original y el de la copia; **no son idénticos**). El original sigue fuera del paquete. Los 76 CSV por petición no se publican; sus tamaños y SHA-256 están en `N9_tmp_raw_hashes.csv`.
- **N9 no se combina con N9b** ni respalda ninguna cifra del informe. La réplica integrada es **N9b** (`oe_n9b_2026-10-14/campaign_final`, 160/160 corridas con `status = ok`), que se reanudó con `--resume` a partir del diario `campaign_final.journal/`.
- Verificación de los 38/160: recuento de pares de archivos `.csv` + `.cpu.csv` en `campaign.tmp-raw` (38) y de líneas `[k/160]` en `campaign.log` (38).
