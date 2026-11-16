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

# --- FUNCIÓN DE VERIFICACIÓN (SIN CACHE) ---
def verificar_registro_previo(fecha, div):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    payload = {
        "filter": {
            "and": [
                {"property": "Fecha", "date": {"equals": fecha.strftime("%Y-%m-%d")}},
                {"property": "División", "select": {"equals": div}}
            ]
        }
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        # Retornamos True si hay al menos un resultado
        return len(res.json().get("results", [])) > 0
    except:
        return False

@st.cache_data(ttl=60)
def fetch_jugadores(div):
    if div == "No seleccionada": return []
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        payload = {"filter": {"and": [{"property": "División", "select": {"equals": div}}, {"property": "Estado", "select": {"equals": "Activo"}}]}}
        response = requests.post(url, headers=headers, json=payload)
        return [{"nombre": next((v.get("title", [{}])[0].get("plain_text") for k, v in p["properties"].items() if v["type"] == "title"), "Sin nombre"), "id": p["id"]} for p in response.json().get("results", [])]
    except: return []

# --- INTERFAZ ---
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.path.exists('.') and os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
    else: st.write("🛡️")
with col_title: st.title(f"Loga {division}")

if division == "No seleccionada":
    st.error("Accede con ?div=M16 (ejemplo)")
    st.stop()

# Selector de fecha (DD/MM/YYYY)
fecha_input = st.date_input("Seleccionar Fecha", datetime.now(), format="DD/MM/YYYY")

# VERIFICACIÓN EN TIEMPO REAL
hay_datos = verificar_registro_previo(fecha_input, division)

jugadores = fetch_jugadores(division)
if not jugadores:
    st.info("Buscando jugadores activos...")
    st.stop()

if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

# Lista de jugadores
for j in jugadores:
    nombre = j['nombre']
    st.text(nombre)
    st.session_state.asistencias[nombre] = st.radio(
        nombre, ["Presente", "Ausente", "SAF"], 
        index=0 if st.session_state.asistencias.get(nombre) == "Presente" else (1 if st.session_state.asistencias.get(nombre) == "Ausente" else 2),
        key=f"r_{nombre}_{fecha_input}", 
        label_visibility="collapsed", horizontal=True
    )
    st.write("---")

# --- BLOQUE DE AVISO Y CONTADOR ---
if hay_datos:
    st.warning(f"⚠️ ATENCIÓN: Ya se registró asistencia para {division} el {fecha_input.strftime('%d/%m/%Y')}. Si envías ahora, se duplicarán los datos.")

resumen = list(st.session_state.asistencias.values())
st.markdown(f"""
    <div style="display: flex; justify-content: space-around; background-color: #262730; padding: 15px; border-radius: 10px; margin: 20px 0; color: white;">
        <div style="text-align: center;"><b>Pres</b><br>{resumen.count("Presente")}</div>
        <div style="text-align: center;"><b>Aus</b><br>{resumen.count("Ausente")}</div>
        <div style="text-align: center;"><b>SAF</b><br>{resumen.count("SAF")}</div>
    </div>
""", unsafe_allow_html=True)

# Botón Envío
if st.button("Enviar asistencia", use_container_width=True, type="primary"):
    with st.spinner("Enviando registros a Notion..."):
        errores = []
        for j in jugadores:
            payload = {
                "parent": {"database_id": DB_ASISTENCIA},
                "properties": {
                    "Jugador": {"relation": [{"id": j['id']}]},
                    "Asistencia": {"select": {"name": st.session_state.asistencias[j['nombre']]}},
                    "Fecha": {"date": {"start": fecha_input.strftime("%Y-%m-%d")}},
                    "División": {"select": {"name": division}}
                }
            }
            res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
            if res.status_code != 200:
                errores.append(j['nombre'])
        
        if not errores:
            st.success(f"¡Asistencia de {division} enviada con éxito!")
        else:
            st.error(f"Error en {len(errores)} registros. Revisa la conexión.")
