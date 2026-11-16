import streamlit as st
import requests
from datetime import datetime
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga M16", page_icon="🛡️", layout="centered")

# --- CSS PARA CONTRASTE AUTOMÁTICO ---
st.markdown("""
    <style>
    .stats-card {
        background-color: var(--secondary-background-color);
        padding: 15px; border-radius: 10px;
        border: 1px solid var(--border-color);
        display: flex; justify-content: space-around;
        margin: 20px 0; color: var(--text-color);
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
            page_id = page["id"]
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            if estado == "Activo": jugadores.append({"nombre": nombre, "id": page_id})
        return sorted(jugadores, key=lambda x: x['nombre'])
    except: return []

jugadores = fetch_jugadores()
if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

# Cabecera
col_img, col_title = st.columns([1, 4])
with col_img:
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", width=80)
    else: st.write("🛡️")
with col_title: st.title("Loga M16")

fecha_entrenamiento = st.date_input("Fecha", datetime.now())
st.subheader("Jugadores Activos")

# Lista
for j in jugadores:
    nombre = j['nombre']
    st.text(nombre) 
    st.session_state.asistencias[nombre] = st.radio(
        nombre, ["Presente", "Ausente", "SAF"],
        index=1 if st.session_state.asistencias.get(nombre) == "Ausente" else (0 if st.session_state.asistencias.get(nombre) == "Presente" else 2),
        key=f"r_{nombre}", label_visibility="collapsed", horizontal=True
    )
    st.write("---")

# Botón de envío real
if st.button("Enviar asistencia", use_container_width=True, type="primary"):
    with st.spinner("Enviando a Notion..."):
        errores = 0
        for j in jugadores:
            nombre = j['nombre']
            estado = st.session_state.asistencias[nombre]
            # Payload para crear registro en Asistencia
            payload = {
                "parent": {"database_id": DB_ASISTENCIA},
                "properties": {
                    "Jugador": {"relation": [{"id": j['id']}]},
                    "Asistencia": {"select": {"name": estado}},
                    "Fecha": {"date": {"start": fecha_entrenamiento.isoformat()}}
                }
            }
            res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
            if res.status_code != 200: errores += 1
        
        if errores == 0: st.success("¡Asistencia enviada a Notion correctamente!")
        else: st.error(f"Hubo errores en {errores} registros.")

# Contador
resumen = list(st.session_state.asistencias.values())
st.markdown(f"""
    <div class="stats-card">
        <div style="text-align: center;"><b>Pres</b><br><div class="stat-val">{resumen.count("Presente")}</div></div>
        <div style="text-align: center;"><b>Aus</b><br><div class="stat-val">{resumen.count("Ausente")}</div></div>
        <div style="text-align: center;"><b>SAF</b><br><div class="stat-val">{resumen.count("SAF")}</div></div>
    </div>
""", unsafe_allow_html=True)
