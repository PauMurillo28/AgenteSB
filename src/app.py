import pandas as pd
import streamlit as st

import agent

st.set_page_config(page_title="Asistente Red Salud Andina", page_icon="🩺")
st.title("🩺 Asistente de Red Salud Andina")
st.caption("Resuelvo dudas sobre sedes, horarios, requisitos y costos. "
           "No agendo citas ni doy consejo médico. Por favor no escriba datos personales.")

SALUDO = ("Hola, soy el asistente de Red Salud Andina. Puedo ayudarle con sedes, horarios, "
          "requisitos y costos de consulta. ¿Qué necesita saber?")

if "mensajes" not in st.session_state:
    st.session_state.mensajes = [{"role": "assistant", "content": SALUDO}]

for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.write(m["content"])

if pregunta := st.chat_input("Escriba su pregunta aquí"):
    pregunta = pregunta[:500]
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.write(pregunta)
    with st.chat_message("assistant"):
        with st.spinner("Un momento..."):
            texto = agent.responder(st.session_state.mensajes)
        st.write(texto)
    st.session_state.mensajes.append({"role": "assistant", "content": texto})

# Vista del registro para la operación (protegida con clave; útil para mostrar la fila en el video)
with st.sidebar:
    with st.expander("Registro (operación)"):
        clave = st.text_input("Clave", type="password")
        if clave and clave == agent.secret("ADMIN_KEY"):
            if agent.LOG_PATH.exists():
                st.dataframe(pd.read_csv(agent.LOG_PATH))
            else:
                st.write("Aún no hay registros locales (si usa Google Sheets, ábrala allí).")
