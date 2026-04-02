import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

def conectar_google_sheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        # Nombre del archivo convertido en Google Sheets
        sheet = client.open("Morita_DB").sheet1
        return sheet
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_inventario_google():
    try:
        sheet = conectar_google_sheets()
        # Retorna una lista de diccionarios: [{'Codigo': ..., 'Producto': ..., 'Precio': ...}]
        return sheet.get_all_records() if sheet else None
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return None

def agregar_producto_google(codigo, producto, precio):
    """Ahora recibe tres parámetros para coincidir con la nueva tabla"""
    try:
        sheet = conectar_google_sheets()
        if sheet:
            # Inserta en A, B y C
            sheet.append_row([str(codigo), producto, precio])
            return True
    except:
        return False

def borrar_producto_google(nombre_producto):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            # Buscamos por nombre (Columna B)
            celda = sheet.find(nombre_producto)
            if celda:
                sheet.delete_rows(celda.row)
                return True
    except:
        return False

def editar_producto_google(nombre_original, nuevo_codigo, nuevo_nombre, nuevo_precio):
    """Actualiza las tres columnas basadas en el nombre original"""
    try:
        sheet = conectar_google_sheets()
        if sheet:
            celda = sheet.find(nombre_original)
            if celda:
                sheet.update_cell(celda.row, 1, str(nuevo_codigo)) # Columna A: Código
                sheet.update_cell(celda.row, 2, nuevo_nombre)      # Columna B: Producto
                sheet.update_cell(celda.row, 3, nuevo_precio)      # Columna C: Precio
                return True
    except:
        return False
