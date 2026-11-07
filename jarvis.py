import os
import sqlite3
import streamlit as st
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Jarvis Business AI - Gemini Cloud",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS
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

# --- INICIALIZACIÓN DE API KEY Y CLIENTE ---
API_KEY_FIJA = "AQ.Ab8RN6K6jGgFiPwQySgVLk37wvKQDEe_qH2c223euWTewfizsQ"
api_key = (
    API_KEY_FIJA
    if "AQ.Ab8RN" in API_KEY_FIJA
    else (os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY"))
)

# Inicialización explícita del cliente moderno con la clave
client = genai.Client(api_key=api_key) if api_key else None

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


def cargar_historial_bd(limite=6):
  """Carga solo los últimos mensajes para velocidad máxima."""
  conexion = sqlite3.connect(DB_NAME)
  cursor = conexion.cursor()
  cursor.execute(
      "SELECT rol, contenido FROM mensajes ORDER BY id DESC LIMIT ?", (limite,)
  )
  filas = cursor.fetchall()
  conexion.close()
  return filas[::-1]


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


inicializar_db()

# --- PANEL LATERAL ---
with st.sidebar:
  st.title("⚡ Jarvis Control (Cloud)")
  st.caption("Asistente comercial de alta velocidad.")
  st.divider()

  st.subheader("🤖 Modelo Activo")
  st.info("Modelo: gemini-3.8-flash")

  st.divider()
  st.subheader("📂 Documentos de Negocio")
  archivo_subido = st.file_uploader("Sube un archivo (.txt)", type=["txt"])
  texto_archivo = ""
  if archivo_subido is not None:
    texto_archivo = archivo_subido.read().decode("utf-8")
    st.success("¡Archivo activo!")

  st.divider()
  if st.button("🧹 Borrar Memoria Completa"):
    limpiar_base_datos()
    st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.title("💼 Jarvis - Asistente Comercial Gemini Pro")
st.markdown("Optimizado para máxima velocidad de respuesta en la nube.")
st.divider()

SYSTEM_PROMPT = (
    "Eres Jarvis, un asistente experto en gestión de negocios, logística,"
    " costos y estrategia comercial. Responde de forma directa, concisa y"
    " profesional."
)

# Mostrar todo el historial
conexion = sqlite3.connect(DB_NAME)
cursor = conexion.cursor()
cursor.execute("SELECT rol, contenido FROM mensajes")
todas_las_filas = cursor.fetchall()
conexion.close()

for rol, contenido in todas_las_filas:
  with st.chat_message(rol, avatar="⚡" if rol == "assistant" else "👤"):
    st.markdown(contenido)

# ENTRADA DEL USUARIO
pregunta_usuario = st.chat_input(
    "Escribe tu consulta de negocio o pide un reporte en PDF..."
)

if pregunta_usuario:
  if not client:
    st.error("❌ No se encontró la API Key de Gemini.")
  else:
    contenido_final = pregunta_usuario
    if texto_archivo and len(todas_las_filas) == 0:
      contenido_final = (
          f"Documento cargado:\n{texto_archivo}\n\nPregunta: {pregunta_usuario}"
      )

    guardar_mensaje("user", pregunta_usuario)
    with st.chat_message("user", avatar="👤"):
      st.markdown(pregunta_usuario)

    with st.chat_message("assistant", avatar="⚡"):
      with st.spinner("⚡ Jarvis respondiendo..."):
        try:
          mensajes_recientes = cargar_historial_bd(limite=6)
          prompt_optimizado = ""
          for r, c in mensajes_recientes:
            rol_str = "Usuario" if r == "user" else "Jarvis"
            prompt_optimizado += f"{rol_str}: {c}\n"

          # Usamos explícitamente gemini-3.8-flash que es el modelo actual requerido
          response = client.models.generate_content(
              model="gemini-3.8-flash",
              contents=prompt_optimizado,
              config=types.GenerateContentConfig(
                  system_instruction=SYSTEM_PROMPT,
                  temperature=0.7,
              ),
          )

          respuesta_texto = response.text
          st.markdown(respuesta_texto)
          guardar_mensaje("assistant", respuesta_texto)

          if (
              "pdf" in pregunta_usuario.lower()
              or "reporte" in pregunta_usuario.lower()
          ):
            nombre_pdf = "reporte_jarvis.pdf"
            c = canvas.Canvas(nombre_pdf, pagesize=letter)
            c.drawString(
                100, 750, "Reporte Oficial - Jarvis Business Management"
            )
            y = 700
            for linea in respuesta_texto.split("\n"):
              if y > 50:
                c.drawString(100, y, linea[:90])
                y -= 20
            c.save()
            st.success(f"📄 ¡PDF generado: '{nombre_pdf}'!")

        except Exception as e:
          st.error(f"❌ Error al comunicarse con Gemini: {e}")
