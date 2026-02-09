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
    st.title("📦 GESTIÓN DE PRODUCTOS")
    inv = cargar_json()
    df_inv = pd.DataFrame(inv)

    tab1, tab2, tab3 = st.tabs(["📄 PLANILLA Y EXCEL", "➕ ALTA / MODIFICACIÓN", "🗑️ BAJA"])

    with tab1:
        st.subheader("Inventario Actual")
        if not df_inv.empty:
            st.dataframe(df_inv, use_container_width=True)
        else:
            st.info("El inventario está vacío.")
        
        st.divider()
        col_ex1, col_ex2 = st.columns(2)
        
        # --- SECCIÓN DESCARGA ---
        with col_ex1:
            st.write("### 📥 Exportar")
            if not df_inv.empty:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_inv.to_excel(writer, index=False)
                
                st.download_button(
                    label="DESCARGAR EXCEL ACTUAL",
                    data=buffer,
                    file_name=f"inventario_morita_{datetime.date.today()}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )

        # --- SECCIÓN SUBIDA (CARGA MASIVA) ---
        with col_ex2:
            st.write("### 📤 Carga Masiva")
            archivo = st.file_uploader("Subir planilla (.xlsx)", type=['xlsx'])
            if archivo:
                try:
                    # Usamos openpyxl para evitar el error de motor
                    df_nuevo = pd.read_excel(archivo, engine='openpyxl')
                    
                    # Limpiamos nombres de columnas (quitar espacios y normalizar)
                    df_nuevo.columns = [str(c).strip().capitalize() for c in df_nuevo.columns]
                    
                    if 'Producto' in df_nuevo.columns and 'Precio' in df_nuevo.columns:
                        st.warning("⚠️ Esto reemplazará todos los productos actuales.")
                        if st.button("🚀 CONFIRMAR CARGA TOTAL"):
                            # Limpieza de datos: quitar filas vacías y convertir nombres a Mayúsculas
                            df_final = df_nuevo[['Producto', 'Precio']].dropna()
                            df_final['Producto'] = df_final['Producto'].astype(str).str.upper().str.strip()
                            
                            guardar_json(df_final.to_dict(orient='records'))
                            st.success(f"✅ ¡Se cargaron {len(df_final)} productos correctamente!")
                            st.rerun()
                    else:
                        st.error("❌ El Excel debe tener las columnas 'Producto' y 'Precio'")
                except Exception as e:
                    st.error(f"Error al leer el archivo: {e}")

    with tab2:
        st.subheader("Alta o Modificación Manual")
        nombres_prod = [p['Producto'] for p in inv]
        seleccion = st.selectbox("Seleccione un producto para editar o elija 'NUEVO':", ["--- NUEVO PRODUCTO ---"] + nombres_prod)
        
        with st.form("form_edicion"):
            if seleccion == "--- NUEVO PRODUCTO ---":
                nombre = st.text_input("Nombre del Producto (Ej: COCA COLA 1.5L)")
                precio = st.number_input("Precio de Venta", min_value=0.0, step=100.0)
            else:
                prod_data = next(p for p in inv if p['Producto'] == seleccion)
                nombre = st.text_input("Nombre", value=prod_data['Producto'])
                precio = st.number_input("Precio", value=float(prod_data['Precio']), step=100.0)
            
            enviar = st.form_submit_button("💾 GUARDAR PRODUCTO")
            
            if enviar:
                if nombre:
                    # Si es edición, quitamos el viejo antes de agregar el nuevo
                    if seleccion != "--- NUEVO PRODUCTO ---":
                        inv = [p for p in inv if p['Producto'] != seleccion]
                    
                    inv.append({"Producto": nombre.upper().strip(), "Precio": precio})
                    guardar_json(inv)
                    st.success(f"✅ {nombre.upper()} guardado con éxito.")
                    st.rerun()
                else:
                    st.error("El nombre del producto no puede estar vacío.")

    with tab3:
        st.subheader("Eliminar Producto")
        if inv:
            eliminar = st.selectbox("Seleccione producto a borrar:", [""] + [p['Producto'] for p in inv])
            if eliminar:
                st.error(f"¿Está seguro de eliminar {eliminar}?")
                if st.button("🗑️ SÍ, ELIMINAR DEFINITIVAMENTE"):
                    inv = [p for p in inv if p['Producto'] != eliminar]
                    guardar_json(inv)
                    st.success("Producto eliminado.")
                    st.rerun()
        else:
            st.info("No hay productos para eliminar.")
