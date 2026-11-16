import streamlit as st
import requests
from datetime import datetime
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga M16", page_icon="🛡️", layout="centered")

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

# Cabecera
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

# CONTADOR FORZADO HORIZONTAL (Sin CSS externo, solo estilos inline)
resumen = list(st.session_state.asistencias.values())
st.markdown(f"""
    <div style="display: table; width: 100%; table-layout: fixed; background: #262730; color: white; border-radius: 10px; margin: 20px 0;">
        <div style="display: table-row;">
            <div style="display: table-cell; padding: 15px; text-align: center;">Pres<br><span style="font-size:20px;">{resumen.count("Presente")}</span></div>
            <div style="display: table-cell; padding: 15px; text-align: center;">Aus<br><span style="font-size:20px;">{resumen.count("Ausente")}</span></div>
            <div style="display: table-cell; padding: 15px; text-align: center;">SAF<br><span style="font-size:20px;">{resumen.count("SAF")}</span></div>
        </div>
    </div>
""", unsafe_allow_html=True)

if st.button("Enviar asistencia", use_container_width=True, type="primary"):
    errores = []
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
        if res.status_code != 200: errores.append(nombre)
    if not errores: st.success("¡Datos enviados!")
    else: st.error("Errores en: " + ", ".join(errores))
