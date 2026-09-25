"""Deduplica por ENLACE DURO los archivos idénticos (mismo sha256) entre versiones de la biblioteca y con `_tts_cache/`.
No borra contenido: cada archivo sigue existiendo en su ruta con los mismos bytes (se verifica el hash ANTES y DESPUÉS).

    python -m adaptation_swarm.tools.dedupe_library            # SIMULACIÓN (por defecto): solo informa el ahorro
    python -m adaptation_swarm.tools.dedupe_library --apply    # aplica los enlaces duros (requiere aprobación del propietario)
"""

import argparse
import hashlib
import os
from collections import defaultdict
from pathlib import Path

from adaptation_swarm.config import SETTINGS


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plan(root: Path) -> dict:
    files = [p for p in root.rglob("*") if p.is_file() and p.name != "manifest.json" and not p.name.startswith(".")]
    groups: dict[str, list[Path]] = defaultdict(list)
    seen_inodes: set[tuple[int, int]] = set()
    inode_of_group: dict[str, int] = {}
    to_link: list[tuple[Path, Path]] = []
    saved = 0
    for p in sorted(files):
        st = p.stat()
        h = _sha(p)
        if h not in inode_of_group:
            inode_of_group[h] = st.st_ino
            groups[h].append(p)
            seen_inodes.add((st.st_dev, st.st_ino))
        elif st.st_ino != inode_of_group[h]:
            to_link.append((groups[h][0], p))
            if (st.st_dev, st.st_ino) not in seen_inodes:
                seen_inodes.add((st.st_dev, st.st_ino))
                saved += st.st_size
    return {"files": len(files), "unique_contents": len(groups), "links_to_create": to_link, "bytes_saved": saved}


def apply(links: list[tuple[Path, Path]]) -> int:
    n = 0
    for keep, dup in links:
        h_before = _sha(dup)
        tmp = dup.with_name(dup.name + ".dedupe-tmp")
        os.link(keep, tmp)
        if _sha(tmp) != h_before:                  # imposible si el plan es correcto; aborta sin tocar el original
            tmp.unlink()
            raise RuntimeError(f"hash distinto al enlazar {dup}")
        os.replace(tmp, dup)
        n += 1
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    r = plan(SETTINGS.library_root)
    print(f"archivos {r['files']} · contenidos únicos {r['unique_contents']} · enlaces a crear {len(r['links_to_create'])} · "
          f"ahorro {r['bytes_saved'] / 1e6:.0f} MB")
    if a.apply:
        print(f"{apply(r['links_to_create'])} enlaces aplicados")
    else:
        print("SIMULACIÓN: no se modificó nada (usar --apply con aprobación)")
