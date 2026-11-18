import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Gestión Loga", page_icon="🛡️", layout="wide")

# === 1. Cargar solo jugadores ACTIVOS ===
@st.cache_data(ttl=300)
def cargar_jugadores_activos():
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        res = requests.post(url, headers=headers, json={}).json()
        activos = {}
        for p in res.get("results", []):
            props = p["properties"]
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            if estado == "Activo":
                nombre = next(
                    (v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"),
                    "S/N"
                )
                activos[p["id"]] = nombre
        return activos
    except:
        return {}

# === 2. Cargar asistencias SOLO de jugadores activos ===
@st.cache_data(ttl=300)
def cargar_asistencias_activos(jugadores_activos):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    all_results = []
    has_more, next_cursor = True, None
    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        try:
            res = requests.post(url, headers=headers, json=payload).json()
            all_results.extend(res.get("results", []))
            has_more = res.get("has_more", False)
            next_cursor = res.get("next_cursor")
        except:
            has_more = False

    data = []
    for row in all_results:
        p = row["properties"]

        j_rel = p.get("Jugador", {}).get("relation", [])
        if not j_rel: continue
        j_id = j_rel[0].get("id")
        if j_id not in jugadores_activos: continue

        fecha_raw = p.get("Fecha", {}).get("date", {}).get("start")
        if not fecha_raw: continue

        div = "S/D"
        p_div = p.get("División", {})
        if p_div.get("type") == "select":
            div = (p_div.get("select") or {}).get("name", "S/D")
        elif p_div.get("type") == "rollup":
            arr = p_div.get("rollup", {}).get("array", [])
            if arr:
                for item in arr:
                    nombre_div = item.get("select", {}).get("name")
                    if nombre_div:
                        div = nombre_div
                        break

        asistencia = (p.get("Asistencia", {}).get("select") or {}).get("name", "Sin marcar")

        data.append({
            "Fecha": fecha_raw,
            "Asistencia": asistencia,
            "División": div,
            "Jugador": jugadores_activos[j_id],
            "JugadorID": j_id
        })
    return pd.DataFrame(data)

# === 3. UI Principal ===
st.title("🛡️ Gestión por División")

jugadores_activos = cargar_jugadores_activos()
df_raw = cargar_asistencias_activos(jugadores_activos)

if not df_raw.empty:
    divs = sorted(df_raw['División'].unique())
    div_elegida = st.sidebar.selectbox("Seleccionar División", options=divs)
    df_div = df_raw[df_raw['División'] == div_elegida].copy()

    if not df_div.empty:
        df_div['Fecha'] = pd.to_datetime(df_div['Fecha'], errors='coerce')
        df_div = df_div.dropna(subset=['Fecha']).sort_values('Fecha')
        df_div['Jugador'] = df_div['Jugador'].fillna("Desconocido")

        # --- Conteo ABSOLUTO de entrenamientos ---
        entrenamientos = df_div['Fecha'].nunique()
        fechas_ordenadas = sorted(df_div['Fecha'].unique())
        mapa_nros = {f: i + 1 for i, f in enumerate(fechas_ordenadas)}

        # === FÓRMULA EXACTA DE NOTION (SAF CUENTA COMO PRESENTE) ===
        df_valid = df_div[df_div['Asistencia'].isin(['Presente', 'Ausente', 'SAF'])]
        stats_jugador = df_valid.groupby(['Jugador', 'Asistencia']).size().unstack(fill_value=0).reset_index()
        
        for col in ['Presente', 'Ausente', 'SAF']:
            if col not in stats_jugador.columns:
                stats_jugador[col] = 0
        
        # Denominador = solo los registros del jugador
        stats_jugador['Total_Registros'] = stats_jugador['Presente'] + stats_jugador['Ausente'] + stats_jugador['SAF']
        # Numerador = Presente + SAF (SAF cuenta como presente)
        stats_jugador['Efectivos'] = stats_jugador['Presente'] + stats_jugador['SAF']
        # % exacto
        stats_jugador['% Asistencia'] = stats_jugador.apply(
            lambda x: round((x['Efectivos'] / x['Total_Registros'] * 100), 1) if x['Total_Registros'] > 0 else 0, axis=1
        )

        # --- Métricas Generales ---
        presentes_totales = int(stats_jugador['Efectivos'].sum())  # SAF incluido
        total_validos = int(stats_jugador['Total_Registros'].sum())

        col_metrics, col_pie = st.columns([2, 1])
        with col_metrics:
            st.subheader(f"Resumen General: {div_elegida}")
            m1, m2 = st.columns(2)
            m1.metric("Total Entrenamientos", entrenamientos)
            m1.metric("Jugadores en Base", df_div['JugadorID'].nunique())
            m2.metric("Asistencia Global (%)", f"{(presentes_totales / total_validos * 100):.1f}%" if total_validos > 0 else "0%")
            m2.metric("Promedio Presentes/Día", f"{(presentes_totales / entrenamientos):.1f}" if entrenamientos > 0 else "0")

        with col_pie:
            pie_data = df_valid['Asistencia'].value_counts().reset_index()
            pie_data.columns = ['Estado', 'Cantidad']
            fig_pie = px.pie(
                pie_data, values='Cantidad', names='Estado', hole=0.5,
                color='Estado',
                color_discrete_map={'Presente': '#800000', 'Ausente': '#1a237e', 'SAF': '#FFFFFF'}
            )
            fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()

        # === GRÁFICO: % ASISTENCIA POR JUGADOR ===
        st.subheader("Porcentaje de Asistencia por Jugador")
        stats_ordenado = stats_jugador.sort_values('% Asistencia', ascending=False)
        fig_pct = px.bar(
            stats_ordenado, x='Jugador', y='% Asistencia', text_auto='.1f',
            color_discrete_sequence=['#2ecc71']
        )
        fig_pct.update_traces(texttemplate='%{y:.1f}%', textposition='outside')
        fig_pct.update_layout(yaxis_title="% Asistencia", xaxis_title="Jugador", margin=dict(t=20))
        st.plotly_chart(fig_pct, use_container_width=True)

        st.divider()

        # === GRÁFICO: AUSENTES ÚLTIMO MES ===
        st.subheader("Ausencias en el Último Mes")
        fecha_hace_un_mes = datetime.now() - timedelta(days=30)
        df_ultimo_mes = df_valid[df_valid['Fecha'] >= fecha_hace_un_mes]
        
        ausentes_mes = df_ultimo_mes[df_ultimo_mes['Asistencia'] == 'Ausente'].groupby('Jugador').size().reset_index(name='Ausencias')
        if not ausentes_mes.empty:
            ausentes_mes = ausentes_mes.sort_values('Ausencias', ascending=True)
            fig_aus = px.bar(
                ausentes_mes, x='Ausencias', y='Jugador', orientation='h', text='Ausencias',
                color_discrete_sequence=['#3498db']
            )
            fig_aus.update_traces(textposition='outside')
            fig_aus.update_layout(xaxis_title="Cantidad de Ausencias", yaxis_title="", margin=dict(t=20))
            st.plotly_chart(fig_aus, use_container_width=True)
        else:
            st.success("¡Excelente! No hay ausencias registradas en los últimos 30 días.")

        st.divider()

        # === GRÁFICO: EVOLUCIÓN ANUAL (SAF abajo) ===
        st.subheader("Evolución de Entrenamientos")
        actividad_df = df_div[df_div['Asistencia'].isin(['Presente', 'SAF'])]
        presents_saf_df = actividad_df.groupby(['Fecha', 'Asistencia']).size().reset_index(name='Cantidad')
        presents_saf_df['Nro'] = presents_saf_df['Fecha'].map(mapa_nros)
        presents_saf_df['Fecha_Str'] = presents_saf_df['Fecha'].dt.strftime('%d/%m/%Y')

        fig_anual = px.bar(
            presents_saf_df, x='Nro', y='Cantidad', color='Asistencia',
            labels={'Nro': 'Entrenamiento', 'Cantidad': 'Jugadores'},
            color_discrete_map={'Presente': '#800000', 'SAF': '#1a237e'},
            category_orders={"Asistencia": ["SAF", "Presente"]},
            hover_data={'Fecha_Str': True, 'Nro': False}
        )
        fig_anual.update_layout(barmode='stack', hovermode="x unified")
        st.plotly_chart(fig_anual, use_container_width=True)

        st.divider()

        # === RANKING DETALLADO ===
        st.subheader("Ranking de Compromiso")
        ranking = stats_jugador[['Jugador', 'Presente', 'SAF', 'Ausente', 'Total_Registros', '% Asistencia']].copy()
        ranking = ranking.sort_values('% Asistencia', ascending=False)
        ranking.columns = ['Jugador', 'Presentes', 'SAF', 'Ausentes', 'Total', '% Asistencia']
        st.dataframe(ranking, use_container_width=True, hide_index=True)

    else:
        st.info(f"No hay registros para la división {div_elegida}.")
else:
    st.warning("Cargando datos de Notion... por favor espera.")
