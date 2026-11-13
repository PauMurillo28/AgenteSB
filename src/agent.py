"""Agente: instrucciones (archivo local) + base de conocimiento (Firestore, con respaldo en .md)
+ modelo Gemini + registro de preguntas sin respuesta (Firestore, con respaldo en CSV)."""
import csv
import datetime
import os
import pathlib
import re
import threading
import time

from google import genai
from google.genai import types

BASE = pathlib.Path(__file__).parent
INSTRUCCIONES = (BASE / "instrucciones.md").read_text(encoding="utf-8")
LOG_PATH = pathlib.Path(os.environ.get("LOG_PATH", BASE / "logs" / "preguntas_sin_respuesta.csv"))
TTL_KB = 300  # segundos: cambios hechos en Firestore se reflejan en máximo 5 minutos
CONTADOR_REGISTROS = 0  # solo lo usa el script de pruebas
_kb = {"t": 0.0, "texto": ""}
_db_obj = None
_client_obj = None
_kb_lock = threading.Lock()
_db_lock = threading.Lock()


def secret(name, default=None):
    if os.environ.get(name):
        return os.environ[name]
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception as e:
        print(f"[secret] No pude leer '{name}' de st.secrets: {e!r}")
        return default


# ---------------- Firestore ----------------
def _db():
    global _db_obj
    with _db_lock:  # evita iniciar Firebase dos veces desde hilos distintos
        if _db_obj is not None:
            return _db_obj
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            ruta = os.environ.get("FIREBASE_CREDENTIALS_FILE")
            if ruta:
                cred = credentials.Certificate(ruta)
            else:
                import streamlit as st
                cred = credentials.Certificate(dict(st.secrets["firebase"]))
            firebase_admin.initialize_app(cred)
        _db_obj = firestore.client()
        return _db_obj


def _kb_desde_firestore() -> str:
    docs = _db().collection("base_conocimiento").where("activo", "==", True).stream(timeout=8, retry=None)
    filas = sorted((d.to_dict() for d in docs), key=lambda x: x.get("orden", 0))
    if not filas:
        raise ValueError("La colección base_conocimiento está vacía")
    partes, actual = [], None
    for f in filas:
        if f["seccion"] != actual:
            actual = f["seccion"]
            partes.append(f"\n## {actual}")
        partes.append(f"- {f['tema']}: {f['contenido']}")
    return "\n".join(partes)


def _refrescar_kb():
    t0 = time.time()
    try:
        texto = _kb_desde_firestore()
        print(f"[tiempo] KB desde Firestore: {time.time() - t0:.2f}s")
    except Exception as e:
        print(f"[kb] Firestore no disponible ({time.time() - t0:.1f}s), uso base_conocimiento.md: {e!r}")
        texto = (BASE / "base_conocimiento.md").read_text(encoding="utf-8")
    _kb.update(t=time.time(), texto=texto)


def base_conocimiento() -> str:
    """Devuelve la KB desde caché. Si venció, responde con la copia vieja y refresca en segundo
    plano (el usuario nunca espera a Firestore, salvo la primera vez)."""
    if _kb["texto"]:
        if time.time() - _kb["t"] >= TTL_KB and _kb_lock.acquire(blocking=False):
            def _bg():
                try:
                    _refrescar_kb()
                finally:
                    _kb_lock.release()
            threading.Thread(target=_bg, daemon=True).start()
        return _kb["texto"]
    with _kb_lock:  # primera carga: si ya hay otra en curso, espera a que termine
        if not _kb["texto"]:
            _refrescar_kb()
    return _kb["texto"]


def precalentar():
    """Carga la KB y abre la conexión mientras el usuario todavía está leyendo la página."""
    threading.Thread(target=base_conocimiento, daemon=True).start()


def construir_system() -> str:
    return INSTRUCCIONES + "\n\n# BASE DE CONOCIMIENTO\n" + base_conocimiento()


# ---------------- Registro de preguntas sin respuesta ----------------
def limpiar_pii(texto: str) -> str:
    texto = re.sub(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+", "[dato omitido]", texto)
    texto = re.sub(r"\+?\d[\d\s\-().]{5,}\d", "[dato omitido]", texto)
    return texto.strip()[:300]


def _guardar(pregunta: str):
    try:
        from firebase_admin import firestore
        _db().collection("preguntas_sin_respuesta").add(
            {"fecha": firestore.SERVER_TIMESTAMP, "pregunta": pregunta, "estado": "pendiente"})
        return
    except Exception as e:
        print(f"[registro] Firestore falló, uso CSV: {e!r}")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "pregunta_sin_respuesta"])
        w.writerow([datetime.date.today().isoformat(), pregunta])


def leer_registros(n: int = 50) -> list:
    """Últimos registros para la vista de operación."""
    try:
        from firebase_admin import firestore
        docs = (_db().collection("preguntas_sin_respuesta")
                .order_by("fecha", direction=firestore.Query.DESCENDING).limit(n).stream())
        return [{"fecha": str(d.get("fecha"))[:16], "pregunta": d.get("pregunta"),
                 "estado": d.get("estado")} for d in docs]
    except Exception as e:
        print(f"[registro] No pude leer Firestore: {e!r}")
        if LOG_PATH.exists():
            with open(LOG_PATH, encoding="utf-8") as f:
                return list(csv.DictReader(f))
        return []


def registrar_pregunta_sin_respuesta(pregunta: str) -> str:
    """Registra una duda informativa sobre Red Salud Andina cuya respuesta no se tiene
    (ej.: valor de un examen). NO usar para agendar o consultar citas, resultados, consejo
    médico, saludos ni temas ajenos a la red. Enviar SOLO el texto de la pregunta, sin
    nombres, documentos, teléfonos ni otros datos personales."""
    global CONTADOR_REGISTROS
    CONTADOR_REGISTROS += 1
    threading.Thread(target=_guardar, args=(limpiar_pii(pregunta),)).start()  # no hace esperar al usuario
    return "Listo. No menciones este registro al usuario; solo indícale el canal de contacto adecuado."


# ---------------- Modelo ----------------
def _modelos():
    return [m.strip() for m in secret("MODELS", "gemini-3.5-flash,gemini-3.5-flash-lite").split(",")]


def _cliente():
    global _client_obj
    if _client_obj is None:
        _client_obj = genai.Client(api_key=secret("GEMINI_API_KEY"))
    return _client_obj


def responder(historial: list) -> str:
    client = _cliente()
    contenido = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part(text=m["content"])])
        for m in historial[-12:]
    ]
    config = types.GenerateContentConfig(
        system_instruction=construir_system(),
        tools=[registrar_pregunta_sin_respuesta],
        temperature=0.2,
        max_output_tokens=800,
    )
    ultimo_error = None
    for modelo in _modelos():
        try:
            t0 = time.time()
            r = client.models.generate_content(model=modelo, contents=contenido, config=config)
            print(f"[tiempo] modelo {modelo}: {time.time() - t0:.2f}s")
            if r.text:
                return r.text.strip()
        except Exception as e:
            print(f"Falló el modelo {modelo}: {e}")
            ultimo_error = e
    print("Error del modelo:", ultimo_error)
    return ("Tuve un problema técnico. Puede escribir de nuevo en unos segundos o llamar al "
            "(601) 555 0100 (L–V 7:00–19:00, sáb 8:00–14:00).")


precalentar()