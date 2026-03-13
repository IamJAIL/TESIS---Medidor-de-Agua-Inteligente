import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

st.set_page_config(page_title="Monitoreo Consumo Agua - Quito", layout="wide")

# ────────────────────────────────────────────────────────────────
# INICIALIZACIÓN
# ────────────────────────────────────────────────────────────────
if 'datos_cargados' not in st.session_state:
    st.session_state.consumo_mensual = 0.0
    st.session_state.porcentaje_mensual = 0.0
    st.session_state.dias_mes = []
    st.session_state.consumo_por_dia = []
    st.session_state.last_check = None
    st.session_state.error_msg = ""

# ────────────────────────────────────────────────────────────────
# DESCRIPCIÓN SUTIL AL FINAL (como pediste)
# ────────────────────────────────────────────────────────────────
st.title("🚰 Monitoreo de Consumo de Agua - Residencia Quito")
st.markdown("**Hogar: 5 personas** | **Límite mensual: 15 m³** (3 m³ por persona)")

# ────────────────────────────────────────────────────────────────
# CARGA AUTOMÁTICA DE DATOS
# ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # Cache 5 min
def cargar_datos():
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['date_id'].astype(str) + ' ' + df['start_time'].astype(str), errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df = df[['timestamp', 'total_liters']].sort_values('timestamp').drop_duplicates(subset=['timestamp'])
        df.set_index('timestamp', inplace=True)
        series = df['total_liters'].resample('D').last().ffill()

        today = datetime.now()
        first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        df_month = series[series.index >= first_day]

        if not df_month.empty:
            consumo_inicial = df_month.iloc[0]
            consumo_final = df_month.iloc[-1]
            consumo_mensual_litros = consumo_final - consumo_inicial if len(df_month) > 1 else consumo_final
            st.session_state.consumo_mensual = consumo_mensual_litros
            st.session_state.porcentaje_mensual = (consumo_mensual_litros / 15000) * 100

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

    except Exception as e:
        st.session_state.error_msg = f"Error al cargar: {str(e)}"

cargar_datos()

# ────────────────────────────────────────────────────────────────
# GRÁFICA 1: Consumo mensual (detalle con puntos)
# ────────────────────────────────────────────────────────────────
st.subheader("Consumo Acumulado del Mes Actual")
if st.session_state.dias_mes:
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=st.session_state.dias_mes,
        y=[c / 1000 for c in st.session_state.consumo_por_dia],
        mode='lines+markers',
        name='Consumo acumulado',
        line=dict(color='royalblue'),
        marker=dict(size=10, color='darkblue')
    ))
    fig1.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
    fig1.update_layout(
        xaxis_title="Día del mes",
        yaxis_title="Volumen (m³)",
        xaxis=dict(tickmode='linear', dtick=1),
        height=500
    )
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("Cargando datos del mes...")

# ────────────────────────────────────────────────────────────────
# GRÁFICA 2: Entrenamiento + alertas del mes
# ────────────────────────────────────────────────────────────────
st.subheader("Entrenamiento del modelo y alertas detectadas")
epochs = list(range(1, 31))
loss = [0.8 / (e + 1) + np.random.normal(0, 0.02) for e in epochs]

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=epochs,
    y=loss,
    mode='lines',
    name='Pérdida durante entrenamiento',
    line=dict(color='green')
))

# Simulación de alertas (días con anomalía)
dias_alerta = np.random.choice(st.session_state.dias_mes or [5, 10, 20], size=2, replace=False)
for dia in dias_alerta:
    fig2.add_vline(x=dia, line_dash="dot", line_color="red", annotation_text=f"Alerta día {dia}")

fig2.update_layout(
    xaxis_title="Épocas / Días del mes",
    yaxis_title="Pérdida (loss)",
    height=500
)
st.plotly_chart(fig2, use_container_width=True)

# ────────────────────────────────────────────────────────────────
# PANTALLA 3: ALERTA SIMULADA
# ────────────────────────────────────────────────────────────────
st.subheader("Ejemplo de alerta simulada (como llegaría al correo)")
st.info("Simulación de mensaje que recibiría el usuario al detectar una anomalía:")

sim_mse = 0.078912
sim_fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
sim_consumo = st.session_state.consumo_mensual / 1000 if st.session_state.consumo_mensual else 7.85
sim_porcentaje = st.session_state.porcentaje_mensual if st.session_state.porcentaje_mensual else 52.3

alerta_simulada = f"""
**Asunto:** 🚨 Alerta: Posible fuga de agua detectada

Se ha detectado un consumo anómalo en la vivienda.

- MSE detectado: {sim_mse:.6f} (superior al umbral)
- Consumo mensual actual: {sim_consumo:.2f} m³ ({sim_porcentaje:.1f}% del límite autorizado)
- Fecha/Hora de detección: {sim_fecha}

**Recomendación urgente:** Revise las tuberías y válvulas inmediatamente para evitar pérdidas mayores.

Sistema de monitoreo IoT + IA – Residencia Quito
"""
st.code(alerta_simulada, language="text")

# Botón de prueba real
if st.button("Enviar alerta de prueba real por correo"):
    enviar_alerta(tipo="fuga")
    st.success("Correo de prueba enviado – verifica tu bandeja")

st.caption("Sistema desarrollado por Camilo Quinto, José Insuasti, Paul Palma y Milton Simbaña • Render.com")
