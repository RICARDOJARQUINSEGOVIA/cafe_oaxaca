# -*- coding: utf-8 -*-
"""
Dashboard — Modelo competitivo de comercialización de café · Oaxaca
Proyecto General de Protocolo y Bases.

Fuentes:
  · SIAP (SIAP-SADER), Cierre de la producción agrícola, 2010-2024.
  · INEGI, Censo Agropecuario 2022.
  · INEGI, Índice Nacional de Precios al Consumidor (base 2Q jul-2018).
  · INEGI, Marco Geoestadístico (geometrías municipales).

Ejecutar:  streamlit run app.py
"""

import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import carga

# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Café Oaxaca · SIAP + Censo INEGI",
                   page_icon="☕", layout="wide")

# Paleta: base café con acentos vivos (académico pero colorido)
C = {
    "cafe":   "#6F4E37",
    "tierra": "#A9744F",
    "crema":  "#D8C3A5",
    "naranja":"#E8871E",
    "verde":  "#4C9A5C",
    "azul":   "#2E6E9E",
    "vino":   "#9B2D30",
    "morado": "#6A4C93",
    "amarillo":"#E9B44C",
}
SECUENCIAL = ["#F3E9DC", "#D8C3A5", "#C89F72", "#A9744F", "#6F4E37", "#4A3226"]

# CSS: agranda tipografía de métricas y da aire
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 30px; }
[data-testid="stMetricLabel"] { font-size: 15px; }
.block-container { padding-top: 2rem; max-width: 100%; }
h1 { color: #4A3226; }
h2, h3 { color: #6F4E37; }
.fuente { font-size: 12px; color: #8a7a6a; font-style: italic;
          border-left: 3px solid #D8C3A5; padding-left: 8px; margin: 4px 0 12px; }
.explica { font-size: 14px; color: #4a4a4a; background: #FaF6F0;
           border-radius: 8px; padding: 10px 14px; margin: 6px 0 14px; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Cargando y procesando datos…")
def _todo():
    siap = carga.cargar_siap_serie()
    inpc = carga.cargar_inpc()
    return siap, inpc


@st.cache_data(show_spinner=False)
def _derivados(anio_base):
    siap, inpc = _todo()
    idx = carga.indices_grupo1(siap, inpc, anio_base)
    cru = carga.cruce_grupo3(siap, inpc, anio_base)
    ctx = carga.censo_destino_estatal()
    cen_mun = carga.censo_cafe_municipal()
    return idx, cru, ctx, cen_mun


@st.cache_data(show_spinner=False)
def _geojson():
    return carga.cargar_geojson()


@st.cache_data(show_spinner=False)
def _nacional(anio):
    siap, _ = _todo()
    return carga.contexto_nacional(siap, anio)


try:
    siap, inpc = _todo()
except Exception as e:
    st.error(f"No se pudieron cargar los datos. Revisa la carpeta data/. Detalle: {e}")
    st.stop()


def fuente(txt):
    st.markdown(f'<p class="fuente">Fuente: {txt}</p>', unsafe_allow_html=True)


def explica(txt):
    st.markdown(f'<p class="explica">📊 <b>Cómo leer esta gráfica:</b> {txt}</p>',
                unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
st.sidebar.title("☕ Café de Oaxaca")
st.sidebar.caption("Diagnóstico con datos oficiales · SIAP + INEGI")

PAGINAS = ["Resumen", "Precio justo", "Especialización", "Vulnerabilidad",
           "Comercialización", "Estructura × Desempeño", "🗺️ Mapa", "Datos"]
pagina = st.sidebar.radio("Sección", PAGINAS, index=0)
st.sidebar.divider()

anio_base = st.sidebar.selectbox("Precios reales en pesos de:", [2024, 2018, 2010], index=0)
idx, cru, ctx, cen_mun = _derivados(anio_base)

st.sidebar.divider()
st.sidebar.markdown("**Municipios objetivo (opcional)**")
munis_txt = st.sidebar.text_area("Uno por línea, para resaltar", height=90,
                                 label_visibility="collapsed",
                                 placeholder="Pluma Hidalgo\nCandelaria Loxicha\n...")
munis_obj = {carga.norm(m) for m in munis_txt.splitlines() if m.strip()}

st.sidebar.divider()
st.sidebar.markdown("""
<span style="font-size:12px; color:#8a7a6a;">
<b>Fuentes:</b><br>
SIAP-SADER. Cierre de la producción agrícola, 2010-2024.<br>
INEGI. Censo Agropecuario 2022.<br>
INEGI. INPC (base 2ª quincena julio 2018).<br>
INEGI. Marco Geoestadístico.
</span>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
st.title("Diagnóstico de producción y comercialización de café en Oaxaca")
st.caption(f"Serie 2010-2024 · Precios reales en pesos de {anio_base} · "
           "Proyecto General de Protocolo y Bases")

# =========================================================================== #
# RESUMEN
# =========================================================================== #
if pagina == "Resumen":
    ult, pri = idx.iloc[-1], idx.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Municipios cafetaleros", f"{int(ult['Municipios'])}")
    c2.metric(f"Precio real ({anio_base})", f"${ult['Precio_real']:,.0f}/ton",
              f"{(ult['Precio_real']-pri['Precio_real'])/pri['Precio_real']*100:+.1f}% vs 2010")
    c3.metric("Brecha vs. nacional", f"{ult['Brecha_pct']:+.1f}%")
    c4.metric("Volumen (ton)", f"{ult['Volumen']:,.0f}")
    st.divider()

    colA, colB = st.columns([3, 2])
    with colA:
        st.markdown("#### Hallazgos centrales del diagnóstico")
        st.markdown(f"""
- **Precio real estancado:** en pesos de {anio_base}, el precio del café en Oaxaca
  no mejoró en 15 años pese a que el nominal subió. El productor conserva casi el
  mismo poder adquisitivo que en 2010.
- **Desventaja persistente:** Oaxaca recibió un precio por debajo de la media
  nacional los 15 años de la serie, sin excepción.
- **Café de subsistencia:** según el Censo 2022, **{ctx['pct_no_vende']*100:.0f}%**
  de las unidades no vende nada (solo autoconsumo). Aun así, quienes sí venden
  concentran el **{ctx['pct_ton_vendida']*100:.0f}%** del volumen: los que no venden
  son productores muy pequeños.
- **El problema es comercial, no productivo:** los municipios con más población
  indígena producen con mejor rendimiento y menor pérdida, pero reciben menor
  precio y menos crédito.
        """)
    with colB:
        vende = ctx["up_venta"]
        no_vende = ctx["up_no_vende"]
        fig = go.Figure(go.Pie(labels=["Vende parte o toda su cosecha",
                                       "No vende (solo autoconsumo/otros)"],
                               values=[vende, no_vende], hole=0.55,
                               marker_colors=[C["naranja"], C["crema"]]))
        fig.update_layout(height=280, margin=dict(t=30, b=10, l=10, r=10),
                          title="¿Vende o no vende su café? (Censo 2022)",
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)
        fuente(f"INEGI, Censo Agropecuario 2022. Base: {ctx['up_total']:,.0f} unidades "
               "de producción de café en Oaxaca. Reparto excluyente (suma 100%).")

# =========================================================================== #
# PRECIO JUSTO
# =========================================================================== #
if pagina == "Precio justo":
    st.subheader("Precio real vs. nominal y brecha con el promedio nacional")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=idx["Anio"], y=idx["Precio_nominal"], name="Precio nominal",
                             line=dict(color=C["crema"], dash="dot", width=2.5)))
    fig.add_trace(go.Scatter(x=idx["Anio"], y=idx["Precio_real"], name=f"Precio real (${anio_base})",
                             line=dict(color=C["naranja"], width=3.5)))
    fig.add_trace(go.Scatter(x=idx["Anio"], y=idx["Precio_real_nac"], name="Precio real nacional",
                             line=dict(color=C["azul"], dash="dash", width=2.5)))
    fig.update_layout(height=440, plot_bgcolor="white", yaxis_title="$/ton",
                      legend=dict(orientation="h", y=1.12), margin=dict(t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
    fuente("SIAP-SADER (precio medio rural) deflactado con INPC de INEGI.")
    explica("la línea punteada beige es el precio en pesos corrientes (nominal); sube, pero "
            "engaña porque incluye inflación. La línea naranja es el precio real (descontada la "
            "inflación): si está plana, el productor no mejoró su poder de compra. La línea azul "
            "es el promedio nacional: siempre por encima de Oaxaca.")

    st.markdown("##### Brecha de precio: Oaxaca vs. nacional (%)")
    figb = px.bar(idx, x="Anio", y="Brecha_pct", color="Brecha_pct",
                  color_continuous_scale=["#9B2D30", "#E8871E", "#4C9A5C"])
    figb.add_hline(y=0, line_color="gray")
    figb.update_layout(height=300, plot_bgcolor="white", coloraxis_showscale=False,
                       yaxis_title="% (negativo = Oaxaca recibe menos)", margin=dict(t=10, b=10))
    st.plotly_chart(figb, use_container_width=True)
    explica("cada barra es un año. Todas caen por debajo de cero: el productor oaxaqueño recibió "
            "menos que el promedio nacional en los 15 años. Entre más roja y baja la barra, mayor "
            "la desventaja (el peor año fue 2012, durante la crisis de la roya).")

# =========================================================================== #
# ESPECIALIZACIÓN
# =========================================================================== #
if pagina == "Especialización":
    st.subheader("Cociente de Localización (LQ) y concentración de la producción")
    col1, col2 = st.columns(2)
    with col1:
        figlq = go.Figure()
        figlq.add_trace(go.Scatter(x=idx["Anio"], y=idx["LQ"], line=dict(color=C["naranja"], width=3.5),
                                   fill="tozeroy", fillcolor="rgba(232,135,30,0.12)"))
        figlq.add_hline(y=1, line_dash="dash", line_color="gray",
                        annotation_text="LQ=1 (sin especialización)")
        figlq.update_layout(height=350, plot_bgcolor="white", title="LQ — especialización cafetalera",
                            yaxis_title="LQ", margin=dict(t=40, b=10))
        st.plotly_chart(figlq, use_container_width=True)
    with col2:
        figc = go.Figure()
        figc.add_trace(go.Scatter(x=idx["Anio"], y=idx["Gini"], name="Gini",
                                  line=dict(color=C["vino"], width=3)))
        figc.add_trace(go.Scatter(x=idx["Anio"], y=idx["HHI"], name="HHI",
                                  line=dict(color=C["morado"], width=3), yaxis="y2"))
        figc.update_layout(height=350, plot_bgcolor="white", title="Concentración entre municipios",
                           yaxis=dict(title="Gini", range=[0, 1]),
                           yaxis2=dict(title="HHI", overlaying="y", side="right"),
                           legend=dict(orientation="h", y=1.18), margin=dict(t=40, b=10))
        st.plotly_chart(figc, use_container_width=True)
    fuente("Cálculo propio con datos de SIAP-SADER. LQ (cociente de localización), "
           "índice de Gini e índice de Herfindahl-Hirschman (HHI).")
    explica("el LQ (izquierda) mide si Oaxaca se especializa en café más que el país: arriba de 1 "
            "sí. Cae con los años, señal de que el café pesa cada vez menos en su economía agrícola. "
            "El Gini y HHI (derecha) miden si la producción se concentra en pocos municipios: se "
            "mantienen altos, lo que justifica enfocar el proyecto en municipios específicos.")

# =========================================================================== #
# VULNERABILIDAD
# =========================================================================== #
if pagina == "Vulnerabilidad":
    st.subheader("Vulnerabilidad productiva: superficie no cosechada y rendimiento")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=idx["Anio"], y=idx["Pct_no_cosechada"], name="% no cosechada",
                         marker_color=C["tierra"]))
    fig.add_trace(go.Scatter(x=idx["Anio"], y=idx["Rendimiento"], name="Rendimiento (ton/ha)",
                             line=dict(color=C["verde"], width=3.5), yaxis="y2"))
    fig.update_layout(height=440, plot_bgcolor="white",
                      yaxis=dict(title="% superficie no cosechada"),
                      yaxis2=dict(title="Rendimiento (ton/ha)", overlaying="y", side="right"),
                      legend=dict(orientation="h", y=1.12), margin=dict(t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
    fuente("SIAP-SADER. La vulnerabilidad se aproxima por la brecha entre superficie "
           "sembrada y cosechada (el SIAP no registra 'siniestrada' en cultivos perennes).")
    explica("las barras marrones son el % de superficie sembrada que NO se llegó a cosechar (pérdida). "
            "La línea verde es el rendimiento. Cuando las barras suben y la línea baja (2015-2019), es "
            "la huella de la epidemia de roya que golpeó a la cafeticultura oaxaqueña.")

# =========================================================================== #
# COMERCIALIZACIÓN
# =========================================================================== #
if pagina == "Comercialización":
    st.subheader("Estructura de comercialización — Censo Agropecuario 2022")
    c1, c2, c3 = st.columns(3)
    c1.metric("Unidades de producción de café", f"{ctx['up_total']:,.0f}")
    c2.metric("Vende parte o toda su cosecha", f"{ctx['pct_vende']*100:.1f}%")
    c3.metric("No vende (solo autoconsumo)", f"{ctx['pct_no_vende']*100:.1f}%")
    fuente("INEGI, Censo Agropecuario 2022 (tabulado agr07, nivel estatal). "
           "Estas dos categorías sí son excluyentes: suman 100%.")

    st.markdown("##### ¿A qué destina su café el productor oaxaqueño?")
    destinos = pd.DataFrame({
        "Destino": ["Venta", "Autoconsumo familiar", "Semilla", "Consumo animal"],
        "Porcentaje": [ctx["pct_vende"]*100, ctx["pct_autoconsumo"]*100,
                       ctx["pct_semilla"]*100, ctx["pct_consanim"]*100],
    })
    figd = px.bar(destinos.sort_values("Porcentaje"), x="Porcentaje", y="Destino",
                  orientation="h", color="Porcentaje",
                  color_continuous_scale=[C["crema"], C["tierra"], C["naranja"]],
                  text=destinos.sort_values("Porcentaje")["Porcentaje"].map(lambda v: f"{v:.1f}%"))
    figd.update_layout(height=280, plot_bgcolor="white", coloraxis_showscale=False,
                       xaxis_title="% de unidades de producción", margin=dict(t=10, b=10))
    figd.update_traces(textposition="outside")
    st.plotly_chart(figd, use_container_width=True)
    fuente("INEGI, Censo Agropecuario 2022 (tabulado agr07).")
    st.warning("⚠️ **Importante:** estos destinos NO son excluyentes y por eso suman más de "
               "100%. Una misma unidad de producción puede vender una parte de su café Y destinar "
               "otra al autoconsumo familiar a la vez. Cada barra responde a «¿la unidad destinó "
               "café a este fin? sí/no», no a un reparto del total. El reparto que sí suma 100% es "
               "el de arriba: vende (65.3%) vs. no vende (34.7%).")
    st.info(f"📌 Dato clave: aunque solo el {ctx['pct_vende']*100:.0f}% de las unidades vende, "
            f"esas ventas representan el **{ctx['pct_ton_vendida']*100:.0f}% del volumen** total "
            "de café del estado. Es decir, quienes no venden son productores muy pequeños cuya "
            "cosecha se destina sobre todo al hogar: café de subsistencia.")
    st.divider()

    st.markdown("##### Municipios con más unidades de producción de café (Censo 2022)")
    cen_top = cen_mun.sort_values("CEN_UP", ascending=False).head(20).copy()
    cen_top["Municipio"] = cen_top["MUN_KEY"].str.title()
    figm = px.bar(cen_top.sort_values("CEN_UP"), x="CEN_UP", y="Municipio", orientation="h",
                  color="CEN_UP", color_continuous_scale=SECUENCIAL,
                  labels={"CEN_UP": "Unidades de producción"})
    figm.update_layout(height=560, plot_bgcolor="white", coloraxis_showscale=False,
                       margin=dict(t=10, b=10))
    st.plotly_chart(figm, use_container_width=True)
    fuente("INEGI, Censo Agropecuario 2022 (tabulado agr05, nivel municipal).")
    explica("cada barra es un municipio y su largo es cuántas unidades de producción de café tiene. "
            "Identifica los polos productivos del estado. El destino de venta detallado "
            "(intermediario/industria) solo existe a nivel estatal por confidencialidad; el detalle "
            "municipal lo aportará la encuesta a productores.")

# =========================================================================== #
# ESTRUCTURA × DESEMPEÑO
# =========================================================================== #
if pagina == "Estructura × Desempeño":
    st.subheader("Cruce: perfil del productor (Censo 2022) × desempeño (SIAP 2018-2024)")
    labels_x = {"SOC_indigena": "% población indígena", "SOC_prim_menos": "% con primaria o menos",
                "CRED_pct": "% con crédito"}
    labels_y = {"precio_real": "Precio real", "rendimiento": "Rendimiento",
                "pct_no_cosechada": "% no cosechada"}
    cc1, cc2 = st.columns(2)
    eje_x = cc1.selectbox("Variable estructural (Censo 2022):", labels_x.keys(),
                          format_func=lambda k: labels_x[k])
    eje_y = cc2.selectbox("Variable de desempeño (SIAP):", labels_y.keys(),
                          format_func=lambda k: labels_y[k])

    d = cru[[eje_x, eje_y, "Nommunicipio", "volumen"]].dropna()
    if munis_obj:
        d = d.copy()
        d["Objetivo"] = d["Nommunicipio"].apply(lambda x: carga.norm(x) in munis_obj)
    figs = px.scatter(d, x=eje_x, y=eje_y, size="volumen",
                      color="Objetivo" if munis_obj else None,
                      color_discrete_map={True: C["naranja"], False: C["crema"]},
                      hover_name="Nommunicipio", trendline="ols",
                      trendline_color_override=C["vino"],
                      labels={eje_x: labels_x[eje_x], eje_y: labels_y[eje_y]})
    figs.update_layout(height=470, plot_bgcolor="white", margin=dict(t=10, b=10),
                       showlegend=bool(munis_obj))
    st.plotly_chart(figs, use_container_width=True)
    fuente("Cálculo propio. Perfil: INEGI, Censo Agropecuario 2022 (soc03/soc04/cred01). "
           "Desempeño: SIAP-SADER 2018-2024 deflactado.")
    if len(d) > 10:
        r = np.corrcoef(d[eje_x], d[eje_y])[0, 1]
        explica(f"cada punto es un municipio; el tamaño es su volumen de café. La línea roja marca la "
                f"tendencia. Correlación de Pearson: r = {r:+.3f} (n={len(d)}). Recuerda: indica "
                "asociación estadística, NO causa. Magnitudes débiles a moderadas.")

# =========================================================================== #
# MAPA
# =========================================================================== #
if pagina == "🗺️ Mapa":
    st.subheader("Mapa de Oaxaca por municipio")
    geo = _geojson()
    if geo is None:
        st.warning("No se encontró el GeoJSON de municipios en data/. "
                   "Coloca 'oaxaca_municipios.geojson' para activar el mapa.")
    else:
        var_map = st.selectbox("Indicador a mapear:",
                               ["precio_real", "rendimiento", "volumen", "SOC_indigena", "CRED_pct"],
                               format_func=lambda k: {"precio_real": "Precio real ($/ton)",
                                                      "rendimiento": "Rendimiento (ton/ha)",
                                                      "volumen": "Volumen (ton)",
                                                      "SOC_indigena": "% población indígena",
                                                      "CRED_pct": "% con crédito"}[k])
        dmap = cru[["Idmunicipio", "Nommunicipio", var_map]].dropna().copy()
        dmap["Idmunicipio"] = dmap["Idmunicipio"].astype(int)
        figmap = px.choropleth_mapbox(
            dmap, geojson=geo, locations="Idmunicipio",
            featureidkey="properties.cve_mun", color=var_map,
            color_continuous_scale="YlOrBr", hover_name="Nommunicipio",
            mapbox_style="carto-positron", zoom=6.3,
            center={"lat": 16.9, "lon": -96.5}, opacity=0.75)
        figmap.update_layout(height=560, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(figmap, use_container_width=True)
        fuente("Cálculo propio sobre geometrías de INEGI, Marco Geoestadístico. "
               "Datos de café: SIAP-SADER y Censo Agropecuario 2022.")
        explica("cada municipio se colorea según el indicador elegido (más oscuro = valor más alto). "
                "Los municipios en blanco no tienen registro de café. Pasa el cursor para ver el "
                "nombre y valor. Sirve para ubicar geográficamente dónde se concentra la producción "
                "o dónde el precio es más bajo.")

        st.divider()
        st.markdown("##### Contraste estado vs. país: producción de café por entidad")
        nac = _nacional(2024)
        nac["Es_Oaxaca"] = nac["Nomestado"] == "Oaxaca"
        fign = px.bar(nac.head(12).sort_values("Volumen"), x="Volumen", y="Nomestado",
                      orientation="h", color="Es_Oaxaca",
                      color_discrete_map={True: C["naranja"], False: C["crema"]},
                      labels={"Nomestado": "", "Volumen": "Volumen (ton)"})
        fign.update_layout(height=420, plot_bgcolor="white", showlegend=False,
                           margin=dict(t=10, b=10))
        st.plotly_chart(fign, use_container_width=True)
        fuente("SIAP-SADER, cierre 2024.")
        explica("compara la producción de café de Oaxaca (naranja) con los demás estados productores. "
                "Ubica a Oaxaca en el ranking nacional de volumen.")

# =========================================================================== #
# DATOS
# =========================================================================== #
if pagina == "Datos":
    st.subheader("Tablas y descargas")
    st.markdown("**Índices Grupo 1 (serie histórica)**")
    st.dataframe(idx.round(2), use_container_width=True, height=280)
    st.download_button("⬇️ Índices (CSV)", idx.to_csv(index=False).encode("utf-8-sig"),
                       "indices_grupo1.csv", "text/csv")
    st.markdown("**Cruce Grupo 3 (municipal)**")
    st.dataframe(cru.round(2), use_container_width=True, height=280)
    st.download_button("⬇️ Cruce (CSV)", cru.to_csv(index=False).encode("utf-8-sig"),
                       "cruce_grupo3.csv", "text/csv")
    st.divider()
    st.markdown("""
    **Referencias de fuentes (formato académico):**
    - SIAP-SADER. (2024). *Cierre de la producción agrícola* (2010-2024). Servicio de
      Información Agroalimentaria y Pesquera.
    - INEGI. (2023). *Censo Agropecuario 2022*. Instituto Nacional de Estadística y Geografía.
    - INEGI. (2024). *Índice Nacional de Precios al Consumidor* (base 2ª quincena julio 2018).
    - INEGI. (2023). *Marco Geoestadístico*. Áreas geoestadísticas municipales.
    """)
