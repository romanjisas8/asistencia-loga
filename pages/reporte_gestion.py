import streamlit as st
import requests
import pandas as pd
import plotly.express as px

TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Gestión Loga", page_icon="🛡️", layout="wide")

@st.cache_data(ttl=300)
def cargar_asistencias():
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    res = requests.post(url, headers=headers, json={}).json()
    data = []
    for row in res.get("results", []):
        p = row["properties"]
        # Usamos los nombres exactos que detectó el DEBUG
        fecha = p.get("Fecha", {}).get("date", {}).get("start")
        div = (p.get("División", {}).get("select") or {}).get("name", "S/D")
        asistencia = (p.get("Asistencia", {}).get("select") or {}).get("name", "Sin marcar")
        j_rel = p.get("Jugador", {}).get("relation", [])
        j_id = j_rel[0].get("id", "Sin Vinculo") if j_rel else "Sin Vinculo"
        
        if fecha:
            data.append({"Fecha": fecha, "Asistencia": asistencia, "División": div, "JugadorID": j_id})
    return pd.DataFrame(data)

st.title("🛡️ Gestión por División")
df = cargar_asistencias()

if not df.empty:
    divs = sorted([d for d in df['División'].unique() if d != "S/D"])
    div_elegida = st.sidebar.selectbox("Seleccionar División", options=divs)
    df_div = df[df['División'] == div_elegida].copy()
    
    if not df_div.empty:
        df_div['Fecha'] = pd.to_datetime(df_div['Fecha'])
        
        # Métricas
        entrenamientos = df_div['Fecha'].nunique()
        presentes = len(df_div[df_div['Asistencia']=='Presente'])
        total_validos = len(df_div[df_div['Asistencia'].isin(['Presente', 'Ausente', 'SAF'])])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Entrenamientos", entrenamientos)
        c2.metric("Promedio Asistencia", f"{(presentes/total_validos*100):.1f}%" if total_validos > 0 else "0%")
        c3.metric("Jugadores x Entreno", f"{(presentes/entrenamientos):.1f}" if entrenamientos > 0 else "0")

        # Gráfico
        st.subheader("Tendencia")
        tendencia = df_div[df_div['Asistencia'].isin(['Presente', 'SAF'])].groupby(['Fecha', 'Asistencia']).size().unstack(fill_value=0).reset_index()
        fig = px.bar(tendencia, x='Fecha', y=['Presente', 'SAF'], color_discrete_map={'Presente': '#800000', 'SAF': '#1a237e'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No hay datos para esta división.")
