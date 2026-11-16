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
division = query_params.get("div", "No seleccionada")

@st.cache_data(ttl=60)
def fetch_jugadores(div):
    if div == "No seleccionada": return []
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        payload = {"filter": {"and": [{"property": "División", "select": {"equals": div}}, {"property": "Estado", "select": {"equals": "Activo"}}]}}
        response = requests.post(url, headers=headers, json=payload)
        return [{"nombre": next((v.get("title", [{}])[0].get("plain_text") for k, v in p["properties"].items() if v["type"] == "title"), "Sin nombre"), "id": p["id"]} for p in response.json().get("results", [])]
    except: return []

def ya_tiene_asistencia(fecha, div):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    payload = {"filter": {"and": [{"property": "Fecha", "date": {"equals": fecha.strftime("%Y-%m-%d")}}, {"property": "División", "select": {"equals": div}}]}}
    return len(requests.post(url, headers=headers, json=payload).json().get("results", [])) > 0

jugadores = fetch_jugadores(division)
if 'asistencias' not in st.session_state: st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}
if 'confirmacion' not in st.session_state: st.session_state.confirmacion = False

# UI
col_img, col_title = st.columns([1, 4])
with col_img: 
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", width=80)
with col_title: st.title(f"Loga {division}")

fecha = st.date_input("Fecha", datetime.now())
for j in jugadores:
    st.text(j['nombre'])
    st.session_state.asistencias[j['nombre']] = st.radio(j['nombre'], ["Presente", "Ausente", "SAF"], index=1 if st.session_state.asistencias.get(j['nombre']) == "Ausente" else 0, key=f"r_{j['nombre']}", label_visibility="collapsed", horizontal=True)
    st.write("---")

# Lógica de envío con confirmación
if st.button("Enviar asistencia", use_container_width=True, type="primary"):
    if ya_tiene_asistencia(fecha, division):
        st.warning("⚠️ Ya existe asistencia registrada para hoy. Presiona nuevamente 'Confirmar envío' si deseas duplicar.")
        st.session_state.confirmacion = True
    else:
        st.session_state.confirmacion = True

if st.session_state.confirmacion:
    if st.button("Confirmar envío", use_container_width=True, type="primary"):
        errores = []
        for j in jugadores:
            payload = {"parent": {"database_id": DB_ASISTENCIA}, "properties": {"Jugador": {"relation": [{"id": j['id']}]}, "Asistencia": {"select": {"name": st.session_state.asistencias[j['nombre']]}}, "Fecha": {"date": {"start": fecha.strftime("%Y-%m-%d")}}, "División": {"select": {"name": division}}}}
            if requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload).status_code != 200: errores.append(j['nombre'])
        
        if not errores: 
            st.success("¡Datos enviados!")
            st.session_state.confirmacion = False
        else: st.error("Errores en: " + ", ".join(errores))
