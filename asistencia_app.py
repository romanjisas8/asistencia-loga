import streamlit as st
import requests
from datetime import datetime
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga M16", page_icon="🛡️", layout="centered")

# CSS para que el tablero sea legible en CUALQUIER modo
st.markdown("""
    <style>
    .stats-card {
        background-color: var(--secondary-background-color);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid var(--border-color);
        display: flex;
        justify-content: space-around;
        margin: 20px 0;
        color: var(--text-color);
    }
    .stat-val { font-size: 20px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def fetch_jugadores():
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        response = requests.post(url, headers=headers, json={})
        jugadores = []
        for page in response.json().get("results", []):
            props = page["properties"]
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            if estado == "Activo": jugadores.append({"nombre": nombre, "id": page["id"]})
        return sorted(jugadores, key=lambda x: x['nombre'])
    except: return []

jugadores = fetch_jugadores()
if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

col_img, col_title = st.columns([1, 4])
with col_img:
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", width=80)
    else: st.write("🛡️")
with col_title: st.title("Loga M16")

st.date_input("Fecha", datetime.now())
st.subheader("Jugadores Activos")

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

# Contador Dinámico con variables de tema de Streamlit
resumen = list(st.session_state.asistencias.values())
st.markdown(f"""
    <div class="stats-card">
        <div style="text-align: center;"><b>Pres</b><br><div class="stat-val">{resumen.count("Presente")}</div></div>
        <div style="text-align: center;"><b>Aus</b><br><div class="stat-val">{resumen.count("Ausente")}</div></div>
        <div style="text-align: center;"><b>SAF</b><br><div class="stat-val">{resumen.count("SAF")}</div></div>
    </div>
""", unsafe_allow_html=True)

if st.button("Enviar asistencia", use_container_width=True, type="primary"):
    st.success("¡Datos enviados!")
