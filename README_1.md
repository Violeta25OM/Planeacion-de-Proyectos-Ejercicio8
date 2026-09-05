# Frontera Eficiente · Portafolio de Proyectos de Construcción

Aplicación **Streamlit** que aplica el modelo de **frontera eficiente de Markowitz** a la
planeación de un portafolio de obra, tomando como activo la **línea de negocio** y como
insumo la base histórica de cinco años (2021–2025) del libro
`Base_Datos_Historica_5Anios_Construccion.xlsx`.

Además de optimizar la asignación del presupuesto, estima para un proyecto concreto su
**costo real**, **utilidad real**, **desviación de costo** y los **riesgos comercial, de
ejecución y financiero**, y grafica **correlación y regresión contra un índice de referencia**.

---

## 1. Contenido del repositorio

```
.
├── app.py                  # Aplicación completa (datos, modelo, gráficas, interfaz)
├── requirements.txt        # Dependencias
├── README.md               # Este documento
├── .streamlit/
│   └── config.toml         # Tema: verde sobre negro, Arial blanca
└── data/
    └── Base_Datos_Historica_5Anios_Construccion.xlsx
```

---

## 2. Instalación y ejecución local

```bash
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>

python -m venv .venv
source .venv/bin/activate          # Windows:  .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

La aplicación abre en `http://localhost:8501`.

## 3. Publicación en Streamlit Community Cloud

1. Subir el repositorio a GitHub **incluyendo la carpeta `data/`** con el libro de Excel.
2. Entrar a [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Seleccionar el repositorio, la rama `main` y el archivo principal `app.py`.
4. **Deploy**. Streamlit instala `requirements.txt` automáticamente.

Si prefiere no versionar la base, omita la carpeta `data/`: la aplicación muestra un
cargador de archivos en la barra lateral y funciona con el libro que se suba en sesión.

---

## 4. Fuente de datos

El libro se lee completo y se depuran los renglones de total y de nota al pie mediante el
patrón de la llave de cada hoja.

| Hoja | Uso en la aplicación |
|---|---|
| `Cat_TipoObra` | Catálogo de las 7 líneas de negocio (los activos del portafolio) |
| `Cat_Clientes` | Aporta el **estado** de cada obra a través del cliente contratante |
| `Proyectos_Historicos` | 62 obras cerradas: base de la estimación del proyecto y de los riesgos |
| `Rendimientos_Mensuales` | 60 periodos × 7 líneas: insumo de μ y de la matriz de covarianza |
| `Macro_Referencia` | Índices macro alternativos para la regresión |
| `Parametros` | Valores por omisión de capital, tasa libre de riesgo y límites de peso |
| `Correlacion`, `Covarianza` | Matrices precalculadas del libro, usadas como cotejo |

> La covarianza que calcula la aplicación reproduce la hoja `Covarianza` del libro con
> diferencia máxima del orden de 1e-17 (misma convención muestral, n−1).

---

## 5. Entradas de la aplicación

| Entrada | Descripción |
|---|---|
| **Línea de negocio** | Universo de líneas admitidas en el portafolio y línea del proyecto a evaluar |
| **Costo presupuesto** | Costo directo presupuestado en MXN. Es también el capital que se reparte entre líneas |
| **Estado** | Entidad federativa del cliente contratante (columna `estado` de `Cat_Clientes`) |
| **Plazo a calcular** | 1, 2, 3, 4 o 5 años |

Supuestos ajustables en el panel lateral: tasa libre de riesgo, peso mínimo y máximo por
línea, puntos de la frontera, carteras simuladas, ventana de estimación (24/36/48/60 meses)
e índice de referencia.

## 6. Salidas

**Pestaña Proyecto** — utilidad real, costo real, desviación de costo, pérdida esperada,
los tres riesgos con su probabilidad dentro del plazo, escenarios optimista/base/adverso y
tabla comparativa por línea de negocio.

**Pestaña Frontera eficiente** — nube de carteras factibles, frontera, línea del mercado de
capitales, portafolio tangente y de mínima varianza, pesos óptimos y monto asignado por línea.

**Pestaña Correlación y regresión** — matriz de correlación 7×7, regresión de cada línea
contra el índice con β, α, R² y p-valor, y rendimiento acumulado contra el índice.

**Pestaña Base histórica** — obras de la muestra utilizada y **descarga de resultados en Excel**
(supuestos, estimación, pesos óptimos, frontera, correlación y regresión).

---

## 7. Formulario del modelo

### 7.1 Estimación del proyecto

Sobre la muestra que corresponde a la línea y al estado capturados. La jerarquía es
`línea + estado → línea (nacional) → estado (todas las líneas) → portafolio completo`,
y baja de nivel solo cuando la submuestra tiene menos de 4 obras. El nivel utilizado se
declara siempre en pantalla.

| Salida | Fórmula |
|---|---|
| Desviación de costo | `d = promedio(desviacion_costo_pct)` |
| **Costo real** | `Costo real = Costo presupuesto × (1 + d)` |
| Ingreso del contrato | `I = Costo presupuesto / (1 − margen presupuestado promedio)` |
| Monto final | `MF = I × (1 + aditivas promedio)` |
| **Utilidad real** | `U = MF − Costo real` |
| Margen real | `U / MF` |
| Escenarios | percentiles `p10` y `p90` de `desviacion_costo_pct` |

### 7.2 Riesgo comercial, de ejecución y financiero

Frecuencia empírica en la muestra, trasladada al plazo evaluado:

```
p_anual = 1 − (1 − p_obra)^(1 / duración_promedio_en_años)
p_plazo = 1 − (1 − p_anual)^T
impacto = promedio(d | evento = 1) − promedio(d | evento = 0)
pérdida esperada = p_plazo × impacto × Costo presupuesto
```

### 7.3 Markowitz

```
μ      = media mensual × 12
Σ      = covarianza muestral mensual (n−1) × 12
σ_p    = √(wᵀ Σ w)
Frontera:   min wᵀΣw   s.a.  wᵀμ = R,  Σw = 1,  w_min ≤ w_i ≤ w_max
Tangente:   max (wᵀμ − r_f) / √(wᵀΣw)
Horizonte:  μ_T = μ × T ,  σ_T = σ × √T          (supuesto i.i.d.)
VaR 95%:    Capital × (μ_T − 1.645 × σ_T)
```

Sin ventas en corto: `w_i ≥ 0`. La optimización usa SLSQP (`scipy.optimize.minimize`).

### 7.4 Regresión contra el índice

Modelo de mercado de una variable, mínimos cuadrados sobre los 60 periodos:

```
r_i,t = α_i + β_i · r_índice,t + ε_i,t

riesgo sistemático = |β_i| · σ_índice · √12
riesgo específico  = σ(ε_i) · √12
```

Índices disponibles: portafolio interno equiponderado (predeterminado), PIB de la
construcción, INPC de construcción, precio del acero, precio del cemento y CETES 28 días.

---

## 8. Diseño

Formato bursátil / fintech: fondo negro `#000000`, paneles `#101314`, acento verde `#00E676`,
tipografía Arial blanca. La cromática de las series está validada para fondo oscuro
(banda de luminosidad OKLCH, piso de croma, separación para daltonismo y contraste ≥ 3:1),
y cada línea de negocio conserva su color aunque se filtre el universo. La matriz de
correlación usa escala divergente con gris neutro en cero; las magnitudes, una sola tinta.

## 9. Límites del modelo

Los datos del libro son hipotéticos, construidos con un modelo de factores. La estimación
por submuestra pierde precisión cuando hay pocas obras. El escalamiento al plazo supone
rendimientos independientes entre periodos. El resultado es un insumo de decisión, no un
sustituto del juicio técnico de la dirección de obra.

---

## 10. Licencia

MIT.
