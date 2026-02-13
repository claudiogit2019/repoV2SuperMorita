import streamlit as st
import json
import datetime
import pandas as pd
import os
from fpdf import FPDF
import io
from streamlit_mic_recorder import mic_recorder
from gemini_service import procesar_voz_completo 

# --- FUNCIONES DE APOYO ---
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

# --- GENERADOR DE PDF ---
def generar_ticket_pdf(items, total, paga_efe, paga_tra, vuelto, vendedor, metodo):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 20)
        pdf.cell(190, 15, "MORITA MINIMERCADO", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(190, 10, f"FECHA: {obtener_fecha_hora().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
        pdf.cell(190, 10, f"CAJERO: {vendedor.upper()}", ln=True, align='C')
        pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(90, 8, "PRODUCTO")
        pdf.cell(30, 8, "CANT.")
        pdf.cell(60, 8, "SUBTOTAL", ln=True, align='R')
        
        pdf.set_font("Arial", '', 10)
        for i in items:
            c = i.get('Cantidad', i.get('Cant', 1))
            # Limpieza de caracteres para evitar errores de encoding
            nombre = str(i['Producto'])[:30].encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(90, 8, nombre)
            pdf.cell(30, 8, f"{c:g}")
            pdf.cell(60, 8, f"${i['Subtotal']:,.0f}", ln=True, align='R')
        
        pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(130, 10, "TOTAL:", align='R'); pdf.cell(60, 10, f"${total:,.0f}", ln=True, align='R')
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(130, 7, f"METODO: {metodo}", align='R', ln=True)
        pdf.cell(130, 7, f"EFECTIVO: ${paga_efe:,.0f}", align='R', ln=True)
        pdf.cell(130, 7, f"TRANSFERENCIA: ${paga_tra:,.0f}", align='R', ln=True)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(130, 10, "VUELTO:", align='R'); pdf.cell(60, 10, f"${vuelto:,.0f}", ln=True, align='R')
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Error PDF: {e}")
        return None

def mostrar_caja():
    estado_disco = cargar_json("data/estado_caja.json")
    if isinstance(estado_disco, list): estado_disco = {}
    caja_abierta = estado_disco.get("caja_abierta", False)
    turno_actual = estado_disco.get("turno_actual", "S/T")

    if not caja_abierta:
        st.error("⚠️ LA CAJA ESTÁ CERRADA.")

    st.markdown("<style>.total-grande { font-size: 3.5rem !important; font-weight: bold; color: #D32F2F; text-align: right; }</style>", unsafe_allow_html=True)
    st.title(f"🛒 CAJA - {turno_actual}") 

    inv = cargar_json("data/inventario.json")
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    # --- COMANDO DE VOZ ---
    with st.expander("🎙️ PEDIDO POR VOZ"):
        audio = mic_recorder(start_prompt="🎙️ HABLAR", stop_prompt="⏹️ PROCESAR", key='mic_v_final')
        if audio:
            res = procesar_voz_completo(audio['bytes'], json.dumps(inv))
            if res and "|" in res: st.session_state.entendido = res
        if "entendido" in st.session_state:
            st.info(f"IA ENTENDIÓ:\n{st.session_state.entendido}")
            c1, c2 = st.columns(2)
            if c1.button("✅ AGREGAR"):
                for linea in st.session_state.entendido.split("\n"):
                    if "|" in linea:
                        p = linea.split("|")
                        st.session_state.carrito.append({"Producto": p[0].strip(), "Cantidad": float(p[1].strip()), "Subtotal": float(p[2].strip().replace("$","").replace(",",""))})
                del st.session_state.entendido
                st.rerun()
            if c2.button("🗑️ DESCARTAR"):
                del st.session_state.entendido
                st.rerun()

    st.divider()
    col_izq, col_der = st.columns([1, 1.2])

    with col_izq:
        st.subheader("🔍 BUSCAR")
        busq = st.text_input("Producto:", key="busq").upper()
        if len(busq) >= 2:
            coincidencias = [p for p in inv if busq in str(p['Producto']).upper()][:12]
            for p in coincidencias:
                cn, cc, ca = st.columns([2, 1, 0.6])
                cn.write(f"**{p['Producto']}**\n${p['Precio']:,.0f}")
                cant_m = cc.number_input("Cant.", min_value=0.1, value=1.0, key=f"k_{p['Producto']}")
                if ca.button("➕", key=f"add_{p['Producto']}"):
                    st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "Cantidad": cant_m, "Subtotal": p['Precio'] * cant_m})
                    st.rerun()

    with col_der:
        st.subheader("📋 FACTURA")
        
        # PERSISTENCIA DEL TICKET DESPUÉS DE FINALIZAR
        if "venta_hecha" in st.session_state:
            st.success("✅ VENTA REGISTRADA")
            st.download_button("🖨️ DESCARGAR TICKET PDF", data=st.session_state.pdf_cache, file_name="ticket.pdf", mime="application/pdf", use_container_width=True)
            if st.button("➕ NUEVA FACTURA", type="primary", use_container_width=True):
                del st.session_state.venta_hecha
                del st.session_state.pdf_cache
                st.session_state.carrito = []
                st.rerun()
        
        elif st.session_state.carrito:
            total = sum(i['Subtotal'] for i in st.session_state.carrito)
            for idx, item in enumerate(st.session_state.carrito):
                ca, cb, cc = st.columns([2.5, 1, 0.5])
                ca.write(f"{item['Producto']} (x{item['Cantidad']:g})")
                cb.write(f"${item['Subtotal']:,.0f}")
                if cc.button("❌", key=f"d_{idx}"):
                    st.session_state.carrito.pop(idx); st.rerun()

            st.divider()
            metodo = st.radio("Método de Pago:", ["Efectivo", "Transferencia", "Ambos"], horizontal=True)
            
            p_efe, p_tra = 0.0, 0.0
            if metodo == "Efectivo":
                p_efe = st.number_input("Paga con $:", value=float(total))
            elif metodo == "Transferencia":
                p_tra = total
            else: # AMBOS (Aquí recuperamos los dos campos)
                c1, c2 = st.columns(2)
                p_efe = c1.number_input("Monto Efectivo $:")
                p_tra = c2.number_input("Monto Transferencia $:")
            
            vuelto = max(0.0, (p_efe + p_tra) - total)
            st.markdown(f'<p class="total-grande">TOTAL: ${total:,.0f}</p>', unsafe_allow_html=True)
            if vuelto > 0: st.success(f"Vuelto: ${vuelto:,.0f}")

            if st.button("✅ FINALIZAR VENTA", type="primary", use_container_width=True):
                if not caja_abierta:
                    st.error("LA CAJA ESTÁ CERRADA")
                else:
                    # 1. Guardar en JSON
                    ventas = cargar_json("data/ventas_diarias.json")
                    if not isinstance(ventas, list): ventas = []
                    nueva_v = {
                        "fecha": obtener_fecha_hora().strftime("%Y-%m-%d"),
                        "hora": obtener_fecha_hora().strftime("%H:%M:%S"),
                        "vendedor": st.session_state.usuario_data.get('nombre', 'Pamela'),
                        "total": total, "metodo": metodo, "detalle": st.session_state.carrito
                    }
                    ventas.append(nueva_v)
                    guardar_json("data/ventas_diarias.json", ventas)
                    
                    # 2. Generar PDF para el botón de descarga
                    pdf = generar_ticket_pdf(st.session_state.carrito, total, p_efe, p_tra, vuelto, st.session_state.usuario_data.get('nombre', 'Pamela'), metodo)
                    
                    st.session_state.pdf_cache = pdf
                    st.session_state.venta_hecha = True
                    st.rerun()

            if st.button("🗑️ LIMPIAR TODO"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("Carrito vacío")

