import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px
import random
from typing import List, Tuple
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
        # Habilita o modo WAL para melhor concorrência
        conn.execute("PRAGMA journal_mode=WAL")
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
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, var(--dark-color), #34495e) !important;
            }
            .sidebar-metric-label { color: white !important; }
            .sidebar-metric-value { color: white !important; font-size: 1.5rem !important; font-weight: bold !important; }
            .proxima-entrega { background: white; padding: 10px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); color: black !important; }
            .proxima-entrega strong, .proxima-entrega small { color: black !important; }
            .stButton>button { background: linear-gradient(135deg, var(--primary-color), #2980b9); color: white; font-weight: 600; border: none; border-radius: 8px; padding: 0.7rem 1.5rem; transition: var(--transition); box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; }
            .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 7px 14px rgba(0,0,0,0.15); background: linear-gradient(135deg, #2980b9, var(--primary-color)); }
        </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def check_and_update_schema(conn: sqlite3.Connection):
    """Verifica e atualiza o schema da tabela 'atividades' para garantir que todas as colunas existam."""
    c = conn.cursor()
    
    expected_columns = {
        'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'cnpj': 'TEXT',
        'razao_social': 'TEXT NOT NULL',
        'olaiseto_folio_cliente': 'TEXT',
        'tributacao': 'TEXT NOT NULL',
        'empresa_responsavel': 'TEXT',
        'responsavel': 'TEXT NOT NULL',
        'atividade': 'TEXT NOT NULL',
        'grupo': 'TEXT',
        'cidade': 'TEXT',
        'desde': 'TEXT',
        'status': 'TEXT',
        'email': 'TEXT',
        'telefone': 'TEXT',
        'contato': 'TEXT',
        'possui_folha': 'TEXT',
        'financeiro': 'TEXT',
        'quadro_contas_bancarias': 'INTEGER',
        'forma_entrega': 'TEXT',
        'empresa_administrada': 'TEXT',
        'protesta_no_bancario': 'TEXT',
        'parcela_perto': 'TEXT',
        'contrato': 'TEXT',  # Corrigido de 'catrato'
        'saldo_anterior': 'TEXT',
        'extrato': 'TEXT',
        'data_criacao': 'TEXT NOT NULL',
        'mes_referencia': 'TEXT',
        'feito': 'INTEGER DEFAULT 0'
    }
    
    try:
        c.execute("PRAGMA table_info(atividades)")
        existing_columns = {row[1] for row in c.fetchall()}
        
        for col_name, col_def in expected_columns.items():
            if col_name not in existing_columns:
                c.execute(f"ALTER TABLE atividades ADD COLUMN {col_name} {col_def}")
        
        conn.commit()

    except sqlite3.Error as e:
        # A tabela provavelmente não existe ainda, o que é normal na primeira execução
        if "no such table" not in str(e):
            st.error(f"Erro ao verificar o schema do banco de dados: {e}")

def init_db():
    """Inicializa o banco de dados, criando e atualizando a tabela se necessário."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Cria a tabela se ela não existir
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
                contrato TEXT, -- Corrigido de 'catrato'
                saldo_anterior TEXT,
                extrato TEXT,
                data_criacao TEXT NOT NULL,
                mes_referencia TEXT,
                feito INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

        # Verifica e adiciona colunas que possam estar faltando
        check_and_update_schema(conn)
        
        # Popula com dados iniciais se a tabela estiver vazia
        c.execute("SELECT COUNT(*) FROM atividades")
        if c.fetchone()[0] == 0:
            gerar_atividades_iniciais(conn)

def gerar_atividades_iniciais(conn: sqlite3.Connection):
    """Gera algumas atividades iniciais para demonstração."""
    clientes = [
        ("00.000.000/0001-00", "Cliente A", "OL12345", "Simples Nacional", "Empresa A", "Responsável 1"),
        ("11.111.111/0001-11", "Cliente B", "OL67890", "Lucro Presumido", "Empresa B", "Responsável 2"),
    ]
    atividades_exemplo = ["Fechamento mensal", "Relatório contábil", "Conciliação bancária"]
    
    try:
        c = conn.cursor()
        for cliente in clientes:
            campos = (
                cliente[0], cliente[1], cliente[2], cliente[3], cliente[4], cliente[5], random.choice(atividades_exemplo),
                "Grupo 1", "São Paulo", "01/2020", "Ativo", "email@cliente.com", "(11) 99999-9999", "Contato Financeiro",
                "Sim", "Em dia", 2, "E-mail", "Empresa Admin", "Não", "Parcela 1", "Contrato 123", # 'Contrato 123'
                "R$ 10.000,00", "Disponível", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%m/%Y'), random.choice([0, 1])
            )
            c.execute('''
                INSERT INTO atividades (
                    cnpj, razao_social, olaiseto_folio_cliente, tributacao, empresa_responsavel, responsavel, atividade, 
                    grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                    financeiro, quadro_contas_bancarias, forma_entrega, empresa_administrada, protesta_no_bancario, 
                    parcela_perto, contrato, saldo_anterior, extrato, data_criacao, mes_referencia, feito
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    parcela_perto, contrato, saldo_anterior, extrato, mes_referencia, data_criacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', campos_completos)
            conn.commit()
            return True
    except sqlite3.Error as e:
        st.error(f"Erro ao adicionar atividade: {e}")
        return False

def adicionar_atividades_em_lote(dados: List[Tuple]) -> bool:
    """Adiciona múltiplas atividades ao banco de dados."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            dados_completos = [(*linha, datetime.now().strftime('%Y-%m-%d %H:%M:%S')) for linha in dados]
            c.executemany('''
                INSERT INTO atividades (
                    cnpj, razao_social, olaiseto_folio_cliente, tributacao, empresa_responsavel, responsavel, atividade, 
                    grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                    financeiro, quadro_contas_bancarias, forma_entrega, empresa_administrada, protesta_no_bancario, 
                    parcela_perto, contrato, saldo_anterior, extrato, mes_referencia, data_criacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', dados_completos)
            conn.commit()
            return True
    except sqlite3.Error as e:
        st.error(f"Erro durante a inserção em lote: {e}")
        return False

def excluir_atividade(id_atividade: int) -> bool:
    """Remove uma atividade do banco de dados pelo ID."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM atividades WHERE id = ?', (id_atividade,))
            conn.commit()
            return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao excluir atividade: {e}")
        return False

def marcar_feito(id_atividade: int, feito: bool) -> bool:
    """Atualiza o status de conclusão de uma atividade."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE atividades SET feito = ? WHERE id = ?', (int(feito), id_atividade))
            conn.commit()
            return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False

def get_atividades(filtro_mes: str = None, filtro_responsavel: str = None) -> List[Tuple]:
    """Retorna atividades com filtros opcionais, especificando todas as colunas."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            # Seleciona colunas explicitamente para garantir a ordem e evitar erros de desempacotamento
            query = '''
                SELECT id, cnpj, razao_social, olaiseto_folio_cliente, tributacao, empresa_responsavel, 
                       responsavel, atividade, grupo, cidade, desde, status, email, telefone, contato, 
                       possui_folha, financeiro, quadro_contas_bancarias, forma_entrega, 
                       empresa_administrada, protesta_no_bancario, parcela_perto, contrato, 
                       saldo_anterior, extrato, data_criacao, mes_referencia, feito 
                FROM atividades
            '''
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

def get_responsaveis() -> List[str]:
    """Retorna a lista de responsáveis únicos."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT DISTINCT responsavel FROM atividades ORDER BY responsavel')
            return ["Todos"] + [row[0] for row in c.fetchall() if row[0]]
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar responsáveis: {e}")
        return ["Todos"]

def get_dataframe(query: str, params: tuple = None) -> pd.DataFrame:
    """Executa uma query e retorna um DataFrame do Pandas."""
    try:
        with get_db_connection() as conn:
            return pd.read_sql_query(query, conn, params=params if params else None)
    except Exception as e:
        st.error(f"Erro ao gerar dados: {e}")
        return pd.DataFrame()

# --- COMPONENTES DA INTERFACE ---
def login_section():
    """Exibe a seção de login."""
    st.markdown('<div class="title">Carteira de Clientes - Painel de Atividades</div>', unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Usuário", key="username")
        password = st.text_input("Senha", type="password", key="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            if username == "admin" and password == "reali":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciais inválidas. Tente novamente.", icon="⚠️")

def cadastro_atividade():
    """Exibe o formulário para cadastro de novas atividades."""
    st.markdown('<div class="header">📝 Cadastro de Atividades</div>', unsafe_allow_html=True)
    
    with st.form("nova_atividade", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<h6>Informações Básicas</h6>", unsafe_allow_html=True)
            cnpj = st.text_input("CNPJ*", placeholder="00.000.000/0000-00")
            razao_social = st.text_input("Razão Social*", placeholder="Razão social completa")
            tributacao = st.selectbox("Tributação*", ["Simples Nacional", "Lucro Presumido", "Lucro Real"])
            responsavel = st.text_input("Responsável*", placeholder="Nome do responsável")
            atividade = st.text_input("Atividade*", placeholder="Descrição da atividade")
        with col2:
            st.markdown("<h6>Informações Adicionais</h6>", unsafe_allow_html=True)
            olaiseto_folio = st.text_input("OLAISETO FOLIO DO CLIENTE")
            empresa_responsavel = st.text_input("Empresa Responsável")
            grupo = st.text_input("Grupo")
            cidade = st.text_input("Cidade")
            desde = st.date_input("Cliente desde", value=datetime.now())
            status = st.selectbox("Status", ["Ativo", "Inativo", "Potencial"])

        mes_referencia = st.selectbox("Mês de Referência", [f"{m:02d}/{a}" for a in range(2023, 2026) for m in range(1, 13)])
        
        with st.expander("Mais detalhes (opcional)"):
            c1, c2, c3 = st.columns(3)
            with c1:
                email = c1.text_input("E-mail")
                telefone = c1.text_input("Telefone")
                contato = c1.text_input("Contato")
            with c2:
                possui_folha = c2.selectbox("Possui Folha?", ["Sim", "Não"])
                financeiro = c2.text_input("Financeiro")
                quadro_contas_bancarias = c2.number_input("Nº Contas Bancárias", min_value=0, value=0)
            with c3:
                forma_entrega = c3.selectbox("Forma de Entrega", ["E-mail", "Correio", "Pessoalmente"])
                empresa_administrada = c3.text_input("Empresa Administrada")
                protesta_no_bancario = c3.selectbox("Protesta no Bancário?", ["Sim", "Não"])
        
        if st.form_submit_button("Adicionar Atividade", use_container_width=True, type="primary"):
            if all([cnpj, razao_social, responsavel, atividade]):
                campos = (
                    cnpj, razao_social, olaiseto_folio, tributacao, empresa_responsavel, responsavel, atividade,
                    grupo, cidade, desde.strftime('%Y-%m-%d'), status, email, telefone, contato, possui_folha,
                    financeiro, quadro_contas_bancarias, forma_entrega, empresa_administrada,
                    protesta_no_bancario, '', '', '', '', mes_referencia  # Campos vazios para compatibilidade
                )
                if adicionar_atividade(campos):
                    st.success("Atividade cadastrada com sucesso!", icon="✅")
                    st.rerun()
            else:
                st.error("Preencha os campos obrigatórios (*)", icon="❌")

def lista_atividades():
    """Exibe a lista de atividades cadastradas com filtros."""
    st.markdown('<div class="header">📋 Lista de Atividades</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    meses = sorted(set([f"{m:02d}/{a}" for a in range(2023, 2026) for m in range(1, 13)]), reverse=True)
    mes_selecionado = col1.selectbox("Filtrar por mês:", ["Todos"] + meses)
    responsavel_selecionado = col2.selectbox("Filtrar por responsável:", get_responsaveis())
    
    atividades = get_atividades(mes_selecionado, responsavel_selecionado)
    
    if not atividades:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.", icon="ℹ️")
        return
    
    for row in atividades:
        # Desempacotamento seguro com 28 variáveis
        (id_atividade, cnpj, razao_social, olaiseto_folio, tributacao, emp_resp, responsavel, atividade, 
         grupo, cidade, desde, status, email, tel, contato, folha, financeiro, contas, entrega, 
         emp_admin, protesto, parcela, contrato, saldo, extrato, data_criacao, mes_ref, feito) = row
        
        with st.expander(f"{'✅' if feito else '📌'} {razao_social} - {atividade} ({mes_ref})"):
            st.markdown(f'<div class="card{" completed" if feito else ""}">', unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**Responsável:** {responsavel} | **CNPJ:** {cnpj}")
                st.markdown(f"**Tributação:** {tributacao} | **Status:** {status}")
                st.markdown(f"**Contato:** {contato} ({tel} / {email})")
                st.markdown(f"**Data de Criação:** {datetime.strptime(data_criacao, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')}")
            with c2:
                st.checkbox("Concluído", value=bool(feito), key=f"feito_{id_atividade}", on_change=marcar_feito, args=(id_atividade, not feito))
                if st.button("Excluir", key=f"del_{id_atividade}", use_container_width=True):
                    if excluir_atividade(id_atividade):
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def mostrar_indicadores():
    """Exibe os indicadores de entrega."""
    st.markdown('<div class="header">📊 Indicadores de Entrega</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📅 Por Mês", "👤 Por Responsável", "📋 Entregas Gerais"])
    
    with st.spinner("Carregando dados..."):
        data_inicio = datetime.now() - relativedelta(months=3)
        data_fim = datetime.now()
        
        # Converte para string no formato que o SQLite espera para BETWEEN
        data_inicio_str = data_inicio.strftime('%Y-%m-%d 00:00:00')
        data_fim_str = data_fim.strftime('%Y-%m-%d 23:59:59')

        with tab1:
            st.subheader("Entregas por Mês")
            query_mes = '''
                SELECT mes_referencia, SUM(feito) as concluidas, COUNT(*) as total
                FROM atividades WHERE data_criacao BETWEEN ? AND ?
                GROUP BY mes_referencia ORDER BY SUBSTR(mes_referencia, 4) || SUBSTR(mes_referencia, 1, 2)
            '''
            dados_mes = get_dataframe(query_mes, (data_inicio_str, data_fim_str))
            if not dados_mes.empty:
                fig = px.bar(dados_mes, x='mes_referencia', y=['concluidas', 'total'], barmode='group', labels={'value': 'Quantidade'})
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("Entregas por Responsável")
            query_resp = '''
                SELECT responsavel, SUM(feito) as concluidas, COUNT(*) as total, (SUM(feito) * 100.0 / COUNT(*)) as percentual
                FROM atividades WHERE data_criacao BETWEEN ? AND ?
                GROUP BY responsavel ORDER BY percentual DESC
            '''
            dados_resp = get_dataframe(query_resp, (data_inicio_str, data_fim_str))
            if not dados_resp.empty:
                fig = px.bar(dados_resp, x='percentual', y='responsavel', orientation='h', text='percentual', color='percentual', color_continuous_scale='Greens')
                fig.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("Tabela de Entregas Gerais")
            # Consulta corrigida para usar nomes de coluna válidos
            query_geral = '''
                SELECT 
                    cnpj AS "CNPJ", razao_social AS "Razão Social", olaiseto_folio_cliente AS "Folio Cliente",
                    tributacao AS "Tributação", empresa_responsavel AS "Empresa Resp.", responsavel AS "Responsável",
                    atividade AS "Atividade", grupo AS "Grupo", cidade AS "Cidade", desde AS "Desde",
                    status AS "Status", email AS "E-MAIL", telefone AS "Telefone", contato AS "Contato",
                    possui_folha AS "Possui Folha", financeiro AS "Financeiro", 
                    quadro_contas_bancarias AS "Nº Contas", forma_entrega AS "Forma Entrega",
                    empresa_administrada AS "Empresa Admin.", protesta_no_bancario AS "Protesto Bancário",
                    parcela_perto AS "Parcela Perto", contrato AS "Contrato", saldo_anterior AS "Saldo Anterior",
                    extrato AS "Extrato", data_criacao AS "Data Criação"
                FROM atividades WHERE data_criacao BETWEEN ? AND ? ORDER BY data_criacao DESC
            '''
            dados_gerais = get_dataframe(query_geral, (data_inicio_str, data_fim_str))
            if not dados_gerais.empty:
                st.dataframe(dados_gerais, use_container_width=True, height=600)

def mostrar_sidebar():
    """Exibe a barra lateral com estatísticas e logout."""
    with st.sidebar:
        st.markdown("## Configurações")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Estatísticas Rápidas")
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                total = c.execute("SELECT COUNT(*) FROM atividades").fetchone()[0]
                concluidas = c.execute("SELECT COUNT(*) FROM atividades WHERE feito = 1").fetchone()[0]
                percentual = (concluidas / total * 100) if total > 0 else 0
                st.markdown(f"""
                    <div class="sidebar-metric-label">Total de Atividades: <b>{total}</b></div>
                    <div class="sidebar-metric-label">Concluídas: <b>{concluidas} ({percentual:.1f}%)</b></div>
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
        mostrar_sidebar()
        st.markdown('<div class="title">Painel de Atividades</div>', unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Atividades", "📝 Cadastrar", "📊 Indicadores"])
        
        with tab1:
            lista_atividades()
        with tab2:
            cadastro_atividade()
        with tab3:
            mostrar_indicadores()

if __name__ == "__main__":
    main()
