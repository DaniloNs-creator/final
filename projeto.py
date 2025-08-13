import streamlit as st
import sqlite3
from datetime import datetime

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Carteira de Clientes",
    page_icon="📊",
    layout="wide"
)

# --- CSS PROFISSIONAL ---
def load_css():
    st.markdown("""
        <style>
            .main {
                background-color: #f8f9fa;
            }
            .title {
                color: #2c3e50;
                font-size: 2.5rem;
                font-weight: bold;
                margin-bottom: 1rem;
            }
            .header {
                color: #2c3e50;
                font-size: 1.8rem;
                font-weight: 600;
                margin: 1rem 0;
            }
            .card {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 1rem;
                margin-bottom: 1rem;
            }
            .stButton>button {
                background-color: #2c3e50;
                color: white;
                font-weight: bold;
            }
        </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('atividades.db', check_same_thread=False)
    c = conn.cursor()
    
    # Criação da tabela com todas as colunas necessárias
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
            feito INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    return conn

# --- FUNÇÕES DO SISTEMA ---
def adicionar_atividade(conn, campos):
    c = conn.cursor()
    c.execute('''
        INSERT INTO atividades (
            cliente, razao_social, classificacao, tributacao, responsavel, atividade, 
            grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
            financeiro, contas_bancarias, forma_entrega, data_entrega
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', campos)
    conn.commit()

def excluir_atividade(conn, id):
    c = conn.cursor()
    c.execute('DELETE FROM atividades WHERE id = ?', (id,))
    conn.commit()

def marcar_feito(conn, id, feito):
    c = conn.cursor()
    c.execute('UPDATE atividades SET feito = ? WHERE id = ?', (feito, id))
    conn.commit()

def get_atividades(conn):
    c = conn.cursor()
    c.execute('SELECT * FROM atividades ORDER BY id DESC')
    return c.fetchall()

# --- COMPONENTES DA INTERFACE ---
def login_section():
    st.markdown('<div class="title">Carteira de Clientes</div>', unsafe_allow_html=True)
    
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        if username == "admin" and password == "reali":
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Credenciais inválidas")

def cadastro_atividade(conn):
    st.markdown('<div class="header">Cadastro de Atividades</div>', unsafe_allow_html=True)
    
    with st.form("nova_atividade"):
        col1, col2 = st.columns(2)
        
        with col1:
            cliente = st.text_input("Cliente*")
            razao_social = st.text_input("Razão Social")
            classificacao = st.selectbox("Classificação", ["A", "B", "C", "D"])
            tributacao = st.selectbox("Tributação", ["Simples", "Presumido", "Real"])
            responsavel = st.text_input("Responsável*")
            atividade = st.text_input("Atividade*")
            
        with col2:
            grupo = st.text_input("Grupo")
            cidade = st.text_input("Cidade")
            desde = st.date_input("Cliente desde")
            status = st.selectbox("Status", ["Ativo", "Inativo"])
            email = st.text_input("E-mail")
            telefone = st.text_input("Telefone")
            
        contato = st.text_input("Contato")
        possui_folha = st.selectbox("Possui Folha?", ["Sim", "Não"])
        financeiro = st.text_input("Financeiro")
        contas_bancarias = st.number_input("Contas Bancárias", min_value=0, value=1)
        forma_entrega = st.selectbox("Forma de Entrega", ["Email", "Correio"])
        data_entrega = st.date_input("Data de Entrega")
        
        if st.form_submit_button("Salvar"):
            if cliente and responsavel and atividade:
                campos = (
                    cliente, razao_social, classificacao, tributacao, responsavel, atividade,
                    grupo, cidade, desde.strftime('%Y-%m-%d'), status, email, telefone, contato,
                    possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega.strftime('%Y-%m-%d')
                )
                adicionar_atividade(conn, campos)
                st.success("Atividade cadastrada!")
            else:
                st.error("Preencha os campos obrigatórios")

def lista_atividades(conn):
    st.markdown('<div class="header">Lista de Atividades</div>', unsafe_allow_html=True)
    
    atividades = get_atividades(conn)
    
    if not atividades:
        st.info("Nenhuma atividade cadastrada")
        return
    
    for row in atividades:
        with st.container():
            # Acesso seguro aos dados por índice
            id = row[0]
            cliente = row[1]
            atividade = row[6]
            status = row[10]
            feito = row[19]
            
            with st.expander(f"{cliente} - {atividade}"):
                col1, col2 = st.columns([3,1])
                
                with col1:
                    st.write(f"Responsável: {row[5]}")
                    st.write(f"Razão Social: {row[2]}")
                    st.write(f"Status: {status}")
                    st.write(f"Data Entrega: {row[18]}")
                
                with col2:
                    novo_feito = st.checkbox("Concluído", value=bool(feito), key=f"feito_{id}")
                    if novo_feito != feito:
                        marcar_feito(conn, id, int(novo_feito))
                    
                    if st.button("Excluir", key=f"del_{id}"):
                        excluir_atividade(conn, id)
                        st.experimental_rerun()

# --- APLICAÇÃO PRINCIPAL ---
def main():
    load_css()
    conn = init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_section()
    else:
        st.sidebar.title("Menu")
        opcao = st.sidebar.radio("Opções", ["Cadastrar", "Listar"])
        
        if st.sidebar.button("Sair"):
            st.session_state.logged_in = False
            st.experimental_rerun()
        
        if opcao == "Cadastrar":
            cadastro_atividade(conn)
        else:
            lista_atividades(conn)
    
    conn.close()

if __name__ == "__main__":
    main()
