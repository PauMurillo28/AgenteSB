import base64
import pathlib
import uuid

import pandas as pd
import streamlit as st
from PIL import Image

import agent

# ---------- Recursos gráficos (carpeta Media, al lado de src) ----------
MEDIA = pathlib.Path(__file__).resolve().parent.parent / "Media"
RUTA_AVATAR = MEDIA / "avatar.jpeg"
RUTA_LOGO = MEDIA / "LogoConFondo.jpeg"
RUTA_FAVICON = MEDIA / "LogoSinFondo.jpeg"


def _imagen(ruta):
    try:
        return Image.open(ruta)
    except Exception:
        return None


def _logo_html():
    """Logo incrustado en la barra (altura fija: se ve bien en escritorio y celular)."""
    try:
        b64 = base64.b64encode(RUTA_LOGO.read_bytes()).decode()
        return f'<img class="logo-barra" alt="Logo de Red Salud Andina" src="data:image/jpeg;base64,{b64}">'
    except Exception:
        return ""


AVATAR = str(RUTA_AVATAR) if RUTA_AVATAR.exists() else "🩺"

# set_page_config debe ser la primera instrucción de Streamlit
st.set_page_config(
    page_title="Asistente Red Salud Andina",
    page_icon=_imagen(RUTA_FAVICON) or "🩺",  # ícono de la pestaña del navegador
    layout="centered",
)

# ---------- Estado de accesibilidad ----------
TEMAS = {
    "Claro": dict(bg="#FFFFFF", fg="#1F2937", panel="#F1F5F9", campo="#FFFFFF", borde="#CBD5E1", acento="#0B6E99", esquema="light"),
    "Oscuro": dict(bg="#0E1117", fg="#E6EDF3", panel="#1A1F2B", campo="#262D3B", borde="#3A4252", acento="#4FB3E8", esquema="dark"),
    "Alto contraste": dict(bg="#000000", fg="#FFFFFF", panel="#000000", campo="#000000", borde="#FFFFFF", acento="#FFD400", esquema="dark"),
}
ORDEN_TEMAS = list(TEMAS)
FS_MIN, FS_MAX, FS_PASO, FS_BASE = 14, 28, 2, 18

st.session_state.setdefault("tema", "Claro")
st.session_state.setdefault("fs", FS_BASE)
st.session_state.setdefault("sesion", uuid.uuid4().hex[:12])  # id aleatorio, sin datos personales


def siguiente_tema():
    i = ORDEN_TEMAS.index(st.session_state.tema)
    st.session_state.tema = ORDEN_TEMAS[(i + 1) % len(ORDEN_TEMAS)]


def cambiar_fuente(delta):
    st.session_state.fs = max(FS_MIN, min(FS_MAX, st.session_state.fs + delta))


def restablecer_fuente():
    st.session_state.fs = FS_BASE


# ---------- Barra superior FIJA: logo + accesibilidad (siempre visible, fuera del chat) ----------
with st.container(key="barra_fija"):
    st.markdown(f'<div class="fila-logo">{_logo_html()}<div class="titulo-barra">Asistente de Red Salud Andina</div></div>',
                unsafe_allow_html=True)
    b_tema, b_menos, b_normal, b_mas = st.columns([4, 1, 1, 1], gap="small")
    with b_tema:
        st.button(f"🎨 {st.session_state.tema}", on_click=siguiente_tema, key="b_tema",
                  help="Cambiar entre claro, oscuro y alto contraste", use_container_width=True)
    with b_menos:
        st.button("A−", on_click=cambiar_fuente, args=(-FS_PASO,), key="b_menos", help="Achicar la letra",
                  disabled=st.session_state.fs <= FS_MIN, use_container_width=True)
    with b_normal:
        st.button("A", on_click=restablecer_fuente, key="b_normal", help="Tamaño normal de letra",
                  use_container_width=True)
    with b_mas:
        st.button("A+", on_click=cambiar_fuente, args=(FS_PASO,), key="b_mas", help="Agrandar la letra",
                  disabled=st.session_state.fs >= FS_MAX, use_container_width=True)

# ---------- Estilos (tema + tamaño de letra) ----------
t, fs = TEMAS[st.session_state.tema], st.session_state.fs
_css = f"""
<div class="css-inyectado"></div>
<style>
[data-testid="stElementContainer"]:has(.css-inyectado), .element-container:has(.css-inyectado) {{ display: none; }}
:root {{ --hbar: 7.4rem; }}

/* Ocultar el menú, la barra y el pie de Streamlit (sus ajustes de tema chocarían con los nuestros) */
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], footer, #MainMenu {{ display: none !important; }}

/* Fondo y textos */
.stApp {{ background: {t['bg']}; color-scheme: {t['esquema']}; }}
.stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp h1, .stApp h2, .stApp h3,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: {t['fg']} !important; }}
.block-container {{ padding-top: calc(var(--hbar) + 1rem) !important; padding-bottom: 7rem !important; }}

/* Barra fija superior */
.st-key-barra_fija {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000; box-sizing: border-box;
  background: {t['bg']}; border-bottom: 2px solid {t['borde']};
  padding: .6rem max(1rem, calc((100vw - 736px) / 2)) .7rem; gap: .6rem !important;
}}
.st-key-barra_fija [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: .5rem !important; }}
.st-key-barra_fija [data-testid="stColumn"], .st-key-barra_fija [data-testid="column"] {{ min-width: 0 !important; }}
.st-key-barra_fija [data-testid="stImage"] img {{ border-radius: 8px; }}
.fila-logo {{ display: flex; align-items: center; gap: .7rem; min-height: 44px; margin-bottom: .35rem; }}
.st-key-barra_fija [data-testid="stMarkdownContainer"] p {{ margin: 0; }}
.logo-barra {{ height: 42px; width: auto; border-radius: 8px; flex-shrink: 0; }}
.titulo-barra {{ font-size: clamp(.8rem, 4vw, 1.15rem); font-weight: 700; line-height: 1.15; color: {t['fg']}; }}

/* Botones */
.stButton button {{
  background: {t['campo']} !important; color: {t['fg']} !important; border: 2px solid {t['borde']} !important;
  font-weight: 700; padding: .25rem .15rem; min-height: 2.5rem; white-space: nowrap;
}}
.stButton button p {{ color: {t['fg']} !important; font-size: .9rem !important; white-space: nowrap; }}
.stButton button:hover:not(:disabled) {{ border-color: {t['acento']} !important; }}
.stButton button:disabled {{ opacity: .35; }}

/* Mensajes del chat */
[data-testid="stChatMessage"] {{ background: {t['panel']}; border: 1px solid {t['borde']}; border-radius: 12px; }}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {{ font-size: {fs}px !important; line-height: 1.55; }}
[data-testid="stCaptionContainer"] p {{ font-size: {max(fs - 3, 12)}px !important; }}

/* Cuadro de texto del chat (y cualquier campo de texto): cambia con el tema */
[data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {{ background: {t['bg']} !important; }}
[data-testid="stChatInput"], [data-testid="stChatInput"] div {{ background: {t['campo']} !important; }}
[data-testid="stChatInput"] {{ border: 2px solid {t['borde']} !important; border-radius: 12px; }}
[data-testid="stChatInput"] textarea {{
  background: {t['campo']} !important; color: {t['fg']} !important; -webkit-text-fill-color: {t['fg']} !important;
  font-size: {fs}px !important; caret-color: {t['fg']};
}}
[data-testid="stChatInput"] textarea::placeholder {{ color: {t['fg']} !important; opacity: .6; -webkit-text-fill-color: {t['fg']}; }}
[data-testid="stChatInput"] button {{ background: transparent !important; }}
[data-testid="stChatInput"] button svg {{ fill: {t['fg']} !important; color: {t['fg']} !important; }}
div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="base-input"] {{ background: {t['campo']} !important; }}
div[data-baseweb="input"] input {{ background: {t['campo']} !important; color: {t['fg']} !important; -webkit-text-fill-color: {t['fg']} !important; }}
[data-testid="stExpander"] details {{ background: {t['panel']}; border-color: {t['borde']}; }}
[data-testid="stExpander"] summary span, [data-testid="stExpander"] summary svg {{ color: {t['fg']} !important; fill: {t['fg']} !important; }}

[data-testid="stChatInput"] textarea:focus, [data-testid="stChatInput"] textarea:focus-visible {{ outline: none !important; box-shadow: none !important; }}
[data-testid="stChatInput"]:focus-within {{ border-color: {t['acento']} !important; box-shadow: 0 0 0 2px {t['acento']}; }}
div[data-baseweb="popover"]:has([data-testid="stTooltipContent"]), [data-testid="stTooltipContent"] {{ display: none !important; }}
*:focus-visible {{ outline: 3px solid {t['acento']} !important; outline-offset: 2px; }}
</style>
"""
# Markdown corta el bloque <style> en la primera línea vacía: se eliminan todas
st.markdown("\n".join(l for l in _css.splitlines() if l.strip()), unsafe_allow_html=True)

_aviso = (" Para mejorar el servicio, se guardan sus mensajes sin datos personales."
          if agent.logs_activos() else "")
st.caption("Resuelvo dudas sobre sedes, horarios, requisitos y costos. "
           "No agendo citas ni doy consejo médico. Por favor no escriba datos personales." + _aviso)

# ---------- Vista de registro para la operación: solo con ?admin en la dirección y clave ----------
if "admin" in st.query_params:
    with st.expander("Registro y analítica (operación)"):
        clave = st.text_input("Clave", type="password")
        if clave and clave == agent.secret("ADMIN_KEY"):
            tab1, tab2 = st.tabs(["Preguntas sin respuesta", "Conversaciones y métricas"])
            with tab1:
                filas = agent.leer_registros()
                if filas:
                    st.dataframe(pd.DataFrame(filas))
                else:
                    st.write("Aún no hay preguntas registradas.")
            with tab2:
                filas = agent.leer_interacciones(500)
                if not filas:
                    st.write("Aún no hay conversaciones guardadas.")
                else:
                    df = pd.DataFrame(filas)
                    por_sesion = df.groupby("sesion")["turno"].max()
                    m1, m2 = st.columns(2)
                    m1.metric("Conversaciones", int(por_sesion.size))
                    m2.metric("Mensajes del paciente por conversación", f"{por_sesion.mean():.1f}")
                    m3, m4 = st.columns(2)
                    m3.metric("Turnos con pregunta sin respuesta", f"{100 * df['registro_sin_respuesta'].mean():.0f}%")
                    m4.metric("Tiempo medio de respuesta (s)", f"{df['latencia_ms'].mean() / 1000:.1f}")
                    st.caption(f"Calculado sobre los últimos {len(df)} turnos guardados.")
                    cols = [c for c in ["fecha", "sesion", "turno", "pregunta", "respuesta",
                                        "registro_sin_respuesta", "latencia_ms", "lineas"] if c in df.columns]
                    st.dataframe(df[cols])
                    st.download_button("Descargar CSV", df.to_csv(index=False).encode("utf-8-sig"),
                                       "conversaciones.csv", "text/csv")

# ---------- Chat ----------
SALUDO = ("Hola, soy el asistente de Red Salud Andina. Puedo ayudarle con sedes, horarios, "
          "requisitos y costos de consulta. ¿Qué necesita saber?")

if "mensajes" not in st.session_state:
    st.session_state.mensajes = [{"role": "assistant", "content": SALUDO}]

for m in st.session_state.mensajes:
    with st.chat_message(m["role"], avatar=AVATAR if m["role"] == "assistant" else None):
        st.write(m["content"])

if pregunta := st.chat_input("Escriba su pregunta aquí"):
    pregunta = pregunta[:500]
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.write(pregunta)
    with st.chat_message("assistant", avatar=AVATAR):
        with st.spinner("Un momento..."):
            texto = agent.responder(st.session_state.mensajes, sesion=st.session_state.sesion)
        st.write(texto)
    st.session_state.mensajes.append({"role": "assistant", "content": texto})