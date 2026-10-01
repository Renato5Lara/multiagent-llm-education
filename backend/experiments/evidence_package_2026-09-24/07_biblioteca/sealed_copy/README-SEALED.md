# Copia sellada del audio de la biblioteca M1 (local)

**COPIA SELLADA LOCAL: NO constituye todavía almacenamiento externo de preservación institucional.**
Es una copia adicional (no un movimiento) de los mp3 de la biblioteca `datasets/adaptation_library/` y de los manifiestos de cada versión, creada por
`python -m adaptation_swarm.tools.seal_audio`. Los originales no se modificaron. Los mp3 están **fuera de Git** por la Decisión C (DECISION-CLOSURE §14);
el mecanismo definitivo de almacenamiento externo está PENDIENTE.

- Versiones incluidas: lib-v1-3f931e10, lib-v2-767b4a53, lib-v3-5fa0acdd, lib-v4-039dcf58, lib-v5-9ae9ffdd, lib-v6-86516a15, lib-v7-7c046f32, lib-v8-079928dc, lib-v9-a0231e9b, lib-v10-5dd83cd4
- Archivos: 2164 (mp3: 2151, manifiestos: 10)
- Verificación: `cd` a este directorio y ejecutar `LC_ALL=C sha256sum -c SHA256SUMS` (todo debe decir OK), o
  `python -m adaptation_swarm.tools.seal_audio --verify .` (además compara cada mp3 con el sha256 de su manifiesto).
- `library_inventory.json/.md`: inventario de la biblioteca de origen en el momento del sellado.
- Los archivos se marcaron de solo lectura (`chmod a-w`).
