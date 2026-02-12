import streamlit as st
import json
import pandas as pd
import datetime
import os

# --- FUNCIONES DE PERSISTENCIA ---
def cargar_json(ruta):
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding='utf-8') as f:
                return json.load(f)
        except: return {} # Devolver diccionario para el estado
    return {}

def guardar_json(ruta, datos):
    os.makedirs("data", exist_ok=True)
    with open(ruta, "w", encoding='utf-8') as f:
        json.dump(datos, f, indent=4)

def mostrar_reporte():
    # Estilo responsive para métricas
    st.markdown("""
        <style>
            [data-testid="stMetric"] { background-color: #f8f9fa; border: 1px solid #ddd; padding: 15px; border-radius: 10px; }
            @media (max-width: 640px) { .stTable { font-size: 0.9rem !important; } }
        </style>
    """, unsafe_allow_html=True)

    st.title("💰 APERTURA / CIERRE")

    # --- LÓGICA DE SINCRONIZACIÓN POR ARCHIVO ---
    # Leemos siempre del disco para saber si el Admin abrió remotamente
    estado_disco = cargar_json("data/estado_caja.json")
    
    # Actualizamos el session_state basándonos en el archivo físico
    if isinstance(estado_disco, dict) and estado_disco.get("caja_abierta", False):
        st.session_state.caja_abierta = True
        st.session_state.turno_actual = estado_disco.get("turno_actual")
        st.session_state.monto_inicio = estado_disco.get("monto_inicio", 0.0)
    else:
        st.session_state.caja_abierta = False

    # --- 1. INTERFAZ DE APERTURA ---
    if not st.session_state.caja_abierta:
        st.warning("🔒 LA CAJA ESTÁ CERRADA")
        with st.container(border=True):
            monto = st.number_input("Monto Inicial en Efectivo $:", min_value=0.0, step=500.0)
            turno = st.selectbox("Seleccionar Turno:", ["Turno 1", "Turno 2"])
            if st.button("🔓 ABRIR CAJA", use_container_width=True, type="primary"):
                # GUARDAR EN DISCO (Para que la vendedora lo vea remoto)
                nuevo_estado = {
                    "caja_abierta": True,
                    "monto_inicio": monto,
                    "turno_actual": turno,
                    "vendedor_apertura": st.session_state.usuario_data['nombre'],
                    "fecha_apertura": str(datetime.date.today())
                }
                guardar_json("data/estado_caja.json", nuevo_estado)
                
                st.session_state.caja_abierta = True
                st.session_state.turno_actual = turno
                st.session_state.monto_inicio = monto
                st.rerun()
    
    # --- 2. INTERFAZ DE CAJA ABIERTA Y CIERRE ---
    else:
        st.success(f"✅ CAJA ABIERTA - {st.session_state.turno_actual}")
        
        # Cargamos las ventas temporales
        ventas_turno = cargar_json("data/ventas_diarias.json")
        if not isinstance(ventas_turno, list): ventas_turno = []
        
        if ventas_turno:
            df_turno = pd.DataFrame(ventas_turno)
            
            # Arqueo por Vendedor sin decimales extras
            st.subheader("👤 Arqueo por Vendedor")
            resumen_vendedores = df_turno.groupby('vendedor')['total'].sum().reset_index()
            resumen_vendedores['total'] = resumen_vendedores['total'].apply(lambda x: f"${x:,.0f}")
            resumen_vendedores.columns = ['Vendedor', 'Total $']
            st.table(resumen_vendedores)

            # Métricas
            total_vendido = df_turno['total'].sum()
            col1, col2 = st.columns(2)
            col1.metric("Ventas del Turno", f"${total_vendido:,.0f}")
            col2.metric("Total en Caja", f"${total_vendido + st.session_state.monto_inicio:,.0f}")

            with st.expander("📦 Detalle de Productos Vendidos"):
                detalles = []
                for v in ventas_turno: detalles.extend(v['detalle'])
                df_det = pd.DataFrame(detalles)
                resumen_prod = df_det.groupby('Producto')['Cantidad'].sum().reset_index()
                st.dataframe(resumen_prod, use_container_width=True)

            st.divider()
            
            if st.button("🔒 FINALIZAR TURNO Y CERRAR CAJA", type="primary", use_container_width=True):
                # 1. Mover ventas al Historial Permanente
                historial_p = cargar_json("data/historial_permanente.json")
                if not isinstance(historial_p, list): historial_p = []
                
                for v in ventas_turno: v['turno_cierre'] = st.session_state.turno_actual
                historial_p.extend(ventas_turno)
                guardar_json("data/historial_permanente.json", historial_p)
                
                # 2. LIMPIAR DISCO (Sincronización remota)
                guardar_json("data/ventas_diarias.json", [])
                guardar_json("data/estado_caja.json", {"caja_abierta": False})
                
                # 3. Resetear sesión local
                st.session_state.caja_abierta = False
                if "ticket_ready" in st.session_state: del st.session_state.ticket_ready
                
                st.success("✅ Caja cerrada y datos archivados.")
                st.rerun()
        else:
            st.info("No hay ventas registradas en este turno aún.")
            if st.button("Cerrar Caja Vacía", use_container_width=True):
                guardar_json("data/estado_caja.json", {"caja_abierta": False})
                st.session_state.caja_abierta = False
                st.rerun()

def mostrar_historial_permanente():
    st.title("📅 HISTORIAL GENERAL")
    historial = cargar_json("data/historial_permanente.json")
    
    if historial and isinstance(historial, list):
        df = pd.DataFrame(historial)
        df = df.sort_values(by=['fecha', 'hora'], ascending=False)
        
        df_mostrar = df[['fecha', 'hora', 'vendedor', 'total', 'metodo']].copy()
        df_mostrar['total'] = df_mostrar['total'].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(df_mostrar, use_container_width=True)
        
        st.divider()
        if st.button("🗑️ LIMPIAR TODO EL HISTORIAL (MODO PRUEBA)", use_container_width=True):
            guardar_json("data/historial_permanente.json", [])
            st.success("Historial borrado.")
            st.rerun()
    else:
        st.info("El historial permanente está vacío.")
