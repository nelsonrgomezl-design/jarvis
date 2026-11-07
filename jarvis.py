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

# --- CONFIGURACIÓN DE LA API KEY ---
# PEGA TU CLAVE DE GOOGLE AI STUDIO AQUÍ ENTRE LAS COMILLAS:
API_KEY_FIJA = "PEGA_AQUI_TU_API_KEY"

# Lógica para detectar la clave automáticamente
api_key = API_KEY_FIJA

if not api_key or api_key == "PEGA_AQUI_TU_API_KEY":
  if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
  elif "GEMINI_API_KEY" in os.environ:
    api_key = os.environ["GEMINI_API_KEY"]

if api_key and api_key != "PEGA_AQUI_TU_API_KEY":
  genai.configure(api_key=api_key)

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

# --- PANEL LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
  st.title("⚡ Jarvis Control (Cloud)")
  st.caption("Asistente comercial potenciado con Google Gemini API.")
  st.divider()

  st.subheader("🤖 Modelo")
  st.info("Modelo activo: gemini-1.5-flash")

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

system_instruction = (
    "Eres Jarvis, un asistente de IA experto en gestión de negocios,"
    " optimización operativa, logística y estrategia comercial. Ayudas a"
    " estructurar procesos, analizar métricas, realizar cálculos matemáticos"
    " complejos de costos y tomar decisiones con un tono profesional, directo"
    " y orientado a resultados."
)

# Mostrar historial visual en pantalla
filas_bd_visual = cargar_historial_bd()
for rol, contenido in filas_bd_visual:
  st.chat_message(rol, avatar="⚡" if rol == "assistant" else "👤").markdown(
      contenido
  )

# Entrada de texto del usuario
pregunta_usuario = st.chat_input(
    "Escribe tu consulta de negocio, cálculo o pide un reporte en PDF..."
)

if pregunta_usuario:
  if not api_key or api_key == "PEGA_AQUI_TU_API_KEY":
    st.error(
        "❌ Pega tu Gemini API Key en la línea 30 del archivo jarvis.py en"
        " GitHub."
    )
  else:
    contenido_final = pregunta_usuario
    if texto_archivo and len(filas_bd_visual) == 0:
      contenido_final = (
          f"Información del documento del negocio cargado:\n\n{texto_archivo}\n\nCon"
          f" base en esto responde: {pregunta_usuario}"
      )
