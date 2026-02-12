import streamlit as st
import json
import os
import datetime
from dotenv import load_dotenv
from modulos import caja, inventario_abm, reporte, usuarios

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(layout="wide", page_title="MORITA V2", initial_sidebar_state="expanded")

# CARGAR API KEY DE GROQ
load_dotenv()
if "GROQ_API_KEY" not in st.session_state:
    st.session_state.GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- AJUSTE DE HORA ARGENTINA (UTC-3) ---
def obtener_ahora_argentina():
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)

# CSS ACTUALIZADO: Mobile-Friendly y Limpieza de Login
st.markdown("""
    <style>
        html, body, [class*="st-"] { font-size: 1.1rem !important; }
        /* Botones grandes para uso táctil en celular */
        .stButton > button { height: 3.5em !important; font-size: 1.2rem !important; width: 100%; border-radius: 10px; }
        .stTextInput input, .stSelectbox div { height: 55px !important; font-size: 1.2rem !important; }
        
        .titulo-morita { color: #D32F2F; font-size: 3.5rem !important; font-weight: bold; text-align: center; margin-bottom: 20px; }
        .fecha-interior { text-align: right; color: #555; font-size: 1rem; font-weight: bold; margin-bottom: 10px; margin-top: -30px; }
        
        [data-testid="stSidebar"] { background-color: #1E1E1E; }
        [data-testid="stSidebar"] * { color: white !important; font-size: 1.1rem !important; }
        
        /* Ocultar instrucciones de Streamlit para ganar espacio en celular */
        div[data-testid="InputInstructions"] { display: none; }
        
        /* Ajustes específicos para móviles */
        @media (max-width: 640px) {
            .titulo-morita { font-size: 2.2rem !important; }
            .stButton > button { height: 3em !important; font-size: 1.1rem !important; }
        }
    </style>
""", unsafe_allow_html=True)

def cargar_usuarios():
    ruta_usuarios = "data/usuarios.json"
    if os.path.exists(ruta_usuarios):
        try:
            with open(ruta_usuarios, "r", encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return [{"usuario": "admin", "clave": "1234", "rol": "admin", "nombre": "Administrador"}]

# --- LÓGICA DE PERSISTENCIA ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario_data = None

# --- PANTALLA DE LOGIN (Sin Fecha/Hora según pedido) ---
if not st.session_state.autenticado:
    st.markdown('<div style="margin-top: 50px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 class="titulo-morita">🍎 MINIMERCADO<br>MORITA</h1>', unsafe_allow_html=True)
    
    _, col_centro, _ = st.columns([0.5, 2, 0.5]) # Ajuste para que en celular el form sea ancho
    with col_centro:
        with st.form("login_form"):
            u_input = st.text_input("USUARIO").strip()
            p_input = st.text_input("CONTRASEÑA", type="password").strip()
            if st.form_submit_button("INGRESAR"):
                lista_usuarios = cargar_usuarios()
                user_found = next((u for u in lista_usuarios if u['usuario'] == u_input and u['clave'] == p_input), None)
                if user_found:
                    st.session_state.autenticado = True
                    st.session_state.rol = user_found['rol']
                    st.session_state.usuario_data = user_found
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")

# --- SISTEMA AUTENTICADO ---
else:
    # Fecha/Hora solo en el interior
    ahora = obtener_ahora_argentina()
    st.markdown(f'<div class="fecha-interior">📅 {ahora.strftime("%d/%m/%Y")} | ⏰ {ahora.strftime("%H:%M")}</div>', unsafe_allow_html=True)

    # Sidebar: Info Usuario
    st.sidebar.markdown(f"### 👤 {st.session_state.usuario_data['nombre']}")
    st.sidebar.markdown(f"**Rol:** {st.session_state.rol.upper()}")
    st.sidebar.divider()
    
    # MENÚ REORGANIZADO SEGÚN REQUERIMIENTOS ACTUALES
    opciones = ["🛒 CAJA"]
    if st.session_state.rol == "admin":
        opciones += ["📦 PRODUCTOS", "👤 GESTIÓN USUARIOS", "💰 APERTURA / CIERRE", "📅 HISTORIAL GENERAL"]
    else:
        # Los vendedores quizás necesitan ver Productos para consultar precios solamente
        opciones += ["📦 PRODUCTOS"]
    
    menu = st.sidebar.radio("MENÚ", opciones)

    st.sidebar.divider()
    if st.sidebar.button("🚪 SALIR"):
        st.session_state.autenticado = False
        st.session_state.usuario_data = None
        st.session_state.rol = None
        if 'carrito' in st.session_state: st.session_state.carrito = []
        st.rerun()

    # --- NAVEGACIÓN DE MÓDULOS ---
    if menu == "🛒 CAJA":
        caja.mostrar_caja()
    elif menu == "📦 PRODUCTOS":
        inventario_abm.mostrar_abm()
    elif menu == "💰 APERTURA / CIERRE":
        reporte.mostrar_reporte() # Maneja la lógica de limpiar turno y arqueo
    elif menu == "📅 HISTORIAL GENERAL":
        reporte.mostrar_historial_permanente() # La nueva función con el botón de limpiar
    elif menu == "👤 GESTIÓN USUARIOS":
        usuarios.mostrar_gestion_usuarios()
