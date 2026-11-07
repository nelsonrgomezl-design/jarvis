import os
import sqlite3
from google import genai
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- CONFIGURACIÓN DE LA PÁGINA Y ESTILO VISUAL ---
st.set_page_config(
    page_title="Jarvis Business AI - Gemini Cloud",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stChatBox { border-radius: 10px; }
    .sidebar .stButton button { width: 100%; border-radius: 8px; background-color: #ff4b4b; color: white; font-weight: bold; }
    .sidebar .stButton button:hover { background-color: #ff2b2b; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- PANEL LATERAL PARA GESTIÓN DE CREDENCIALES ---
with st.sidebar:
  st.title("⚡ Jarvis Control (Cloud)")
  st.caption("Asistente comercial potenciado con Google Gemini API.")
  st.divider()

  # Intentar obtener clave de secretos o entorno
  api_key = None
  if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
  elif "GEMINI_API_KEY" in os.environ:
    api_key = os.environ["GEMINI_API_KEY"]

  # Si no está configurada globalmente, pedirla de manera segura en la interfaz
  if not api_key:
    st.subheader("🔑 Credenciales")
    api_key_input = st.text_input(
        "Gemini API Key", type="password", placeholder="Pega tu clave aquí..."
    )
    if api_key_input:
      api_key = api_key_input

  st.subheader("🤖 Modelo")
  st.info("Modelo activo: gemini-flash-latest")

  st.divider()
  st.subheader("📂 Documentos de Negocio")
  archivo_subido = st.file_uploader(
      "Sube un archivo de texto (.txt)", type=["txt"]
  )
  texto_archivo = ""
  if archivo_subido is not None:
    texto_archivo = archivo_subido.read().decode("utf-8")
    st.success(f"¡Archivo '{archivo_subido.name}' activo!")

  st.divider()
  if st.button("🧹 Borrar Memoria Completa"):
    conexion = sqlite3.connect("historial_jarvis.db")
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM mensajes")
    conexion.commit()
    conexion.close()
    if "chat_session" in st.session_state:
      del st.session_state.chat_session
    st.rerun()

# --- INICIALIZAR CLIENTE DE GEMINI DE FORMA SEGURA ---
client = None
if api_key:
  try:
    client = genai.Client(api_key=api_key)
  except Exception as e:
    st.sidebar.error(f"Error al configurar cliente: {e}")

# --- BASE DE DATOS SQLITE ---
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


inicializar_db()

# --- INTERFAZ PRINCIPAL DE CHAT ---
st.title("💼 Jarvis - Asistente Comercial Gemini Pro")
st.markdown(
    "Operando con la potencia en la nube de Google Gemini. Memoria"
    " persistente, análisis de archivos y reportes PDF."
)
st.divider()

# Mostrar historial visual en pantalla
filas_bd_visual = cargar_historial_bd()
for rol, contenido in filas_bd_visual:
  st.chat_message(rol, avatar="⚡" if rol == "assistant" else "👤").markdown(
      contenido
  )

pregunta_usuario = st.chat_input(
    "Escribe tu consulta de negocio, cálculo o pide un reporte en PDF..."
)

if pregunta_usuario:
  if not client:
    st.error(
        "❌ Por favor ingresa tu Gemini API Key en el panel lateral o en los"
        " Secretos de Streamlit."
    )
  else:
    contenido_final = pregunta_usuario
    if texto_archivo and len(filas_bd_visual) == 0:
      contenido_final = (
          f"Información del documento del negocio cargado:\n\n{texto_archivo}\n\nCon"
          f" base en esto responde: {pregunta_usuario}"
      )

    guardar_mensaje("user", pregunta_usuario)
    st.chat_message("user", avatar="👤").markdown(pregunta_usuario)

    with st.chat_message("assistant", avatar="⚡"):
      with st.spinner("Jarvis procesando en la nube..."):
        try:
          # Reconstruir el historial acumulado de la base de datos para la API moderna
          historial_mensajes = []
          for r, c in cargar_historial_bd():
            historial_mensajes.append(c)

          # Llamada moderna optimizada con el cliente oficial
          response = client.models.generate_content(
              model="gemini-flash-latest",
              contents=historial_mensajes,
          )
          respuesta_texto = response.text
          st.markdown(respuesta_texto)
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
          st.error(f"❌ Error al comunicarse con la API de Gemini: {e}")
