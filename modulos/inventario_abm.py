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
            # Guardamos copia local limpia
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
    
    # --- FILTRO ANTICORRIMIENTO (Mapeo Seguro) ---
    # Solo procesamos filas que tengan contenido real en 'Producto'
    # y convertimos todo a string para evitar errores de tipo.
    inv = []
    for p in inv_raw:
        if isinstance(p, dict) and p.get('Producto'):
            item = {
                "Codigo": str(p.get('Codigo', '')).strip(),
                "Producto": str(p.get('Producto', '')).strip().upper(),
                "Precio": p.get('Precio', 0)
            }
            inv.append(item)

    tab1, tab2, tab3, tab4 = st.tabs(["➕ ALTA", "✏️ MODIFICACIÓN", "🗑️ BAJA", "📈 STOCK"])

    # --- TAB 1: ALTA DE PRODUCTO ---
    with tab1:
        st.subheader("Cargar Nuevo Producto")
        with st.form("form_alta", clear_on_submit=True):
            codigo = st.text_input("Código de Barras (Scanner)", key="input_alta_cod").strip()
            nombre = st.text_input("Nombre del Producto", key="input_alta_nom").upper().strip()
            precio = st.number_input("Precio", min_value=0.0, step=10.0, key="input_alta_pre")
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ CARGAR"):
                if nombre and codigo:
                    # Buscamos duplicados de forma estricta
                    if any(p['Codigo'] == codigo for p in inv):
                        st.error(f"❌ El código {codigo} ya existe.")
                    elif any(p['Producto'] == nombre for p in inv):
                        st.error(f"❌ El producto {nombre} ya existe.")
                    else:
                        # Mandamos a Google Sheets
                        if agregar_producto_google(codigo, nombre, precio):
                            st.success(f"✅ PRODUCTO CARGADO: {nombre}")
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
        nombres_prod = sorted([p['Producto'] for p in inv])
        seleccion = st.selectbox("Seleccione para modificar:", ["---"] + nombres_prod)
        
        if seleccion != "---":
            prod_actual = next((p for p in inv if p['Producto'] == seleccion), None)
            
            if prod_actual:
                with st.form("form_modificar"):
                    nuevo_cod = st.text_input("Código", value=prod_actual['Codigo']).strip()
                    nuevo_nom = st.text_input("Nombre", value=prod_actual['Producto']).upper().strip()
                    
                    # Manejo de precio seguro
                    try:
                        val_pre = float(str(prod_actual['Precio']).replace(',', '.'))
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
        nombres_baja = sorted([p['Producto'] for p in inv])
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
        if inv:
            df_inv = pd.DataFrame(inv)
            df_display = df_inv[['Codigo', 'Producto', 'Precio']].sort_values(by="Producto")
            st.dataframe(df_display, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_display.to_excel(writer, index=False)
            st.download_button(label="📥 EXPORTAR", data=buffer.getvalue(), file_name="stock.xlsx")
        else:
            st.info("Inventario vacío o error de carga.")
