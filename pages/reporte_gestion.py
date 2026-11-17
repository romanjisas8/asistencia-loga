import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuración de secretos (Usa los mismos que la App de asistencia)
TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Reporte de Gestión - Loga", page_icon="📈", layout="wide")

st.title("📈 Reporte de Gestión Deportiva")

# --- FUNCIÓN PARA TRAER TODOS LOS DATOS ---
@st.cache_data(ttl=300)
def cargar_todo_el_historial():
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    all_results = []
    has_more = True
    next_cursor = None
    
    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        res = requests.post(url, headers=headers, json=payload).json()
        all_results.extend(res.get("results", []))
        has_more = res.get("has_more", False)
        next_cursor = res.get("next_cursor")
    
    data = []
    for row in all_results:
        p = row["properties"]
        # Extraer División
        div = ""
        p_div = p.get("División", {})
        if p_div.get("type") == "select": div = p_div.get("select", {}).get("name", "S/D")
        elif p_div.get("type") == "rollup":
            arr = p_div.get("rollup", {}).get("array", [])
            if arr: div = arr[0].get("select", {}).get("name", "S/D")
            
        data.append({
            "Fecha": p.get("Fecha", {}).get("date", {}).get("start", ""),
            "Asistencia": p.get("Asistencia", {}).get("select", {}).get("name", ""),
            "División": div
        })
    return pd.DataFrame(data)

# --- PROCESAMIENTO ---
df = cargar_todo_el_historial()
df['Fecha'] = pd.to_datetime(df['Fecha'])

# Sidebar para filtros
st.sidebar.header("Filtros")
div_filtro = st.sidebar.multiselect("Seleccionar Divisiones", options=df['División'].unique(), default=df['División'].unique())

df_filtrado = df[df['División'].isin(div_filtro)]

# --- MÉTRICAS GENERALES ---
col1, col2, col3 = st.columns(3)
total_presentes = len(df_filtrado[df_filtrado['Asistencia'] == 'Presente'])
promedio = (total_presentes / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0

col1.metric("Total Registros", len(df_filtrado))
col2.metric("Total Presentes", total_presentes)
col3.metric("% Asistencia Promedio", f"{promedio:.1f}%")

st.divider()

# --- GRÁFICO DE TENDENCIA ---
st.subheader("Evolución de Asistencia por Día")
# Agrupamos por fecha para ver cuántos presentes hubo cada día
tendencia = df_filtrado[df_filtrado['Asistencia'] == 'Presente'].groupby('Fecha').size().reset_index(name='Cantidad')
fig = px.line(tendencia, x='Fecha', y='Cantidad', title="Chicos presentes por entrenamiento", markers=True)
st.plotly_chart(fig, use_container_width=True)

# --- TABLA DE RESUMEN POR DIVISIÓN ---
st.subheader("Resumen por Categoría")
resumen_div = df_filtrado.groupby(['División', 'Asistencia']).size().unstack(fill_value=0)
st.dataframe(resumen_div, use_container_width=True)

st.info("💡 Este reporte se actualiza cada 5 minutos con los datos de Notion.")
