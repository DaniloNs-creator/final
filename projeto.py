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
        # Usando um timeout maior para evitar problemas de bloqueio
        conn = sqlite3.connect('clientes.db', check_same_thread=False, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL")  # Melhora a concorrência
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
            .main { background: var(--background-gradient); color: var(--dark-color); font-family: 'Segoe UI', sans-serif; }
            .title { color: var(--dark-color); font-size: 2.8rem; font-weight: 800; margin-bottom: 1.5rem; padding-bottom: 0.5rem; background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 2px 2px 4px rgba(0,0,0,0.1); animation: fadeIn 1s ease-in-out; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
            .header { color: var(--dark-color); font-size: 1.8rem; font-weight: 700; margin: 1.5rem 0 1rem 0; padding-left: 10px; border-left: 5px solid var(--primary-color); animation: slideIn 0.5s ease-out; }
            @keyframes slideIn { from { transform: translateX(-20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
            .card { background: white; border-radius: 12px; box-shadow: var(--card-shadow); padding: 1.8rem; margin-bottom: 1.8rem; transition: var(--transition); border: none; animation: popIn 0.4s ease-out; }
            @keyframes popIn { 0% { transform: scale(0.95); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
            .card:hover { transform: translateY(-5px); box-shadow: 0 15px 30px rgba(0,0,0,0.15); }
            .completed { background-color: rgba(46, 204, 113, 0.1); border-left: 5px solid var(--secondary-color); position: relative; overflow: hidden; }
            .completed::after { content: "✓ CONCLUÍDO"; position: absolute; top: 10px; right: -30px; background: var(--secondary-color); color: white; padding: 3px 30px; font-size: 0.7rem; font-weight: bold; transform: rotate(45deg); box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
            [data-testid="stSidebar"] { background: linear-gradient(180deg, var(--dark-color), #34495e) !important; color: white !important; padding: 1.5rem !important; }
            .sidebar-metric-label { color: white !important; font-size: 1rem !important; margin-bottom: 0.5rem !important; }
            .sidebar-metric-value { color: white !important; font-size: 1.5rem !important; font-weight: bold !important; }
            .proxima-entrega { background: white; padding: 10px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); color: black !important; }
            .proxima-entrega strong, .proxima-entrega small { color: black !important; }
            .form-label { font-weight: 600; margin-bottom: 0.5rem; color: var(--dark-color); display: block; position: relative; padding-left: 15px; }
            .form-label::before { content: ""; position: absolute; left: 0; top: 50%; transform: translateY(-50%); width: 8px; height: 8px; background: var(--primary-color); border-radius: 50%; }
            .stButton>button { background: linear-gradient(135deg, var(--primary-color), #2980b9); color: white; font-weight: 600; border: none; border-radius: 8px; padding: 0.7rem 1.5rem; transition: var(--transition); box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; }
            .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 7px 14px rgba(0,0,0,0.15); background: linear-gradient(135deg, #2980b9, var(--primary-color)); }
            .success-message { background-color: rgba(46, 204, 113, 0.2); color: var(--dark-color); padding: 1rem; border-radius: 8px; border-left: 5px solid var(--secondary-color); margin: 1rem 0; animation: fadeIn 0.5s ease-in; }
            .error-message { background-color: rgba(231, 76, 60, 0.2); color: var(--dark-color); padding: 1rem; border-radius: 8px; border-left: 5px solid var(--accent-color); margin: 1rem 0; animation: shake 0.5s ease-in; }
            @keyframes shake { 0%, 100% { transform: translateX(0); } 20%, 60% { transform: translateX(-5px); } 40%, 80% { transform: translateX(5px); } }
            .info-message { background-color: rgba(52, 152, 219, 0.2); color: var(--dark-color); padding: 1rem; border-radius: 8px; border-left: 5px solid var(--primary-color); margin: 1rem 0; animation: fadeIn 0.5s ease-in; }
        </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def update_schema(conn: sqlite3.Connection):
    """Verifica e atualiza o schema da tabela 'atividades' adicionando colunas ausentes."""
    c = conn.cursor()
    c.execute("PRAGMA table_info(atividades)")
    existing_columns = {row[1] for row in c.fetchall()}

    all_columns = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT", "cnpj": "TEXT", "razao_social": "TEXT NOT NULL",
        "olaiseto_folio_cliente": "TEXT", "tributacao": "TEXT NOT NULL", "empresa_responsavel": "TEXT",
        "responsavel": "TEXT NOT NULL", "atividade": "TEXT NOT NULL", "grupo": "TEXT", "cidade": "TEXT",
        "desde": "TEXT", "status": "TEXT", "email": "TEXT", "telefone": "TEXT", "contato": "TEXT",
        "possui_folha": "TEXT", "financeiro": "TEXT", "quadro_contas_bancarias": "INTEGER",
        "forma_entrega": "TEXT", "empresa_administrada": "TEXT", "protesta_no_bancario": "TEXT",
        "parcela_perto": "TEXT", "contrato": "TEXT", "saldo_anterior": "TEXT", "extrato": "TEXT",
        "data_criacao": "TEXT NOT NULL", "mes_referencia": "TEXT", "feito": "INTEGER DEFAULT 0"
    }

    for col_name, col_type in all_columns.items():
        if col_name not in existing_columns:
            try:
                simplified_type = col_type.split(" NOT NULL")[0].split(" PRIMARY KEY")[0]
                c.execute(f"ALTER TABLE atividades ADD COLUMN {col_name} {simplified_type}")
                st.toast(f"Schema atualizado: Coluna '{col_name}' adicionada.", icon="🔧")
            except sqlite3.Error as e:
                st.error(f"Não foi possível adicionar a coluna '{col_name}': {e}")
    conn.commit()

def init_db():
    """Inicializa o banco de dados, criando e atualizando a tabela se necessário."""
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
                contrato TEXT, -- CORRIGIDO
                saldo_anterior TEXT,
                extrato TEXT,
                data_criacao TEXT NOT NULL,
                mes_referencia TEXT,
                feito INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        
        # Garante que a tabela tenha todas as colunas necessárias
        update_schema(conn)

        c.execute("SELECT COUNT(*) FROM atividades")
        if c.fetchone()[0] == 0:
            gerar_atividades_iniciais(conn)

def gerar_atividades_iniciais(conn: sqlite3.Connection):
    """Gera algumas atividades iniciais para demonstração."""
    clientes = [
        ("00.000.000/0001-00", "Cliente A", "OL12345", "Simples Nacional", "Empresa A", "Responsável 1"),
        ("11.111.111/0001-11", "Cliente B", "OL67890", "Lucro Presumido", "Empresa B", "Responsável 2"),
    ]
    
    atividades = ["Fechamento mensal", "Relatório contábil", "Conciliação bancária"]
    
    try:
        c = conn.cursor()
        for cliente in clientes:
            campos = (
                cliente[0], cliente[1], cliente[2], cliente[3], cliente[4], cliente[5], random.choice(atividades),
                "Grupo 1", "São Paulo", "01/2020", "Ativo", "email@cliente.com", "(11) 99999-9999", "Contato",
                "Sim", "Em dia", 2, "E-mail", "Empresa Admin", "Não", "Parcela 1", "Contrato 123",
                "R$ 10.000,00", "Disponível", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                datetime.now().strftime('%m/%Y'), random.choice([0, 1])
            )
            # A query INSERT precisa ter o número correto de colunas (27) e placeholders (27)
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
    """Adiciona múltiplas atividades ao banco de dados em lote."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            dados_completos = [
                (*linha, datetime.now().strftime('%Y-%m-%d %H:%M:%S')) for linha in dados
            ]
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

def excluir_atividade(id: int) -> bool:
    """Remove uma atividade do banco de dados pelo ID."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM atividades WHERE id = ?', (id,))
            conn.commit()
            return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao excluir atividade: {e}")
        return False

def marcar_feito(id: int, feito: bool):
    """Atualiza o status de conclusão de uma atividade."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE atividades SET feito = ? WHERE id = ?', (int(feito), id))
            conn.commit()
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar status: {e}")

def get_atividades(filtro_mes: str = None, filtro_responsavel: str = None) -> List[Tuple]:
    """Retorna todas as atividades com filtros opcionais."""
    try:
        with get_db_connection() as conn:
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
            return conn.cursor().execute(query, tuple(params)).fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar atividades: {e}")
        return []

def get_responsaveis() -> List[str]:
    """Retorna a lista de responsáveis únicos."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT DISTINCT responsavel FROM atividades WHERE responsavel IS NOT NULL ORDER BY responsavel')
            return ["Todos"] + [row[0] for row in c.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar responsáveis: {e}")
        return ["Todos"]

def get_dados_indicadores(data_inicio: str, data_fim: str) -> pd.DataFrame:
    """Retorna dados para os indicadores de entrega."""
    try:
        with get_db_connection() as conn:
            query = '''
                SELECT mes_referencia, SUM(feito) as concluidas, COUNT(*) as total
                FROM atividades WHERE data_criacao BETWEEN ? AND ?
                GROUP BY mes_referencia
                ORDER BY SUBSTR(mes_referencia, 4) || SUBSTR(mes_referencia, 1, 2)
            '''
            df = pd.read_sql(query, conn, params=(data_inicio, data_fim))
            if not df.empty:
                df['percentual'] = (df['concluidas'] / df['total'] * 100).round(2)
            return df
    except Exception as e:
        st.error(f"Erro ao gerar indicadores: {e}")
        return pd.DataFrame()

def get_dados_responsaveis(data_inicio: str, data_fim: str) -> pd.DataFrame:
    """Retorna dados para análise por responsável."""
    try:
        with get_db_connection() as conn:
            query = '''
                SELECT responsavel, SUM(feito) as concluidas, COUNT(*) as total
                FROM atividades WHERE data_criacao BETWEEN ? AND ?
                GROUP BY responsavel ORDER BY total DESC
            '''
            df = pd.read_sql(query, conn, params=(data_inicio, data_fim))
            if not df.empty:
                df['percentual'] = (df['concluidas'] / df['total'] * 100).round(2)
            return df
    except Exception as e:
        st.error(f"Erro ao gerar dados por responsável: {e}")
        return pd.DataFrame()

def get_entregas_gerais(data_inicio: str, data_fim: str) -> pd.DataFrame:
    """Retorna dados para a tabela de entregas gerais."""
    try:
        with get_db_connection() as conn:
            query = '''
                SELECT 
                    cnpj AS "CNPJ",
                    razao_social AS "Razão Social",
                    olaiseto_folio_cliente AS "Folio Cliente",
                    tributacao AS "Tributação",
                    responsavel AS "Responsável",
                    atividade AS "Atividade",
                    status AS "Status",
                    mes_referencia AS "Mês Referência",
                    data_criacao AS "Data Criação",
                    CASE WHEN feito = 1 THEN 'Sim' ELSE 'Não' END AS "Concluído",
                    grupo AS "Grupo",
                    cidade AS "Cidade",
                    email AS "E-mail",
                    telefone AS "Telefone"
                FROM atividades
                WHERE data_criacao BETWEEN ? AND ?
                ORDER BY data_criacao DESC
            '''
            return pd.read_sql(query, conn, params=(data_inicio, data_fim))
    except Exception as e:
        st.error(f"Erro ao gerar dados de entregas gerais: {e}")
        return pd.DataFrame()

# --- COMPONENTES DA INTERFACE ---
def login_section():
    """Exibe a seção de login."""
    st.markdown('<div class="title">Carteira de Clientes - Painel de Atividades</div>', unsafe_allow_html=True)
    with st.form("login_form"):
        col1, col2 = st.columns(2)
        username = col1.text_input("Usuário", key="username", placeholder="admin")
        password = col2.text_input("Senha", type="password", key="password", placeholder="reali")
        if st.form_submit_button("Entrar", use_container_width=True):
            if username == "admin" and password == "reali":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciais inválidas. Tente novamente.", icon="⚠️")

def upload_atividades():
    """Exibe o formulário para upload de atividades em Excel."""
    st.markdown('<p class="header">📤 Upload de Atividades em Lote</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Selecione um arquivo Excel (.xlsx)", type=["xlsx"])
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.markdown("**Pré-visualização dos dados:**")
            st.dataframe(df.head())
            
            # Mapeamento flexível de colunas
            col_map = {
                'cnpj': ['CNPJ'], 'razao_social': ['Razão Social', 'RAZAO SOCIAL'],
                'olaiseto_folio_cliente': ['OLAISETO FOLIO DO CLIENTE', 'Folio'],
                'tributacao': ['Tributação', 'TRIBUTACAO'], 'responsavel': ['Responsável', 'RESPONSAVEL'],
                'atividade': ['Atividade', 'ATIVIDADE'], 'mes_referencia': ['Mês Referência', 'MES REFERENCIA']
            }
            
            # Normalizar nomes das colunas do DataFrame
            df.columns = df.columns.str.strip()
            
            # Preparar dados para inserção
            atividades = []
            for _, row in df.iterrows():
                # Função auxiliar para obter valor da linha com nomes de coluna flexíveis
                def get_val(key, default=''):
                    for name in col_map.get(key, []):
                        if name in row and pd.notna(row[name]):
                            return row[name]
                    return default

                atividades.append((
                    get_val('cnpj'), get_val('razao_social'), get_val('olaiseto_folio_cliente'),
                    get_val('tributacao', 'Simples Nacional'), row.get('Empresa Responsável', ''), get_val('responsavel'),
                    get_val('atividade', 'Atividade em lote'), row.get('Grupo', ''), row.get('Cidade', ''),
                    datetime.now().strftime('%Y-%m-%d'), 'Ativo', row.get('E-mail', ''), row.get('Telefone', ''),
                    row.get('Contato', ''), 'Sim', 'Em dia', 1, 'E-mail', '', 'Não', '',
                    get_val('contrato', ''), '', '', get_val('mes_referencia', datetime.now().strftime('%m/%Y'))
                ))

            if st.button("Confirmar Importação", type="primary", use_container_width=True):
                if adicionar_atividades_em_lote(atividades):
                    st.success(f"✅ {len(atividades)} atividades importadas com sucesso!")
                    st.rerun()
                else:
                    st.error("Ocorreu um erro ao importar as atividades.")
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")

def cadastro_atividade_form():
    """Exibe o formulário para cadastro manual."""
    with st.form("nova_atividade", clear_on_submit=True):
        st.markdown('<p class="form-label">Informações do Cliente e Atividade</p>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        razao_social = col1.text_input("Razão Social*")
        cnpj = col2.text_input("CNPJ")
        responsavel = col3.text_input("Responsável*")
        
        col4, col5, col6 = st.columns(3)
        atividade = col4.text_input("Atividade*")
        tributacao = col5.selectbox("Tributação*", ["Simples Nacional", "Lucro Presumido", "Lucro Real"])
        mes_referencia = col6.selectbox("Mês de Referência*", [f"{m:02d}/{a}" for a in range(2023, 2027) for m in range(1, 13)])
        
        with st.expander("Mais detalhes (opcional)"):
            c1, c2, c3 = st.columns(3)
            olaiseto_folio = c1.text_input("OLAISETO FOLIO")
            status = c2.selectbox("Status", ["Ativo", "Inativo", "Potencial"])
            contrato = c3.text_input("Contrato")

        if st.form_submit_button("Adicionar Atividade", use_container_width=True, type="primary"):
            if all([razao_social, responsavel, atividade]):
                campos = (
                    cnpj, razao_social, olaiseto_folio, tributacao, '', responsavel, atividade, '', '',
                    datetime.now().strftime('%Y-%m-%d'), status, '', '', '', 'Sim', 'Em dia', 1,
                    'E-mail', '', 'Não', '', contrato, '', '', mes_referencia
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
    meses = sorted(set([f"{m:02d}/{a}" for a in range(2023, 2027) for m in range(1, 13)]), reverse=True)
    mes_selecionado = col1.selectbox("Filtrar por mês:", ["Todos"] + meses)
    responsavel_selecionado = col2.selectbox("Filtrar por responsável:", get_responsaveis())
    
    atividades = get_atividades(mes_selecionado, responsavel_selecionado)
    
    if not atividades:
        st.info("Nenhuma atividade encontrada para os filtros selecionados.", icon="ℹ️")
        return
    
    for row in atividades:
        # O unpack agora corresponde às 28 colunas da tabela
        (id, cnpj, razao_social, _, _, _, responsavel, atividade, _, _, _, status, _, _, _, _, _, _, _, _, _, _, contrato, _, _, data_criacao, mes_referencia, feito) = row
        
        container_class = "card completed" if feito else "card"
        expander_title = f"{'✅' if feito else '📌'} {razao_social} - {atividade} ({mes_referencia})"
        
        with st.expander(expander_title):
            st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**Responsável:** {responsavel} | **Status:** {status}")
                st.markdown(f"**CNPJ:** {cnpj or 'N/A'} | **Contrato:** {contrato or 'N/A'}")
                st.markdown(f"<small>Criado em: {datetime.strptime(data_criacao, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')}</small>", unsafe_allow_html=True)
            with c2:
                st.checkbox("Concluído", bool(feito), key=f"feito_{id}", on_change=marcar_feito, args=(id, not feito))
                if st.button("Excluir", key=f"del_{id}", use_container_width=True, type="secondary"):
                    if excluir_atividade(id):
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def mostrar_indicadores():
    """Exibe os indicadores de entrega."""
    st.markdown('<div class="header">📊 Indicadores de Desempenho</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📅 Por Mês", "👤 Por Responsável", "📋 Tabela Geral"])
    
    hoje = datetime.now()
    data_inicio_default = hoje - relativedelta(months=3)
    
    with tab1:
        c1, c2 = st.columns(2)
        data_inicio = c1.date_input("Data Início", data_inicio_default, key="d1_mes")
        data_fim = c2.date_input("Data Fim", hoje, key="d2_mes")
        dados = get_dados_indicadores(data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d 23:59:59'))
        if dados.empty:
            st.warning("Não há dados no período selecionado.")
        else:
            fig = px.bar(dados, x='mes_referencia', y=['concluidas', 'total'], barmode='group',
                         labels={'value': 'Quantidade', 'mes_referencia': 'Mês'},
                         color_discrete_map={'concluidas': '#2ecc71', 'total': '#3498db'})
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        c1, c2 = st.columns(2)
        data_inicio = c1.date_input("Data Início", data_inicio_default, key="d1_resp")
        data_fim = c2.date_input("Data Fim", hoje, key="d2_resp")
        dados = get_dados_responsaveis(data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d 23:59:59'))
        if dados.empty:
            st.warning("Não há dados no período selecionado.")
        else:
            fig = px.bar(dados, y='responsavel', x='percentual', orientation='h', text='percentual',
                         labels={'percentual': '% Conclusão', 'responsavel': 'Responsável'},
                         color='percentual', color_continuous_scale='Greens')
            fig.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        c1, c2 = st.columns(2)
        data_inicio = c1.date_input("Data Início", data_inicio_default, key="d1_geral")
        data_fim = c2.date_input("Data Fim", hoje, key="d2_geral")
        dados = get_entregas_gerais(data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d 23:59:59'))
        if dados.empty:
            st.warning("Não há dados no período selecionado.")
        else:
            st.dataframe(dados, use_container_width=True, height=600)

def mostrar_sidebar():
    """Exibe a barra lateral com estatísticas e logout."""
    with st.sidebar:
        st.markdown("## Painel de Controle")
        if st.button("🚪 Sair", use_container_width=True, type="primary"):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown("---")
        st.markdown("### Estatísticas Gerais")
        try:
            with get_db_connection() as conn:
                total = conn.cursor().execute("SELECT COUNT(*) FROM atividades").fetchone()[0]
                concluidas = conn.cursor().execute("SELECT COUNT(*) FROM atividades WHERE feito = 1").fetchone()[0]
                percentual = (concluidas / total * 100) if total > 0 else 0
                st.markdown(f'<div class="sidebar-metric-label">Total de Atividades</div><div class="sidebar-metric-value">{total}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sidebar-metric-label">Concluídas</div><div class="sidebar-metric-value">{concluidas} ({percentual:.1f}%)</div>', unsafe_allow_html=True)
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
        
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Atividades", "📝 Cadastrar / Importar", "📊 Indicadores"])
        
        with tab1:
            lista_atividades()
        
        with tab2:
            st.markdown('<div class="header">📝 Cadastro de Atividade Manual</div>', unsafe_allow_html=True)
            cadastro_atividade_form()
            st.markdown("---")
            upload_atividades()
        
        with tab3:
            mostrar_indicadores()

if __name__ == "__main__":
    main()
