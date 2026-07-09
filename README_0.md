# ☕ Dashboard SIAP — Café de Oaxaca

Tablero interactivo (Streamlit) de apoyo al proyecto **"Modelo competitivo de
comercialización de café para el desarrollo de las microempresas rurales de
Oaxaca"**. Usa las bases de cierre agrícola del **SIAP (2010–2024)**.

## 1. Instalación

```bash
# (recomendado) crear entorno
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## 2. Colocar los datos

Crea una carpeta `data/` junto a `app.py` y copia ahí tus 15 archivos:

```
cafe_dashboard/
├── app.py
├── requirements.txt
└── data/
    ├── 2010.csv
    ├── 2011.csv
    ├── ...
    └── 2024.csv
```

Los archivos deben tener el formato original del SIAP (24 columnas:
`Anio, Idestado, Nomestado, ... Nomcultivo, Sembrada, Cosechada, Siniestrada,
Volumenproduccion, Rendimiento, Preciomediorural, Valorproduccion`) y estar en
codificación **latin-1** (la que ya traen tus descargas). No necesitas
convertirlos.

> Si prefieres no usar la carpeta `data/`, puedes subir los CSV directamente
> desde la barra lateral del tablero (menú **«Cargar datos»**).

## 3. Ejecutar

```bash
streamlit run app.py
```

Se abrirá en el navegador (normalmente http://localhost:8501).

## 4. Qué contiene

| Pestaña | Aporte al proyecto |
|---|---|
| **Resumen ejecutivo** | KPIs del estado + brecha de precio vs. media nacional (argumento de precio justo) |
| **Diagnóstico territorial** | Ranking y tabla de municipios cafetaleros; resalta tus 28 municipios objetivo |
| **Serie histórica y precio** | Evolución 2010–2024 de volumen, precio, valor y superficie |
| **Rendimiento y siniestralidad** | Brecha de rendimiento por municipio (dónde priorizar buenas prácticas) |
| **Benchmarking nacional** | Oaxaca vs. Chiapas, Veracruz, Puebla… en volumen y precio |
| **Datos** | Explorador y descarga de los datos filtrados |

## 5. Tips de uso

- En la barra lateral puedes **pegar la lista de tus 28 municipios objetivo**
  (uno por línea) para que se resalten en naranja en los gráficos.
- El **precio medio rural es nominal** (pesos corrientes). Para comparar poder
  adquisitivo entre años, conviene deflactar con el INPC del INEGI. (Puedo
  añadir esa función si me pasas la serie del INPC.)
- Todos los gráficos son de Plotly: puedes hacer zoom, exportar PNG y pasar el
  cursor para ver valores.

## 6. Ideas de extensión (siguientes iteraciones)

- **Mapa coroplético real** de Oaxaca por municipio (requiere un GeoJSON de
  municipios; puedo integrarlo).
- **Deflactor INPC** para precios reales.
- **Cruce con la encuesta a 500 productores** (Fase 1 del protocolo) para unir
  el diagnóstico secundario (SIAP) con el primario (cuestionario).
- Indicador de **concentración de valor** (¿cuánto del valor nacional capta
  Oaxaca vs. su volumen?).
