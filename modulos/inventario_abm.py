import streamlit as st
import pandas as pd
import json
import io
import datetime
import os

def cargar_json():
    ruta = "data/inventario.json"
    if not os.path.exists("data"):
        os.makedirs("data")
    try:
        if os.path.exists(ruta):
            with open(ruta, "r", encoding='utf-8') as f:
                return json.load(f)
        return []
    except: return []

def guardar_json(datos):
    with open("data/inventario.json", "w", encoding='utf-8') as f:
        json.dump(datos, f, indent=4)

def mostrar_abm():
    # Título simplificado a gusto del cliente
    st.title("📦 PRODUCTOS") 
    inv = cargar_json()
    
    # Pestañas con nombres simplificados
    tab1, tab2, tab3, tab4 = st.tabs(["➕ ALTA", "✏️ MODIFICACIÓN", "🗑️ BAJA", "📈 STOCK"])

    # --- TAB 1: ALTA DE PRODUCTO ---
    with tab1:
        st.subheader("Cargar Nuevo Producto")
        # Usamos session_state para la función de limpiar
        if "alta_nombre" not in st.session_state: st.session_state.alta_nombre = ""
        if "alta_precio" not in st.session_state: st.session_state.alta_precio = 0.0

        with st.form("form_alta", clear_on_submit=True):
            nombre = st.text_input("Nombre del Producto", key="input_alta_nom").upper().strip()
            precio = st.number_input("Precio", min_value=0.0, step=100.0, key="input_alta_pre")
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ CARGAR"):
                if nombre:
                    # Verificar si ya existe
                    if any(p['Producto'] == nombre for p in inv):
                        st.error(f"❌ El producto {nombre} ya existe.")
                    else:
                        inv.append({"Producto": nombre, "Precio": precio})
                        guardar_json(inv)
                        st.success(f"✅ PRODUCTO CARGADO: {nombre} ha sido agregado con éxito.")
                        st.rerun()
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
                    # Eliminar viejo y poner nuevo
                    inv = [p for p in inv if p['Producto'] != seleccion]
                    inv.append({"Producto": nuevo_nombre, "Precio": nuevo_precio})
                    guardar_json(inv)
                    st.success(f"✅ PRODUCTO MODIFICADO: {seleccion} actualizado correctamente.")
                    st.rerun()
                
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
                    inv = [p for p in inv if p['Producto'] != eliminar]
                    guardar_json(inv)
                    st.success(f"✅ PRODUCTO ELIMINADO: {eliminar} fue borrado del sistema.")
                    st.rerun()
        else:
            st.info("No hay productos en el sistema.")

    # --- TAB 4: STOCK (EXCEL / PLANILLA) ---
    with tab4:
        st.subheader("Gestión de Stock")
        df_inv = pd.DataFrame(inv)
        
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
                st.write("### 📤 Carga Masiva")
                archivo = st.file_uploader("Subir planilla .xlsx", type=['xlsx'])
                if archivo:
                    try:
                        df_nuevo = pd.read_excel(archivo, engine='openpyxl')
                        df_nuevo.columns = [str(c).strip().capitalize() for c in df_nuevo.columns]
                        
                        if 'Producto' in df_nuevo.columns and 'Precio' in df_nuevo.columns:
                            if st.button("🚀 REEMPLAZAR STOCK COMPLETO"):
                                df_final = df_nuevo[['Producto', 'Precio']].dropna()
                                df_final['Producto'] = df_final['Producto'].astype(str).str.upper().str.strip()
                                guardar_json(df_final.to_dict(orient='records'))
                                st.success(f"✅ STOCK ACTUALIZADO: Se cargaron {len(df_final)} productos.")
                                st.rerun()
                        else:
                            st.error("❌ El archivo debe tener columnas 'Producto' y 'Precio'")
                    except Exception as e:
                        st.error(f"Error: {e}")
