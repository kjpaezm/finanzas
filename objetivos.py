"""
objetivos.py — Módulo 3: Gestor de Objetivos a Largo Plazo.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, date

from modules import calculos, data_manager

TIPOS_OBJETIVO = [
    "Fondo de emergencia",
    "Compra futura (coche, casa…)",
    "Retiro / PEA",
    "Educación",
    "Viaje",
    "Otro",
]


def render(datos: dict) -> None:
    st.title("🎯 Objetivos a Largo Plazo")
    st.caption("Crea metas financieras y visualiza cómo el interés compuesto trabaja para ti.")

    # ── Crear nuevo objetivo ──────────────────────────────────────────────────
    with st.expander("➕ Nuevo objetivo", expanded=not datos["objetivos"]):
        with st.form("form_obj", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nombre   = col1.text_input("Nombre del objetivo", placeholder="Ej. Fondo de emergencia")
            tipo_obj = col2.selectbox("Tipo", TIPOS_OBJETIVO)

            col3, col4, col5 = st.columns(3)
            meta_obj  = col3.number_input("Meta (€)", min_value=100.0, step=100.0, format="%.2f")
            acum_ini  = col4.number_input("Ya tengo (€)", min_value=0.0, step=50.0, format="%.2f")
            fecha_lim = col5.date_input("Fecha límite", value=date(date.today().year + 5, 1, 1))

            enviado = st.form_submit_button("✅ Crear objetivo", use_container_width=True)
            if enviado:
                if not nombre.strip():
                    st.error("Ponle nombre al objetivo.")
                elif meta_obj <= 0:
                    st.error("La meta debe ser mayor que 0.")
                else:
                    data_manager.agregar_objetivo(
                        datos, nombre.strip(), meta_obj, acum_ini, str(fecha_lim), tipo_obj
                    )
                    st.success("Objetivo creado ✓")
                    st.rerun()

    # ── Lista de objetivos ────────────────────────────────────────────────────
    st.divider()
    if not datos["objetivos"]:
        st.info("📌 Aún no tienes objetivos. Crea el primero arriba.")
        return

    for i, obj in enumerate(datos["objetivos"]):
        pct = min(obj["acumulado"] / obj["meta"] * 100, 100) if obj["meta"] else 0
        estado = "✅" if pct >= 100 else ("🟡" if pct >= 50 else "🔴")

        with st.container(border=True):
            col_t, col_pct = st.columns([3, 1])
            col_t.markdown(f"### {estado} {obj['nombre']}")
            col_pct.metric("Progreso", f"{pct:.1f}%")

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("🎯 Meta",       f"{obj['meta']:,.2f} €")
            col_b.metric("💰 Acumulado",  f"{obj['acumulado']:,.2f} €")
            col_c.metric("📅 Límite",     obj["fecha_limite"])

            st.progress(pct / 100)

            # Actualizar acumulado
            with st.form(f"upd_{i}", clear_on_submit=True):
                nuevo = st.number_input("Actualizar acumulado (€)", min_value=0.0,
                                        value=float(obj["acumulado"]), step=50.0,
                                        key=f"num_{i}", format="%.2f")
                if st.form_submit_button("💾 Actualizar"):
                    data_manager.actualizar_objetivo(datos, i, nuevo)
                    st.success("Actualizado ✓")
                    st.rerun()

    # ── Proyecciones de interés compuesto ────────────────────────────────────
    st.divider()
    st.subheader("📈 Proyector de Interés Compuesto")

    col1, col2, col3, col4 = st.columns(4)
    capital_ini  = col1.number_input("Capital inicial (€)", min_value=0.0, value=1000.0, step=100.0)
    aport_mens   = col2.number_input("Aportación mensual (€)", min_value=0.0, value=200.0, step=50.0)
    tasa_proy    = col3.slider("Rentabilidad anual (%)", 1, 15, 8) / 100
    horizonte    = col4.slider("Horizonte máx. (años)", 5, 40, 20)

    # Tabla de hitos
    años_lista = [y for y in [1, 2, 3, 5, 10, 15, 20, 30, 40] if y <= horizonte]
    proyecciones = calculos.proyeccion_anual(capital_ini, aport_mens, tasa_proy, años_lista)

    df_p = pd.DataFrame(proyecciones)
    df_p["aportado"]     = [capital_ini + aport_mens * 12 * a for a in df_p["años"]]
    df_p["rendimiento"]  = (df_p["capital"] - df_p["aportado"]).round(2)
    df_p.columns = ["Años", "Capital (€)", "Aportado (€)", "Rendimiento (€)"]
    st.dataframe(df_p.style.format("{:,.2f}", subset=["Capital (€)", "Aportado (€)", "Rendimiento (€)"]),
                 use_container_width=True, hide_index=True)

    # Gráfico de acumulación a 5, 10, 20 años
    serie = calculos.serie_temporal_crecimiento(capital_ini, aport_mens, tasa_proy, horizonte * 12)
    df_s = pd.DataFrame(serie)
    df_s["aportado"] = [capital_ini + aport_mens * 12 * r["año"] for r in serie]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_s["año"], y=df_s["capital"],
                             fill="tozeroy", name="Capital proyectado",
                             line=dict(color="#3b82f6")))
    fig.add_trace(go.Scatter(x=df_s["año"], y=df_s["aportado"],
                             fill="tozeroy", name="Total aportado",
                             line=dict(color="#94a3b8", dash="dash")))
    # Hitos
    hitos_x = [5, 10, 20] if horizonte >= 20 else [h for h in [5, 10] if h <= horizonte]
    for h in hitos_x:
        match = df_s[df_s["año"] == h]
        if not match.empty:
            val = match.iloc[0]["capital"]
            fig.add_vline(x=h, line_dash="dot", line_color="orange")
            fig.add_annotation(x=h, y=val, text=f"{val:,.0f} €",
                                showarrow=True, arrowhead=2, ax=30, ay=-30)

    fig.update_layout(
        title=f"Acumulación de capital a {horizonte} años (rentabilidad {tasa_proy*100:.0f}% anual)",
        xaxis_title="Año", yaxis_title="€",
        height=400, hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Tiempo para alcanzar cada objetivo ────────────────────────────────────
    st.divider()
    st.subheader("⏱️ ¿Cuánto tiempo para cada objetivo?")
    if datos["objetivos"]:
        tasa_obj = st.slider("Tasa anual para cálculo (%)", 0, 12, 7, key="tasa_obj") / 100
        aport_calc = st.number_input("Aportación mensual prevista (€)", min_value=0.0,
                                      value=float(aport_mens), step=50.0, key="aport_obj")
        filas = []
        for obj in datos["objetivos"]:
            meses = calculos.meses_para_objetivo(
                obj["meta"], obj["acumulado"], aport_calc, tasa_obj
            )
            if meses is None:
                tiempo = "∞ (sin aportación)"
            elif meses == 0:
                tiempo = "¡Conseguido! 🎉"
            else:
                tiempo = f"{meses // 12} años {meses % 12} meses"
            filas.append({
                "Objetivo": obj["nombre"],
                "Meta (€)": f"{obj['meta']:,.2f}",
                "Acumulado (€)": f"{obj['acumulado']:,.2f}",
                "Tiempo estimado": tiempo,
            })
        st.table(pd.DataFrame(filas))
