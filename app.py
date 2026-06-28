import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Monitoreo de Agua", layout="wide")

st.title("🚰 Monitoreo de Consumo de Agua")
st.markdown("**Hogar: 5 personas** | **Límite mensual recomendado: 15 m³**")

url = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"

@st.cache_data(ttl=300)
def cargar_datos():
    df = pd.read_csv(url)
    df['timestamp'] = pd.to_datetime(df['date_id'].astype(str) + ' ' + df['start_time'].astype(str), errors='coerce')
    df = df.dropna(subset=['timestamp'])
    df = df[['timestamp', 'total_liters']].sort_values('timestamp')
    df.set_index('timestamp', inplace=True)
    return df

df = cargar_datos()

# Filtro del mes actual
today = datetime.now()
first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
df_month = df[df.index >= first_day]

if not df_month.empty:
    consumo_actual = df_month['total_liters'].iloc[-1] - df_month['total_liters'].iloc[0]
    consumo_actual = max(0, consumo_actual)
    porcentaje = (consumo_actual / 15000) * 100

    st.metric("Consumo Mensual Actual", f"{consumo_actual/1000:.2f} m³", f"{porcentaje:.1f}% del límite")
    
    # Gráfica 1: Acumulado del mes
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df_month.index,
        y=(df_month['total_liters'] - df_month['total_liters'].iloc[0])/1000,
        mode='lines+markers',
        name='Consumo Acumulado',
        line=dict(color='royalblue')
    ))
    fig1.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
    fig1.update_layout(
        title="Consumo Acumulado del Mes Actual",
        xaxis_title="Fecha",
        yaxis_title="Volumen (m³)",
        height=450
    )
    st.plotly_chart(fig1, use_container_width=True)

else:
    st.warning("No hay datos suficientes para el mes actual.")

st.caption("Sistema de Monitoreo de Consumo de Agua • Render Free Tier")
