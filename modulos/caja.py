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
                # Si es el archivo de estado, esperamos un diccionario, si no una lista
                return json.loads(content) if content else {}
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
            c_v = f"{item['Cantidad']:g}"
            pdf.cell(100, 8, str(item['Producto'])[:35], border=1)
            pdf.cell(20, 8, str(c_v), border=1)
            pdf.cell(35, 8, f"${item['Subtotal']:,.0f}", border=1, ln=True)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"TOTAL: ${total:,.0f}", ln=True, align="R")
        
        output_raw = pdf.output()
        if isinstance(output_raw, bytearray):
            return bytes(output_raw)
        elif isinstance(output_raw, str):
            return output_raw.encode('latin-1')
        return output_raw
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None

def mostrar_caja():
    # --- BLOQUE DE SINCRONIZACIÓN REMOTA ---
    # Leemos el estado físico desde la carpeta data
    estado_disco = cargar_json("data/estado_caja.json")
    
    if isinstance(estado_disco, dict) and estado_disco.get("caja_abierta", False):
        st.session_state.caja_abierta = True
        st.session_state.turno_actual = estado_disco.get("turno_actual", "S/T")
    else:
        st.session_state.caja_abierta = False
        st.session_state.turno_actual = "S/T"
    # ---------------------------------------

    st.markdown("""
        <style>
            div[data-testid="InputInstructions"] { display: none; }
            .total-grande { font-size: 3.5rem !important; font-weight: bold; color: #D32F2F; text-align: right; line-height: 1; margin-bottom: 15px; }
            @media (max-width: 640px) {
                .total-grande { font-size: 2.5rem !important; }
            }
        </style>
    """, unsafe_allow_html=True)

    t_actual = st.session_state.turno_actual
    st.title(f"🛒 CAJA - {t_actual}") 

    inv = cargar_json("data/inventario.json")
    if not isinstance(inv, list): inv = [] # Aseguramos que el inventario sea lista
    
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    # --- COMANDO DE VOZ ---
    with st.expander("🎙️ PEDIDO POR VOZ"):
        audio = mic_recorder(start_prompt="🎙️ HABLAR", stop_prompt="⏹️ PROCESAR", key='mic_caja_v3')
        if audio:
            with st.spinner("Analizando..."):
                try:
                    res = procesar_voz_completo(audio['bytes'], json.dumps(inv))
                    if res and "|" in res: st.session_state.entendido = res
                    else: st.warning("No se reconoció el pedido.")
                except Exception as e: st.error(f"Error de voz: {e}")

        if "entendido" in st.session_state:
            st.info(f"**DETECTADO:**\n\n{st.session_state.entendido}")
            c1, c2 = st.columns(2)
            if c1.button("✅ AGREGAR AL CARRITO", use_container_width=True):
                for linea in st.session_state.entendido.split("\n"):
                    if "|" in linea:
                        try:
                            p = linea.split("|")
                            nom, cant, sub = p[0].strip(), float(p[1].strip()), float(p[2].strip().replace("$","").replace(",",""))
                            precio_u = next((item['Precio'] for item in inv if item['Producto'] == nom), sub/cant)
                            st.session_state.carrito.append({"Producto": nom, "Precio": precio_u, "Cantidad": cant, "Subtotal": sub})
                        except: continue
                del st.session_state.entendido
                st.rerun()
            if c2.button("🗑️ DESCARTAR", use_container_width=True):
                del st.session_state.entendido
                st.rerun()

    st.divider()

    col_izq, col_der = st.columns([1.1, 1])

    with col_izq:
        st.subheader("🔍 BUSCAR")
        busq = st.text_input("Producto:", label_visibility="collapsed", placeholder="Buscar...").upper()
        if len(busq) >= 2:
            coincidencias = [p for p in inv if busq in str(p['Producto']).upper()][:12]
            for p in coincidencias:
                c_nom, c_cant, c_add = st.columns([2, 1, 0.6])
                c_nom.write(f"**{p['Producto']}**\n${p['Precio']:,.0f}")
                cant_m = c_cant.number_input("Cant.", min_value=0.1, value=1.0, key=f"m_{p['Producto']}", step=1.0)
                if c_add.button("➕", key=f"b_{p['Producto']}", use_container_width=True):
                    st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "Cantidad": cant_m, "Subtotal": p['Precio'] * cant_m})
                    st.rerun()

    with col_der:
        st.subheader("📋 CARRITO")
        if st.session_state.carrito:
            total = sum(i['Subtotal'] for i in st.session_state.carrito)
            for idx, item in enumerate(st.session_state.carrito):
                ca, cb, cc = st.columns([2.5, 1, 0.5])
                ca.write(f"{item['Producto']} (x{item['Cantidad']:g})")
                cb.write(f"${item['Subtotal']:,.0f}")
                if cc.button("❌", key=f"del_{idx}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()

            st.divider()
            metodo = st.radio("Método de Pago:", ["Efectivo", "Transferencia", "Ambos"], horizontal=True)
            p_efe, p_tra, vuelto = 0.0, 0.0, 0.0
            
            if metodo == "Efectivo":
                p_efe = st.number_input("Paga con $:", min_value=0.0, step=100.0)
                vuelto = max(0.0, p_efe - total)
            elif metodo == "Transferencia": p_tra = total
            else:
                ce, ct = st.columns(2)
                p_efe = ce.number_input("Efectivo $:", min_value=0.0)
                p_tra = ct.number_input("Transf. $:", min_value=0.0)
                vuelto = max(0.0, (p_efe + p_tra) - total)

            st.markdown(f'<p class="total-grande">TOTAL: ${total:,.0f}</p>', unsafe_allow_html=True)
            if vuelto > 0 and metodo != "Transferencia":
                st.success(f"**VUELTO: ${vuelto:,.0f}**")

            if st.button("✅ FINALIZAR VENTA", use_container_width=True, type="primary"):
                if not st.session_state.get('caja_abierta', False):
                    st.error("⚠️ LA CAJA ESTÁ CERRADA. Ábrela en el menú.")
                else:
                    ahora = obtener_fecha_hora()
                    # Cargamos ventas diarias asegurando que sea una lista
                    ventas_raw = cargar_json("data/ventas_diarias.json")
                    ventas_diarias = ventas_raw if isinstance(ventas_raw, list) else []
                    
                    ventas_diarias.append({
                        "fecha": ahora.strftime("%Y-%m-%d"), "hora": ahora.strftime("%H:%M:%S"),
                        "vendedor": st.session_state.usuario_data['nombre'],
                        "turno": st.session_state.turno_actual,
                        "total": total, "metodo": metodo, "detalle": st.session_state.carrito
                    })
                    
                    with open("data/ventas_diarias.json", "w", encoding='utf-8') as f:
                        json.dump(ventas_diarias, f, indent=4)
                    
                    st.session_state.ticket_ready = generar_ticket_pdf(
                        st.session_state.carrito, total, 
                        st.session_state.usuario_data['nombre'], 
                        p_efe, p_tra, vuelto, metodo
                    )
                    st.success("Venta Exitosa")

            if "ticket_ready" in st.session_state and st.session_state.ticket_ready:
                st.download_button(
                    label="🖨️ DESCARGAR TICKET", 
                    data=st.session_state.ticket_ready, 
                    file_name=f"ticket_{datetime.datetime.now().strftime('%H%M%S')}.pdf", 
                    mime="application/pdf",
                    use_container_width=True
                )
                
                if st.button("🔄 NUEVA VENTA", use_container_width=True):
                    st.session_state.carrito = []
                    if "ticket_ready" in st.session_state: del st.session_state.ticket_ready
                    st.rerun()
        else:
            st.info("El carrito está vacío.")
