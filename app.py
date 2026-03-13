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
# INICIALIZACIÓN DE TODAS LAS CLAVES DE SESSION_STATE (AL INICIO)
# ────────────────────────────────────────────────────────────────
if 'consumo_mensual' not in st.session_state:
    st.session_state.consumo_mensual = 0.0
    st.session_state.porcentaje_mensual = 0.0
    st.session_state.estado = "Presiona 'Actualizar datos' para comenzar"
    st.session_state.last_check = None
    st.session_state.error_msg = ""
    st.session_state.dias_mes = []
    st.session_state.consumo_por_dia = []

# ────────────────────────────────────────────────────────────────
# TÍTULO Y DESCRIPCIÓN SUTIL
# ────────────────────────────────────────────────────────────────
st.title("🚰 Monitoreo de Consumo de Agua - Residencia Quito")
st.markdown("**Hogar: 5 personas** | **Límite mensual: 15 m³** (3 m³ por persona)")

st.caption("Sistema desarrollado por Camilo Quinto, José Insuasti, Paul Palma y Milton Simbaña • Render.com")

# ────────────────────────────────────────────────────────────────
# CONFIG EMAIL Y URL
# ────────────────────────────────────────────────────────────────
EMAIL_FROM = 'joshinanlo@gmail.com'
EMAIL_TO = 'joshinanlo@gmail.com'
APP_PASSWORD = os.environ.get("APP_PASSWORD", "lvchktwnenwvgdje")

url = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"

# ────────────────────────────────────────────────────────────────
# FUNCIÓN ALERTA
# ────────────────────────────────────────────────────────────────
def enviar_alerta(tipo="fuga"):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if tipo == "fuga":
            subject = f"🚨 Alerta posible fuga - {now_str}"
            body = f"Posible consumo anómalo detectado.\nConsumo mensual: {st.session_state.consumo_mensual/1000:.2f} m³ ({st.session_state.porcentaje_mensual:.1f}%)\nRevise urgentemente."
        else:
            subject = f"⚠️ Consumo mensual alto - {now_str}"
            body = f"Consumo mensual cerca del límite.\nActual: {st.session_state.consumo_mensual/1000:.2f} m³ ({st.session_state.porcentaje_mensual:.1f}%)\nRevise el uso."
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        st.success("Alerta enviada")
    except Exception as e:
        st.error(f"Error correo: {e}")

# ────────────────────────────────────────────────────────────────
# FUNCIÓN ACTUALIZAR DATOS (solo al botón)
# ────────────────────────────────────────────────────────────────
def actualizar_datos():
    st.session_state.estado = "Actualizando..."
    st.session_state.error_msg = ""

    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['date_id'].astype(str) + ' ' + df['start_time'].astype(str), errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df = df[['timestamp', 'total_liters']].sort_values('timestamp').drop_duplicates(subset=['timestamp'])
        df.set_index('timestamp', inplace=True)
        series = df['total_liters'].resample('D').last().ffill()

        # Consumo mensual
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
        st.session_state.estado = "Datos actualizados"

    except Exception as e:
        st.session_state.error_msg = f"Error: {str(e)}"
        st.session_state.estado = "Error al actualizar"

# ────────────────────────────────────────────────────────────────
# DASHBOARD Y GRÁFICA
# ────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
col1.metric("Consumo mensual actual", f"{st.session_state.consumo_mensual/1000:.2f} m³")
col2.metric("Porcentaje usado", f"{st.session_state.porcentaje_mensual:.1f}%")

st.metric("Estado", st.session_state.estado)
st.metric("Último chequeo", st.session_state.last_check.strftime('%d/%m %H:%M') if st.session_state.last_check else "No actualizado")

if st.session_state.error_msg:
    st.error(st.session_state.error_msg)

# Botón principal
if st.button("🔄 Actualizar datos ahora"):
    actualizar_datos()
    st.rerun()

# Gráfica única: Consumo mensual por día
if st.session_state.dias_mes:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=st.session_state.dias_mes,
        y=[c / 1000 for c in st.session_state.consumo_por_dia],
        mode='lines+markers',
        name='Consumo acumulado',
        line=dict(color='royalblue')
    ))
    fig.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
    fig.update_layout(
        title="Consumo Acumulado del Mes Actual (m³)",
        xaxis_title="Día del mes",
        yaxis_title="Volumen (m³)",
        xaxis=dict(tickmode='linear', dtick=1)
    )
    st.plotly_chart(fig, use_container_width=True)

if st.button("Enviar alerta de prueba"):
    # Simulación de alerta (sin enviar realmente para evitar spam en pruebas)
    st.success("Correo de prueba simulado (no enviado)")
