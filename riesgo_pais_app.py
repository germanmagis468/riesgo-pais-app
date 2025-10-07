import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Tuple, Optional

st.set_page_config(page_title="Riesgo País Argentina", layout="wide")
st.title("📉 Riesgo País Argentina - Monitoreo en tiempo real")

# --- Parámetros base ---
BOND_ARG = "AL30D.BA"   # Bono argentino en USD (más estable que GD30D)
BOND_USA = "^TNX"        # Bono del Tesoro de EE.UU. a 10 años (rendimiento %)

# --- Sidebar (configuración de usuario) ---
st.sidebar.header("⚙️ Configuración")
intervalo_seg = st.sidebar.slider("Intervalo de actualización (segundos)", 30, 600, 60)
umbral = st.sidebar.number_input("Umbral de alerta (pb)", value=2500)
st.sidebar.info("Los datos provienen de Yahoo Finance (AL30D.BA y ^TNX).")

# Selector de rango histórico
st.sidebar.markdown("### 📅 Selección de período histórico")
año = st.sidebar.selectbox("Año", [2020, 2021, 2022, 2023, 2024, 2025], index=4)
mes = st.sidebar.selectbox("Mes", list(range(1,13)), index=datetime.now().month-1)

# --- Funciones ---
@st.cache_data(ttl=60)
def obtener_riesgo_actual() -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    try:
        bono_arg = yf.Ticker(BOND_ARG)
        bono_usa = yf.Ticker(BOND_USA)

        hist_arg = bono_arg.history(period="5d")
        hist_usa = bono_usa.history(period="5d")

        if hist_arg.empty or hist_usa.empty:
            return None, None, None, None

        precio_arg = float(hist_arg["Close"].iloc[-1])
        rendimiento_usa = float(hist_usa["Close"].iloc[-1])

        rendimiento_arg = max(0.0, (100.0 / precio_arg) * 10.0)
        riesgo_pb = (rendimiento_arg - rendimiento_usa) * 100.0
        return riesgo_pb, rendimiento_arg, rendimiento_usa, precio_arg
    except Exception:
        return None, None, None, None

@st.cache_data(ttl=600)
def obtener_historico_completo() -> Optional[pd.DataFrame]:
    """Descarga histórico completo y calcula riesgo país diario."""
    try:
        bono_arg = yf.Ticker(BOND_ARG).history(period="5y")["Close"]
        bono_usa = yf.Ticker(BOND_USA).history(period="5y")["Close"]
        df = pd.DataFrame({"precio_arg": bono_arg, "rend_usa": bono_usa}).dropna()
        df["riesgo_pb"] = (100.0 / df["precio_arg"] * 10.0 - df["rend_usa"]) * 100.0
        df["mm7"] = df["riesgo_pb"].rolling(7).mean()
        df["mm30"] = df["riesgo_pb"].rolling(30).mean()
        df["año"] = df.index.year
        df["mes"] = df.index.month
        return df
    except Exception:
        return None

# --- Datos actuales ---
riesgo_pb, rend_arg, rend_usa, precio_arg = obtener_riesgo_actual()

col1, col2, col3, col4 = st.columns(4)
if riesgo_pb is not None:
    estado = "🟢 Bajo" if riesgo_pb < 1500 else ("🟠 Medio" if riesgo_pb < 2500 else "🔴 Alto")
    col1.metric("Riesgo País (último)", f"{riesgo_pb:,.0f} pb", estado)
    col2.metric("Rend. ARG (aprox)", f"{rend_arg:,.2f} %")
    col3.metric("UST 10Y", f"{rend_usa:,.2f} %")
    col4.metric("AL30D precio", f"{precio_arg:,.2f} USD")
else:
    st.error("No se pudo obtener el dato en vivo (Yahoo Finance no devolvió valores).")

st.divider()

# --- Comparación histórica ---
st.subheader("📊 Comparación histórica (por mes)")
df_hist = obtener_historico_completo()

if df_hist is None or df_hist.empty:
    st.warning("No se pudieron cargar los datos históricos.")
else:
    df_mes = df_hist[(df_hist["año"] == año) & (df_hist["mes"] == mes)]
    if df_mes.empty:
        st.info("No hay datos disponibles para ese mes.")
    else:
        st.line_chart(df_mes[["riesgo_pb", "mm7", "mm30"]])
        csv_mes = df_mes.to_csv().encode("utf-8")
        st.download_button("⬇️ Descargar CSV (mes seleccionado)", data=csv_mes,
                           file_name=f"riesgo_pais_{año}_{mes}.csv", mime="text/csv")

st.divider()

# --- Auto-refresco ---
st.markdown(
    f"""
    <script>
    setTimeout(function() {{ window.location.reload(); }}, {int(intervalo_seg)*1000});
    </script>
    """,
    unsafe_allow_html=True
)
