import streamlit as st
import json

def cargar_usuarios():
    try:
        with open("data/usuarios.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except: return []

def guardar_usuarios(datos):
    with open("data/usuarios.json", "w", encoding='utf-8') as f:
        json.dump(datos, f, indent=4)

def mostrar_gestion_usuarios():
    st.title("👤 GESTIÓN DE VENDEDORES")
    usuarios = cargar_usuarios()
    
    with st.form("nuevo_usuario"):
        st.subheader("Registrar Nuevo Vendedor")
        nombre = st.text_input("Nombre Completo")
        user = st.text_input("Nombre de Usuario (ID)")
        clave = st.text_input("Password", type="password")
        rol = st.selectbox("Perfil", ["vendedor", "admin"])
        if st.form_submit_button("AÑADIR USUARIO"):
            usuarios.append({"usuario": user, "clave": clave, "rol": rol, "nombre": nombre, "activo": True})
            guardar_usuarios(usuarios)
            st.success(f"Usuario {nombre} creado con éxito")
            st.rerun()

    st.subheader("Lista de Personal")
    for i, u in enumerate(usuarios):
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.write(f"**{u['nombre']}** ({u['rol']})")
        if c3.button("Eliminar", key=f"del_u_{i}"):
            usuarios.pop(i)
            guardar_usuarios(usuarios)
            st.rerun()
