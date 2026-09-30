"""
data_manager.py — Capa de persistencia (JSON local).
Carga y guarda todos los datos del usuario en data/datos.json.
"""

import json
import uuid
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


def agregar_transaccion(datos: dict, fecha: str, tipo: str, categoria: str, monto: float, descripcion: str) -> dict:
    """Añade una nueva transacción asignándole un UUID único."""
    nueva_transaccion = {
        "id": str(uuid.uuid4()),  # Genera ID único
        "fecha": fecha,
        "tipo": tipo,
        "categoria": categoria,
        "monto": monto,
        "descripcion": descripcion
    }
    datos.setdefault("transacciones", []).append(nueva_transaccion)
    guardar_datos(datos)
    return datos

def eliminar_transaccion_por_id(datos: dict, transaccion_id: str) -> dict:
    """Elimina una transacción específica mediante su ID único."""
    datos["transacciones"] = [t for t in datos.get("transacciones", []) if t.get("id") != transaccion_id]
    guardar_datos(datos)
    return datos


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
