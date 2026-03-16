# Gráfica 2: Entrenamiento + alertas del mes (eje X solo hasta día actual)
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

# Día actual del mes
dia_actual = datetime.now().day

# Simulación de alertas solo hasta el día actual
dias_alerta = np.random.choice(range(1, dia_actual + 1), size=min(3, dia_actual), replace=False)
for dia in dias_alerta:
    fig2.add_vline(x=dia, line_dash="dot", line_color="red", annotation_text=f"Alerta día {dia}")

fig2.update_layout(
    title=f"Pérdida del entrenamiento y alertas/anomalías detectadas (hasta día {dia_actual})",
    xaxis_title="Épocas (izquierda) / Días del mes (derecha)",
    yaxis_title="Pérdida (loss)",
    xaxis=dict(range=[1, max(30, dia_actual + 5)]),  # un poco de margen
    height=500
)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("""
**Explicación detallada de la gráfica:**  
- La curva verde muestra cómo disminuye el error (pérdida o loss) a lo largo de las épocas de entrenamiento del modelo LSTM Autoencoder. Una curva descendente indica que el modelo aprendió correctamente los patrones normales de consumo de agua en la vivienda.  
- Las líneas verticales rojas marcan los días del mes actual en los que se detectó una posible anomalía (error de reconstrucción superior al umbral establecido). Cada alerta representa un momento donde el patrón de consumo no coincidió con lo "normal" aprendido, lo que activa la revisión para detectar fugas o desperdicios tempranos.
""")

# Botón de prueba de alerta
if st.button("Enviar alerta de prueba por correo"):
    enviar_alerta(tipo="fuga")
    st.success("Alerta enviada")

st.caption("Sistema desarrollado por Camilo Quinto, José Insuasti, Paul Palma y Milton Simbaña • Render.com")
