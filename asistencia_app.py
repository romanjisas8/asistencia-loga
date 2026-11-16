import streamlit as st
import requests
from datetime import datetime
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga", page_icon="🛡️", layout="centered")

query_params = st.query_params
division_seleccionada = query_params.get("div", "No seleccionada")

@st.cache_data(ttl=60)
def fetch_jugadores(div):
    if div == "No seleccionada": return []
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        # Filtro intentando coincidir con "División" y "Estado"
        payload = {
            "filter": {
                "and": [
                    {"property": "División", "select": {"equals": div}},
                    {"property": "Estado", "select": {"equals": "Activo"}}
                ]
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        
        # DEBUG: Si falla o está vacío, listamos lo que hay realmente en Notion
        if response.status_code != 200 or len(response.json().get("results", [])) == 0:
             all_res = requests.post(url, headers=headers, json={})
             # Recolectar divisiones existentes para debug
             divs = set()
             for p in all_res.json().get("results", []):
                 d = p["properties"].get("División", {}).get("select", {}).get("name")
                 if d: divs.add(d)
             return [f"Debug: No hallé jugadores para '{div}'. En Notion existen: {list(divs)}"]
        
        jugadores = []
        for page in response.json().get("results", []):
            props = page["properties"]
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            jugadores.append({"nombre": nombre, "id": page["id"]})
        return sorted(jugadores, key=lambda x: x['nombre'])
    except Exception as e: return [f"Error técnico: {str(e)}"]

# Cabecera
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

# Mostrar error de debug si existe
if len(jugadores) > 0 and isinstance(jugadores[0], str) and "Debug" in jugadores[0]:
    st.warning(jugadores[0])
    st.stop()

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
        if res.status_code != 200: errores.append(f"{nombre}: {res.json().get('message', 'Error')}")
    if not errores: st.success("¡Datos enviados!")
    else: st.error("Errores: " + ", ".join(errores))
