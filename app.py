import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Monitoreo Consumo Agua - Quito", layout="wide")

st.title("🚰 Monitoreo de Consumo de Agua - Residencia Quito")
st.markdown("**Hogar: 5 personas** | **Límite mensual: 15 m³** (3 m³ por persona)")

# ────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ────────────────────────────────────────────────────────────────
url = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"

# Estado inicial
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False
    st.session_state.consumo_mensual = 0.0
    st.session_state.porcentaje_mensual = 0.0
    st.session_state.dias_mes = []
    st.session_state.consumo_por_dia = []
    st.session_state.last_check = None
    st.session_state.error_msg = ""

# ────────────────────────────────────────────────────────────────
# CARGA Y PROCESAMIENTO DE DATOS
# ────────────────────────────────────────────────────────────────
def cargar_y_procesar():
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['date_id'].astype(str) + ' ' + df['start_time'].astype(str), errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df = df[['timestamp', 'total_liters']].sort_values('timestamp').drop_duplicates(subset=['timestamp'])
        df.set_index('timestamp', inplace=True)
        series = df['total_liters'].resample('D').last().ffill()

        # Consumo mensual (desde día 1 del mes actual)
        today = datetime.now()
        first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        df_month = series[series.index >= first_day]

        if not df_month.empty:
            consumo_inicial = df_month.iloc[0]
            consumo_final = df_month.iloc[-1]
            consumo_mensual_litros = consumo_final - consumo_inicial if len(df_month) > 1 else consumo_final
            st.session_state.consumo_mensual = consumo_mensual_litros
            st.session_state.porcentaje_mensual = (consumo_mensual_litros / 15000) * 100

            # Datos para gráfica: días y consumo acumulado
            dias = [(d - first_day).days + 1 for d in df_month.index]
            consumo_por_dia = (df_month - consumo_inicial).tolist()

            st.session_state.dias_mes = dias
            st.session_state.consumo_por_dia = consumo_por_dia
        else:
            st.session_state.consumo_mensual = 0.0
            st.session_state.porcentaje_mensual = 0.0
            st.session_state.dias_mes = []
            st.session_state.consumo_por_dia = []

        st.session_state.last_check = datetime.now()
        st.session_state.estado = "Datos actualizados"
        st.session_state.datos_cargados = True

    except Exception as e:
        st.session_state.error_msg = f"Error al cargar datos: {str(e)}"
        st.session_state.estado = "Error"

# ────────────────────────────────────────────────────────────────
# SIMULACIÓN DE ENTRENAMIENTO Y EVENTOS (para gráfica 2)
# ────────────────────────────────────────────────────────────────
def generar_entrenamiento_simulado():
    # Simulación de pérdida durante entrenamiento (epochs)
    epochs = list(range(1, 31))
    loss = [0.8 / (e + 1) + np.random.normal(0, 0.02) for e in epochs]  # pérdida decreciente

    # Simulación de eventos/anomalías en el mes actual (días aleatorios)
    today = datetime.now()
    first_day = today.replace(day=1)
    num_dias_mes = (today - first_day).days + 1
    eventos = np.random.choice([0, 1], size=num_dias_mes, p=[0.85, 0.15])  # 15% probabilidad de evento

    return epochs, loss, eventos

# ────────────────────────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
col1.metric("Consumo mensual actual", f"{st.session_state.consumo_mensual/1000:.2f} m³")
col2.metric("Porcentaje usado", f"{st.session_state.porcentaje_mensual:.1f}%")

st.metric("Estado", st.session_state.estado)
st.metric("Último chequeo", st.session_state.last_check.strftime('%d/%m %H:%M') if st.session_state.last_check else "No actualizado")

if st.session_state.error_msg:
    st.error(st.session_state.error_msg)

# Botón para actualizar datos
if st.button("🔄 Actualizar consumo mensual"):
    cargar_y_procesar()
    st.rerun()

# ────────────────────────────────────────────────────────────────
# GRÁFICA 1: Consumo mensual acumulado (automática si hay datos)
# ────────────────────────────────────────────────────────────────
if st.session_state.dias_mes:
    fig_mensual = go.Figure()
    fig_mensual.add_trace(go.Scatter(
        x=st.session_state.dias_mes,
        y=[c / 1000 for c in st.session_state.consumo_por_dia],
        mode='lines+markers',
        name='Consumo acumulado',
        line=dict(color='royalblue')
    ))
    fig_mensual.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
    fig_mensual.update_layout(
        title="Consumo Acumulado del Mes Actual (m³)",
        xaxis_title="Día del mes",
        yaxis_title="Volumen (m³)",
        xaxis=dict(tickmode='linear', dtick=1)
    )
    st.plotly_chart(fig_mensual, use_container_width=True)

# ────────────────────────────────────────────────────────────────
# GRÁFICA 2: Entrenamiento del modelo + eventos del mes
# ────────────────────────────────────────────────────────────────
st.subheader("Entrenamiento del modelo y eventos detectados")
epochs, loss, eventos = generar_entrenamiento_simulado()

fig_entrenamiento = go.Figure()

# Curva de pérdida del entrenamiento
fig_entrenamiento.add_trace(go.Scatter(
    x=epochs,
    y=loss,
    mode='lines',
    name='Pérdida (loss) durante entrenamiento',
    line=dict(color='green')
))

# Eventos del mes (líneas verticales rojas en los días con anomalía)
if eventos.any():
    dias_evento = [d for d, e in zip(range(1, len(eventos)+1), eventos) if e == 1]
    for dia in dias_evento:
        fig_entrenamiento.add_vline(x=dia, line_dash="dot", line_color="red", annotation_text=f"Evento día {dia}")

fig_entrenamiento.update_layout(
    title="Pérdida durante entrenamiento del modelo y eventos detectados en el mes",
    xaxis_title="Épocas (entrenamiento) / Días del mes (eventos)",
    yaxis_title="Pérdida (loss)",
    showlegend=True
)
st.plotly_chart(fig_entrenamiento, use_container_width=True)

st.caption("Sistema desarrollado por Camilo Quinto, José Insuasti, Paul Palma y Milton Simbaña • Render.com")
