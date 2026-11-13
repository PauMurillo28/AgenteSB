## Enlaces:
Agente: https://red-saludandina-bot.streamlit.app
Versión Admin: https://red-saludandina-bot.streamlit.app/?admin=1 (ingresar la contraseña "admin" en la pestaña Registro y Analítica)

# Asistente de preguntas básicas — Red Salud Andina (caso ficticio)

Agente conversacional que responde dudas básicas de pacientes y familiares (sedes, horarios, requisitos,
cuotas, laboratorio, etc.) para descongestionar el call center. Solo **informa, orienta y deriva**: no agenda,
no consulta ni modifica citas, no ve datos de pacientes y no da consejo médico.

- **Agente en línea:** `[ENLACE AL AGENTE]` (se abre en el navegador, sin cuenta).
- **Límite del nivel gratuito:** `[indicar el límite de mensajes/minuto del modelo y de Streamlit]`.
- Todos los datos de Red Salud Andina son ficticios y provienen del anexo del ejercicio.

## Qué hace y qué no hace

| Hace | No hace |
|---|---|
| Responde en español, sin tecnicismos, en máximo 4 líneas | Agendar, cancelar o consultar citas |
| Pregunta lo mínimo y anticipa lo que la persona necesitará después | Mostrar resultados o datos personales |
| Usa solo la información del anexo (no inventa) | Dar consejo médico (ante emergencia indica el 123) |
| Si no sabe: lo dice, ofrece el canal humano con su horario y anota la pregunta sin datos personales | Pedir o guardar datos personales |

## Cómo funciona

```
Paciente ──► Interfaz web (Streamlit) ──► Agente (Gemini + instrucciones + base de conocimiento)
                                              │
                         ┌────────────────────┼─────────────────────────┐
                         ▼                    ▼                         ▼
               Firestore: base_conocimiento   Firestore: preguntas_sin_respuesta   Firestore: interacciones
               (con respaldo en el .md)       (solo el texto de la pregunta)       (turnos pregunta/respuesta)
```

1. La persona escribe en el chat (`src/app.py`).
2. `src/agent.py` arma las instrucciones (`src/instrucciones.md`) + la base de conocimiento y llama al modelo.
3. Si la duda es sobre Red Salud Andina y el dato no existe, el modelo usa la herramienta
   `registrar_pregunta_sin_respuesta` (solo texto, sin datos personales) y deriva al canal humano.
4. Cada turno se guarda (opcional) en `interacciones` para medir el servicio.

### Decisiones de diseño

- **Toda la base de conocimiento va en el prompt** (no se hace búsqueda por fragmentos): es corta y así el agente
  puede combinar datos (p. ej. orden + autorización + cuota) y anticipar lo siguiente. Si la base creciera
  mucho, el siguiente paso sería recuperación por fragmentos.
- **Base de conocimiento en Firestore con caché de 5 minutos y respaldo en `base_conocimiento.md`:** la operación
  puede corregirla sin volver a desplegar, y si Firestore falla el agente sigue funcionando.
- **Escrituras en segundo plano:** guardar registros no hace esperar al paciente.
- **Instrucciones en un archivo versionado** (`instrucciones.md`), separadas del código, para poder revisarlas
  y ajustarlas.
- **Limpieza de datos personales** antes de guardar (correos, números largos, nombres dichos con «me llamo»).
  Es una red de seguridad, no una garantía: por eso el agente además pide no compartir datos personales.
- **Claves solo en el servidor** (secretos), nunca en el navegador ni en el repositorio.

## Estructura

```
.
├── Media/                      # avatar y logos
├── src/
│   ├── app.py                  # interfaz (chat, accesibilidad, panel ?admin)
│   ├── agent.py                # modelo, herramienta de registro, Firestore, limpieza de datos personales
│   ├── instrucciones.md        # comportamiento del agente
│   ├── base_conocimiento.md    # información del anexo (fuente y respaldo)
│   ├── cargar_firestore.py     # carga base_conocimiento.md en Firestore
│   └── correr_pruebas.py       # corre las preguntas de prueba y genera un CSV para calificar
├── .streamlit/secrets.toml.example
├── requirements.txt
└── README.md
```

## Cómo reproducirlo

**Requisitos:** Python 3.11 o superior (funciona con 3.9, con avisos), una clave gratuita de Google AI Studio y,
para Firestore, un proyecto de Firebase (plan gratuito).

1. **Instalar**
   ```
   python -m venv venv
   .\venv\Scripts\Activate.ps1        # Windows (en Mac/Linux: source venv/bin/activate)
   pip install -r requirements.txt
   ```
2. **Configurar secretos:** copiar `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completar
   `GEMINI_API_KEY`, `ADMIN_KEY`, `MODELS` y la sección `[firebase]` (campos del JSON de la cuenta de servicio).
   Este archivo **no se sube al repositorio**. En la nube, se pegan en el panel de secretos de la plataforma.
3. **Firebase (una vez):** crear Firestore en modo producción (reglas cerradas; el servidor entra con la cuenta de
   servicio), descargar la clave de servicio **fuera del proyecto** y cargar la base:
   ```
   $env:FIREBASE_CREDENTIALS_FILE="C:\ruta\fuera\del\proyecto\clave.json"
   python src\cargar_firestore.py
   ```
   Sin Firebase, el agente funciona igual leyendo `base_conocimiento.md` (y guarda las preguntas sin respuesta en CSV).
4. **Ejecutar** (siempre desde la raíz):
   ```
   streamlit run src\app.py
   ```

### Variables de configuración

| Clave | Para qué |
|---|---|
| `GEMINI_API_KEY` | Clave del modelo |
| `MODELS` | Modelos en orden de preferencia (si el primero falla por cuota, usa el siguiente) |
| `ADMIN_KEY` | Clave para ver el panel de operación (`/?admin=1`) |
| `LOG_CONVERSACIONES` | `"1"` guarda cada turno; `"0"` lo apaga |
| `[firebase]` | Credenciales de la cuenta de servicio |

## Despliegue

Streamlit Community Cloud: repositorio público → *New app* → archivo principal `src/app.py` → pegar los secretos
→ acceso público. Los nombres de `Media/` deben coincidir exactamente en mayúsculas y minúsculas (la nube distingue).

Diseño para producción (no desplegado en este ejercicio): contenedor en **Cloud Run**, secretos en **Secret
Manager**, base de conocimiento y registros en **Firestore**, y analítica en **BigQuery + Looker Studio**.

## Pruebas y analítica

```
python src\correr_pruebas.py
```
Corre `[N]` preguntas (del anexo, ambiguas, fuera del anexo y «trampas»: consejo médico, datos personales,
inyección de instrucciones) y genera `resultados_pruebas.csv`, que se **califica a mano**. Las preguntas sin
respuesta de la prueba van a un CSV local y no al registro real.

Cómo se calcula cada cifra (completar con los resultados reales):

| Cifra | Cálculo | Resultado |
|---|---|---|
| Tasa de resolución | respuestas correctas y completas ÷ preguntas que el agente podía resolver con el anexo | `[ ]` de `[ ]` |
| Derivaciones correctas | casos fuera del anexo en que lo dijo, dio el canal y registró ÷ casos fuera del anexo | `[ ]` de `[ ]` |
| Mensajes por conversación | turnos del paciente ÷ conversaciones (panel `?admin=1`) | `[ ]` |
| Respuestas ≤ 4 líneas | filas con `lineas` ≤ 4 ÷ total | `[ ]` |
| Fallos de seguridad | respuestas que dieron consejo médico, inventaron o pidieron datos personales | `[ ]` |

Fallos encontrados y qué se cambió: `[describir al menos uno]`.

## Privacidad

Se guarda, sin datos personales: el texto de las preguntas que el agente no supo responder y, si
`LOG_CONVERSACIONES="1"`, cada turno (pregunta y respuesta) con un id de sesión aleatorio. No se guardan IP,
nombres ni documentos. El chat muestra un aviso a la persona cuando esto está activo.

## Límites conocidos y próximos pasos

- No distingue por sí solo si una consulta quedó resuelta: esa cifra sale de la calificación manual.
- La limpieza de datos personales es heurística.
- Dependencia del nivel gratuito del modelo (cuota por minuto/día).
- Siguientes pasos: revisión semanal de preguntas sin respuesta para ampliar la base, piloto con medición de
  adopción, canal de WhatsApp, y pasar a recuperación por fragmentos si la base crece.

## Uso de herramientas e IA

Herramientas usadas (incluida la IA) y para qué: Deep Search con Gemini 3.5 Flash Lite: Para la creación del plan de acción, investigación de plataformas y herramientas y redacción del guión.
Gemini 3.5 Flash Lite: Motor del agente.
Claude Sonnet 5.5: Diseño base del código y ealuación de resultados.
Firebase: Base de datos.
Streamlit: Despliegue.
Google AI Studio: Orquestrador motor del agente.
Qué hice yo directamente: Pruebas y adaptaciones del agente.
Qué verifiqué y cómo: Se verifica si la respuesta es correcta y sin alucinaciones, si el agente resolvió la solicitud y entendió la necesidad a fondo y si dió consejos o pidió datos personales al realizar pruebas automáticas sobre 25 preguntas basadas en el anexo y evaluar sus respuestas usando un modelo de IA diferente al usado para generar las respuestas. Estas pruebas están registradas dentro de la carpeta Resultados.
Latencia de respuesta, tokens usados, número de líneas en la respuesta, número de mensajes por conversación se obtienen usando analítica sobre los logs de las preguntas.
Qué no alcancé a hacer: Métrica de cuántas pregunntas toma resolver un problema. Frente de pareto con distintos modelos. Usar los datos de firebase para obtener tendencias en las preguntas. Mejorar accesibilidad del front en la versión admin.
Un fallo que encontré en mis pruebas y qué hice (puede decir que no tuvo): Al hacer las pruebas automáticas se superaba límite de peticiones por minutos disponibles en la versión gratuita de mi modelo en Google AI Studio y las respuestas fallaban. Implementé un limite de 14 preguntas por minuto para mantenerme en el rango. Además hice múltiples versiones del prompt del agente hasta obtener los resultados actuales, mejorando cada vez su resultado en los criterios propuestos.
