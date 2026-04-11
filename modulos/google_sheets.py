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
        
        # Leemos el rango exacto A:C para ignorar cualquier columna "basura" a la derecha
        # Esto soluciona que el sistema lea celdas vacías como códigos
        lista_de_listas = sheet.get("A2:C5000")
        
        if not lista_de_listas:
            return []

        inventario_limpio = []
        for fila in lista_de_listas:
            # Rellenamos con vacíos si la fila está incompleta en Sheets
            while len(fila) < 3:
                fila.append("")
            
            # Mapeo manual estricto: A=0 (Codigo), B=1 (Producto), C=2 (Precio)
            inventario_limpio.append({
                "Codigo": str(fila[0]).strip(),
                "Producto": str(fila[1]).strip().upper(),
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
            # 1. Buscamos la primera fila realmente vacía basándonos en la columna B (Producto)
            # Esto evita que se salte filas o se corra si hay basura en la columna A
            col_producto = sheet.col_values(2)
            proxima_fila = len(col_producto) + 1
            
            # 2. Definimos el rango exacto para asegurar A, B y C
            rango = f"A{proxima_fila}:C{proxima_fila}"
            
            # 3. Preparamos los datos
            valores = [[str(codigo), str(producto).upper(), precio]]
            
            # 4. Usamos update con el rango explícito
            sheet.update(range_name=rango, values=valores, value_input_option='USER_ENTERED')
            return True
    except Exception as e:
        st.error(f"Error al agregar producto: {e}")
        return False

def borrar_producto_google(nombre_producto):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            # Buscamos específicamente en la Columna B (Producto)
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
                # Actualización garantizando la columna física
                # A=1, B=2, C=3
                sheet.update_cell(celda.row, 1, str(nuevo_codigo))
                sheet.update_cell(celda.row, 2, str(nuevo_nombre).upper())
                sheet.update_cell(celda.row, 3, nuevo_precio)
                return True
    except:
        return False
