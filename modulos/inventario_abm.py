import streamlit as st
import pandas as pd
import json
import io
import datetime

def cargar_json():
    try:
        with open("data/inventario.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except: return []

def guardar_json(datos):
    with open("data/inventario.json", "w", encoding='utf-8') as f:
        json.dump(datos, f, indent=4)

def mostrar_abm():
    st.title("📦 GESTIÓN DE PRODUCTOS")
    inv = cargar_json()
    df_inv = pd.DataFrame(inv)

    tab1, tab2, tab3 = st.tabs(["📄 PLANILLA Y EXCEL", "➕ ALTA / MODIFICACIÓN", "🗑️ BAJA"])

    with tab1:
        st.subheader("Inventario Actual (Producto y Precio)")
        st.dataframe(df_inv, use_container_width=True)
        
        col_ex1, col_ex2 = st.columns(2)
        # DESCARGA
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_inv.to_excel(writer, index=False)
        
        col_ex1.download_button(
            label="📥 DESCARGAR EXCEL",
            data=buffer,
            file_name=f"inventario_{datetime.date.today()}.xlsx",
            mime="application/vnd.ms-excel"
        )
        # SUBIDA
        archivo = col_ex2.file_uploader("📤 SUBIR EXCEL (Solo columnas 'Producto' y 'Precio')", type=['xlsx'])
        if archivo:
            df_nuevo = pd.read_excel(archivo)
            # Aseguramos que solo queden las columnas Producto y Precio
            if 'Producto' in df_nuevo.columns and 'Precio' in df_nuevo.columns:
                if st.button("CONFIRMAR REEMPLAZO TOTAL"):
                    guardar_json(df_nuevo[['Producto', 'Precio']].to_dict(orient='records'))
                    st.success("Inventario actualizado correctamente")
                    st.rerun()
            else:
                st.error("El Excel debe tener las columnas 'Producto' y 'Precio'")

    with tab2:
        st.subheader("Alta o Modificación")
        nombres = ["NUEVO PRODUCTO"] + [p['Producto'] for p in inv]
        seleccion = st.selectbox("Seleccione para editar:", nombres)
        
        # Corregido: El formulario ahora tiene su botón de envío interno
        with st.form("form_edicion"):
            if seleccion == "NUEVO PRODUCTO":
                nombre = st.text_input("Nombre del Producto")
                precio = st.number_input("Precio", min_value=0.0, step=0.01)
            else:
                prod_data = next(p for p in inv if p['Producto'] == seleccion)
                nombre = st.text_input("Nombre", value=prod_data['Producto'])
                precio = st.number_input("Precio", value=float(prod_data['Precio']), step=0.01)
            
            # BOTÓN OBLIGATORIO PARA STREAMLIT FORMS
            enviar = st.form_submit_button("💾 GUARDAR CAMBIOS")
            
            if enviar:
                # Quitamos el anterior si es edición
                if seleccion != "NUEVO PRODUCTO":
                    inv = [p for p in inv if p['Producto'] != seleccion]
                inv.append({"Producto": nombre.upper(), "Precio": precio})
                guardar_json(inv)
                st.success(f"Producto {nombre} guardado.")
                st.rerun()

    with tab3:
        st.subheader("Eliminar")
        eliminar = st.selectbox("Producto a eliminar:", [""] + [p['Producto'] for p in inv])
        if eliminar and st.button("🗑️ ELIMINAR DEFINITIVAMENTE"):
            inv = [p for p in inv if p['Producto'] != eliminar]
            guardar_json(inv)
            st.warning("Producto eliminado")
            st.rerun()
