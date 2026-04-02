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
            return datos_google
        if os.path.exists(ruta):
            with open(ruta, "r", encoding='utf-8') as f:
                return json.load(f)
        return []
    except: return []

def guardar_json(datos):
    with open("data/inventario.json", "w", encoding='utf-8') as f:
        json.dump(datos, f, indent=4)

def mostrar_abm():
    st.title("📦 GESTIÓN DE PRODUCTOS") 
    inv = cargar_json()
    
    tab1, tab2, tab3, tab4 = st.tabs(["➕ ALTA", "✏️ MODIFICACIÓN", "🗑️ BAJA", "📈 STOCK"])

    # --- TAB 1: ALTA DE PRODUCTO ---
    with tab1:
        st.subheader("Cargar Nuevo Producto")
        with st.form("form_alta", clear_on_submit=True):
            # Agregamos campo Código
            codigo = st.text_input("Código de Barras (Scanner)", key="input_alta_cod").strip()
            nombre = st.text_input("Nombre del Producto", key="input_alta_nom").upper().strip()
            precio = st.number_input("Precio", min_value=0.0, step=100.0, key="input_alta_pre")
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ CARGAR"):
                if nombre and codigo:
                    # Verificamos duplicados por código o nombre
                    if any(str(p.get('Codigo')) == codigo for p in inv):
                        st.error(f"❌ El código {codigo} ya existe.")
                    elif any(p['Producto'] == nombre for p in inv):
                        st.error(f"❌ El producto {nombre} ya existe.")
                    else:
                        if agregar_producto_google(codigo, nombre, precio):
                            inv.append({"Codigo": codigo, "Producto": nombre, "Precio": precio})
                            guardar_json(inv)
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
            prod_actual = next(p for p in inv if p['Producto'] == seleccion)
            with st.form("form_modificar"):
                nuevo_cod = st.text_input("Código", value=str(prod_actual.get('Codigo', ''))).strip()
                nuevo_nom = st.text_input("Nombre", value=prod_actual['Producto']).upper().strip()
                nuevo_pre = st.number_input("Precio", value=float(prod_actual['Precio']), min_value=0.0)
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 GUARDAR"):
                    if editar_producto_google(seleccion, nuevo_cod, nuevo_nom, nuevo_pre):
                        inv = [p for p in inv if p['Producto'] != seleccion]
                        inv.append({"Codigo": nuevo_cod, "Producto": nuevo_nom, "Precio": nuevo_pre})
                        guardar_json(inv)
                        st.success("✅ Cambios guardados")
                        st.rerun()
                    else:
                        st.error("❌ Error en Google Sheets")
                
                if c2.form_submit_button("🧹 CANCELAR"):
                    st.rerun()

    # --- TAB 3: BAJA ---
    with tab3:
        st.subheader("Eliminar Producto")
        eliminar = st.selectbox("Seleccione producto:", ["---"] + sorted([p['Producto'] for p in inv]))
        if eliminar != "---":
            st.warning(f"¿Eliminar '{eliminar}'?")
            if st.button("🗑️ SÍ, ELIMINAR"):
                if borrar_producto_google(eliminar):
                    inv = [p for p in inv if p['Producto'] != eliminar]
                    guardar_json(inv)
                    st.success("✅ Eliminado")
                    st.rerun()
                else:
                    st.error("❌ Error en Google Sheets")

    # --- TAB 4: STOCK Y EXPORTACIÓN ---
    with tab4:
        st.subheader("Gestión de Stock")
        df_inv = pd.DataFrame(obtener_inventario_google() or inv)
        
        if not df_inv.empty:
            # Reordenar para ver Código primero
            cols = ['Codigo', 'Producto', 'Precio']
            df_inv = df_inv[cols] if all(c in df_inv.columns for c in cols) else df_inv
            st.dataframe(df_inv.sort_values(by="Producto"), use_container_width=True)
            
            st.divider()
            st.write("### 📥 Descargar Reporte")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_inv.to_excel(writer, index=False)
            st.download_button(
                label="DESCARGAR EXCEL",
                data=buffer.getvalue(),
                file_name=f"stock_morita_{datetime.date.today()}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )

