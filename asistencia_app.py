import streamlit as st
import requests
from datetime import datetime
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Club", page_icon="🛡️", layout="centered")

# Leer la división desde la URL (ej: tu-app.streamlit.app/?div=M16)
query_params = st.query_params
division_seleccionada = query_params.get("div", "No seleccionada")

@st.cache_data(ttl=60)
def fetch_jugadores(div):
    if div == "No seleccionada": return []
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        # Filtramos directamente desde Notion por la propiedad "División"
        payload = {
            "filter": {
                "and": [
                    {"property": "División", "select": {"equals": div}},
                    {"property": "Estado", "select": {"equals": "Activo"}}
                ]
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        jugadores = []
        for page in response.json().get("results", []):
            props = page["properties"]
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            jugadores.append({"nombre": nombre, "id": page["id"]})
        return sorted(jugadores, key=lambda x: x['nombre'])
    except: return []

# Interfaz
col_img, col_title = st.columns([1, 4])
with col_img:
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", width=80)
    else: st.write("🛡️")
with col_title: st.title(f"Loga {division_seleccionada}")

if division_seleccionada == "No seleccionada":
    st.error("Por favor, accede a través del link de tu división (ej: ?div=M16)")
    st.stop()

jugadores = fetch_jugadores(division_seleccionada)
if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

st.subheader(f"Jugadores Activos - {division_seleccionada}")
for j in jugadores:
    nombre = j['nombre']
    st.text(nombre)
    st.session_state.asistencias[nombre] = st.radio(nombre, ["Presente", "Ausente", "SAF"], index=1, key=f"r_{nombre}", label_visibility="collapsed", horizontal=True)
    st.write("---")

if st.button("Enviar asistencia", use_container_width=True, type="primary"):
    # Lógica de envío (igual que antes)
    ...
