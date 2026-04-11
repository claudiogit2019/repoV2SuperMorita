import streamlit as st
import pandas as pd
import json
import io
import datetime
import os
# Importamos las funciones de sincronización
from modulos.google_sheets import (
    obtener_inventario_google, 
    agregar_producto_google, 
    borrar_producto_google, 
    editar_producto_google
)

def cargar_json():
    ruta = "data/inventario.json"
    if not os.path.exists("data"):
        os.makedirs("data")
    try:
        datos_google = obtener_inventario_google()
        if datos_google:
            # Solo guardamos si hay datos válidos para evitar sobreescribir con basura
            with open(ruta, "w", encoding='utf-8') as f:
                json.dump(datos_google, f, indent=4, ensure_ascii=False)
            return datos_google
        if os.path.exists(ruta):
            with open(ruta, "r", encoding='utf-8') as f:
                return json.load(f)
        return []
    except: 
        return []

def guardar_json(datos):
    with open("data/inventario.json", "w", encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def mostrar_abm():
    st.title("📦 GESTIÓN DE PRODUCTOS") 
    inv_raw = cargar_json()
    
    # --- LIMPIEZA CRÍTICA PARA EVITAR EL TYPEERROR ---
    # Filtramos para que solo queden diccionarios que tengan la clave 'Producto' con contenido
    inv = [p for p in inv_raw if isinstance(p, dict) and p.get('Producto')]

    tab1, tab2, tab3, tab4 = st.tabs(["➕ ALTA", "✏️ MODIFICACIÓN", "🗑️ BAJA", "📈 STOCK"])

    # --- TAB 1: ALTA DE PRODUCTO ---
    with tab1:
        st.subheader("Cargar Nuevo Producto")
        with st.form("form_alta", clear_on_submit=True):
            # Usamos strip() para evitar espacios invisibles que desplacen columnas
            codigo = st.text_input("Código de Barras (Scanner)", key="input_alta_cod").strip()
            nombre = st.text_input("Nombre del Producto", key="input_alta_nom").upper().strip()
            precio = st.number_input("Precio", min_value=0.0, step=10.0, key="input_alta_pre")
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ CARGAR"):
                if nombre and codigo:
                    # Verificación de duplicados más robusta
                    existe_cod = any(str(p.get('Codigo', '')) == codigo for p in inv)
                    existe_nom = any(str(p.get('Producto', '')).upper() == nombre.upper() for p in inv)
                    
                    if existe_cod:
                        st.error(f"❌ El código {codigo} ya existe.")
                    elif existe_nom:
                        st.error(f"❌ El producto {nombre} ya existe.")
                    else:
                        # Forzamos el orden de envío para que Google Sheets reciba A, B, C correctamente
                        if agregar_producto_google(codigo, nombre, precio):
                            st.success(f"✅ PRODUCTO CARGADO: {nombre}")
                            # No hace falta append manual si st.rerun() vuelve a cargar de Google
                            st.rerun()
                        else:
                            st.error("❌ Error al sincronizar con Google.")
                else:
                    st.error("⚠️ Ingrese Código y Nombre.")
            
            if c2.form_submit_button("🧹 LIMPIAR"):
                st.rerun()

    # --- TAB 2: MODIFICACIÓN ---
    with tab2:
        st.subheader("Editar Producto Existente")
        # El sorted ahora es seguro gracias al filtro de arriba
        nombres_prod = sorted([str(p['Producto']) for p in inv])
        seleccion = st.selectbox("Seleccione para modificar:", ["---"] + nombres_prod)
        
        if seleccion != "---":
            prod_actual = next((p for p in inv if str(p['Producto']) == seleccion), None)
            
            if prod_actual:
                with st.form("form_modificar"):
                    nuevo_cod = st.text_input("Código", value=str(prod_actual.get('Codigo', ''))).strip()
                    nuevo_nom = st.text_input("Nombre", value=str(prod_actual.get('Producto', ''))).upper().strip()
                    
                    # Manejo seguro de precios con coma o punto
                    try:
                        precio_raw = str(prod_actual.get('Precio', 0)).replace(',', '.')
                        val_pre = float(precio_raw)
                    except:
                        val_pre = 0.0
                        
                    nuevo_pre = st.number_input("Precio", value=val_pre, min_value=0.0)
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 GUARDAR"):
                        if editar_producto_google(seleccion, nuevo_cod, nuevo_nom, nuevo_pre):
                            st.success("✅ Cambios guardados")
                            st.rerun()
                        else:
                            st.error("❌ Error en Google Sheets")
                    
                    if c2.form_submit_button("🧹 CANCELAR"):
                        st.rerun()

    # --- TAB 3: BAJA ---
    with tab3:
        st.subheader("Eliminar Producto")
        nombres_baja = sorted([str(p['Producto']) for p in inv])
        eliminar = st.selectbox("Seleccione producto:", ["---"] + nombres_baja)
        if eliminar != "---":
            st.warning(f"¿Eliminar '{eliminar}'?")
            if st.button("🗑️ SÍ, ELIMINAR"):
                if borrar_producto_google(eliminar):
                    st.success("✅ Eliminado")
                    st.rerun()
                else:
                    st.error("❌ Error en Google Sheets")

    # --- TAB 4: STOCK ---
    with tab4:
        st.subheader("Gestión de Stock")
        df_inv = pd.DataFrame(inv)
        
        if not df_inv.empty:
            # Aseguramos que las columnas existan antes de mostrar
            for col in ['Codigo', 'Producto', 'Precio']:
                if col not in df_inv.columns:
                    df_inv[col] = ""
            
            df_display = df_inv[['Codigo', 'Producto', 'Precio']].sort_values(by="Producto")
            st.dataframe(df_display, use_container_width=True)
            
            # Exportación
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_display.to_excel(writer, index=False)
            st.download_button(
                label="📥 DESCARGAR EXCEL",
                data=buffer.getvalue(),
                file_name=f"stock_{datetime.date.today()}.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.info("No hay datos para mostrar.")
