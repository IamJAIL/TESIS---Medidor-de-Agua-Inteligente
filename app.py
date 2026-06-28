import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Monitoreo de Agua", layout="wide")

st.title("🚰 Monitoreo de Consumo de Agua")
st.markdown("**Hogar: 5 personas** | **Límite mensual: 15 m³**")

# ==================== DATOS DE EJEMPLO ====================
# Generamos datos de ejemplo para todo el mes (junio 2026)
np.random.seed(42)
days = list(range(1, 29))  # Hasta el día 28
daily_consumption = np.random.uniform(0.3, 0.8, size=len(days))  # Entre 0.3 y 0.8 m³ por día
cumulative = np.cumsum(daily_consumption)

data = pd.DataFrame({
    'Día': days,
    'Consumo Diario (m³)': daily_consumption,
    'Consumo Acumulado (m³)': cumulative
})

total_consumption = cumulative[-1]

# ==================== DASHBOARD ====================
col1, col2 = st.columns(2)
col1.metric("Consumo Mensual Actual", f"{total_consumption:.2f} m³")
col2.metric("Porcentaje del Límite", f"{(total_consumption/15)*100:.1f}%", 
            delta="Dentro del límite" if total_consumption < 15 else "Cerca del límite")

# Gráfica 1: Consumo Acumulado del Mes
fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=data['Día'],
    y=data['Consumo Acumulado (m³)'],
    mode='lines+markers',
    name='Consumo Acumulado',
    line=dict(color='royalblue'),
    marker=dict(size=6)
))
fig1.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
fig1.update_layout(
    title="Consumo Acumulado del Mes (Datos de Ejemplo)",
    xaxis_title="Día del mes",
    yaxis_title="Volumen acumulado (m³)",
    height=450
)
st.plotly_chart(fig1, use_container_width=True)

# Resumen
st.subheader("Resumen del Mes")
st.dataframe(data.style.format({"Consumo Diario (m³)": "{:.2f}", "Consumo Acumulado (m³)": "{:.2f}"}), 
             use_container_width=True)

st.success("✅ El consumo se encuentra dentro del límite mensual recomendado.")

st.caption("Datos de ejemplo generados • Monitoreo de Consumo de Agua")
