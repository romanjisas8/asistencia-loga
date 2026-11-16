import streamlit as st
import requests
from datetime import datetime
import os

# Configuración de Secretos
TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga", page_icon="🛡️", layout="centered")

query_params = st.query_params
division = query_params.get("div", "No seleccionada")

# Inicializar estados de sesión
if 'confirmar_duplicado' not in st.session_state: st.session_state.confirmar_duplicado = False

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
    try:
        res = requests.post(url, headers=headers, json=payload)
        return len(res.json().get("results", [])) > 0
    except: return False

# Cabecera
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
    else: st.write("🛡️")
with col_title: st.title(f"Loga {division}")

if division == "No seleccionada":
    st.error("Accede a través del link de tu división (ej: ?div=M16)")
    st.stop()

# Fecha formato DD-MM-YYYY
fecha_input = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")

# Aviso automático de registros previos
hay_asistencia = ya_tiene_asistencia(fecha_input, division)
if hay_asistencia:
    st.warning(f"⚠️ ATENCIÓN: Ya se registró asistencia para {division} el día {fecha_input.strftime('%d-%m-%Y')}.")

jugadores = fetch_jugadores(division)
if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

# Lista de jugadores
for j in jugadores:
    st.text(j['nombre'])
    st.session_state.asistencias[j['nombre']] = st.radio(j['nombre'], ["Presente", "Ausente", "SAF"], 
        index=1 if st.session_state.asistencias.get(j['nombre']) == "Ausente" else 0,
        key=f"r_{j['nombre']}", label_visibility="collapsed", horizontal=True)
    st.write("---")

# Tablero Contador Horizontal
resumen = list(st.session_state.asistencias.values())
st.markdown(f"""
    <div style="display: flex; justify-content: space-around; background-color: #262730; padding: 15px; border-radius: 10px; margin: 20px 0; color: white;">
        <div style="text-align: center;"><b>Pres</b><br><span style="font-size: 20px;">{resumen.count("Presente")}</span></div>
        <div style="text-align: center;"><b>Aus</b><br><span style="font-size: 20px;">{resumen.count("Ausente")}</span></div>
        <div style="text-align: center;"><b>SAF</b><br><span style="font-size: 20px;">{resumen.count("SAF")}</span></div>
    </div>
""", unsafe_allow_html=True)

# Lógica de Botón y Confirmación
if not st.session_state.confirmar_duplicado:
    if st.button("Enviar asistencia", use_container_width=True, type="primary"):
        if hay_asistencia:
            st.session_state.confirmar_duplicado = True
            st.rerun()
        else:
            ejecutar_envio = True
            # (Proceder con el envío directo)
else:
    st.error(f"🛑 CUIDADO: Vas a duplicar la asistencia de {division} para esta fecha.")
    col1, col2 = st.columns(2)
    if col1.button("SÍ, ENVIAR DE TODAS FORMAS", use_container_width=True):
        ejecutar_envio = True
        st.session_state.confirmar_duplicado = False
    if col2.button("CANCELAR", use_container_width=True):
        st.session_state.confirmar_duplicado = False
        st.rerun()

# Proceso de guardado en Notion
if 'ejecutar_envio' in locals() and ejecutar_envio:
    errores = []
    with st.spinner("Guardando en Notion..."):
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
            if requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload).status_code != 200:
                errores.append(j['nombre'])
    
    if not errores:
        st.success("¡Asistencia enviada con éxito!")
    else:
        st.error(f"Hubo errores en {len(errores)} jugadores.")
