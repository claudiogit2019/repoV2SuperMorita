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
        if not sheet:
            return None
        
        # CAMBIO CLAVE: Obtenemos todos los valores como matriz simple [filas][columnas]
        # Esto evita que gspread intente "adivinar" las columnas si hay huecos.
        lista_de_listas = sheet.get_all_values()
        
        if len(lista_de_listas) <= 1:
            return []

        inventario_limpio = []
        # Saltamos la primera fila (encabezados)
        for fila in lista_de_listas[1:]:
            # Aseguramos que la fila tenga al menos 3 columnas para evitar errores de índice
            while len(fila) < 3:
                fila.append("")
            
            # Mapeo manual estricto: A=0, B=1, C=2
            inventario_limpio.append({
                "Codigo": str(fila[0]).strip(),
                "Producto": str(fila[1]).strip(),
                "Precio": fila[2] if fila[2] else 0
            })
        
        return inventario_limpio
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return None

def agregar_producto_google(codigo, producto, precio):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            # Forzamos el orden: A: Código, B: Producto, C: Precio
            # Usamos value_input_option='USER_ENTERED' para que Google Sheets 
            # reconozca los números como números y no como texto.
            nueva_fila = [str(codigo), str(producto).upper(), precio]
            sheet.append_row(nueva_fila, value_input_option='USER_ENTERED')
            return True
    except:
        return False

def borrar_producto_google(nombre_producto):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            # Buscamos específicamente en la Columna B (Producto) para no borrar filas equivocadas
            # si el nombre coincide con un código de barras.
            celda = sheet.find(nombre_producto, in_column=2)
            if celda:
                sheet.delete_rows(celda.row)
                return True
    except:
        return False

def editar_producto_google(nombre_original, nuevo_codigo, nuevo_nombre, nuevo_precio):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            # Buscamos por el nombre original en la columna B
            celda = sheet.find(nombre_original, in_column=2)
            if celda:
                # Actualización por celdas individuales garantizando la columna
                sheet.update_cell(celda.row, 1, str(nuevo_codigo)) # Columna A
                sheet.update_cell(celda.row, 2, str(nuevo_nombre).upper()) # Columna B
                sheet.update_cell(celda.row, 3, nuevo_precio) # Columna C
                return True
    except:
        return False
