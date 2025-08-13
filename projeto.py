import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import random
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
            
            .completed {
                background-color: #e8f5e9;
                border-left: 5px solid var(--success-color);
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
        </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db() -> sqlite3.Connection:
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
            mes_referencia TEXT NOT NULL
        )
    ''')
    conn.commit()
    
    # Verificar e adicionar coluna mes_referencia se não existir
    c.execute("PRAGMA table_info(atividades)")
    columns = [column[1] for column in c.fetchall()]
    if 'mes_referencia' not in columns:
        c.execute("ALTER TABLE atividades ADD COLUMN mes_referencia TEXT NOT NULL DEFAULT '01/2023'")
        conn.commit()
    
    # Popular com dados iniciais se a tabela estiver vazia
    c.execute("SELECT COUNT(*) FROM atividades")
    if c.fetchone()[0] == 0:
        popular_dados_iniciais(conn)
    
    return conn

def popular_dados_iniciais(conn: sqlite3.Connection):
    clientes = [
        ("Cliente A", "Razão Social A", "B", "Simples Nacional", "Responsável 1"),
        ("Cliente B", "Razão Social B", "A", "Lucro Presumido", "Responsável 2"),
        ("Cliente C", "Razão Social C", "C", "Lucro Real", "Responsável 1"),
    ]
    
    atividades = [
        "Fechamento mensal",
        "Relatório contábil",
        "Conciliação bancária"
    ]
    
    hoje = datetime.now()
    fim = datetime(2025, 12, 1)
    c = conn.cursor()
    
    while hoje <= fim:
        mes_ref = hoje.strftime("%m/%Y")
        for cliente in clientes:
            atividade = random.choice(atividades)
            campos = (
                cliente[0], cliente[1], cliente[2], cliente[3], cliente[4], atividade,
                "Grupo 1", "São Paulo", "01/2020", "Ativo", "email@cliente.com", 
                "(11) 99999-9999", "Contato Financeiro", "Sim", "Em dia", 2, 
                "E-mail", hoje.strftime('%Y-%m-%d'), int(False),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'), mes_ref
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

# --- FUNÇÕES PRINCIPAIS ---
def adicionar_atividade(conn: sqlite3.Connection, campos: Tuple) -> bool:
    try:
        c = conn.cursor()
        campos_completos = campos + (int(False), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), campos[17])  # feito, data_criacao, mes_referencia
        c.execute('''
            INSERT INTO atividades (
                cliente, razao_social, classificacao, tributacao, responsavel, atividade, 
                grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                financeiro, contas_bancarias, forma_entrega, data_entrega, feito, data_criacao, mes_referencia
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', campos_completos)
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao adicionar atividade: {e}")
        return False

def get_atividades(conn: sqlite3.Connection, filtro_mes: str = None) -> List[Tuple]:
    try:
        c = conn.cursor()
        if filtro_mes:
            c.execute('''
                SELECT id, cliente, razao_social, classificacao, tributacao, responsavel, 
                       atividade, grupo, cidade, desde, status, email, telefone, contato, 
                       possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega, 
                       feito, data_criacao, mes_referencia 
                FROM atividades 
                WHERE mes_referencia = ? 
                ORDER BY data_criacao DESC
            ''', (filtro_mes,))
        else:
            c.execute('''
                SELECT id, cliente, razao_social, classificacao, tributacao, responsavel, 
                       atividade, grupo, cidade, desde, status, email, telefone, contato, 
                       possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega, 
                       feito, data_criacao, mes_referencia 
                FROM atividades 
                ORDER BY data_criacao DESC
            ''')
        return c.fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar atividades: {e}")
        return []

def get_dados_indicadores(conn: sqlite3.Connection) -> pd.DataFrame:
    try:
        query = '''
            SELECT 
                mes_referencia,
                SUM(feito) as concluidas,
                COUNT(*) as total,
                (SUM(feito) * 100.0 / COUNT(*)) as percentual
            FROM atividades
            GROUP BY mes_referencia
            ORDER BY 
                SUBSTR(mes_referencia, 4, 4) || 
                SUBSTR(mes_referencia, 1, 2)
        '''
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erro ao gerar indicadores: {e}")
        return pd.DataFrame()

# --- INTERFACE DO USUÁRIO ---
def mostrar_cadastro(conn):
    st.markdown('<div class="header">📝 Cadastro de Atividades</div>', unsafe_allow_html=True)
    
    with st.form("nova_atividade", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="form-label">Informações Básicas</div>', unsafe_allow_html=True)
            cliente = st.text_input("Cliente*")
            responsavel = st.text_input("Responsável*")
            atividade = st.text_input("Atividade*")
            
        with col2:
            st.markdown('<div class="form-label">Informações Adicionais</div>', unsafe_allow_html=True)
            status = st.selectbox("Status", ["Ativo", "Inativo", "Potencial", "Perdido"])
            mes_referencia = st.selectbox("Mês de Referência*", 
                [f"{m:02d}/{y}" for y in range(2023, 2026) for m in range(1, 13)])
        
        if st.form_submit_button("Adicionar"):
            if cliente and responsavel and atividade:
                campos = (
                    cliente, "", "", "", responsavel, atividade,
                    "", "", "", status, "", "", "",
                    "", "", 0, "", datetime.now().strftime('%Y-%m-%d'),
                    mes_referencia
                )
                if adicionar_atividade(conn, campos):
                    st.success("Atividade cadastrada com sucesso!")

def mostrar_lista(conn):
    st.markdown('<div class="header">📋 Lista de Atividades</div>', unsafe_allow_html=True)
    
    meses = [f"{m:02d}/{y}" for y in range(2023, 2026) for m in range(1, 13)]
    mes_selecionado = st.selectbox("Filtrar por mês:", ["Todos"] + meses)
    
    atividades = get_atividades(conn, mes_selecionado if mes_selecionado != "Todos" else None)
    
    for row in atividades:
        try:
            (id, cliente, *_, feito, _, mes_ref) = row
            with st.expander(f"{'✅' if feito else '📌'} {cliente} - {mes_ref}"):
                st.write(f"Responsável: {row[5]}")
                st.write(f"Status: {row[10]}")
        except Exception as e:
            st.error(f"Erro ao exibir atividade: {e}")

def mostrar_indicadores(conn):
    st.markdown('<div class="header">📊 Indicadores</div>', unsafe_allow_html=True)
    
    dados = get_dados_indicadores(conn)
    if not dados.empty:
        st.plotly_chart(px.bar(dados, x='mes_referencia', y=['concluidas', 'total'], 
                             barmode='group', title="Entregas por Mês"))
        st.plotly_chart(px.pie(dados, values='percentual', names='mes_referencia',
                             title="Percentual de Conclusão", hole=0.4))

# --- APLICAÇÃO PRINCIPAL ---
def main():
    load_css()
    conn = init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        with st.form("login"):
            if st.form_submit_button("Login"):
                st.session_state.logged_in = True
                st.rerun()
    else:
        tab1, tab2, tab3 = st.tabs(["Cadastro", "Lista", "Indicadores"])
        with tab1:
            mostrar_cadastro(conn)
        with tab2:
            mostrar_lista(conn)
        with tab3:
            mostrar_indicadores(conn)
        
        if st.sidebar.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

if __name__ == "__main__":
    main()
