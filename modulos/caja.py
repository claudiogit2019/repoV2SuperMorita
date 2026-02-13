import streamlit as st
import json
import datetime
import pandas as pd
import os
from fpdf import FPDF
import io

# Importamos las herramientas de voz
from streamlit_mic_recorder import mic_recorder
from gemini_service import procesar_voz_completo 

# --- CONFIGURACIÓN DE HORA ARGENTINA ---
def obtener_fecha_hora():
    ahora_utc = datetime.datetime.now(datetime.timezone.utc)
    return ahora_utc - datetime.timedelta(hours=3)

def cargar_json(ruta):
    try:
        if os.path.exists(ruta):
            with open(ruta, "r", encoding='utf-8') as f: 
                content = f.read()
                data = json.loads(content) if content else {}
                return data
        return {}
    except: return {}

def generar_ticket_pdf(carrito, total, vendedor, paga_efe, paga_tra, vuelto, metodo):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "MORITA MINIMERCADO", ln=True, align="C")
        
        pdf.set_font("Arial", "", 10)
        ahora = obtener_fecha_hora()
        pdf.cell(0, 5, f"FECHA: {ahora.strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        pdf.cell(0, 5, f"CAJERO: {vendedor}", ln=True, align="C")
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(100, 8, "Producto", border=1)
        pdf.cell(20, 8, "Cant.", border=1)
        pdf.cell(35, 8, "Subtotal", border=1, ln=True)
        
        pdf.set_font("Arial", "", 10)
        for item in carrito:
            cant = item.get('Cantidad', item.get('Cant', 1))
            pdf.cell(100, 8, str(item['Producto'])[:35], border=1)
            pdf.cell(20, 8, f"{cant:g}", border=1)
            pdf.cell(35, 8, f"${item['Subtotal']:,.0f}", border=1, ln=True)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"TOTAL: ${total:,.0f}", ln=True, align="R")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, f"PAGO: ${paga_efe + paga_tra:,.0f} | VUELTO: ${vuelto:,.0f}", ln=True, align="R")
        
        # --- SOLUCIÓN PDF UNIVERSAL ---
        resultado = pdf.output() 
        if isinstance(resultado, str):
            return resultado.encode('latin-1')
        return bytes(resultado)
    except Exception as e:
        return None

def mostrar_caja():
    # --- 1. SINCRONIZACIÓN DE CAJA ---
    estado_disco = cargar_json("data/estado_caja.json")
    caja_abierta = isinstance(estado_disco, dict) and estado_disco.get("caja_abierta", False)
    turno_actual = estado_disco.get("turno_actual", "S/T")

    if not caja_abierta:
        st.error("⚠️ LA CAJA ESTÁ CERRADA. Por favor, abra la caja primero.")

    st.markdown("""
        <style>
            .total-grande { font-size: 3.5rem !important; font-weight: bold; color: #D32F2F; text-align: right; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.title(f"🛒 CAJA - {turno_actual}") 

    inv = cargar_json("data/inventario.json")
    if not isinstance(inv, list): inv = []
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    # --- COMANDO DE VOZ ---
    with st.expander("🎙️ PEDIDO POR VOZ"):
        audio = mic_recorder(start_prompt="🎙️ HABLAR", stop_prompt="⏹️ PROCESAR", key='mic_v_final')
        if audio:
            res = procesar_voz_completo(audio['bytes'], json.dumps(inv))
            if res and "|" in res: st.session_state.entendido = res

        if "entendido" in st.session_state:
            st.info(f"**DETECTADO:**\n{st.session_state.entendido}")
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
    col_izq, col_der = st.columns([1.1, 1])

    with col_izq:
        st.subheader("🔍 BUSCAR")
        busq = st.text_input("Producto:", placeholder="Escriba aquí...").upper()
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
        
        # --- MOSTRAR TICKET SI YA SE VENDIÓ ---
        if "ticket_ready" in st.session_state:
            st.success("✅ VENTA REGISTRADA CON ÉXITO")
            st.download_button("🖨️ DESCARGAR TICKET (PDF)", st.session_state.ticket_ready, "ticket.pdf", "application/pdf", use_container_width=True)
            if st.button("➕ NUEVA FACTURA", type="primary", use_container_width=True):
                del st.session_state.ticket_ready
                st.session_state.carrito = []
                st.rerun()

        # --- MOSTRAR CARRITO SI NO SE HA VENDIDO AÚN ---
        elif st.session_state.carrito:
            total = sum(i['Subtotal'] for i in st.session_state.carrito)
            for idx, item in enumerate(st.session_state.carrito):
                ca, cb, cc = st.columns([2.5, 1, 0.5])
                ca.write(f"{item['Producto']} (x{item.get('Cantidad', 1):g})")
                cb.write(f"${item['Subtotal']:,.0f}")
                if cc.button("❌", key=f"del_{idx}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()

            st.divider()
            metodo = st.radio("Método:", ["Efectivo", "Transferencia", "Ambos"], horizontal=True)
            p_efe, p_tra = 0.0, 0.0
            if metodo == "Efectivo": p_efe = st.number_input("Paga con:", value=float(total))
            elif metodo == "Transferencia": p_tra = total
            else:
                c1, c2 = st.columns(2)
                p_efe = c1.number_input("Efe:")
                p_tra = c2.number_input("Transf:")
            
            vuelto = max(0.0, (p_efe + p_tra) - total)
            st.markdown(f'<p class="total-grande">TOTAL: ${total:,.0f}</p>', unsafe_allow_html=True)
            if vuelto > 0: st.success(f"Vuelto: ${vuelto:,.0f}")

            if st.button("✅ FINALIZAR VENTA", type="primary", use_container_width=True):
                if not caja_abierta:
                    st.error("LA CAJA ESTÁ CERRADA")
                else:
                    # 1. REGISTRO EN EL ARCHIVO (Para que lo vea el Administrador)
                    v_raw = cargar_json("data/ventas_diarias.json")
                    ventas = v_raw if isinstance(v_raw, list) else []
                    ahora = obtener_fecha_hora()
                    
                    nueva_venta = {
                        "fecha": ahora.strftime("%Y-%m-%d"),
                        "hora": ahora.strftime("%H:%M:%S"),
                        "vendedor": st.session_state.usuario_data.get('nombre', 'Cajero'),
                        "turno": turno_actual,
                        "total": total,
                        "metodo": metodo,
                        "detalle": st.session_state.carrito
                    }
                    ventas.append(nueva_venta)
                    
                    with open("data/ventas_diarias.json", "w", encoding='utf-8') as f:
                        json.dump(ventas, f, indent=4)
                    
                    # 2. GENERACIÓN DEL PDF
                    pdf = generar_ticket_pdf(st.session_state.carrito, total, st.session_state.usuario_data.get('nombre', 'Cajero'), p_efe, p_tra, vuelto, metodo)
                    if pdf:
                        st.session_state.ticket_ready = pdf
                        st.rerun()

            if st.button("🗑️ LIMPIAR TODO", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("Carrito vacío")

