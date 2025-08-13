import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Painel de Entregas de Atividades", layout="wide")

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('atividades.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            atividade TEXT,
            responsavel TEXT,
            data_entrega DATE,
            status TEXT,
            feito INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

# --- FUNÇÕES AUXILIARES ---
def inserir_atividade(cliente, atividade, responsavel, data_entrega, status):
    conn.execute(
        'INSERT INTO atividades (cliente, atividade, responsavel, data_entrega, status, feito) VALUES (?, ?, ?, ?, ?, ?)',
        (cliente, atividade, responsavel, data_entrega, status, 0)
    )
    conn.commit()

def excluir_atividade(id):
    conn.execute('DELETE FROM atividades WHERE id=?', (id,))
    conn.commit()

def atualizar_feito(id, feito):
    conn.execute('UPDATE atividades SET feito=? WHERE id=?', (feito, id))
    conn.commit()

def atualizar_data_entrega(id, data_entrega):
    conn.execute('UPDATE atividades SET data_entrega=? WHERE id=?', (data_entrega, id))
    conn.commit()

def get_atividades():
    df = pd.read_sql_query('SELECT * FROM atividades', conn)
    return df

# --- LAYOUT DO PAINEL ---
st.title("Painel de Entregas de Atividades")

with st.expander("Adicionar nova atividade"):
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        cliente = st.text_input("Cliente")
    with col2:
        atividade = st.text_input("Atividade")
    with col3:
        responsavel = st.text_input("Responsável")
    with col4:
        data_entrega = st.date_input("Data de Entrega", value=date.today())
    with col5:
        status = st.selectbox("Status", ["Pendente", "Em andamento", "Concluído"])
    if st.button("Incluir Atividade"):
        if cliente and atividade and responsavel:
            inserir_atividade(cliente, atividade, responsavel, data_entrega.strftime("%Y-%m-%d"), status)
            st.success("Atividade incluída com sucesso!")
        else:
            st.warning("Preencha todos os campos obrigatórios.")

st.markdown("---")

# --- TABELA DE ATIVIDADES ---
df = get_atividades()
if df.empty:
    st.info("Nenhuma atividade cadastrada.")
else:
    st.subheader("Lista de Atividades")
    df['feito'] = df['feito'].astype(bool)
    df['data_entrega'] = pd.to_datetime(df['data_entrega']).dt.strftime('%d/%m/%Y')

    # Layout igual ao Excel: colunas principais
    cols = st.columns([2, 3, 2, 2, 2, 1, 1])
    with cols[0]:
        st.markdown("**Cliente**")
    with cols[1]:
        st.markdown("**Atividade**")
    with cols[2]:
        st.markdown("**Responsável**")
    with cols[3]:
        st.markdown("**Data de Entrega**")
    with cols[4]:
        st.markdown("**Status**")
    with cols[5]:
        st.markdown("**Feito**")
    with cols[6]:
        st.markdown("**Excluir**")

    for idx, row in df.iterrows():
        cols = st.columns([2, 3, 2, 2, 2, 1, 1])
        with cols[0]:
            st.write(row['cliente'])
        with cols[1]:
            st.write(row['atividade'])
        with cols[2]:
            st.write(row['responsavel'])
        with cols[3]:
            nova_data = st.date_input(
                f"Data {row['id']}", 
                value=pd.to_datetime(row['data_entrega'], dayfirst=True), 
                key=f"data_{row['id']}"
            )
            if nova_data.strftime('%d/%m/%Y') != row['data_entrega']:
                atualizar_data_entrega(row['id'], nova_data.strftime('%Y-%m-%d'))
        with cols[4]:
            st.write(row['status'])
        with cols[5]:
            checked = st.checkbox("", value=row['feito'], key=f"feito_{row['id']}")
            if checked != row['feito']:
                atualizar_feito(row['id'], int(checked))
        with cols[6]:
            if st.button("Excluir", key=f"excluir_{row['id']}"):
                excluir_atividade(row['id'])
                st.experimental_rerun()

    st.markdown("---")
    st.write(f"Total de atividades: {len(df)}")
    st.write(f"Atividades concluídas: {df['feito'].sum()}")

st.caption("Desenvolvido para reproduzir o painel da planilha 'Carteira de Clientes.xlsm' em Streamlit + SQLite.")
