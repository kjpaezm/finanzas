"""
Coach Financiero Integral — app.py
Punto de entrada principal de la aplicación Streamlit.
"""

import streamlit as st

st.set_page_config(
    page_title="Coach Financiero",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Importaciones de módulos propios ──────────────────────────────────────────
from modules import (
    dashboard,
    diagnostico,
    objetivos,
    inversion,
    notificaciones,
    data_manager,
)

# ── Estado global persistente en sesión ──────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = data_manager.cargar_datos()

# ── Sidebar de navegación ─────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/money-bag.png", width=64)
    st.title("Coach Financiero")
    st.caption("Tu asesor financiero personal")
    st.divider()

    pagina = st.radio(
        "Navegar a:",
        options=[
            "📊 Dashboard & Gastos",
            "🔍 Diagnóstico & Consejos",
            "🎯 Objetivos a Largo Plazo",
            "📈 Motor de Inversión PEA",
            "🔔 Notificaciones",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("v1.0 · Datos guardados localmente")

# ── Enrutado de páginas ───────────────────────────────────────────────────────
if pagina == "📊 Dashboard & Gastos":
    dashboard.render(st.session_state.data)
elif pagina == "🔍 Diagnóstico & Consejos":
    diagnostico.render(st.session_state.data)
elif pagina == "🎯 Objetivos a Largo Plazo":
    objetivos.render(st.session_state.data)
elif pagina == "📈 Motor de Inversión PEA":
    inversion.render(st.session_state.data)
elif pagina == "🔔 Notificaciones":
    notificaciones.render(st.session_state.data)
