import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import random
from typing import List, Tuple, Optional
import io

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Carteira de Clientes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PROFISSIONAL ANIMADO ---
def load_css():
    st.markdown("""
        <style>
            :root {
                --primary-color: #3498db;
                --secondary-color: #2ecc71;
                --dark-color: #2c3e50;
                --light-color: #ecf0f1;
                --accent-color: #e74c3c;
                --background-gradient: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                --card-shadow: 0 10px 20px rgba(0,0,0,0.1), 0 6px 6px rgba(0,0,0,0.05);
                --transition: all 0.3s cubic-bezier(.25,.8,.25,1);
            }
            
            .main {
                background: var(--background-gradient);
                color: var(--dark-color);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            .title {
                color: var(--dark-color);
                font-size: 2.8rem;
                font-weight: 800;
                margin-bottom: 1.5rem;
                padding-bottom: 0.5rem;
                background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                animation: fadeIn 1s ease-in-out;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .header {
                color: var(--dark-color);
                font-size: 1.8rem;
                font-weight: 700;
                margin: 1.5rem 0 1rem 0;
                padding-left: 10px;
                border-left: 5px solid var(--primary-color);
                animation: slideIn 0.5s ease-out;
            }
            
            @keyframes slideIn {
                from { transform: translateX(-20px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            
            .card {
                background: white;
                border-radius: 12px;
                box-shadow: var(--card-shadow);
                padding: 1.8rem;
                margin-bottom: 1.8rem;
                transition: var(--transition);
                border: none;
                animation: popIn 0.4s ease-out;
            }
            
            @keyframes popIn {
                0% { transform: scale(0.95); opacity: 0; }
                100% { transform: scale(1); opacity: 1; }
            }
            
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 30px rgba(0,0,0,0.15);
            }
            
            .completed {
                background-color: rgba(46, 204, 113, 0.1);
                border-left: 5px solid var(--secondary-color);
                position: relative;
                overflow: hidden;
            }
            
            .completed::after {
                content: "✓ CONCLUÍDO";
                position: absolute;
                top: 10px;
                right: -30px;
                background: var(--secondary-color);
                color: white;
                padding: 3px 30px;
                font-size: 0.7rem;
                font-weight: bold;
                transform: rotate(45deg);
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            }
            
            /* Sidebar styling */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, var(--dark-color), #34495e) !important;
                color: white !important;
                padding: 1.5rem !important;
            }
            
            /* Estilo para as métricas na sidebar */
            .sidebar-metric {
                color: white !important;
            }
            
            .sidebar-metric-label {
                color: white !important;
                font-size: 1rem !important;
                margin-bottom: 0.5rem !important;
            }
            
            .sidebar-metric-value {
                color: white !important;
                font-size: 1.5rem !important;
                font-weight: bold !important;
            }
            
            /* Estilo específico para as próximas entregas */
            .proxima-entrega {
                background: white;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                color: black !important;
            }
            
            .proxima-entrega strong, 
            .proxima-entrega small {
                color: black !important;
            }
            
            /* Restante do CSS permanece igual */
            .form-label {
                font-weight: 600;
                margin-bottom: 0.5rem;
                color: var(--dark-color);
                display: block;
                position: relative;
                padding-left: 15px;
            }
            
            .form-label::before {
                content: "";
                position: absolute;
                left: 0;
                top: 50%;
                transform: translateY(-50%);
                width: 8px;
                height: 8px;
                background: var(--primary-color);
                border-radius: 50%;
            }
            
            .stButton>button {
                background: linear-gradient(135deg, var(--primary-color), #2980b9);
                color: white;
                font-weight: 600;
                border: none;
                border-radius: 8px;
                padding: 0.7rem 1.5rem;
                transition: var(--transition);
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                width: 100%;
            }
            
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 7px 14px rgba(0,0,0,0.15);
                background: linear-gradient(135deg, #2980b9, var(--primary-color));
            }
            
            .stButton>button:active {
                transform: translateY(0);
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .stTextInput>div>div>input, 
            .stSelectbox>div>div>select,
            .stDateInput>div>div>input,
            .stNumberInput>div>div>input {
                background-color: white;
                border: 2px solid #dfe6e9;
                border-radius: 8px;
                padding: 0.7rem 1rem;
                transition: var(--transition);
            }
            
            .stTextInput>div>div>input:focus, 
            .stSelectbox>div>div>select:focus,
            .stDateInput>div>div>input:focus {
                border-color: var(--primary-color);
                box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
                outline: none;
            }
            
            .stCheckbox>div>label {
                font-weight: 500;
                color: var(--dark-color);
            }
            
            .stCheckbox>div>div>svg {
                color: var(--secondary-color) !important;
            }
            
            .success-message {
                background-color: rgba(46, 204, 113, 0.2);
                color: var(--dark-color);
                padding: 1rem;
                border-radius: 8px;
                border-left: 5px solid var(--secondary-color);
                margin: 1rem 0;
                animation: fadeIn 0.5s ease-in;
            }
            
            .error-message {
                background-color: rgba(231, 76, 60, 0.2);
                color: var(--dark-color);
                padding: 1rem;
                border-radius: 8px;
                border-left: 5px solid var(--accent-color);
                margin: 1rem 0;
                animation: shake 0.5s ease-in;
            }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                20%, 60% { transform: translateX(-5px); }
                40%, 80% { transform: translateX(5px); }
            }
            
            .info-message {
                background-color: rgba(52, 152, 219, 0.2);
                color: var(--dark-color);
                padding: 1rem;
                border-radius: 8px;
                border-left: 5px solid var(--primary-color);
                margin: 1rem 0;
                animation: fadeIn 0.5s ease-in;
            }
            
            .stTabs [data-baseweb="tab-list"] {
                gap: 10px;
            }
            
            .stTabs [data-baseweb="tab"] {
                padding: 0.5rem 1.5rem;
                border-radius: 8px !important;
                background-color: white !important;
                transition: var(--transition);
                border: 1px solid #dfe6e9 !important;
                font-weight: 600;
            }
            
            .stTabs [aria-selected="true"] {
                background: linear-gradient(135deg, var(--primary-color), #2980b9) !important;
                color: white !important;
                border: none !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .stTabs [aria-selected="true"] [data-testid="stMarkdownContainer"] p {
                color: white !important;
            }
            
            .stExpander [data-testid="stExpander"] {
                border: none !important;
                box-shadow: var(--card-shadow);
                border-radius: 12px !important;
                margin-bottom: 1rem;
                transition: var(--transition);
            }
            
            .stExpander [data-testid="stExpander"]:hover {
                box-shadow: 0 15px 30px rgba(0,0,0,0.15);
            }
            
            .stExpander [data-testid="stExpanderDetails"] {
                padding: 1.5rem !important;
            }
            
            .stDataFrame {
                border-radius: 12px !important;
                box-shadow: var(--card-shadow) !important;
            }
            
            /* Efeito de onda nos botões */
            .ripple {
                position: relative;
                overflow: hidden;
            }
            
            .ripple:after {
                content: "";
                display: block;
                position: absolute;
                width: 100%;
                height: 100%;
                top: 0;
                left: 0;
                pointer-events: none;
                background-image: radial-gradient(circle, #fff 10%, transparent 10.01%);
                background-repeat: no-repeat;
                background-position: 50%;
                transform: scale(10, 10);
                opacity: 0;
                transition: transform .5s, opacity 1s;
            }
            
            .ripple:active:after {
                transform: scale(0, 0);
                opacity: 0.3;
                transition: 0s;
            }
            
            [data-testid="stSidebar"] .stButton>button {
                background: linear-gradient(135deg, var(--secondary-color), #27ae60) !important;
            }
            
            [data-testid="stSidebar"] .stButton>button:hover {
                background: linear-gradient(135deg, #27ae60, var(--secondary-color)) !important;
            }
            
            /* Custom scrollbar */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            
            ::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 10px;
            }
            
            ::-webkit-scrollbar-thumb {
                background: var(--primary-color);
                border-radius: 10px;
            }
            
            ::-webkit-scrollbar-thumb:hover {
                background: #2980b9;
            }
            
            /* Pulse animation for important elements */
            @keyframes pulse {
                0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(52, 152, 219, 0.7); }
                70% { transform: scale(1.02); box-shadow: 0 0 0 10px rgba(52, 152, 219, 0); }
                100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(52, 152, 219, 0); }
            }
            
            .pulse {
                animation: pulse 2s infinite;
            }
            
            /* Responsive adjustments */
            @media (max-width: 768px) {
                .title {
                    font-size: 2rem;
                }
                
                .header {
                    font-size: 1.5rem;
                }
            }
        </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db() -> sqlite3.Connection:
    """Inicializa e retorna a conexão com o banco de dados, criando a tabela se necessário."""
    conn = sqlite3.connect('clientes.db', check_same_thread=False)
    c = conn.cursor()
    
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
            data_criacao TEXT NOT NULL,
            mes_referencia TEXT
        )
    ''')
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM atividades")
    if c.fetchone()[0] == 0:
        gerar_atividades_mensais(conn)
    
    return conn

def gerar_atividades_mensais(conn: sqlite3.Connection):
    """Gera atividades mensais para todos os clientes até dezembro de 2025."""
    clientes = [
        ("Cliente A", "Razão Social A", "B", "Simples Nacional", "Responsável 1"),
        ("Cliente B", "Razão Social B", "A", "Lucro Presumido", "Responsável 2"),
        ("Cliente C", "Razão Social C", "C", "Lucro Real", "Responsável 1"),
        ("Cliente D", "Razão Social D", "B", "Simples Nacional", "Responsável 3"),
    ]
    
    atividades = [
        "Fechamento mensal",
        "Relatório contábil",
        "Conciliação bancária",
        "Declarações fiscais"
    ]
    
    hoje = datetime.now()
    fim = datetime(2025, 12, 1)
    
    c = conn.cursor()
    
    while hoje <= fim:
        mes_ref = hoje.strftime("%m/%Y")
        for cliente in clientes:
            atividade = random.choice(atividades)
            feito = random.choice([0, 1])
            campos = (
                cliente[0], cliente[1], cliente[2], cliente[3], cliente[4], atividade,
                "Grupo 1", "São Paulo", "01/2020", "Ativo", "email@cliente.com", "(11) 99999-9999", "Contato Financeiro",
                "Sim", "Em dia", 2, "E-mail", hoje.strftime('%Y-%m-%d'), feito, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), mes_ref
            )
            
            c.execute('''
                INSERT INTO atividades (
                    cliente, razao_social, classificacao, tributacao, responsavel, atividade, 
                    grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                    financeiro, contas_bancarias, forma_entrega, data_entrega, feito, data_criacao, mes_referencia
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', campos)
        
        hoje += timedelta(days=30)
    
    conn.commit()

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
                financeiro, contas_bancarias, forma_entrega, data_entrega, mes_referencia, data_criacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', campos_completos)
        conn.commit()
        st.session_state.atualizar_lista = True  # Flag para atualizar a lista
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao adicionar atividade: {e}")
        return False

def adicionar_atividades_em_lote(conn: sqlite3.Connection, dados: List[Tuple]) -> bool:
    """Adiciona múltiplas atividades ao banco de dados em lote."""
    try:
        c = conn.cursor()
        
        # Preparar os dados com data de criação
        dados_completos = [
            (*linha, datetime.now().strftime('%Y-%m-%d %H:%M:%S')) 
            for linha in dados
        ]
        
        c.executemany('''
            INSERT INTO atividades (
                cliente, razao_social, classificacao, tributacao, responsavel, atividade, 
                grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                financeiro, contas_bancarias, forma_entrega, data_entrega, mes_referencia, data_criacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', dados_completos)
        
        conn.commit()
        st.session_state.atualizar_lista = True  # Flag para atualizar a lista
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao adicionar atividades em lote: {e}")
        return False

def excluir_atividade(conn: sqlite3.Connection, id: int) -> bool:
    """Remove uma atividade do banco de dados pelo ID."""
    try:
        c = conn.cursor()
        c.execute('DELETE FROM atividades WHERE id = ?', (id,))
        conn.commit()
        st.session_state.atualizar_lista = True  # Flag para atualizar a lista
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
        st.session_state.atualizar_lista = True  # Flag para atualizar a lista
        return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False

def get_atividades(conn: sqlite3.Connection, filtro_mes: str = None, filtro_responsavel: str = None) -> List[Tuple]:
    """Retorna todas as atividades ordenadas por data de criação com filtros opcionais."""
    try:
        c = conn.cursor()
        query = 'SELECT * FROM atividades'
        params = []
        
        conditions = []
        if filtro_mes and filtro_mes != "Todos":
            conditions.append('mes_referencia = ?')
            params.append(filtro_mes)
        if filtro_responsavel and filtro_responsavel != "Todos":
            conditions.append('responsavel = ?')
            params.append(filtro_responsavel)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        query += ' ORDER BY data_criacao DESC'
        
        c.execute(query, tuple(params))
        return c.fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar atividades: {e}")
        return []

def get_responsaveis(conn: sqlite3.Connection) -> List[str]:
    """Retorna a lista de responsáveis únicos."""
    try:
        c = conn.cursor()
        c.execute('SELECT DISTINCT responsavel FROM atividades ORDER BY responsavel')
        return ["Todos"] + [row[0] for row in c.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar responsáveis: {e}")
        return ["Todos"]

def get_dados_indicadores(conn: sqlite3.Connection) -> pd.DataFrame:
    """Retorna dados para os indicadores de entrega."""
    try:
        query = '''
            SELECT 
                mes_referencia,
                SUM(feito) as concluidas,
                COUNT(*) as total,
                (SUM(feito) * 100.0 / COUNT(*)) as percentual
            FROM atividades
            GROUP BY mes_referencia
            ORDER BY SUBSTR(mes_referencia, 4) || SUBSTR(mes_referencia, 1, 2)
        '''
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erro ao gerar indicadores: {e}")
        return pd.DataFrame()

def get_dados_responsaveis(conn: sqlite3.Connection) -> pd.DataFrame:
    """Retorna dados para análise por responsável."""
    try:
        query = '''
            SELECT 
                responsavel,
                SUM(feito) as concluidas,
                COUNT(*) as total,
                (SUM(feito) * 100.0 / COUNT(*)) as percentual
            FROM atividades
            GROUP BY responsavel
            ORDER BY percentual DESC
        '''
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erro ao gerar dados por responsável: {e}")
        return pd.DataFrame()

# --- COMPONENTES DA INTERFACE ---
def login_section():
    """Exibe a seção de login."""
    st.markdown('<div class="title">Carteira de Clientes - Painel de Atividades</div>', unsafe_allow_html=True)
    
    with st.container():
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

def upload_atividades(conn: sqlite3.Connection):
    """Exibe o formulário para upload de atividades em Excel."""
    st.markdown('<div class="header">📤 Upload de Atividades</div>', unsafe_allow_html=True)
    
    with st.expander("📝 Instruções para Upload", expanded=False):
        st.markdown("""
            **Como preparar seu arquivo Excel:**
            1. O arquivo deve conter as colunas obrigatórias:
               - `Razão Social` (texto)
               - `CNPJ` (texto)
               - `Grupo` (texto)
               - `Tributação` (texto)
               - `Responsável` (texto)
            2. Você pode incluir colunas adicionais se desejar
            3. Salve o arquivo no formato .xlsx ou .xls
            
            **Dica:** Baixe nosso [modelo de planilha](#) para garantir o formato correto.
        """)
    
    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel com as atividades", 
        type=["xlsx", "xls"],
        accept_multiple_files=False,
        help="Arraste e solte ou clique para selecionar o arquivo"
    )
    
    if uploaded_file is not None:
        try:
            # Lê o arquivo Excel
            df = pd.read_excel(uploaded_file)
            
            # Verifica colunas obrigatórias
            required_columns = {'Razão Social', 'CNPJ', 'Grupo', 'Tributação', 'Responsável'}
            if not required_columns.issubset(df.columns):
                missing_cols = required_columns - set(df.columns)
                st.error(f"Colunas obrigatórias faltando: {', '.join(missing_cols)}")
                return
            
            # Mostra pré-visualização
            st.markdown("**Pré-visualização dos dados (5 primeiras linhas):**")
            st.dataframe(df.head())
            
            # Prepara dados para inserção
            atividades = []
            for _, row in df.iterrows():
                atividades.append((
                    row.get('Razão Social', ''),  # cliente
                    row.get('Razão Social', ''),  # razao_social
                    row.get('Classificação', 'B'),  # classificacao
                    row.get('Tributação', 'Simples Nacional'),  # tributacao
                    row.get('Responsável', ''),  # responsavel
                    "Atividade cadastrada em lote",  # atividade
                    row.get('Grupo', ''),  # grupo
                    row.get('Cidade', ''),  # cidade
                    datetime.now().strftime('%Y-%m-%d'),  # desde
                    "Ativo",  # status
                    row.get('E-mail', ''),  # email
                    row.get('Telefone', ''),  # telefone
                    row.get('Contato', ''),  # contato
                    row.get('Possui Folha', 'Sim'),  # possui_folha
                    row.get('Financeiro', 'Em dia'),  # financeiro
                    row.get('Contas Bancárias', 1),  # contas_bancarias
                    row.get('Forma de Entrega', 'E-mail'),  # forma_entrega
                    datetime.now().strftime('%Y-%m-%d'),  # data_entrega
                    datetime.now().strftime('%m/%Y')  # mes_referencia
                ))
            
            # Botão para confirmar importação
            if st.button("Confirmar Importação", type="primary", use_container_width=True):
                if adicionar_atividades_em_lote(conn, atividades):
                    st.success(f"✅ {len(atividades)} atividades importadas com sucesso!")
                    st.rerun()  # Força a atualização da lista de atividades
                else:
                    st.error("Ocorreu um erro ao importar as atividades")
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

def cadastro_atividade(conn: sqlite3.Connection):
    """Exibe o formulário para cadastro de novas atividades."""
    st.markdown('<div class="header">📝 Cadastro de Atividades</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Formulário Manual", "Upload em Lote"])
    
    with tab1:
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
            
            mes_referencia = st.selectbox("Mês de Referência", [
                f"{mes:02d}/{ano}" 
                for ano in range(2023, 2026) 
                for mes in range(1, 13)
            ])
            
            st.markdown("<small>Campos marcados com * são obrigatórios</small>", unsafe_allow_html=True)
            
            if st.form_submit_button("Adicionar Atividade", use_container_width=True, type="primary"):
                if cliente and responsavel and atividade:
                    campos = (
                        cliente, razao_social, classificacao, tributacao, responsavel, atividade,
                        grupo, cidade, desde.strftime('%Y-%m-%d'), status, email, telefone, contato,
                        possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega.strftime('%Y-%m-%d'), mes_referencia
                    )
                    if adicionar_atividade(conn, campos):
                        st.success("Atividade cadastrada com sucesso!", icon="✅")
                        st.rerun()  # Força a atualização da lista de atividades
                else:
                    st.error("Preencha os campos obrigatórios!", icon="❌")
    
    with tab2:
        upload_atividades(conn)

def lista_atividades(conn: sqlite3.Connection):
    """Exibe a lista de atividades cadastradas com filtros."""
    st.markdown('<div class="header">📋 Lista de Atividades</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        meses = sorted(set(
            f"{mes:02d}/{ano}" 
            for ano in range(2023, 2026) 
            for mes in range(1, 13)
        ), reverse=True)
        mes_selecionado = st.selectbox("Filtrar por mês de referência:", ["Todos"] + meses)
    
    with col2:
        responsaveis = get_responsaveis(conn)
        responsavel_selecionado = st.selectbox("Filtrar por responsável:", responsaveis)
    
    atividades = get_atividades(conn, mes_selecionado if mes_selecionado != "Todos" else None,
                              responsavel_selecionado if responsavel_selecionado != "Todos" else None)
    
    if not atividades:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.", icon="ℹ️")
        return
    
    for row in atividades:
        try:
            (id, cliente, razao_social, classificacao, tributacao, responsavel, 
             atividade, grupo, cidade, desde, status, email, telefone, contato, 
             possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega, 
             feito, data_criacao, mes_referencia) = row
        except ValueError as e:
            st.error(f"Erro ao processar atividade: {e}")
            continue
        
        with st.expander(f"{'✅' if feito else '📌'} {cliente} - {atividade} ({status}) - {mes_referencia}", expanded=False):
            st.markdown(f'<div class="card{" completed" if feito else ""}">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Responsável:** {responsavel}")
                st.markdown(f"**Razão Social:** {razao_social}")
                st.markdown(f"**Classificação/Tributação:** {classificacao} / {tributacao}")
                st.markdown(f"**Grupo/Cidade:** {grupo} / {cidade}")
                st.markdown(f"**Contato:** {contato} ({telefone} - {email})")
                st.markdown(f"**Financeiro:** {financeiro} | Folha: {possui_folha} | Contas: {contas_bancarias}")
                st.markdown(f"**Entrega:** {forma_entrega} em {data_entrega}")
                st.markdown(f"**Mês Referência:** {mes_referencia}")
                st.markdown(f"**Data de Criação:** {data_criacao}")
                
            with col2:
                st.checkbox(
                    "Marcar como concluído", 
                    value=bool(feito),
                    key=f"feito_{id}",
                    on_change=marcar_feito,
                    args=(conn, id, not feito)
                )
                
                if st.button("Excluir", key=f"del_{id}", use_container_width=True):
                    if excluir_atividade(conn, id):
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

def mostrar_indicadores(conn: sqlite3.Connection):
    """Exibe os indicadores de entrega."""
    st.markdown('<div class="header">📊 Indicadores de Entrega</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📅 Por Mês", "👤 Por Responsável"])
    
    with tab1:
        dados_mes = get_dados_indicadores(conn)
        
        if dados_mes.empty:
            st.warning("Não há dados suficientes para exibir os indicadores por mês.")
        else:
            st.subheader("Entregas por Mês")
            fig_bar = px.bar(
                dados_mes,
                x='mes_referencia',
                y=['concluidas', 'total'],
                barmode='group',
                labels={'value': 'Quantidade', 'mes_referencia': 'Mês de Referência'},
                color_discrete_map={'concluidas': '#2ecc71', 'total': '#3498db'}
            )
            fig_bar.update_layout(
                showlegend=True, 
                legend_title_text='',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#f1f1f1')
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.subheader("Percentual de Conclusão")
            fig_pie = px.pie(
                dados_mes,
                values='percentual',
                names='mes_referencia',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Greens
            )
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                marker=dict(line=dict(color='#fff', width=2))
            )
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.subheader("Detalhamento por Mês")
            dados_mes['percentual'] = dados_mes['percentual'].round(2)
            st.dataframe(
                dados_mes[['mes_referencia', 'concluidas', 'total', 'percentual']]
                .rename(columns={
                    'mes_referencia': 'Mês',
                    'concluidas': 'Concluídas',
                    'total': 'Total',
                    'percentual': '% Conclusão'
                }),
                use_container_width=True,
                height=400
            )
    
    with tab2:
        dados_responsaveis = get_dados_responsaveis(conn)
        
        if dados_responsaveis.empty:
            st.warning("Não há dados suficientes para exibir os indicadores por responsável.")
        else:
            st.subheader("Entregas por Responsável")
            fig_bar_resp = px.bar(
                dados_responsaveis,
                x='responsavel',
                y=['concluidas', 'total'],
                barmode='group',
                labels={'value': 'Quantidade', 'responsavel': 'Responsável'},
                color_discrete_map={'concluidas': '#2ecc71', 'total': '#3498db'}
            )
            fig_bar_resp.update_layout(
                showlegend=True, 
                legend_title_text='',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#f1f1f1')
            )
            st.plotly_chart(fig_bar_resp, use_container_width=True)
            
            st.subheader("Distribuição de Atividades")
            fig_pie_resp = px.pie(
                dados_responsaveis,
                values='total',
                names='responsavel',
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie_resp.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                marker=dict(line=dict(color='#fff', width=2))
            )
            fig_pie_resp.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie_resp, use_container_width=True)
            
            st.subheader("Performance por Responsável")
            fig_hbar = px.bar(
                dados_responsaveis,
                x='percentual',
                y='responsavel',
                orientation='h',
                text='percentual',
                labels={'percentual': '% Conclusão', 'responsavel': 'Responsável'},
                color='percentual',
                color_continuous_scale='Greens'
            )
            fig_hbar.update_traces(
                texttemplate='%{x:.1f}%', 
                textposition='outside',
                marker=dict(line=dict(color='rgba(0,0,0,0.1)', width=1))
            )
            fig_hbar.update_layout(
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_hbar, use_container_width=True)
            
            st.subheader("Detalhamento por Responsável")
            dados_responsaveis['percentual'] = dados_responsaveis['percentual'].round(2)
            st.dataframe(
                dados_responsaveis[['responsavel', 'concluidas', 'total', 'percentual']]
                .rename(columns={
                    'responsavel': 'Responsável',
                    'concluidas': 'Concluídas',
                    'total': 'Total',
                    'percentual': '% Conclusão'
                }),
                use_container_width=True,
                height=400
            )

# --- APLICAÇÃO PRINCIPAL ---
def main():
    """Função principal que gerencia o fluxo da aplicação."""
    load_css()
    conn = init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_section()
    else:
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Atividades", "📝 Cadastrar Atividades", "📊 Indicadores de Entrega"])
        
        with tab1:
            lista_atividades(conn)
        
        with tab2:
            cadastro_atividade(conn)
        
        with tab3:
            mostrar_indicadores(conn)
        
        with st.sidebar:
            st.markdown("## Configurações")
            
            if st.button("🚪 Sair", use_container_width=True, type="primary"):
                st.session_state.logged_in = False
                st.rerun()
            
            st.markdown("---")
            st.markdown("### Estatísticas Rápidas")
            
            try:
                c = conn.cursor()
                
                c.execute("SELECT COUNT(*) FROM atividades")
                total = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM atividades WHERE feito = 1")
                concluidas = c.fetchone()[0]
                
                percentual = (concluidas / total * 100) if total > 0 else 0
                
                # Exibindo as métricas com texto branco
                st.markdown(f"""
                    <div class="sidebar-metric-label">Total de Atividades</div>
                    <div class="sidebar-metric-value">{total}</div>
                    <div class="sidebar-metric-label">Atividades Concluídas</div>
                    <div class="sidebar-metric-value">{concluidas} ({percentual:.1f}%)</div>
                """, unsafe_allow_html=True)
                
                # Próximas entregas
                hoje = datetime.now().strftime('%Y-%m-%d')
                c.execute('''
                    SELECT cliente, atividade, data_entrega 
                    FROM atividades 
                    WHERE data_entrega >= ? AND feito = 0
                    ORDER BY data_entrega ASC
                    LIMIT 5
                ''', (hoje,))
                proximas = c.fetchall()
                
                if proximas:
                    st.markdown("### Próximas Entregas")
                    for cliente, atividade, data in proximas:
                        st.markdown(f"""
                            <div class="proxima-entrega">
                                <strong>{cliente}</strong><br>
                                {atividade}<br>
                                <small>📅 {data}</small>
                            </div>
                        """, unsafe_allow_html=True)
            except sqlite3.Error as e:
                st.error(f"Erro ao carregar estatísticas: {e}")

if __name__ == "__main__":
    main()
