import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import numpy as np

# Configuração inicial da página
st.set_page_config(
    page_title="Controle de Atividades Fiscais - HÄFELE BRASIL",
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
    .status-fechado {
        background-color: #e2e3e5;
        color: #383d41;
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

# Conexão com o banco de dados SQLite
DATABASE = 'atividades_fiscais.db'

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        return conn
    except sqlite3.Error as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
    return conn

def create_table():
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS atividades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Obrigacao TEXT NOT NULL,
                    Descricao TEXT,
                    Periodicidade TEXT,
                    OrgaoResponsavel TEXT,
                    DataLimite TEXT,
                    Status TEXT,
                    Dificuldade TEXT,
                    Prazo TEXT,
                    DataInicio TEXT,
                    DataConclusao TEXT,
                    MesAnoReferencia TEXT NOT NULL
                )
            """)
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Erro ao criar tabela: {e}")
        finally:
            conn.close()

def insert_initial_data(data):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            for activity in data:
                # Verificar se a atividade já existe para o mês/ano de referência
                cursor.execute("""
                    SELECT id FROM atividades
                    WHERE Obrigacao = ? AND MesAnoReferencia = ?
                """, (activity['Obrigação'], activity['MesAnoReferencia']))
                if cursor.fetchone() is None:
                    cursor.execute("""
                        INSERT INTO atividades (
                            Obrigacao, Descricao, Periodicidade, OrgaoResponsavel, DataLimite,
                            Status, Dificuldade, Prazo, DataInicio, DataConclusao, MesAnoReferencia
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        activity['Obrigação'], activity['Descrição'], activity['Periodicidade'],
                        activity['Órgão Responsável'], activity['Data Limite'], activity['Status'],
                        activity['Dificuldade'], activity['Prazo'], activity['Data Início'],
                        activity['Data Conclusão'], activity['MesAnoReferencia']
                    ))
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Erro ao inserir dados iniciais: {e}")
        finally:
            conn.close()

def load_data_from_db(mes_ano_referencia):
    conn = create_connection()
    df = pd.DataFrame()
    if conn:
        try:
            df = pd.read_sql_query(f"SELECT * FROM atividades WHERE MesAnoReferencia = '{mes_ano_referencia}'", conn)
            # Converter colunas de data para datetime
            for col in ['Prazo', 'DataInicio', 'DataConclusao']:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        except sqlite3.Error as e:
            st.error(f"Erro ao carregar dados do banco de dados: {e}")
        finally:
            conn.close()
    return df

def update_activity_in_db(activity_id, column, value):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE atividades SET {column} = ? WHERE id = ?", (value, activity_id))
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Erro ao atualizar atividade: {e}")
        finally:
            conn.close()

def add_activity_to_db(activity):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO atividades (
                    Obrigacao, Descricao, Periodicidade, OrgaoResponsavel, DataLimite,
                    Status, Dificuldade, Prazo, DataInicio, DataConclusao, MesAnoReferencia
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                activity['Obrigação'], activity['Descrição'], activity['Periodicidade'],
                activity['Órgão Responsável'], activity['Data Limite'], activity['Status'],
                activity['Dificuldade'], activity['Prazo'], activity['Data Início'],
                activity['Data Conclusão'], activity['MesAnoReferencia']
            ))
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Erro ao adicionar atividade: {e}")
        finally:
            conn.close()

def load_initial_data_template():
    # Retorna uma lista de dicionários com os modelos de atividades
    return [
        {
            "Obrigação": "Sped Fiscal",
            "Descrição": "Entrega do arquivo digital da EFD ICMS/IPI com registros fiscais de entradas, saídas, apuração de ICMS e IPI.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": None, # Será preenchido com a data correta para o mês de referência
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
            "Prazo": None,
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
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Parametrização do sistema",
            "Descrição": "Atualização do sistema ERP com as novas margens de valor agregado (MVA) do ICMS ST.",
            "Periodicidade": "Eventual",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Conforme publicação de nova legislação",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": None,
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
            "Prazo": None,
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
            "Prazo": None,
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
            "Prazo": None,
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
            "Prazo": None,
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
            "Prazo": None,
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
            "Prazo": None,
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
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "DIRF - Prestadores",
            "Descrição": "Declaração de retenções de IRRF sobre pagamentos a prestadores de serviços.",
            "Periodicidade": "Anual",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Último dia útil de fevereiro",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "INSS Faturamento",
            "Descrição": "Apuração da contribuição previdenciária sobre a receita bruta.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o dia 20 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "REINF",
            "Descrição": "Entrega da EFD-REINF com retenções de INSS e contribuições previdenciárias.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o dia 15 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "DCTF WEB",
            "Descrição": "Declaração de débitos e créditos tributários federais via eSocial/REINF.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o dia 15 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "DCTF",
            "Descrição": "Declaração de débitos e créditos tributários federais convencionais.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o 15º dia útil do segundo mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "ISS Eletrônico",
            "Descrição": "Declaração e recolhimento do ISS sobre serviços prestados.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Prefeitura de Piraquara",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Conciliação GNRE ICMS ST",
            "Descrição": "Conferência entre GNREs pagas e notas fiscais de saída com ICMS ST.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "ST Faturamento",
            "Descrição": "Conferência dos cálculos de ICMS ST nas vendas com substituição tributária.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Cálculo IRPJ/CSLL",
            "Descrição": "Apuração do IRPJ e CSLL com base no lucro presumido ou real.",
            "Periodicidade": "Trimestral",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Último dia útil do mês subsequente ao trimestre",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        }
    ]

def get_next_month_year(current_month_year):
    month, year = map(int, current_month_year.split('/'))
    if month == 12:
        return f"01/{year + 1}"
    else:
        return f"{str(month + 1).zfill(2)}/{year}"

def get_previous_month_year(current_month_year):
    month, year = map(int, current_month_year.split('/'))
    if month == 1:
        return f"12/{year - 1}"
    else:
        return f"{str(month - 1).zfill(2)}/{year}"

def calculate_deadline(data_limite_text, mes_ano_referencia):
    # Converte o mes_ano_referencia para um objeto datetime
    ref_month, ref_year = map(int, mes_ano_referencia.split('/'))
    
    today = datetime(ref_year, ref_month, 1)

    if "dia 10 do mês subsequente" in data_limite_text:
        return (today.replace(day=1) + timedelta(days=32)).replace(day=10) # Próximo mês dia 10
    elif "dia 15 do mês subsequente" in data_limite_text:
        return (today.replace(day=1) + timedelta(days=32)).replace(day=15) # Próximo mês dia 15
    elif "dia 20 do mês subsequente" in data_limite_text:
        return (today.replace(day=1) + timedelta(days=32)).replace(day=20) # Próximo mês dia 20
    elif "dia 25 do mês subsequente" in data_limite_text:
        return (today.replace(day=1) + timedelta(days=32)).replace(day=25) # Próximo mês dia 25
    elif "último dia útil do mês subsequente" in data_limite_text:
        next_month = today.replace(day=1) + timedelta(days=32)
        last_day = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return last_day # Último dia do próximo mês
    elif "10º dia útil do segundo mês subsequente" in data_limite_text:
        second_next_month = (today.replace(day=1) + timedelta(days=62)).replace(day=1) # Dois meses à frente
        # Lógica para encontrar o 10º dia útil (simplificado, pode ser mais complexo)
        day_count = 0
        current_date = second_next_month
        while day_count < 10:
            if current_date.weekday() < 5: # Monday to Friday
                day_count += 1
            if day_count < 10: # Only advance if not the 10th day yet
                current_date += timedelta(days=1)
        return current_date
    elif "Último dia útil de fevereiro" in data_limite_text:
        return datetime(ref_year, 2, 28) if ref_year % 4 != 0 else datetime(ref_year, 2, 29) # Considera ano bissexto
    elif "Último dia útil do mês subsequente ao trimestre" in data_limite_text:
        quarter_end_month = ((ref_month - 1) // 3 + 1) * 3
        if quarter_end_month == ref_month: # Se o mês atual for o último do trimestre
            next_month = today.replace(month=quarter_end_month, day=1) + timedelta(days=32)
            last_day = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            return last_day
        else: # Se não for o último mês do trimestre, não tem prazo para este mês
            return None
    else:
        # Para "Conforme publicação de nova legislação" ou outras, pode ser definido manualmente
        return today + timedelta(days=90) # Exemplo: 90 dias para eventuais

# Inicializar o banco de dados e carregar dados
create_table()

# Funções auxiliares
def apply_status_style(status):
    if status == "Pendente":
        return '<span class="status-badge status-pendente">Pendente</span>'
    elif status == "Em Andamento":
        return '<span class="status-badge status-andamento">Em Andamento</span>'
    elif status == "Finalizado":
        return '<span class="status-badge status-finalizado">Finalizado</span>'
    else: # Status "Fechado"
        return '<span class="status-badge status-fechado">Fechado</span>'

def apply_difficulty_style(dificuldade):
    if dificuldade == "Baixa":
        return '<span class="dificuldade-badge dificuldade-baixa">Baixa</span>'
    elif dificuldade == "Média":
        return '<span class="dificuldade-badge dificuldade-media">Média</span>'
    else:
        return '<span class="dificuldade-badge dificuldade-alta">Alta</span>'

def calculate_days_remaining(row):
    if pd.isna(row['Prazo']) or row['Status'] in ['Finalizado', 'Fechado']:
        return None
    hoje = datetime.now()
    prazo = row['Prazo']
    return (prazo - hoje).days

# Interface do usuário
def main():
    st.markdown('<div class="header animate-fadeIn"><h1>📊 Controle de Atividades Fiscais - HÄFELE BRASIL</h1></div>', unsafe_allow_html=True)

    # Controle do mês/ano de referência
    if 'mes_ano_referencia' not in st.session_state:
        st.session_state.mes_ano_referencia = datetime.now().strftime('%m/%Y')

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("Mês Anterior ◀️"):
            st.session_state.mes_ano_referencia = get_previous_month_year(st.session_state.mes_ano_referencia)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia) # Recarrega dados
            if st.session_state.df_atividades.empty:
                st.warning(f"Não há dados para {st.session_state.mes_ano_referencia}. Use 'Habilitar Próximo Mês' para gerar atividades.")
    with col_nav2:
        st.markdown(f"<h2 style='text-align: center;'>Mês/Ano de Referência: {st.session_state.mes_ano_referencia}</h2>", unsafe_allow_html=True)
    with col_nav3:
        if st.button("Próximo Mês ▶️"):
            st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia) # Recarrega dados
            if st.session_state.df_atividades.empty:
                st.warning(f"Não há dados para {st.session_state.mes_ano_referencia}. Use 'Habilitar Próximo Mês' para gerar atividades.")

    # Carregar dados do banco de dados para o mês de referência atual
    st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)

    # Se não houver dados para o mês/ano de referência, perguntar se deseja inicializar
    if st.session_state.df_atividades.empty:
        st.warning(f"Não há atividades cadastradas para {st.session_state.mes_ano_referencia}.")
        if st.button(f"Habilitar Mês {st.session_state.mes_ano_referencia}"):
            initial_templates = load_initial_data_template()
            activities_to_insert = []
            for activity in initial_templates:
                # Calcular o prazo com base no mês de referência
                prazo_calculated = calculate_deadline(activity['Data Limite'], st.session_state.mes_ano_referencia)
                activity['Prazo'] = prazo_calculated.strftime('%Y-%m-%d %H:%M:%S') if prazo_calculated else None
                activity['MesAnoReferencia'] = st.session_state.mes_ano_referencia
                activities_to_insert.append(activity)
            
            insert_initial_data(activities_to_insert)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            st.success(f"Atividades padrão para {st.session_state.mes_ano_referencia} habilitadas com sucesso!")
            st.experimental_rerun() # Recarregar a página para mostrar os dados

    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Status", ["Todos", "Pendente", "Em Andamento", "Finalizado", "Fechado"])
        with col2:
            dificuldade_filter = st.selectbox("Dificuldade", ["Todos", "Baixa", "Média", "Alta"])
        with col3:
            orgao_filter = st.selectbox("Órgão Responsável", ["Todos"] + list(st.session_state.df_atividades['Órgão Responsável'].unique()))

    # Aplicar filtros
    filtered_df = st.session_state.df_atividades.copy()
    if status_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    if dificuldade_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Dificuldade'] == dificuldade_filter]
    if orgao_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Órgão Responsável'] == orgao_filter]

    # Calcular dias restantes
    filtered_df['Dias Restantes'] = filtered_df.apply(calculate_days_remaining, axis=1)

    # Mostrar métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total de Atividades", len(st.session_state.df_atividades))
    with col2:
        st.metric("Pendentes", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Pendente"]))
    with col3:
        st.metric("Em Andamento", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Em Andamento"]))
    with col4:
        st.metric("Finalizadas", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Finalizado"]))
    with col5:
        st.metric("Fechadas", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Fechado"]))

    # Gráficos
    with st.expander("📈 Análise Gráfica", expanded=True):
        tab1, tab2, tab3 = st.tabs(["Status", "Dificuldade", "Prazo"])

        with tab1:
            status_counts = st.session_state.df_atividades['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Quantidade']
            fig_status = px.pie(status_counts, values='Quantidade', names='Status',
                               title='Distribuição por Status',
                               color='Status',
                               color_discrete_map={'Pendente':'#ffc107', 'Em Andamento':'#007bff', 'Finalizado':'#28a745', 'Fechado':'#6c757d'})
            st.plotly_chart(fig_status, use_container_width=True)

        with tab2:
            dificuldade_counts = st.session_state.df_atividades['Dificuldade'].value_counts().reset_index()
            dificuldade_counts.columns = ['Dificuldade', 'Quantidade']
            fig_dificuldade = px.bar(dificuldade_counts, x='Dificuldade', y='Quantidade',
                                   title='Distribuição por Nível de Dificuldade',
                                   color='Dificuldade',
                                   color_discrete_map={'Baixa':'#28a745', 'Média':'#ffc107', 'Alta':'#dc3545'})
            st.plotly_chart(fig_dificuldade, use_container_width=True)

        with tab3:
            prazo_df = st.session_state.df_atividades.copy()
            prazo_df['Prazo'] = pd.to_datetime(prazo_df['Prazo'])
            prazo_df = prazo_df.sort_values('Prazo')
            prazo_df['Prazo Formatado'] = prazo_df['Prazo'].dt.strftime('%d/%m/%Y')

            # Criar datas mínimas para o gráfico de timeline
            prazo_df['Data Início'] = prazo_df['Data Início'].fillna(prazo_df['Prazo'].dt.date - timedelta(days=1))
            prazo_df['Data Início'] = prazo_df['Data Início'].apply(lambda x: pd.to_datetime(x) if x is not None else None)

            fig_prazo = px.timeline(prazo_df, x_start="Data Início", x_end="Prazo", y="Obrigação",
                                   color="Status",
                                   title='Linha do Tempo das Atividades',
                                   color_discrete_map={'Pendente':'#ffc107', 'Em Andamento':'#007bff', 'Finalizado':'#28a745', 'Fechado':'#6c757d'},
                                   hover_name="Obrigação",
                                   hover_data=["Status", "Dificuldade", "Prazo Formatado"])
            fig_prazo.update_yaxes(autorange="reversed")
            fig_prazo.update_layout(showlegend=True)
            st.plotly_chart(fig_prazo, use_container_width=True)

    # Tabela de atividades
    st.markdown('<div class="card animate-fadeIn"><h3>📋 Lista de Atividades</h3></div>', unsafe_allow_html=True)

    # Formatar DataFrame para exibição
    display_df = filtered_df.copy()
    display_df['Status'] = display_df['Status'].apply(apply_status_style)
    display_df['Dificuldade'] = display_df['Dificuldade'].apply(apply_difficulty_style)
    display_df['Prazo'] = display_df['Prazo'].dt.strftime('%d/%m/%Y')
    display_df['Data Início'] = display_df['Data Início'].apply(
        lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
    )
    display_df['Data Conclusão'] = display_df['Data Conclusão'].apply(
        lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
    )

    # Selecionar colunas para exibição
    cols_to_display = ['Obrigação', 'Descrição', 'Periodicidade', 'Órgão Responsável',
                      'Data Limite', 'Status', 'Dificuldade', 'Prazo', 'Dias Restantes']

    st.write(display_df[cols_to_display].to_html(escape=False, index=False), unsafe_allow_html=True)

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
                if nova_obrigacao and nova_descricao and novo_orgao and nova_data_limite and novo_prazo:
                    nova_atividade = {
                        "Obrigação": nova_obrigacao,
                        "Descrição": nova_descricao,
                        "Periodicidade": nova_periodicidade,
                        "Órgão Responsável": novo_orgao,
                        "Data Limite": nova_data_limite,
                        "Status": novo_status,
                        "Dificuldade": nova_dificuldade,
                        "Prazo": datetime.combine(novo_prazo, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S'),
                        "Data Início": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if novo_status == "Em Andamento" else None,
                        "Data Conclusão": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if novo_status == "Finalizado" else None,
                        "MesAnoReferencia": st.session_state.mes_ano_referencia
                    }

                    add_activity_to_db(nova_atividade)
                    st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                    st.success("✅ Atividade adicionada com sucesso!")
                    st.experimental_rerun() # Recarregar a página para mostrar a nova atividade
                else:
                    st.error("⚠️ Preencha todos os campos obrigatórios (marcados com *)")

    # Editar status e prazo das atividades
    if not st.session_state.df_atividades.empty:
        with st.expander("✏️ Editar Atividades", expanded=False):
            atividades_para_editar = st.session_state.df_atividades['Obrigação'].unique()
            atividade_selecionada = st.selectbox("Selecione a atividade para editar", atividades_para_editar, key="edit_select")

            if atividade_selecionada:
                atividade_row = st.session_state.df_atividades[st.session_state.df_atividades['Obrigação'] == atividade_selecionada].iloc[0]
                atividade_id = atividade_row['id']
                current_status = atividade_row['Status']
                current_prazo = atividade_row['Prazo'].date() if pd.notna(atividade_row['Prazo']) else datetime.now().date()

                col1, col2 = st.columns(2)
                with col1:
                    novo_status = st.selectbox("Novo Status", ["Pendente", "Em Andamento", "Finalizado", "Fechado"],
                                              index=["Pendente", "Em Andamento", "Finalizado", "Fechado"].index(current_status), key="status_select")
                with col2:
                    novo_prazo = st.date_input("Novo Prazo Final", value=current_prazo, key="prazo_date")

                if st.button("Atualizar Atividade Selecionada"):
                    # Atualizar status
                    if novo_status != current_status:
                        update_activity_in_db(atividade_id, 'Status', novo_status)
                        if novo_status == "Em Andamento" and pd.isna(atividade_row['Data Início']):
                            update_activity_in_db(atividade_id, 'DataInicio', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        if novo_status == "Finalizado":
                            update_activity_in_db(atividade_id, 'DataConclusao', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        st.success(f"✅ Status da atividade '{atividade_selecionada}' atualizado para '{novo_status}'!")
                    
                    # Atualizar prazo
                    if novo_prazo != current_prazo:
                        update_activity_in_db(atividade_id, 'Prazo', datetime.combine(novo_prazo, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S'))
                        st.success(f"✅ Prazo da atividade '{atividade_selecionada}' atualizado para '{novo_prazo.strftime('%d/%m/%Y')}'!")
                    
                    st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                    st.experimental_rerun()
    else:
        st.info("Nenhuma atividade para editar. Adicione atividades ou habilite um novo mês.")

    # Fechar período e habilitar próximo mês
    st.markdown("---")
    st.markdown('<div class="card animate-fadeIn"><h3>🗓️ Fechamento e Habilitação de Período</h3></div>', unsafe_allow_html=True)

    todas_finalizadas = all(st.session_state.df_atividades['Status'].isin(["Finalizado", "Fechado"]))

    if todas_finalizadas and not st.session_state.df_atividades.empty:
        st.success(f"🎉 Todas as atividades para {st.session_state.mes_ano_referencia} estão finalizadas!")
        if st.button("Fechar Período e Habilitar Próximo Mês"):
            # Mudar o status de todas as atividades do mês atual para "Fechado"
            conn = create_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE atividades
                        SET Status = 'Fechado'
                        WHERE MesAnoReferencia = ?
                    """, (st.session_state.mes_ano_referencia,))
                    conn.commit()
                except sqlite3.Error as e:
                    st.error(f"Erro ao fechar período: {e}")
                finally:
                    conn.close()

            st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)

            if st.session_state.df_atividades.empty:
                st.warning(f"Não há dados para {st.session_state.mes_ano_referencia}. Gerando atividades padrão...")
                initial_templates = load_initial_data_template()
                activities_to_insert = []
                for activity in initial_templates:
                    # Calcular o prazo com base no mês de referência
                    prazo_calculated = calculate_deadline(activity['Data Limite'], st.session_state.mes_ano_referencia)
                    activity['Prazo'] = prazo_calculated.strftime('%Y-%m-%d %H:%M:%S') if prazo_calculated else None
                    activity['MesAnoReferencia'] = st.session_state.mes_ano_referencia
                    activities_to_insert.append(activity)
                insert_initial_data(activities_to_insert)
                st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                st.success(f"Período de {get_previous_month_year(st.session_state.mes_ano_referencia)} fechado e atividades para {st.session_state.mes_ano_referencia} habilitadas com sucesso!")
            else:
                st.success(f"Período de {get_previous_month_year(st.session_state.mes_ano_referencia)} fechado e mês {st.session_state.mes_ano_referencia} habilitado com atividades já existentes!")
            st.experimental_rerun()
    elif not st.session_state.df_atividades.empty:
        st.warning(f"Ainda há atividades pendentes ou em andamento para {st.session_state.mes_ano_referencia}. Finalize-as para fechar o período.")


if __name__ == "__main__":
    main()
