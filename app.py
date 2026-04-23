import streamlit as st
from src.database import get_equipos

st.set_page_config(page_title="Gestor Torneo RFFM", layout="wide")

st.title("🏆 Gestión de Campeonato RFFM")

# Sidebar para navegación
menu = st.sidebar.selectbox("Menú", ["Dashboard", "Configurador", "Carga de Equipos", "Cuadro Visual"])

if menu == "Dashboard":
    st.write(f"Bienvenido David. Tienes {len(get_equipos())} equipos cargados.")
    # Aquí irá un resumen de la fase actual
