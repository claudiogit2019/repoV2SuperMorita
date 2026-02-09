import streamlit as st
import json
import pandas as pd
import datetime

def mostrar_reporte():
    st.title("📊 CIERRE DE CAJA Y TURNOS")

    # Inicializamos estados si no existen
    if 'caja_abierta' not in st.session_state: st.session_state.caja_abierta = False

    if not st.session_state.caja_abierta:
        st.warning("LA CAJA ESTÁ CERRADA")
        with st.form("apertura"):
            monto = st.number_input("Monto Inicial en Efectivo:", min_value=0.0)
            turno = st.selectbox("Turno:", ["Mañana", "Tarde", "Noche"])
            if st.form_submit_button("🔓 ABRIR CAJA"):
                st.session_state.caja_abierta = True
                st.session_state.monto_inicio = monto
                st.session_state.turno_actual = turno
                st.rerun()
    else:
        st.success(f"Caja abierta - Turno: {st.session_state.turno_actual}")
        
        try:
            with open("data/ventas_diarias.json", "r") as f: ventas = json.load(f)
        except: ventas = []

        if ventas:
            df = pd.DataFrame(ventas)
            st.metric("VENTAS TOTALES DEL TURNO", f"${df['total'].sum():,.2f}")
            
            # SECCIÓN SOLICITADA: Cantidad de productos vendidos
            st.subheader("📦 CANTIDADES VENDIDAS")
            detalles = []
            for v in ventas: detalles.extend(v['detalle'])
            df_det = pd.DataFrame(detalles)
            resumen = df_det.groupby('Producto')['Cantidad'].sum().reset_index()
            st.table(resumen)
            
            st.subheader("📜 Historial de Ventas")
            st.dataframe(df[['hora', 'vendedor', 'total']])
        
        if st.button("🔒 CERRAR CAJA (Finalizar Turno)"):
            # Aquí podrías mover las ventas a un historial permanente antes de borrar
            with open("data/ventas_diarias.json", "w") as f: json.dump([], f)
            st.session_state.caja_abierta = False
            st.success("Turno cerrado. Datos de ventas reiniciados.")
            st.rerun()