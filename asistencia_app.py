import streamlit as st
import requests
from datetime import datetime
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga", page_icon="🛡️", layout="centered")

@st.cache_data(ttl=60)
def fetch_jugadores(div):
    if div == "No seleccionada": return []
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        response = requests.post(url, headers=headers, json={})
        jugadores = []
        for page in response.json().get("results", []):
            props = page["properties"]
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            div_notion = props.get("División", {}).get("select", {}).get("name", "")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            if estado == "Activo" and div_notion and div_notion.upper() == div.upper():
                jugadores.append({"nombre": nombre, "id": page["id"]})
        return sorted(jugadores, key=lambda x: x['nombre'])
    except: return []

query_params = st.query_params
division_seleccionada = query_params.get("div", "No seleccionada")

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

resumen = list(st.session_state.asistencias.values())
st.markdown(f"""
    <div style="display: flex; justify-content: space-around; background-color: #262730; padding: 15px; border-radius: 10px; margin: 20px 0;">
        <div style="text-align: center;"><b>Pres</b><br><span style="font-size: 20px;">{resumen.count("Presente")}</span></div>
        <div style="text-align: center;"><b>Aus</b><br><span style="font-size: 20px;">{resumen.count("Ausente")}</span></div>
        <div style="text-align: center;"><b>SAF</b><br><span style="font-size: 20px;">{resumen.count("SAF")}</span></div>
    </div>
""", unsafe_allow_html=True)

if st.button("Enviar asistencia", use_container_width=True, type="primary"):
    errores = []
    for j in jugadores:
        nombre = j['nombre']
        estado = st.session_state.asistencias[nombre]
        payload = {
            "parent": {"database_id": DB_ASISTENCIA},
            "properties": {
                "Jugador": {"relation": [{"id": j['id']}]},
                "Asistencia": {"select": {"name": estado}},
                "Fecha": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
            }
        }
        res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        if res.status_code != 200: errores.append(nombre)
    if not errores: st.success("¡Datos enviados!")
    else: st.error("Errores en: " + ", ".join(errores))
