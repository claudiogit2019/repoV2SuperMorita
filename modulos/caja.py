import streamlit as st
import json
import datetime
import pandas as pd
import os
from fpdf import FPDF
import io
from streamlit_mic_recorder import mic_recorder
from gemini_service import procesar_voz_completo 

# --- FUNCIONES DE APOYO (IDÉNTICAS A REPUESTOS) ---
def obtener_fecha_hora():
    ahora_utc = datetime.datetime.now(datetime.timezone.utc)
    return ahora_utc - datetime.timedelta(hours=3)

def cargar_json(ruta):
    try:
        if os.path.exists(ruta):
            with open(ruta, "r", encoding='utf-8') as f:
                return json.load(f)
        return []
    except: return []

def guardar_json(ruta, datos):
    with open(ruta, "w", encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

# --- GENERADOR DE PDF (ADAPTADO DE TU CÓDIGO DE REPUESTOS) ---
def generar_ticket_pdf(items, total, paga, vuelto, vendedor):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 22)
    pdf.cell(190, 15, "MORITA MINIMERCADO", ln=True, align='C')
    pdf.set_font("helvetica", '', 14)
    pdf.cell(190, 10, f"VENDEDOR: {vendedor.upper()}", ln=True, align='C')
    pdf.cell(190, 10, f"FECHA: {obtener_fecha_hora().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    pdf.set_font("helvetica", 'B', 12)
    for i in items:
        # Usamos .get por si la clave es 'Cant' o 'Cantidad'
        c = i.get('Cantidad', i.get('Cant', 1))
        pdf.cell(90, 10, f"{i['Producto'].upper()[:25]}")
        pdf.cell(40, 10, f"x{round(c, 2)}")
        pdf.cell(60, 10, f"${round(i['Subtotal'], 2):,.2f}", ln=True, align='R')
    
    pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    pdf.set_font("helvetica", 'B', 18)
    pdf.cell(130, 12, "TOTAL:", align='R'); pdf.cell(60, 12, f"${total:,.2f}", ln=True, align='R')
    pdf.set_font("helvetica", '', 14) 
    pdf.cell(130, 10, "PAGA CON:", align='R'); pdf.cell(60, 10, f"${paga:,.2f}", ln=True, align='R')
    pdf.cell(130, 12, "VUELTO:", align='R'); pdf.cell(60, 12, f"${vuelto:,.2f}", ln=True, align='R')
    
    # El truco de los bytes que te funciona en Repuestos
    return bytes(pdf.output())

def mostrar_caja():
    # 1. Cargar Estado de Caja y Usuarios
    estado_caja = cargar_json("data/estado_caja.json")
    if isinstance(estado_caja, list): estado_caja = {} # Parche por si el json está vacío
    
    caja_abierta = estado_caja.get("caja_abierta", False)
    turno = estado_caja.get("turno_actual", "S/T")

    st.title(f"🛒 CAJA - {turno}")

    # Inicializar Carrito
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    # Cargar Inventario
    inv = cargar_json("data/inventario.json")

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("🔍 BUSCAR")
        busq = st.text_input("Producto:", placeholder="Escriba aquí...").upper()
        if len(busq) >= 2:
            coincidencias = [p for p in inv if busq in str(p['Producto']).upper()][:10]
            for p in coincidencias:
                c_n, c_c, c_a = st.columns([2, 1, 0.5])
                c_n.write(f"**{p['Producto']}**\n${p['Precio']:,.0f}")
                cant = c_c.number_input("Cant.", min_value=0.1, value=1.0, key=f"k_{p['Producto']}")
                if c_a.button("➕", key=f"btn_{p['Producto']}"):
                    st.session_state.carrito.append({
                        "Producto": p['Producto'], 
                        "Precio": p['Precio'], 
                        "Cantidad": cant, 
                        "Subtotal": p['Precio'] * cant
                    })
                    st.rerun()

    with col2:
        st.subheader("🧾 DETALLE DE VENTA")
        if st.session_state.carrito:
            total_f = round(sum(i['Subtotal'] for i in st.session_state.carrito), 2)
            
            # Tabla de productos en el carrito
            for idx, item in enumerate(st.session_state.carrito):
                cf1, cf2, cf3, cf4 = st.columns([3, 1, 1, 0.5])
                cf1.write(f"{item['Producto']}")
                cf2.write(f"x{item['Cantidad']}")
                cf3.write(f"${item['Subtotal']:,.0f}")
                if cf4.button("❌", key=f"del_{idx}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()

            st.divider()
            st.markdown(f"## TOTAL: ${total_f:,.2f}")
            
            paga = st.number_input("PAGA CON ($):", min_value=0.0, value=float(total_f))
            vuelto = round(max(0.0, paga - total_f), 2)
            st.success(f"VUELTO: ${vuelto:,.2f}")

            # FILA DE BOTONES (Igual que en Repuestos)
            b1, b2, b3 = st.columns(3)
            
            # BOTÓN 1: FINALIZAR (Aquí es donde se guarda al JSON)
            if b1.button("⚡ FINALIZAR", use_container_width=True):
                if not caja_abierta:
                    st.error("Caja cerrada. No se guardará.")
                else:
                    # Guardar Venta
                    ventas = cargar_json("data/ventas_diarias.json")
                    if not isinstance(ventas, list): ventas = []
                    
                    nueva_v = {
                        "fecha": obtener_fecha_hora().strftime("%Y-%m-%d"),
                        "vendedor": st.session_state.usuario_data.get('nombre', 'Cajero'),
                        "total": total_f,
                        "metodo": "Efectivo", # Simplificado para asegurar guardado
                        "detalle": st.session_state.carrito
                    }
                    ventas.append(nueva_v)
                    guardar_json("data/ventas_diarias.json", ventas)
                    
                    # Limpiar y Avisar
                    st.session_state.carrito = []
                    st.toast("Venta Guardada con éxito!")
                    st.rerun()

            # BOTÓN 2: PDF (Funciona igual que en Repuestos)
            pdf_bytes = generar_ticket_pdf(st.session_state.carrito, total_f, paga, vuelto, st.session_state.usuario_data.get('nombre', 'Pamela'))
            b2.download_button("🖨️ TICKET", data=pdf_bytes, file_name="ticket.pdf", mime="application/pdf", use_container_width=True)

            # BOTÓN 3: REINICIAR
            if b3.button("🔄 REINICIAR", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("La caja está vacía.")
