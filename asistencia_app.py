import streamlit as st
import requests
from datetime import datetime
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# Configuración de página
st.set_page_config(page_title="Asistencia Loga M16", page_icon="🛡️", layout="centered")

@st.cache_data(ttl=60)
def fetch_jugadores():
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        response = requests.post(url, headers=headers, json={})
        jugadores = []
        for page in response.json().get("results", []):
            props = page["properties"]
            page_id = page["id"]
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            if estado == "Activo": jugadores.append({"nombre": nombre, "id": page_id})
        return sorted(jugadores, key=lambda x: x['nombre'])
    except: return []

jugadores = fetch_jugadores()
if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

# Cabecera con Logo
col_img, col_title = st.columns([1, 4])
with col_img:
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", width=80)
    else: st.write("🛡️")
with col_title: st.title("Loga M16")

st.date_input("Fecha", datetime.now())
st.subheader("Jugadores Activos")

# Lista de jugadores
for j in jugadores:
    nombre = j['nombre']
    st.text(nombre) 
    st.session_state.asistencias[nombre] = st.radio(
        nombre, ["Presente", "Ausente", "SAF"],
        index=1 if st.session_state.asistencias.get(nombre) == "Ausente" else (0 if st.session_state.asistencias.get(nombre) == "Presente" else 2),
        key=f"r_{nombre}", label_visibility="collapsed", horizontal=True
    )
    st.write("---")

st.divider()

# Contador debajo de la lista
resumen = list(st.session_state.asistencias.values())
st.markdown(f"""
    <div style="display: flex; justify-content: space-around; background-color: #262730; padding: 15px; border-radius: 10px; margin: 20px 0;">
        <div style="text-align: center;"><b>Pres</b><br><span style="font-size: 20px;">{resumen.count("Presente")}</span></div>
        <div style="text-align: center;"><b>Aus</b><br><span style="font-size: 20px;">{resumen.count("Ausente")}</span></div>
        <div style="text-align: center;"><b>SAF</b><br><span style="font-size: 20px;">{resumen.count("SAF")}</span></div>
    </div>
""", unsafe_allow_html=True)

if st.button("Enviar asistencia", use_container_width=True, type="primary"):
    st.success("¡Datos enviados!")
