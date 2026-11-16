import streamlit as st
import requests
from datetime import datetime
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Loga M16", page_icon="🛡️", layout="centered")

# --- CONTADOR ---
if 'asistencias' not in st.session_state: st.session_state.asistencias = {}
resumen = list(st.session_state.asistencias.values())
c1, c2, c3 = st.columns(3)
c1.metric("Pres", resumen.count("Presente"))
c2.metric("Aus", resumen.count("Ausente"))
c3.metric("SAF", resumen.count("SAF"))
st.divider()

# Cabecera y Lista
col_img, col_title = st.columns([1, 4])
with col_img: 
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", width=80)
with col_title: st.title("Loga M16")

jugadores = # ... (aquí cargamos los jugadores como antes) ...

# ... (bucle de radio buttons) ...

# BOTÓN DE ENVÍO
if st.button("Enviar asistencia", type="primary"):
    for j in jugadores:
        nombre = j['nombre']
        payload = {
            "parent": {"database_id": DB_ASISTENCIA},
            "properties": {
                "Jugador": {"relation": [{"id": j['id']}]},
                "Asistencia": {"select": {"name": st.session_state.asistencias[nombre]}},
                "Fecha": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
            }
        }
        res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        if res.status_code != 200:
            st.error(f"Error en {nombre}: {res.json()['message']}")
