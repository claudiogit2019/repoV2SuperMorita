import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

def conectar_google_sheets():
    try:
        # Definimos los permisos necesarios
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Cargamos las credenciales desde los Secrets de Streamlit
        # Asegúrate de que en Secrets el nombre sea [gcp_service_account]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        client = gspread.authorize(creds)
        # IMPORTANTE: El nombre debe coincidir con tu archivo en Drive
        # Según tu imagen es "stock_morita_2026-02-14"
        sheet = client.open("Morita_DB").sheet1
        return sheet
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_inventario_google():
    sheet = conectar_google_sheets()
    if sheet:
        try:
            # Trae todos los registros de la planilla
            datos = sheet.get_all_records()
            return datos
        except Exception as e:
            # Aquí evitamos el error del <Response [200]>
            return None
    return None
