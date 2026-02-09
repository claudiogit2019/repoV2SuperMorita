import streamlit as st
import json
import os
import datetime
from dotenv import load_dotenv

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(layout="wide", page_title="MORITA V2", initial_sidebar_state="expanded")

# CARGAR API KEY DE GROQ (Nueva Key)
load_dotenv()
if "GROQ_API_KEY" not in st.session_state:
    st.session_state.GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# CSS PARA LETRA GRANDE Y DISEÑO PROFESIONAL
st.markdown("""
    <style>
        html, body, [class*="st-"] { font-size: 1.3rem !important; }
        .stButton > button { height: 3.5em !important; font-size: 1.5rem !important; width: 100%; }
        .stTextInput input, .stSelectbox div { height: 60px !important; font-size: 1.5rem !important; }
        .titulo-morita { color: #D32F2F; font-size: 4.5rem !important; font-weight: bold; text-align: center; margin-top: -20px; }
        .fecha-login { text-align: center; background-color: #F0F2F6; padding: 20px; border-radius: 15px; border: 2px solid #D32F2F; margin-bottom: 30px; }
        [data-testid="stSidebar"] { background-color: #1E1E1E; }
        [data-testid="stSidebar"] * { color: white !important; font-size: 1.2rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE APOYO ---
def cargar_usuarios():
    try:
        with open("data/usuarios.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return [{"usuario": "admin", "clave": "1234", "rol": "admin", "nombre": "Administrador"}]

# --- LÓGICA DE PERSISTENCIA INICIAL ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario_data = None

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    # --- ENCABEZADO DE FECHA Y HORA GRANDE ---
    ahora = datetime.datetime.now()
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    fecha_hoy = f"{dias_semana[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year}"
    hora_hoy = ahora.strftime("%H:%M")

    st.markdown(f"""
        <div class="fecha-login">
            <div style="font-size: 2rem; color: #555;">{fecha_hoy}</div>
            <div style="font-size: 4rem; font-weight: bold; color: #D32F2F;">{hora_hoy}</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="titulo-morita">🍎 MINIMERCADO MORITA </h1>', unsafe_allow_html=True)
    
    with st.columns([1, 1, 1])[1]:
        with st.form("login"):
            u_input = st.text_input("USUARIO")
            p_input = st.text_input("CONTRASEÑA", type="password")
            if st.form_submit_button("INGRESAR AL SISTEMA"):
                usuarios = cargar_usuarios()
                user_found = next((user for user in usuarios if user['usuario'] == u_input and user['clave'] == p_input), None)
                
                if user_found:
                    st.session_state.autenticado = True
                    st.session_state.rol = user_found['rol']
                    st.session_state.usuario_data = user_found
                    st.rerun()
                else:
                    st.error("❌ Usuario o Clave incorrectos")

# --- SISTEMA AUTENTICADO ---
else:
    # Sidebar con info del usuario logueado
    st.sidebar.markdown(f"### 👤 {st.session_state.usuario_data['nombre']}")
    st.sidebar.markdown(f"**Perfil:** {st.session_state.rol.upper()}")
    
    # Definir opciones del menú según ROL
    opciones = ["🛒 CAJA / VENTAS"]
    if st.session_state.rol == "admin":
        opciones += ["📦 GESTIÓN PRODUCTOS", "📊 CIERRE DE CAJA", "👤 GESTIÓN USUARIOS"]
    
    menu = st.sidebar.radio("MENÚ PRINCIPAL", opciones)

    st.sidebar.divider()
    if st.sidebar.button("🚪 CERRAR SESIÓN"):
        st.session_state.autenticado = False
        st.session_state.usuario_data = None
        st.rerun()

    # --- IMPORTACIÓN DE MÓDULOS ---
    from modulos import caja, inventario_abm, reporte, usuarios

    if menu == "🛒 CAJA / VENTAS":
        caja.mostrar_caja()
    elif menu == "📦 GESTIÓN PRODUCTOS":
        inventario_abm.mostrar_abm()
    elif menu == "📊 CIERRE DE CAJA":
        reporte.mostrar_reporte()
    elif menu == "👤 GESTIÓN USUARIOS":
        usuarios.mostrar_gestion_usuarios()
