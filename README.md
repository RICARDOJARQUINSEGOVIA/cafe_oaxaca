# ☕ Dashboard — Café de Oaxaca (SIAP + Censo + INPC)

Aplicación Streamlit de apoyo al proyecto **"Modelo competitivo de comercialización
de café para el desarrollo de las microempresas rurales de Oaxaca"**.

Consolida cuatro bloques analíticos ya validados:

1. **Serie histórica SIAP 2010-2024** — producción, precio, rendimiento.
2. **Deflactor INPC** — precios reales (poder adquisitivo del productor).
3. **Índices Grupo 1** — Cociente de Localización (LQ), Gini, HHI, brecha de precio,
   vulnerabilidad (superficie no cosechada).
4. **Cruce Grupo 3** — perfil del productor (Censo 2022) × desempeño histórico (SIAP).

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Datos (carpeta `data/`)

La app lee todo de `data/`. Debe contener:

| Archivo(s) | Fuente | Nota |
|---|---|---|
| `2010.csv` … `2024.csv` | SIAP cierre agrícola | encoding latin-1, 24 columnas |
| `inpc_anual.csv` | INEGI (INPC promedio anual) | ya incluido, base 2018 |
| `ca2022_agr05.csv` | Censo Agropecuario 2022 | café municipal |
| `ca2022_agr07.csv` | Censo 2022 | destino de producción (estatal) |
| `ca2022_soc03.csv` | Censo 2022 | habla indígena por municipio |
| `ca2022_soc04.csv` | Censo 2022 | nivel de estudios |
| `ca2022_cred01.csv` | Censo 2022 | crédito y seguro |

> Los 15 CSV del SIAP no se incluyen en el ZIP por tamaño. Cópialos a `data/`
> antes de ejecutar (son los mismos que ya tienes).

## Ejecutar

```bash
streamlit run app.py
```

Abre en http://localhost:8501

## Pestañas

- **Resumen** — KPIs y hallazgos centrales; foto de venta vs. autoconsumo.
- **Precio justo** — precio real vs. nominal y brecha con el nacional.
- **Especialización y concentración** — LQ, Gini, HHI en el tiempo.
- **Vulnerabilidad** — superficie no cosechada y rendimiento (huella de la roya).
- **Comercialización (Censo)** — estructura de venta y café municipal 2022.
- **Estructura × Desempeño** — cruce interactivo (elige variables); muestra correlación.
- **Datos** — tablas y descarga CSV.

## Controles (barra lateral)

- **Año base de precios reales**: 2024 (default), 2018 o 2010.
- **Municipios objetivo**: pega tus 28 municipios para resaltarlos en el cruce.

## Notas metodológicas (importantes para el uso académico)

- **Precios reales** deflactados con INPC oficial (INEGI, base 2ª quincena julio 2018).
- **Vulnerabilidad**: el SIAP no llena "Siniestrada" en perennes; se usa la brecha
  sembrada−cosechada como proxy válido.
- **SIAP vs. Censo** miden cosas parecidas pero no idénticas (años y definiciones
  distintas); se usan como fuentes complementarias, no aditivas.
- **Destino de venta** detallado solo existe a nivel estatal (confidencialidad del
  Censo); el detalle municipal corresponde a la encuesta a 500 productores.
- **Cruce Grupo 3**: correlaciones = asociación, NO causalidad. Magnitudes débiles
  a moderadas. Los resultados nulos (p. ej. escolaridad) se reportan igual.

## Arquitectura

- `carga.py` — capa de datos (lectura, integración, índices). Reutilizable.
- `app.py` — interfaz Streamlit. Consume `carga.py`.
- Todo cacheado con `@st.cache_data` para respuesta rápida.
