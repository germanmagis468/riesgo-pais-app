import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Tuple, Optional

st.set_page_config(page_title="Riesgo País Argentina", layout="wide")
st.title("📉 Riesgo País Argentina - Monitoreo en tiempo real")

# --- Parámetros base ---
BOND_ARG = "GD30D.BA"   # Bono argentino en USD (precio)
BOND_USA = "^TNX"        # Bono del Tesoro de EE.UU. a 10 años (rendimiento %)

# --- Sidebar (configuración de usuario) ---
st.sidebar.header("⚙️ Configuración")
intervalo_seg = st.sidebar.slider("Intervalo de actualización (segundos)", 30, 600, 60)
umbral = st.sidebar.number_input("Umbral de alerta (pb)", value=2500)
periodo_hist = st.sidebar.selectbox("Período histórico", ["1y", "2y", "5y", "max"], index=0)
st.sidebar.info(
    "Los datos provienen de Yahoo Finance (GD30D.BA y ^TNX).\n"
    "El cálculo del rendimiento argentino es **estimado** a partir del precio del bono (aprox.)."
)

@st.cache_data(ttl=30)
def obtener_riesgo_actual() -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Devuelve (riesgo_pb, rendimiento_arg_%_aprox, rendimiento_usa_%, precio_arg_usd)."""
    try:
        bono_arg = yf.Ticker(BOND_ARG)
        bono_usa = yf.Ticker(BOND_USA)

        # Precio de cierre más reciente del GD30D
        hist_arg = bono_arg.history(period="1d")
        if hist_arg.empty:
            return None, None, None, None
        precio_arg = float(hist_arg["Close"].iloc[-1])

        # Rendimiento USA 10y (%)
        hist_usa = bono_usa.history(period="1d")
        if hist_usa.empty:
            return None, None, None, None
        rendimiento_usa = float(hist_usa["Close"].iloc[-1])

        # Aproximación de rendimiento del bono argentino en %.
        # NOTA: Para un cálculo exacto se requiere YTM; aquí usamos una relación inversa simple.
        rendimiento_arg = max(0.0, (100.0 / precio_arg) * 10.0)

        riesgo_pb = (rendimiento_arg - rendimiento_usa) * 100.0
        return riesgo_pb, rendimiento_arg, rendimiento_usa, precio_arg
    except Exception as e:
        return None, None, None, None

@st.cache_data(ttl=300)
def obtener_riesgo_historico(periodo: str) -> Optional[pd.DataFrame]:
    """Calcula serie histórica estimada de riesgo país para el período elegido."""
    try:
        bono_arg = yf.Ticker(BOND_ARG).history(period=periodo)["Close"]
        bono_usa = yf.Ticker(BOND_USA).history(period=periodo)["Close"]
        if bono_arg.empty or bono_usa.empty:
            return None

        # Alinear índices por si difieren
        df = pd.DataFrame({"precio_arg": bono_arg, "rend_usa": bono_usa}).dropna()

        # Cálculo estimado de riesgo país (pb)
        df["riesgo_pb"] = (100.0 / df["precio_arg"] * 10.0 - df["rend_usa"]) * 100.0
        df["mm_7"] = df["riesgo_pb"].rolling(7).mean()
        df["mm_30"] = df["riesgo_pb"].rolling(30).mean()
        return df
    except Exception:
        return None

# --- Estado de sesión para acumular lecturas en vivo ---
if "live_data" not in st.session_state:
    st.session_state.live_data = pd.DataFrame(columns=["timestamp", "riesgo_pb"])

# --- Actualización en vivo mediante autorefresh ---
# Cada recarga de la página re-ejecuta el script y agrega la lectura actual.
st_autorefresh = st.experimental_rerun  # alias para compatibilidad si cambia la API

# Obtener lectura actual
riesgo_pb, rend_arg, rend_usa, precio_arg = obtener_riesgo_actual()

col1, col2, col3, col4 = st.columns(4)
if riesgo_pb is not None:
    estado = "🟢 Bajo" if riesgo_pb < 1500 else ("🟠 Medio" if riesgo_pb < 2500 else "🔴 Alto")
    col1.metric("Riesgo País (último)", f"{riesgo_pb:,.0f} pb", estado)
    col2.metric("Rend. ARG (aprox)", f"{rend_arg:,.2f} %")
    col3.metric("UST 10Y", f"{rend_usa:,.2f} %")
    col4.metric("GD30D precio", f"{precio_arg:,.2f} USD")
else:
    st.error("No se pudo obtener el dato en vivo. Intentá nuevamente.")

# Agregar punto a la serie en vivo
if riesgo_pb is not None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.live_data.loc[len(st.session_state.live_data)] = [ts, riesgo_pb]

# --- Gráfico en vivo ---
st.subheader("Evolución en vivo (sesión actual)")
if not st.session_state.live_data.empty:
    df_live = st.session_state.live_data.set_index("timestamp")
    st.line_chart(df_live)

    # Descarga CSV de la sesión
    csv_live = df_live.to_csv().encode("utf-8")
    st.download_button("⬇️ Descargar CSV (sesión)", data=csv_live, file_name="riesgo_pais_sesion.csv", mime="text/csv")

# Alerta de umbral
if riesgo_pb is not None and riesgo_pb > umbral:
    st.warning(f"🚨 ALERTA: El riesgo país superó el umbral de {umbral:,.0f} pb. Valor actual: {riesgo_pb:,.0f} pb.")

st.divider()

# --- Comparación histórica ---
st.subheader("Comparación histórica (estimada)")
df_hist = obtener_riesgo_historico(periodo_hist)
if df_hist is None or df_hist.empty:
    st.info("No hay datos históricos disponibles para mostrar.")
else:
    tabs = st.tabs(["Serie", "Medias móviles"])
    with tabs[0]:
        st.line_chart(df_hist[["riesgo_pb"]])
    with tabs[1]:
        st.line_chart(df_hist[["riesgo_pb", "mm_7", "mm_30"]])

    csv_hist = df_hist.to_csv().encode("utf-8")
    st.download_button("⬇️ Descargar CSV (histórico)", data=csv_hist, file_name=f"riesgo_pais_historico_{periodo_hist}.csv", mime="text/csv")

# --- Auto-refresco no bloqueante ---
# Usamos un truco con JavaScript para refrescar sin while True
st.markdown(
    f"""
    <script>
    setTimeout(function() {{ window.location.reload(); }}, {int(intervalo_seg)*1000});
    </script>
    """,
    unsafe_allow_html=True
)
