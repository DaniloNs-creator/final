import streamlit as st
import sqlite3
from datetime import datetime

# --- CSS PROFISSIONAL ---
st.markdown("""
    <style>
        .main {background-color: #f0f2f6;}
        .title {color: #003366; font-size: 32px; font-weight: bold;}
        .header {color: #003366; font-size: 24px; font-weight: bold;}
        .form-label {font-weight: bold;}
        .button {background-color: #003366; color: white; font-weight: bold;}
        .checkbox-label {font-weight: bold;}
        .stButton>button {background-color: #003366; color: white; font-weight: bold;}
        .stTextInput>div>input {background-color: #f8f8f8;}
        .stDataFrame {background-color: #fff;}
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS ---
conn = sqlite3.connect('atividades.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS atividades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        razao_social TEXT,
        classificacao TEXT,
        tributacao TEXT,
        responsavel TEXT,
        atividade TEXT,
        grupo TEXT,
        cidade TEXT,
        desde TEXT,
        status TEXT,
        email TEXT,
        telefone TEXT,
        contato TEXT,
        possui_folha TEXT,
        financeiro TEXT,
        contas_bancarias INTEGER,
        forma_entrega TEXT,
        data_entrega TEXT,
        feito INTEGER
    )
''')
conn.commit()

# --- LOGIN ---
def login():
    st.markdown('<p class="title">Carteira de Clientes - Painel de Atividades</p>', unsafe_allow_html=True)
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if username == "admin" and password == "reali":
            st.session_state.logged_in = True
        else:
            st.error("Usuário ou senha incorretos")

# --- ADICIONAR ATIVIDADE ---
def adicionar_atividade(campos):
    c.execute('''
        INSERT INTO atividades (
            cliente, razao_social, classificacao, tributacao, responsavel, atividade, grupo, cidade, desde, status,
            email, telefone, contato, possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega, feito
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', campos)
    conn.commit()

# --- EXCLUIR ATIVIDADE ---
def excluir_atividade(id):
    c.execute('DELETE FROM atividades WHERE id = ?', (id,))
    conn.commit()

# --- MARCAR COMO FEITO ---
def marcar_feito(id, feito):
    c.execute('UPDATE atividades SET feito = ? WHERE id = ?', (feito, id))
    conn.commit()

# --- PAINEL PRINCIPAL ---
def painel():
    st.markdown('<p class="header">Cadastro de Atividades</p>', unsafe_allow_html=True)
    with st.form("nova_atividade"):
        cliente = st.text_input("Cliente")
        razao_social = st.text_input("Razão Social")
        classificacao = st.text_input("Classificação do Cliente")
        tributacao = st.text_input("Tributação")
        responsavel = st.text_input("Responsável")
        atividade = st.text_input("Atividade")
        grupo = st.text_input("Grupo")
        cidade = st.text_input("Cidade")
        desde = st.text_input("Desde")
        status = st.text_input("Status")
        email = st.text_input("E-mail")
        telefone = st.text_input("Telefone")
        contato = st.text_input("Contato")
        possui_folha = st.selectbox("Possui Folha?", ["Sim", "Não"])
        financeiro = st.text_input("Financeiro")
        contas_bancarias = st.number_input("Qtd. Contas Bancárias", min_value=0, step=1)
        forma_entrega = st.text_input("Forma de Entrega")
        data_entrega = st.date_input("Data de Entrega", value=datetime.today())
        enviado = st.form_submit_button("Adicionar Atividade")
        if enviado:
            campos = (
                cliente, razao_social, classificacao, tributacao, responsavel, atividade, grupo, cidade, desde, status,
                email, telefone, contato, possui_folha, financeiro, contas_bancarias, forma_entrega,
                data_entrega.strftime('%Y-%m-%d'), 0
            )
            adicionar_atividade(campos)
            st.success("Atividade adicionada com sucesso!")

    st.markdown('<p class="header">Lista de Atividades</p>', unsafe_allow_html=True)
    atividades = c.execute('SELECT * FROM atividades').fetchall()
    if atividades:
        cols = [
            "Cliente", "Razão Social", "Classificação", "Tributação", "Responsável", "Atividade", "Grupo", "Cidade",
            "Desde", "Status", "E-mail", "Telefone", "Contato", "Possui Folha", "Financeiro", "Contas Bancárias",
            "Forma Entrega", "Data Entrega", "Feito", "Ações"
        ]
        for row in atividades:
            id, cliente, razao_social, classificacao, tributacao, responsavel, atividade, grupo, cidade, desde, status, email, telefone, contato, possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega, feito = row
            col1, col2, col3, col4, col5, col6, col7, col8, col9, col10 = st.columns([2,2,2,2,2,2,2,2,2,2])
            col1.write(cliente)
            col2.write(razao_social)
            col3.write(classificacao)
            col4.write(tributacao)
            col5.write(responsavel)
            col6.write(atividade)
            col7.write(grupo)
            col8.write(cidade)
            col9.write(data_entrega)
            feito_checkbox = col10.checkbox("Feito", value=bool(feito), key=f"feito_{id}")
            if feito_checkbox != bool(feito):
                marcar_feito(id, int(feito_checkbox))
            if st.button("Excluir", key=f"del_{id}"):
                excluir_atividade(id)
                st.experimental_rerun()
    else:
        st.info("Nenhuma atividade cadastrada.")

# --- CONTROLE DE SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
else:
    painel()
