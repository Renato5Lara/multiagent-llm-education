"""Utilidades comunes. Sin rutas absolutas: todo es relativo a la raíz de `reproducibility/`."""
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data" / "experiments"
META = ROOT / "data" / "metadata"
OUT = ROOT / "outputs"
MANIFEST = ROOT / "EVIDENCE_MANIFEST.csv"
# códigos de salida distintos para cada clase de error
EXIT_OK, EXIT_INTEGRIDAD, EXIT_ESQUEMA, EXIT_DATOS, EXIT_DIFERENCIA = 0, 2, 3, 4, 5


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


_SUP = str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789")


def parse_num(s: str):
    """Cifra del informe → (valor, decimales_publicados). Admite coma decimal, espacios de millares, signo − y notación `a × 10ⁿ`."""
    s = s.replace("\u2212", "-").replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ").strip()
    m = re.fullmatch(r"(-?[\d ]+(?:,\d+)?)\s*×\s*10([⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+)", s)
    if m:
        mant, dec = _plain(m.group(1))
        return mant * 10 ** int(m.group(2).translate(_SUP)), dec, int(m.group(2).translate(_SUP))
    v, dec = _plain(s)
    return v, dec, None


def _plain(s: str):
    s = s.replace(" ", "")
    if "," in s:
        dec = len(s.split(",")[1])
    elif "." in s:                      # algunas tablas del anexo usan punto decimal
        dec = len(s.split(".")[1])
    else:
        dec = 0
    return float(s.replace(",", ".")), dec


def doble_redondeo(pub_str, recomputed, dec, exp):
    """¿Se obtiene el valor publicado redondeando primero a más decimales (p. ej. el de un archivo de resultados) y luego a su precisión (mitad hacia arriba)?
    Devuelve (valor_intermedio, decimales_intermedios) o None. No aplica a la notación `a x 10^n`."""
    from decimal import ROUND_HALF_UP, Decimal
    if exp is not None:
        return None
    pub = Decimal(pub_str.replace("\u2212", "-").replace(" ", "").replace("\u00a0", "").replace(",", "."))
    for extra in (1, 2, 3):
        inter = Decimal(repr(recomputed)).quantize(Decimal(1).scaleb(-(dec + extra)), rounding=ROUND_HALF_UP)
        if inter.quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP) == pub:
            return str(inter), dec + extra
    return None


def compare(pub_str: str, recomputed: float):
    """Compara un valor publicado con el recalculado. Tolerancia = media unidad del último decimal publicado (redondeo).
    COINCIDE ≤ 0,5 u; DIFERENCIA_EXPLICABLE ≤ 1 u (redondeos encadenados); DISCREPANCIA > 1 u. Para `a × 10ⁿ` la unidad se aplica a la mantisa."""
    pub, dec, exp = parse_num(pub_str)
    unit = 10.0 ** (-dec) * (10.0 ** exp if exp is not None else 1.0)
    diff = recomputed - pub
    ratio = abs(diff) / unit
    estado = "COINCIDE" if ratio <= 0.5 + 1e-9 else "DIFERENCIA_EXPLICABLE" if ratio <= 1.0 + 1e-9 else "DISCREPANCIA"
    extra = {}
    if estado == "DIFERENCIA_EXPLICABLE":
        dr = doble_redondeo(pub_str, recomputed, dec, exp)
        if dr:
            extra = {"explicacion": "DOBLE_REDONDEO_CONFIRMADO", "valor_sin_redondear": recomputed, "valor_intermedio": dr[0],
                     "detalle": f"{recomputed!r} -> {dr[1]} decimales: {dr[0]} -> {dec} decimales (mitad hacia arriba): {pub_str.strip()}"}
        else:
            estado = "DIFERENCIA_SIN_EXPLICAR"      # una unidad de diferencia que el doble redondeo NO explica: no se da por buena
    return dict(**extra, publicado=pub_str, publicado_num=pub, recalculado=recomputed, dif_abs=diff, dif_rel=(diff / pub if pub else None),
                tolerancia=0.5 * unit, estado=estado, precision_publicada=f"{dec} decimales" + (f", ×10^{exp}" if exp is not None else ""))


class Pub(str):
    """Cifra tal como aparece en el informe, con su ubicación exacta (tabla, fila, columna, encabezado). Las operaciones de texto habituales conservan la ubicación."""

    def __new__(cls, s, **meta):
        o = str.__new__(cls, s)
        o.meta = meta
        return o

    def _w(self, s):
        return Pub(s, **self.meta)

    def strip(self, *a):
        return self._w(str.strip(self, *a))

    def replace(self, *a):
        return self._w(str.replace(self, *a))

    def split(self, *a, **k):
        return [self._w(x) for x in str.split(self, *a, **k)]


class Row(list):
    """Fila de una tabla del informe; indexar devuelve `Pub` con la ubicación."""

    def __init__(self, cells, tabla, fila, header):
        super().__init__(cells)
        self.tabla, self.fila, self.header = tabla, fila, header

    def __getitem__(self, i):
        v = super().__getitem__(i)
        if isinstance(i, int):
            return Pub(v, tabla=self.tabla, fila=self.fila, col=i % len(self), encabezado=(self.header[i % len(self)] if self.header and len(self.header) == len(self) else ""),
                       etiqueta_fila=str.strip(super().__getitem__(0)) if len(self) else "")
        return v


def like(orig, s):
    """Devuelve `s` con la ubicación de `orig` (para cadenas derivadas por expresiones regulares)."""
    return Pub(s, **orig.meta) if hasattr(orig, "meta") else s


def report_tables():
    import os
    alt = os.environ.get("REPRO_INFORME_JSON")      # p. ej. las tablas de una versión corregida del informe
    d = json.loads((Path(alt) if alt else META / "informe_D2.9.7_tablas.json").read_text(encoding="utf-8"))
    out = {}
    for t in d["tables"]:
        m = re.match(r"Tabla (\d+)\.", t["caption_prev"])
        if m:
            n = int(m.group(1))
            hdr = t["rows"][0]
            out[n] = [Row(r, n, k, hdr) for k, r in enumerate(t["rows"])]
    return d["source_sha256"], out


def es_probabilidad(nombre) -> bool:
    """Columnas o claves que contienen valores p (se comparan solo en relativo; el ruido absoluto cercano a cero no aplica a probabilidades)."""
    s = str(nombre).lower()
    return s.startswith("p") and (len(s) <= 2 or s[1] in "_(-") or "p_" in s or "pr(" in s or s.endswith("_p") or s == "p"


def comparar_archivos(regenerado: Path, publicado: Path) -> str:
    """Nivel de igualdad entre un archivo regenerado y el publicado:
    COINCIDE_BYTE_A_BYTE · COINCIDE_SALVO_FINALES_DE_LINEA (los publicados se generaron en Windows con CRLF; en Linux/Colab salen con LF) ·
    COINCIDE_NUMERICO (mismo contenido; números iguales con tolerancia relativa 1e-6 y absoluta 1e-12, es decir, ruido de punto flotante entre plataformas;
    en JSON, además, las barras `\\` y `/` de las rutas se consideran iguales porque los publicados se generaron en Windows) · DIFIERE · NO_GENERADO."""
    if not regenerado.exists():
        return "NO_GENERADO"
    a, b = regenerado.read_bytes(), publicado.read_bytes()
    if a == b:
        return "COINCIDE_BYTE_A_BYTE"
    na, nb = a.replace(b"\r\n", b"\n"), b.replace(b"\r\n", b"\n")
    if na == nb:
        return "COINCIDE_SALVO_FINALES_DE_LINEA"
    try:
        if publicado.suffix == ".csv":
            import pandas as pd
            x, y = pd.read_csv(regenerado, low_memory=False), pd.read_csv(publicado, low_memory=False)
            if x.shape == y.shape and list(x.columns) == list(y.columns):
                import numpy as np
                ok = True
                for c in x.columns:
                    if pd.api.types.is_numeric_dtype(x[c]) and pd.api.types.is_numeric_dtype(y[c]):
                        atol = 0.0 if es_probabilidad(c) else 1e-12      # una probabilidad se compara siempre en relativo: 1e-184 y 3e-184 NO son iguales
                        ok &= bool(np.allclose(x[c].to_numpy(float), y[c].to_numpy(float), rtol=1e-6, atol=atol, equal_nan=True))
                    else:
                        ok &= bool((x[c].fillna("") == y[c].fillna("")).all())
                return "COINCIDE_NUMERICO" if ok else "DIFIERE"
        elif publicado.suffix == ".json":
            import json
            import math

            def eq(p, q, key=""):
                if isinstance(p, dict) and isinstance(q, dict):
                    return p.keys() == q.keys() and all(eq(p[k], q[k], k) for k in p)
                if isinstance(p, list) and isinstance(q, list):
                    return len(p) == len(q) and all(eq(i, j, key) for i, j in zip(p, q))
                if isinstance(p, float) or isinstance(q, float):
                    return isinstance(p, (int, float)) and isinstance(q, (int, float)) and (math.isclose(p, q, rel_tol=1e-6, abs_tol=0.0 if es_probabilidad(key) else 1e-12) or (math.isnan(p) and math.isnan(q)))
                if isinstance(p, str) and isinstance(q, str):
                    return p.replace("\\", "/") == q.replace("\\", "/")
                return p == q
            return "COINCIDE_NUMERICO" if eq(json.loads(regenerado.read_text(encoding="utf-8")), json.loads(publicado.read_text(encoding="utf-8"))) else "DIFIERE"
    except Exception:  # noqa: BLE001
        pass
    return "DIFIERE"
