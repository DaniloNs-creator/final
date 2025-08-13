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
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS ANIMADO E ESTILIZADO ---
def load_css():
    st.markdown("""
        <style>
            :root {
                --primary-color: #3498db;
                --secondary-color: #2ecc71;
                --dark-color: #2c3e50;
                --light-color: #ecf0f1;
                --danger-color: #e74c3c;
                --warning-color: #f39c12;
                --info-color: #1abc9c;
                --background-color: #f9f9f9;
                --card-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                --transition-speed: 0.3s;
            }
            
            .main {
                background-color: var(--background-color);
                color: var(--dark-color);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            /* Animação de entrada */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .animated {
                animation: fadeIn 0.5s ease-out forwards;
            }
            
            /* Títulos */
            .main-title {
                color: var(--dark-color);
                font-size: 2.8rem;
                font-weight: 700;
                margin-bottom: 1.5rem;
                padding-bottom: 0.8rem;
                border-bottom: 3px solid var(--primary-color);
                position: relative;
                animation-delay: 0.1s;
            }
            
            .main-title::after {
                content: '';
                position: absolute;
                bottom: -3px;
                left: 0;
                width: 50%;
                height: 3px;
                background: var(--secondary-color);
                transition: width var(--transition-speed) ease;
            }
            
            .main-title:hover::after {
                width: 100%;
            }
            
            .section-title {
                color: var(--dark-color);
                font-size: 1.8rem;
                font-weight: 600;
                margin: 1.8rem 0 1.2rem 0;
                padding-left: 0.5rem;
                border-left: 4px solid var(--primary-color);
                transition: all var(--transition-speed);
            }
            
            .section-title:hover {
                border-left: 4px solid var(--secondary-color);
                padding-left: 1rem;
            }
            
            /* Cards */
            .card {
                background: white;
                border-radius: 12px;
                box-shadow: var(--card-shadow);
                padding: 1.8rem;
                margin-bottom: 1.8rem;
                transition: all var(--transition-speed);
                border: 1px solid rgba(0, 0, 0, 0.05);
            }
            
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
            }
            
            .completed {
                background: linear-gradient(135deg, #f8fff8 0%, #e8f5e9 100%);
                border-left: 5px solid var(--secondary-color);
            }
            
            /* Formulários */
            .form-label {
                font-weight: 600;
                margin-bottom: 0.6rem;
                color: var(--dark-color);
                display: block;
                transition: all var(--transition-speed);
            }
            
            /* Botões */
            .stButton>button {
                background: linear-gradient(135deg, var(--primary-color) 0%, #2980b9 100%);
                color: white;
                font-weight: 600;
                border: none;
                border-radius: 8px;
                padding: 0.7rem 1.5rem;
                transition: all var(--transition-speed);
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            .stButton>button:hover {
                background: linear-gradient(135deg, var(--secondary-color) 0%, #27ae60 100%);
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }
            
            .danger-button>button {
                background: linear-gradient(135deg, var(--danger-color) 0%, #c0392b 100%);
            }
            
            .danger-button>button:hover {
                background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            }
            
            /* Inputs */
            .stTextInput>div>div>input, 
            .stSelectbox>div>div>select,
            .stDateInput>div>div>input,
            .stNumberInput>div>div>input {
                background-color: white;
                border: 1px solid #dfe6e9;
                border-radius: 8px;
                padding: 0.7rem 1rem;
                transition: all var(--transition-speed);
                box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05);
            }
            
            .stTextInput>div>div>input:focus, 
            .stSelectbox>div>div>select:focus,
            .stDateInput>div>div>input:focus {
                border-color: var(--primary-color);
                box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
            }
            
            /* Mensagens */
            .success-message {
                background-color: rgba(46, 204, 113, 0.1);
                color: var(--secondary-color);
                font-weight: 600;
                padding: 1rem;
                border-radius: 8px;
                border-left: 4px solid var(--secondary-color);
            }
            
            .error-message {
                background-color: rgba(231, 76, 60, 0.1);
                color: var(--danger-color);
                font-weight: 600;
                padding: 1rem;
                border-radius: 8px;
                border-left: 4px solid var(--danger-color);
            }
            
            .info-message {
                background-color: rgba(52, 152, 219, 0.1);
                color: var(--primary-color);
                font-weight: 600;
                padding: 1rem;
                border-radius: 8px;
                border-left: 4px solid var(--primary-color);
            }
            
            /* Sidebar */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, var(--dark-color) 0%, #34495e 100%);
                color: white;
            }
            
            .sidebar .sidebar-content {
                background: transparent;
            }
            
            /* Tabs */
            .stTabs [role="tablist"] {
                gap: 0.5rem;
                margin-bottom: 1.5rem;
            }
            
            .stTabs [role="tab"] {
                padding: 0.7rem 1.5rem;
                border-radius: 8px;
                background-color: #f1f5f9;
                color: var(--dark-color);
                transition: all var(--transition-speed);
                border: none;
                font-weight: 600;
            }
            
            .stTabs [role="tab"]:hover {
                background-color: #e2e8f0;
                color: var(--primary-color);
            }
            
            .stTabs [aria-selected="true"] {
                background: linear-gradient(135deg, var(--primary-color) 0%, #2980b9 100%);
                color: white;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            /* Progresso */
            .progress-container {
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
                margin: 0.5rem 0;
                overflow: hidden;
            }
            
            .progress-bar {
                height: 100%;
                background: linear-gradient(90deg, var(--secondary-color) 0%, var(--primary-color) 100%);
                border-radius: 4px;
                transition: width 0.6s ease;
            }
            
            /* Efeito de hover nos cards de atividade */
            .activity-card {
                transition: all var(--transition-speed);
                cursor: pointer;
            }
            
            .activity-card:hover {
                transform: scale(1.02);
            }
            
            /* Responsividade */
            @media (max-width: 768px) {
                .main-title {
                    font-size: 2rem;
                }
                
                .section-title {
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
            data_criacao TEXT NOT NULL,
            mes_referencia TEXT
        )
    ''')
    conn.commit()
    
    # Gerar atividades mensais até 12/2025 se a tabela estiver vazia
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
            feito = random.choice([0, 1])  # Adiciona aleatoriamente atividades concluídas
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
        
        hoje += timedelta(days=30)  # Aproximadamente 1 mês
    
    conn.commit()

# --- FUNÇÕES DO SISTEMA ---
def adicionar_atividade(conn: sqlite3.Connection, campos: Tuple) -> bool:
    """Adiciona uma nova atividade ao banco de dados."""
    try:
        c = conn.cursor()
        campos_completos = campos + (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),)  # Adiciona data_criacao
        
        c.execute('''
            INSERT INTO atividades (
                cliente, razao_social, classificacao, tributacao, responsavel, atividade, 
                grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                financeiro, contas_bancarias, forma_entrega, data_entrega, mes_referencia, data_criacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    st.markdown('<div class="main-title animated">Carteira de Clientes - Painel de Atividades</div>', unsafe_allow_html=True)
    
    with st.container():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image("https://via.placeholder.com/300x150?text=Company+Logo", width=200)
        with col2:
            st.markdown("""
                <div style="margin-top: 1.5rem;">
                    <h3 style="color: #2c3e50;">Gestão completa da carteira de clientes</h3>
                    <p style="color: #7f8c8d;">Acompanhe todas as atividades e indicadores em um só lugar</p>
                </div>
            """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.markdown('<div class="section-title">🔒 Acesso ao Sistema</div>', unsafe_allow_html=True)
        
        username = st.text_input("Usuário", placeholder="Digite seu nome de usuário", key="username")
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha", key="password")
        
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            login_button = st.form_submit_button("Entrar", use_container_width=True)
        with col2:
            st.form_submit_button("Esqueci minha senha", use_container_width=True)
        
        if login_button:
            if username == "admin" and password == "reali":
                st.session_state.logged_in = True
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Credenciais inválidas. Tente novamente.", icon="⚠️")

def cadastro_atividade(conn: sqlite3.Connection):
    """Exibe o formulário para cadastro de novas atividades."""
    st.markdown('<div class="section-title animated">📝 Cadastro de Atividades</div>', unsafe_allow_html=True)
    
    with st.form("nova_atividade", clear_on_submit=True):
        with st.container():
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="form-label">Informações Básicas</div>', unsafe_allow_html=True)
                cliente = st.text_input("Cliente*", placeholder="Nome do cliente", key="cliente")
                razao_social = st.text_input("Razão Social", placeholder="Razão social completa", key="razao_social")
                classificacao = st.selectbox("Classificação", ["A", "B", "C", "D"], key="classificacao")
                tributacao = st.selectbox("Tributação", ["Simples Nacional", "Lucro Presumido", "Lucro Real"], key="tributacao")
                responsavel = st.text_input("Responsável*", placeholder="Nome do responsável", key="responsavel")
                atividade = st.text_input("Atividade*", placeholder="Descrição da atividade", key="atividade")
                
            with col2:
                st.markdown('<div class="form-label">Informações Adicionais</div>', unsafe_allow_html=True)
                grupo = st.text_input("Grupo", placeholder="Grupo do cliente", key="grupo")
                cidade = st.text_input("Cidade", placeholder="Cidade do cliente", key="cidade")
                desde = st.date_input("Cliente desde", value=datetime.now(), key="desde")
                status = st.selectbox("Status", ["Ativo", "Inativo", "Potencial", "Perdido"], key="status")
                email = st.text_input("E-mail", placeholder="E-mail de contato", key="email")
                telefone = st.text_input("Telefone", placeholder="Telefone de contato", key="telefone")
        
        st.markdown('<div class="form-label">Detalhes Financeiros</div>', unsafe_allow_html=True)
        with st.container():
            col3, col4, col5 = st.columns(3)
            
            with col3:
                contato = st.text_input("Contato Financeiro", placeholder="Nome do contato", key="contato")
                possui_folha = st.selectbox("Possui Folha?", ["Sim", "Não", "Não se aplica"], key="possui_folha")
                
            with col4:
                financeiro = st.text_input("Financeiro", placeholder="Informações financeiras", key="financeiro")
                contas_bancarias = st.number_input("Contas Bancárias", min_value=0, value=1, key="contas_bancarias")
                
            with col5:
                forma_entrega = st.selectbox("Forma de Entrega", ["E-mail", "Correio", "Pessoalmente", "Outros"], key="forma_entrega")
                data_entrega = st.date_input("Data de Entrega", value=datetime.now(), key="data_entrega")
        
        mes_referencia = st.selectbox("Mês de Referência", [
            f"{mes:02d}/{ano}" 
            for ano in range(2023, 2026) 
            for mes in range(1, 13)
        ], key="mes_referencia")
        
        st.markdown("<small>Campos marcados com * são obrigatórios</small>", unsafe_allow_html=True)
        
        submitted = st.form_submit_button("Adicionar Atividade", use_container_width=True)
        if submitted:
            if cliente and responsavel and atividade:
                campos = (
                    cliente, razao_social, classificacao, tributacao, responsavel, atividade,
                    grupo, cidade, desde.strftime('%Y-%m-%d'), status, email, telefone, contato,
                    possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega.strftime('%Y-%m-%d'), mes_referencia
                )
                if adicionar_atividade(conn, campos):
                    st.success("Atividade cadastrada com sucesso!", icon="✅")
            else:
                st.error("Preencha os campos obrigatórios!", icon="❌")

def lista_atividades(conn: sqlite3.Connection):
    """Exibe a lista de atividades cadastradas com filtros."""
    st.markdown('<div class="section-title animated">📋 Lista de Atividades</div>', unsafe_allow_html=True)
    
    # Filtros
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            # Filtro por mês de referência
            meses = sorted(set(
                f"{mes:02d}/{ano}" 
                for ano in range(2023, 2026) 
                for mes in range(1, 13)
            ), reverse=True)
            mes_selecionado = st.selectbox("Filtrar por mês de referência:", ["Todos"] + meses, key="filtro_mes")
        
        with col2:
            # Filtro por responsável
            responsaveis = get_responsaveis(conn)
            responsavel_selecionado = st.selectbox("Filtrar por responsável:", responsaveis, key="filtro_responsavel")
    
    # Obter atividades com os filtros aplicados
    atividades = get_atividades(conn, mes_selecionado if mes_selecionado != "Todos" else None,
                              responsavel_selecionado if responsavel_selecionado != "Todos" else None)
    
    if not atividades:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.", icon="ℹ️")
        return
    
    for row in atividades:
        # Verificação segura dos dados
        try:
            (id, cliente, razao_social, classificacao, tributacao, responsavel, 
             atividade, grupo, cidade, desde, status, email, telefone, contato, 
             possui_folha, financeiro, contas_bancarias, forma_entrega, data_entrega, 
             feito, data_criacao, mes_referencia) = row
        except ValueError as e:
            st.error(f"Erro ao processar atividade: {e}")
            continue
        
        # Determina a classe CSS baseada no status
        container_class = "card completed" if feito else "card"
        
        # Cartão de atividade
        with st.expander(f"{'✅' if feito else '📌'} {cliente} - {atividade} ({status}) - {mes_referencia}", expanded=False):
            st.markdown(f'<div class="{container_class} activity-card">', unsafe_allow_html=True)
            
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
            
            st.markdown('</div>', unsafe_allow_html=True)

def mostrar_indicadores(conn: sqlite3.Connection):
    """Exibe os indicadores de entrega."""
    st.markdown('<div class="section-title animated">📊 Indicadores de Entrega</div>', unsafe_allow_html=True)
    
    # Abas para diferentes visualizações
    tab1, tab2 = st.tabs(["📅 Por Mês", "👤 Por Responsável"])
    
    with tab1:
        dados_mes = get_dados_indicadores(conn)
        
        if dados_mes.empty:
            st.warning("Não há dados suficientes para exibir os indicadores por mês.")
        else:
            # Gráfico de barras - Entregas por mês
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
            
            # Gráfico de rosca - Percentual de conclusão
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
                marker=dict(line=dict(color='#fff', width=1))
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Tabela com os dados detalhados
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
            # Gráfico de barras - Entregas por responsável
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
            
            # Gráfico de pizza - Distribuição por responsável
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
                marker=dict(line=dict(color='#fff', width=1))
            )
            fig_pie_resp.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie_resp, use_container_width=True)
            
            # Gráfico de barras horizontais - Performance por responsável
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
                xaxis=dict(showgrid=True, gridcolor='#f1f1f1'),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_hbar, use_container_width=True)
            
            # Tabela com os dados detalhados
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
    
    # Verifica estado de login
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_section()
    else:
        # Sidebar com informações do usuário
        with st.sidebar:
            st.markdown(f"""
                <div style="text-align: center; margin-bottom: 2rem;">
                    <div style="font-size: 1.2rem; font-weight: 600; color: white; margin-bottom: 0.5rem;">
                        Olá, {st.session_state.user}!
                    </div>
                    <div style="color: #bdc3c7; font-size: 0.9rem;">
                        Último acesso: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Menu rápido
            st.markdown("""
                <div style="color: white; font-weight: 600; margin-bottom: 1rem;">
                    🚀 Menu Rápido
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("📋 Lista de Atividades", use_container_width=True):
                st.session_state.current_tab = "📋 Lista de Atividades"
            
            if st.button("📝 Cadastrar Atividade", use_container_width=True):
                st.session_state.current_tab = "📝 Cadastrar Atividades"
            
            if st.button("📊 Visualizar Indicadores", use_container_width=True):
                st.session_state.current_tab = "📊 Indicadores de Entrega"
            
            st.markdown("---")
            
            # Botão de logout
            if st.button("🔒 Sair", use_container_width=True, key="logout_button"):
                st.session_state.logged_in = False
                st.rerun()
        
        # Menu principal com abas
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Atividades", "📝 Cadastrar Atividades", "📊 Indicadores de Entrega"])
        
        with tab1:
            lista_atividades(conn)
        
        with tab2:
            cadastro_atividade(conn)
        
        with tab3:
            mostrar_indicadores(conn)

if __name__ == "__main__":
    main()
