"""
inversion.py — Módulo 4: Motor de Inversión y Recomendación PEA (Trade Republic).
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from modules import calculos, data_manager


def render(datos: dict) -> None:
    st.title("📈 Motor de Inversión PEA — Trade Republic")
    st.caption(
        "Selección de ETFs elegibles en PEA, calculadora de compra mensual "
        "y seguimiento de tu cartera."
    )

    # ── Perfil de riesgo ──────────────────────────────────────────────────────
    perfil = st.radio(
        "Tu perfil de riesgo:",
        ["conservador", "moderado", "agresivo"],
        index=1,
        horizontal=True,
        help="Conservador: solo MSCI World. Agresivo: incluye S&P 500 y más concentración geográfica.",
    )

    # ── Tabla de ETFs elegibles ───────────────────────────────────────────────
    st.divider()
    st.subheader("📋 ETFs Elegibles PEA — Filtrados (TER < 0.30%)")

    etfs = calculos.recomendar_etf(perfil)
    df_etf = pd.DataFrame([{
        "Ticker":       e["ticker"],
        "Nombre":       e["nombre"],
        "Índice":       e["indice"],
        "TER (%)":      e["ter"],
        "Acumulación":  "✅ Sí" if e["acumulación"] else "❌ No",
        "ISIN":         e["isin"],
    } for e in etfs])
    st.dataframe(df_etf, use_container_width=True, hide_index=True)

    # Tarjetas de detalle
    st.subheader("🔎 Descripción de cada ETF")
    cols = st.columns(len(etfs))
    for col, etf in zip(cols, etfs):
        with col:
            with st.container(border=True):
                st.markdown(f"#### {etf['ticker']}")
                st.caption(etf["nombre"])
                st.markdown(f"**TER:** `{etf['ter']}%`")
                st.markdown(f"**Índice:** {etf['indice']}")
                st.markdown(f"**ISIN:** `{etf['isin']}`")
                st.info(etf["descripcion"])

    # ── Calculadora de Orden de Compra ────────────────────────────────────────
    st.divider()
    st.subheader("🛒 Calculadora de Orden de Compra Mensual")
    st.caption(
        "Trade Republic aplica **1€ de comisión por orden**. "
        "La calculadora descuenta este coste automáticamente."
    )

    hoy = datetime.today()
    resumen = calculos.resumen_mes(datos["transacciones"], hoy.year, hoy.month)
    ingreso_base = datos["perfil"]["ingreso_mensual"]
    margen_defecto = max(resumen["balance"], 0.0) or ingreso_base * 0.20

    col1, col2 = st.columns(2)
    margen_ahorro = col1.number_input(
        "Margen de ahorro disponible este mes (€)",
        min_value=0.0, value=round(margen_defecto, 2), step=10.0
    )
    etf_sel_ticker = col2.selectbox(
        "ETF a comprar",
        options=[e["ticker"] for e in etfs],
        format_func=lambda t: next(e["nombre"] for e in etfs if e["ticker"] == t)
    )
    precio_etf = st.number_input(
        f"Precio actual de {etf_sel_ticker} (€) — consulta en Trade Republic",
        min_value=0.01, value=50.0, step=0.5, format="%.2f"
    )

    orden = calculos.calcular_orden_compra(margen_ahorro, precio_etf)

    st.divider()
    if orden["participaciones"] > 0:
        o1, o2, o3 = st.columns(3)
        o1.metric("🛒 Participaciones a comprar", f"{orden['participaciones']} uds.")
        o2.metric("💶 Importe total (con comisión)", f"{orden['importe']:.2f} €")
        o3.metric("💰 Sobrante en cuenta", f"{orden['restante']:.2f} €")

        etf_info = next(e for e in etfs if e["ticker"] == etf_sel_ticker)
        st.success(
            f"📌 **ORDEN EXACTA PARA TRADE REPUBLIC:**  \n"
            f"Comprar **{orden['participaciones']} participación(es)** de `{etf_sel_ticker}` "
            f"({etf_info['nombre']})  \n"
            f"• ISIN: `{etf_info['isin']}`  \n"
            f"• Precio ref.: **{precio_etf:.2f} €/ud.**  \n"
            f"• Coste total estimado: **{orden['importe']:.2f} €** (incluye 1€ comisión TR)  \n"
            f"• Sobrante para próximo mes: **{orden['restante']:.2f} €**"
        )

        # Botón para registrar la compra en cartera
        if st.button("✅ Registrar esta compra en mi cartera"):
            _registrar_compra(datos, etf_sel_ticker, etf_info, orden["participaciones"], precio_etf)
            st.success("Compra registrada en tu cartera ✓")
            st.rerun()
    else:
        st.warning(
            "⚠️ El margen de ahorro disponible no es suficiente para comprar "
            f"1 participación de {etf_sel_ticker} a {precio_etf:.2f} € (+ 1€ comisión)."
        )

    # ── Seguimiento de cartera ────────────────────────────────────────────────
    st.divider()
    st.subheader("💼 Mi Cartera PEA")
    if datos["etf_cartera"]:
        df_c = pd.DataFrame(datos["etf_cartera"])
        df_c["valor_compra"] = (df_c["participaciones"] * df_c["precio_compra"]).round(2)
        st.dataframe(
            df_c.rename(columns={
                "ticker": "Ticker",
                "nombre": "Nombre",
                "participaciones": "Participaciones",
                "precio_compra": "Precio medio (€)",
                "valor_compra": "Valor invertido (€)"
            }),
            use_container_width=True, hide_index=True
        )
        total = df_c["valor_compra"].sum()
        st.metric("💰 Total invertido en PEA", f"{total:,.2f} €")

        # Gráfico de distribución
        fig_pie = px.pie(df_c, values="valor_compra", names="ticker",
                         title="Distribución de cartera PEA",
                         color_discrete_sequence=px.colors.qualitative.Set3)
        fig_pie.update_layout(height=300)
        st.plotly_chart(fig_pie, use_container_width=True)

        if st.button("🗑️ Limpiar cartera"):
            datos["etf_cartera"] = []
            data_manager.guardar_datos(datos)
            st.rerun()
    else:
        st.info("📭 Aún no has registrado ninguna compra. Usa la calculadora de arriba.")

    # ── Proyección de la cartera ──────────────────────────────────────────────
    st.divider()
    st.subheader("🚀 Proyección de tu PEA a largo plazo")
    total_invertido = sum(
        p["participaciones"] * p["precio_compra"] for p in datos["etf_cartera"]
    ) if datos["etf_cartera"] else 0

    cap_ini_pea  = st.number_input("Capital actual PEA (€)", min_value=0.0,
                                    value=round(total_invertido, 2), step=100.0)
    aport_pea    = st.number_input("Aportación mensual PEA (€)", min_value=0.0,
                                    value=round(margen_ahorro, 2), step=50.0)
    tasa_pea     = st.slider("Rentabilidad anual esperada (%) — hist. MSCI World ~8%", 4, 12, 8) / 100

    serie_pea = calculos.serie_temporal_crecimiento(cap_ini_pea, aport_pea, tasa_pea, 20 * 12)
    df_pea = pd.DataFrame(serie_pea)
    df_pea["aportado"] = [cap_ini_pea + aport_pea * 12 * r["año"] for r in serie_pea]

    fig_pea = go.Figure()
    fig_pea.add_trace(go.Scatter(x=df_pea["año"], y=df_pea["capital"],
                                  fill="tozeroy", name="Capital PEA",
                                  line=dict(color="#22c55e")))
    fig_pea.add_trace(go.Scatter(x=df_pea["año"], y=df_pea["aportado"],
                                  fill="tozeroy", name="Aportado",
                                  line=dict(color="#94a3b8", dash="dash")))
    fig_pea.update_layout(
        title=f"Proyección PEA a 20 años — rentabilidad {tasa_pea*100:.0f}%",
        xaxis_title="Año", yaxis_title="€",
        height=380, hovermode="x unified"
    )
    st.plotly_chart(fig_pea, use_container_width=True)

    if not df_pea.empty:
        val_20 = df_pea.iloc[-1]["capital"]
        aport_20 = df_pea.iloc[-1]["aportado"]
        st.info(
            f"📊 En 20 años habrás aportado **{aport_20:,.0f} €** y tu PEA valdría "
            f"aprox. **{val_20:,.0f} €** — "
            f"el mercado habría generado **{val_20 - aport_20:,.0f} €** de rentabilidad."
        )


def _registrar_compra(datos, ticker, etf_info, participaciones, precio):
    """Añade o acumula la compra en la cartera."""
    for pos in datos["etf_cartera"]:
        if pos["ticker"] == ticker:
            total_parts = pos["participaciones"] + participaciones
            # Precio medio ponderado
            pos["precio_compra"] = round(
                (pos["participaciones"] * pos["precio_compra"] + participaciones * precio)
                / total_parts, 4
            )
            pos["participaciones"] = total_parts
            data_manager.guardar_datos(datos)
            return
    datos["etf_cartera"].append({
        "ticker": ticker,
        "nombre": etf_info["nombre"],
        "participaciones": participaciones,
        "precio_compra": round(precio, 4),
    })
    data_manager.guardar_datos(datos)
