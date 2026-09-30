"""
dashboard.py — Módulo 1: Dashboard de Presupuesto y Gastos.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from modules import calculos, data_manager

CATEGORIAS = {
    "gasto":  ["Vivienda", "Alimentación", "Transporte", "Salud", "Educación",
                "Seguros", "Ocio", "Restaurantes", "Suscripciones", "Ropa",
                "Viajes", "Hobbies", "Otros"],
    "ingreso": ["Salario", "Freelance", "Dividendos", "Alquiler", "Otros ingresos"],
    "ahorro":  ["Ahorro", "Inversión", "Fondo de emergencia", "PEA"],
}

COLORES = {"ingreso": "#22c55e", "gasto": "#ef4444", "ahorro": "#3b82f6"}


def render(datos: dict) -> None:
    st.title("📊 Dashboard de Presupuesto y Gastos")
    st.caption("Registra tus movimientos y evalúa tu salud financiera en tiempo real.")

    # ── Configuración de perfil ────────────────────────────────────────────────
    with st.expander("⚙️ Configurar ingreso mensual y nombre", expanded=not datos["perfil"]["ingreso_mensual"]):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Tu nombre", value=datos["perfil"]["nombre"])
        with col2:
            ingreso = st.number_input("Ingreso neto mensual (€)", min_value=0.0,
                                      value=float(datos["perfil"]["ingreso_mensual"]),
                                      step=50.0, format="%.2f")
        if st.button("💾 Guardar perfil"):
            datos["perfil"]["nombre"] = nombre
            datos["perfil"]["ingreso_mensual"] = ingreso
            data_manager.guardar_datos(datos)
            st.success("Perfil actualizado ✓")
            st.rerun()

    ingreso_mensual = datos["perfil"]["ingreso_mensual"]

    # ── Selección de mes ──────────────────────────────────────────────────────
    hoy = datetime.today()
    col_año, col_mes = st.columns([1, 2])
    with col_año:
        año_sel = st.selectbox("Año", list(range(hoy.year - 2, hoy.year + 1)),
                               index=2)
    with col_mes:
        mes_sel = st.selectbox("Mes", list(range(1, 13)),
                               index=hoy.month - 1,
                               format_func=lambda m: datetime(2000, m, 1).strftime("%B").capitalize())

    resumen = calculos.resumen_mes(datos["transacciones"], año_sel, mes_sel)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.divider()
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("💰 Ingresos", f"{resumen['ingresos']:,.2f} €")
    k2.metric("💸 Gastos",   f"{resumen['gastos']:,.2f} €",
              delta=f"{resumen['gastos'] - ingreso_mensual * 0.80:+.0f} € vs ideal",
              delta_color="inverse")
    k3.metric("🏦 Ahorro/Inv.", f"{resumen['ahorro']:,.2f} €",
              delta=f"{resumen['tasa_ahorro']}% del ingreso")
    k4.metric("📐 Balance",  f"{resumen['balance']:,.2f} €",
              delta_color="normal" if resumen['balance'] >= 0 else "inverse")
    k5.metric("📅 Ingreso base", f"{ingreso_mensual:,.2f} €")

    # ── Regla 50/30/20 ────────────────────────────────────────────────────────
    st.subheader("Regla 50/30/20")
    regla = calculos.regla_502030(datos["transacciones"], ingreso_mensual, año_sel, mes_sel)
    if ingreso_mensual > 0:
        categorias_regla = ["Necesidades (50%)", "Deseos (30%)", "Ahorro/Inv. (20%)"]
        reales    = [regla["necesidades"]["real"], regla["deseos"]["real"], regla["ahorro_inv"]["real"]]
        ideales   = [regla["necesidades"]["ideal"], regla["deseos"]["ideal"], regla["ahorro_inv"]["ideal"]]
        pcts_real = [regla["necesidades"]["pct"], regla["deseos"]["pct"], regla["ahorro_inv"]["pct"]]

        col_n, col_d, col_a = st.columns(3)
        for col, cat, real, ideal, pct in zip(
            [col_n, col_d, col_a], categorias_regla, reales, ideales, pcts_real
        ):
            salud = "✅" if real <= ideal else "⚠️"
            col.metric(f"{salud} {cat}", f"{real:,.2f} €", f"{pct}% | ideal: {ideal:,.0f} €",
                       delta_color="off")
            col.progress(min(pct / 100, 1.0))
    else:
        st.info("Configura tu ingreso mensual arriba para ver la regla 50/30/20.")

    # ── Gráficos ──────────────────────────────────────────────────────────────
    txs_mes = calculos.filtrar_mes(datos["transacciones"], año_sel, mes_sel)
    st.divider()
    if txs_mes:
        col_pie, col_bar = st.columns(2)
        df = pd.DataFrame(txs_mes)

        with col_pie:
            st.subheader("Gastos por categoría")
            df_gastos = df[df["tipo"] == "gasto"]
            if not df_gastos.empty:
                fig = px.pie(df_gastos, values="importe", names="categoria",
                             hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin gastos este mes.")

        with col_bar:
            st.subheader("Ingresos vs Gastos vs Ahorro")
            fig2 = go.Figure(data=[
                go.Bar(name="Ingresos", x=["Este mes"], y=[resumen["ingresos"]], marker_color="#22c55e"),
                go.Bar(name="Gastos",   x=["Este mes"], y=[resumen["gastos"]],   marker_color="#ef4444"),
                go.Bar(name="Ahorro",   x=["Este mes"], y=[resumen["ahorro"]],   marker_color="#3b82f6"),
            ])
            fig2.update_layout(barmode="group", height=300, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📭 Aún no hay transacciones este mes. Añade tu primera a continuación.")

    # ── Formulario de registro ────────────────────────────────────────────────
    st.divider()
    st.subheader("➕ Registrar transacción")
    with st.form("form_tx", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        tipo_tx  = c1.selectbox("Tipo", ["gasto", "ingreso", "ahorro"])
        importe  = c2.number_input("Importe (€)", min_value=0.01, step=0.01, format="%.2f")
        fecha_tx = c3.date_input("Fecha", value=datetime.today())

        c4, c5 = st.columns(2)
        categoria = c4.selectbox("Categoría", CATEGORIAS[tipo_tx])
        descripcion = c5.text_input("Descripción", placeholder="Ej. Supermercado Carrefour")

        enviado = st.form_submit_button("✅ Añadir transacción", use_container_width=True)
        if enviado:
            if not descripcion.strip():
                st.error("Añade una descripción.")
            else:
                data_manager.agregar_transaccion(
                    datos, descripcion.strip(), categoria, tipo_tx,
                    importe, str(fecha_tx)
                )
                st.success(f"✓ {tipo_tx.capitalize()} de {importe:.2f} € registrado.")
                st.rerun()

    # ── Tabla de transacciones ────────────────────────────────────────────────
    st.divider()
    st.subheader(f"📋 Transacciones de {datetime(año_sel, mes_sel, 1).strftime('%B %Y').capitalize()}")
    if txs_mes:
        df_show = pd.DataFrame(txs_mes)
        df_show["importe_fmt"] = df_show.apply(
            lambda r: f"{'−' if r['tipo']=='gasto' else '+'}{r['importe']:.2f} €", axis=1
        )
        df_show["color"] = df_show["tipo"].map(COLORES)
        st.dataframe(
            df_show[["fecha", "descripcion", "categoria", "tipo", "importe_fmt"]].rename(
                columns={"fecha":"Fecha","descripcion":"Descripción","categoria":"Categoría",
                         "tipo":"Tipo","importe_fmt":"Importe"}
            ),
            use_container_width=True, hide_index=True,
        )

        # Eliminar transacción
        with st.expander("🗑️ Eliminar transacción"):
            total_tx = datos["transacciones"]
            opciones = {
                f"[{i}] {t['fecha']} | {t['descripcion']} | {t['importe']} €": i
                for i, t in enumerate(total_tx)
                if calculos.filtrar_mes([t], año_sel, mes_sel)
            }
            if opciones:
                sel = st.selectbox("Selecciona", list(opciones.keys()))
                if st.button("Eliminar", type="primary"):
                    data_manager.eliminar_transaccion(datos, opciones[sel])
                    st.success("Eliminada ✓")
                    st.rerun()
