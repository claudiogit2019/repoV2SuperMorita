import streamlit as st
import json
import datetime
import pandas as pd
import os
from fpdf import FPDF
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
                return json.loads(content) if content else []
        return []
    except: return []

# --- FUNCIÓN PDF CORREGIDA PARA 0 KB ---
def generar_ticket_pdf(carrito, total, vendedor, paga_efe, paga_tra, vuelto, metodo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16) # Helvetica es más estándar
    pdf.cell(0, 10, "MORITA MINIMERCADO", ln=True, align="C")
    
    pdf.set_font("Helvetica", "", 10)
    ahora = obtener_fecha_hora()
    pdf.cell(0, 5, f"FECHA: {ahora.strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.cell(0, 5, f"CAJERO: {vendedor}", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 8, "Producto", border=1)
    pdf.cell(20, 8, "Cant.", border=1)
    pdf.cell(35, 8, "Subtotal", border=1, ln=True)
    
    pdf.set_font("Helvetica", "", 10)
    for item in carrito:
        c_v = f"{item['Cantidad']:g}"
        pdf.cell(100, 8, str(item['Producto']), border=1)
        pdf.cell(20, 8, str(c_v), border=1)
        pdf.cell(35, 8, f"${item['Subtotal']:,.0f}", border=1, ln=True)
    
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"TOTAL: ${total:,.0f}", ln=True, align="R")
    
    # IMPORTANTE: Generar los bytes y forzar el formato binario
    return bytes(pdf.output())

def mostrar_caja():
    st.markdown("""
        <style>
            div[data-testid="InputInstructions"] { display: none; }
            div[data-testid="stMetricValue"] { font-size: 25px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🛒 CAJA Y CONSULTAS")
    inv = cargar_json("data/inventario.json")
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    col_izq, col_der = st.columns([1.5, 1])

    with col_izq:
        st.subheader("🎙️ COMANDO DE VOZ")
        audio = mic_recorder(start_prompt="🎙️ HABLAR", stop_prompt="⏹️ PARAR", key='mic_v_final_morita')
        
        if audio:
            with st.spinner("IA Analizando..."):
                res = procesar_voz_completo(audio['bytes'], json.dumps(inv))
                if res: st.session_state.entendido = res

        if "entendido" in st.session_state:
            st.info(f"**ENTENDÍ:**\n{st.session_state.entendido}")
            c1, c2, _ = st.columns([1, 1, 2])
            with c1:
                if st.button("✅ AGREGAR", type="primary"):
                    for linea in st.session_state.entendido.split("\n"):
                        if "|" in linea:
                            try:
                                p = linea.split("|")
                                nom, cant, sub = p[0].strip(), float(p[1].strip()), float(p[2].strip().replace("$","").replace(",",""))
                                st.session_state.carrito.append({
                                    "Producto": nom, "Precio": sub/cant, "Cantidad": cant, "Subtotal": sub
                                })
                            except: continue
                    del st.session_state.entendido
                    st.rerun()
            with c2:
                if st.button("🗑️ LIMPIAR"):
                    del st.session_state.entendido
                    st.rerun()

        st.divider()
        st.subheader("🔍 BÚSQUEDA MANUAL")
        busq = st.text_input("Buscar:").upper()
        if len(busq) >= 2:
            coincidencias = [p for p in inv if busq in str(p['Producto']).upper()]
            for p in coincidencias:
                cx, cy, cz = st.columns([2, 1, 0.5])
                cx.write(f"**{p['Producto']}**")
                cant_m = cy.number_input("Cant.", min_value=0.1, value=1.0, key=f"m_{p['Producto']}", label_visibility="collapsed")
                if cz.button("➕", key=f"b_{p['Producto']}"):
                    st.session_state.carrito.append({
                        "Producto": p['Producto'], "Precio": p['Precio'], 
                        "Cantidad": cant_m, "Subtotal": p['Precio'] * cant_m
                    })
                    st.rerun()

    with col_der:
        st.subheader("📋 FACTURA")
        if st.session_state.carrito:
            total = sum(i['Subtotal'] for i in st.session_state.carrito)
            for idx, item in enumerate(st.session_state.carrito):
                c_f = f"{item['Cantidad']:g}"
                ca, cb, cc = st.columns([2, 1, 0.5])
                ca.write(f"{item['Producto']} (x{c_f})")
                cb.write(f"${item['Subtotal']:,.0f}")
                if cc.button("❌", key=f"d_{idx}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()

            st.divider()
            metodo = st.radio("Pago:", ["Efectivo", "Transferencia", "Ambos"], horizontal=True)
            p_efe, p_tra, vuelto = 0.0, 0.0, 0.0
            
            if metodo == "Efectivo":
                p_efe = st.number_input("Paga con ($):", min_value=0.0, step=100.0)
                vuelto = max(0.0, p_efe - total)
            elif metodo == "Transferencia":
                p_tra = total
            else:
                c1, c2 = st.columns(2); p_efe = c1.number_input("Efe:"); p_tra = c2.number_input("Transf:")
                vuelto = max(0.0, (p_efe + p_tra) - total)

            st.divider()
            st.markdown(f"### TOTAL: ${total:,.0f}")
            if metodo != "Transferencia":
                st.write(f"**Efectivo:** ${p_efe:,.0f}")
                if vuelto > 0: st.success(f"**Vuelto:** ${vuelto:,.0f}")
            if metodo == "Transferencia" or metodo == "Ambos":
                st.write(f"**Transferencia:** ${p_tra:,.0f}")

            # BOTÓN FINALIZAR
            if st.button("✅ FINALIZAR VENTA", use_container_width=True):
                ahora = obtener_fecha_hora()
                ventas = cargar_json("data/ventas_diarias.json")
                ventas.append({
                    "fecha": ahora.strftime("%Y-%m-%d"),
                    "mes": ahora.strftime("%Y-%m"),
                    "hora": ahora.strftime("%H:%M:%S"),
                    "vendedor": st.session_state.usuario_data['nombre'],
                    "total": total, "metodo": metodo,
                    "detalle": st.session_state.carrito
                })
                os.makedirs("data", exist_ok=True)
                with open("data/ventas_diarias.json", "w", encoding='utf-8') as f:
                    json.dump(ventas, f, indent=4)
                
                # Generamos los bytes del PDF y los guardamos en session_state
                st.session_state.ticket_ready = generar_ticket_pdf(st.session_state.carrito, total, st.session_state.usuario_data['nombre'], p_efe, p_tra, vuelto, metodo)
                st.success("Venta Registrada")

            # --- BOTONES DE ACCIÓN (TICKET Y NUEVA VENTA) ---
            if "ticket_ready" in st.session_state:
                st.download_button(
                    label="🖨️ DESCARGAR TICKET", 
                    data=st.session_state.ticket_ready, 
                    file_name=f"ticket_{datetime.datetime.now().strftime('%H%M%S')}.pdf", 
                    mime="application/pdf",
                    use_container_width=True
                )
                
                if st.button("🔄 NUEVA VENTA / LIMPIAR", use_container_width=True, type="secondary"):
                    st.session_state.carrito = []
                    if "ticket_ready" in st.session_state:
                        del st.session_state.ticket_ready
                    st.rerun()

    # --- HISTORIAL ADMIN ---
    if st.session_state.get('rol') == "admin":
        st.divider()
        st.subheader("📅 HISTORIAL Y CIERRE (ADMIN)")
        v_hist = cargar_json("data/ventas_diarias.json")
        if v_hist:
            df = pd.DataFrame(v_hist)
            if st.checkbox("Ver detalle productos"):
                items_cierre = []
                for v in v_hist:
                    for d in v['detalle']:
                        items_cierre.append({
                            "Fecha": v['fecha'], "Producto": d['Producto'],
                            "Cant": f"{d['Cantidad']:g}", "Subtotal": f"${d['Subtotal']:,.0f}"
                        })
                st.table(pd.DataFrame(items_cierre).tail(20))
            
            df_ver = df[['fecha', 'hora', 'vendedor', 'total', 'metodo']].copy()
            df_ver['total'] = df_ver['total'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(df_ver.tail(20), use_container_width=True)