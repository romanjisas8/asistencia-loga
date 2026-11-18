import streamlit as st
import requests
import pandas as pd
import plotly.express as px

TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Gestión Loga", layout="wide")

@st.cache_data(ttl=300)
def cargar_asistencias():
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    try:
        res = requests.post(url, headers=headers, json={}).json()
        data = []
        # DEBUG: Imprimir los nombres de columnas encontrados
        if res.get("results"):
            cols = res["results"][0]["properties"].keys()
            st.sidebar.write("Columnas detectadas en Notion:", list(cols))
        
        for row in res.get("results", []):
            p = row["properties"]
            # Intentamos encontrar la columna de división dinámicamente
            div = "S/D"
            for nombre_col in ["División", "Division", "división"]:
                if nombre_col in p:
                    col = p[nombre_col]
                    if col.get("type") == "select": div = (col.get("select") or {}).get("name", "S/D")
                    elif col.get("type") == "rollup":
                        arr = col.get("rollup", {}).get("array", [])
                        if arr: div = (arr[0].get("select") or {}).get("name", "S/D")
            
            asistencia = (p.get("Asistencia", {}).get("select") or {}).get("name", "Sin marcar")
            fecha = p.get("Fecha", {}).get("date", {}).get("start")
            
            if fecha:
                data.append({"Fecha": fecha, "Asistencia": asistencia, "División": div})
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error cargando: {e}")
        return pd.DataFrame()

df = cargar_asistencias()
if not df.empty:
    divs = sorted([d for d in df['División'].unique() if d != "S/D"])
    div_elegida = st.sidebar.selectbox("Seleccionar División", options=divs)
    df_div = df[df['División'] == div_elegida].copy()
    # ... (resto de tu lógica de métricas y gráficos)
