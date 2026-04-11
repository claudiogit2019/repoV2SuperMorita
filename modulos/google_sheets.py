import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

def conectar_google_sheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Morita_DB").sheet1
        return sheet
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_inventario_google():
    try:
        sheet = conectar_google_sheets()
        if not sheet: return None
        
        # Rango A:C para evitar columnas basura
        lista_de_listas = sheet.get("A2:C5000")
        if not lista_de_listas: return []

        inventario_limpio = []
        for fila in lista_de_listas:
            while len(fila) < 3:
                fila.append("")
            
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
            # Buscamos proxima fila basada en columna B (Producto)
            col_producto = sheet.col_values(2)
            proxima_fila = len(col_producto) + 1
            rango = f"A{proxima_fila}:C{proxima_fila}"
            valores = [[str(codigo), str(producto).upper(), precio]]
            sheet.update(range_name=rango, values=valores, value_input_option='USER_ENTERED')
            return True
    except Exception as e:
        st.error(f"Error al agregar producto: {e}")
        return False

def borrar_producto_google(nombre_producto):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            # Búsqueda robusta para borrar
            nombres = sheet.col_values(2)
            for i, nombre in enumerate(nombres):
                if nombre.strip().upper() == nombre_producto.strip().upper():
                    sheet.delete_rows(i + 1)
                    return True
            return False
    except:
        return False

def editar_producto_google(nombre_original, nuevo_codigo, nuevo_nombre, nuevo_precio):
    """
    Versión blindada para registros antiguos: 
    Busca ignorando espacios extra que puedan tener los datos viejos.
    """
    try:
        sheet = conectar_google_sheets()
        if sheet:
            # 1. Traemos toda la columna de productos para comparar manualmente
            # Esto soluciona el fallo de .find() con registros mal formateados
            nombres_col_b = sheet.col_values(2)
            
            fila_encontrada = None
            busqueda = nombre_original.strip().upper()
            
            for i, nombre_celda in enumerate(nombres_col_b):
                if nombre_celda.strip().upper() == busqueda:
                    fila_encontrada = i + 1
                    break
            
            if fila_encontrada:
                # 2. Actualizamos con update_cells o por rango para mayor velocidad
                # Usamos update_cell para asegurar precisión en las columnas A, B y C
                sheet.update_cell(fila_encontrada, 1, str(nuevo_codigo))
                sheet.update_cell(fila_encontrada, 2, str(nuevo_nombre).upper())
                sheet.update_cell(fila_encontrada, 3, nuevo_precio)
                return True
            else:
                st.warning(f"No se encontró el producto '{nombre_original}' para editar.")
                return False
    except Exception as e:
        st.error(f"Error técnico al editar registro: {e}")
        return False
