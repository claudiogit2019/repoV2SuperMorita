import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

def conectar_google_sheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        # Asegúrate que el nombre sea el del archivo CONVERTIDO (sin .xlsx)
        sheet = client.open("stock_morita_2026-02-14").sheet1
        return sheet
    except:
        return None

def obtener_inventario_google():
    try:
        sheet = conectar_google_sheets()
        return sheet.get_all_records() if sheet else None
    except:
        return None

def agregar_producto_google(producto, precio):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            sheet.append_row([producto, precio])
            return True
    except:
        return False

def borrar_producto_google(nombre_producto):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            celda = sheet.find(nombre_producto)
            if celda:
                sheet.delete_rows(celda.row)
                return True
    except:
        return False

def editar_producto_google(nombre_original, nuevo_nombre, nuevo_precio):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            celda = sheet.find(nombre_original)
            if celda:
                sheet.update_cell(celda.row, 1, nuevo_nombre) # Columna A
                sheet.update_cell(celda.row, 2, nuevo_precio) # Columna B
                return True
    except:
        return False
