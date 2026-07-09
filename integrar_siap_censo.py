# -*- coding: utf-8 -*-
"""
Integrador de bases municipales de café — Oaxaca
Une SIAP (producción/precio) + Censo Agropecuario 2022 (comercialización, perfil)
por clave INEGI de municipio (CVE_MUN de 5 dígitos: EE + MMM).

Fuentes:
  - SIAP: cierre agrícola, archivos AAAA.csv (2010-2024), encoding latin-1
  - Censo Agropecuario 2022, datos abiertos (upagro_csv), encoding utf-8:
      ca2022_agr05  -> café municipal (UP, superficie, producción)
      ca2022_agr07  -> destino de producción por estado (autoconsumo vs venta)
      ca2022_soc03  -> habla indígena por municipio y sexo
      ca2022_soc04  -> nivel de estudios por municipio y sexo
      ca2022_cred01 -> crédito y seguro por municipio

Salida: dataset municipal maestro (un renglón por municipio-año de café).
"""

import glob
import os
import re
import unicodedata

import numpy as np
import pandas as pd

UPLOADS = "/mnt/user-data/uploads"
OUT = "/mnt/user-data/outputs"
ENT_OAX = 20  # clave INEGI de Oaxaca


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def norm(s):
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def cve_mun(ent, mun):
    """Clave INEGI de 5 dígitos: EE + MMM."""
    return f"{int(ent):02d}{int(mun):03d}"


def es_cafe(serie):
    """True para 'Café' exacto; excluye 'Ixhuatlán del Café' (municipio)."""
    return serie.astype(str).apply(lambda x: norm(x) == "cafe")


# --------------------------------------------------------------------------- #
# 1) SIAP — café municipal, todos los años disponibles
# --------------------------------------------------------------------------- #
def cargar_siap(entidad=ENT_OAX):
    rutas = sorted(glob.glob(os.path.join(UPLOADS, "20[0-9][0-9].csv")))
    frames = []
    for r in rutas:
        try:
            df = pd.read_csv(r, encoding="latin-1", low_memory=False)
            frames.append(df)
        except Exception as e:
            print(f"  aviso: no se pudo leer {r}: {e}")
    if not frames:
        raise SystemExit("No se encontraron archivos SIAP (AAAA.csv) en uploads.")

    siap = pd.concat(frames, ignore_index=True)
    for c in ["Sembrada", "Cosechada", "Siniestrada", "Volumenproduccion",
              "Rendimiento", "Preciomediorural", "Valorproduccion", "Anio"]:
        siap[c] = pd.to_numeric(siap[c], errors="coerce")

    siap = siap[siap["Nomcultivo"].astype(str).str.contains("caf", case=False, na=False)]
    siap = siap[siap["Idestado"] == entidad].copy()
    siap["CVE_MUN"] = siap.apply(lambda r: cve_mun(r["Idestado"], r["Idmunicipio"]), axis=1)

    # Agregar por municipio-año (suma sobre modalidades/ciclos; precio ponderado por volumen)
    def _agg(g):
        vol = g["Volumenproduccion"].sum()
        val = g["Valorproduccion"].sum()
        # precio medio rural ponderado por volumen; si no hay volumen, promedio simple
        if vol and vol > 0:
            precio = (g["Preciomediorural"] * g["Volumenproduccion"]).sum() / vol
        else:
            precio = g["Preciomediorural"].mean()
        return pd.Series({
            "SIAP_Sembrada": g["Sembrada"].sum(),
            "SIAP_Cosechada": g["Cosechada"].sum(),
            "SIAP_Siniestrada": g["Siniestrada"].sum(),
            "SIAP_Volumen_ton": vol,
            "SIAP_Valor_pesos": val,
            "SIAP_Precio_rural": precio,
            "SIAP_Rendimiento": g["Rendimiento"].mean(),
            "Nommunicipio": g["Nommunicipio"].iloc[0],
        })

    out = (siap.groupby(["CVE_MUN", "Anio"], as_index=False)
                .apply(_agg, include_groups=False)
                .reset_index(drop=True))
    return out


# --------------------------------------------------------------------------- #
# 2) Censo agr05 — café municipal (2022)
# --------------------------------------------------------------------------- #
def cargar_censo_agr05(entidad=ENT_OAX):
    df = pd.read_csv(os.path.join(UPLOADS, "ca2022_agr05.csv"), encoding="utf-8")
    ent_str = df["ENT_FED"].astype(str)
    df = df[ent_str.str.startswith(f"{entidad:02d} ")]
    df = df[es_cafe(df["DESCRIPCION"])]
    df = df[df["NOM_MUN"].notna()].copy()

    # NOM_MUN viene como '002 Acatlán de Pérez Figueroa' -> extraer clave
    def _cve(nom):
        m = re.match(r"\s*(\d{1,3})\s", str(nom))
        return cve_mun(entidad, m.group(1)) if m else None

    df["CVE_MUN"] = df["NOM_MUN"].apply(_cve)
    df = df[df["CVE_MUN"].notna()]

    for c in ["UP_TOTAL", "SUPSEM_AGCA_PER", "SUPCOS_AGCA_PER", "TON_AGCA"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    out = df[["CVE_MUN", "UP_TOTAL", "SUPSEM_AGCA_PER", "SUPCOS_AGCA_PER", "TON_AGCA"]].copy()
    out = out.rename(columns={
        "UP_TOTAL": "CEN_UP_cafe",
        "SUPSEM_AGCA_PER": "CEN_SupSembrada",
        "SUPCOS_AGCA_PER": "CEN_SupCosechada",
        "TON_AGCA": "CEN_Volumen_ton",
    })
    return out.groupby("CVE_MUN", as_index=False).sum(numeric_only=True)


# --------------------------------------------------------------------------- #
# 3) Censo agr07 — destino (autoconsumo vs venta). Nivel ESTADO.
#    Se reparte como CONTEXTO estatal (mismo valor para todos los municipios).
# --------------------------------------------------------------------------- #
def cargar_censo_agr07(entidad=ENT_OAX):
    df = pd.read_csv(os.path.join(UPLOADS, "ca2022_agr07.csv"), encoding="utf-8")
    df = df[(df["ENT_FED"] == f"{entidad:02d} OAX") & es_cafe(df["DESCRIPCION"])].copy()
    if df.empty:
        return None
    r = df.iloc[0]
    up_total = float(r["UP_TOTAL"])
    up_venta = float(r["UP_VENTA"])
    up_consfam = float(r["UP_CONSFAM"])
    ton_total = float(r["TON_AGCA_CUL"])
    ton_venta = float(r["TON_VENTA_CUL"])
    return {
        "CTX_UP_total_cafe": up_total,
        "CTX_UP_venta": up_venta,
        "CTX_UP_autoconsumo": up_consfam,
        "CTX_pct_UP_que_vende": up_venta / up_total if up_total else np.nan,
        "CTX_pct_UP_autoconsumo": up_consfam / up_total if up_total else np.nan,
        "CTX_Ton_total": ton_total,
        "CTX_Ton_venta": ton_venta,
        "CTX_pct_Ton_vendida": ton_venta / ton_total if ton_total else np.nan,
    }


# --------------------------------------------------------------------------- #
# 4) Censo soc03 (indígena) y soc04 (estudios) — municipal, total UP (no solo café)
# --------------------------------------------------------------------------- #
def cargar_soc(entidad=ENT_OAX):
    # En soc03/soc04 el municipio viene por NOMBRE (sin clave numérica).
    # Se une por nombre normalizado. ESTRATO NaN = total (ambos sexos).
    s3 = pd.read_csv(os.path.join(UPLOADS, "ca2022_soc03.csv"), encoding="utf-8")
    s3 = s3[s3["ENT_FED"].astype(str).str.startswith(f"{entidad:02d} ")]
    s3 = s3[s3["ESTRATO"].isna() & s3["MUNICIPIO"].notna()].copy()
    s3["MUN_KEY"] = s3["MUNICIPIO"].apply(norm)
    s3["P_SI_INDIG"] = pd.to_numeric(s3["P_SI_INDIG"], errors="coerce")
    soc3 = s3[["MUN_KEY", "P_SI_INDIG"]].rename(columns={"P_SI_INDIG": "SOC_pct_indigena"})
    soc3 = soc3.groupby("MUN_KEY", as_index=False).first()

    s4 = pd.read_csv(os.path.join(UPLOADS, "ca2022_soc04.csv"), encoding="utf-8")
    s4 = s4[s4["ENT_FED"].astype(str).str.startswith(f"{entidad:02d} ")]
    s4 = s4[s4["ESTRATO"].isna() & s4["MUNICIPIO"].notna()].copy()
    s4["MUN_KEY"] = s4["MUNICIPIO"].apply(norm)
    for c in ["P_PROD_PRESC", "P_PROD_PRIM", "P_PROD_SINEST"]:
        s4[c] = pd.to_numeric(s4[c], errors="coerce")
    s4["SOC_pct_prim_o_menos"] = s4[["P_PROD_PRESC", "P_PROD_PRIM", "P_PROD_SINEST"]].sum(axis=1)
    soc4 = s4[["MUN_KEY", "SOC_pct_prim_o_menos"]].groupby("MUN_KEY", as_index=False).first()

    return soc3.merge(soc4, on="MUN_KEY", how="outer")


# --------------------------------------------------------------------------- #
# 5) Censo cred01 — crédito y seguro municipal
# --------------------------------------------------------------------------- #
def cargar_credito(entidad=ENT_OAX):
    # cred01: clave estatal en NOMBRE ('20 OAX'); municipio por nombre en NOM_MUN.
    df = pd.read_csv(os.path.join(UPLOADS, "ca2022_cred01.csv"), encoding="utf-8")
    df = df[df["NOMBRE"].astype(str).str.startswith(f"{entidad:02d} ")]
    df = df[df["NOM_MUN"].notna()].copy()
    df["MUN_KEY"] = df["NOM_MUN"].apply(norm)
    for c in ["UP_TOTAL", "UP_SOLIC_CRED", "UP_OBTEN_CRED", "UP_OBTEN_SEG"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["CRED_pct_obtuvo_credito"] = np.where(
        df["UP_TOTAL"] > 0, df["UP_OBTEN_CRED"] / df["UP_TOTAL"], np.nan)
    df["CRED_pct_obtuvo_seguro"] = np.where(
        df["UP_TOTAL"] > 0, df["UP_OBTEN_SEG"] / df["UP_TOTAL"], np.nan)
    out = df[["MUN_KEY", "CRED_pct_obtuvo_credito", "CRED_pct_obtuvo_seguro"]]
    return out.groupby("MUN_KEY", as_index=False).first()


# --------------------------------------------------------------------------- #
# INTEGRACIÓN
# --------------------------------------------------------------------------- #
def main():
    print("1) Cargando SIAP...")
    siap = cargar_siap()
    anios = sorted(siap["Anio"].dropna().unique().astype(int))
    print(f"   SIAP: {len(siap)} filas municipio-año | años {anios}")

    print("2) Cargando Censo agr05 (café municipal)...")
    cen05 = cargar_censo_agr05()
    print(f"   Censo café municipal: {len(cen05)} municipios")

    print("3) Cargando Censo agr07 (destino estatal)...")
    ctx = cargar_censo_agr07()
    if ctx:
        print(f"   Oaxaca: {ctx['CTX_pct_UP_que_vende']*100:.1f}% de UP vende, "
              f"{ctx['CTX_pct_UP_autoconsumo']*100:.1f}% autoconsumo familiar")

    print("4) Cargando Censo soc03/soc04 (perfil)...")
    soc = cargar_soc()
    print(f"   Perfil municipal: {len(soc)} municipios")

    print("5) Cargando Censo cred01 (crédito)...")
    cred = cargar_credito()
    print(f"   Crédito municipal: {len(cred)} municipios")

    # Base municipal-año del SIAP como esqueleto
    df = siap.copy()
    df["MUN_KEY"] = df["Nommunicipio"].apply(norm)
    df = df.merge(cen05, on="CVE_MUN", how="left")       # café: por clave INEGI
    df = df.merge(soc, on="MUN_KEY", how="left")         # perfil: por nombre
    df = df.merge(cred, on="MUN_KEY", how="left")        # crédito: por nombre
    df = df.drop(columns=["MUN_KEY"])

    # Contexto estatal (mismo valor para todas las filas) — hallazgo central
    if ctx:
        for k, v in ctx.items():
            df[k] = v

    # Orden de columnas
    cols_id = ["CVE_MUN", "Nommunicipio", "Anio"]
    cols_siap = [c for c in df.columns if c.startswith("SIAP_")]
    cols_cen = [c for c in df.columns if c.startswith("CEN_")]
    cols_soc = [c for c in df.columns if c.startswith("SOC_")]
    cols_cred = [c for c in df.columns if c.startswith("CRED_")]
    cols_ctx = [c for c in df.columns if c.startswith("CTX_")]
    df = df[cols_id + cols_siap + cols_cen + cols_soc + cols_cred + cols_ctx]
    df = df.sort_values(["Anio", "Nommunicipio"]).reset_index(drop=True)

    os.makedirs(OUT, exist_ok=True)
    csv_path = os.path.join(OUT, "dataset_integrado_cafe_oaxaca.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n✔ Dataset integrado: {len(df)} filas, {len(df.columns)} columnas")
    print(f"  Guardado en: {csv_path}")

    # Diccionario de variables
    dic = pd.DataFrame({
        "Variable": df.columns,
        "Fuente": (["ID"]*len(cols_id) + ["SIAP"]*len(cols_siap) +
                   ["Censo agr05"]*len(cols_cen) + ["Censo soc03/04"]*len(cols_soc) +
                   ["Censo cred01"]*len(cols_cred) + ["Censo agr07 (estatal)"]*len(cols_ctx)),
        "Nivel": (["—"]*len(cols_id) + ["Municipio-año"]*len(cols_siap) +
                  ["Municipio (2022)"]*len(cols_cen) + ["Municipio (2022)"]*len(cols_soc) +
                  ["Municipio (2022)"]*len(cols_cred) + ["Estado (2022)"]*len(cols_ctx)),
    })
    return df, dic, ctx, csv_path


if __name__ == "__main__":
    df, dic, ctx, path = main()
    df.to_pickle("/home/claude/_df.pkl")
    dic.to_pickle("/home/claude/_dic.pkl")
    import json
    json.dump(ctx, open("/home/claude/_ctx.json", "w"))
