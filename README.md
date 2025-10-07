# Riesgo País Argentina — Streamlit App (Gratis)

App web para **monitorear en tiempo real** un estimador del **Riesgo País** de Argentina.
- Fuente de datos: Yahoo Finance (`GD30D.BA` y `^TNX`).
- El rendimiento argentino se **aproxima** a partir del precio (no es YTM exacto).
- Incluye: gráfico en vivo + comparación histórica + descarga CSV + alerta por umbral.

## Cómo ejecutar online (gratis)
1. Crea un repositorio en GitHub y sube estos archivos: `riesgo_pais_app.py`, `requirements.txt`, `README.md`.
2. Ve a https://share.streamlit.io (Streamlit Cloud) y conéctalo a tu repo.
3. Selecciona `riesgo_pais_app.py` como archivo principal y despliega.

## Notas
- Este es un estimador con fines educativos/indicativos.
- Para un cálculo exacto del spread soberano, se requiere el **rendimiento a vencimiento (YTM)** del bono argentino.
