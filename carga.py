# -*- coding: utf-8 -*-
"""
carga.py — Capa de datos del dashboard de café (Oaxaca).
Reúne y cachea: SIAP (serie), Censo 2022, INPC, índices Grupo 1 y cruce Grupo 3.
Toda la lógica ya fue validada en la fase de análisis.
"""

import glob
import os
import re
import unicodedata

import numpy as np
import pandas as pd

DATA = os.path.join(os.path.dirname(__file__), "data")
ENT_NOMBRE = "Oaxaca"
ENT_CVE = 20


# --------------------------------------------------------------------------- #
def norm(s):
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def _es_cafe(serie):
    return serie.astype(str).str.contains("caf", case=False, na=False)


def _cafe_exacto(serie):
    return serie.astype(str).apply(lambda x: norm(x) == "cafe")


# --------------------------------------------------------------------------- #
# SIAP — serie completa
# --------------------------------------------------------------------------- #
def cargar_siap_serie():
    # Preferir parquet (café ya filtrado, mucho más liviano); si no, leer los CSV.
    pq_cafe = os.path.join(DATA, "siap_cafe.parquet")
    pq_tot = os.path.join(DATA, "siap_totales.parquet")
    if os.path.exists(pq_cafe) and os.path.exists(pq_tot):
        cafe = pd.read_parquet(pq_cafe)
        tot = pd.read_parquet(pq_tot)
        # Reconstruir estructura mínima: el resto del código espera un df con café
        # y necesita los totales de volumen por estado-año para el LQ.
        # Guardamos los totales como atributo accesible.
        cafe.attrs["totales_estado"] = tot
        return cafe
    # Fallback: CSV originales
    frames = []
    for r in sorted(glob.glob(os.path.join(DATA, "20[0-9][0-9].csv"))):
        frames.append(pd.read_csv(r, encoding="latin-1", low_memory=False))
    if not frames:
        return pd.DataFrame()
    siap = pd.concat(frames, ignore_index=True)
    for c in ["Sembrada", "Cosechada", "Siniestrada", "Volumenproduccion",
              "Rendimiento", "Preciomediorural", "Valorproduccion", "Anio"]:
        siap[c] = pd.to_numeric(siap[c], errors="coerce")
    return siap


def cargar_inpc():
    df = pd.read_csv(os.path.join(DATA, "inpc_anual.csv"))
    return dict(zip(df["anio"].astype(int), df["inpc"]))


# --------------------------------------------------------------------------- #
# Índices Grupo 1 (serie histórica)
# --------------------------------------------------------------------------- #
def gini(x):
    x = np.sort(np.asarray(x, dtype=float))
    x = x[~np.isnan(x)]
    if len(x) == 0 or x.sum() == 0:
        return np.nan
    n = len(x)
    idx = np.arange(1, n + 1)
    return (2 * np.sum(idx * x) / (n * x.sum())) - (n + 1) / n


def hhi(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    tot = x.sum()
    if tot == 0:
        return np.nan
    return np.sum((x / tot * 100) ** 2)


def indices_grupo1(siap, inpc, anio_base=2024):
    es_cafe = _es_cafe(siap["Nomcultivo"])
    cafe = siap[es_cafe]
    I_base = inpc.get(anio_base, np.nan)
    # Totales de volumen agrícola por estado-año (para el denominador del LQ).
    # Con parquet vienen en attrs; con CSV se calculan del propio siap.
    totales = siap.attrs.get("totales_estado")

    def vol_total(anio, estado=None):
        if totales is not None:
            t = totales[totales["Anio"] == anio]
            if estado:
                t = t[t["Nomestado"] == estado]
            return t["Vol_total_agricola"].sum()
        s = siap[siap["Anio"] == anio]
        if estado:
            s = s[s["Nomestado"] == estado]
        return s["Volumenproduccion"].sum()

    filas = []
    for anio in sorted(cafe["Anio"].dropna().unique().astype(int)):
        cy = cafe[cafe["Anio"] == anio]
        oax = cy[cy["Nomestado"] == ENT_NOMBRE]

        vol_cafe_oax = oax["Volumenproduccion"].sum()
        vol_total_oax = vol_total(anio, ENT_NOMBRE)
        vol_cafe_nac = cy["Volumenproduccion"].sum()
        vol_total_nac = vol_total(anio)
        lq = np.nan
        if vol_total_oax and vol_cafe_nac and vol_total_nac:
            lq = (vol_cafe_oax / vol_total_oax) / (vol_cafe_nac / vol_total_nac)

        vol_mun = oax.groupby("Idmunicipio")["Volumenproduccion"].sum()
        g, h = gini(vol_mun.values), hhi(vol_mun.values)

        vol_o = oax["Volumenproduccion"].sum()
        p_nom_o = ((oax["Preciomediorural"] * oax["Volumenproduccion"]).sum() / vol_o
                   if vol_o else np.nan)
        vol_n = cy["Volumenproduccion"].sum()
        p_nom_n = ((cy["Preciomediorural"] * cy["Volumenproduccion"]).sum() / vol_n
                   if vol_n else np.nan)
        factor = I_base / inpc.get(anio, np.nan)
        brecha = ((p_nom_o - p_nom_n) / p_nom_n * 100) if p_nom_n else np.nan

        semb, cos = oax["Sembrada"].sum(), oax["Cosechada"].sum()
        pct_nc = ((semb - cos) / semb * 100) if semb else np.nan

        filas.append({
            "Anio": anio,
            "Municipios": oax["Idmunicipio"].nunique(),
            "LQ": lq, "Gini": g, "HHI": h,
            "Precio_nominal": p_nom_o,
            "Precio_real": p_nom_o * factor,
            "Precio_real_nac": p_nom_n * factor,
            "Brecha_pct": brecha,
            "Pct_no_cosechada": pct_nc,
            "Rendimiento": oax["Rendimiento"].mean(),
            "Volumen": vol_o,
        })
    return pd.DataFrame(filas).sort_values("Anio").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Censo 2022
# --------------------------------------------------------------------------- #
def censo_cafe_municipal():
    df = pd.read_csv(os.path.join(DATA, "ca2022_agr05.csv"), encoding="utf-8")
    df = df[df["ENT_FED"].astype(str).str.startswith(f"{ENT_CVE:02d} ")]
    df = df[_cafe_exacto(df["DESCRIPCION"]) & df["NOM_MUN"].notna()].copy()
    df["MUN_KEY"] = df["NOM_MUN"].apply(lambda x: norm(re.sub(r"^\s*\d+\s", "", str(x))))
    for c in ["UP_TOTAL", "SUPSEM_AGCA_PER", "TON_AGCA"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    out = df[["MUN_KEY", "UP_TOTAL", "SUPSEM_AGCA_PER", "TON_AGCA"]].rename(columns={
        "UP_TOTAL": "CEN_UP", "SUPSEM_AGCA_PER": "CEN_Sup", "TON_AGCA": "CEN_Ton"})
    return out.groupby("MUN_KEY", as_index=False).sum(numeric_only=True)


def censo_destino_estatal():
    df = pd.read_csv(os.path.join(DATA, "ca2022_agr07.csv"), encoding="utf-8")
    df = df[(df["ENT_FED"] == f"{ENT_CVE:02d} OAX") & _cafe_exacto(df["DESCRIPCION"])]
    if df.empty:
        return {}
    r = df.iloc[0]
    up_t = float(r["UP_TOTAL"])
    up_v = float(r["UP_VENTA"])
    up_c = float(r["UP_CONSFAM"])
    up_s = float(r["UP_SEMILLA"])
    up_a = float(r["UP_CONSANIM"])
    ton_t = float(r["TON_AGCA_CUL"])
    ton_v = float(r["TON_VENTA_CUL"])
    return {
        "up_total": up_t, "up_venta": up_v, "up_autoconsumo": up_c,
        "up_semilla": up_s, "up_consanim": up_a,
        "pct_vende": up_v / up_t if up_t else np.nan,
        "pct_autoconsumo": up_c / up_t if up_t else np.nan,
        "pct_semilla": up_s / up_t if up_t else np.nan,
        "pct_consanim": up_a / up_t if up_t else np.nan,
        "up_no_vende": up_t - up_v,
        "pct_no_vende": (up_t - up_v) / up_t if up_t else np.nan,
        "ton_total": ton_t, "ton_venta": ton_v,
        "pct_ton_vendida": ton_v / ton_t if ton_t else np.nan,
    }


def censo_perfil():
    def _muni_total(path, col, salida):
        df = pd.read_csv(os.path.join(DATA, path), encoding="utf-8")
        df = df[df["ENT_FED"].astype(str).str.startswith(f"{ENT_CVE:02d} ")]
        df = df[df["ESTRATO"].isna() & df["MUNICIPIO"].notna()].copy()
        df["MUN_KEY"] = df["MUNICIPIO"].apply(norm)
        if isinstance(col, list):
            for c in col:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df[salida] = df[col].sum(axis=1)
        else:
            df[salida] = pd.to_numeric(df[col], errors="coerce")
        return df.groupby("MUN_KEY", as_index=False)[salida].first()

    ind = _muni_total("ca2022_soc03.csv", "P_SI_INDIG", "SOC_indigena")
    esc = _muni_total("ca2022_soc04.csv",
                      ["P_PROD_PRESC", "P_PROD_PRIM", "P_PROD_SINEST"], "SOC_prim_menos")

    cr = pd.read_csv(os.path.join(DATA, "ca2022_cred01.csv"), encoding="utf-8")
    cr = cr[cr["NOMBRE"].astype(str).str.startswith(f"{ENT_CVE:02d} ") & cr["NOM_MUN"].notna()].copy()
    cr["MUN_KEY"] = cr["NOM_MUN"].apply(norm)
    for c in ["UP_TOTAL", "UP_OBTEN_CRED"]:
        cr[c] = pd.to_numeric(cr[c], errors="coerce")
    cr["CRED_pct"] = np.where(cr["UP_TOTAL"] > 0, cr["UP_OBTEN_CRED"] / cr["UP_TOTAL"] * 100, np.nan)
    cred = cr.groupby("MUN_KEY", as_index=False)["CRED_pct"].first()

    return ind.merge(esc, on="MUN_KEY", how="outer").merge(cred, on="MUN_KEY", how="outer")


# --------------------------------------------------------------------------- #
# Cruce Grupo 3 (estructura x desempeño)
# --------------------------------------------------------------------------- #
def cargar_geojson():
    """GeoJSON optimizado de los 570 municipios de Oaxaca (clave cve_mun)."""
    import json
    ruta = os.path.join(DATA, "oaxaca_municipios.geojson")
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def contexto_nacional(siap, anio):
    """Producción y precio de café por estado en un año (para contraste estado/país)."""
    es_cafe = _es_cafe(siap["Nomcultivo"])
    cy = siap[es_cafe & (siap["Anio"] == anio)]
    est = (cy.groupby("Nomestado", as_index=False)
             .apply(lambda g: pd.Series({
                 "Volumen": g["Volumenproduccion"].sum(),
                 "Precio": ((g["Preciomediorural"] * g["Volumenproduccion"]).sum()
                            / g["Volumenproduccion"].sum()) if g["Volumenproduccion"].sum() else np.nan,
                 "Valor": g["Valorproduccion"].sum(),
             }), include_groups=False)
             .sort_values("Volumen", ascending=False))
    return est


def cruce_grupo3(siap, inpc, anio_base=2024, ventana=(2018, 2024)):
    es_cafe = _es_cafe(siap["Nomcultivo"])
    cafe = siap[es_cafe & (siap["Nomestado"] == ENT_NOMBRE)].copy()
    gw = cafe[(cafe["Anio"] >= ventana[0]) & (cafe["Anio"] <= ventana[1])].copy()
    I_base = inpc.get(anio_base, np.nan)
    gw["factor"] = gw["Anio"].map(lambda a: I_base / inpc.get(int(a), np.nan) if pd.notna(a) else np.nan)
    gw["preal"] = gw["Preciomediorural"] * gw["factor"]

    def agg(g):
        vol = g["Volumenproduccion"].sum()
        preal = ((g["preal"] * g["Volumenproduccion"]).sum() / vol) if vol else g["preal"].mean()
        semb, cos = g["Sembrada"].sum(), g["Cosechada"].sum()
        return pd.Series({
            "Nommunicipio": g["Nommunicipio"].iloc[0],
            "precio_real": preal, "rendimiento": g["Rendimiento"].mean(),
            "pct_no_cosechada": (semb - cos) / semb * 100 if semb else np.nan,
            "volumen": vol})

    rm = gw.groupby("Idmunicipio").apply(agg, include_groups=False).reset_index()
    rm["MUN_KEY"] = rm["Nommunicipio"].apply(norm)
    perfil = censo_perfil()
    return rm.merge(perfil, on="MUN_KEY", how="left")
