import streamlit as st
import requests
import pandas as pd

TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.title("🛡️ Diagnóstico de Datos")

@st.cache_data(ttl=300)
def diagnosticar_datos():
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    res = requests.post(url, headers=headers, json={}).json()
    
    debug_data = []
    for row in res.get("results", []):
        props = row["properties"]
        # Buscamos qué tiene la columna "División"
        p_div = props.get("División", {})
        debug_data.append({
            "Tipo_Columna": p_div.get("type"),
            "Contenido_Bruto": str(p_div)
        })
    return pd.DataFrame(debug_data)

df_debug = diagnosticar_datos()
if not df_debug.empty:
    st.write("Datos encontrados en Notion (Primeros 10):")
    st.dataframe(df_debug.head(10))
else:
    st.error("No se encontró ningún registro en la base de datos de Asistencia. ¿Estás seguro que el DB_ASISTENCIA es el correcto?")
