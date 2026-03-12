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
from streamlit_autorefresh import st_autorefresh
import os

st.set_page_config(page_title="Monitoreo Consumo Agua - Quito", layout="wide")

# ==================== REFRESCO AUTOMÁTICO DE GRÁFICAS ====================
st_autorefresh(interval=60000, key="datarefresh")

# ==================== DESCRIPCIÓN Y AUTORES ====================
with st.expander("ℹ️ Acerca de este sistema", expanded=True):
    st.markdown("""
    **Sistema de monitoreo y análisis de consumo de agua potable residencial**  
    Vivienda unifamiliar ubicada en la ciudad de **Quito, Ecuador**, basado en tecnologías  
    **Internet de las Cosas (IoT)** e **Inteligencia Artificial (IA)**, orientado a la reducción  
    de consumos anómalos y al uso eficiente del recurso hídrico a nivel doméstico.
    
    **Autores:**  
    - Camilo Quinto  
    - José Insuasti  
    - Paul Palma  
    - Milton Simbaña
    """)

st.title("🚰 Monitoreo Inteligente de Consumo de Agua - Residencia Quito")
st.markdown("**Hogar: 5 personas** | **Límite mensual autorizado: 15 m³** (3 m³ por persona)")

# ==================== CONFIGURACIÓN (CORREGIDA) ====================
EMAIL_FROM = 'joshinanlo@gmail.com'
EMAIL_TO = 'joshinanlo@gmail.com'
APP_PASSWORD = os.environ.get("APP_PASSWORD", "lvchktwnenwvgdje")

url = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"

# Variables de estado
if 'consumo_actual' not in st.session_state:
    st.session_state.consumo_actual = 0.0
    st.session_state.porcentaje = 0.0
    st.session_state.mse_actual = 0.0
    st.session_state.estado = "Cargando datos..."
    st.session_state.hist_consumo = []
    st.session_state.hist_mse = []
    st.session_state.last_check = None

# Función de alerta
def enviar_alerta(mse):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = f"🚨 Alerta: Posible fuga de agua - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        body = f"""Se ha detectado un consumo anómalo.

MSE: {mse:.6f}
Consumo actual: {st.session_state.consumo_actual:.2f} m³ ({st.session_state.porcentaje:.1f}% del límite)
Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Por favor revise las tuberías urgentemente.
"""
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        st.success("✅ Alerta enviada por correo electrónico")
    except Exception as e:
        st.error(f"Error al enviar correo: {e}")

# Hilo de monitoreo
def monitoreo_background():
    try:
        model = load_model('modelo_anomalias_agua.h5', compile=False)
        model.compile(optimizer='adam', loss=MeanSquaredError())
        st.session_state.estado = "Modelo cargado correctamente"
    except Exception as e:
        st.session_state.estado = f"Error cargando modelo: {e}"
        return

    while True:
        try:
            df = pd.read_csv(url)
            df['timestamp'] = pd.to_datetime(df['date_id'].astype(str) + ' ' + df['start_time'].astype(str), errors='coerce')
            df = df.dropna(subset=['timestamp'])
            df = df[['timestamp', 'total_liters']].sort_values('timestamp').drop_duplicates(subset=['timestamp'])
            df.set_index('timestamp', inplace=True)
            series = df['total_liters'].resample('5T').last().ffill()
            consumption = series.diff().fillna(0)

            if len(consumption) >= 288:
                last_seq = consumption[-288:].values.reshape(1, 288, 1)
                last_scaled = scaler.transform(last_seq.reshape(-1, 1)).reshape(1, 288, 1)

                pred = model.predict(last_scaled, verbose=0)
                mse = np.mean(np.power(last_scaled - pred, 2))

                st.session_state.mse_actual = mse
                st.session_state.consumo_actual = series.iloc[-1] / 1000
                st.session_state.porcentaje = (st.session_state.consumo_actual / 15) * 100
                st.session_state.hist_consumo.append(st.session_state.consumo_actual)
                st.session_state.hist_mse.append(mse)
                st.session_state.last_check = datetime.now()

                if len(st.session_state.hist_consumo) > 200:
                    st.session_state.hist_consumo.pop(0)
                    st.session_state.hist_mse.pop(0)

                if mse > threshold:
                    enviar_alerta(mse)
                    st.session_state.estado = "¡ALERTA DE FUGA!"
                else:
                    st.session_state.estado = "Normal"

        except Exception as e:
            st.session_state.estado = f"Error en chequeo: {str(e)}"

        time.sleep(60)

# Iniciar hilo
if 'monitoreo_started' not in st.session_state:
    threading.Thread(target=monitoreo_background, daemon=True).start()
    st.session_state.monitoreo_started = True

# Dashboard
col1, col2, col3 = st.columns(3)
col1.metric("Consumo acumulado", f"{st.session_state.consumo_actual:.2f} m³", f"{st.session_state.porcentaje:.1f}% del límite")
col2.metric("Estado del sistema", st.session_state.estado)
col3.metric("Último chequeo", st.session_state.last_check.strftime('%H:%M:%S') if st.session_state.last_check else "Cargando...")

if st.session_state.hist_consumo:
    fig_consumo = go.Figure()
    fig_consumo.add_trace(go.Scatter(y=st.session_state.hist_consumo, mode='lines+markers', name='Consumo (m³)', line=dict(color='blue')))
    fig_consumo.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
    fig_consumo.update_layout(title="Consumo Acumulado en Tiempo Real", xaxis_title="Chequeos recientes", yaxis_title="m³")
    st.plotly_chart(fig_consumo, use_container_width=True)

    fig_mse = go.Figure()
    fig_mse.add_trace(go.Scatter(y=st.session_state.hist_mse, mode='lines+markers', name='Error MSE', line=dict(color='red')))
    fig_mse.update_layout(title="Error MSE en Tiempo Real", xaxis_title="Chequeos recientes", yaxis_title="MSE")
    st.plotly_chart(fig_mse, use_container_width=True)

st.caption("Sistema desarrollado por Camilo Quinto, José Insuasti, Paul Palma y Milton Simbaña • Actualización automática cada 60 segundos • Render.com")

if st.button("Enviar alerta de prueba"):
    enviar_alerta(0.5)
    st.success("Correo de prueba enviado")

