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

st.title("🚰 Monitoreo de Consumo de Agua - Residencia Quito")
st.markdown("**Hogar: 5 personas** | **Límite mensual: 15 m³** (3 m³ por persona)")

# Configuración
EMAIL_FROM = 'joshinanlo@gmail.com'
EMAIL_TO = 'joshinanlo@gmail.com'
APP_PASSWORD = os.environ.get("APP_PASSWORD")

url = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"

# Inicialización
if 'consumo_mensual' not in st.session_state:
    st.session_state.consumo_mensual = 0.0
    st.session_state.porcentaje_mensual = 0.0
    st.session_state.dias_mes = []
    st.session_state.consumo_por_dia = []
    st.session_state.error_msg = ""

# Función alerta
def enviar_alerta():
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        body = f"Alerta detectada.\nConsumo mensual: {st.session_state.consumo_mensual/1000:.2f} m³ ({st.session_state.porcentaje_mensual:.1f}%)\nRevise urgentemente."
        msg['Subject'] = "🚨 Alerta de Consumo"
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        st.success("Alerta enviada")
    except:
        st.error("No se pudo enviar la alerta")

# Carga de datos más robusta
@st.cache_data(ttl=300)
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

        if len(df_month) >= 1:
            # Cálculo seguro contra resets
            diff = df_month.diff().fillna(0)
            diff = diff.clip(lower=0)                    # Elimina negativos
            consumo_mensual = diff.sum()

            st.session_state.consumo_mensual = consumo_mensual
            st.session_state.porcentaje_mensual = (consumo_mensual / 15000) * 100

            dias = df_month.index.day.tolist()
            consumo_por_dia = diff.cumsum().tolist()

            st.session_state.dias_mes = dias
            st.session_state.consumo_por_dia = consumo_por_dia
            st.session_state.error_msg = ""
        else:
            st.session_state.error_msg = "No hay datos suficientes este mes"

    except Exception as e:
        st.session_state.error_msg = f"Error al cargar datos: {str(e)}"

cargar_datos()

# Dashboard
col1, col2 = st.columns(2)
col1.metric("Consumo mensual actual", f"{st.session_state.consumo_mensual/1000:.2f} m³")
col2.metric("Porcentaje usado", f"{st.session_state.porcentaje_mensual:.1f}%")

if st.session_state.error_msg:
    st.error(st.session_state.error_msg)

# Gráfica principal
if st.session_state.dias_mes:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=st.session_state.dias_mes,
        y=[c / 1000 for c in st.session_state.consumo_por_dia],
        mode='lines+markers',
        name='Consumo acumulado',
        line=dict(color='royalblue'),
        marker=dict(size=8, color='darkblue')
    ))
    fig.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
    fig.update_layout(
        title="Consumo Acumulado del Mes Actual (m³)",
        xaxis_title="Día del mes",
        yaxis_title="Volumen acumulado (m³)",
        xaxis=dict(tickmode='linear', dtick=1),
        height=550
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Esperando datos del mes actual...")

st.caption("Sistema desarrollado por Camilo Quinto, José Insuasti, Paul Palma y Milton Simbaña • Render.com")

if st.button("Enviar alerta de prueba por correo"):
    enviar_alerta()
    st.success("Alerta enviada")
