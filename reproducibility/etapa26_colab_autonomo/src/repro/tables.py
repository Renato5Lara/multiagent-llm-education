"""Exportacion de tablas y del resumen de reproduccion de cada notebook (CSV y JSON; XLSX si openpyxl esta disponible)."""
import json
import os
import shutil
import pandas as pd


def exportar_tablas(oe, archivos, out_dir):
    """Copia a out_dir/<oe>/ las tablas CSV calculadas por el analisis y las reune en un libro XLSX. Devuelve la lista de rutas."""
    d = os.path.join(out_dir, oe)
    os.makedirs(d, exist_ok=True)
    salida, hojas = [], {}
    for etiqueta, ruta in archivos.items():
        if not os.path.exists(ruta):
            raise FileNotFoundError(f'Tabla esperada no generada: {ruta}')
        dest = os.path.join(d, etiqueta + '.csv')
        shutil.copyfile(ruta, dest)
        salida.append(dest)
        hojas[etiqueta[:31]] = pd.read_csv(dest)
    try:
        with pd.ExcelWriter(os.path.join(d, f'tablas_{oe}.xlsx')) as w:
            for k, v in hojas.items():
                v.to_excel(w, sheet_name=k, index=False)
        salida.append(os.path.join(d, f'tablas_{oe}.xlsx'))
    except ImportError:
        pass
    return salida


def guardar_resumen(oe, out_dir, comparaciones, oficiales, entorno, extra=None):
    """Escribe resumen_<oe>.json y las tablas de comparacion (reproducido frente a local, reproducido frente a la tesis)."""
    d = os.path.join(out_dir, oe)
    os.makedirs(d, exist_ok=True)
    comparaciones.to_csv(os.path.join(d, 'comparacion_reproducido_vs_local.csv'), index=False, encoding='utf-8-sig')
    oficiales.to_csv(os.path.join(d, 'comparacion_reproducido_vs_cifras_de_la_tesis.csv'), index=False, encoding='utf-8-sig')
    res = dict(objetivo=oe, entorno=entorno, comparaciones=comparaciones.to_dict('records'), cifras_oficiales=oficiales.to_dict('records'), extra=extra or {})
    with open(os.path.join(d, f'resumen_{oe}.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=str)
    return res
