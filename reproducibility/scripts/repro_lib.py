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
    dec = len(s.split(",")[1]) if "," in s else 0
    return float(s.replace(",", ".")), dec


def compare(pub_str: str, recomputed: float):
    """Compara un valor publicado con el recalculado. Tolerancia = media unidad del último decimal publicado (redondeo).
    COINCIDE ≤ 0,5 u; DIFERENCIA_EXPLICABLE ≤ 1 u (redondeos encadenados); DISCREPANCIA > 1 u. Para `a × 10ⁿ` la unidad se aplica a la mantisa."""
    pub, dec, exp = parse_num(pub_str)
    unit = 10.0 ** (-dec) * (10.0 ** exp if exp is not None else 1.0)
    diff = recomputed - pub
    ratio = abs(diff) / unit
    estado = "COINCIDE" if ratio <= 0.5 + 1e-9 else "DIFERENCIA_EXPLICABLE" if ratio <= 1.0 + 1e-9 else "DISCREPANCIA"
    return dict(publicado=pub_str, publicado_num=pub, recalculado=recomputed, dif_abs=diff, dif_rel=(diff / pub if pub else None),
                tolerancia=0.5 * unit, estado=estado, precision_publicada=f"{dec} decimales" + (f", ×10^{exp}" if exp is not None else ""))


def report_tables():
    d = json.loads((META / "informe_D2.9.7_tablas.json").read_text(encoding="utf-8"))
    out = {}
    for t in d["tables"]:
        m = re.match(r"Tabla (\d+)\.", t["caption_prev"])
        if m:
            out[int(m.group(1))] = t["rows"]
    return d["source_sha256"], out
