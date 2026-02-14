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
        # Prioridad: Intentamos traer de Google Sheets
        datos_google = obtener_inventario_google()
        if datos_google:
            return datos_google
            
        # Respaldo: Si Google falla, cargamos local
        if os.path.exists(ruta):
            with open(ruta, "r", encoding='utf-8') as f:
                return json.load(f)
        return []
    except: return []

def guardar_json(datos):
    with open("data/inventario.json", "w", encoding='utf-8') as f:
        json.dump(datos, f, indent=4)

def mostrar_abm():
    st.title("📦 PRODUCTOS") 
    inv = cargar_json()
    
    tab1, tab2, tab3, tab4 = st.tabs(["➕ ALTA", "✏️ MODIFICACIÓN", "🗑️ BAJA", "📈 STOCK"])

    # --- TAB 1: ALTA DE PRODUCTO ---
    with tab1:
        st.subheader("Cargar Nuevo Producto")
        with st.form("form_alta", clear_on_submit=True):
            nombre = st.text_input("Nombre del Producto", key="input_alta_nom").upper().strip()
            precio = st.number_input("Precio", min_value=0.0, step=100.0, key="input_alta_pre")
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ CARGAR"):
                if nombre:
                    if any(p['Producto'] == nombre for p in inv):
                        st.error(f"❌ El producto {nombre} ya existe.")
                    else:
                        # 1. Sincronizar con Google
                        exito = agregar_producto_google(nombre, precio)
                        if exito:
                            # 2. Guardar Local
                            inv.append({"Producto": nombre, "Precio": precio})
                            guardar_json(inv)
                            st.success(f"✅ PRODUCTO EN NUBE: {nombre} agregado con éxito.")
                            st.rerun()
                        else:
                            st.error("❌ Error de conexión con Google Sheets.")
                else:
                    st.error("⚠️ Ingrese un nombre válido.")
            
            if c2.form_submit_button("🧹 LIMPIAR"):
                st.rerun()

    # --- TAB 2: MODIFICACIÓN ---
    with tab2:
        st.subheader("Editar Producto Existente")
        nombres_prod = sorted([p['Producto'] for p in inv])
        seleccion = st.selectbox("Seleccione el producto a modificar:", ["---"] + nombres_prod)
        
        if seleccion != "---":
            prod_actual = next(p for p in inv if p['Producto'] == seleccion)
            
            with st.form("form_modificar"):
                nuevo_nombre = st.text_input("Nombre", value=prod_actual['Producto']).upper().strip()
                nuevo_precio = st.number_input("Precio", value=float(prod_actual['Precio']), min_value=0.0, step=100.0)
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 GUARDAR CAMBIOS"):
                    # 1. Editar en Google
                    if editar_producto_google(seleccion, nuevo_nombre, nuevo_precio):
                        # 2. Editar Local
                        inv = [p for p in inv if p['Producto'] != seleccion]
                        inv.append({"Producto": nuevo_nombre, "Precio": nuevo_precio})
                        guardar_json(inv)
                        st.success(f"✅ MODIFICADO EN NUBE: {seleccion} actualizado.")
                        st.rerun()
                    else:
                        st.error("❌ No se pudo actualizar en Google Sheets.")
                
                if c2.form_submit_button("🧹 CANCELAR"):
                    st.rerun()

    # --- TAB 3: BAJA ---
    with tab3:
        st.subheader("Eliminar Producto")
        if inv:
            eliminar = st.selectbox("Seleccione producto para borrar:", ["---"] + sorted([p['Producto'] for p in inv]))
            if eliminar != "---":
                st.warning(f"¿Está seguro de que desea eliminar '{eliminar}'?")
                if st.button("🗑️ SÍ, ELIMINAR DEFINITIVAMENTE"):
                    # 1. Borrar en Google
                    if borrar_producto_google(eliminar):
                        # 2. Borrar Local
                        inv = [p for p in inv if p['Producto'] != eliminar]
                        guardar_json(inv)
                        st.success(f"✅ ELIMINADO EN NUBE: {eliminar} fue borrado.")
                        st.rerun()
                    else:
                        st.error("❌ Error al borrar en Google Sheets.")
        else:
            st.info("No hay productos en el sistema.")

    # --- TAB 4: STOCK ---
    with tab4:
        st.subheader("Gestión de Stock (Sincronizado con Google)")
        # Forzamos recarga de Google para ver que todo esté igual
        inv_real = obtener_inventario_google()
        df_inv = pd.DataFrame(inv_real if inv_real else inv)
        
        if not df_inv.empty:
            st.dataframe(df_inv.sort_values(by="Producto"), use_container_width=True)
            
            st.divider()
            col_ex1, col_ex2 = st.columns(2)
            
            with col_ex1:
                st.write("### 📥 Descargar")
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_inv.to_excel(writer, index=False)
                st.download_button(
                    label="DESCARGAR EXCEL DE STOCK",
                    data=buffer.getvalue(),
                    file_name=f"stock_morita_{datetime.date.today()}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )

            with col_ex2:
                st.info("💡 Los cambios realizados en las pestañas anteriores se reflejan automáticamente en tu Google Sheet.")
