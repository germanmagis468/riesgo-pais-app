import streamlit as st
import yfinance as yf
import pandas as pd
import requests, re
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, Tuple

st.set_page_config(page_title="Riesgo País Argentina", layout="wide")
st.title("📉 Riesgo País Argentina - Monitoreo en tiempo real")

TICKERS_ARG = {
    "AL30D (USD)": "AL30D.BA",
    "GD30D (USD)": "GD30D.BA",
    "AE38D (USD)": "AE38D.BA",
}
UST_TICKER = "^TNX"
DEFAULT_SYMBOL_NAME = "AL30D (USD)"

st.sidebar.header("⚙️ Configuración")
symbol_name = st.sidebar.selectbox("Bono argentino (USD)", list(TICKERS_ARG.keys()), index=list(TICKERS_ARG.keys()).index(DEFAULT_SYMBOL_NAME))
SYMBOL = TICKERS_ARG[symbol_name]

intervalo_seg = st.sidebar.slider("Intervalo de actualización (segundos)", 30, 600, 60)
umbral = st.sidebar.number_input("Umbral de alerta (pb)", value=2500)

st.sidebar.markdown("### Fuente para el precio del bono 🇦🇷")
fuente = st.sidebar.selectbox("Preferencia de fuente", ["Auto (recomendado)", "Yahoo Finance", "Rava", "InvertirOnline", "Manual"])
precio_manual = None
if fuente == "Manual":
    precio_manual = st.sidebar.number_input("Precio manual del bono (USD)", min_value=0.0, value=30.0, step=0.1)

st.sidebar.info(
    "Si una fuente falla, la app intenta otra. El rendimiento argentino se **aproxima** a partir del precio (no YTM exacto)."
)

st.sidebar.markdown("### 📅 Histórico por mes")
año = st.sidebar.selectbox("Año", list(range(2019, datetime.now().year + 1)), index=max(0, (datetime.now().year - 2019)))
mes = st.sidebar.selectbox("Mes", list(range(1,13)), index=datetime.now().month-1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

@st.cache_data(ttl=90)
def fetch_price_yahoo(ticker: str) -> Optional[float]:
    try:
        t = yf.Ticker(ticker)
        h = t.history(period="5d")
        if not h.empty:
            return float(h["Close"].dropna().iloc[-1])
        h2 = t.history(period="5d", interval="30m")
        if not h2.empty:
            return float(h2["Close"].dropna().iloc[-1])
        return None
    except Exception:
        return None

@st.cache_data(ttl=120)
def fetch_price_rava(symbol_plain: str) -> Optional[float]:
    try:
        sym = symbol_plain.replace(".BA", "").upper()
        url = f"https://www.rava.com/perfil/{sym}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        html = r.text
        m = re.search(r'"ultima"\s*:\s*"?([\d\.,]+)"?', html, flags=re.IGNORECASE)
        if m:
            val = m.group(1).replace(".", "").replace(",", ".")
            return float(val)
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        m2 = re.search(r"Último[:\s]+([\d\.,]+)", text)
        if m2:
            val = m2.group(1).replace(".", "").replace(",", ".")
            return float(val)
        return None
    except Exception:
        return None

@st.cache_data(ttl=120)
def fetch_price_iol(symbol_plain: str) -> Optional[float]:
    try:
        sym = symbol_plain.replace(".BA", "").upper()
        urls = [
            "https://iol.invertironline.com/mercado/cotizaciones/argentina/bonos/todos",
            "https://iol.invertironline.com/mercado/cotizaciones/argentina/bonos",
        ]
        for url in urls:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            pat = rf"{sym}[^0-9]{{0,40}}([\d]{{1,3}}(?:[\.\\s]?\d{{3}})*(?:,\d+))"
            m = re.search(pat, r.text, flags=re.IGNORECASE)
            if m:
                raw = m.group(1)
                val = raw.replace(".", "").replace(" ", "").replace(",", ".")
                return float(val)
        return None
    except Exception:
        return None

@st.cache_data(ttl=90)
def fetch_ust_yield() -> Optional[float]:
    try:
        t = yf.Ticker(UST_TICKER)
        h = t.history(period="5d")
        if not h.empty:
            return float(h["Close"].dropna().iloc[-1])
        return None
    except Exception:
        return None

def get_bono_price(symbol: str, fuente_pref: str) -> Tuple[Optional[float], str]:
    if fuente_pref == "Manual":
        return precio_manual, "Manual"
    elif fuente_pref == "Yahoo Finance":
        order = ["yahoo", "rava", "iol"]
    elif fuente_pref == "Rava":
        order = ["rava", "yahoo", "iol"]
    elif fuente_pref == "InvertirOnline":
        order = ["iol", "yahoo", "rava"]
    else:
        order = ["yahoo", "rava", "iol"]

    for src in order:
        if src == "yahoo":
            p = fetch_price_yahoo(symbol)
            if p is not None:
                return p, "Yahoo"
        elif src == "rava":
            p = fetch_price_rava(symbol)
            if p is not None:
                return p, "Rava"
        elif src == "iol":
            p = fetch_price_iol(symbol)
            if p is not None:
                return p, "InvertirOnline"
    return None, "Ninguna"

@st.cache_data(ttl=60)
def obtener_riesgo_actual(symbol: str, fuente_pref: str):
    precio_arg, fuente_usada = get_bono_price(symbol, fuente_pref)
    rend_usa = fetch_ust_yield()

    if precio_arg is None or rend_usa is None:
        return None, None, rend_usa, precio_arg, fuente_usada

    rendimiento_arg = max(0.0, (100.0 / float(precio_arg)) * 10.0)
    riesgo_pb = (rendimiento_arg - rend_usa) * 100.0
    return riesgo_pb, rendimiento_arg, rend_usa, float(precio_arg), fuente_usada

@st.cache_data(ttl=600)
def obtener_historico(symbol: str) -> Optional[pd.DataFrame]:
    try:
        precio = yf.Ticker(symbol).history(period="5y")["Close"]
        ust = yf.Ticker(UST_TICKER).history(period="5y")["Close"]
        if precio.empty or ust.empty:
            return None
        df = pd.DataFrame({"precio_arg": precio, "rend_usa": ust}).dropna()
        df["riesgo_pb"] = (100.0 / df["precio_arg"] * 10.0 - df["rend_usa"]) * 100.0
        df["mm7"] = df["riesgo_pb"].rolling(7).mean()
        df["mm30"] = df["riesgo_pb"].rolling(30).mean()
        df["año"] = df.index.year
        df["mes"] = df.index.month
        return df
    except Exception:
        return None

if "live_data" not in st.session_state:
    st.session_state.live_data = pd.DataFrame(columns=["timestamp", "riesgo_pb"])

riesgo_pb, rend_arg, rend_usa, precio_arg, fuente_usada = obtener_riesgo_actual(SYMBOL, fuente)

col1, col2, col3, col4, col5 = st.columns(5)
if riesgo_pb is not None:
    estado = "🟢 Bajo" if riesgo_pb < 1500 else ("🟠 Medio" if riesgo_pb < 2500 else "🔴 Alto")
    col1.metric("Riesgo País (último)", f"{riesgo_pb:,.0f} pb", estado)
    col2.metric("Rend. ARG (aprox)", f"{rend_arg:,.2f} %")
    col3.metric("UST 10Y", f"{rend_usa:,.2f} %")
    col4.metric(f"{symbol_name} precio", f"{precio_arg:,.2f} USD")
    col5.metric("Fuente usada", fuente_usada)
else:
    tips = []
    if fuente_usada == "Ninguna":
        tips.append("Probá cambiar la **fuente** (Rava / IOL / Yahoo).")
    if fuente == "Manual":
        tips.append("Ingresá el **precio manual** para continuar.")
    st.error("No se pudo obtener el dato en vivo. " + " ".join(tips))

if riesgo_pb is not None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.live_data.loc[len(st.session_state.live_data)] = [ts, riesgo_pb]

st.subheader("Evolución en vivo (sesión actual)")
if not st.session_state.live_data.empty:
    df_live = st.session_state.live_data.set_index("timestamp")
    df_live["mm7"] = df_live["riesgo_pb"].rolling(7).mean()
    st.line_chart(df_live)
    csv_live = df_live.to_csv().encode("utf-8")
    st.download_button("⬇️ Descargar CSV (sesión)", data=csv_live, file_name="riesgo_pais_sesion.csv", mime="text/csv")

st.divider()

st.subheader("📊 Comparación histórica por mes")
df_hist = obtener_historico(SYMBOL)
if df_hist is None or df_hist.empty:
    st.warning("No se pudieron cargar datos históricos desde Yahoo para el bono seleccionado.")
else:
    df_mes = df_hist[(df_hist["año"] == año) & (df_hist["mes"] == mes)]
    if df_mes.empty:
        st.info("No hay datos disponibles para ese mes/año.")
    else:
        st.line_chart(df_mes[["riesgo_pb", "mm7", "mm30"]])
        csv_mes = df_mes.to_csv().encode("utf-8")
        st.download_button("⬇️ Descargar CSV (mes seleccionado)", data=csv_mes, file_name=f"riesgo_pais_{symbol_name.replace(' ','_')}_{año}_{mes}.csv", mime="text/csv")

st.divider()

st.markdown(
    f"""
    <script>
    setTimeout(function() {{ window.location.reload(); }}, {int(intervalo_seg)*1000});
    </script>
    """,
    unsafe_allow_html=True
)
