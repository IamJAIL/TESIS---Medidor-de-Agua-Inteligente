import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Water Consumption Monitoring", layout="wide")

st.title("🚰 Water Consumption Monitoring")
st.markdown("**Household: 5 people** | **Monthly Limit: 15 m³**")

# ==================== EXAMPLE DATA ====================
np.random.seed(42)
days = list(range(1, 29))  # Up to day 28
daily_consumption = np.random.uniform(0.3, 0.75, size=len(days))  # Safe values
cumulative = np.cumsum(daily_consumption)

data = pd.DataFrame({
    'Day': days,
    'Daily Consumption (m³)': daily_consumption,
    'Cumulative Consumption (m³)': cumulative
})

total_consumption = cumulative[-1]

# ==================== DASHBOARD ====================
col1, col2 = st.columns(2)
col1.metric("Current Monthly Consumption", f"{total_consumption:.2f} m³")
col2.metric("Percentage of Limit", f"{(total_consumption/15)*100:.1f}%", 
            delta="Within limit" if total_consumption < 15 else "Close to limit")

# Graph 1: Cumulative Consumption
fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=data['Day'],
    y=data['Cumulative Consumption (m³)'],
    mode='lines+markers',
    name='Cumulative Consumption',
    line=dict(color='royalblue'),
    marker=dict(size=6)
))
fig1.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="15 m³ Limit")
fig1.update_layout(
    title="Monthly Cumulative Water Consumption",
    xaxis_title="Day of the Month",
    yaxis_title="Cumulative Volume (m³)",
    height=450
)
st.plotly_chart(fig1, use_container_width=True)

# Summary Table
st.subheader("Monthly Summary")
st.dataframe(data.style.format({
    "Daily Consumption (m³)": "{:.2f}", 
    "Cumulative Consumption (m³)": "{:.2f}"
}), use_container_width=True)

st.success("✅ The consumption is within the recommended monthly limit.")

st.caption("Example Data • Water Consumption Monitoring System")
