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
        box_shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
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
    
    today = datetime(ref_year, ref_month, 1) # Usar o primeiro dia do mês de referência para base de cálculo

    # Lógica de cálculo de prazo ajustada para o mês de referência
    if "dia 10 do mês subsequente" in data_limite_text:
        # Pega o primeiro dia do mês subsequente e adiciona 9 dias para chegar ao dia 10
        date_for_calc = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=1)
        return date_for_calc.replace(day=10)
    elif "dia 15 do mês subsequente" in data_limite_text:
        date_for_calc = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=1)
        return date_for_calc.replace(day=15)
    elif "dia 20 do mês subsequente" in data_limite_text:
        date_for_calc = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=1)
        return date_for_calc.replace(day=20)
    elif "dia 25 do mês subsequente" in data_limite_text:
        date_for_calc = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=1)
        return date_for_calc.replace(day=25)
    elif "último dia útil do mês subsequente" in data_limite_text:
        next_month_start = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=1)
        # Para encontrar o último dia útil, começa do último dia do mês e volta se for fim de semana
        last_day_next_month = (next_month_start + pd.DateOffset(months=1)) - timedelta(days=1)
        while last_day_next_month.weekday() >= 5: # 5 = Saturday, 6 = Sunday
            last_day_next_month -= timedelta(days=1)
        return last_day_next_month
    elif "10º dia útil do segundo mês subsequente" in data_limite_text:
        # Pega o primeiro dia do segundo mês subsequente
        second_next_month_start = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=2)
        day_count = 0
        current_date = second_next_month_start
        while day_count < 10:
            if current_date.weekday() < 5: # Monday to Friday
                day_count += 1
            if day_count < 10: # Only advance if not the 10th day yet
                current_date += timedelta(days=1)
        return current_date
    elif "Último dia útil de fevereiro" in data_limite_text:
        # Assumindo que o ano da DIRF é o ano da referência
        try:
            feb_last_day = datetime(ref_year, 2, 28)
            if ref_year % 4 == 0 and (ref_year % 100 != 0 or ref_year % 400 == 0): # Ano bissexto
                feb_last_day = datetime(ref_year, 2, 29)
            while feb_last_day.weekday() >= 5:
                feb_last_day -= timedelta(days=1)
            return feb_last_day
        except ValueError: # Caso o mês de referência seja anterior a fevereiro no primeiro ano
            return None # Ou definir uma lógica de fallback
    elif "Último dia útil do mês subsequente ao trimestre" in data_limite_text:
        # Calcular o último dia do trimestre fiscal atual (para o mês de referência)
        current_quarter = (ref_month - 1) // 3
        quarter_end_month = (current_quarter * 3) + 3 # 3, 6, 9, 12
        
        if ref_month == quarter_end_month: # Se o mês de referência for o final de um trimestre
            # O prazo é o último dia útil do mês subsequente ao trimestre
            next_month_after_quarter = datetime(ref_year, quarter_end_month, 1) + pd.DateOffset(months=1)
            last_day = (next_month_after_quarter + pd.DateOffset(months=1)) - timedelta(days=1)
            while last_day.weekday() >= 5:
                last_day -= timedelta(days=1)
            return last_day
        else:
            return None # Não há prazo trimestral para este mês de referência específico
    else:
        # Para "Conforme publicação de nova legislação" ou outras que não têm data fixa
        # Pode-se definir um prazo padrão ou deixar como None para ser preenchido manualmente
        return datetime(ref_year, ref_month, 1) + timedelta(days=90) # Exemplo: 90 dias a partir do início do mês

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
    elif status == "Fechado":
        return '<span class="status-badge status-fechado">Fechado</span>'
    else:
        return f'<span class="status-badge">{status}</span>' # Fallback para status desconhecido

def apply_difficulty_style(dificuldade):
    if dificuldade == "Baixa":
        return '<span class="dificuldade-badge dificuldade-baixa">Baixa</span>'
    elif dificuldade == "Média":
        return '<span class="dificuldade-badge dificuldade-media">Média</span>'
    elif dificuldade == "Alta":
        return '<span class="dificuldade-badge dificuldade-alta">Alta</span>'
    else:
        return f'<span class="dificuldade-badge">{dificuldade}</span>' # Fallback

def calculate_days_remaining(row):
    # Use datetime.now() para a data atual, independente do mês de referência
    hoje = datetime.now()
    if pd.isna(row['Prazo']) or row['Status'] in ['Finalizado', 'Fechado']:
        return None
    prazo = row['Prazo']
    days = (prazo - hoje).days
    return days if days >= 0 else 0 # Retorna 0 se o prazo já passou


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
            # Ao mudar de mês, recarregamos os dados. Não precisamos de experimental_rerun aqui.
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            # Forçar uma nova execução para atualizar a UI imediatamente
            st.experimental_rerun()
    with col_nav2:
        st.markdown(f"<h2 style='text-align: center;'>Mês/Ano de Referência: {st.session_state.mes_ano_referencia}</h2>", unsafe_allow_html=True)
    with col_nav3:
        if st.button("Próximo Mês ▶️"):
            st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
            # Ao mudar de mês, recarregamos os dados.
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            # Forçar uma nova execução para atualizar a UI imediatamente
            st.experimental_rerun()

    # Carregar dados do banco de dados para o mês de referência atual
    # Garantir que st.session_state.df_atividades esteja sempre inicializado
    if 'df_atividades' not in st.session_state:
        st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
    else:
        # Isso garante que df_atividades está sincronizado com o mês atual após navegação
        # ou se o app for iniciado.
        # Evita recarregar desnecessariamente se o mês já foi carregado
        current_df_month = None
        if not st.session_state.df_atividades.empty:
            current_df_month = st.session_state.df_atividades['MesAnoReferencia'].iloc[0]
        
        if current_df_month != st.session_state.mes_ano_referencia:
             st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)


    # Se não houver dados para o mês/ano de referência, perguntar se deseja inicializar
    if st.session_state.df_atividades.empty:
        st.warning(f"Não há atividades cadastradas para {st.session_state.mes_ano_referencia}.")
        if st.button(f"Habilitar Mês {st.session_state.mes_ano_referencia}", key="habilitar_mes_btn"):
            initial_templates = load_initial_data_template()
            activities_to_insert = []
            for activity in initial_templates:
                # Calcular o prazo com base no mês de referência atual
                prazo_calculated = calculate_deadline(activity['Data Limite'], st.session_state.mes_ano_referencia)
                activity['Prazo'] = prazo_calculated.strftime('%Y-%m-%d %H:%M:%S') if prazo_calculated else None
                activity['MesAnoReferencia'] = st.session_state.mes_ano_referencia
                activity['Data Inicio'] = None # Assegurar que Data Inicio seja None no início
                activity['Data Conclusao'] = None # Assegurar que Data Conclusao seja None no início
                activities_to_insert.append(activity)
            
            insert_initial_data(activities_to_insert)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            st.success(f"Atividades padrão para {st.session_state.mes_ano_referencia} habilitadas com sucesso!")
            st.experimental_rerun() # Recarregar a página para mostrar os dados

    # Filtrar DF para exibição e métricas
    # APLICAR FILTROS APENAS SE HOUVER DADOS
    filtered_df = pd.DataFrame() # Inicializa como DataFrame vazio
    if not st.session_state.df_atividades.empty:
        filtered_df = st.session_state.df_atividades.copy()

        # Filtros
        with st.expander("🔍 Filtros", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                status_options = ["Todos", "Pendente", "Em Andamento", "Finalizado", "Fechado"]
                if 'Status' in filtered_df.columns:
                    status_filter = st.selectbox("Status", status_options)
                else:
                    status_filter = st.selectbox("Status", status_options, disabled=True)
            with col2:
                difficulty_options = ["Todos", "Baixa", "Média", "Alta"]
                if 'Dificuldade' in filtered_df.columns:
                    dificuldade_filter = st.selectbox("Dificuldade", difficulty_options)
                else:
                    dificuldade_filter = st.selectbox("Dificuldade", difficulty_options, disabled=True)
            with col3:
                orgao_options = ["Todos"]
                if 'Órgão Responsável' in filtered_df.columns:
                    orgao_options.extend(list(filtered_df['Órgão Responsável'].unique()))
                    orgao_filter = st.selectbox("Órgão Responsável", orgao_options)
                else:
                    orgao_filter = st.selectbox("Órgão Responsável", orgao_options, disabled=True)

        if not filtered_df.empty: # Re-verificar após carregar para garantir que não está vazia após filtros
            if status_filter != "Todos":
                filtered_df = filtered_df[filtered_df['Status'] == status_filter]
            if dificuldade_filter != "Todos":
                filtered_df = filtered_df[filtered_df['Dificuldade'] == dificuldade_filter]
            if orgao_filter != "Todos":
                filtered_df = filtered_df[filtered_df['Órgão Responsável'] == orgao_filter]
        
        # Calcular dias restantes, aplicando apenas se o DF não estiver vazio
        if not filtered_df.empty:
            filtered_df['Dias Restantes'] = filtered_df.apply(calculate_days_remaining, axis=1)
        else:
            filtered_df['Dias Restantes'] = None # Garante a coluna mesmo se o filtro esvaziar o DF

    # Mostrar métricas - sempre mostrar, mesmo que com zero
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total de Atividades", len(st.session_state.df_atividades) if not st.session_state.df_atividades.empty else 0)
    with col2:
        st.metric("Pendentes", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Pendente"]) if not st.session_state.df_atividades.empty else 0)
    with col3:
        st.metric("Em Andamento", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Em Andamento"]) if not st.session_state.df_atividades.empty else 0)
    with col4:
        st.metric("Finalizadas", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Finalizado"]) if not st.session_state.df_atividades.empty else 0)
    with col5:
        st.metric("Fechadas", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Fechado"]) if not st.session_state.df_atividades.empty else 0)

    # Gráficos
    st.markdown("---")
    st.markdown('<div class="card animate-fadeIn"><h3>📈 Análise Gráfica</h3></div>', unsafe_allow_html=True)
    if not st.session_state.df_atividades.empty:
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
            prazo_df['Prazo'] = pd.to_datetime(prazo_df['Prazo'], errors='coerce')
            prazo_df = prazo_df.dropna(subset=['Prazo']) # Remove linhas sem prazo válido para o gráfico
            
            if not prazo_df.empty:
                prazo_df = prazo_df.sort_values('Prazo')
                prazo_df['Prazo Formatado'] = prazo_df['Prazo'].dt.strftime('%d/%m/%Y')

                # Para o gráfico de timeline, 'Data Início' precisa ser datetime.
                # Se for None/NaT, atribua um valor para visualização (ex: 1 dia antes do prazo)
                prazo_df['Data Início Visual'] = prazo_df['Data Início'].fillna(prazo_df['Prazo'] - timedelta(days=1))
                
                fig_prazo = px.timeline(prazo_df, x_start="Data Início Visual", x_end="Prazo", y="Obrigação",
                                       color="Status",
                                       title='Linha do Tempo das Atividades',
                                       color_discrete_map={'Pendente':'#ffc107', 'Em Andamento':'#007bff', 'Finalizado':'#28a745', 'Fechado':'#6c757d'},
                                       hover_name="Obrigação",
                                       hover_data={"Status": True, "Dificuldade": True, "Prazo Formatado": True, "Data Início Visual": False}) # Não mostrar Data Início Visual no hover
                fig_prazo.update_yaxes(autorange="reversed")
                fig_prazo.update_layout(showlegend=True)
                st.plotly_chart(fig_prazo, use_container_width=True)
            else:
                st.info("Não há atividades com prazo definido para exibir na linha do tempo.")
    else:
        st.info("Adicione atividades ou habilite um mês para ver as análises gráficas.")


    # Tabela de atividades
    st.markdown("---")
    st.markdown('<div class="card animate-fadeIn"><h3>📋 Lista de Atividades</h3></div>', unsafe_allow_html=True)

    if not filtered_df.empty:
        # Formatar DataFrame para exibição
        display_df = filtered_df.copy()
        display_df['Status'] = display_df['Status'].apply(apply_status_style)
        display_df['Dificuldade'] = display_df['Dificuldade'].apply(apply_difficulty_style)
        
        # Formatar datas para exibição, tratando NaT (Not a Time)
        display_df['Prazo'] = display_df['Prazo'].dt.strftime('%d/%m/%Y').replace({pd.NaT: ''})
        display_df['Data Início'] = display_df['Data Início'].dt.strftime('%d/%m/%Y').replace({pd.NaT: ''})
        display_df['Data Conclusão'] = display_df['Data Conclusão'].dt.strftime('%d/%m/%Y').replace({pd.NaT: ''})
        
        # Selecionar colunas para exibição
        cols_to_display = ['Obrigação', 'Descrição', 'Periodicidade', 'Órgão Responsável',
                          'Data Limite', 'Status', 'Dificuldade', 'Prazo', 'Dias Restantes']
        
        # Assegurar que todas as colunas existem antes de tentar selecioná-las
        cols_exist = [col for col in cols_to_display if col in display_df.columns]
        
        st.write(display_df[cols_exist].to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.")


    # Adicionar nova atividade
    st.markdown("---")
    with st.expander("➕ Adicionar Nova Atividade", expanded=False):
        with st.form("nova_atividade_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nova_obrigacao = st.text_input("Obrigação*", placeholder="Nome da obrigação fiscal", key="nova_obrigacao")
                nova_descricao = st.text_area("Descrição*", placeholder="Descrição detalhada da atividade", key="nova_descricao")
                nova_periodicidade = st.selectbox("Periodicidade*", ["Mensal", "Trimestral", "Anual", "Eventual", "Extinta"], key="nova_periodicidade")
            with col2:
                novo_orgao = st.text_input("Órgão Responsável*", placeholder="Órgão responsável", key="novo_orgao")
                nova_data_limite = st.text_input("Data Limite de Entrega*", placeholder="Ex: Até o dia 10 do mês subsequente", key="nova_data_limite")
                novo_status = st.selectbox("Status*", ["Pendente", "Em Andamento", "Finalizado", "Fechado"], key="novo_status")
                nova_dificuldade = st.selectbox("Dificuldade*", ["Baixa", "Média", "Alta"], key="nova_dificuldade")
                novo_prazo = st.date_input("Prazo Final*", key="novo_prazo_data")

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
    st.markdown("---")
    with st.expander("✏️ Editar Atividades", expanded=False):
        if not st.session_state.df_atividades.empty:
            atividades_para_editar = st.session_state.df_atividades['Obrigação'].unique()
            atividade_selecionada = st.selectbox("Selecione a atividade para editar", atividades_para_editar, key="edit_select")

            if atividade_selecionada:
                atividade_row_series = st.session_state.df_atividades[st.session_state.df_atividades['Obrigação'] == atividade_selecionada].iloc[0]
                atividade_id = atividade_row_series['id']
                current_status = atividade_row_series['Status']
                
                # Certifica-se de que current_prazo é um objeto date
                current_prazo = atividade_row_series['Prazo'].date() if pd.notna(atividade_row_series['Prazo']) else datetime.now().date()

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
                        
                        # Atualizar DataInicio e DataConclusao com base no novo status
                        if novo_status == "Em Andamento" and (pd.isna(atividade_row_series['Data Início']) or atividade_row_series['Data Início'] == ''):
                            update_activity_in_db(atividade_id, 'DataInicio', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        elif novo_status != "Em Andamento" and pd.notna(atividade_row_series['Data Início']): # Limpar se não estiver mais em andamento
                             update_activity_in_db(atividade_id, 'DataInicio', None)

                        if novo_status == "Finalizado":
                            update_activity_in_db(atividade_id, 'DataConclusao', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        elif novo_status != "Finalizado" and pd.notna(atividade_row_series['Data Conclusão']): # Limpar se não estiver mais finalizado
                            update_activity_in_db(atividade_id, 'DataConclusao', None)

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

    todas_finalizadas_ou_fechadas = False
    if not st.session_state.df_atividades.empty:
        # Verifica se todas as atividades do mês de referência estão Finalizadas ou Fechadas
        todas_finalizadas_ou_fechadas = all(st.session_state.df_atividades['Status'].isin(["Finalizado", "Fechado"]))

    if todas_finalizadas_ou_fechadas and not st.session_state.df_atividades.empty:
        st.success(f"🎉 Todas as atividades para {st.session_state.mes_ano_referencia} estão finalizadas ou fechadas!")
        if st.button("Fechar Período e Habilitar Próximo Mês", key="fechar_periodo_btn"):
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

            # Avança para o próximo mês
            st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)

            if st.session_state.df_atividades.empty:
                st.warning(f"Não há dados para {st.session_state.mes_ano_referencia}. Gerando atividades padrão...")
                initial_templates = load_initial_data_template()
                activities_to_insert = []
                for activity in initial_templates:
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
    else:
        st.info("Nenhuma atividade para fechar. Habilite um mês primeiro.")


if __name__ == "__main__":
    main()
