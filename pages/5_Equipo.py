import streamlit as st

st.title("Equipo del Proyecto")
st.divider()

col1, col2 = st.columns(2)
with col1:
    st.image("assets/carolina.png", width=200)
    st.subheader("Carolina Bechara")
    st.markdown("Comerciante Internacional Área Comercial")

with col2:
    st.image("assets/santiago.png", width=200)
    st.subheader("Santiago Cano")
    st.markdown("Comerciante Internacional — Área Comercial")