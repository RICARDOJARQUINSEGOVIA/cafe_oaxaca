# -*- coding: utf-8 -*-
"""
Índices analíticos Grupo 1 — serie histórica SIAP 2010-2024 (solo SIAP + INPC).
Café, enfoque Oaxaca.

Calcula por año:
  1. Cociente de Localización (LQ): especialización de Oaxaca en café vs. México.
  2. Concentración entre municipios: Gini y HHI (Herfindahl-Hirschman).
  3. Precio real deflactado (pesos 2024) y brecha vs. media nacional.
  4. Siniestralidad y rendimiento.

Fundamento (literatura): Cociente de Localización y HHI/Gini son los índices
estándar en análisis regional agrícola (p. ej. estudios de clústeres cafetaleros).
"""

import glob
import os
import numpy as np
import pandas as pd

UPLOADS = "/mnt/user-data/uploads"
OUT = "/mnt/user-data/outputs"
ENT_OAX = "Oaxaca"


def cargar_todo_siap():
    frames = []
    for r in sorted(glob.glob(os.path.join(UPLOADS, "20[0-9][0-9].csv"))):
        df = pd.read_csv(r, encoding="latin-1", low_memory=False)
        frames.append(df)
    siap = pd.concat(frames, ignore_index=True)
    for c in ["Sembrada", "Cosechada", "Siniestrada", "Volumenproduccion",
              "Rendimiento", "Preciomediorural", "Valorproduccion", "Anio"]:
        siap[c] = pd.to_numeric(siap[c], errors="coerce")
    return siap


def gini(x):
    """Coef. de Gini de una distribución no negativa (0=equidad, 1=concentración)."""
    x = np.sort(np.asarray(x, dtype=float))
    x = x[~np.isnan(x)]
    if len(x) == 0 or x.sum() == 0:
        return np.nan
    n = len(x)
    idx = np.arange(1, n + 1)
    return (2 * np.sum(idx * x) / (n * x.sum())) - (n + 1) / n


def hhi(x):
    """Índice Herfindahl-Hirschman (0-10000) sobre cuotas municipales."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    tot = x.sum()
    if tot == 0:
        return np.nan
    cuotas = x / tot * 100
    return np.sum(cuotas ** 2)


def main():
    siap = cargar_todo_siap()
    inpc = pd.read_csv(os.path.join(OUT, "inpc_anual.csv"))
    inpc_map = dict(zip(inpc["anio"].astype(int), inpc["inpc"]))
    INPC_2024 = inpc_map[2024]

    es_cafe = siap["Nomcultivo"].astype(str).str.contains("caf", case=False, na=False)
    cafe = siap[es_cafe].copy()

    filas = []
    for anio in sorted(siap["Anio"].dropna().unique().astype(int)):
        sy = siap[siap["Anio"] == anio]
        cy = cafe[cafe["Anio"] == anio]
        oax = cy[cy["Nomestado"] == ENT_OAX]

        # --- 1. Cociente de Localización (volumen) ---
        # LQ = (café_Oax / total_Oax) / (café_Nac / total_Nac)
        vol_cafe_oax = oax["Volumenproduccion"].sum()
        vol_total_oax = sy[sy["Nomestado"] == ENT_OAX]["Volumenproduccion"].sum()
        vol_cafe_nac = cy["Volumenproduccion"].sum()
        vol_total_nac = sy["Volumenproduccion"].sum()
        lq = np.nan
        if vol_total_oax and vol_cafe_nac and vol_total_nac:
            lq = (vol_cafe_oax / vol_total_oax) / (vol_cafe_nac / vol_total_nac)

        # --- 2. Concentración entre municipios de Oaxaca ---
        vol_mun = oax.groupby("Idmunicipio")["Volumenproduccion"].sum()
        g = gini(vol_mun.values)
        h = hhi(vol_mun.values)

        # --- 3. Precio real y brecha ---
        vol_o = oax["Volumenproduccion"].sum()
        precio_nom_oax = ((oax["Preciomediorural"] * oax["Volumenproduccion"]).sum()
                          / vol_o) if vol_o else np.nan
        vol_n = cy["Volumenproduccion"].sum()
        precio_nom_nac = ((cy["Preciomediorural"] * cy["Volumenproduccion"]).sum()
                          / vol_n) if vol_n else np.nan
        factor = INPC_2024 / inpc_map.get(anio, np.nan)
        precio_real_oax = precio_nom_oax * factor
        precio_real_nac = precio_nom_nac * factor
        brecha = ((precio_nom_oax - precio_nom_nac) / precio_nom_nac * 100
                  if precio_nom_nac else np.nan)

        # --- 4. Vulnerabilidad y rendimiento ---
        # NOTA: en café (perenne) el SIAP no llena 'Siniestrada'; la vulnerabilidad
        # real se captura por la brecha sembrada-cosechada (superficie no cosechada).
        semb = oax["Sembrada"].sum()
        cos = oax["Cosechada"].sum()
        no_cosechada = semb - cos
        pct_no_cosechada = (no_cosechada / semb * 100) if semb else np.nan
        rend = oax["Rendimiento"].mean()

        filas.append({
            "Anio": anio,
            "Municipios_cafe_Oax": oax["Idmunicipio"].nunique(),
            "LQ_especializacion": round(lq, 3) if pd.notna(lq) else np.nan,
            "Gini_concentracion": round(g, 3) if pd.notna(g) else np.nan,
            "HHI_concentracion": round(h, 1) if pd.notna(h) else np.nan,
            "Precio_nominal_Oax": round(precio_nom_oax, 0) if pd.notna(precio_nom_oax) else np.nan,
            "Precio_real2024_Oax": round(precio_real_oax, 0) if pd.notna(precio_real_oax) else np.nan,
            "Precio_real2024_Nac": round(precio_real_nac, 0) if pd.notna(precio_real_nac) else np.nan,
            "Brecha_precio_pct": round(brecha, 1) if pd.notna(brecha) else np.nan,
            "Sup_no_cosechada_ha": round(no_cosechada, 0),
            "Pct_no_cosechada_Oax": round(pct_no_cosechada, 2) if pd.notna(pct_no_cosechada) else np.nan,
            "Rendimiento_Oax": round(rend, 3) if pd.notna(rend) else np.nan,
            "Volumen_Oax_ton": round(vol_o, 1),
        })

    res = pd.DataFrame(filas).sort_values("Anio")
    res.to_csv(os.path.join(OUT, "indices_grupo1_serie.csv"),
               index=False, encoding="utf-8-sig")
    return res


if __name__ == "__main__":
    res = main()
    pd.set_option("display.width", 200, "display.max_columns", 20)
    print(res.to_string(index=False))
    res.to_pickle("/home/claude/_indices.pkl")
