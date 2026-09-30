"""
notificaciones.py — Módulo 5: Notificaciones por email (SMTP) y preview del resumen.
"""

import streamlit as st
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from modules import calculos, data_manager


def render(datos: dict) -> None:
    st.title("🔔 Notificaciones Mensuales")
    st.caption(
        "Envía automáticamente un resumen financiero a tu email cada mes, "
        "con el balance, un tip de mejora y la orden exacta de compra para el PEA."
    )

    # ── Configuración SMTP ────────────────────────────────────────────────────
    st.subheader("⚙️ Configuración de Email")
    with st.expander("Configurar cuenta de envío (Gmail recomendado)", expanded=True):
        st.info(
            "Para Gmail: activa la verificación en 2 pasos y genera una "
            "**Contraseña de Aplicación** en https://myaccount.google.com/apppasswords  \n"
            "Esa contraseña (16 caracteres) es la que debes poner abajo, **no tu contraseña normal**."
        )
        col1, col2 = st.columns(2)
        smtp_user  = col1.text_input("Email remitente (Gmail)", placeholder="tumail@gmail.com",
                                     value=datos["configuracion_notif"].get("smtp_user", ""))
        smtp_pass  = col2.text_input("Contraseña de aplicación", type="password")
        email_dest = st.text_input("Email destinatario (el tuyo)",
                                   value=datos["configuracion_notif"].get("email_destino", ""))

        if st.button("💾 Guardar configuración"):
            datos["configuracion_notif"]["smtp_user"]     = smtp_user
            datos["configuracion_notif"]["smtp_pass"]     = smtp_pass  # se guarda en local
            datos["configuracion_notif"]["email_destino"] = email_dest
            data_manager.guardar_datos(datos)
            st.success("Configuración guardada localmente ✓")

    # ── Preview del resumen ───────────────────────────────────────────────────
    st.divider()
    hoy = datetime.today()
    col_a, col_m = st.columns(2)
    año_sel = col_a.selectbox("Año", list(range(hoy.year - 1, hoy.year + 1)), index=1)
    mes_sel = col_m.selectbox("Mes", list(range(1, 13)), index=hoy.month - 1,
                               format_func=lambda m: datetime(2000, m, 1).strftime("%B").capitalize())

    resumen = calculos.resumen_mes(datos["transacciones"], año_sel, mes_sel)
    hormiga = calculos.detectar_gastos_hormiga(
        calculos.filtrar_mes(datos["transacciones"], año_sel, mes_sel)
    )
    alertas = calculos.detectar_incrementos(datos["transacciones"], año_sel, mes_sel)

    # Orden ETF
    etfs = calculos.recomendar_etf("moderado")
    etf_principal = etfs[0] if etfs else None
    margen = max(resumen["balance"], 0.0)

    st.subheader("📧 Preview del Email")
    html_email = _generar_html(datos, resumen, hormiga, alertas, etf_principal, margen, año_sel, mes_sel)
    st.markdown(html_email, unsafe_allow_html=True)

    # ── Botón de envío ────────────────────────────────────────────────────────
    st.divider()
    cfg = datos["configuracion_notif"]
    if st.button("📤 Enviar resumen por email ahora", type="primary", use_container_width=True):
        smtp_user = cfg.get("smtp_user", "")
        smtp_pass = cfg.get("smtp_pass", "")
        email_dest_btn = cfg.get("email_destino", "")

        if not all([smtp_user, smtp_pass, email_dest_btn]):
            st.error("Completa la configuración de email primero.")
        else:
            exito, mensaje = _enviar_email(
                smtp_user, smtp_pass, email_dest_btn,
                f"💰 Tu Resumen Financiero — {datetime(año_sel, mes_sel, 1).strftime('%B %Y').capitalize()}",
                html_email,
            )
            if exito:
                st.success(f"✅ Email enviado a {email_dest_btn}")
            else:
                st.error(f"❌ Error al enviar: {mensaje}")

    # ── Instrucciones de notificación móvil (ntfy.sh) ─────────────────────────
    st.divider()
    st.subheader("📱 Notificación a tu Móvil (ntfy.sh — gratuito)")
    with st.expander("Cómo recibir notificaciones push en tu móvil"):
        st.markdown("""
1. Instala la app **ntfy** en tu móvil (iOS / Android) → https://ntfy.sh
2. Suscríbete a un canal único tuyo (ej. `coach-financiero-TU_NOMBRE`)
3. Ejecuta el script de abajo desde la terminal de tu ordenador el día 1 de cada mes
   (o configúralo con `cron` para que sea automático):

```bash
# Instalar httpx si no lo tienes
pip install httpx

# Enviar notificación push
python scripts/notif_movil.py \\
  --canal "coach-financiero-TU_NOMBRE" \\
  --mes {mes} --año {año}
```

4. El script enviará:
   - ✅ Balance del mes y % de ahorro
   - 💡 Tip de mejora prioritario
   - 📈 Orden de compra ETF para el PEA
        """.format(mes=mes_sel, año=año_sel))


def _generar_html(datos, resumen, hormiga, alertas, etf, margen, año, mes) -> str:
    nombre = datos["perfil"]["nombre"]
    mes_str = datetime(año, mes, 1).strftime("%B %Y").capitalize()

    tip = "Tus finanzas lucen saludables este mes. ¡Mantén el ritmo!"
    if resumen["tasa_ahorro"] < 15:
        tip = f"Tu tasa de ahorro es {resumen['tasa_ahorro']}%. Busca reducir al menos una categoría de 'Deseos' para llegar al 20%."
    elif hormiga:
        tip = f"Tienes {sum(h['total_mes'] for h in hormiga):.2f} € en gastos hormiga. Elimínalos y ponlos a trabajar en el PEA."
    elif alertas:
        tip = f"La categoría «{alertas[0]['categoria']}» subió un {alertas[0]['cambio_pct']}% este mes. Revísala."

    orden_etf = ""
    if etf and margen > 0:
        precio_ref = 50.0  # precio referencia por defecto
        orden = calculos.calcular_orden_compra(margen, precio_ref)
        if orden["participaciones"] > 0:
            orden_etf = (
                f"<p>📈 <strong>Orden de compra PEA:</strong> "
                f"Compra <strong>{orden['participaciones']} participación(es)</strong> de "
                f"<code>{etf['ticker']}</code> ({etf['nombre']}) — "
                f"TER: {etf['ter']}% — ISIN: <code>{etf['isin']}</code></p>"
            )
        else:
            orden_etf = "<p>⚠️ Margen insuficiente para comprar ETF este mes.</p>"

    return f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;
            border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px;">
  <h2 style="color: #1e40af;">💰 Resumen Financiero — {mes_str}</h2>
  <p>Hola <strong>{nombre}</strong>, aquí está tu resumen del mes:</p>
  <hr>
  <h3>📊 Balance del mes</h3>
  <table style="width:100%; border-collapse:collapse;">
    <tr><td>Ingresos</td><td style="color:#16a34a; font-weight:bold;">{resumen['ingresos']:,.2f} €</td></tr>
    <tr><td>Gastos</td><td style="color:#dc2626; font-weight:bold;">{resumen['gastos']:,.2f} €</td></tr>
    <tr><td>Ahorro / Inversión</td><td style="color:#2563eb; font-weight:bold;">{resumen['ahorro']:,.2f} €</td></tr>
    <tr style="border-top:2px solid #e2e8f0;"><td><strong>Balance neto</strong></td>
        <td style="font-weight:bold;">{resumen['balance']:,.2f} €</td></tr>
    <tr><td><strong>Tasa de ahorro</strong></td>
        <td><strong>{resumen['tasa_ahorro']}%</strong></td></tr>
  </table>
  <hr>
  <h3>💡 Tip prioritario</h3>
  <p style="background:#fef3c7; padding:12px; border-radius:8px;">{tip}</p>
  <hr>
  <h3>📈 Acción inversión PEA</h3>
  {orden_etf if orden_etf else '<p>Configura tu margen de ahorro para recibir la orden de compra.</p>'}
  <hr>
  <p style="color:#94a3b8; font-size:12px;">Generado por Coach Financiero · {datetime.today().strftime('%d/%m/%Y %H:%M')}</p>
</div>
"""


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> bool:
    """Envía un correo electrónico utilizando credenciales seguras de st.secrets."""
    try:
        # Obtener credenciales desde los secretos de Streamlit
        smtp_server = st.secrets["smtp"]["server"]
        smtp_port = st.secrets["smtp"]["port"]
        smtp_user = st.secrets["smtp"]["user"]
        smtp_password = st.secrets["smtp"]["password"]

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Error al enviar correo: {e}")
        return False
