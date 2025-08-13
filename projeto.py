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
            campos = (
                cliente[0], cliente[1], cliente[2], cliente[3], cliente[4], atividade,
                "Grupo 1", "São Paulo", "01/2020", "Ativo", "email@cliente.com", "(11) 99999-9999", "Contato Financeiro",
                "Sim", "Em dia", 2, "E-mail", hoje.strftime('%Y-%m-%d'), mes_ref
            )
            
            c.execute('''
                INSERT INTO atividades (
                    cliente, razao_social, classificacao, tributacao, responsavel, atividade, 
                    grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                    financeiro, contas_bancarias, forma_entrega, data_entrega, data_criacao, mes_referencia
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', campos + (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
        
        hoje += timedelta(days=30)  # Aproximadamente 1 mês
    
    conn.commit()

# --- FUNÇÕES DO SISTEMA ---
def adicionar_atividade(conn: sqlite3.Connection, campos: Tuple) -> bool:
    """Adiciona uma nova atividade ao banco de dados."""
    try:
        c = conn.cursor()
        campos_completos = campos + (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), campos[8])  # data_criacao e mes_referencia
        c.execute('''
            INSERT INTO atividades (
                cliente, razao_social, classificacao, tributacao, responsavel, atividade, 
                grupo, cidade, desde, status, email, telefone, contato, possui_folha, 
                financeiro, contas_bancarias, forma_entrega, data_entrega, data_criacao, mes_referencia
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

def get_atividades(conn: sqlite3.Connection, filtro_mes: str = None) -> List[Tuple]:
    """Retorna todas as atividades ordenadas por data de criação."""
    try:
        c = conn.cursor()
        if filtro_mes:
            c.execute('SELECT * FROM atividades WHERE mes_referencia = ? ORDER BY data_criacao DESC', (filtro_mes,))
        else:
            c.execute('SELECT * FROM atividades ORDER BY data_criacao DESC')
        return c.fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar atividades: {e}")
        return []

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
        
        mes_referencia = st.selectbox("Mês de Referência", [
            f"{mes:02d}/{ano}" 
            for ano in range(2023, 2026) 
            for mes in range(1, 13)
        ])
        
        st.markdown("<small>Campos marcados com * são obrigatórios</small>", unsafe_allow_html=True)
        
        if st.form_submit_button("Adicionar Atividade", use_container_width=True):
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
    """Exibe a lista de atividades cadastradas."""
    st.markdown('<div class="header">📋 Lista de Atividades</div>', unsafe_allow_html=True)
    
    # Filtro por mês de referência
    meses = sorted(set(
        f"{mes:02d}/{ano}" 
        for ano in range(2023, 2026) 
        for mes in range(1, 13)
    ), reverse=True)
    
    mes_selecionado = st.selectbox("Filtrar por mês de referência:", ["Todos"] + meses)
    
    if mes_selecionado == "Todos":
        atividades = get_atividades(conn)
    else:
        atividades = get_atividades(conn, mes_selecionado)
    
    if not atividades:
        st.info("Nenhuma atividade cadastrada ainda.", icon="ℹ️")
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
        container_class = "completed" if feito else ""
        
        # Cartão de atividade
        with st.expander(f"{'✅' if feito else '📌'} {cliente} - {atividade} ({status}) - {mes_referencia}", expanded=False):
            st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
            
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
    st.markdown('<div class="header">📊 Indicadores de Entrega</div>', unsafe_allow_html=True)
    
    dados = get_dados_indicadores(conn)
    
    if dados.empty:
        st.warning("Não há dados suficientes para exibir os indicadores.")
        return
    
    # Gráfico de barras - Entregas por mês
    st.subheader("Entregas por Mês")
    fig_bar = px.bar(
        dados,
        x='mes_referencia',
        y=['concluidas', 'total'],
        barmode='group',
        labels={'value': 'Quantidade', 'mes_referencia': 'Mês de Referência'},
        color_discrete_map={'concluidas': '#2ecc71', 'total': '#3498db'}
    )
    fig_bar.update_layout(showlegend=True, legend_title_text='')
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Gráfico de rosca - Percentual de conclusão
    st.subheader("Percentual de Conclusão")
    fig_pie = px.pie(
        dados,
        values='percentual',
        names='mes_referencia',
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Greens
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Tabela com os dados detalhados
    st.subheader("Detalhamento por Mês")
    dados['percentual'] = dados['percentual'].round(2)
    st.dataframe(
        dados[['mes_referencia', 'concluidas', 'total', 'percentual']]
        .rename(columns={
            'mes_referencia': 'Mês',
            'concluidas': 'Concluídas',
            'total': 'Total',
            'percentual': '% Conclusão'
        }),
        use_container_width=True
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
        # Menu principal com abas
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Atividades", "📝 Cadastrar Atividades", "📊 Indicadores de Entrega"])
        
        with tab1:
            lista_atividades(conn)
        
        with tab2:
            cadastro_atividade(conn)
        
        with tab3:
            mostrar_indicadores(conn)
        
        # Botão de logout na sidebar
        st.sidebar.markdown("---")
        if st.sidebar.button("Sair", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

if __name__ == "__main__":
    main()
