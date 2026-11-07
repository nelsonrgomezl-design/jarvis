import os
import sqlite3
import google.generativeai as genai
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- CONFIGURACIÓN DE LA PÁGINA Y ESTILO VISUAL AVANZADO ---
st.set_page_config(
    page_title="Jarvis Business AI - Gemini Cloud",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stChatBox {
        border-radius: 10px;
    }
    .sidebar .stButton button {
        width: 100%;
        border-radius: 8px;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
    }
    .sidebar .stButton button:hover {
        background-color: #ff2b2b;
    }
    </style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS SQLITE (Memoria Persistente) ---
DB_NAME = "historial_jarvis.db"


def inicializar_db():
  conexion = sqlite3.connect(DB_NAME)
  cursor = conexion.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rol TEXT,
            contenido TEXT
        )
    """)
  conexion.commit()
  conexion.close()


def cargar_historial_bd():
  conexion = sqlite3.connect(DB_NAME)
  cursor = conexion.cursor()
  cursor.execute("SELECT rol, contenido FROM mensajes")
  filas = cursor.fetchall()
  conexion.close()
  return filas


def guardar_mensaje(rol, contenido):
  conexion = sqlite3.connect(DB_NAME)
  cursor = conexion.cursor()
  cursor.execute(
      "INSERT INTO mensajes (rol, contenido) VALUES (?, ?)", (rol, contenido)
  )
  conexion.commit()
  conexion.close()


def limpiar_base_datos():
  conexion = sqlite3.connect(DB_NAME)
  cursor = conexion.cursor()
  cursor.execute("DELETE FROM mensajes")
  conexion.commit()
  conexion.close()


# Inicializar base de datos
inicializar_db()

# --- PANEL LATERAL (CONFIGURACIÓN Y CREDENCIALES) ---
with st.sidebar:
  st.title("⚡ Jarvis Control (Cloud)")
  st.caption("Asistente comercial potenciado con Google Gemini API.")

  st.divider()

  # Configuración de la API Key de Gemini
  st.subheader("🔑 Credenciales")
  api_key_input = st.text_input(
      "Gemini API Key", type="password", placeholder="Pega tu clave aquí..."
  )

  if api_key_input:
    genai.configure(api_key=api_key_input)
  elif "GEMINI_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

  st.divider()

  # Selector de modelo de Gemini
  st.subheader("🤖 Modelo")
  modelo_seleccionado = st.selectbox(
      "Selecciona el Modelo",
      ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
      index=0,
  )

  st.divider()

  # Carga de archivos de texto
  st.subheader("📂 Documentos de Negocio")
  archivo_subido = st.file_uploader(
      "Sube un archivo de texto (.txt)", type=["txt"]
  )

  texto_archivo = ""
  if archivo_subido is not None:
    texto_archivo = archivo_subido.read().decode("utf-8")
    st.success(f"¡Archivo '{archivo_subido.name}' activo!")
    with st.expander("Ver contenido"):
      st.text(texto_archivo)

  st.divider()

  # Utilidades y limpieza
  if st.button("🧹 Borrar Memoria Completa"):
    limpiar_base_datos()
    if "chat_session" in st.session_state:
      del st.session_state.chat_session
    st.rerun()

# --- INTERFAZ PRINCIPAL DE CHAT ---
st.title("💼 Jarvis - Asistente Comercial Gemini Pro")
st.markdown(
    "Operando con la potencia en la nube de Google Gemini. Memoria"
    " persistente, análisis de archivos y reportes PDF."
)
st.divider()

# Configurar el modelo y la sesión de chat con el System Prompt inicial
system_instruction = (
    "Eres Jarvis, un asistente de IA experto en gestión de negocios,"
    " optimización operativa, logística y estrategia comercial. Ayudas a"
    " estructurar procesos, analizar métricas, realizar cálculos matemáticos"
    " complejos de costos y tomar decisiones con un tono profesional, directo"
    " y orientado a resultados."
)

if "chat_session" not in st.session_state:
  try:
    generation_config = {"temperature": 0.7}
    gemini_model = genai.GenerativeModel(
        model_name=modelo_seleccionado,
        system_instruction=system_instruction,
        generation_config=generation_config,
    )

    # Reconstruir el historial de la sesión de chat usando SQLite
    historial_previo = []
    filas_bd = cargar_historial_bd()

    for rol, contenido in filas_bd:
      # Mapear roles de SQLite al formato que espera la API de Gemini ('user' / 'model')
      rol_gemini = "user" if rol == "user" else "model"
      historial_previo.append({"role": rol_gemini, "parts": [contenido]})

    st.session_state.chat_session = gemini_model.start_chat(
        history=historial_previo
    )
  except Exception as e:
    st.warning(
        "⚠️ Por favor, ingresa tu API Key de Gemini en la barra lateral para"
        " iniciar."
    )

# Mostrar el historial visual en pantalla cargado desde la BD
filas_bd_visual = cargar_historial_bd()
for rol, contenido in filas_bd_visual:
  with st.chat_message(
      rol, avatar="⚡" if rol == "assistant" else "👤"
  ):  # Mantenemos visualmente el rol del asistente
    st.markdown(contenido)

# Entrada de texto del usuario
pregunta_usuario = st.chat_input(
    "Escribe tu consulta de negocio, cálculo o pide un reporte en PDF..."
)

if pregunta_usuario:
  if not api_key_input and "GEMINI_API_KEY" not in os.environ:
    st.error("❌ Debes ingresar tu Gemini API Key en la barra lateral primero.")
  else:
    # Inyectar contenido del archivo si es la primera interacción y se adjuntó un txt
    contenido_final = pregunta_usuario
    if texto_archivo and len(filas_bd_visual) == 0:
      contenido_final = (
          f"Información del documento del negocio cargado:\n\n{texto_archivo}\n\nCon"
          f" base en esto responde: {pregunta_usuario}"
      )

    # Guardar y mostrar mensaje del usuario
    guardar_mensaje("user", pregunta_usuario)
    with st.chat_message("user", avatar="👤"):
      st.markdown(pregunta_usuario)

    # Generar respuesta con la API de Gemini
    with st.chat_message("assistant", avatar="⚡"):
      with st.spinner(f"Jarvis ({modelo_seleccionado}) procesando en la nube..."):
        try:
          # Enviar mensaje a la sesión activa de Gemini
          respuesta_gemini = st.session_state.chat_session.send_message(
              contenido_final
          )
          respuesta_texto = respuesta_gemini.text
          st.markdown(respuesta_texto)

          # Guardar respuesta del asistente en la base de datos SQLite
          guardar_mensaje("assistant", respuesta_texto)

          # Generación automática de PDF si se solicita
          if (
              "pdf" in pregunta_usuario.lower()
              or "reporte" in pregunta_usuario.lower()
          ):
            nombre_pdf = "reporte_jarvis.pdf"
            c = canvas.Canvas(nombre_pdf, pagesize=letter)
            c.drawString(
                100, 750, "Reporte Oficial - Jarvis Business Management"
            )
            c.drawString(100, 730, "Resumen de operaciones y cálculos:")

            y = 700
            for linea in respuesta_texto.split("\n"):
              if y > 50:
                c.drawString(100, y, linea[:90])
                y -= 20

            c.save()
            st.success(f"📄 ¡PDF generado con éxito: '{nombre_pdf}'!")

        except Exception as e:
          st.error(
              f"❌ Error al comunicarse con la API de Gemini. Detalle: {e}"
          )