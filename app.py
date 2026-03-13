import streamlit as st
import pandas as pd
import numpy as np
import threading
import time
from datetime import datetime
import plotly.graph_objects as go
from tensorflow.keras.models import load_model
from tensorflow.keras.losses import MeanSquaredError
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
APP_PASSWORD = os.environ.get("APP_PASSWORD", "lvchktwnenwvgdje")

url = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"

# Estado inicial
if 'consumo_actual' not in st.session_state:
    st.session_state.consumo_actual = 0.0
    st.session_state.consumo_mensual = 0.0
    st.session_state.porcentaje_mensual = 0.0
    st.session_state.mse_actual = 0.0
    st.session_state.estado = "Presiona 'Actualizar datos' para comenzar"
    st.session_state.hist_consumo = []
    st.session_state.hist_mse = []
    st.session_state.last_check = None
    st.session_state.error_msg = ""

# Función alerta
def enviar_alerta(mse, tipo="fuga"):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        if tipo == "fuga":
            subject = f"🚨 Alerta posible fuga - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            body = f"""Posible fuga detectada.

MSE: {mse:.6f}
Consumo mensual: {st.session_state.consumo_mensual/1000:.2f} m³ ({st.session_state.porcentaje_mensual:.1f}%)
Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        else:
            subject = f"⚠️ Consumo mensual alto - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            body = f"""Consumo mensual cerca del límite.

Actual: {st.session_state.consumo_mensual/1000:.2f} m³ ({st.session_state.porcentaje_mensual:.1f}%)
Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        st.success("Alerta enviada")
    except Exception as e:
        st.error(f"Error correo: {e}")

# Hilo de monitoreo (solo se ejecuta cuando se presiona el botón)
def actualizar_datos():
    st.session_state.estado = "Actualizando datos..."
    try:
        model = load_model('modelo_anomalias_agua.h5', compile=False)
        model.compile(optimizer='adam', loss=MeanSquaredError())
    except Exception as e:
        st.session_state.error_msg = f"Error modelo: {str(e)}"
        st.session_state.estado = "Error cargando modelo"
        return

    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['date_id'].astype(str) + ' ' + df['start_time'].astype(str), errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df = df[['timestamp', 'total_liters']].sort_values('timestamp').drop_duplicates(subset=['timestamp'])
        df.set_index('timestamp', inplace=True)
        series = df['total_liters'].resample('5T').last().ffill()
        consumption = series.diff().fillna(0)

        if len(consumption) < 288:
            st.session_state.error_msg = "Datos insuficientes"
            st.session_state.estado = "Datos insuficientes"
            return

        last_seq = consumption[-288:].values.reshape(1, 288, 1)
        last_scaled = scaler.transform(last_seq.reshape(-1, 1)).reshape(1, 288, 1)

        pred = model.predict(last_scaled, verbose=0)
        mse = np.mean(np.power(last_scaled - pred, 2))

        # Consumo total
        st.session_state.consumo_actual = series.iloc[-1]

        # Consumo mensual
        today = datetime.now()
        first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        df_month = series[series.index >= first_day]
        if not df_month.empty:
            consumo_mensual_litros = df_month.iloc[-1] - df_month.iloc[0] if len(df_month) > 1 else df_month.iloc[-1]
            st.session_state.consumo_mensual = consumo_mensual_litros
            st.session_state.porcentaje_mensual = (consumo_mensual_litros / 15000) * 100
        else:
            st.session_state.consumo_mensual = 0.0
            st.session_state.porcentaje_mensual = 0.0

        st.session_state.mse_actual = mse
        st.session_state.hist_consumo.append(st.session_state.consumo_actual / 1000)
        st.session_state.hist_mse.append(mse)
        st.session_state.last_check = datetime.now()

        if len(st.session_state.hist_consumo) > 200:
            st.session_state.hist_consumo.pop(0)
            st.session_state.hist_mse.pop(0)

        if mse > threshold:
            enviar_alerta(mse, "fuga")
            st.session_state.estado = "¡ALERTA DE FUGA!"
        elif st.session_state.porcentaje_mensual > 90:
            enviar_alerta(mse, "limite")
            st.session_state.estado = "Consumo mensual alto"
        else:
            st.session_state.estado = "Normal"
            st.session_state.error_msg = ""

    except Exception as e:
        st.session_state.error_msg = f"Error: {str(e)}"
        st.session_state.estado = "Error al actualizar"

# Dashboard principal
col1, col2, col3 = st.columns(3)
col1.metric("Consumo mensual actual", f"{st.session_state.consumo_mensual/1000:.2f} m³", f"{st.session_state.porcentaje_mensual:.1f}%")
col2.metric("Estado", st.session_state.estado)
col3.metric("Último chequeo", st.session_state.last_check.strftime('%d/%m %H:%M') if st.session_state.last_check else "No actualizado")

if st.session_state.error_msg:
    st.error(st.session_state.error_msg)

# Botón principal
if st.button("🔄 Actualizar datos ahora"):
    actualizar_datos()
    st.rerun()  # Fuerza actualización de toda la página

# Gráficas
if st.session_state.hist_consumo:
    fig_consumo = go.Figure()
    fig_consumo.add_trace(go.Scatter(y=st.session_state.hist_consumo, mode='lines+markers', name='Consumo (m³)', line=dict(color='blue')))
    fig_consumo.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite mensual")
    fig_consumo.update_layout(title="Consumo Acumulado", xaxis_title="Actualizaciones", yaxis_title="m³")
    st.plotly_chart(fig_consumo, use_container_width=True)

    fig_mensual = go.Figure()
    fig_mensual.add_trace(go.Bar(x=["Mes actual"], y=[st.session_state.consumo_mensual/1000], name='Consumo mensual', marker_color='royalblue'))
    fig_mensual.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
    fig_mensual.update_layout(title="Consumo del Mes Actual", yaxis_title="m³")
    st.plotly_chart(fig_mensual, use_container_width=True)

    fig_mse = go.Figure()
    fig_mse.add_trace(go.Scatter(y=st.session_state.hist_mse, mode='lines+markers', name='Error MSE', line=dict(color='red')))
    fig_mse.update_layout(title="Error MSE (detección de anomalías)", xaxis_title="Actualizaciones", yaxis_title="MSE")
    st.plotly_chart(fig_mse, use_container_width=True)

st.caption("Sistema desarrollado por Camilo Quinto, José Insuasti, Paul Palma y Milton Simbaña • Render.com")

if st.button("Enviar alerta de prueba"):
    enviar_alerta(0.5)
    st.success("Correo de prueba enviado")
