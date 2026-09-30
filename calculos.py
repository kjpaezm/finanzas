"""
calculos.py — Motor de cálculo financiero.
Todas las funciones son puras (sin estado), fáciles de testear.
"""

from __future__ import annotations
import math
from datetime import datetime, date
from typing import List, Dict, Tuple


# ── 1. Resumen mensual ────────────────────────────────────────────────────────

def filtrar_mes(transacciones: list, año: int, mes: int) -> list:
    """Devuelve sólo las transacciones del mes/año indicado."""
    return [
        tx for tx in transacciones
        if datetime.strptime(tx["fecha"], "%Y-%m-%d").year == año
        and datetime.strptime(tx["fecha"], "%Y-%m-%d").month == mes
    ]


def resumen_mes(transacciones: list, año: int, mes: int) -> Dict:
    txs = filtrar_mes(transacciones, año, mes)
    ingresos = sum(t["importe"] for t in txs if t["tipo"] == "ingreso")
    gastos   = sum(t["importe"] for t in txs if t["tipo"] == "gasto")
    ahorro   = sum(t["importe"] for t in txs if t["tipo"] == "ahorro")
    return {
        "ingresos": round(ingresos, 2),
        "gastos":   round(gastos, 2),
        "ahorro":   round(ahorro, 2),
        "balance":  round(ingresos - gastos - ahorro, 2),
        "tasa_ahorro": round((ahorro / ingresos * 100) if ingresos else 0, 1),
    }


# ── 2. Regla 50/30/20 ────────────────────────────────────────────────────────

CATEGORIAS_50 = {
    "Vivienda", "Alimentación", "Transporte", "Salud", "Educación", "Seguros"
}
CATEGORIAS_30 = {
    "Ocio", "Restaurantes", "Suscripciones", "Ropa", "Viajes", "Hobbies"
}
CATEGORIAS_20 = {
    "Ahorro", "Inversión", "Fondo de emergencia", "PEA"
}


def regla_502030(transacciones: list, ingresos: float, año: int, mes: int) -> Dict:
    txs = filtrar_mes(transacciones, año, mes)
    gastos_tx = [t for t in txs if t["tipo"] in ("gasto", "ahorro")]

    necesidades  = sum(t["importe"] for t in gastos_tx if t["categoria"] in CATEGORIAS_50)
    deseos       = sum(t["importe"] for t in gastos_tx if t["categoria"] in CATEGORIAS_30)
    ahorro_inv   = sum(t["importe"] for t in gastos_tx if t["categoria"] in CATEGORIAS_20)

    base = ingresos if ingresos > 0 else 1
    return {
        "necesidades":  {"real": round(necesidades, 2),  "ideal": round(base * 0.50, 2), "pct": round(necesidades / base * 100, 1)},
        "deseos":       {"real": round(deseos, 2),        "ideal": round(base * 0.30, 2), "pct": round(deseos / base * 100, 1)},
        "ahorro_inv":   {"real": round(ahorro_inv, 2),    "ideal": round(base * 0.20, 2), "pct": round(ahorro_inv / base * 100, 1)},
    }


# ── 3. Diagnóstico de gastos hormiga ─────────────────────────────────────────

def detectar_gastos_hormiga(transacciones: list, umbral_diario: float = 5.0) -> List[Dict]:
    """
    Agrupa gastos pequeños (≤ umbral_diario) y calcula su impacto mensual.
    Devuelve lista de categorías con gasto hormiga significativo.
    """
    pequeños = [t for t in transacciones if t["tipo"] == "gasto" and t["importe"] <= umbral_diario]
    por_categoria: Dict[str, float] = {}
    for t in pequeños:
        por_categoria[t["categoria"]] = por_categoria.get(t["categoria"], 0) + t["importe"]

    resultado = []
    for cat, total in por_categoria.items():
        if total >= 20:  # sólo si supera 20€/mes acumulados
            resultado.append({"categoria": cat, "total_mes": round(total, 2)})
    return sorted(resultado, key=lambda x: x["total_mes"], reverse=True)


def detectar_incrementos(transacciones: list, año: int, mes: int) -> List[Dict]:
    """Compara el mes actual con el anterior y detecta categorías con incremento > 20%."""
    mes_ant = mes - 1 if mes > 1 else 12
    año_ant  = año if mes > 1 else año - 1

    actual   = {t["categoria"]: 0.0 for t in transacciones if t["tipo"] == "gasto"}
    anterior = dict(actual)

    for t in transacciones:
        if t["tipo"] != "gasto":
            continue
        d = datetime.strptime(t["fecha"], "%Y-%m-%d")
        if d.year == año and d.month == mes:
            actual[t["categoria"]] = actual.get(t["categoria"], 0) + t["importe"]
        elif d.year == año_ant and d.month == mes_ant:
            anterior[t["categoria"]] = anterior.get(t["categoria"], 0) + t["importe"]

    alertas = []
    for cat in actual:
        prev = anterior.get(cat, 0)
        curr = actual[cat]
        if prev > 0 and curr > 0:
            cambio = (curr - prev) / prev * 100
            if cambio > 20:
                alertas.append({"categoria": cat, "anterior": round(prev, 2),
                                 "actual": round(curr, 2), "cambio_pct": round(cambio, 1)})
    return sorted(alertas, key=lambda x: x["cambio_pct"], reverse=True)


# ── 4. Efecto Mariposa ────────────────────────────────────────────────────────

def efecto_mariposa(ahorro_mensual: float, tasa_anual: float = 0.08, años: int = 20) -> Dict:
    """
    Proyecta el valor futuro de un ahorro mensual invertido en PEA.
    Usa la fórmula de anualidad: FV = PMT × [((1+r)^n − 1) / r]
    """
    r = tasa_anual / 12
    n = años * 12
    if r == 0:
        fv = ahorro_mensual * n
    else:
        fv = ahorro_mensual * ((math.pow(1 + r, n) - 1) / r)
    aportado = ahorro_mensual * n
    return {
        "valor_futuro": round(fv, 2),
        "aportado":     round(aportado, 2),
        "rendimiento":  round(fv - aportado, 2),
    }


# ── 5. Proyección de interés compuesto para objetivos ────────────────────────

def proyeccion_anual(
    capital_inicial: float,
    aportacion_mensual: float,
    tasa_anual: float,
    años_lista: List[int],
) -> List[Dict]:
    """Devuelve el capital proyectado para cada horizonte en años_lista."""
    resultados = []
    for años in años_lista:
        r = tasa_anual / 12
        n = años * 12
        if r == 0:
            fv = capital_inicial + aportacion_mensual * n
        else:
            fv = capital_inicial * math.pow(1 + r, n) + \
                 aportacion_mensual * ((math.pow(1 + r, n) - 1) / r)
        resultados.append({"años": años, "capital": round(fv, 2)})
    return resultados


def serie_temporal_crecimiento(
    capital_inicial: float,
    aportacion_mensual: float,
    tasa_anual: float,
    meses_total: int,
) -> List[Dict]:
    """Genera serie mes a mes para el gráfico de acumulación."""
    r = tasa_anual / 12
    serie = []
    capital = capital_inicial
    for m in range(1, meses_total + 1):
        capital = capital * (1 + r) + aportacion_mensual
        if m % 12 == 0:
            serie.append({"año": m // 12, "capital": round(capital, 2)})
    return serie


# ── 6. Tiempo para alcanzar un objetivo ──────────────────────────────────────

def meses_para_objetivo(meta: float, acumulado: float, aportacion: float, tasa_anual: float) -> int | None:
    """Calcula cuántos meses faltan para llegar a la meta."""
    if aportacion <= 0:
        return None
    r = tasa_anual / 12
    pendiente = meta - acumulado
    if pendiente <= 0:
        return 0
    if r == 0:
        return math.ceil(pendiente / aportacion)
    # Resuelve: pendiente = PMT × [((1+r)^n − 1) / r]  →  n = log(1 + pendiente×r/PMT) / log(1+r)
    try:
        n = math.log(1 + pendiente * r / aportacion) / math.log(1 + r)
        return math.ceil(n)
    except (ValueError, ZeroDivisionError):
        return None


# ── 7. Recomendación ETF PEA ─────────────────────────────────────────────────

ETF_PEA = [
    {
        "ticker": "WPEA",
        "nombre": "Amundi MSCI World SRI PAB – UCITS ETF Acc",
        "isin": "LU2572257124",
        "ter": 0.18,
        "indice": "MSCI World SRI",
        "capitalización": "Grande",
        "acumulación": True,
        "descripcion": "Exposición global con filtro ESG. Réplica física. Ideal para largo plazo.",
    },
    {
        "ticker": "CW8",
        "nombre": "Amundi MSCI World UCITS ETF – EUR Acc",
        "isin": "LU1681043599",
        "ter": 0.12,
        "indice": "MSCI World",
        "capitalización": "Grande",
        "acumulación": True,
        "descripcion": "El más barato y diversificado para PEA. Réplica sintética (swap). Referencia de mercado global.",
    },
    {
        "ticker": "ESE",
        "nombre": "BNP Paribas Easy S&P 500 UCITS ETF EUR Acc",
        "isin": "LU0496786574",
        "ter": 0.15,
        "indice": "S&P 500",
        "capitalización": "Grande",
        "acumulación": True,
        "descripcion": "Concentrado en EE.UU., máxima rentabilidad histórica. Complementa bien con WPEA.",
    },
    {
        "ticker": "PUST",
        "nombre": "Lyxor PEA S&P 500 UCITS ETF – Acc",
        "isin": "FR0011871128",
        "ter": 0.15,
        "indice": "S&P 500",
        "capitalización": "Grande",
        "acumulación": True,
        "descripcion": "Alternativa a ESE con alta liquidez en Euronext París.",
    },
]


def recomendar_etf(perfil_riesgo: str = "moderado") -> List[Dict]:
    """
    Filtra y ordena ETFs por TER y adecuación al perfil.
    Perfil: conservador | moderado | agresivo
    """
    elegibles = [e for e in ETF_PEA if e["ter"] < 0.30]
    if perfil_riesgo == "conservador":
        elegibles = [e for e in elegibles if "World" in e["indice"]]
    elif perfil_riesgo == "agresivo":
        pass  # todos
    return sorted(elegibles, key=lambda x: x["ter"])


def calcular_orden_compra(
    margen_ahorro: float,
    precio_etf: float,
    comision: float = 1.0,
) -> Dict:
    """
    Calcula cuántas participaciones comprar con el margen disponible.
    Trade Republic cobra 1€ de comisión por orden.
    """
    disponible = margen_ahorro - comision
    if disponible <= 0 or precio_etf <= 0:
        return {"participaciones": 0, "importe": 0, "restante": margen_ahorro}
    participaciones = int(disponible // precio_etf)
    importe = round(participaciones * precio_etf + comision, 2)
    restante = round(margen_ahorro - importe, 2)
    return {
        "participaciones": participaciones,
        "importe": importe,
        "restante": restante,
    }
