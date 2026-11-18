import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Gestión Loga", page_icon="🛡️", layout="wide")

@st.cache_data(ttl=300)
def cargar_asistencias():
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    all_results = []
    has_more, next_cursor = True, None
    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        res = requests.post(url, headers=headers, json=payload).json()
        all_results.extend(res.get("results", []))
        has_more = res.get("has_more", False)
        next_cursor = res.get("next_cursor")
    
    data = []
    for row in all_results:
        p = row["properties"]
        fecha_raw = p.get("Fecha", {}).get("date", {}).get("start")
        if not fecha_raw: continue
        
        # Procesar división y asistencia
        div = (p.get("División", {}).get("select") or {}).get("name", "S/D")
        if not div: # Fallback para rollup
            arr = p.get("División", {}).get("rollup", {}).get("array", [])
            if arr: div = (arr[0].get("select") or {}).get("name", "S/D")
            
        data.append({
            "Fecha": fecha_raw,
            "Asistencia": (p.get("Asistencia", {}).get("select") or {}).get("name", "Sin marcar"),
            "División": div,
            "JugadorID": p.get("Jugador", {}).get("relation", [{}])[0].get("id", "Sin Vinculo")
        })
    return pd.DataFrame(data)

# --- UI ---
st.title("🛡️ Gestión por División")
df_raw = cargar_asistencias()

if not df_raw.empty:
    divs = sorted(df_raw['División'].unique())
    div_elegida = st.sidebar.selectbox("Seleccionar División", options=divs)
    df_div = df_raw[df_raw['División'] == div_elegida].copy()
    
    if not df_div.empty:
        # Convertir a datetime forzando zona horaria de Argentina
        df_div['Fecha'] = pd.to_datetime(df_div['Fecha']).dt.tz_localize(None)
        
        # --- CONTEO TOTAL ABSOLUTO ---
        entrenamientos = df_div['Fecha'].nunique()
        presentes_totales = len(df_div[df_div['Asistencia']=='Presente'])
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Entrenamientos", entrenamientos) # Debería dar 109
        c2.metric("Promedio Asistencia", f"{(presentes_totales/len(df_div)*100):.1f}%")
        c3.metric("Presentes x Entrenamiento", f"{(presentes_totales / entrenamientos):.1f}" if entrenamientos > 0 else "0")

        # Gráfico Anual (Contando todos los días)
        resumen_diario = df_div.groupby(['Fecha', 'Asistencia']).size().unstack(fill_value=0).reset_index()
        fig = px.bar(resumen_diario, x='Fecha', y=['Presente', 'SAF'], 
                     title=f"Evolución {div_elegida}",
                     color_discrete_map={'Presente': '#800000', 'SAF': '#1a237e'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos.")
