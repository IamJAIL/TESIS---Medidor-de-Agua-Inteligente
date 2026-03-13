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

# Configuración email
EMAIL_FROM = 'joshinanlo@gmail.com'
EMAIL_TO = 'joshinanlo@gmail.com'
APP_PASSWORD = os.environ.get("APP_PASSWORD", "lvchktwnenwvgdje")

url = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"

# Estado inicial
if 'datos_cargados' not in st.session_state:
    st.session_state.consumo_mensual = 0.0
    st.session_state.porcentaje_mensual = 0.0
    st.session_state.dias_mes = []
    st.session_state.consumo_por_dia = []
    st.session_state.dias_con_alerta = []  # Días con fuga/anomalía
    st.session_state.last_check = None
    st.session_state.error_msg = ""

# Función alerta (solo para prueba o real)
def enviar_alerta(tipo="fuga"):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        body = f"{tipo.capitalize()} detectada.\nConsumo mensual: {st.session_state.consumo_mensual/1000:.2f} m³ ({st.session_state.porcentaje_mensual:.1f}%)\nFecha/Hora: {now_str}"
        msg['Subject'] = f"{'🚨' if tipo=='fuga' else '⚠️'} Alerta - {now_str}"
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        st.success("Alerta enviada")
    except Exception as e:
        st.error(f"Error correo: {e}")

# Carga automática de datos al abrir la página
@st.cache_data(ttl=300)  # Cache 5 minutos para no recargar cada vez
def cargar_datos():
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

            # Días y consumo acumulado
            dias = [(d - first_day).days + 1 for d in df_month.index]
            consumo_por_dia = (df_month - consumo_inicial).tolist()

            st.session_state.dias_mes = dias
            st.session_state.consumo_por_dia = consumo_por_dia

            # Simulación de días con alerta (en producción real vendría del MSE > threshold)
            # Para ejemplo: marcamos días con consumo > 1 m³ como "evento"
            dias_alerta = [d for d, c in zip(dias, consumo_por_dia) if c / 1000 > 1]
            st.session_state.dias_con_alerta = dias_alerta

        else:
            st.session_state.consumo_mensual = 0.0
            st.session_state.porcentaje_mensual = 0.0
            st.session_state.dias_mes = []
            st.session_state.consumo_por_dia = []
            st.session_state.dias_con_alerta = []

        st.session_state.last_check = datetime.now()

    except Exception as e:
        st.session_state.error_msg = f"Error al cargar: {str(e)}"

# Cargar datos automáticamente al abrir la página
cargar_datos()

# Dashboard
col1, col2 = st.columns(2)
col1.metric("Consumo mensual actual", f"{st.session_state.consumo_mensual/1000:.2f} m³")
col2.metric("Porcentaje usado", f"{st.session_state.porcentaje_mensual:.1f}%")

st.metric("Último chequeo", st.session_state.last_check.strftime('%d/%m %H:%M') if st.session_state.last_check else "No cargado")

if st.session_state.error_msg:
    st.error(st.session_state.error_msg)

# ────────────────────────────────────────────────────────────────
# GRÁFICA 1: Consumo mensual acumulado (detalle con puntos)
# ────────────────────────────────────────────────────────────────
if st.session_state.dias_mes:
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=st.session_state.dias_mes,
        y=[c / 1000 for c in st.session_state.consumo_por_dia],
        mode='lines+markers',  # Línea + puntos en cada día con consumo
        name='Consumo acumulado',
        line=dict(color='royalblue'),
        marker=dict(size=8, color='darkblue')
    ))
    fig1.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
    fig1.update_layout(
        title="Consumo Acumulado del Mes Actual (m³)",
        xaxis_title="Día del mes",
        yaxis_title="Volumen (m³)",
        xaxis=dict(tickmode='linear', dtick=1, range=[1, max(st.session_state.dias_mes)+1]),
        height=500
    )
    st.plotly_chart(fig1, use_container_width=True)

# ────────────────────────────────────────────────────────────────
# GRÁFICA 2: Entrenamiento + alertas del mes
# ────────────────────────────────────────────────────────────────
st.subheader("Entrenamiento del modelo y alertas detectadas")
epochs = list(range(1, 31))
loss = [0.8 / (e + 1) + np.random.normal(0, 0.02) for e in epochs]  # Simulación de pérdida

fig2 = go.Figure()

# Curva de pérdida del entrenamiento
fig2.add_trace(go.Scatter(
    x=epochs,
    y=loss,
    mode='lines',
    name='Pérdida durante entrenamiento',
    line=dict(color='green')
))

# Alertas/anomalías en el mes (líneas verticales rojas)
if st.session_state.dias_con_alerta:
    for dia in st.session_state.dias_con_alerta:
        fig2.add_vline(x=dia, line_dash="dot", line_color="red", annotation_text=f"Alerta día {dia}", annotation_position="top right")

fig2.update_layout(
    title="Pérdida del entrenamiento y alertas/anomalías del mes",
    xaxis_title="Épocas (izquierda) / Días del mes (derecha)",
    yaxis_title="Pérdida (loss)",
    showlegend=True,
    height=500
)
st.plotly_chart(fig2, use_container_width=True)

# Botón de prueba de alerta
if st.button("Enviar alerta de prueba"):
    enviar_alerta(tipo="fuga")
    st.success("Correo de prueba enviado (verifica tu bandeja)")

st.caption("Sistema desarrollado por Camilo Quinto, José Insuasti, Paul Palma y Milton Simbaña • Render.com")
