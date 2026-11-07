import os
import sqlite3
from google import genai
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- CONFIGURACIÓN DE PÁGINA ---
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

# --- CONFIGURACIÓN DE API KEY Y CLIENTE MODERNO ---
API_KEY_FIJA = "AQ.Ab8RN6K6jGgFiPwQySgVLk37wvKQDEe_qH2c223euWTewfizsQ"

api_key = API_KEY_FIJA
if not api_key or "AQ.Ab8RN" not in api_key:
  api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

# Inicializar cliente de Google GenAI
client = genai.Client(api_key=api_key)

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

# --- PANEL LATERAL ---
with st.sidebar:
  st.title("⚡ Jarvis Control (Cloud)")
  st.caption("Asistente comercial potenciado con Google Gemini API.")
  st.divider()

  st.subheader("🤖 Modelo")
  st.info("Modelo activo: gemini-2.0-flash")

  st.divider()

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

  if st.button("🧹 Borrar Memoria Completa"):
    limpiar_base_datos()
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

# MOSTRAR MENSAJES PREVIOS EN PANTALLA
filas_bd_visual = cargar_historial_bd()
for rol, contenido in filas_bd_visual:
  with st.chat_message(rol, avatar="⚡" if rol == "assistant" else "👤"):
    st.markdown(contenido)

# ENTRADA DEL USUARIO
pregunta_usuario = st.chat_input(
    "Escribe tu consulta de negocio, cálculo o pide un reporte en PDF..."
)

if pregunta_usuario:
  contenido_final = pregunta_usuario
  if texto_archivo and len(filas_bd_visual) == 0:
    contenido_final = (
        f"Información del documento del negocio cargado:\n\n{texto_archivo}\n\nCon"
        f" base en esto responde: {pregunta_usuario}"
    )

  # 1. Guardar y renderizar mensaje del usuario inmediatamente
  guardar_mensaje("user", pregunta_usuario)
  with st.chat_message("user", avatar="👤"):
    st.markdown(pregunta_usuario)

  # 2. Generar respuesta de Jarvis con el cliente moderno
  with st.chat_message("assistant", avatar="⚡"):
    with st.spinner("Jarvis procesando..."):
      try:
        # Construir el historial acumulado para pasarlo al modelo moderno de la librería `google-genai`
        historial_textos = []
        for r, c in cargar_historial_bd():
          historial_textos.append(c)

        # Usamos 'gemini-2.0-flash' que es totalmente compatible con la nueva librería oficial de API
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=historial_textos,
        )

        respuesta_texto = response.text
        st.markdown(respuesta_texto)

        # Guardar respuesta del asistente en SQLite
        guardar_mensaje("assistant", respuesta_texto)

        # Generación de PDF si se solicita
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
        st.error(f"❌ Error al comunicarse con Gemini: {e}")
