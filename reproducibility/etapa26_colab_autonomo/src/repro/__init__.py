"""Biblioteca de reproduccion de los resultados OE1-OE5 (solo analisis; no repite las campanas)."""
__version__ = "1.0.0"
from .data_loading import fetch_packages, fetch_package, load_manifest, verify_sums_file, DataIntegrityError  # noqa: F401
from .runner import sh  # noqa: F401
from . import validation, official, figures, tables  # noqa: F401
