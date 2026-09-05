# -*- coding: utf-8 -*-
"""
============================================================================
 FRONTERA EFICIENTE DE PORTAFOLIO DE PROYECTOS  |  MODELO DE MARKOWITZ
 Aplicacion Streamlit para PyMEs del sector construccion
============================================================================
 Fuente de datos : Base_Datos_Historica_5Anios_Construccion.xlsx
 Activo          : linea de negocio (id_tipo_obra), no la obra individual
 Autor           : Violeta
 Licencia        : MIT
============================================================================
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy import stats
from scipy.optimize import minimize

# ===========================================================================
# 1. CONFIGURACION GENERAL Y TEMA VISUAL (verde / negro, Arial, look bursatil)
# ===========================================================================

RUTA_DEFECTO = "data/Base_Datos_Historica_5Anios_Construccion.xlsx"
TODOS = "Todos"
MIN_OBS = 4          # obras minimas para estimar con una submuestra
DIAS_ANIO = 365.0

# --- Paleta ----------------------------------------------------------------
# Cromatica categorica validada para fondo oscuro (banda de luminosidad OKLCH
# 0.48-0.67, piso de croma, separacion CVD y contraste >= 3:1 verificados).
# El orden es fijo: la linea de negocio conserva su color aunque se filtre.
COLOR_SERIE: List[str] = [
    "#00A94F",  # TO-01  verde
    "#2196F3",  # TO-02  azul
    "#B8860B",  # TO-03  ambar
    "#A05BC4",  # TO-04  morado
    "#E0524F",  # TO-05  rojo
    "#1F9E92",  # TO-06  teal
    "#7E8CE0",  # TO-07  indigo
]

TEMA = {
    "fondo":        "#000000",
    "panel":        "#101314",
    "panel_alto":   "#161B1C",
    "borde":        "#1F2A26",
    "acento":       "#00E676",   # verde de interfaz (no es color de serie)
    "acento_2":     "#00C853",
    "texto":        "#FFFFFF",
    "texto_2":      "#9BA6A2",
    "positivo":     "#00E676",
    "negativo":     "#FF5252",
    "advertencia":  "#FFB300",
    "grid":         "rgba(255,255,255,0.08)",
}

# Rampa secuencial (una sola tinta, claro -> oscuro) para magnitudes.
RAMPA_VERDE = [
    [0.00, "#04160C"], [0.25, "#0B4526"], [0.50, "#12793F"],
    [0.75, "#00A94F"], [1.00, "#5BE39A"],
]
# Rampa divergente (dos tintas + gris neutro al centro) para correlaciones.
RAMPA_DIVERGENTE = [
    [0.00, "#E0524F"], [0.25, "#8E4340"], [0.50, "#4A4F52"],
    [0.75, "#12793F"], [1.00, "#00E676"],
]

CSS = f"""
<style>
html, body, [class*="css"], .stApp, .stMarkdown, .stMetric, button, input, select, textarea {{
    font-family: Arial, Helvetica, "Liberation Sans", sans-serif !important;
}}
.stApp {{ background-color: {TEMA['fondo']}; color: {TEMA['texto']}; }}
section[data-testid="stSidebar"] {{
    background-color: {TEMA['panel']};
    border-right: 1px solid {TEMA['borde']};
}}
section[data-testid="stSidebar"] * {{ color: {TEMA['texto']} !important; }}
h1, h2, h3, h4, h5, h6, p, li, label, span, div {{ color: {TEMA['texto']}; }}

/* --- Cintillo superior tipo terminal bursatil --- */
.cintillo {{
    background: linear-gradient(90deg, {TEMA['panel_alto']} 0%, #0A0F0D 100%);
    border: 1px solid {TEMA['borde']};
    border-left: 4px solid {TEMA['acento']};
    padding: 18px 22px; margin-bottom: 18px;
}}
.cintillo h1 {{
    font-size: 26px; font-weight: 700; letter-spacing: 1.5px;
    margin: 0; text-transform: uppercase; color: {TEMA['texto']};
}}
.cintillo p {{
    margin: 6px 0 0 0; font-size: 12.5px; letter-spacing: .6px;
    color: {TEMA['texto_2']}; text-transform: uppercase;
}}
.tag {{
    display: inline-block; padding: 2px 10px; margin-right: 6px;
    border: 1px solid {TEMA['acento']}; color: {TEMA['acento']};
    font-size: 11px; letter-spacing: 1px;
}}

/* --- Tarjeta KPI --- */
.kpi {{
    background: {TEMA['panel']}; border: 1px solid {TEMA['borde']};
    border-top: 2px solid {TEMA['acento']};
    padding: 14px 16px; height: 100%;
}}
.kpi .etq {{
    font-size: 11px; letter-spacing: 1.1px; color: {TEMA['texto_2']};
    text-transform: uppercase; margin-bottom: 6px;
}}
.kpi .val {{ font-size: 26px; font-weight: 700; line-height: 1.15; }}
.kpi .sub {{ font-size: 11.5px; color: {TEMA['texto_2']}; margin-top: 5px; }}
.val-pos {{ color: {TEMA['positivo']}; }}
.val-neg {{ color: {TEMA['negativo']}; }}
.val-neu {{ color: {TEMA['texto']}; }}
.val-adv {{ color: {TEMA['advertencia']}; }}

/* --- Barra de riesgo --- */
.barra {{ background: #1C2321; height: 7px; width: 100%; margin-top: 8px; }}
.barra > div {{ height: 7px; }}

/* --- Pestanas --- */
.stTabs [data-baseweb="tab-list"] {{ gap: 2px; border-bottom: 1px solid {TEMA['borde']}; }}
.stTabs [data-baseweb="tab"] {{
    background: {TEMA['panel']}; color: {TEMA['texto_2']};
    padding: 10px 18px; font-size: 13px; letter-spacing: .8px; text-transform: uppercase;
}}
.stTabs [aria-selected="true"] {{
    background: {TEMA['panel_alto']} !important; color: {TEMA['acento']} !important;
    border-bottom: 2px solid {TEMA['acento']};
}}
.stButton>button, .stDownloadButton>button {{
    background: transparent; color: {TEMA['acento']};
    border: 1px solid {TEMA['acento']}; border-radius: 0;
    font-size: 12.5px; letter-spacing: 1px; text-transform: uppercase; padding: 8px 18px;
}}
.stButton>button:hover, .stDownloadButton>button:hover {{
    background: {TEMA['acento']}; color: #000000;
}}
[data-testid="stDataFrame"] {{ border: 1px solid {TEMA['borde']}; }}
hr {{ border-color: {TEMA['borde']}; }}
.nota {{
    font-size: 11.5px; color: {TEMA['texto_2']}; border-left: 2px solid {TEMA['borde']};
    padding-left: 10px; margin-top: 6px;
}}
#MainMenu, footer {{ visibility: hidden; }}
</style>
"""


def aplicar_tema_plotly(fig: go.Figure, alto: int = 430, titulo: str = "") -> go.Figure:
    """Deja toda figura con el mismo lenguaje visual: fondo oscuro, Arial blanca,
    rejilla recesiva y leyenda horizontal arriba."""
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=titulo, font=dict(size=15, color=TEMA["texto"]), x=0, xanchor="left"),
        paper_bgcolor=TEMA["panel"],
        plot_bgcolor=TEMA["panel"],
        font=dict(family="Arial, Helvetica, sans-serif", color=TEMA["texto"], size=12),
        height=alto,
        margin=dict(l=60, r=30, t=60 if titulo else 30, b=50),
        hoverlabel=dict(bgcolor=TEMA["panel_alto"], bordercolor=TEMA["acento"],
                        font=dict(family="Arial", color=TEMA["texto"], size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    )
    fig.update_xaxes(gridcolor=TEMA["grid"], zerolinecolor=TEMA["grid"],
                     linecolor=TEMA["borde"], tickfont=dict(size=11, color=TEMA["texto_2"]))
    fig.update_yaxes(gridcolor=TEMA["grid"], zerolinecolor=TEMA["grid"],
                     linecolor=TEMA["borde"], tickfont=dict(size=11, color=TEMA["texto_2"]))
    return fig


# ===========================================================================
# 2. UTILIDADES DE FORMATO
# ===========================================================================

def mxn(x: float, dec: int = 0) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/d"
    return f"${x:,.{dec}f}"


def pct(x: float, dec: int = 2) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/d"
    return f"{x * 100:,.{dec}f}%"


def tarjeta(etiqueta: str, valor: str, sub: str = "", clase: str = "val-neu") -> str:
    return (f'<div class="kpi"><div class="etq">{etiqueta}</div>'
            f'<div class="val {clase}">{valor}</div>'
            f'<div class="sub">{sub}</div></div>')


def barra_riesgo(p: float) -> str:
    p = float(np.clip(p, 0, 1))
    color = TEMA["positivo"] if p < 0.25 else (TEMA["advertencia"] if p < 0.5 else TEMA["negativo"])
    return f'<div class="barra"><div style="width:{p*100:.1f}%;background:{color};"></div></div>'


# ===========================================================================
# 3. CARGA Y LIMPIEZA DE LA BASE HISTORICA
# ===========================================================================

HOJAS_TABLA = {
    "Cat_TipoObra":          ("id_tipo_obra", r"^TO-\d+$"),
    "Cat_Clientes":          ("id_cliente",   r"^CL-\d+$"),
    "Proyectos_Historicos":  ("id_proyecto",  r"^H-\d+$"),
    "Estadisticos_Linea":    ("id_tipo_obra", r"^TO-\d+$"),
    "Riesgos_Historicos":    ("id_tipo_obra", r"^TO-\d+$"),
    "Resumen_Anual":         ("id_tipo_obra", r"^TO-\d+$"),
}


def _depurar(df: pd.DataFrame, clave: str, patron: str) -> pd.DataFrame:
    """Las hojas del libro traen renglones de total y notas al pie. Se conservan
    solo los registros cuya llave cumple el patron del catalogo."""
    if clave not in df.columns:
        return df
    m = df[clave].astype(str).str.strip().str.match(patron, na=False)
    return df.loc[m].reset_index(drop=True)


@st.cache_data(show_spinner="Cargando base historica...")
def cargar_base(contenido: bytes) -> Dict[str, pd.DataFrame]:
    """Lee el libro completo, depura renglones de nota y devuelve tablas limpias."""
    xl = pd.ExcelFile(io.BytesIO(contenido))
    d: Dict[str, pd.DataFrame] = {}

    for hoja, (clave, patron) in HOJAS_TABLA.items():
        if hoja in xl.sheet_names:
            d[hoja] = _depurar(pd.read_excel(xl, sheet_name=hoja), clave, patron)

    # --- Serie de rendimientos mensuales (insumo de mu y de la covarianza) ---
    r = pd.read_excel(xl, sheet_name="Rendimientos_Mensuales")
    r = r[pd.to_numeric(r["periodo"], errors="coerce").notna()].copy()
    r["periodo"] = r["periodo"].astype(int)
    cols_to = [c for c in r.columns if re.match(r"^TO-\d+$", str(c))]
    r[cols_to] = r[cols_to].apply(pd.to_numeric, errors="coerce")
    d["Rendimientos_Mensuales"] = r.reset_index(drop=True)

    # --- Series macro de referencia ---
    if "Macro_Referencia" in xl.sheet_names:
        m = pd.read_excel(xl, sheet_name="Macro_Referencia")
        m = m[pd.to_numeric(m["periodo"], errors="coerce").notna()].copy()
        m["periodo"] = m["periodo"].astype(int)
        d["Macro_Referencia"] = m.reset_index(drop=True)

    # --- Parametros de la direccion ---
    p = pd.read_excel(xl, sheet_name="Parametros").dropna(subset=["parametro", "valor"])
    d["Parametros"] = p.reset_index(drop=True)

    # --- Matrices precalculadas del libro (se usan como cotejo) ---
    for hoja in ("Correlacion", "Covarianza"):
        if hoja in xl.sheet_names:
            mm = pd.read_excel(xl, sheet_name=hoja)
            mm = _depurar(mm, "id_tipo_obra", r"^TO-\d+$").set_index("id_tipo_obra")
            d[hoja] = mm[[c for c in mm.columns if re.match(r"^TO-\d+$", str(c))]]

    return d


def parametro(par: pd.DataFrame, nombre: str, defecto: float) -> float:
    fila = par.loc[par["parametro"] == nombre, "valor"]
    if fila.empty:
        return defecto
    try:
        return float(fila.iloc[0])
    except (TypeError, ValueError):
        return defecto


# Columnas numericas de la tabla de hechos. Se declaran de forma explicita porque
# las versiones recientes de pandas no exponen las columnas de texto como "object"
# y una coercion generica convertiria en NaN las llaves id_tipo_obra / id_cliente.
COLS_NUMERICAS_PROYECTO = [
    "anio_cierre", "monto_contratado_mxn", "aditivas_mxn", "monto_final_mxn",
    "costo_presupuestado_mxn", "costo_real_mxn", "utilidad_presupuestada_mxn",
    "utilidad_real_mxn", "margen_presupuestado_pct", "margen_real_pct",
    "desviacion_costo_pct", "desviacion_margen_pp", "dias_plan", "dias_real",
    "retraso_pct", "roi_anualizado_pct", "riesgo_ejecucion_materializado",
    "riesgo_comercial_materializado", "riesgo_financiero_materializado",
]


@st.cache_data(show_spinner=False)
def construir_proyectos(base_key: str, _d: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tabla de hechos enriquecida: obra + linea de negocio + estado del cliente."""
    p = _d["Proyectos_Historicos"].copy()
    p = p.merge(_d["Cat_TipoObra"][["id_tipo_obra", "nombre_linea_negocio"]],
                on="id_tipo_obra", how="left")
    p = p.merge(_d["Cat_Clientes"][["id_cliente", "nombre_cliente", "sector_cliente",
                                    "estado", "calificacion_credito"]],
                on="id_cliente", how="left")
    for c in COLS_NUMERICAS_PROYECTO:
        if c in p.columns:
            p[c] = pd.to_numeric(p[c], errors="coerce")
    p["duracion_anios"] = p["dias_real"] / DIAS_ANIO
    return p


# ===========================================================================
# 4. MOTOR DE ESTIMACION DEL PROYECTO
#    Costo real, utilidad real, desviacion de costo y los tres riesgos
# ===========================================================================

RIESGOS = {
    "riesgo_ejecucion_materializado":  "Riesgo de ejecucion",
    "riesgo_comercial_materializado":  "Riesgo comercial",
    "riesgo_financiero_materializado": "Riesgo financiero",
}


@dataclass
class Estimacion:
    linea: str
    nombre_linea: str
    nivel_muestra: str
    n_obras: int
    costo_presupuesto: float
    desviacion_costo: float
    desviacion_costo_sd: float
    costo_real: float
    margen_presupuestado: float
    ingreso_estimado: float
    factor_aditivas: float
    monto_final: float
    utilidad_presupuestada: float
    utilidad_real: float
    margen_real: float
    utilidad_optimista: float
    utilidad_adversa: float
    duracion_obra_anios: float
    riesgos: Dict[str, Dict[str, float]]
    perdida_esperada: float
    indice_riesgo: float


def seleccionar_muestra(proy: pd.DataFrame, linea: str, estado: str) -> Tuple[pd.DataFrame, str]:
    """Jerarquia de estimacion: linea + estado -> linea -> estado -> portafolio.
    Se baja de nivel solo cuando la submuestra no alcanza MIN_OBS obras."""
    base_l = proy[proy["id_tipo_obra"] == linea]
    if estado != TODOS:
        m = base_l[base_l["estado"] == estado]
        if len(m) >= MIN_OBS:
            return m, f"Linea + estado ({len(m)} obras)"
        if len(base_l) >= MIN_OBS:
            return base_l, f"Linea, historico nacional ({len(base_l)} obras; en {estado} solo hay {len(m)})"
        m_e = proy[proy["estado"] == estado]
        if len(m_e) >= MIN_OBS:
            return m_e, f"Estado, todas las lineas ({len(m_e)} obras)"
        return proy, f"Portafolio completo ({len(proy)} obras)"
    if len(base_l) >= MIN_OBS:
        return base_l, f"Linea, historico nacional ({len(base_l)} obras)"
    return proy, f"Portafolio completo ({len(proy)} obras)"


def _prob_horizonte(p_obra: float, duracion_anios: float, plazo_anios: int) -> float:
    """Traslada una frecuencia por obra a la probabilidad de que el evento se
    presente al menos una vez dentro del plazo evaluado.

        p_anual = 1 - (1 - p_obra)^(1/duracion)
        p_plazo = 1 - (1 - p_anual)^plazo
    """
    p_obra = float(np.clip(p_obra, 0.0, 0.999))
    dur = max(float(duracion_anios), 0.25)
    p_anual = 1.0 - (1.0 - p_obra) ** (1.0 / dur)
    return float(np.clip(1.0 - (1.0 - p_anual) ** plazo_anios, 0.0, 0.999))


def estimar_proyecto(muestra: pd.DataFrame, nivel: str, linea: str, nombre_linea: str,
                     costo_presupuesto: float, plazo_anios: int) -> Estimacion:
    """Aplica el comportamiento historico de la muestra al costo presupuestado
    capturado por el usuario. Todas las formulas estan documentadas en el README."""
    m = muestra
    desv = pd.to_numeric(m["desviacion_costo_pct"], errors="coerce").dropna()
    d_media = float(desv.mean()) if len(desv) else 0.0
    d_sd = float(desv.std(ddof=1)) if len(desv) > 1 else 0.0

    costo_real = costo_presupuesto * (1.0 + d_media)

    margen_pres = float(pd.to_numeric(m["margen_presupuestado_pct"], errors="coerce").mean())
    margen_pres = float(np.clip(margen_pres, 0.01, 0.60))
    ingreso = costo_presupuesto / (1.0 - margen_pres)

    adit = (pd.to_numeric(m["aditivas_mxn"], errors="coerce")
            / pd.to_numeric(m["monto_contratado_mxn"], errors="coerce")).replace([np.inf, -np.inf], np.nan)
    f_adit = float(adit.mean()) if adit.notna().any() else 0.0
    monto_final = ingreso * (1.0 + f_adit)

    utilidad_pres = ingreso - costo_presupuesto
    utilidad_real = monto_final - costo_real
    margen_real = utilidad_real / monto_final if monto_final else 0.0

    q10 = float(desv.quantile(0.10)) if len(desv) else d_media
    q90 = float(desv.quantile(0.90)) if len(desv) else d_media
    u_opt = monto_final - costo_presupuesto * (1.0 + q10)
    u_adv = monto_final - costo_presupuesto * (1.0 + q90)

    dur = float(pd.to_numeric(m["duracion_anios"], errors="coerce").mean())
    dur = dur if np.isfinite(dur) and dur > 0 else 1.0

    # --- Los tres riesgos: frecuencia empirica + impacto marginal en costo ---
    riesgos: Dict[str, Dict[str, float]] = {}
    perdida = 0.0
    for col, etiqueta in RIESGOS.items():
        f = pd.to_numeric(m[col], errors="coerce").fillna(0.0)
        p_obra = float(f.mean()) if len(f) else 0.0
        con = desv[f.reindex(desv.index).fillna(0) == 1]
        sin = desv[f.reindex(desv.index).fillna(0) == 0]
        impacto = float(con.mean() - sin.mean()) if len(con) and len(sin) else (
            float(con.mean()) if len(con) else 0.0)
        impacto = 0.0 if not np.isfinite(impacto) else impacto
        p_plazo = _prob_horizonte(p_obra, dur, plazo_anios)
        monto = p_plazo * max(impacto, 0.0) * costo_presupuesto
        perdida += monto
        riesgos[etiqueta] = {
            "eventos": float(f.sum()),
            "frecuencia_obra": p_obra,
            "prob_plazo": p_plazo,
            "impacto_costo": impacto,
            "perdida_esperada": monto,
        }

    indice = float(np.mean([v["prob_plazo"] for v in riesgos.values()])) if riesgos else 0.0

    return Estimacion(
        linea=linea, nombre_linea=nombre_linea, nivel_muestra=nivel, n_obras=int(len(m)),
        costo_presupuesto=costo_presupuesto, desviacion_costo=d_media, desviacion_costo_sd=d_sd,
        costo_real=costo_real, margen_presupuestado=margen_pres, ingreso_estimado=ingreso,
        factor_aditivas=f_adit, monto_final=monto_final, utilidad_presupuestada=utilidad_pres,
        utilidad_real=utilidad_real, margen_real=margen_real, utilidad_optimista=u_opt,
        utilidad_adversa=u_adv, duracion_obra_anios=dur, riesgos=riesgos,
        perdida_esperada=perdida, indice_riesgo=indice,
    )


# ===========================================================================
# 5. MOTOR DE MARKOWITZ
# ===========================================================================

@dataclass
class Universo:
    ids: List[str]
    nombres: List[str]
    mu: np.ndarray          # rendimiento esperado anualizado
    cov: np.ndarray         # covarianza anualizada
    sigma: np.ndarray       # volatilidad anualizada
    corr: pd.DataFrame
    retornos: pd.DataFrame  # serie mensual


def construir_universo(d: Dict[str, pd.DataFrame], ids: List[str], periodos_anio: int = 12,
                       ventana: Optional[int] = None) -> Universo:
    """mu = media mensual x 12 ; Sigma = covarianza muestral mensual x 12."""
    r = d["Rendimientos_Mensuales"].copy()
    if ventana:
        r = r.tail(int(ventana))
    ret = r[ids].astype(float).dropna()
    mu = ret.mean().values * periodos_anio
    cov = ret.cov().values * periodos_anio
    sigma = np.sqrt(np.diag(cov))
    nombres = (d["Cat_TipoObra"].set_index("id_tipo_obra")["nombre_linea_negocio"]
               .reindex(ids).fillna(pd.Series(ids, index=ids)).tolist())
    return Universo(ids=ids, nombres=nombres, mu=mu, cov=cov, sigma=sigma,
                    corr=ret.corr(), retornos=ret)


def stats_portafolio(w: np.ndarray, mu: np.ndarray, cov: np.ndarray,
                     rf: float, plazo: int = 1) -> Tuple[float, float, float]:
    """Escalamiento i.i.d. al horizonte: mu_T = mu*T ; sigma_T = sigma*raiz(T)."""
    r = float(w @ mu) * plazo
    v = float(w @ cov @ w) * plazo
    s = float(np.sqrt(max(v, 1e-18)))
    sharpe = (r - rf * plazo) / s if s > 0 else 0.0
    return r, s, sharpe


def _optimizar(mu, cov, w_min, w_max, objetivo, r_objetivo=None):
    n = len(mu)
    restricciones = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    if r_objetivo is not None:
        restricciones.append({"type": "eq", "fun": lambda w, r=r_objetivo: float(w @ mu) - r})
    limites = tuple((w_min, w_max) for _ in range(n))
    w0 = np.repeat(1.0 / n, n)
    w0 = np.clip(w0, w_min, w_max)
    w0 = w0 / w0.sum()
    res = minimize(objetivo, w0, method="SLSQP", bounds=limites,
                   constraints=restricciones, options={"maxiter": 800, "ftol": 1e-12})
    if not res.success:
        return None
    w = np.clip(res.x, w_min, w_max)
    return w / w.sum()


def portafolio_min_varianza(mu, cov, w_min, w_max):
    return _optimizar(mu, cov, w_min, w_max, lambda w: float(w @ cov @ w))


def portafolio_tangente(mu, cov, w_min, w_max, rf):
    def neg_sharpe(w):
        r = float(w @ mu)
        s = float(np.sqrt(max(w @ cov @ w, 1e-18)))
        return -(r - rf) / s
    return _optimizar(mu, cov, w_min, w_max, neg_sharpe)


def frontera_eficiente(mu, cov, w_min, w_max, n_puntos=60) -> pd.DataFrame:
    """Para cada rendimiento objetivo entre el de minima varianza y el maximo
    alcanzable, resuelve  min w'Sigma w  s.a.  w'mu = R, sum(w)=1, w_min<=w<=w_max."""
    w_mv = portafolio_min_varianza(mu, cov, w_min, w_max)
    if w_mv is None:
        return pd.DataFrame()
    r_min = float(w_mv @ mu)
    w_max_r = _optimizar(mu, cov, w_min, w_max, lambda w: -float(w @ mu))
    r_max = float(w_max_r @ mu) if w_max_r is not None else float(mu.max())
    if r_max <= r_min:
        r_max = r_min * 1.0001 + 1e-6

    filas = []
    for r_obj in np.linspace(r_min, r_max, int(n_puntos)):
        w = _optimizar(mu, cov, w_min, w_max, lambda w: float(w @ cov @ w), r_objetivo=r_obj)
        if w is None:
            continue
        filas.append({"rend": float(w @ mu),
                      "riesgo": float(np.sqrt(max(w @ cov @ w, 1e-18))),
                      "pesos": w})
    return pd.DataFrame(filas)


def nube_aleatoria(mu, cov, w_min, w_max, n=4000, semilla=7) -> pd.DataFrame:
    """Carteras factibles simuladas: contexto visual de la frontera."""
    rng = np.random.default_rng(semilla)
    k = len(mu)
    W = rng.dirichlet(np.ones(k) * 1.2, size=int(n))
    W = np.clip(W, w_min, w_max)
    W = W / W.sum(axis=1, keepdims=True)
    r = W @ mu
    s = np.sqrt(np.einsum("ij,jk,ik->i", W, cov, W))
    return pd.DataFrame({"rend": r, "riesgo": s, "sharpe": np.divide(r, s, where=s > 0)})


# ===========================================================================
# 6. CORRELACION Y REGRESION CONTRA EL INDICE DE REFERENCIA
# ===========================================================================

INDICES = {
    "Indice interno del sector (portafolio equiponderado de las 7 lineas)": "__interno__",
    "PIB de la construccion (var. anual)": "var_pib_construccion_anual",
    "INPC construccion (var. mensual)": "var_inpc_construccion_mensual",
    "Precio del acero (var. mensual)": "var_precio_acero_mensual",
    "Precio del cemento (var. mensual)": "var_precio_cemento_mensual",
    "CETES 28 dias (tasa anual)": "tasa_cetes28_anual",
}


def serie_indice(d: Dict[str, pd.DataFrame], etiqueta: str, ids_todas: List[str]) -> pd.Series:
    col = INDICES[etiqueta]
    r = d["Rendimientos_Mensuales"]
    if col == "__interno__":
        s = r[ids_todas].astype(float).mean(axis=1)
    else:
        macro = d["Macro_Referencia"].set_index("periodo")
        s = pd.to_numeric(macro[col], errors="coerce").reindex(r["periodo"].values).values
        s = pd.Series(s, index=r.index)
    s.index = r.index
    return s.astype(float)


def regresion_vs_indice(ret: pd.DataFrame, idx: pd.Series, ids: List[str],
                        nombres: List[str], rf_mensual: float,
                        periodos_anio: int = 12) -> pd.DataFrame:
    """Modelo de mercado (una variable):  r_i,t = alpha_i + beta_i * r_m,t + e_i,t
    estimado por minimos cuadrados ordinarios sobre los 60 periodos."""
    filas = []
    x = idx.astype(float)
    for i, (cid, nom) in enumerate(zip(ids, nombres)):
        y = ret[cid].astype(float)
        ok = x.notna() & y.notna()
        if ok.sum() < 5:
            continue
        lr = stats.linregress(x[ok], y[ok])
        resid = y[ok] - (lr.intercept + lr.slope * x[ok])
        filas.append({
            "id_tipo_obra": cid,
            "linea_negocio": nom,
            "beta": lr.slope,
            "alpha_mensual": lr.intercept,
            "alpha_anualizada": lr.intercept * periodos_anio,
            "correlacion": lr.rvalue,
            "r2": lr.rvalue ** 2,
            "p_valor": lr.pvalue,
            "error_estandar_beta": lr.stderr,
            "riesgo_sistematico": abs(lr.slope) * float(x[ok].std(ddof=1)) * np.sqrt(periodos_anio),
            "riesgo_especifico": float(resid.std(ddof=1)) * np.sqrt(periodos_anio),
            "n": int(ok.sum()),
        })
    return pd.DataFrame(filas)


# ===========================================================================
# 7. GRAFICAS
# ===========================================================================

def g_frontera(nube, front, uni, w_tan, w_mv, rf, plazo) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=nube["riesgo"] * np.sqrt(plazo), y=nube["rend"] * plazo, mode="markers",
        name="Carteras factibles simuladas",
        marker=dict(size=4, color=nube["sharpe"], colorscale=RAMPA_VERDE, opacity=0.45,
                    colorbar=dict(title=dict(text="Sharpe", font=dict(size=10)),
                                  thickness=10, len=0.55, x=1.02,
                                  tickfont=dict(size=9, color=TEMA["texto_2"]))),
        hovertemplate="Riesgo %{x:.2%}<br>Rendimiento %{y:.2%}<extra></extra>"))

    if not front.empty:
        fig.add_trace(go.Scatter(
            x=front["riesgo"] * np.sqrt(plazo), y=front["rend"] * plazo,
            mode="lines", name="Frontera eficiente",
            line=dict(color=TEMA["acento"], width=3),
            hovertemplate="Riesgo %{x:.2%}<br>Rendimiento %{y:.2%}<extra>Frontera</extra>"))

    # Lineas de negocio individuales, con etiqueta directa
    for i, (cid, nom) in enumerate(zip(uni.ids, uni.nombres)):
        fig.add_trace(go.Scatter(
            x=[uni.sigma[i] * np.sqrt(plazo)], y=[uni.mu[i] * plazo], mode="markers+text",
            name=nom, text=[cid], textposition="top center",
            textfont=dict(size=10, color=TEMA["texto_2"]),
            marker=dict(size=11, color=COLOR_SERIE[i % len(COLOR_SERIE)],
                        line=dict(color=TEMA["panel"], width=2)),
            hovertemplate=f"<b>{nom}</b><br>Riesgo %{{x:.2%}}<br>Rendimiento %{{y:.2%}}<extra></extra>"))

    if w_tan is not None:
        r_t, s_t, _ = stats_portafolio(w_tan, uni.mu, uni.cov, rf, plazo)
        fig.add_trace(go.Scatter(x=[0, s_t * 1.9], y=[rf * plazo, rf * plazo + (r_t - rf * plazo) * 1.9],
                                 mode="lines", name="Linea del mercado de capitales",
                                 line=dict(color=TEMA["texto_2"], width=1.5, dash="dot"),
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[s_t], y=[r_t], mode="markers+text",
                                 name="Portafolio tangente (max. Sharpe)",
                                 text=["TANGENTE"], textposition="middle right",
                                 textfont=dict(size=10, color=TEMA["acento"]),
                                 marker=dict(size=16, symbol="star", color=TEMA["acento"],
                                             line=dict(color=TEMA["panel"], width=2)),
                                 hovertemplate="Tangente<br>Riesgo %{x:.2%}<br>Rendimiento %{y:.2%}<extra></extra>"))
    if w_mv is not None:
        r_v, s_v, _ = stats_portafolio(w_mv, uni.mu, uni.cov, rf, plazo)
        fig.add_trace(go.Scatter(x=[s_v], y=[r_v], mode="markers+text",
                                 name="Minima varianza", text=["MIN. VAR"],
                                 textposition="bottom center",
                                 textfont=dict(size=10, color=TEMA["texto_2"]),
                                 marker=dict(size=14, symbol="diamond", color=TEMA["texto"],
                                             line=dict(color=TEMA["panel"], width=2)),
                                 hovertemplate="Minima varianza<br>Riesgo %{x:.2%}<br>Rendimiento %{y:.2%}<extra></extra>"))

    fig.update_xaxes(title_text=f"Riesgo &#8212; desviacion estandar a {plazo} ano(s)", tickformat=".0%")
    fig.update_yaxes(title_text=f"Rendimiento esperado a {plazo} ano(s)", tickformat=".0%")
    return aplicar_tema_plotly(fig, 560, "Frontera eficiente del portafolio de proyectos")


def g_pesos(ids, nombres, w, capital) -> go.Figure:
    orden = np.argsort(w)
    fig = go.Figure(go.Bar(
        x=[w[i] for i in orden], y=[nombres[i] for i in orden], orientation="h",
        marker=dict(color=[COLOR_SERIE[i % len(COLOR_SERIE)] for i in orden],
                    line=dict(color=TEMA["panel"], width=2)),
        text=[f"{w[i]*100:.1f}%  |  {mxn(w[i]*capital)}" for i in orden],
        textposition="outside", textfont=dict(size=11, color=TEMA["texto"]),
        hovertemplate="<b>%{y}</b><br>Peso %{x:.2%}<extra></extra>", showlegend=False))
    fig.update_xaxes(title_text="Peso en el portafolio", tickformat=".0%",
                     range=[0, max(w) * 1.45 if max(w) > 0 else 1])
    fig.update_traces(marker_cornerradius=4)
    return aplicar_tema_plotly(fig, 420, "Asignacion optima del presupuesto por linea de negocio")


def g_correlacion(corr: pd.DataFrame, nombres: List[str]) -> go.Figure:
    z = corr.values
    etiquetas = [f"{c}<br>{n[:22]}" for c, n in zip(corr.columns, nombres)]
    fig = go.Figure(go.Heatmap(
        z=z, x=etiquetas, y=etiquetas, zmid=0, zmin=-1, zmax=1, colorscale=RAMPA_DIVERGENTE,
        xgap=2, ygap=2,
        text=[[f"{v:.2f}" for v in fila] for fila in z], texttemplate="%{text}",
        textfont=dict(size=11, color=TEMA["texto"], family="Arial"),
        colorbar=dict(title=dict(text="Correlacion", font=dict(size=10)), thickness=12,
                      tickfont=dict(size=10, color=TEMA["texto_2"])),
        hovertemplate="%{y}<br>%{x}<br>Correlacion %{z:.3f}<extra></extra>"))
    fig.update_xaxes(tickfont=dict(size=9.5, color=TEMA["texto_2"]))
    fig.update_yaxes(tickfont=dict(size=9.5, color=TEMA["texto_2"]))
    return aplicar_tema_plotly(fig, 520,
                               "Matriz de correlacion de Pearson entre lineas de negocio (60 meses)")


def g_regresion(ret, idx, ids, nombres, reg: pd.DataFrame, etiqueta_indice: str) -> go.Figure:
    n = len(ids)
    cols = 3 if n >= 3 else max(n, 1)
    filas = int(np.ceil(n / cols))
    titulos = []
    for cid, nom in zip(ids, nombres):
        r = reg[reg["id_tipo_obra"] == cid]
        if r.empty:
            titulos.append(nom)
        else:
            r = r.iloc[0]
            titulos.append(f"{nom}  |  β={r['beta']:.2f}  R²={r['r2']:.2f}")
    fig = make_subplots(rows=filas, cols=cols, subplot_titles=titulos,
                        horizontal_spacing=0.07, vertical_spacing=0.16)
    x = idx.astype(float)
    for k, cid in enumerate(ids):
        f, c = k // cols + 1, k % cols + 1
        y = ret[cid].astype(float)
        ok = x.notna() & y.notna()
        color = COLOR_SERIE[uni_pos(cid) % len(COLOR_SERIE)]
        fig.add_trace(go.Scatter(x=x[ok], y=y[ok], mode="markers", name=nombres[k],
                                 showlegend=False,
                                 marker=dict(size=7, color=color, opacity=0.75,
                                             line=dict(color=TEMA["panel"], width=1)),
                                 hovertemplate="Indice %{x:.3f}<br>Linea %{y:.3f}<extra></extra>"),
                      row=f, col=c)
        r = reg[reg["id_tipo_obra"] == cid]
        if not r.empty and ok.sum() > 2:
            r = r.iloc[0]
            xs = np.linspace(float(x[ok].min()), float(x[ok].max()), 40)
            fig.add_trace(go.Scatter(x=xs, y=r["alpha_mensual"] + r["beta"] * xs, mode="lines",
                                     showlegend=False, line=dict(color=TEMA["acento"], width=2),
                                     hoverinfo="skip"), row=f, col=c)
    fig.update_xaxes(tickfont=dict(size=9, color=TEMA["texto_2"]), gridcolor=TEMA["grid"])
    fig.update_yaxes(tickformat=".1%", tickfont=dict(size=9, color=TEMA["texto_2"]),
                     gridcolor=TEMA["grid"])
    for a in fig.layout.annotations:
        a.font.size = 11
        a.font.color = TEMA["texto"]
    fig = aplicar_tema_plotly(fig, 300 * filas,
                              f"Regresion de cada linea contra el indice: {etiqueta_indice}")
    fig.update_layout(showlegend=False)
    return fig


_POS_ID: Dict[str, int] = {}


def uni_pos(cid: str) -> int:
    return _POS_ID.get(cid, 0)


def g_acumulado(ret, idx, ids, nombres, etiqueta_indice) -> go.Figure:
    fig = go.Figure()
    for k, (cid, nom) in enumerate(zip(ids, nombres)):
        acum = (1 + ret[cid].astype(float)).cumprod() - 1
        fig.add_trace(go.Scatter(x=list(range(1, len(acum) + 1)), y=acum, mode="lines", name=nom,
                                 line=dict(color=COLOR_SERIE[uni_pos(cid) % len(COLOR_SERIE)], width=2),
                                 hovertemplate=f"<b>{nom}</b><br>Mes %{{x}}<br>Acumulado %{{y:.1%}}<extra></extra>"))
    acum_i = (1 + idx.astype(float).fillna(0)).cumprod() - 1
    fig.add_trace(go.Scatter(x=list(range(1, len(acum_i) + 1)), y=acum_i, mode="lines",
                             name=f"Indice: {etiqueta_indice[:38]}",
                             line=dict(color=TEMA["texto"], width=2.5, dash="dash"),
                             hovertemplate="Indice<br>Mes %{x}<br>Acumulado %{y:.1%}<extra></extra>"))
    fig.update_xaxes(title_text="Periodo mensual (2021-01 a 2025-12)")
    fig.update_yaxes(title_text="Rendimiento acumulado", tickformat=".0%")
    return aplicar_tema_plotly(fig, 460, "Rendimiento acumulado por linea contra el indice de referencia")


def g_riesgos(est: Estimacion) -> go.Figure:
    etiquetas = list(est.riesgos.keys())
    probs = [est.riesgos[e]["prob_plazo"] for e in etiquetas]
    colores = [TEMA["positivo"] if p < 0.25 else (TEMA["advertencia"] if p < 0.5 else TEMA["negativo"])
               for p in probs]
    fig = go.Figure(go.Bar(x=probs, y=etiquetas, orientation="h",
                           marker=dict(color=colores, line=dict(color=TEMA["panel"], width=2)),
                           text=[f"{p:.1%}" for p in probs], textposition="outside",
                           textfont=dict(size=12, color=TEMA["texto"]),
                           hovertemplate="<b>%{y}</b><br>Probabilidad en el plazo %{x:.1%}<extra></extra>",
                           showlegend=False))
    fig.update_traces(marker_cornerradius=4)
    fig.update_xaxes(title_text="Probabilidad de materializacion dentro del plazo",
                     tickformat=".0%", range=[0, min(1.0, max(probs + [0.1]) * 1.4)])
    return aplicar_tema_plotly(fig, 320, "Perfil de riesgo del proyecto")


# ===========================================================================
# 8. EXPORTACION DE RESULTADOS
# ===========================================================================

def exportar_excel(est_df: pd.DataFrame, pesos_df: pd.DataFrame, front_df: pd.DataFrame,
                   corr: pd.DataFrame, reg: pd.DataFrame, supuestos: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        supuestos.to_excel(w, sheet_name="Supuestos", index=False)
        est_df.to_excel(w, sheet_name="Estimacion_Proyecto", index=False)
        pesos_df.to_excel(w, sheet_name="Pesos_Optimos", index=False)
        front_df.to_excel(w, sheet_name="Frontera_Eficiente", index=False)
        corr.to_excel(w, sheet_name="Correlacion")
        reg.to_excel(w, sheet_name="Regresion_vs_Indice", index=False)
        libro = w.book
        enc = libro.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#0B4526",
                                "border": 1, "font_name": "Arial", "font_size": 10})
        for hoja, df in [("Supuestos", supuestos), ("Estimacion_Proyecto", est_df),
                         ("Pesos_Optimos", pesos_df), ("Frontera_Eficiente", front_df),
                         ("Regresion_vs_Indice", reg)]:
            ws = w.sheets[hoja]
            for j, col in enumerate(df.columns):
                ws.write(0, j, str(col), enc)
                ws.set_column(j, j, max(14, min(34, len(str(col)) + 6)))
            ws.freeze_panes(1, 0)
    return buf.getvalue()


# ===========================================================================
# 9. INTERFAZ
# ===========================================================================

st.set_page_config(page_title="Frontera Eficiente | Portafolio de Proyectos",
                   page_icon="📈", layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)


def cabecera(sub: str) -> None:
    st.markdown(
        f"""<div class="cintillo">
        <h1>Frontera eficiente &#183; portafolio de proyectos</h1>
        <p>{sub}</p>
        <div style="margin-top:10px">
            <span class="tag">MARKOWITZ</span><span class="tag">CONSTRUCCION</span>
            <span class="tag">MXN</span><span class="tag">2021&#8211;2025</span>
        </div></div>""", unsafe_allow_html=True)


def main() -> None:
    # ---------------- Origen de datos ----------------
    st.sidebar.markdown("### Fuente de datos")
    subido = st.sidebar.file_uploader("Base historica (.xlsx)", type=["xlsx"],
                                      help="Si se omite, se usa el archivo del repositorio.")
    if subido is not None:
        contenido, origen = subido.getvalue(), subido.name
    else:
        try:
            with open(RUTA_DEFECTO, "rb") as f:
                contenido = f.read()
            origen = RUTA_DEFECTO
        except FileNotFoundError:
            cabecera("Sin fuente de datos")
            st.error(f"No se encontro **{RUTA_DEFECTO}**. Cargue el libro desde la barra lateral.")
            st.stop()

    d = cargar_base(contenido)
    proy = construir_proyectos(origen, d)
    par = d["Parametros"]

    cat = d["Cat_TipoObra"]
    ids_todas = cat["id_tipo_obra"].tolist()
    nombre_de = dict(zip(cat["id_tipo_obra"], cat["nombre_linea_negocio"]))
    global _POS_ID
    _POS_ID = {cid: i for i, cid in enumerate(ids_todas)}

    # ---------------- INPUTS ----------------
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Parametros del analisis")

    sel = st.sidebar.multiselect(
        "Linea de negocio (universo del portafolio)",
        options=ids_todas, default=ids_todas,
        format_func=lambda c: f"{c} · {nombre_de[c]}")
    if len(sel) < 2:
        st.sidebar.warning("Seleccione al menos dos lineas para optimizar.")
    ids = sel if len(sel) >= 2 else ids_todas

    linea_focus = st.sidebar.selectbox(
        "Linea de negocio del proyecto a evaluar", options=ids,
        format_func=lambda c: f"{c} · {nombre_de[c]}")

    capital_def = float(parametro(par, "capital_disponible_mxn", 450_000_000))
    costo_presupuesto = st.sidebar.number_input(
        "Costo presupuesto (MXN)", min_value=100_000.0, max_value=5_000_000_000.0,
        value=float(capital_def), step=1_000_000.0, format="%.0f",
        help="Costo directo presupuestado. Es tambien el capital que se reparte entre lineas.")

    estados = [TODOS] + sorted(proy["estado"].dropna().unique().tolist())
    estado = st.sidebar.selectbox("Estado", options=estados, index=0)

    plazo = st.sidebar.radio("Plazo a calcular", options=[1, 2, 3, 4, 5], index=0,
                             horizontal=True, format_func=lambda x: f"{x} ano" if x == 1 else f"{x} anos")

    with st.sidebar.expander("Supuestos del modelo", expanded=False):
        rf = st.number_input("Tasa libre de riesgo anual",
                             value=float(parametro(par, "tasa_libre_riesgo_anual", 0.085)),
                             min_value=0.0, max_value=0.30, step=0.005, format="%.4f")
        w_min = st.number_input("Peso minimo por linea",
                                value=float(parametro(par, "peso_min_por_linea", 0.0)),
                                min_value=0.0, max_value=0.50, step=0.01, format="%.2f")
        w_max = st.number_input("Peso maximo por linea",
                                value=float(parametro(par, "peso_max_por_linea", 0.35)),
                                min_value=0.05, max_value=1.00, step=0.05, format="%.2f")
        n_front = st.slider("Puntos de la frontera", 20, 120,
                            int(parametro(par, "num_carteras_frontera", 100)) // 2 or 60, 10)
        n_nube = st.slider("Carteras simuladas", 500, 10000, 4000, 500)
        ventana = st.select_slider("Ventana de estimacion (meses)",
                                   options=[24, 36, 48, 60], value=60)
        etiqueta_indice = st.selectbox("Indice de referencia", options=list(INDICES.keys()), index=0)

    if w_max * len(ids) < 1.0:
        st.sidebar.error(f"Peso maximo infactible: {len(ids)} lineas x {w_max:.0%} < 100%.")
        w_max = 1.0 / len(ids) + 0.05

    # ---------------- Calculos ----------------
    uni = construir_universo(d, ids, 12, ventana)
    nombres = uni.nombres
    muestra, nivel = seleccionar_muestra(proy, linea_focus, estado)
    est = estimar_proyecto(muestra, nivel, linea_focus, nombre_de[linea_focus],
                           costo_presupuesto, plazo)

    w_mv = portafolio_min_varianza(uni.mu, uni.cov, w_min, w_max)
    w_tan = portafolio_tangente(uni.mu, uni.cov, w_min, w_max, rf)
    front = frontera_eficiente(uni.mu, uni.cov, w_min, w_max, n_front)
    nube = nube_aleatoria(uni.mu, uni.cov, w_min, w_max, n_nube)

    idx = serie_indice(d, etiqueta_indice, ids_todas)
    reg = regresion_vs_indice(uni.retornos, idx.reindex(uni.retornos.index),
                              ids, nombres, rf / 12)

    cabecera(f"{nombre_de[linea_focus]} &#183; {estado} &#183; plazo {plazo} ano(s) &#183; "
             f"presupuesto {mxn(costo_presupuesto)} &#183; fuente: {origen.split('/')[-1]}")

    t1, t2, t3, t4, t5 = st.tabs(["Proyecto", "Frontera eficiente",
                                  "Correlacion y regresion", "Base historica", "Metodologia"])

    # =================== T1. PROYECTO ===================
    with t1:
        c = st.columns(4)
        clase_u = "val-pos" if est.utilidad_real >= 0 else "val-neg"
        clase_d = "val-pos" if est.desviacion_costo <= 0 else "val-neg"
        c[0].markdown(tarjeta("Utilidad real estimada", mxn(est.utilidad_real),
                              f"Margen real {pct(est.margen_real)} &#183; presupuestada {mxn(est.utilidad_presupuestada)}",
                              clase_u), unsafe_allow_html=True)
        c[1].markdown(tarjeta("Costo real estimado", mxn(est.costo_real),
                              f"Presupuesto {mxn(est.costo_presupuesto)}",
                              "val-neu"), unsafe_allow_html=True)
        c[2].markdown(tarjeta("Desviacion de costo", pct(est.desviacion_costo),
                              f"Sigma historica {pct(est.desviacion_costo_sd)} &#183; {est.n_obras} obras",
                              clase_d), unsafe_allow_html=True)
        c[3].markdown(tarjeta("Perdida esperada por riesgo", mxn(est.perdida_esperada),
                              f"Indice de riesgo {pct(est.indice_riesgo, 1)} a {plazo} ano(s)",
                              "val-adv"), unsafe_allow_html=True)

        st.markdown(f'<div class="nota">Muestra utilizada: <b>{est.nivel_muestra}</b>. '
                    f'Duracion promedio de obra: {est.duracion_obra_anios:.2f} anos. '
                    f'Aditivas historicas: {pct(est.factor_aditivas)} sobre el monto contratado.</div>',
                    unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        c = st.columns(3)
        for (etq, v), col in zip(est.riesgos.items(), c):
            clase = ("val-pos" if v["prob_plazo"] < 0.25
                     else "val-adv" if v["prob_plazo"] < 0.5 else "val-neg")
            col.markdown(
                tarjeta(etq, pct(v["prob_plazo"], 1),
                        f"Frecuencia por obra {pct(v['frecuencia_obra'], 1)} &#183; "
                        f"{int(v['eventos'])} eventos &#183; impacto en costo {pct(v['impacto_costo'])} "
                        f"&#183; {mxn(v['perdida_esperada'])}", clase) + barra_riesgo(v["prob_plazo"]),
                unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        cA, cB = st.columns([1.15, 1])
        with cA:
            st.plotly_chart(g_riesgos(est), width="stretch",
                            config={"displayModeBar": False})
        with cB:
            esc = pd.DataFrame({
                "Escenario": ["Optimista (p10 de desviacion)", "Base (media historica)",
                              "Adverso (p90 de desviacion)"],
                "Costo real": [est.costo_presupuesto * (1 + float(pd.to_numeric(muestra["desviacion_costo_pct"], errors="coerce").quantile(0.10))),
                               est.costo_real,
                               est.costo_presupuesto * (1 + float(pd.to_numeric(muestra["desviacion_costo_pct"], errors="coerce").quantile(0.90)))],
                "Utilidad real": [est.utilidad_optimista, est.utilidad_real, est.utilidad_adversa],
            })
            esc["Margen real"] = esc["Utilidad real"] / est.monto_final
            st.markdown("**Escenarios de cierre**")
            st.dataframe(esc.style.format({"Costo real": "${:,.0f}", "Utilidad real": "${:,.0f}",
                                           "Margen real": "{:.2%}"}),
                         width="stretch", hide_index=True)
            st.markdown(
                f'<div class="nota">Ingreso estimado del contrato: {mxn(est.ingreso_estimado)} '
                f'(costo presupuesto entre 1 &#8722; margen presupuestado de {pct(est.margen_presupuestado)}). '
                f'Monto final con aditivas: {mxn(est.monto_final)}.</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Estimacion comparada por linea de negocio** (mismo presupuesto, mismo estado y plazo)")
        filas = []
        for cid in ids:
            m_i, n_i = seleccionar_muestra(proy, cid, estado)
            e_i = estimar_proyecto(m_i, n_i, cid, nombre_de[cid], costo_presupuesto, plazo)
            filas.append({
                "id_tipo_obra": cid, "Linea de negocio": e_i.nombre_linea, "Obras": e_i.n_obras,
                "Costo presupuesto": e_i.costo_presupuesto, "Desviacion costo": e_i.desviacion_costo,
                "Costo real": e_i.costo_real, "Utilidad real": e_i.utilidad_real,
                "Margen real": e_i.margen_real,
                "Riesgo ejecucion": e_i.riesgos["Riesgo de ejecucion"]["prob_plazo"],
                "Riesgo comercial": e_i.riesgos["Riesgo comercial"]["prob_plazo"],
                "Riesgo financiero": e_i.riesgos["Riesgo financiero"]["prob_plazo"],
                "Perdida esperada": e_i.perdida_esperada,
            })
        est_df = pd.DataFrame(filas)
        st.dataframe(est_df.style.format({
            "Costo presupuesto": "${:,.0f}", "Costo real": "${:,.0f}", "Utilidad real": "${:,.0f}",
            "Perdida esperada": "${:,.0f}", "Desviacion costo": "{:.2%}", "Margen real": "{:.2%}",
            "Riesgo ejecucion": "{:.1%}", "Riesgo comercial": "{:.1%}", "Riesgo financiero": "{:.1%}",
        }), width="stretch", hide_index=True)

    # =================== T2. FRONTERA ===================
    with t2:
        if w_tan is None or w_mv is None:
            st.error("El optimizador no encontro solucion factible con los limites de peso indicados.")
        else:
            r_t, s_t, sh_t = stats_portafolio(w_tan, uni.mu, uni.cov, rf, plazo)
            r_v, s_v, sh_v = stats_portafolio(w_mv, uni.mu, uni.cov, rf, plazo)
            w_eq = np.repeat(1 / len(ids), len(ids))
            r_e, s_e, sh_e = stats_portafolio(w_eq, uni.mu, uni.cov, rf, plazo)

            c = st.columns(4)
            c[0].markdown(tarjeta("Rendimiento del portafolio tangente", pct(r_t),
                                  f"A {plazo} ano(s) &#183; equiponderado {pct(r_e)}", "val-pos"),
                          unsafe_allow_html=True)
            c[1].markdown(tarjeta("Riesgo del portafolio tangente", pct(s_t),
                                  f"Minima varianza {pct(s_v)} &#183; equiponderado {pct(s_e)}",
                                  "val-neu"), unsafe_allow_html=True)
            c[2].markdown(tarjeta("Indice de Sharpe", f"{sh_t:,.3f}",
                                  f"Equiponderado {sh_e:,.3f} &#183; rf {pct(rf)} anual", "val-pos"),
                          unsafe_allow_html=True)
            c[3].markdown(tarjeta("Utilidad esperada del presupuesto", mxn(costo_presupuesto * r_t),
                                  f"VaR 95%: {mxn(costo_presupuesto * (r_t - 1.645 * s_t))}", "val-neu"),
                          unsafe_allow_html=True)

            st.plotly_chart(g_frontera(nube, front, uni, w_tan, w_mv, rf, plazo),
                            width="stretch", config={"displayModeBar": False})

            cA, cB = st.columns([1.1, 1])
            with cA:
                st.plotly_chart(g_pesos(ids, nombres, w_tan, costo_presupuesto),
                                width="stretch", config={"displayModeBar": False})
            with cB:
                pesos_df = pd.DataFrame({
                    "id_tipo_obra": ids, "Linea de negocio": nombres,
                    "Peso tangente": w_tan, "Monto tangente": w_tan * costo_presupuesto,
                    "Peso min. varianza": w_mv, "Monto min. varianza": w_mv * costo_presupuesto,
                    "Rend. anual": uni.mu, "Riesgo anual": uni.sigma,
                    "Sharpe individual": (uni.mu - rf) / uni.sigma,
                })
                st.markdown("**Pesos optimos y estadisticos por linea**")
                st.dataframe(pesos_df.style.format({
                    "Peso tangente": "{:.2%}", "Peso min. varianza": "{:.2%}",
                    "Monto tangente": "${:,.0f}", "Monto min. varianza": "${:,.0f}",
                    "Rend. anual": "{:.2%}", "Riesgo anual": "{:.2%}", "Sharpe individual": "{:.3f}",
                }), width="stretch", hide_index=True, height=330)
                st.markdown(
                    f'<div class="nota">Restricciones activas: suma de pesos = 100%, '
                    f'{w_min:.0%} &#8804; w<sub>i</sub> &#8804; {w_max:.0%}, sin ventas en corto. '
                    f'Ventana de estimacion: ultimos {ventana} meses.</div>', unsafe_allow_html=True)

    # =================== T3. CORRELACION Y REGRESION ===================
    with t3:
        st.plotly_chart(g_correlacion(uni.corr, nombres), width="stretch",
                        config={"displayModeBar": False})
        if not reg.empty:
            c = st.columns(4)
            b_prom = float((reg["beta"]).mean())
            r2_prom = float(reg["r2"].mean())
            mas_exp = reg.loc[reg["beta"].idxmax()]
            mas_alfa = reg.loc[reg["alpha_anualizada"].idxmax()]
            c[0].markdown(tarjeta("Beta promedio del universo", f"{b_prom:,.3f}",
                                  "Sensibilidad media al indice", "val-neu"), unsafe_allow_html=True)
            c[1].markdown(tarjeta("R&#178; promedio", f"{r2_prom:,.3f}",
                                  "Proporcion de varianza explicada por el indice", "val-neu"),
                          unsafe_allow_html=True)
            c[2].markdown(tarjeta("Linea mas expuesta", f"β {mas_exp['beta']:,.2f}",
                                  mas_exp["linea_negocio"], "val-adv"), unsafe_allow_html=True)
            c[3].markdown(tarjeta("Mayor alfa anualizada", pct(mas_alfa["alpha_anualizada"]),
                                  mas_alfa["linea_negocio"], "val-pos"), unsafe_allow_html=True)

            st.plotly_chart(g_regresion(uni.retornos, idx.reindex(uni.retornos.index), ids, nombres,
                                        reg, etiqueta_indice),
                            width="stretch", config={"displayModeBar": False})
            st.plotly_chart(g_acumulado(uni.retornos, idx.reindex(uni.retornos.index), ids, nombres,
                                        etiqueta_indice),
                            width="stretch", config={"displayModeBar": False})
            st.markdown("**Resultados de la regresion por minimos cuadrados**")
            st.dataframe(reg.rename(columns={
                "linea_negocio": "Linea de negocio", "beta": "Beta", "alpha_mensual": "Alfa mensual",
                "alpha_anualizada": "Alfa anualizada", "correlacion": "Correlacion", "r2": "R2",
                "p_valor": "p-valor", "error_estandar_beta": "EE beta",
                "riesgo_sistematico": "Riesgo sistematico", "riesgo_especifico": "Riesgo especifico",
                "n": "Obs."}).style.format({
                    "Beta": "{:.3f}", "Alfa mensual": "{:.4f}", "Alfa anualizada": "{:.2%}",
                    "Correlacion": "{:.3f}", "R2": "{:.3f}", "p-valor": "{:.4f}", "EE beta": "{:.4f}",
                    "Riesgo sistematico": "{:.2%}", "Riesgo especifico": "{:.2%}"}),
                width="stretch", hide_index=True)
        else:
            st.warning("El indice seleccionado no tiene observaciones suficientes.")

    # =================== T4. BASE HISTORICA ===================
    with t4:
        c = st.columns(4)
        c[0].markdown(tarjeta("Obras en la muestra", f"{est.n_obras}", est.nivel_muestra, "val-neu"),
                      unsafe_allow_html=True)
        c[1].markdown(tarjeta("Ingresos historicos", mxn(muestra["monto_final_mxn"].sum()),
                              "Suma de la muestra", "val-neu"), unsafe_allow_html=True)
        c[2].markdown(tarjeta("Utilidad historica", mxn(muestra["utilidad_real_mxn"].sum()),
                              f"Margen {pct(muestra['utilidad_real_mxn'].sum() / max(muestra['monto_final_mxn'].sum(), 1))}",
                              "val-pos"), unsafe_allow_html=True)
        c[3].markdown(tarjeta("Obras con perdida",
                              f"{int((muestra['utilidad_real_mxn'] < 0).sum())}",
                              f"{(muestra['utilidad_real_mxn'] < 0).mean():.1%} de la muestra", "val-adv"),
                      unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        cols = ["id_proyecto", "nombre_proyecto", "nombre_linea_negocio", "nombre_cliente", "estado",
                "anio_cierre", "monto_final_mxn", "costo_presupuestado_mxn", "costo_real_mxn",
                "utilidad_real_mxn", "margen_real_pct", "desviacion_costo_pct", "retraso_pct",
                "riesgo_ejecucion_materializado", "riesgo_comercial_materializado",
                "riesgo_financiero_materializado", "causa_principal_desviacion", "resultado"]
        st.dataframe(muestra[[c for c in cols if c in muestra.columns]].style.format({
            "monto_final_mxn": "${:,.0f}", "costo_presupuestado_mxn": "${:,.0f}",
            "costo_real_mxn": "${:,.0f}", "utilidad_real_mxn": "${:,.0f}",
            "margen_real_pct": "{:.2%}", "desviacion_costo_pct": "{:.2%}", "retraso_pct": "{:.1%}",
            "anio_cierre": "{:.0f}"}), width="stretch", hide_index=True, height=430)

        supuestos = pd.DataFrame({
            "Parametro": ["Linea de negocio evaluada", "Estado", "Plazo (anos)",
                          "Costo presupuesto (MXN)", "Tasa libre de riesgo", "Peso minimo",
                          "Peso maximo", "Ventana de estimacion (meses)", "Indice de referencia",
                          "Muestra de estimacion", "Fuente"],
            "Valor": [f"{linea_focus} - {nombre_de[linea_focus]}", estado, plazo,
                      f"{costo_presupuesto:,.0f}", f"{rf:.4f}", f"{w_min:.2f}", f"{w_max:.2f}",
                      ventana, etiqueta_indice, est.nivel_muestra, origen],
        })
        pesos_out = pd.DataFrame({
            "id_tipo_obra": ids, "linea_negocio": nombres,
            "peso_tangente": w_tan if w_tan is not None else np.nan,
            "monto_tangente_mxn": (w_tan * costo_presupuesto) if w_tan is not None else np.nan,
            "peso_min_varianza": w_mv if w_mv is not None else np.nan,
            "rend_anual": uni.mu, "riesgo_anual": uni.sigma})
        front_out = (front.assign(**{f"w_{c}": front["pesos"].apply(lambda v, i=i: v[i])
                                     for i, c in enumerate(ids)}).drop(columns=["pesos"])
                     if not front.empty else pd.DataFrame())
        st.download_button(
            "Descargar resultados en Excel",
            data=exportar_excel(est_df, pesos_out, front_out, uni.corr, reg, supuestos),
            file_name=f"Resultados_Markowitz_{linea_focus}_{plazo}a.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # =================== T5. METODOLOGIA ===================
    with t5:
        st.markdown(f"""
### 1. Definicion del activo
El activo del portafolio es la **linea de negocio** (`id_tipo_obra`), no la obra individual:
las obras se cierran y las lineas persisten los cinco anos, por lo que solo estas admiten
serie historica comparable de 60 periodos.

### 2. Estimacion del proyecto
Sobre la muestra historica que corresponde a la linea y al estado capturados
(con degradacion automatica a nivel nacional cuando hay menos de {MIN_OBS} obras):

| Salida | Formula |
|---|---|
| Desviacion de costo | `d = promedio(desviacion_costo_pct)` de la muestra |
| Costo real | `Costo real = Costo presupuesto x (1 + d)` |
| Ingreso del contrato | `I = Costo presupuesto / (1 - margen presupuestado promedio)` |
| Monto final | `MF = I x (1 + aditivas promedio)` |
| Utilidad real | `U = MF - Costo real` |
| Margen real | `U / MF` |
| Escenarios | `p10` y `p90` de la distribucion historica de `desviacion_costo_pct` |

### 3. Los tres riesgos
Cada riesgo se estima con su frecuencia empirica en la muestra y se lleva al plazo elegido:

`p_anual = 1 - (1 - p_obra)^(1/duracion_promedio)`  y  `p_plazo = 1 - (1 - p_anual)^T`

El impacto es la diferencia de sobrecosto entre obras con el evento y obras sin el:
`impacto = promedio(d | evento=1) - promedio(d | evento=0)`.
La perdida esperada del riesgo es `p_plazo x impacto x Costo presupuesto`.

### 4. Markowitz
- Rendimiento esperado anualizado: `mu = media mensual x 12`
- Covarianza anualizada: `Sigma = cov muestral mensual (n-1) x 12`
- Riesgo del portafolio: `sigma_p = raiz(w' Sigma w)`
- Frontera: `min w'Sigma w` sujeto a `w'mu = R`, `suma(w) = 1`, `{w_min:.0%} <= w_i <= {w_max:.0%}`
- Portafolio tangente: `max (w'mu - rf) / raiz(w'Sigma w)` con `rf = {rf:.2%}` anual
- Horizonte: `mu_T = mu x T`, `sigma_T = sigma x raiz(T)` (supuesto i.i.d.)
- VaR parametrico al 95%: `Capital x (mu_T - 1.645 x sigma_T)`

### 5. Regresion contra el indice
Modelo de mercado de una variable estimado por minimos cuadrados sobre los 60 periodos:

`r_i,t = alfa_i + beta_i x r_indice,t + e_i,t`

`beta` mide la exposicion sistematica, `alfa` el rendimiento no explicado por el indice,
`R2` la proporcion de varianza explicada, y el riesgo se descompone en
sistematico (`|beta| x sigma_indice`) y especifico (`sigma` del residual), ambos anualizados.

### 6. Limites del modelo
Los datos del libro son hipoteticos y construidos con un modelo de factores. La estimacion
por submuestra pierde precision cuando hay pocas obras: el nivel de muestra utilizado se
declara siempre en la pestana **Proyecto**. El escalamiento al plazo supone rendimientos
independientes entre periodos.
""")

    st.markdown(
        f'<div class="nota" style="margin-top:22px">Base: {origen.split("/")[-1]} &#183; '
        f'{len(proy)} obras cerradas &#183; {len(uni.retornos)} periodos mensuales &#183; '
        f'{len(ids)} lineas en el universo. Datos hipoteticos de referencia; el modelo no '
        f'sustituye el juicio tecnico de la direccion de obra.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
