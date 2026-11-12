# Agente de preguntas básicas — Red Salud Andina (ficticia)

Chat en Streamlit + modelo Gemini. Responde solo con `base_conocimiento.md`, sigue las reglas de `instrucciones.md`
y, cuando no puede resolver, registra el texto de la pregunta (sin datos personales) y deriva al canal humano.

## Ejecutar en local
1. `python -m venv venv` y activarlo; `pip install -r requirements.txt`
2. Copiar `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y poner su clave de Google AI Studio.
3. `streamlit run app.py`
4. Pruebas: `python correr_pruebas.py` (genera `resultados_pruebas.csv`).

## Archivos
- `instrucciones.md`: comportamiento. `base_conocimiento.md`: única fuente de datos.
- `agent.py`: modelo, herramienta de registro, limpieza de datos personales. `app.py`: interfaz.
Las claves viven solo en secretos del servidor; no hay claves en el repositorio.
