"""Lógica del agente: prompt + base de conocimiento + modelo + registro de preguntas sin respuesta."""
import csv
import datetime
import os
import pathlib
import re

from google import genai
from google.genai import types

BASE = pathlib.Path(__file__).parent
SYSTEM = (
    (BASE / "instrucciones.md").read_text(encoding="utf-8")
    + "\n\n# BASE DE CONOCIMIENTO\n"
    + (BASE / "base_conocimiento.md").read_text(encoding="utf-8")
)
LOG_PATH = pathlib.Path(os.environ.get("LOG_PATH", BASE / "logs" / "preguntas_sin_respuesta.csv"))
CONTADOR_REGISTROS = 0  # solo lo usa el script de pruebas


def secret(name, default=None):
    """Lee primero variables de entorno y luego st.secrets (nunca claves en el código)."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return default


def limpiar_pii(texto: str) -> str:
    """Red de seguridad: borra correos y secuencias largas de números (documentos, teléfonos)."""
    texto = re.sub(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+", "[dato omitido]", texto)
    texto = re.sub(r"\+?\d[\d\s\-().]{5,}\d", "[dato omitido]", texto)
    return texto.strip()[:300]


def _guardar(fila: list):
    # 1) Google Sheets si está configurado
    sheet_id = secret("SHEET_ID")
    if sheet_id:
        try:
            import gspread
            import streamlit as st
            gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
            gc.open_by_key(sheet_id).sheet1.append_row(fila)
            return
        except Exception as e:  # si falla, no se pierde el registro
            print("Fallo Sheets, uso CSV:", e)
    # 2) CSV local
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "pregunta_sin_respuesta"])
        w.writerow(fila)


def registrar_pregunta_sin_respuesta(pregunta: str) -> str:
    """Registra para la operación una pregunta que no se pudo resolver con la base de
    conocimiento. Enviar SOLO el texto de la pregunta, sin nombres, documentos,
    teléfonos ni otros datos personales."""
    global CONTADOR_REGISTROS
    CONTADOR_REGISTROS += 1
    _guardar([datetime.date.today().isoformat(), limpiar_pii(pregunta)])
    return "Pregunta registrada. Ahora indícale al usuario el canal de derivación."


def _modelos():
    return [m.strip() for m in secret("MODELS", "gemini-2.5-flash,gemini-2.5-flash-lite").split(",")]


def responder(historial: list[dict]) -> str:
    """historial: [{'role': 'user'|'assistant', 'content': str}, ...]"""
    client = genai.Client(api_key=secret("GEMINI_API_KEY"))
    contenido = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in historial[-12:]  # limita el contexto
    ]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=[registrar_pregunta_sin_respuesta],  # el SDK ejecuta la función automáticamente
        temperature=0.2,
        max_output_tokens=800,
    )
    ultimo_error = None
    for modelo in _modelos():
        try:
            r = client.models.generate_content(model=modelo, contents=contenido, config=config)
            if r.text:
                return r.text.strip()
        except Exception as e:  # límite de cuota, modelo no disponible, etc.
            ultimo_error = e
    print("Error del modelo:", ultimo_error)
    return ("Tuve un problema técnico. Puede escribir de nuevo en unos segundos o llamar al "
            "(601) 555 0100 (L–V 7:00–19:00, sáb 8:00–14:00).")
