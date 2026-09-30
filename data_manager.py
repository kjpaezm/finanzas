"""
data_manager.py — Capa de persistencia (JSON local).
Carga y guarda todos los datos del usuario en data/datos.json.
"""

import json
import os
from datetime import datetime
import streamlit as st

RUTA_DATOS = os.path.join(os.path.dirname(__file__), "..", "data", "datos.json")

DATOS_INICIALES = {
    "perfil": {
        "nombre": "Mi Coach",
        "email": "",
        "ingreso_mensual": 0.0,
        "moneda": "EUR",
    },
    "transacciones": [],       # {fecha, descripcion, categoria, tipo, importe}
    "objetivos": [],           # {nombre, meta, acumulado, fecha_limite, tipo}
    "configuracion_notif": {
        "email_destino": "",
        "dia_envio": 1,
        "activo": False,
    },
    "etf_cartera": [],         # {ticker, nombre, participaciones, precio_compra}
}


def cargar_datos() -> dict:
    """Carga datos desde disco; si no existe el archivo, devuelve datos iniciales."""
    os.makedirs(os.path.dirname(RUTA_DATOS), exist_ok=True)
    if os.path.exists(RUTA_DATOS):
        try:
            with open(RUTA_DATOS, "r", encoding="utf-8") as f:
                datos = json.load(f)
            # Fusionar claves nuevas sin borrar datos existentes
            for clave, valor in DATOS_INICIALES.items():
                datos.setdefault(clave, valor)
            return datos
        except (json.JSONDecodeError, KeyError):
            pass
    return dict(DATOS_INICIALES)


def guardar_datos(datos: dict) -> None:
    """Persiste el estado actual en disco y actualiza session_state."""
    os.makedirs(os.path.dirname(RUTA_DATOS), exist_ok=True)
    with open(RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
    st.session_state.data = datos


def agregar_transaccion(
    datos: dict,
    descripcion: str,
    categoria: str,
    tipo: str,          # "ingreso" | "gasto" | "ahorro"
    importe: float,
    fecha: str | None = None,
) -> None:
    """Añade una transacción y guarda inmediatamente."""
    tx = {
        "fecha": fecha or datetime.today().strftime("%Y-%m-%d"),
        "descripcion": descripcion,
        "categoria": categoria,
        "tipo": tipo,
        "importe": round(abs(importe), 2),
    }
    datos["transacciones"].append(tx)
    guardar_datos(datos)


def eliminar_transaccion(datos: dict, indice: int) -> None:
    if 0 <= indice < len(datos["transacciones"]):
        datos["transacciones"].pop(indice)
        guardar_datos(datos)


def agregar_objetivo(
    datos: dict,
    nombre: str,
    meta: float,
    acumulado: float,
    fecha_limite: str,
    tipo: str,
) -> None:
    obj = {
        "nombre": nombre,
        "meta": meta,
        "acumulado": acumulado,
        "fecha_limite": fecha_limite,
        "tipo": tipo,
    }
    datos["objetivos"].append(obj)
    guardar_datos(datos)


def actualizar_objetivo(datos: dict, indice: int, nuevo_acumulado: float) -> None:
    if 0 <= indice < len(datos["objetivos"]):
        datos["objetivos"][indice]["acumulado"] = round(nuevo_acumulado, 2)
        guardar_datos(datos)
