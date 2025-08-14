import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import random
from typing import List, Tuple, Optional
import io
import contextlib
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Carteira de Clientes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Gerenciador de Conexão Segura ---
@contextlib.contextmanager
def get_db_connection():
    """Gerenciador de contexto para conexão segura com o banco de dados."""
    conn = None
    try:
        conn = sqlite3.connect('clientes.db', check_same_thread=False, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")  # Melhora o desempenho com múltiplas conexões
        yield conn
    except sqlite3.Error as e:
        st.error(f"Erro de conexão com o banco de dados: {e}")
        raise
    finally:
        if conn:
            conn.close()

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
def init_db():
    """Inicializa o banco de dados, criando a tabela se necessário."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS atividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT,
                razao_social TEXT NOT NULL,
                olaiseto_folio_cliente TEXT,
                tributacao TEXT NOT NULL,
                empresa_responsavel TEXT,
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
                quadro_contas_bancarias INTEGER,
                forma_entrega TEXT,
                empresa_administrada TEXT,
                protesta_no_bancario TEXT,
                parcela_perto TEXT,
                catrato TEXT,
                saldo_anterior TEXT,
                extrato TEXT,
                data_criacao TEXT NOT NULL,
                mes_referencia TEXT,
                feito INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        
        c.execute("SELECT COUNT(*) FROM atividades")
        if c.fetchone()[0] == 0:
            gerar_atividades_mensais(conn)

def gerar_atividades_mensais(conn: sqlite3.Connection):
    """Gera atividades mensais para todos os clientes até dezembro de 2025."""
    clientes = [
        ("00.000.000/0001-00", "Cliente A", "OL12345", "Simples Nacional", "Empresa A", "Responsável 1"),
        ("11.111.111/0001-11", "Cliente B", "OL67890", "Lucro Presumido", "Empresa B", "Responsável 2"),
        ("22.222.222/0001-22", "Cliente C", "OL54321", "Lucro Real", "Empresa C", "Responsável 1"),
        ("33.333.333/0001-33", "Cliente D", "OL09876", "Simples Nacional", "Empresa D", "Responsável 3"),
    ]
    
    atividades = [
        "Fechamento mensal",
        "Relatório contábil",
        "Conciliação bancária",
        "Declarações fiscais"
    ]
    
    hoje = datetime.now()
    fim = datetime(2025, 12, 1)
    
    try:
        c = conn.cursor()
        
        for cliente in clientes:
            atividade = random.choice(atividades)
            feito = random.choice([0, 1])
            campos = (
                cliente[0], cliente[1], cliente[2], cliente[3], cliente[4], cliente[5], atividade,
                "Grupo 1", "São Paulo", "01/2020", "Ativo", "email@cliente.com", "(11) 99999-9999", "Contato Financeiro",
                "Sim", "Em dia", 2, "E-mail", "Empresa Admin", "Não", "Parcela 1", "Contrato 123",
                "R$ 10.000,00", "Disponível", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), hoje.strftime('%m/%Y'), feito
            )
            
            c.execute('''
                INSERT INTO atividades (
                    cnpj, razao_social, olaiseto_folio_cliente, tributacao, empresa_responsavel, responsavel, atividade, 
                    grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                    financeiro, quadro_contas_bancarias, forma_entrega, empresa_administrada, protesta_no_bancario, 
                    parcela_perto, catrato, saldo_anterior, extrato, data_criacao, mes_referencia, feito
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', campos)
        
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Erro ao gerar atividades iniciais: {e}")

# --- FUNÇÕES DO SISTEMA ---
def adicionar_atividade(campos: Tuple) -> bool:
    """Adiciona uma nova atividade ao banco de dados."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            campos_completos = campos + (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),)
            
            c.execute('''
                INSERT INTO atividades (
                    cnpj, razao_social, olaiseto_folio_cliente, tributacao, empresa_responsavel, responsavel, atividade, 
                    grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                    financeiro, quadro_contas_bancarias, forma_entrega, empresa_administrada, protesta_no_bancario, 
                    parcela_perto, catrato, saldo_anterior, extrato, data_criacao, mes_referencia
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', campos_completos)
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return True
    except sqlite3.Error as e:
        st.error(f"Erro ao adicionar atividade: {e}")
        return False

def adicionar_atividades_em_lote(dados: List[Tuple]) -> bool:
    """Adiciona múltiplas atividades ao banco de dados em lote."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Preparar os dados com data de criação
            dados_completos = [
                (*linha, datetime.now().strftime('%Y-%m-%d %H:%M:%S')) 
                for linha in dados
            ]
            
            # Iniciar transação
            c.execute("BEGIN TRANSACTION")
            
            try:
                c.executemany('''
                    INSERT INTO atividades (
                        cnpj, razao_social, olaiseto_folio_cliente, tributacao, empresa_responsavel, responsavel, atividade, 
                        grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                        financeiro, quadro_contas_bancarias, forma_entrega, empresa_administrada, protesta_no_bancario, 
                        parcela_perto, catrato, saldo_anterior, extrato, data_criacao, mes_referencia
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', dados_completos)
                
                conn.commit()
                st.session_state.atualizar_lista = True  # Flag para atualizar a lista
                return True
            except sqlite3.Error as e:
                conn.rollback()
                st.error(f"Erro durante a inserção em lote: {e}")
                return False
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return False

def excluir_atividade(id: int) -> bool:
    """Remove uma atividade do banco de dados pelo ID."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM atividades WHERE id = ?', (id,))
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao excluir atividade: {e}")
        return False

def marcar_feito(id: int, feito: bool) -> bool:
    """Atualiza o status de conclusão de uma atividade."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE atividades SET feito = ? WHERE id = ?', (int(feito), id))
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False

def get_atividades(filtro_mes: str = None, filtro_responsavel: str = None, data_inicio: str = None, data_fim: str = None) -> List[Tuple]:
    """Retorna todas as atividades ordenadas por data de criação com filtros opcionais."""
    try:
        with get_db_connection() as conn:
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
            if data_inicio and data_fim:
                conditions.append('data_criacao BETWEEN ? AND ?')
                params.extend([data_inicio, data_fim])
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY data_criacao DESC'
            
            c.execute(query, tuple(params))
            return c.fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar atividades: {e}")
        return []

def get_responsaveis() -> List[str]:
    """Retorna a lista de responsáveis únicos."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT DISTINCT responsavel FROM atividades ORDER BY responsavel')
            return ["Todos"] + [row[0] for row in c.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar responsáveis: {e}")
        return ["Todos"]

def get_dados_indicadores(data_inicio: str = None, data_fim: str = None) -> pd.DataFrame:
    """Retorna dados para os indicadores de entrega."""
    try:
        with get_db_connection() as conn:
            query = '''
                SELECT 
                    mes_referencia,
                    SUM(feito) as concluidas,
                    COUNT(*) as total,
                    (SUM(feito) * 100.0 / COUNT(*)) as percentual
                FROM atividades
            '''
            params = []
            
            conditions = []
            if data_inicio and data_fim:
                conditions.append('data_criacao BETWEEN ? AND ?')
                params.extend([data_inicio, data_fim])
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += '''
                GROUP BY mes_referencia
                ORDER BY SUBSTR(mes_referencia, 4) || SUBSTR(mes_referencia, 1, 2)
            '''
            
            return pd.read_sql(query, conn, params=tuple(params) if params else None)
    except Exception as e:
        st.error(f"Erro ao gerar indicadores: {e}")
        return pd.DataFrame()

def get_dados_responsaveis(data_inicio: str = None, data_fim: str = None) -> pd.DataFrame:
    """Retorna dados para análise por responsável."""
    try:
        with get_db_connection() as conn:
            query = '''
                SELECT 
                    responsavel,
                    SUM(feito) as concluidas,
                    COUNT(*) as total,
                    (SUM(feito) * 100.0 / COUNT(*)) as percentual
                FROM atividades
            '''
            params = []
            
            conditions = []
            if data_inicio and data_fim:
                conditions.append('data_criacao BETWEEN ? AND ?')
                params.extend([data_inicio, data_fim])
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += '''
                GROUP BY responsavel
                ORDER BY percentual DESC
            '''
            
            return pd.read_sql(query, conn, params=tuple(params) if params else None)
    except Exception as e:
        st.error(f"Erro ao gerar dados por responsável: {e}")
        return pd.DataFrame()

def get_entregas_gerais(data_inicio: str = None, data_fim: str = None) -> pd.DataFrame:
    """Retorna dados para a tabela de entregas gerais."""
    try:
        with get_db_connection() as conn:
            query = '''
                SELECT 
                    id,
                    cnpj AS "CNPJ",
                    razao_social AS "RAZÃO SOCIAL",
                    olaiseto_folio_cliente AS "OLAISETO FOLIO DO CLIENTE",
                    tributacao AS "TRIBUTAÇÃO",
                    empresa_responsavel AS "EMPRESA RESPONSÁVEL",
                    responsavel AS "RESPONSÁVEL",
                    atividade AS "ATIVIDADE",
                    grupo AS "GRUPO",
                    cidade AS "CIDADE",
                    desde AS "DESDE",
                    status AS "ESTATUS",
                    email AS "E-MAIL",
                    telefone AS "TELEFONE",
                    contato AS "CONTATO",
                    possui_folha AS "POSSUI FOLLIM",
                    financeiro AS "FINANCEIRO",
                    quadro_contas_bancarias AS "QUADR DE CONTAS BANCALAS",
                    forma_entrega AS "FORMA DE ENTREVÊNCIA",
                    empresa_administrada AS "EMPRESA ADMINISTRADA",
                    protesta_no_bancario AS "PROFÉSITA NO BANCÁRIO",
                    parcela_perto AS "PARCELA PERTO",
                    catrato AS "CATRATO",
                    saldo_anterior AS "SALANCI",
                    extrato AS "EXTRATO",
                    data_criacao AS "DATA CRIAÇÃO",
                    mes_referencia AS "MÊS REFERÊNCIA",
                    feito AS "CONCLUÍDO"
                FROM atividades
            '''
            params = []
            
            conditions = []
            if data_inicio and data_fim:
                conditions.append('data_criacao BETWEEN ? AND ?')
                params.extend([data_inicio, data_fim])
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY data_criacao DESC'
            
            return pd.read_sql(query, conn, params=tuple(params) if params else None)
    except Exception as e:
        st.error(f"Erro ao gerar dados de entregas gerais: {e}")
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

def upload_atividades():
    """Exibe o formulário para upload de atividades em Excel."""
    st.markdown('<div class="header">📤 Upload de Atividades</div>', unsafe_allow_html=True)
    
    with st.expander("📝 Instruções para Upload", expanded=False):
        st.markdown("""
            **Como preparar seu arquivo Excel:**
            1. O arquivo deve conter as colunas obrigatórias:
               - `CNPJ` (texto)
               - `Razão Social` (texto)
               - `OLAISETO FOLIO DO CLIENTE` (texto)
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
            required_columns = {'CNPJ', 'Razão Social', 'OLAISETO FOLIO DO CLIENTE', 'Tributação', 'Responsável'}
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
                    row.get('CNPJ', ''),  # cnpj
                    row.get('Razão Social', ''),  # razao_social
                    row.get('OLAISETO FOLIO DO CLIENTE', ''),  # olaiseto_folio_cliente
                    row.get('Tributação', 'Simples Nacional'),  # tributacao
                    row.get('Empresa Responsável', ''),  # empresa_responsavel
                    row.get('Responsável', ''),  # responsavel
                    row.get('Atividade', 'Atividade cadastrada em lote'),  # atividade
                    row.get('Grupo', ''),  # grupo
                    row.get('Cidade', ''),  # cidade
                    row.get('Desde', datetime.now().strftime('%Y-%m-%d')),  # desde
                    row.get('Status', 'Ativo'),  # status
                    row.get('E-mail', ''),  # email
                    row.get('Telefone', ''),  # telefone
                    row.get('Contato', ''),  # contato
                    row.get('Possui Folha', 'Sim'),  # possui_folha
                    row.get('Financeiro', 'Em dia'),  # financeiro
                    row.get('Quadro de Contas Bancárias', 1),  # quadro_contas_bancarias
                    row.get('Forma de Entrega', 'E-mail'),  # forma_entrega
                    row.get('Empresa Administrada', ''),  # empresa_administrada
                    row.get('Protesta no Bancário', 'Não'),  # protesta_no_bancario
                    row.get('Parcela Perto', ''),  # parcela_perto
                    row.get('Contrato', ''),  # catrato
                    row.get('Saldo Anterior', ''),  # saldo_anterior
                    row.get('Extrato', ''),  # extrato
                    datetime.now().strftime('%m/%Y')  # mes_referencia
                ))
            
            # Botão para confirmar importação
            if st.button("Confirmar Importação", type="primary", use_container_width=True):
                if adicionar_atividades_em_lote(atividades):
                    st.success(f"✅ {len(atividades)} atividades importadas com sucesso!")
                    st.rerun()  # Força a atualização da lista de atividades
                else:
                    st.error("Ocorreu um erro ao importar as atividades")
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

def cadastro_atividade():
    """Exibe o formulário para cadastro de novas atividades."""
    st.markdown('<div class="header">📝 Cadastro de Atividades</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Formulário Manual", "Upload em Lote"])
    
    with tab1:
        with st.form("nova_atividade", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="form-label">Informações Básicas</div>', unsafe_allow_html=True)
                cnpj = st.text_input("CNPJ*", placeholder="00.000.000/0000-00")
                razao_social = st.text_input("Razão Social*", placeholder="Razão social completa")
                olaiseto_folio = st.text_input("OLAISETO FOLIO DO CLIENTE", placeholder="Código do cliente")
                tributacao = st.selectbox("Tributação*", ["Simples Nacional", "Lucro Presumido", "Lucro Real"])
                empresa_responsavel = st.text_input("Empresa Responsável", placeholder="Nome da empresa responsável")
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
                contato = st.text_input("Contato", placeholder="Nome do contato")
                
            st.markdown('<div class="form-label">Detalhes Financeiros</div>', unsafe_allow_html=True)
            col3, col4, col5 = st.columns(3)
            
            with col3:
                possui_folha = st.selectbox("Possui Folha?", ["Sim", "Não", "Não se aplica"])
                financeiro = st.text_input("Financeiro", placeholder="Informações financeiras")
                
            with col4:
                quadro_contas_bancarias = st.number_input("Quadro de Contas Bancárias", min_value=0, value=1)
                forma_entrega = st.selectbox("Forma de Entrega", ["E-mail", "Correio", "Pessoalmente", "Outros"])
                
            with col5:
                empresa_administrada = st.text_input("Empresa Administrada", placeholder="Nome da empresa administrada")
                protesta_no_bancario = st.selectbox("Protesta no Bancário?", ["Sim", "Não"])
                
            st.markdown('<div class="form-label">Outras Informações</div>', unsafe_allow_html=True)
            col6, col7, col8 = st.columns(3)
            
            with col6:
                parcela_perto = st.text_input("Parcela Perto", placeholder="Informações sobre parcelas")
                
            with col7:
                catrato = st.text_input("Contrato", placeholder="Número do contrato")
                
            with col8:
                saldo_anterior = st.text_input("Saldo Anterior", placeholder="Saldo anterior")
                extrato = st.text_input("Extrato", placeholder="Extrato disponível")
            
            mes_referencia = st.selectbox("Mês de Referência", [
                f"{mes:02d}/{ano}" 
                for ano in range(2023, 2026) 
                for mes in range(1, 13)
            ])
            
            st.markdown("<small>Campos marcados com * são obrigatórios</small>", unsafe_allow_html=True)
            
            if st.form_submit_button("Adicionar Atividade", use_container_width=True, type="primary"):
                if cnpj and razao_social and responsavel and atividade:
                    campos = (
                        cnpj, razao_social, olaiseto_folio, tributacao, empresa_responsavel, responsavel, atividade,
                        grupo, cidade, desde.strftime('%Y-%m-%d'), status, email, telefone, contato,
                        possui_folha, financeiro, quadro_contas_bancarias, forma_entrega, empresa_administrada,
                        protesta_no_bancario, parcela_perto, catrato, saldo_anterior, extrato, mes_referencia
                    )
                    if adicionar_atividade(campos):
                        st.success("Atividade cadastrada com sucesso!", icon="✅")
                        st.rerun()  # Força a atualização da lista de atividades
                else:
                    st.error("Preencha os campos obrigatórios!", icon="❌")
    
    with tab2:
        upload_atividades()

def lista_atividades():
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
        responsaveis = get_responsaveis()
        responsavel_selecionado = st.selectbox("Filtrar por responsável:", responsaveis)
    
    atividades = get_atividades(
        mes_selecionado if mes_selecionado != "Todos" else None,
        responsavel_selecionado if responsavel_selecionado != "Todos" else None
    )
    
    if not atividades:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.", icon="ℹ️")
        return
    
    for row in atividades:
        try:
            (id, cnpj, razao_social, olaiseto_folio, tributacao, empresa_responsavel, responsavel, 
             atividade, grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
             financeiro, quadro_contas_bancarias, forma_entrega, empresa_administrada, protesta_no_bancario,
             parcela_perto, catrato, saldo_anterior, extrato, data_criacao, mes_referencia, feito) = row
        except ValueError as e:
            st.error(f"Erro ao processar atividade: {e}")
            continue
        
        with st.expander(f"{'✅' if feito else '📌'} {razao_social} - {atividade} ({status}) - {mes_referencia}", expanded=False):
            st.markdown(f'<div class="card{" completed" if feito else ""}">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**CNPJ:** {cnpj}")
                st.markdown(f"**Razão Social:** {razao_social}")
                st.markdown(f"**OLAISETO FOLIO:** {olaiseto_folio}")
                st.markdown(f"**Tributação:** {tributacao}")
                st.markdown(f"**Empresa Responsável:** {empresa_responsavel}")
                st.markdown(f"**Responsável:** {responsavel}")
                st.markdown(f"**Grupo/Cidade:** {grupo} / {cidade}")
                st.markdown(f"**Contato:** {contato} ({telefone} - {email})")
                st.markdown(f"**Financeiro:** {financeiro} | Folha: {possui_folha} | Contas: {quadro_contas_bancarias}")
                st.markdown(f"**Entrega:** {forma_entrega}")
                st.markdown(f"**Empresa Administrada:** {empresa_administrada}")
                st.markdown(f"**Protesta no Bancário:** {protesta_no_bancario}")
                st.markdown(f"**Parcela Perto:** {parcela_perto}")
                st.markdown(f"**Contrato:** {catrato}")
                st.markdown(f"**Saldo Anterior:** {saldo_anterior}")
                st.markdown(f"**Extrato:** {extrato}")
                st.markdown(f"**Mês Referência:** {mes_referencia}")
                st.markdown(f"**Data de Criação:** {data_criacao}")
                
            with col2:
                st.checkbox(
                    "Marcar como concluído", 
                    value=bool(feito),
                    key=f"feito_{id}",
                    on_change=marcar_feito,
                    args=(id, not feito)
                )
                
                if st.button("Excluir", key=f"del_{id}", use_container_width=True):
                    if excluir_atividade(id):
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

def mostrar_indicadores():
    """Exibe os indicadores de entrega."""
    st.markdown('<div class="header">📊 Indicadores de Entrega</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📅 Por Mês", "👤 Por Responsável", "📋 Entregas Gerais"])
    
    with tab1:
        st.subheader("Selecionar Período")
        col1, col2 = st.columns(2)
        
        with col1:
            data_inicio = st.date_input(
                "Data Início",
                value=datetime.now() - relativedelta(months=3),
                min_value=datetime(2023, 1, 1),
                max_value=datetime.now()
            )
        
        with col2:
            data_fim = st.date_input(
                "Data Fim",
                value=datetime.now(),
                min_value=datetime(2023, 1, 1),
                max_value=datetime.now()
            )
        
        dados_mes = get_dados_indicadores(
            data_inicio.strftime('%Y-%m-%d'),
            data_fim.strftime('%Y-%m-%d')
        )
        
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
        st.subheader("Selecionar Período")
        col1, col2 = st.columns(2)
        
        with col1:
            data_inicio = st.date_input(
                "Data Início",
                value=datetime.now() - relativedelta(months=3),
                min_value=datetime(2023, 1, 1),
                max_value=datetime.now(),
                key="data_inicio_resp"
            )
        
        with col2:
            data_fim = st.date_input(
                "Data Fim",
                value=datetime.now(),
                min_value=datetime(2023, 1, 1),
                max_value=datetime.now(),
                key="data_fim_resp"
            )
        
        dados_responsaveis = get_dados_responsaveis(
            data_inicio.strftime('%Y-%m-%d'),
            data_fim.strftime('%Y-%m-%d')
        )
        
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
    
    with tab3:
        st.subheader("Selecionar Período")
        col1, col2 = st.columns(2)
        
        with col1:
            data_inicio = st.date_input(
                "Data Início",
                value=datetime.now() - relativedelta(months=3),
                min_value=datetime(2023, 1, 1),
                max_value=datetime.now(),
                key="data_inicio_geral"
            )
        
        with col2:
            data_fim = st.date_input(
                "Data Fim",
                value=datetime.now(),
                min_value=datetime(2023, 1, 1),
                max_value=datetime.now(),
                key="data_fim_geral"
            )
        
        entregas_gerais = get_entregas_gerais(
            data_inicio.strftime('%Y-%m-%d'),
            data_fim.strftime('%Y-%m-%d')
        )
        
        if entregas_gerais is None or entregas_gerais.empty:
            st.warning("Não há dados suficientes para exibir as entregas gerais.")
        else:
            st.subheader("Tabela de Entregas Gerais")
            st.dataframe(
                entregas_gerais,
                use_container_width=True,
                height=600
            )

def mostrar_sidebar():
    """Exibe a barra lateral com estatísticas e próximas entregas."""
    with st.sidebar:
        st.markdown("## Configurações")
        
        if st.button("🚪 Sair", use_container_width=True, type="primary"):
            st.session_state.logged_in = False
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Estatísticas Rápidas")
        
        try:
            with get_db_connection() as conn:
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
                    SELECT razao_social, atividade, data_criacao 
                    FROM atividades 
                    WHERE data_criacao >= ? AND feito = 0
                    ORDER BY data_criacao ASC
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

# --- APLICAÇÃO PRINCIPAL ---
def main():
    """Função principal que gerencia o fluxo da aplicação."""
    load_css()
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_section()
    else:
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Atividades", "📝 Cadastrar Atividades", "📊 Indicadores de Entrega"])
        
        with tab1:
            lista_atividades()
        
        with tab2:
            cadastro_atividade()
        
        with tab3:
            mostrar_indicadores()
        
        mostrar_sidebar()

if __name__ == "__main__":
    main()
