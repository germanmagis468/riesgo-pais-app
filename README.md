# Riesgo País Argentina — Streamlit App (v4 con Rava API)

**Novedad:** integración directa con la **API pública de Rava** para obtener el precio de AL30D/GD30D/AE38D en vivo (JSON), sin scraping.
- En la barra lateral, dejá la **fuente** en "Auto (recomendado)" o elegí **"Rava API"**.
- También podés pegar un **símbolo** (ej: `AL30D`) o la URL del perfil de Rava (ej: `https://www.rava.com/perfil/AL30D`) en el modo "Manual / URL personalizada".
- El spread se calcula como: `(rend_ARG_aprox - UST10Y) * 100` (puntos básicos).
- Incluye gráfico en vivo (sesión), histórico con medias móviles y descarga de CSV.

> Aviso: el rendimiento argentino es **aproximado** a partir del precio (no YTM exacto).
