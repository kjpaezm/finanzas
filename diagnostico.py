"""
diagnostico.py — Módulo 2: Motor de Diagnóstico y Consejos Automáticos.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime

from modules import calculos


def render(datos: dict) -> None:
    st.title("🔍 Diagnóstico & Consejos Automáticos")
    st.caption("Detecta gastos hormiga, incrementos anormales y calcula el Efecto Mariposa de cada euro ahorrado.")

    hoy = datetime.today()
    col_a, col_m = st.columns(2)
    año_sel = col_a.selectbox("Año", list(range(hoy.year - 2, hoy.year + 1)), index=2, key="diag_año")
    mes_sel = col_m.selectbox("Mes", list(range(1, 13)), index=hoy.month - 1, key="diag_mes",
                               format_func=lambda m: datetime(2000, m, 1).strftime("%B").capitalize())

    ingreso = datos["perfil"]["ingreso_mensual"] or 1

    # ── Gastos Hormiga ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🐜 Gastos Hormiga")
    st.caption("Pequeños gastos (≤ 5 €) que, sumados, erosionan tu ahorro.")
    hormiga = calculos.detectar_gastos_hormiga(
        calculos.filtrar_mes(datos["transacciones"], año_sel, mes_sel)
    )
    if hormiga:
        df_h = pd.DataFrame(hormiga)
        df_h["impacto_anual"] = (df_h["total_mes"] * 12).round(2)
        df_h.columns = ["Categoría", "Total mes (€)", "Impacto anual (€)"]
        st.dataframe(df_h, use_container_width=True, hide_index=True)

        peor = hormiga[0]
        efecto = calculos.efecto_mariposa(peor["total_mes"], tasa_anual=0.08, años=20)
        st.warning(
            f"🦋 **Efecto Mariposa:** Si eliminas los gastos hormiga en «{peor['categoria']}» "
            f"({peor['total_mes']:.2f} €/mes) e inviertes ese dinero en tu PEA, "
            f"en 20 años tendrías **{efecto['valor_futuro']:,.0f} €** "
            f"(aportaste {efecto['aportado']:,.0f} € y el mercado generó {efecto['rendimiento']:,.0f} €)."
        )
    else:
        st.success("✅ No se detectan gastos hormiga significativos este mes.")

    # ── Incrementos Anormales ────────────────────────────────────────────────
    st.divider()
    st.subheader("📈 Incrementos Anormales vs. Mes Anterior")
    alertas = calculos.detectar_incrementos(datos["transacciones"], año_sel, mes_sel)
    if alertas:
        for a in alertas:
            st.error(
                f"⚠️ **{a['categoria']}** subió un **{a['cambio_pct']}%** "
                f"({a['anterior']:.2f} € → {a['actual']:.2f} €)"
            )
        df_a = pd.DataFrame(alertas)
        fig = px.bar(df_a, x="categoria", y=["anterior", "actual"],
                     barmode="group", labels={"value": "€", "categoria": "Categoría", "variable": ""},
                     color_discrete_map={"anterior": "#94a3b8", "actual": "#ef4444"},
                     title="Comparativa mes actual vs anterior")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ Ninguna categoría presenta incremento anormal este mes.")

    # ── Efecto Mariposa Interactivo ───────────────────────────────────────────
    st.divider()
    st.subheader("🦋 Calculadora Efecto Mariposa")
    st.caption("Descubre cuánto vale cada euro que dejas de gastar hoy si lo inviertes en el PEA.")

    col1, col2, col3 = st.columns(3)
    gasto_reducir = col1.number_input("Gasto mensual a reducir (€)", min_value=1.0,
                                       value=50.0, step=5.0)
    tasa_anual    = col2.slider("Rentabilidad anual esperada (%)", 4, 12, 8) / 100
    años_proy     = col3.slider("Horizonte (años)", 5, 30, 20)

    efecto_calc = calculos.efecto_mariposa(gasto_reducir, tasa_anual, años_proy)
    e1, e2, e3 = st.columns(3)
    e1.metric("💰 Valor futuro en PEA", f"{efecto_calc['valor_futuro']:,.0f} €")
    e2.metric("📥 Total aportado",      f"{efecto_calc['aportado']:,.0f} €")
    e3.metric("📈 Rentabilidad obtenida", f"{efecto_calc['rendimiento']:,.0f} €")

    # Gráfico de evolución
    serie = calculos.serie_temporal_crecimiento(0, gasto_reducir, tasa_anual, años_proy * 12)
    df_s = pd.DataFrame(serie)
    aportado_serie = [gasto_reducir * 12 * a["año"] for a in serie]
    df_s["aportado"] = aportado_serie
    fig2 = px.area(df_s, x="año", y=["capital", "aportado"],
                   labels={"value": "€", "año": "Año", "variable": ""},
                   color_discrete_map={"capital": "#3b82f6", "aportado": "#94a3b8"},
                   title=f"Crecimiento de {gasto_reducir:.0f} €/mes durante {años_proy} años al {tasa_anual*100:.0f}%")
    fig2.update_layout(height=320)
    st.plotly_chart(fig2, use_container_width=True)

    # ── Tips Personalizados ────────────────────────────────────────────────────
    st.divider()
    st.subheader("💡 Tips Personalizados")
    resumen = calculos.resumen_mes(datos["transacciones"], año_sel, mes_sel)
    tips = _generar_tips(resumen, ingreso, hormiga, alertas)
    for i, tip in enumerate(tips, 1):
        st.info(f"**Tip {i}:** {tip}")


def _generar_tips(resumen: dict, ingreso: float, hormiga: list, alertas: list) -> list:
    tips = []
    tasa = resumen["tasa_ahorro"]
    if tasa < 10:
        tips.append(f"Tu tasa de ahorro es {tasa}%. El objetivo mínimo saludable es 20%. "
                    "Revisa tus gastos variables para liberar margen.")
    if tasa >= 20:
        tips.append(f"¡Excelente! Ahorras un {tasa}% de tus ingresos. "
                    "Considera automatizar la aportación al PEA el día 1 de cada mes (método pay yourself first).")
    if hormiga:
        total_hormiga = sum(h["total_mes"] for h in hormiga)
        tips.append(f"Tienes {total_hormiga:.2f} € en gastos hormiga este mes. "
                    "Eliminarlos equivale a subirse el sueldo sin cambiar tu trabajo.")
    if alertas:
        cat = alertas[0]["categoria"]
        tips.append(f"La categoría «{cat}» ha disparado su gasto este mes. "
                    "Revisa si fue un gasto puntual o empieza a ser un patrón.")
    if resumen["balance"] < 0:
        tips.append("⚠️ Tu balance mensual es negativo: gastas más de lo que ingresas. "
                    "Prioriza eliminar gastos de la categoría 'Deseos' hasta equilibrarlo.")
    if not tips:
        tips.append("Tus finanzas están en buen estado este mes. ¡Mantén el rumbo!")
    return tips
