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

# Función alerta
def enviar_alerta():
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        body = f"Alerta de prueba.\nConsumo mensual actual: {st.session_state.consumo_mensual/1000:.2f} m³\nHora: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg['Subject'] = "🚨 Alerta de Prueba"
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        st.success("✅ Alerta enviada por correo")
    except:
        st.error("❌ No se pudo enviar la alerta")

# Carga de datos
@st.cache_data(ttl=300)
def cargar_datos():
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
        diff = df_month.diff().fillna(0).clip(lower=0)
        st.session_state.consumo_mensual = diff.sum()
        st.session_state.porcentaje_mensual = (st.session_state.consumo_mensual / 15000) * 100
        st.session_state.dias_mes = df_month.index.day.tolist()
        st.session_state.consumo_por_dia = diff.cumsum().tolist()

    return df

df_total = cargar_datos()

# Dashboard
col1, col2 = st.columns(2)
col1.metric("Consumo mensual actual", f"{st.session_state.consumo_mensual/1000:.2f} m³")
col2.metric("Porcentaje usado", f"{st.session_state.porcentaje_mensual:.1f}%")

# Gráfica 1: Consumo del mes actual
if st.session_state.dias_mes:
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=st.session_state.dias_mes,
        y=[c / 1000 for c in st.session_state.consumo_por_dia],
        mode='lines+markers',
        name='Consumo acumulado',
        line=dict(color='royalblue'),
        marker=dict(size=8)
    ))
    fig1.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
    fig1.update_layout(
        title="Consumo Acumulado del Mes Actual (m³)",
        xaxis_title="Día del mes",
        yaxis_title="Volumen acumulado (m³)",
        height=480
    )
    st.plotly_chart(fig1, use_container_width=True)

# Gráfica 2: Histórico completo
st.subheader("Análisis Histórico Completo y Alertas")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=df_total.index,
    y=df_total['total_liters'],
    mode='lines',
    name='Consumo Histórico',
    line=dict(color='blue')
))

# Alertas simuladas (usando fechas reales del dataset)
alert_dates = pd.to_datetime(['2025-03-08', '2025-03-15', '2025-04-05', '2025-04-20'])
for alert_date in alert_dates:
    if alert_date in df_total.index:
        fig2.add_vline(x=alert_date, line_dash="dot", line_color="red", 
                       annotation_text="🚨 Alerta")

fig2.update_layout(
    title="Consumo Histórico Completo desde Febrero",
    xaxis_title="Fecha",
    yaxis_title="Litros Acumulados",
    height=520
)
st.plotly_chart(fig2, use_container_width=True)

# Descripción
st.markdown("""
**Explicación de la segunda gráfica:**  
Esta gráfica muestra **todo el historial de consumo** desde el 20 de febrero hasta la fecha actual.  
Las líneas verticales rojas indican los días en los que se detectaron anomalías y se enviaron alertas por correo electrónico.
""")

# Botón de prueba
if st.button("Enviar alerta de prueba por correo"):
    enviar_alerta()

st.caption("Sistema desarrollado por Camilo Quinto, José Insuasti, Paul Palma y Milton Simbaña • Render.com")
