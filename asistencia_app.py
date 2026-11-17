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

# --- MOTOR DE VERIFICACIÓN ROBUSTO (Detecta Rollups, Fórmulas y Selects) ---
def verificar_bloqueo_total(fecha_sel, div_sel):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    fecha_str = fecha_sel.strftime("%Y-%m-%d")
    
    # Filtramos SOLO por fecha en Notion (es lo más confiable)
    payload = {
        "filter": {
            "property": "Fecha",
            "date": {"equals": fecha_str}
        }
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        resultados = res.json().get("results", [])
        
        for row in resultados:
            props = row["properties"]
            # Buscamos la columna "División" e intentamos leer su valor sea cual sea su tipo
            p_div = props.get("División", {})
            tipo = p_div.get("type", "")
            val_final = ""
            
            if tipo == "select": 
                val_final = p_div.get("select", {}).get("name", "")
            elif tipo == "formula": 
                val_final = p_div.get("formula", {}).get("string", "")
            elif tipo == "rollup":
                # Si es un rollup, suele venir como un array de valores
                array = p_div.get("rollup", {}).get("array", [])
                if array:
                    # Probamos si el primer elemento es select o formula
                    primer = array[0]
                    t_p = primer.get("type", "")
                    if t_p == "select": val_final = primer.get("select", {}).get("name", "")
                    elif t_p == "formula": val_final = primer.get("formula", {}).get("string", "")
            
            # Si encontramos coincidencia de división, BLOQUEAMOS
            if val_final.upper() == div_sel.upper():
                return True
        return False
    except:
        return False

@st.cache_data(ttl=60)
def fetch_jugadores(div):
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        res = requests.post(url, headers=headers, json={})
        jugadores = []
        for p in res.json().get("results", []):
            props = p["properties"]
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            d_notion = props.get("División", {}).get("select", {}).get("name", "")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            if estado == "Activo" and d_notion.upper() == div.upper():
                jugadores.append({"nombre": nombre, "id": p["id"]})
        return sorted(jugadores, key=lambda x: x['nombre'])
    except: return []

# --- INTERFAZ ---
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
with col_title: st.title(f"Loga {division}")

fecha_input = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")

# VERIFICACIÓN DE SEGURIDAD
esta_bloqueado = verificar_bloqueo_total(fecha_input, division)

if esta_bloqueado:
    st.error(f"🛑 BLOQUEO DE SEGURIDAD: Ya existen registros para {division} el {fecha_input.strftime('%d/%m/%Y')}.")
    st.info("No se permite el envío para evitar duplicados en Notion.")
else:
    st.success("✅ Día disponible para cargar asistencia.")

st.divider()

jugadores = fetch_jugadores(division)
if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

for j in jugadores:
    n = j['nombre']
    st.text(n)
    st.session_state.asistencias[n] = st.radio(n, ["Presente", "Ausente", "SAF"], 
        index=1 if st.session_state.asistencias.get(n) == "Ausente" else 0,
        key=f"r_{n}_{fecha_input}", label_visibility="collapsed", horizontal=True)
    st.write("---")

resumen = list(st.session_state.asistencias.values())
st.markdown(f"""<div style="display:flex; justify-content:space-around; background:#262730; padding:15px; border-radius:10px; color:white; margin-bottom:20px;">
    <div>P: {resumen.count("Presente")}</div><div>A: {resumen.count("Ausente")}</div><div>S: {resumen.count("SAF")}</div></div>""", unsafe_allow_html=True)

# --- BOTÓN CON SEGURO ---
if esta_bloqueado:
    st.button("ENVÍO DESACTIVADO (YA EXISTEN DATOS)", use_container_width=True, disabled=True)
else:
    if st.button("Enviar asistencia", use_container_width=True, type="primary"):
        with st.spinner("Guardando en Notion..."):
            for j in jugadores:
                payload = {
                    "parent": {"database_id": DB_ASISTENCIA},
                    "properties": {
                        "Jugador": {"relation": [{"id": j['id']}]},
                        "Asistencia": {"select": {"name": st.session_state.asistencias[j['nombre']]}},
                        "Fecha": {"date": {"start": fecha_input.strftime("%Y-%m-%d")}},
                        "División": {"select": {"name": division}} # Ojo: asegúrate que esto sea un Select o elimínalo si es Rollup automático
                    }
                }
                requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        st.success("¡Datos guardados correctamente!"); st.balloons()
