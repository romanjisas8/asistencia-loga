import streamlit as st
import requests
import pandas as pd
import plotly.express as px

TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Reporte Loga", page_icon="📈", layout="wide")
st.title("📈 Reporte de Gestión")

@st.cache_data(ttl=300)
def cargar_datos():
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    res = requests.post(url, headers=headers, json={}).json()
    data = []
    for row in res.get("results", []):
        p = row["properties"]
        div = p.get("División", {}).get("select", {}).get("name", "S/D")
        data.append({
            "Fecha": p.get("Fecha", {}).get("date", {}).get("start", ""),
            "Asistencia": p.get("Asistencia", {}).get("select", {}).get("name", ""),
            "División": div
        })
    return pd.DataFrame(data)

df = cargar_datos()
if not df.empty:
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    st.subheader("Evolución de Asistencia")
    tendencia = df[df['Asistencia'] == 'Presente'].groupby('Fecha').size().reset_index(name='Cantidad')
    fig = px.line(tendencia, x='Fecha', y='Cantidad', markers=True)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Resumen por División")
    st.table(df.groupby(['División', 'Asistencia']).size().unstack(fill_value=0))
else:
    st.write("No hay datos suficientes para generar el reporte.")
