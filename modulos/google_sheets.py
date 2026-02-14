import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

def conectar_google_sheets():
    # Definimos los permisos necesarios
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Cargamos las credenciales desde los Secrets de Streamlit
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=scope
    )
    client = gspread.authorize(creds)
    return client

def obtener_inventario_google():
    try:
        client = conectar_google_sheets()
        # IMPORTANTE: Cambiá "Morita_DB" por el nombre exacto de tu planilla
        # Y "Inventario" por el nombre de la pestaña (hoja) de abajo
        sheet = client.open("Morita_DB").worksheet("Inventario")
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"Error en Google Sheets: {e}")
        return []
