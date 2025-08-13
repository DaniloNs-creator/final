import streamlit as st
import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional

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
            :root {
                --primary-color: #2c3e50;
                --secondary-color: #3498db;
                --background-color: #f8f9fa;
                --text-color: #333333;
                --success-color: #27ae60;
                --error-color: #e74c3c;
                --warning-color: #f39c12;
            }
            
            .main {
                background-color: var(--background-color);
                color: var(--text-color);
            }
            
            .title {
                color: var(--primary-color);
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 1.5rem;
                border-bottom: 2px solid var(--secondary-color);
                padding-bottom: 0.5rem;
            }
            
            .header {
                color: var(--primary-color);
                font-size: 1.8rem;
                font-weight: 600;
                margin: 1.5rem 0 1rem 0;
            }
            
            .card {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 1.5rem;
                margin-bottom: 1.5rem;
            }
            
            .form-label {
                font-weight: 600;
                margin-bottom: 0.5rem;
                color: var(--primary-color);
            }
            
            .stButton>button {
                background-color: var(--primary-color);
                color: white;
                font-weight: 600;
                border: none;
                border-radius: 4px;
                padding: 0.5rem 1rem;
                transition: all 0.3s;
            }
            
            .stButton>button:hover {
                background-color: var(--secondary-color);
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            
            .stTextInput>div>div>input, 
            .stSelectbox>div>div>select,
            .stDateInput>div>div>input {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 0.5rem 0.75rem;
            }
            
            .success-message {
                color: var(--success-color);
                font-weight: 600;
            }
            
            .error-message {
                color: var(--error-color);
                font-weight: 600;
            }
            
            .info-message {
                color: var(--secondary-color);
                font-weight: 600;
            }
            
            .dataframe {
                width: 100%;
                border-collapse: collapse;
            }
            
            .dataframe th {
                background-color: var(--primary-color);
                color: white;
                font-weight: 600;
                padding: 0.75rem;
                text-align: left;
            }
            
            .dataframe td {
                padding: 0.75rem;
                border-bottom: 1px solid #ddd;
            }
            
            .dataframe tr:nth-child(even) {
                background-color: #f2f2f2;
            }
            
            .dataframe tr:hover {
                background-color: #e9e9e9;
            }
        </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db() -> sqlite3.Connection:
    """Inicializa e retorna a conexão com o banco de dados, criando a tabela se necessário."""
    conn = sqlite3.connect('clientes.db', check_same_thread=False)
    c = conn.cursor()
    
    # Criação da tabela com todas as colunas necessárias
    c.execute('''
        CREATE TABLE IF NOT EXISTS atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            razao_social TEXT,
            classificacao TEXT,
            tributacao TEXT,
            responsavel TEXT NOT NULL,
            atividade TEXT NOT NULL,
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
            feito INTEGER DEFAULT 0,
            data_criacao TEXT NOT NULL
        )
    ''')
    conn.commit()
    return conn

# --- FUNÇÕES DO SISTEMA ---
def adicionar_atividade(conn: sqlite3.Connection, campos: Tuple) -> bool:
    """Adiciona uma nova atividade ao banco de dados."""
    try:
        c = conn.cursor()
        campos_completos = campos + (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),)
        c.execute('''
            INSERT INTO atividades (
                cliente, razao_social, classificacao, tributacao, responsavel, atividade, 
                grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                financeiro, contas_bancarias, forma_entrega, data_entrega, data_criacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', campos_completos)
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao adicionar atividade: {e}")
        return False

def excluir_atividade(conn: sqlite3.Connection, id: int) -> bool:
    """Remove uma atividade do banco de dados pelo ID."""
    try:
        c = conn.cursor()
        c.execute('DELETE FROM atividades WHERE id = ?', (id,))
        conn.commit()
        return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao excluir atividade: {e}")
        return False

def marcar_feito(conn: sqlite3.Connection, id: int, feito: bool) -> bool:
    """Atualiza o status de conclusão de uma atividade."""
    try:
        c = conn.cursor()
        c.execute('UPDATE atividades SET feito = ? WHERE id = ?', (int(feito), id))
        conn.commit()
        return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False

def get_atividades(conn: sqlite3.Connection) -> List[Tuple]:
    """Retorna todas as atividades ordenadas por data de criação."""
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM atividades ORDER BY data_criacao DESC')
        return c.fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar atividades: {e}")
        return []

# --- COMPONENTES DA INTERFACE ---
def login_section():
    """Exibe a seção de login."""
    st.markdown('<div class="title">Carteira de Clientes - Painel de Atividades</div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        col1, col2 = st.columns(2)
        username = col1.text_input("Usuário", key="username")
        password = col2.text_input("Senha", type="password", key="password")
        
        if st.form_submit_button("Entrar", use_container_width=True):
            if username == "admin" and password == "reali":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciais inválidas. Tente novamente.", icon="⚠️")

def cadastro_atividade(conn: sqlite3.Connection):
    """Exibe o formulário para cadastro de novas atividades."""
    st.markdown('<div class="header">📝 Cadastro de Atividades</div>', unsafe_allow_html=True)
    
    with st.form("nova_atividade", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="form-label">Informações Básicas</div>', unsafe_allow_html=True)
            cliente = st.text_input("Cliente*", placeholder="Nome do cliente")
            razao_social = st.text_input("Razão Social", placeholder="Razão social completa")
            classificacao = st.selectbox("Classificação", ["A", "B", "C", "D"])
            tributacao = st.selectbox("Tributação", ["Simples Nacional", "Lucro Presumido", "Lucro Real"])
            responsavel = st.text_input("Responsável*", placeholder="Nome do responsável")
            atividade = st.text_input("Atividade*", placeholder="Descrição da atividade")
            
        with col2:
            st.markdown('<div class="form-label">Informações Adicionais</div>', unsafe_allow_html=True)
            grupo = st.text_input("Grupo", placeholder="Grupo do cliente")
            cidade = st.text_input("Cidade", placeholder="Cidade do cliente")
            desde = st.date_input("Cliente desde", value=datetime.now())
            status = st.selectbox("Status", ["Ativo", "Inativo", "Potencial", "Perdido"])
            email = st.text_input("E-mail", placeholder="E-mail de contato")
            telefone = st.text_input("Telefone", placeholder="Telefone de contato")
            
        st.markdown('<div class="form-label">Detalhes Financeiros</div>', unsafe_allow_html=True)
        col3, col4, col5 = st.columns(3)
        
        with col3:
            contato = st.text_input("Contato Financeiro", placeholder="Nome do contato")
            possui_folha = st.selectbox("Possui Folha?", ["Sim", "Não", "Não se aplica"])
            
        with col4:
            financeiro = st.text_input("Financeiro", placeholder="Informações financeiras")
            contas_bancarias = st.number_input("Contas Bancárias", min_value=0, value=1)
            
        with col5:
            forma_entrega = st.selectbox("Forma de Entrega", ["E-mail", "Correio", "Pessoalmente", "Outros"])
            data_entrega = st.date_input("Data de Entrega", value=datetime.now())
        
        st.markdown("<small>Campos marcados com * são obrigatórios</small>", unsafe_allow_html=True)
        
        if st.form_submit_button("Adicionar Atividade", use_container_width=True):
            if cliente and responsavel and atividade:
                campos = (
                    cliente, razao_social, classificacao, tributacao, responsavel, atividade,
                    grupo, cidade, desde.strftime('%Y-%m-%d'), status, email, telefone, contato,
                    possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega.strftime('%Y-%m-%d')
                )
                if adicionar_atividade(conn, campos):
                    st.success("Atividade cadastrada com sucesso!", icon="✅")
            else:
                st.error("Preencha os campos obrigatórios!", icon="❌")

def lista_atividades(conn: sqlite3.Connection):
    """Exibe a lista de atividades cadastradas."""
    st.markdown('<div class="header">📋 Lista de Atividades</div>', unsafe_allow_html=True)
    
    atividades = get_atividades(conn)
    
    if not atividades:
        st.info("Nenhuma atividade cadastrada ainda.", icon="ℹ️")
        return
    
    for row in atividades:
        with st.container():
            # Verificação segura dos dados
            try:
                (id, cliente, razao_social, classificacao, tributacao, responsavel, 
                 atividade, grupo, cidade, desde, status, email, telefone, contato, 
                 possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega, 
                 feito, data_criacao) = row
            except ValueError as e:
                st.error(f"Erro ao processar atividade: {e}")
                continue
            
            # Cartão de atividade
            with st.expander(f"📌 {cliente} - {atividade} ({status})"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Responsável:** {responsavel}")
                    st.markdown(f"**Razão Social:** {razao_social}")
                    st.markdown(f"**Classificação/Tributação:** {classificacao} / {tributacao}")
                    st.markdown(f"**Grupo/Cidade:** {grupo} / {cidade}")
                    st.markdown(f"**Contato:** {contato} ({telefone} - {email})")
                    st.markdown(f"**Financeiro:** {financeiro} | Folha: {possui_folha} | Contas: {contas_bancarias}")
                    st.markdown(f"**Entrega:** {forma_entrega} em {data_entrega}")
                    st.markdown(f"**Data de Criação:** {data_criacao}")
                    
                with col2:
                    # Checkbox para marcar como concluído
                    st.checkbox(
                        "Marcar como concluído", 
                        value=bool(feito),
                        key=f"feito_{id}",
                        on_change=marcar_feito,
                        args=(conn, id, not feito)
                    )
                    
                    # Botão para excluir
                    if st.button("Excluir", key=f"del_{id}", use_container_width=True):
                        if excluir_atividade(conn, id):
                            st.rerun()

# --- APLICAÇÃO PRINCIPAL ---
def main():
    """Função principal que gerencia o fluxo da aplicação."""
    load_css()
    conn = init_db()
    
    # Verifica estado de login
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_section()
    else:
        # Menu principal
        st.sidebar.title("Menu")
        menu_option = st.sidebar.radio(
            "Selecione uma opção",
            ["Cadastrar Atividade", "Visualizar Atividades"],
            index=1
        )
        
        st.sidebar.markdown("---")
        if st.sidebar.button("Sair", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        
        # Navegação entre páginas
        if menu_option == "Cadastrar Atividade":
            cadastro_atividade(conn)
        else:
            lista_atividades(conn)

if __name__ == "__main__":
    main()
