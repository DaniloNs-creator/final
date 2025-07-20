import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import numpy as np

# Configuração para evitar erros de inotify
st.set_option('deprecation.showfileUploaderEncoding', False)

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
    
    .header {
        background-color: var(--primary-color);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .card {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    }
    
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        font-weight: 600;
    }
    
    .status-pendente {
        background-color: var(--warning-color);
        color: var(--dark-color);
    }
    
    .status-andamento {
        background-color: var(--primary-color);
        color: white;
    }
    
    .status-finalizado {
        background-color: var(--success-color);
        color: white;
    }
    
    .status-fechado {
        background-color: var(--light-color);
        color: var(--dark-color);
    }
    
    .dificuldade-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        font-weight: 600;
    }
    
    .dificuldade-baixa {
        background-color: var(--success-color);
        color: white;
    }
    
    .dificuldade-media {
        background-color: var(--warning-color);
        color: var(--dark-color);
    }
    
    .dificuldade-alta {
        background-color: var(--danger-color);
        color: white;
    }
    
    .animate-fadeIn {
        animation: fadeIn 0.5s ease-in-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# Conexão com o banco de dados SQLite
DATABASE = 'atividades_fiscais.db'

def create_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    try:
        conn = sqlite3.connect(DATABASE)
        return conn
    except sqlite3.Error as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def create_table():
    """Cria a tabela de atividades se não existir."""
    conn = create_connection()
    if conn is not None:
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

def load_data_from_db(mes_ano_referencia):
    """Carrega dados do banco de dados para um DataFrame."""
    conn = create_connection()
    df = pd.DataFrame()
    if conn is not None:
        try:
            query = "SELECT * FROM atividades WHERE MesAnoReferencia = ?"
            df = pd.read_sql_query(query, conn, params=(mes_ano_referencia,))
            
            # Converter colunas de data
            date_columns = ['Prazo', 'DataInicio', 'DataConclusao']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                else:
                    df[col] = pd.NaT
        except sqlite3.Error as e:
            st.error(f"Erro ao carregar dados do banco de dados: {e}")
        finally:
            conn.close()
    return df

def update_activity_in_db(activity_id, updates):
    """Atualiza uma atividade no banco de dados."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values())
            values.append(activity_id)
            
            query = f"UPDATE atividades SET {set_clause} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Erro ao atualizar atividade: {e}")
            return False
        finally:
            conn.close()
    return False

def add_activity_to_db(activity):
    """Adiciona uma nova atividade ao banco de dados."""
    conn = create_connection()
    if conn is not None:
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
            return cursor.lastrowid
        except sqlite3.Error as e:
            st.error(f"Erro ao adicionar atividade: {e}")
            return None
        finally:
            conn.close()
    return None

def load_initial_data_template():
    """Retorna o template de dados iniciais."""
    return [
        {
            "Obrigação": "Sped Fiscal",
            "Descrição": "Entrega do arquivo digital da EFD ICMS/IPI com registros fiscais de entradas, saídas, apuração de ICMS e IPI.",
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
            "Obrigação": "DCTF",
            "Descrição": "Declaração de Débitos e Créditos Tributários Federais",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "RFB",
            "Data Limite": "Até o dia 15 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "EFD Contribuições",
            "Descrição": "Escrituração Fiscal Digital de Contribuições",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "RFB",
            "Data Limite": "Até o dia 15 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": None,
            "Data Início": None,
            "Data Conclusão": None
        }
    ]

def get_next_month_year(current_month_year):
    """Calcula o próximo mês/ano."""
    month, year = map(int, current_month_year.split('/'))
    if month == 12:
        return f"01/{year + 1}"
    return f"{str(month + 1).zfill(2)}/{year}"

def get_previous_month_year(current_month_year):
    """Calcula o mês/ano anterior."""
    month, year = map(int, current_month_year.split('/'))
    if month == 1:
        return f"12/{year - 1}"
    return f"{str(month - 1).zfill(2)}/{year}"

def calculate_deadline(data_limite_text, mes_ano_referencia):
    """Calcula a data limite com base no texto descritivo."""
    ref_month, ref_year = map(int, mes_ano_referencia.split('/'))
    
    if "dia 10 do mês subsequente" in data_limite_text:
        date_for_calc = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=1)
        return date_for_calc.replace(day=10)
    elif "dia 15 do mês subsequente" in data_limite_text:
        date_for_calc = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=1)
        return date_for_calc.replace(day=15)
    return datetime(ref_year, ref_month, 1) + timedelta(days=90)

def apply_status_style(status):
    """Aplica estilo CSS ao status."""
    if status == "Pendente":
        return '<span class="status-badge status-pendente">Pendente</span>'
    elif status == "Em Andamento":
        return '<span class="status-badge status-andamento">Em Andamento</span>'
    elif status == "Finalizado":
        return '<span class="status-badge status-finalizado">Finalizado</span>'
    elif status == "Fechado":
        return '<span class="status-badge status-fechado">Fechado</span>'
    return f'<span class="status-badge">{status}</span>'

def apply_difficulty_style(dificuldade):
    """Aplica estilo CSS à dificuldade."""
    if dificuldade == "Baixa":
        return '<span class="dificuldade-badge dificuldade-baixa">Baixa</span>'
    elif dificuldade == "Média":
        return '<span class="dificuldade-badge dificuldade-media">Média</span>'
    elif dificuldade == "Alta":
        return '<span class="dificuldade-badge dificuldade-alta">Alta</span>'
    return f'<span class="dificuldade-badge">{dificuldade}</span>'

def calculate_days_remaining(row):
    """Calcula dias restantes para conclusão."""
    hoje = datetime.now()
    if pd.isna(row['Prazo']) or row['Status'] in ['Finalizado', 'Fechado']:
        return None
    prazo = row['Prazo']
    days = (prazo - hoje).days
    return days if days >= 0 else 0

def initialize_session_state():
    """Inicializa o estado da sessão."""
    if 'mes_ano_referencia' not in st.session_state:
        st.session_state.mes_ano_referencia = datetime.now().strftime('%m/%Y')
    
    if 'df_atividades' not in st.session_state:
        st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
    
    if 'force_refresh' not in st.session_state:
        st.session_state.force_refresh = False

def refresh_data():
    """Força o recarregamento dos dados do banco."""
    st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
    st.session_state.force_refresh = False

def show_navigation():
    """Mostra a navegação entre meses."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️ Mês Anterior"):
            st.session_state.mes_ano_referencia = get_previous_month_year(st.session_state.mes_ano_referencia)
            refresh_data()
    
    with col2:
        st.markdown(f"<h2 style='text-align: center;'>Mês/Ano de Referência: {st.session_state.mes_ano_referencia}</h2>", unsafe_allow_html=True)
    
    with col3:
        if st.button("Próximo Mês ▶️"):
            st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
            refresh_data()

def show_metrics():
    """Mostra as métricas de status."""
    cols = st.columns(5)
    metrics = [
        ("Total de Atividades", ""),
        ("Pendentes", "Pendente"),
        ("Em Andamento", "Em Andamento"),
        ("Finalizadas", "Finalizado"),
        ("Fechadas", "Fechado")
    ]
    
    for (label, status), col in zip(metrics, cols):
        if status:
            count = len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == status])
        else:
            count = len(st.session_state.df_atividades)
        col.metric(label, count)

def show_charts():
    """Mostra os gráficos de análise."""
    st.markdown("---")
    st.markdown('<div class="card animate-fadeIn"><h3>📈 Análise Gráfica</h3></div>', unsafe_allow_html=True)
    
    if st.session_state.df_atividades.empty:
        st.info("Adicione atividades ou habilite um mês para ver as análises gráficas.")
        return

    tab1, tab2, tab3 = st.tabs(["Status", "Dificuldade", "Prazo"])

    with tab1:
        if not st.session_state.df_atividades.empty and 'Status' in st.session_state.df_atividades.columns:
            status_counts = st.session_state.df_atividades['Status'].value_counts().reset_index()
            fig_status = px.pie(
                status_counts, 
                values='count', 
                names='Status',
                title='Distribuição por Status',
                color='Status',
                color_discrete_map={
                    'Pendente': '#ffc107',
                    'Em Andamento': '#007bff',
                    'Finalizado': '#28a745',
                    'Fechado': '#6c757d'
                }
            )
            st.plotly_chart(fig_status, use_container_width=True)

    with tab2:
        if not st.session_state.df_atividades.empty and 'Dificuldade' in st.session_state.df_atividades.columns:
            dificuldade_counts = st.session_state.df_atividades['Dificuldade'].value_counts().reset_index()
            fig_dificuldade = px.bar(
                dificuldade_counts,
                x='Dificuldade',
                y='count',
                title='Distribuição por Nível de Dificuldade',
                color='Dificuldade',
                color_discrete_map={
                    'Baixa': '#28a745',
                    'Média': '#ffc107',
                    'Alta': '#dc3545'
                }
            )
            st.plotly_chart(fig_dificuldade, use_container_width=True)

    with tab3:
        if not st.session_state.df_atividades.empty and 'Prazo' in st.session_state.df_atividades.columns:
            prazo_df = st.session_state.df_atividades.copy()
            prazo_df = prazo_df.dropna(subset=['Prazo'])
            
            if not prazo_df.empty:
                prazo_df['Prazo Formatado'] = prazo_df['Prazo'].dt.strftime('%d/%m/%Y')
                prazo_df['Data Início Visual'] = prazo_df['DataInicio'].fillna(prazo_df['Prazo'] - timedelta(days=1))
                
                fig_prazo = px.timeline(
                    prazo_df,
                    x_start="Data Início Visual",
                    x_end="Prazo",
                    y="Obrigacao",
                    color="Status",
                    title='Linha do Tempo das Atividades',
                    color_discrete_map={
                        'Pendente': '#ffc107',
                        'Em Andamento': '#007bff',
                        'Finalizado': '#28a745',
                        'Fechado': '#6c757d'
                    },
                    hover_name="Obrigacao",
                    hover_data={
                        "Status": True,
                        "Dificuldade": True,
                        "Prazo Formatado": True,
                        "Data Início Visual": False
                    }
                )
                fig_prazo.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_prazo, use_container_width=True)

def show_activities_table():
    """Mostra a tabela de atividades com filtros."""
    st.markdown("---")
    st.markdown('<div class="card animate-fadeIn"><h3>📋 Lista de Atividades</h3></div>', unsafe_allow_html=True)

    if st.session_state.df_atividades.empty:
        st.info("Nenhuma atividade encontrada para o mês selecionado.")
        return

    with st.expander("🔍 Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Status", ["Todos", "Pendente", "Em Andamento", "Finalizado", "Fechado"])
        with col2:
            difficulty_filter = st.selectbox("Dificuldade", ["Todos", "Baixa", "Média", "Alta"])
        with col3:
            orgao_options = ["Todos"] + list(st.session_state.df_atividades['OrgaoResponsavel'].unique())
            orgao_filter = st.selectbox("Órgão Responsável", orgao_options)

    filtered_df = st.session_state.df_atividades.copy()
    
    if status_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    if difficulty_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Dificuldade'] == difficulty_filter]
    if orgao_filter != "Todos":
        filtered_df = filtered_df[filtered_df['OrgaoResponsavel'] == orgao_filter]
    
    filtered_df['Dias Restantes'] = filtered_df.apply(calculate_days_remaining, axis=1)

    display_df = filtered_df.copy()
    display_df['Status'] = display_df['Status'].apply(apply_status_style)
    display_df['Dificuldade'] = display_df['Dificuldade'].apply(apply_difficulty_style)
    
    for col in ['Prazo', 'DataInicio', 'DataConclusao']:
        display_df[col] = display_df[col].dt.strftime('%d/%m/%Y').replace({pd.NaT: ''})

    cols_to_display = [
        'Obrigacao', 'Descricao', 'Periodicidade', 'OrgaoResponsavel',
        'DataLimite', 'Status', 'Dificuldade', 'Prazo', 'Dias Restantes'
    ]
    
    st.write(display_df[cols_to_display].to_html(escape=False, index=False), unsafe_allow_html=True)

def show_add_activity_form():
    """Mostra o formulário para adicionar nova atividade."""
    st.markdown("---")
    with st.expander("➕ Adicionar Nova Atividade", expanded=False):
        with st.form("nova_atividade_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                obrigacao = st.text_input("Obrigação*", placeholder="Nome da obrigação fiscal")
                descricao = st.text_area("Descrição*", placeholder="Descrição detalhada da atividade")
                periodicidade = st.selectbox("Periodicidade*", ["Mensal", "Trimestral", "Anual", "Eventual", "Extinta"])
            with col2:
                orgao = st.text_input("Órgão Responsável*", placeholder="Órgão responsável")
                data_limite = st.text_input("Data Limite de Entrega*", placeholder="Ex: Até o dia 10 do mês subsequente")
                status = st.selectbox("Status*", ["Pendente", "Em Andamento", "Finalizado", "Fechado"])
                dificuldade = st.selectbox("Dificuldade*", ["Baixa", "Média", "Alta"])
                prazo = st.date_input("Prazo Final*")

            if st.form_submit_button("Adicionar Atividade"):
                if obrigacao and descricao and orgao and data_limite and prazo:
                    nova_atividade = {
                        "Obrigação": obrigacao,
                        "Descrição": descricao,
                        "Periodicidade": periodicidade,
                        "Órgão Responsável": orgao,
                        "Data Limite": data_limite,
                        "Status": status,
                        "Dificuldade": dificuldade,
                        "Prazo": datetime.combine(prazo, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S'),
                        "Data Início": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == "Em Andamento" else None,
                        "Data Conclusão": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == "Finalizado" else None,
                        "MesAnoReferencia": st.session_state.mes_ano_referencia
                    }

                    if add_activity_to_db(nova_atividade):
                        st.success("✅ Atividade adicionada com sucesso!")
                        refresh_data()
                else:
                    st.error("⚠️ Preencha todos os campos obrigatórios (marcados com *)")

def show_edit_activity_form():
    """Mostra o formulário para editar atividades existentes."""
    st.markdown("---")
    with st.expander("✏️ Editar Atividades", expanded=False):
        if st.session_state.df_atividades.empty:
            st.info("Nenhuma atividade para editar. Adicione atividades ou habilite um novo mês.")
            return

        atividade_selecionada = st.selectbox(
            "Selecione a atividade para editar",
            st.session_state.df_atividades['Obrigacao'].unique()
        )

        atividade = st.session_state.df_atividades[
            st.session_state.df_atividades['Obrigacao'] == atividade_selecionada
        ].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            novo_status = st.selectbox(
                "Novo Status",
                ["Pendente", "Em Andamento", "Finalizado", "Fechado"],
                index=["Pendente", "Em Andamento", "Finalizado", "Fechado"].index(atividade['Status'])
            )
        with col2:
            novo_prazo = st.date_input(
                "Novo Prazo Final",
                value=atividade['Prazo'].date() if pd.notna(atividade['Prazo']) else datetime.now().date()
            )

        if st.button("Atualizar Atividade"):
            updates = {}
            
            if novo_status != atividade['Status']:
                updates['Status'] = novo_status
                
                if novo_status == "Em Andamento" and pd.isna(atividade['DataInicio']):
                    updates['DataInicio'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                elif novo_status != "Em Andamento" and pd.notna(atividade['DataInicio']):
                    updates['DataInicio'] = None
                
                if novo_status == "Finalizado":
                    updates['DataConclusao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                elif novo_status != "Finalizado" and pd.notna(atividade['DataConclusao']):
                    updates['DataConclusao'] = None
            
            novo_prazo_dt = datetime.combine(novo_prazo, datetime.min.time())
            if pd.isna(atividade['Prazo']) or novo_prazo_dt != atividade['Prazo']:
                updates['Prazo'] = novo_prazo_dt.strftime('%Y-%m-%d %H:%M:%S')
            
            if updates:
                if update_activity_in_db(atividade['id'], updates):
                    st.success("✅ Atividade atualizada com sucesso!")
                    refresh_data()
            else:
                st.info("Nenhuma alteração detectada para atualizar.")

def show_close_period_section():
    """Mostra a seção para fechar o período atual."""
    st.markdown("---")
    st.markdown('<div class="card animate-fadeIn"><h3>🗓️ Fechamento e Habilitação de Período</h3></div>', unsafe_allow_html=True)

    if st.session_state.df_atividades.empty:
        st.info("Nenhuma atividade para fechar. Habilite um mês primeiro.")
        return

    todas_finalizadas = all(st.session_state.df_atividades['Status'].isin(["Finalizado", "Fechado"]))

    if todas_finalizadas:
        st.success(f"🎉 Todas as atividades para {st.session_state.mes_ano_referencia} estão finalizadas ou fechadas!")
        
        if st.button("Fechar Período e Habilitar Próximo Mês"):
            conn = create_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE atividades
                        SET Status = 'Fechado'
                        WHERE MesAnoReferencia = ? AND Status = 'Finalizado'
                    """, (st.session_state.mes_ano_referencia,))
                    conn.commit()
                except sqlite3.Error as e:
                    st.error(f"Erro ao fechar período: {e}")
                finally:
                    conn.close()

            st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
            refresh_data()

            if st.session_state.df_atividades.empty:
                atividades = load_initial_data_template()
                for atividade in atividades:
                    prazo = calculate_deadline(atividade['Data Limite'], st.session_state.mes_ano_referencia)
                    atividade.update({
                        'Prazo': prazo.strftime('%Y-%m-%d %H:%M:%S') if prazo else None,
                        'MesAnoReferencia': st.session_state.mes_ano_referencia,
                        'Data Início': None,
                        'Data Conclusão': None
                    })
                
                for atividade in atividades:
                    add_activity_to_db(atividade)
                
                refresh_data()
                st.success("Atividades padrão habilitadas para o novo mês!")
    else:
        st.warning(f"Ainda há atividades pendentes ou em andamento para {st.session_state.mes_ano_referencia}. Finalize-as para fechar o período.")

def main():
    """Função principal que orquestra a aplicação."""
    st.markdown('<div class="header animate-fadeIn"><h1>📊 Controle de Atividades Fiscais - HÄFELE BRASIL</h1></div>', unsafe_allow_html=True)

    # Inicialização
    create_table()
    initialize_session_state()

    # Habilitar mês se não houver dados
    if st.session_state.df_atividades.empty:
        st.warning(f"Não há atividades cadastradas para {st.session_state.mes_ano_referencia}.")
        if st.button(f"Habilitar Mês {st.session_state.mes_ano_referencia}"):
            atividades = load_initial_data_template()
            for atividade in atividades:
                prazo = calculate_deadline(atividade['Data Limite'], st.session_state.mes_ano_referencia)
                atividade.update({
                    'Prazo': prazo.strftime('%Y-%m-%d %H:%M:%S') if prazo else None,
                    'MesAnoReferencia': st.session_state.mes_ano_referencia,
                    'Data Início': None,
                    'Data Conclusão': None
                })
            
            for atividade in atividades:
                add_activity_to_db(atividade)
            
            refresh_data()
            st.success("Atividades padrão habilitadas com sucesso!")

    # Botão para forçar atualização
    if st.button("🔄 Atualizar Dados"):
        refresh_data()
        st.success("Dados atualizados com sucesso!")

    # Componentes da interface
    show_navigation()
    show_metrics()
    show_charts()
    show_activities_table()
    show_add_activity_form()
    show_edit_activity_form()
    show_close_period_section()

if __name__ == "__main__":
    main()
