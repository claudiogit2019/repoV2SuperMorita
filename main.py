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
    # Streamlit Cloud suele usar UTC, restamos 3 horas
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)

# CSS PARA LETRA GRANDE Y DISEÑO PROFESIONAL
st.markdown("""
    <style>
        html, body, [class*="st-"] { font-size: 1.2rem !important; }
        .stButton > button { height: 3em !important; font-size: 1.3rem !important; width: 100%; }
        .stTextInput input, .stSelectbox div { height: 50px !important; font-size: 1.3rem !important; }
        .titulo-morita { color: #D32F2F; font-size: 4rem !important; font-weight: bold; text-align: center; margin-top: -20px; }
        .fecha-login { text-align: center; background-color: #F0F2F6; padding: 20px; border-radius: 15px; border: 2px solid #D32F2F; margin-bottom: 30px; }
        [data-testid="stSidebar"] { background-color: #1E1E1E; }
        [data-testid="stSidebar"] * { color: white !important; font-size: 1.1rem !important; }
        /* Ocultar instrucciones de "Press Enter to apply" */
        div[data-testid="InputInstructions"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE APOYO ---
def cargar_usuarios():
    ruta_usuarios = "data/usuarios.json"
    if os.path.exists(ruta_usuarios):
        try:
            with open(ruta_usuarios, "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return [{"usuario": "admin", "clave": "1234", "rol": "admin", "nombre": "Administrador"}]

# --- LÓGICA DE PERSISTENCIA INICIAL ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario_data = None

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    # --- ENCABEZADO DE FECHA Y HORA AJUSTADO A ARGENTINA ---
    ahora = obtener_ahora_argentina()
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    fecha_hoy = f"{dias_semana[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year}"
    hora_hoy = ahora.strftime("%H:%M")

    st.markdown(f"""
        <div class="fecha-login">
            <div style="font-size: 1.8rem; color: #555;">{fecha_hoy}</div>
            <div style="font-size: 5rem; font-weight: bold; color: #D32F2F; line-height: 1;">{hora_hoy}</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="titulo-morita">🍎 MINIMERCADO MORITA </h1>', unsafe_allow_html=True)
    
    # Contenedor de Login centrado
    _, col_centro, _ = st.columns([1, 1, 1])
    with col_centro:
        with st.form("login_form"):
            u_input = st.text_input("USUARIO").strip()
            p_input = st.text_input("CONTRASEÑA", type="password").strip()
            boton_login = st.form_submit_button("INGRESAR AL SISTEMA")
            
            if boton_login:
                lista_usuarios = cargar_usuarios()
                user_found = next((u for u in lista_usuarios if u['usuario'] == u_input and u['clave'] == p_input), None)
                
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
    st.sidebar.divider()
    
    # Definir opciones del menú según ROL
    opciones = ["🛒 CAJA / VENTAS"]
    if st.session_state.rol == "admin":
        opciones += ["📦 GESTIÓN PRODUCTOS", "📊 CIERRE DE CAJA", "👤 GESTIÓN USUARIOS"]
    
    menu = st.sidebar.radio("MENÚ PRINCIPAL", opciones)

    st.sidebar.divider()
    if st.sidebar.button("🚪 CERRAR SESIÓN"):
        st.session_state.autenticado = False
        st.session_state.usuario_data = None
        st.session_state.rol = None
        st.rerun()

    # --- NAVEGACIÓN DE MÓDULOS ---
    if menu == "🛒 CAJA / VENTAS":
        caja.mostrar_caja()
    elif menu == "📦 GESTIÓN PRODUCTOS":
        inventario_abm.mostrar_abm()
    elif menu == "📊 CIERRE DE CAJA":
        reporte.mostrar_reporte()
    elif menu == "👤 GESTIÓN USUARIOS":
        usuarios.mostrar_gestion_usuarios()
