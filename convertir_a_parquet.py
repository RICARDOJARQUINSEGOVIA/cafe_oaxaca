# -*- coding: utf-8 -*-
"""
convertir_a_parquet.py
Convierte los 15 CSV del SIAP (2010-2024) a dos archivos Parquet livianos:
  · siap_cafe.parquet     — solo registros de café (todo el país)
  · siap_totales.parquet  — volumen agrícola total por estado-año (para el LQ)

Reduce ~86 MB de CSV a ~0.25 MB, apto para subir a GitHub / Streamlit Cloud.

Uso (con los CSV en la carpeta data/):
    python convertir_a_parquet.py

Requiere: pandas, pyarrow  (pip install pandas pyarrow)
"""

import glob
import os

import pandas as pd

DATA = os.path.join(os.path.dirname(__file__), "data")

NUM_COLS = ["Sembrada", "Cosechada", "Siniestrada", "Volumenproduccion",
            "Rendimiento", "Preciomediorural", "Valorproduccion",
            "Anio", "Idestado", "Idmunicipio"]


def main():
    rutas = sorted(glob.glob(os.path.join(DATA, "20[0-9][0-9].csv")))
    if not rutas:
        print("No se encontraron CSV del SIAP (20XX.csv) en data/.")
        return

    print(f"Leyendo {len(rutas)} archivos CSV…")
    frames = [pd.read_csv(r, encoding="latin-1", low_memory=False) for r in rutas]
    full = pd.concat(frames, ignore_index=True)

    for c in NUM_COLS:
        if c in full.columns:
            full[c] = pd.to_numeric(full[c], errors="coerce")
    for c in full.columns:
        if full[c].dtype == "object":
            full[c] = full[c].astype(str)

    # 1) Café nacional
    cafe = full[full["Nomcultivo"].str.contains("caf", case=False, na=False)].copy()
    cafe.to_parquet(os.path.join(DATA, "siap_cafe.parquet"),
                    compression="snappy", index=False)

    # 2) Totales de volumen agrícola por estado-año (denominador del LQ)
    tot = full.groupby(["Anio", "Nomestado"], as_index=False)["Volumenproduccion"].sum()
    tot.columns = ["Anio", "Nomestado", "Vol_total_agricola"]
    tot.to_parquet(os.path.join(DATA, "siap_totales.parquet"),
                   compression="snappy", index=False)

    mb = (os.path.getsize(os.path.join(DATA, "siap_cafe.parquet"))
          + os.path.getsize(os.path.join(DATA, "siap_totales.parquet"))) / 1e6
    print(f"Listo. siap_cafe.parquet ({len(cafe)} filas) y siap_totales.parquet "
          f"({len(tot)} filas). Total: {mb:.2f} MB.")
    print("Ya puedes subir la carpeta data/ a GitHub (los CSV grandes ya no son necesarios).")


if __name__ == "__main__":
    main()
