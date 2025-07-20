import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
from sqlite3 import Error

# Configuração inicial da página
st.set_page_config(
    page_title="Controle de Atividades Fiscais Mensais - HÄFELE BRASIL",
    page_icon="📊",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    :root {
        --primary-color: #4a8fe7;
        --secondary-color: #f0f2f6;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
        --dark-color: #343a40;
        --light-color: #f8f9fa;
    }
    
    /* Estilos gerais */
    .stApp {
        background-color: #f5f7fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: var(--dark-color);
        font-weight: 600;
    }
    
    /* Estilo do cabeçalho */
    .header {
        background: linear-gradient(135deg, #4a8fe7 0%, #1e3c72 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .header h1 {
        color: white;
        margin: 0;
    }
    
    /* Estilo dos cards */
    .card {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Estilo dos botões */
    .stButton>button {
        border-radius: 0.5rem;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Estilo dos selects */
    .stSelectbox>div>div>select {
        border-radius: 0.5rem;
        padding: 0.5rem;
    }
    
    /* Estilo das tabelas */
    .stDataFrame {
        border-radius: 0.5rem;
        overflow: hidden;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .status-pendente {
        background-color: #fff3cd;
        color: #856404;
    }
    
    .status-andamento {
        background-color: #cce5ff;
        color: #004085;
    }
    
    .status-finalizado {
        background-color: #d4edda;
        color: #155724;
    }
    
    /* Dificuldade badges */
    .dificuldade-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .dificuldade-baixa {
        background-color: #d4edda;
        color: #155724;
    }
    
    .dificuldade-media {
        background-color: #fff3cd;
        color: #856404;
    }
    
    .dificuldade-alta {
        background-color: #f8d7da;
        color: #721c24;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate-fadeIn {
        animation: fadeIn 0.5s ease-out forwards;
    }
    
    /* Estilo para o expander da tabela */
    .custom-expander .streamlit-expanderHeader {
        font-size: 1.2rem;
        font-weight: 600;
        color: var(--dark-color);
        padding: 0.75rem 1rem;
        background-color: var(--secondary-color);
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .custom-expander .streamlit-expanderContent {
        padding: 1rem;
        background-color: white;
        border-radius: 0 0 0.5rem 0.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .header {
            padding: 1rem;
        }
        
        .card {
            padding: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Banco de dados SQLite
def create_connection():
    conn = None
    try:
        conn = sqlite3.connect('controle_fiscal.db')
        return conn
    except Error as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
    return conn

def initialize_database():
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Tabela de períodos (meses de fechamento)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS periodos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mes INTEGER NOT NULL,
                    ano INTEGER NOT NULL,
                    fechado BOOLEAN NOT NULL DEFAULT 0,
                    data_fechamento TEXT,
                    UNIQUE(mes, ano)
                )
            ''')
            
            # Tabela de atividades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS atividades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    periodo_id INTEGER,
                    obrigacao TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    periodicidade TEXT NOT NULL,
                    orgao_responsavel TEXT NOT NULL,
                    data_limite TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dificuldade TEXT NOT NULL,
                    prazo TEXT NOT NULL,
                    data_inicio TEXT,
                    data_conclusao TEXT,
                    FOREIGN KEY (periodo_id) REFERENCES periodos (id),
                    UNIQUE(periodo_id, obrigacao)
                )
            ''')
            
            conn.commit()
            
            # Verificar se já existem períodos cadastrados
            cursor.execute("SELECT COUNT(*) FROM periodos")
            if cursor.fetchone()[0] == 0:
                # Inserir o período atual se não existir
                now = datetime.now()
                mes_atual = now.month
                ano_atual = now.year
                
                # Inserir os últimos 3 meses e os próximos 2 meses para exemplo
                for i in range(-3, 3):
                    delta = timedelta(days=30*i)
                    data = now + delta
                    mes = data.month
                    ano = data.year
                    
                    cursor.execute(
                        "INSERT OR IGNORE INTO periodos (mes, ano, fechado) VALUES (?, ?, ?)",
                        (mes, ano, 1 if i < -1 else 0)
                    )
                
                conn.commit()
                
                # Carregar atividades padrão para o período atual
                atividades_padrao = get_default_activities(mes_atual, ano_atual)
                periodo_id = cursor.execute(
                    "SELECT id FROM periodos WHERE mes = ? AND ano = ?", 
                    (mes_atual, ano_atual)
                ).fetchone()[0]
                
                for atividade in atividades_padrao:
                    cursor.execute('''
                        INSERT INTO atividades (
                            periodo_id, obrigacao, descricao, periodicidade, orgao_responsavel,
                            data_limite, status, dificuldade, prazo, data_inicio, data_conclusao
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        periodo_id,
                        atividade['Obrigação'],
                        atividade['Descrição'],
                        atividade['Periodicidade'],
                        atividade['Órgão Responsável'],
                        atividade['Data Limite'],
                        atividade['Status'],
                        atividade['Dificuldade'],
                        atividade['Prazo'].strftime('%Y-%m-%d'),
                        atividade['Data Início'].strftime('%Y-%m-%d') if atividade['Data Início'] else None,
                        atividade['Data Conclusão'].strftime('%Y-%m-%d') if atividade['Data Conclusão'] else None
                    ))
                
                conn.commit()
                
        except Error as e:
            st.error(f"Erro ao inicializar banco de dados: {e}")
        finally:
            conn.close()

def get_default_activities(mes, ano):
    # Ajustar os prazos para o mês/ano especificado
    def ajustar_prazo(dia, meses_adicionais=1):
        try:
            data = datetime(ano, mes, dia) + timedelta(days=30*meses_adicionais)
            return data
        except:
            return datetime(ano, mes, 28) + timedelta(days=30*meses_adicionais)  # Para meses com menos dias
    
    data = [
        {
            "Obrigação": "Sped Fiscal",
            "Descrição": "Entrega do arquivo digital da EFD ICMS/IPI com registros fiscais de entradas, saídas, apuração de ICMS e IPI.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": ajustar_prazo(10),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Apuração do ICMS",
            "Descrição": "Cálculo do ICMS devido no período com base nas operações de entrada e saída.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": ajustar_prazo(10),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Diferencial de Alíquota",
            "Descrição": "Cálculo e recolhimento do DIFAL nas aquisições interestaduais destinadas ao consumo ou ativo imobilizado.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": ajustar_prazo(10),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "GIA-Normal",
            "Descrição": "Declaração mensal com informações do ICMS apurado e recolhido.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": ajustar_prazo(10),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "GIA-ST",
            "Descrição": "Declaração mensal do ICMS-ST devido por substituição tributária.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": ajustar_prazo(10),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Apuração IPI",
            "Descrição": "Cálculo do IPI devido com base nas saídas de produtos industrializados.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Baixa",
            "Prazo": ajustar_prazo(10),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Sped Contribuições",
            "Descrição": "Entrega da EFD Contribuições com dados de PIS e COFINS.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o 10º dia útil do segundo mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": ajustar_prazo(10, 2),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Cálculo PIS COFINS",
            "Descrição": "Apuração dos valores de PIS e COFINS com base na receita bruta.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o 25º dia do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": ajustar_prazo(25),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Preenchimento DARFs",
            "Descrição": "Geração dos DARFs para pagamento de tributos federais (PIS, COFINS, IPI, IRPJ, CSLL).",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o último dia útil do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Baixa",
            "Prazo": ajustar_prazo(30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Preenchimento GR-PR ICMS",
            "Descrição": "Geração da guia de recolhimento do ICMS normal no Paraná.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Baixa",
            "Prazo": ajustar_prazo(10),
            "Data Início": None,
            "Data Conclusão": None
        }
    ]
    return data

# Funções auxiliares
def apply_status_style(status):
    if status == "Pendente":
        return '<span class="status-badge status-pendente">Pendente</span>'
    elif status == "Em Andamento":
        return '<span class="status-badge status-andamento">Em Andamento</span>'
    else:
        return '<span class="status-badge status-finalizado">Finalizado</span>'

def apply_difficulty_style(dificuldade):
    if dificuldade == "Baixa":
        return '<span class="dificuldade-badge dificuldade-baixa">Baixa</span>'
    elif dificuldade == "Média":
        return '<span class="dificuldade-badge dificuldade-media">Média</span>'
    else:
        return '<span class="dificuldade-badge dificuldade-alta">Alta</span>'

def calculate_days_remaining(prazo_str, status):
    if not prazo_str or status == 'Finalizado':
        return None
    
    prazo = datetime.strptime(prazo_str, '%Y-%m-%d')
    hoje = datetime.now()
    return (prazo - hoje).days

def get_periodos():
    conn = create_connection()
    periodos = []
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, mes, ano, fechado, data_fechamento FROM periodos ORDER BY ano, mes")
            periodos = cursor.fetchall()
        except Error as e:
            st.error(f"Erro ao buscar períodos: {e}")
        finally:
            conn.close()
    return periodos

def get_periodo_atual():
    now = datetime.now()
    mes_atual = now.month
    ano_atual = now.year
    
    conn = create_connection()
    periodo = None
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, mes, ano, fechado, data_fechamento FROM periodos WHERE mes = ? AND ano = ?",
                (mes_atual, ano_atual)
            )
            periodo = cursor.fetchone()
        except Error as e:
            st.error(f"Erro ao buscar período atual: {e}")
        finally:
            conn.close()
    return periodo

def get_atividades_por_periodo(periodo_id, status_filter="Todos", dificuldade_filter="Todos", orgao_filter="Todos"):
    conn = create_connection()
    atividades = []
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    id, obrigacao, descricao, periodicidade, orgao_responsavel, 
                    data_limite, status, dificuldade, prazo, data_inicio, data_conclusao
                FROM atividades 
                WHERE periodo_id = ?
            '''
            params = [periodo_id]
            
            # Aplicar filtros
            if status_filter != "Todos":
                query += " AND status = ?"
                params.append(status_filter)
            if dificuldade_filter != "Todos":
                query += " AND dificuldade = ?"
                params.append(dificuldade_filter)
            if orgao_filter != "Todos":
                query += " AND orgao_responsavel = ?"
                params.append(orgao_filter)
            
            cursor.execute(query, params)
            atividades = cursor.fetchall()
        except Error as e:
            st.error(f"Erro ao buscar atividades: {e}")
        finally:
            conn.close()
    
    # Converter para DataFrame
    if atividades:
        df = pd.DataFrame(atividades, columns=[
            'id', 'Obrigação', 'Descrição', 'Periodicidade', 'Órgão Responsável',
            'Data Limite', 'Status', 'Dificuldade', 'Prazo', 'Data Início', 'Data Conclusão'
        ])
        
        # Converter strings de data para datetime
        df['Prazo'] = pd.to_datetime(df['Prazo'])
        df['Data Início'] = pd.to_datetime(df['Data Início'])
        df['Data Conclusão'] = pd.to_datetime(df['Data Conclusão'])
        
        # Calcular dias restantes
        df['Dias Restantes'] = df.apply(
            lambda row: calculate_days_remaining(row['Prazo'].strftime('%Y-%m-%d'), row['Status']), 
            axis=1
        )
        
        return df
    return pd.DataFrame()

def update_atividade_status(atividade_id, novo_status):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            data_atual = datetime.now().strftime('%Y-%m-%d')
            
            if novo_status == "Em Andamento":
                cursor.execute('''
                    UPDATE atividades 
                    SET status = ?, data_inicio = COALESCE(data_inicio, ?)
                    WHERE id = ?
                ''', (novo_status, data_atual, atividade_id))
            elif novo_status == "Finalizado":
                cursor.execute('''
                    UPDATE atividades 
                    SET status = ?, data_conclusao = ?
                    WHERE id = ?
                ''', (novo_status, data_atual, atividade_id))
            else:
                cursor.execute('''
                    UPDATE atividades 
                    SET status = ?
                    WHERE id = ?
                ''', (novo_status, atividade_id))
            
            conn.commit()
            return True
        except Error as e:
            st.error(f"Erro ao atualizar status: {e}")
            return False
        finally:
            conn.close()
    return False

def update_atividade_prazo(atividade_id, novo_prazo):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE atividades 
                SET prazo = ?
                WHERE id = ?
            ''', (novo_prazo.strftime('%Y-%m-%d'), atividade_id))
            
            conn.commit()
            return True
        except Error as e:
            st.error(f"Erro ao atualizar prazo: {e}")
            return False
        finally:
            conn.close()
    return False

def add_nova_atividade(periodo_id, atividade):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO atividades (
                    periodo_id, obrigacao, descricao, periodicidade, orgao_responsavel,
                    data_limite, status, dificuldade, prazo, data_inicio, data_conclusao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                periodo_id,
                atividade['Obrigação'],
                atividade['Descrição'],
                atividade['Periodicidade'],
                atividade['Órgão Responsável'],
                atividade['Data Limite'],
                atividade['Status'],
                atividade['Dificuldade'],
                atividade['Prazo'].strftime('%Y-%m-%d'),
                atividade['Data Início'].strftime('%Y-%m-%d') if atividade['Data Início'] else None,
                atividade['Data Conclusão'].strftime('%Y-%m-%d') if atividade['Data Conclusão'] else None
            ))
            
            conn.commit()
            return True
        except Error as e:
            st.error(f"Erro ao adicionar atividade: {e}")
            return False
        finally:
            conn.close()
    return False

def fechar_periodo(periodo_id):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Verificar se todas as atividades estão finalizadas
            cursor.execute('''
                SELECT COUNT(*) FROM atividades 
                WHERE periodo_id = ? AND status != 'Finalizado'
            ''', (periodo_id,))
            pendentes = cursor.fetchone()[0]
            
            if pendentes > 0:
                return False, f"Ainda existem {pendentes} atividades pendentes ou em andamento."
            
            # Fechar o período atual
            cursor.execute('''
                UPDATE periodos 
                SET fechado = 1, data_fechamento = ?
                WHERE id = ?
            ''', (datetime.now().strftime('%Y-%m-%d'), periodo_id))
            
            # Habilitar o próximo período (se existir)
            cursor.execute('''
                SELECT mes, ano FROM periodos WHERE id = ?
            ''', (periodo_id,))
            mes, ano = cursor.fetchone()
            
            # Calcular próximo mês/ano
            if mes == 12:
                proximo_mes = 1
                proximo_ano = ano + 1
            else:
                proximo_mes = mes + 1
                proximo_ano = ano
            
            # Verificar se o próximo período já existe
            cursor.execute('''
                SELECT id FROM periodos WHERE mes = ? AND ano = ?
            ''', (proximo_mes, proximo_ano))
            proximo_periodo_id = cursor.fetchone()
            
            if not proximo_periodo_id:
                # Criar novo período se não existir
                cursor.execute('''
                    INSERT INTO periodos (mes, ano, fechado) VALUES (?, ?, 0)
                ''', (proximo_mes, proximo_ano))
                
                proximo_periodo_id = cursor.lastrowid
                
                # Adicionar atividades padrão para o novo período
                atividades_padrao = get_default_activities(proximo_mes, proximo_ano)
                for atividade in atividades_padrao:
                    cursor.execute('''
                        INSERT INTO atividades (
                            periodo_id, obrigacao, descricao, periodicidade, orgao_responsavel,
                            data_limite, status, dificuldade, prazo, data_inicio, data_conclusao
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        proximo_periodo_id,
                        atividade['Obrigação'],
                        atividade['Descrição'],
                        atividade['Periodicidade'],
                        atividade['Órgão Responsável'],
                        atividade['Data Limite'],
                        atividade['Status'],
                        atividade['Dificuldade'],
                        atividade['Prazo'].strftime('%Y-%m-%d'),
                        atividade['Data Início'].strftime('%Y-%m-%d') if atividade['Data Início'] else None,
                        atividade['Data Conclusão'].strftime('%Y-%m-%d') if atividade['Data Conclusão'] else None
                    ))
            
            conn.commit()
            return True, "Período fechado com sucesso e próximo mês habilitado."
        except Error as e:
            conn.rollback()
            return False, f"Erro ao fechar período: {e}"
        finally:
            conn.close()
    return False, "Erro ao conectar ao banco de dados."

def formatar_mes_ano(mes, ano):
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    return f"{meses[mes-1]}/{ano}"

# Interface do usuário
def main():
    # Inicializar banco de dados
    initialize_database()
    
    st.markdown('<div class="header animate-fadeIn"><h1>📊 Controle de Atividades Fiscais Mensais - HÄFELE BRASIL</h1></div>', unsafe_allow_html=True)
    
    # Obter período atual
    periodo_atual = get_periodo_atual()
    
    if not periodo_atual:
        st.error("Não foi possível carregar o período atual. Por favor, recarregue a página.")
        return
    
    periodo_id, mes, ano, fechado, data_fechamento = periodo_atual
    
    # Mostrar cabeçalho com informações do período
    st.markdown(f'<div class="card"><h3>Período Atual: {formatar_mes_ano(mes, ano)}</h3></div>', unsafe_allow_html=True)
    
    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Status", ["Todos", "Pendente", "Em Andamento", "Finalizado"])
        with col2:
            dificuldade_filter = st.selectbox("Dificuldade", ["Todos", "Baixa", "Média", "Alta"])
        with col3:
            orgaos = ["Todos"] + list(get_atividades_por_periodo(periodo_id)['Órgão Responsável'].unique())
            orgao_filter = st.selectbox("Órgão Responsável", orgaos)
    
    # Carregar atividades do período atual
    df_atividades = get_atividades_por_periodo(periodo_id, status_filter, dificuldade_filter, orgao_filter)
    
    # Mostrar métricas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Atividades", len(df_atividades))
    with col2:
        st.metric("Pendentes", len(df_atividades[df_atividades['Status'] == "Pendente"]))
    with col3:
        st.metric("Em Andamento", len(df_atividades[df_atividades['Status'] == "Em Andamento"]))
    with col4:
        st.metric("Finalizadas", len(df_atividades[df_atividades['Status'] == "Finalizado"]))
    
    # Gráficos - Agora em um expander
    with st.expander("📈 Análise Gráfica", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Status", "Dificuldade", "Prazo"])
        
        with tab1:
            status_counts = df_atividades['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Quantidade']
            fig_status = px.pie(status_counts, values='Quantidade', names='Status', 
                               title='Distribuição por Status',
                               color='Status',
                               color_discrete_map={'Pendente':'#ffc107', 'Em Andamento':'#007bff', 'Finalizado':'#28a745'})
            st.plotly_chart(fig_status, use_container_width=True)
        
        with tab2:
            dificuldade_counts = df_atividades['Dificuldade'].value_counts().reset_index()
            dificuldade_counts.columns = ['Dificuldade', 'Quantidade']
            fig_dificuldade = px.bar(dificuldade_counts, x='Dificuldade', y='Quantidade', 
                                   title='Distribuição por Nível de Dificuldade',
                                   color='Dificuldade',
                                   color_discrete_map={'Baixa':'#28a745', 'Média':'#ffc107', 'Alta':'#dc3545'})
            st.plotly_chart(fig_dificuldade, use_container_width=True)
        
        with tab3:
            prazo_df = df_atividades.copy()
            prazo_df['Prazo'] = pd.to_datetime(prazo_df['Prazo'])
            prazo_df = prazo_df.sort_values('Prazo')
            prazo_df['Prazo Formatado'] = prazo_df['Prazo'].dt.strftime('%d/%m/%Y')
            
            # Criar datas mínimas para o gráfico de timeline
            prazo_df['Data Início'] = prazo_df['Data Início'].fillna(prazo_df['Prazo'] - timedelta(days=1))
            
            fig_prazo = px.timeline(prazo_df, x_start="Data Início", x_end="Prazo", y="Obrigação", 
                                   color="Status",
                                   title='Linha do Tempo das Atividades',
                                   color_discrete_map={'Pendente':'#ffc107', 'Em Andamento':'#007bff', 'Finalizado':'#28a745'},
                                   hover_name="Obrigação",
                                   hover_data=["Status", "Dificuldade", "Prazo Formatado"])
            fig_prazo.update_yaxes(autorange="reversed")
            fig_prazo.update_layout(showlegend=True)
            st.plotly_chart(fig_prazo, use_container_width=True)
    
    # Tabela de atividades - Agora dentro de um expander
    with st.expander("📋 Lista de Atividades", expanded=True):
        # Formatar DataFrame para exibição
        display_df = df_atividades.copy()
        display_df['Status'] = display_df['Status'].apply(apply_status_style)
        display_df['Dificuldade'] = display_df['Dificuldade'].apply(apply_difficulty_style)
        display_df['Prazo'] = display_df['Prazo'].dt.strftime('%d/%m/%Y')
        display_df['Data Início'] = display_df['Data Início'].apply(
            lambda x: x.strftime('%d/%m/%Y') if not pd.isna(x) else ''
        )
        display_df['Data Conclusão'] = display_df['Data Conclusão'].apply(
            lambda x: x.strftime('%d/%m/%Y') if not pd.isna(x) else ''
        )
        
        # Selecionar colunas para exibição
        cols_to_display = ['Obrigação', 'Descrição', 'Periodicidade', 'Órgão Responsável', 
                          'Data Limite', 'Status', 'Dificuldade', 'Prazo', 'Dias Restantes']
        
        st.write(display_df[cols_to_display].to_html(escape=False, index=False), unsafe_allow_html=True)
    
    # Seção de edição
    with st.expander("✏️ Editar Atividades", expanded=False):
        tab1, tab2 = st.tabs(["Editar Status", "Editar Prazo"])
        
        with tab1:
            st.markdown("**Atualizar Status de Atividade**")
            
            atividades_para_editar = df_atividades['Obrigação'].unique()
            atividade_selecionada = st.selectbox("Selecione a atividade para editar", atividades_para_editar)
            
            atividade_idx = df_atividades[df_atividades['Obrigação'] == atividade_selecionada].index[0]
            atividade_id = df_atividades.loc[atividade_idx, 'id']
            current_status = df_atividades.loc[atividade_idx, 'Status']
            
            col1, col2 = st.columns([1, 3])
            with col1:
                novo_status = st.selectbox("Novo Status", ["Pendente", "Em Andamento", "Finalizado"], 
                                          index=["Pendente", "Em Andamento", "Finalizado"].index(current_status))
            
            if st.button("Atualizar Status"):
                if update_atividade_status(atividade_id, novo_status):
                    st.success(f"✅ Status da atividade '{atividade_selecionada}' atualizado para '{novo_status}'!")
                    # Substitui st.experimental_rerun() por st.rerun()
                    st.rerun()
                else:
                    st.error("⚠️ Erro ao atualizar status. Tente novamente.")
        
        with tab2:
            st.markdown("**Atualizar Prazo de Atividade**")
            
            atividades_para_editar = df_atividades['Obrigação'].unique()
            atividade_selecionada = st.selectbox("Selecione a atividade para editar o prazo", atividades_para_editar)
            
            atividade_idx = df_atividades[df_atividades['Obrigação'] == atividade_selecionada].index[0]
            atividade_id = df_atividades.loc[atividade_idx, 'id']
            current_prazo = df_atividades.loc[atividade_idx, 'Prazo']
            
            novo_prazo = st.date_input("Novo Prazo", value=current_prazo)
            
            if st.button("Atualizar Prazo"):
                if update_atividade_prazo(atividade_id, novo_prazo):
                    st.success(f"✅ Prazo da atividade '{atividade_selecionada}' atualizado para {novo_prazo.strftime('%d/%m/%Y')}!")
                    # Substitui st.experimental_rerun() por st.rerun()
                    st.rerun()
                else:
                    st.error("⚠️ Erro ao atualizar prazo. Tente novamente.")
    
    # Adicionar nova atividade
    with st.expander("➕ Adicionar Nova Atividade", expanded=False):
        with st.form("nova_atividade_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nova_obrigacao = st.text_input("Obrigação*", placeholder="Nome da obrigação fiscal")
                nova_descricao = st.text_area("Descrição*", placeholder="Descrição detalhada da atividade")
                nova_periodicidade = st.selectbox("Periodicidade*", ["Mensal", "Trimestral", "Anual", "Eventual", "Extinta"])
            with col2:
                novo_orgao = st.text_input("Órgão Responsável*", placeholder="Órgão responsável")
                nova_data_limite = st.text_input("Data Limite de Entrega*", placeholder="Ex: Até o dia 10 do mês subsequente")
                novo_status = st.selectbox("Status*", ["Pendente", "Em Andamento", "Finalizado"])
                nova_dificuldade = st.selectbox("Dificuldade*", ["Baixa", "Média", "Alta"])
                novo_prazo = st.date_input("Prazo Final*")
            
            if st.form_submit_button("Adicionar Atividade"):
                if nova_obrigacao and nova_descricao and novo_orgao and nova_data_limite:
                    nova_atividade = {
                        "Obrigação": nova_obrigacao,
                        "Descrição": nova_descricao,
                        "Periodicidade": nova_periodicidade,
                        "Órgão Responsável": novo_orgao,
                        "Data Limite": nova_data_limite,
                        "Status": novo_status,
                        "Dificuldade": nova_dificuldade,
                        "Prazo": datetime.combine(novo_prazo, datetime.min.time()),
                        "Data Início": datetime.now() if novo_status == "Em Andamento" else None,
                        "Data Conclusão": datetime.now() if novo_status == "Finalizado" else None
                    }
                    
                    if add_nova_atividade(periodo_id, nova_atividade):
                        st.success("✅ Atividade adicionada com sucesso!")
                        # Substitui st.experimental_rerun() por st.rerun()
                        st.rerun()
                    else:
                        st.error("⚠️ Erro ao adicionar atividade. Tente novamente.")
                else:
                    st.error("⚠️ Preencha todos os campos obrigatórios (marcados com *)")
    
    # Fechar período
    if not fechado:
        with st.expander("🔒 Fechar Período", expanded=False):
            st.markdown(f"**Fechar o período de {formatar_mes_ano(mes, ano)}**")
            st.warning("Ao fechar o período, todas as atividades devem estar com status 'Finalizado'. O próximo mês será automaticamente habilitado.")
            
            if st.button("Fechar Período Atual"):
                success, message = fechar_periodo(periodo_id)
                if success:
                    st.success(message)
                    # Substitui st.experimental_rerun() por st.rerun()
                    st.rerun()
                else:
                    st.error(message)
    else:
        st.markdown(f'<div class="card"><p>Período de {formatar_mes_ano(mes, ano)} foi fechado em {datetime.strptime(data_fechamento, "%Y-%m-%d").strftime("%d/%m/%Y")}.</p></div>', unsafe_allow_html=True)
    
    # Histórico de períodos
    with st.expander("📅 Histórico de Períodos", expanded=False):
        periodos = get_periodos()
        if periodos:
            historico_df = pd.DataFrame(periodos, columns=['id', 'Mês', 'Ano', 'Fechado', 'Data Fechamento'])
            historico_df['Período'] = historico_df.apply(lambda row: formatar_mes_ano(row['Mês'], row['Ano']), axis=1)
            historico_df['Status'] = historico_df['Fechado'].apply(lambda x: "Fechado" if x else "Aberto")
            historico_df['Data Fechamento'] = historico_df['Data Fechamento'].apply(
                lambda x: datetime.strptime(x, "%Y-%m-%d").strftime("%d/%m/%Y") if x else "-"
            )
            
            st.write(historico_df[['Período', 'Status', 'Data Fechamento']].to_html(index=False, escape=False), unsafe_allow_html=True)
        else:
            st.info("Nenhum período histórico encontrado.")

if __name__ == "__main__":
    main()
