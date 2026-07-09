# -*- coding: utf-8 -*-
"""
Deflactor de precios con INPC oficial (INEGI, base 2ª quincena julio 2018 = 100).
Convierte precios nominales del SIAP a precios reales en pesos de un año base.

Fuente del INPC: INEGI, INPC general mensual 2010-2024 (180 meses verificados).
Archivo fijo en el repositorio: data/inpc_anual.csv (promedio anual).

Uso:
    from deflactor import cargar_inpc, a_precio_real
    inpc = cargar_inpc("data/inpc_anual.csv")
    precio_real = a_precio_real(precio_nominal, anio, inpc, anio_base=2024)
"""

import os
import pandas as pd

ANIO_BASE_DEFAULT = 2024


def cargar_inpc(ruta):
    """Lee inpc_anual.csv (columnas: anio, inpc) y devuelve un dict {anio: inpc}."""
    if not os.path.exists(ruta):
        raise FileNotFoundError(
            f"No se encontró el INPC en {ruta}. "
            "Coloca data/inpc_anual.csv en el repositorio."
        )
    df = pd.read_csv(ruta)
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
    df["inpc"] = pd.to_numeric(df["inpc"], errors="coerce")
    df = df.dropna(subset=["anio", "inpc"])
    return dict(zip(df["anio"].astype(int), df["inpc"]))


def factor_deflactor(anio, inpc, anio_base=ANIO_BASE_DEFAULT):
    """Factor multiplicativo para llevar 'anio' a pesos de 'anio_base'."""
    if anio not in inpc or anio_base not in inpc:
        return float("nan")
    return inpc[anio_base] / inpc[anio]


def a_precio_real(precio_nominal, anio, inpc, anio_base=ANIO_BASE_DEFAULT):
    """precio_real = precio_nominal * (INPC_base / INPC_anio)."""
    return precio_nominal * factor_deflactor(anio, inpc, anio_base)


def deflactar_columna(df, col_precio, col_anio, inpc,
                      anio_base=ANIO_BASE_DEFAULT, nombre_salida=None):
    """Agrega una columna de precio real a un DataFrame (vectorizado)."""
    nombre_salida = nombre_salida or f"{col_precio}_real_{anio_base}"
    factores = df[col_anio].map(lambda a: factor_deflactor(int(a), inpc, anio_base)
                                if pd.notna(a) else float("nan"))
    df[nombre_salida] = df[col_precio] * factores
    return df


if __name__ == "__main__":
    inpc = cargar_inpc("/mnt/user-data/outputs/inpc_anual.csv")
    print("INPC cargado:", len(inpc), "años")
    print("Factor 2010 -> 2024:", round(factor_deflactor(2010, inpc), 4))
    print("$5,000 (2010) en pesos de 2024:",
          round(a_precio_real(5000, 2010, inpc), 0))
