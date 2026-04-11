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
        # Si obtenemos datos de Google (aunque sea una lista vacía [], pero no None)
        if datos_google is not None:
            with open(ruta, "w", encoding='utf-8') as f:
                json.dump(datos_google, f, indent=4, ensure_ascii=False)
            return datos_google
        
        # Si Google falla, vamos al local
        if os.path.exists(ruta):
            with open(ruta, "r", encoding='utf-8') as f:
                return json.load(f)
        return []
    except: 
        return []

def mostrar_abm():
    st.title("📦 GESTIÓN DE PRODUCTOS") 
    
    # Cargamos el inventario ya normalizado por google_sheets.py
    inv = cargar_json()
    
    # Aseguramos que sea una lista para evitar errores de iteración
    if inv is None:
        inv = []

    tab1, tab2, tab3, tab4 = st.tabs(["➕ ALTA", "✏️ MODIFICACIÓN", "🗑️ BAJA", "📈 STOCK"])

    # --- TAB 1: ALTA DE PRODUCTO ---
    with tab1:
        st.subheader("Cargar Nuevo Producto")
        with st.form("form_alta", clear_on_submit=True):
            codigo = st.text_input("Código de Barras", key="input_alta_cod").strip()
            nombre = st.text_input("Nombre del Producto", key="input_alta_nom").upper().strip()
            precio = st.number_input("Precio", min_value=0.0, step=10.0, key="input_alta_pre")
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ CARGAR"):
                if nombre and codigo:
                    # Buscamos duplicados en el inventario actual
                    if any(str(p.get('Codigo')) == codigo for p in inv):
                        st.error(f"❌ El código {codigo} ya existe.")
                    elif any(str(p.get('Producto')).upper() == nombre for p in inv):
                        st.error(f"❌ El producto {nombre} ya existe.")
                    else:
                        if agregar_producto_google(codigo, nombre, precio):
                            st.success(f"✅ PRODUCTO CARGADO: {nombre}")
                            st.rerun()
                        else:
                            st.error("❌ Error al sincronizar con Google Sheets.")
                else:
                    st.error("⚠️ Ingrese Código y Nombre.")
            
            if c2.form_submit_button("🧹 LIMPIAR"):
                st.rerun()

    # --- TAB 2: MODIFICACIÓN ---
    with tab2:
        st.subheader("Editar Producto Existente")
        # Filtramos solo los que tengan nombre válido para el selectbox
        nombres_prod = sorted([str(p['Producto']) for p in inv if p.get('Producto')])
        seleccion = st.selectbox("Seleccione para modificar:", ["---"] + nombres_prod)
        
        if seleccion != "---":
            prod_actual = next((p for p in inv if str(p['Producto']) == seleccion), None)
            
            if prod_actual:
                with st.form("form_modificar"):
                    nuevo_cod = st.text_input("Código", value=str(prod_actual.get('Codigo', ''))).strip()
                    nuevo_nom = st.text_input("Nombre", value=str(prod_actual.get('Producto', ''))).upper().strip()
                    
                    try:
                        # Limpieza de precio por si viene con formatos raros
                        p_val = str(prod_actual.get('Precio', 0)).replace(',', '.')
                        val_pre = float(p_val)
                    except:
                        val_pre = 0.0
                        
                    nuevo_pre = st.number_input("Precio", value=val_pre, min_value=0.0)
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 GUARDAR"):
                        if editar_producto_google(seleccion, nuevo_cod, nuevo_nom, nuevo_pre):
                            st.success("✅ Cambios guardados")
                            st.rerun()
                        else:
                            st.error("❌ Error al actualizar en la nube")
                    
                    if c2.form_submit_button("🧹 CANCELAR"):
                        st.rerun()

    # --- TAB 3: BAJA ---
    with tab3:
        st.subheader("Eliminar Producto")
        nombres_baja = sorted([str(p['Producto']) for p in inv if p.get('Producto')])
        eliminar = st.selectbox("Seleccione producto para borrar:", ["---"] + nombres_baja)
        
        if eliminar != "---":
            st.warning(f"¿Está seguro de eliminar '{eliminar}'?")
            if st.button("🗑️ SÍ, ELIMINAR"):
                if borrar_producto_google(eliminar):
                    st.success("✅ Eliminado correctamente")
                    st.rerun()
                else:
                    st.error("❌ Error al eliminar de Google Sheets")

    # --- TAB 4: STOCK ---
    with tab4:
        st.subheader("Estado de Stock")
        if inv:
            df_inv = pd.DataFrame(inv)
            # Reordenamos columnas para asegurar la vista A, B, C
            columnas_ok = [c for c in ['Codigo', 'Producto', 'Precio'] if c in df_inv.columns]
            df_display = df_inv[columnas_ok].sort_values(by="Producto")
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Botón de exportación
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_display.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 DESCARGAR EXCEL",
                data=buffer.getvalue(),
                file_name=f"stock_morita_{datetime.date.today()}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )
        else:
            st.info("No se encontraron productos en el inventario.")
