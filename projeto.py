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
    /* Seu CSS personalizado permanece o mesmo */
    :root {
        --primary-color: #4a8fe7;
        --secondary-color: #f0f2f6;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
        --dark-color: #343a40;
        --light-color: #f8f9fa;
    }

    .stApp {
        background-color: #f5f7fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--dark-color);
        font-weight: 600;
    }

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

    .stSelectbox>div>div>select {
        border-radius: 0.5rem;
        padding: 0.5rem;
    }

    .stDataFrame {
        border-radius: 0.5rem;
        overflow: hidden;
    }

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

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .animate-fadeIn {
        animation: fadeIn 0.5s ease-out forwards;
    }

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
    """Cria e retorna uma conexão com o banco de dados SQLite."""
    try:
        conn = sqlite3.connect(DATABASE)
        return conn
    except sqlite3.Error as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def create_table():
    """Cria a tabela de atividades se ela não existir."""
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

def insert_initial_data(data):
    """Insere dados iniciais no banco de dados."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            for activity in data:
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
                    df[col] = pd.to_datetime(df[col], errors='coerce')
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
            return True
        except sqlite3.Error as e:
            st.error(f"Erro ao adicionar atividade: {e}")
            return False
        finally:
            conn.close()
    return False

def load_initial_data_template():
    """Retorna o template de dados iniciais para o sistema."""
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
        # ... (adicionar todas as outras atividades iniciais)
    ]

def get_next_month_year(current_month_year):
    """Retorna o próximo mês/ano com base no atual."""
    month, year = map(int, current_month_year.split('/'))
    if month == 12:
        return f"01/{year + 1}"
    return f"{str(month + 1).zfill(2)}/{year}"

def get_previous_month_year(current_month_year):
    """Retorna o mês/ano anterior com base no atual."""
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
    # ... (adicionar outras condições de cálculo de prazo)
    return datetime(ref_year, ref_month, 1) + timedelta(days=90)

def apply_status_style(status):
    """Aplica estilo CSS ao status da atividade."""
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
    """Aplica estilo CSS ao nível de dificuldade."""
    if dificuldade == "Baixa":
        return '<span class="dificuldade-badge dificuldade-baixa">Baixa</span>'
    elif dificuldade == "Média":
        return '<span class="dificuldade-badge dificuldade-media">Média</span>'
    elif dificuldade == "Alta":
        return '<span class="dificuldade-badge dificuldade-alta">Alta</span>'
    return f'<span class="dificuldade-badge">{dificuldade}</span>'

def calculate_days_remaining(row):
    """Calcula dias restantes para conclusão da atividade."""
    hoje = datetime.now()
    if pd.isna(row['Prazo']) or row['Status'] in ['Finalizado', 'Fechado']:
        return None
    prazo = row['Prazo']
    days = (prazo - hoje).days
    return days if days >= 0 else 0

def initialize_session_state():
    """Inicializa o estado da sessão do Streamlit."""
    if 'mes_ano_referencia' not in st.session_state:
        st.session_state.mes_ano_referencia = datetime.now().strftime('%m/%Y')
    
    if 'df_atividades' not in st.session_state:
        st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)

def show_navigation():
    """Mostra a navegação entre meses."""
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("Mês Anterior ◀️", key="btn_prev_month"):
            st.session_state.mes_ano_referencia = get_previous_month_year(st.session_state.mes_ano_referencia)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            st.rerun()
    
    with col_nav2:
        st.markdown(f"<h2 style='text-align: center;'>Mês/Ano de Referência: {st.session_state.mes_ano_referencia}</h2>", unsafe_allow_html=True)
    
    with col_nav3:
        if st.button("Próximo Mês ▶️", key="btn_next_month"):
            st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            st.rerun()

def show_metrics():
    """Mostra as métricas de status das atividades."""
    col1, col2, col3, col4, col5 = st.columns(5)
    df = st.session_state.df_atividades
    
    with col1:
        st.metric("Total de Atividades", len(df) if not df.empty else 0)
    with col2:
        st.metric("Pendentes", len(df[df['Status'] == "Pendente"]) if not df.empty else 0)
    with col3:
        st.metric("Em Andamento", len(df[df['Status'] == "Em Andamento"]) if not df.empty else 0)
    with col4:
        st.metric("Finalizadas", len(df[df['Status'] == "Finalizado"]) if not df.empty else 0)
    with col5:
        st.metric("Fechadas", len(df[df['Status'] == "Fechado"]) if not df.empty else 0)

def show_charts():
    """Mostra os gráficos de análise."""
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
                               color_discrete_map={
                                   'Pendente':'#ffc107', 
                                   'Em Andamento':'#007bff', 
                                   'Finalizado':'#28a745', 
                                   'Fechado':'#6c757d'
                               })
            st.plotly_chart(fig_status, use_container_width=True)

        with tab2:
            dificuldade_counts = st.session_state.df_atividades['Dificuldade'].value_counts().reset_index()
            dificuldade_counts.columns = ['Dificuldade', 'Quantidade']
            fig_dificuldade = px.bar(dificuldade_counts, x='Dificuldade', y='Quantidade',
                                   title='Distribuição por Nível de Dificuldade',
                                   color='Dificuldade',
                                   color_discrete_map={
                                       'Baixa':'#28a745', 
                                       'Média':'#ffc107', 
                                       'Alta':'#dc3545'
                                   })
            st.plotly_chart(fig_difficulty, use_container_width=True)

        with tab3:
            prazo_df = st.session_state.df_atividades.copy()
            for col in ['Prazo', 'DataInicio', 'DataConclusao']:
                if col not in prazo_df.columns:
                    prazo_df[col] = pd.NaT
                else:
                    prazo_df[col] = pd.to_datetime(prazo_df[col], errors='coerce')
            
            prazo_df = prazo_df.dropna(subset=['Prazo'])
            
            if not prazo_df.empty:
                prazo_df = prazo_df.sort_values('Prazo')
                prazo_df['Prazo Formatado'] = prazo_df['Prazo'].dt.strftime('%d/%m/%Y')
                prazo_df['Data Início Visual'] = prazo_df['DataInicio']
                prazo_df.loc[prazo_df['Data Início Visual'].isna(), 'Data Início Visual'] = prazo_df['Prazo'] - timedelta(days=1)

                fig_prazo = px.timeline(
                    prazo_df, 
                    x_start="Data Início Visual", 
                    x_end="Prazo", 
                    y="Obrigacao",
                    color="Status",
                    title='Linha do Tempo das Atividades',
                    color_discrete_map={
                        'Pendente':'#ffc107', 
                        'Em Andamento':'#007bff', 
                        'Finalizado':'#28a745', 
                        'Fechado':'#6c757d'
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
                fig_prazo.update_layout(showlegend=True)
                st.plotly_chart(fig_prazo, use_container_width=True)
            else:
                st.info("Não há atividades com prazo definido para exibir na linha do tempo.")
    else:
        st.info("Adicione atividades ou habilite um mês para ver as análises gráficas.")

def show_activities_table():
    """Mostra a tabela de atividades com filtros."""
    st.markdown("---")
    st.markdown('<div class="card animate-fadeIn"><h3>📋 Lista de Atividades</h3></div>', unsafe_allow_html=True)

    if st.session_state.df_atividades.empty:
        st.info("Nenhuma atividade encontrada para o mês selecionado.")
        return

    # Aplicar filtros
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox(
                "Status", 
                ["Todos", "Pendente", "Em Andamento", "Finalizado", "Fechado"], 
                key="filter_status"
            )
        with col2:
            difficulty_filter = st.selectbox(
                "Dificuldade", 
                ["Todos", "Baixa", "Média", "Alta"], 
                key="filter_difficulty"
            )
        with col3:
            orgao_options = ["Todos"] + list(st.session_state.df_atividades['OrgaoResponsavel'].unique())
            orgao_filter = st.selectbox(
                "Órgão Responsável", 
                orgao_options, 
                key="filter_orgao"
            )

    # Filtrar DataFrame
    filtered_df = st.session_state.df_atividades.copy()
    
    if status_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    if difficulty_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Dificuldade'] == difficulty_filter]
    if orgao_filter != "Todos":
        filtered_df = filtered_df[filtered_df['OrgaoResponsavel'] == orgao_filter]
    
    # Calcular dias restantes
    filtered_df['Dias Restantes'] = filtered_df.apply(calculate_days_remaining, axis=1)

    # Formatar DataFrame para exibição
    display_df = filtered_df.copy()
    display_df['Status'] = display_df['Status'].apply(apply_status_style)
    display_df['Dificuldade'] = display_df['Dificuldade'].apply(apply_difficulty_style)
    
    # Formatar datas
    for col in ['Prazo', 'DataInicio', 'DataConclusao']:
        if col in display_df.columns:
            display_df[col] = display_df[col].dt.strftime('%d/%m/%Y').replace({pd.NaT: ''})
        else:
            display_df[col] = ''

    # Selecionar colunas para exibição
    cols_to_display = [
        'Obrigacao', 'Descricao', 'Periodicidade', 'OrgaoResponsavel',
        'DataLimite', 'Status', 'Dificuldade', 'Prazo', 'Dias Restantes'
    ]
    
    # Garantir que as colunas existam
    cols_exist = [col for col in cols_to_display if col in display_df.columns]
    
    if not display_df.empty:
        st.write(display_df[cols_exist].to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.")

def show_add_activity_form():
    """Mostra o formulário para adicionar nova atividade."""
    st.markdown("---")
    with st.expander("➕ Adicionar Nova Atividade", expanded=False):
        with st.form("nova_atividade_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nova_obrigacao = st.text_input("Obrigação*", placeholder="Nome da obrigação fiscal", key="nova_obrigacao")
                nova_descricao = st.text_area("Descrição*", placeholder="Descrição detalhada da atividade", key="nova_descricao")
                nova_periodicidade = st.selectbox(
                    "Periodicidade*", 
                    ["Mensal", "Trimestral", "Anual", "Eventual", "Extinta"], 
                    key="nova_periodicidade"
                )
            with col2:
                novo_orgao = st.text_input("Órgão Responsável*", placeholder="Órgão responsável", key="novo_orgao")
                nova_data_limite = st.text_input(
                    "Data Limite de Entrega*", 
                    placeholder="Ex: Até o dia 10 do mês subsequente", 
                    key="nova_data_limite"
                )
                novo_status = st.selectbox(
                    "Status*", 
                    ["Pendente", "Em Andamento", "Finalizado", "Fechado"], 
                    key="novo_status"
                )
                nova_dificuldade = st.selectbox(
                    "Dificuldade*", 
                    ["Baixa", "Média", "Alta"], 
                    key="nova_dificuldade"
                )
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

                    if add_activity_to_db(nova_atividade):
                        st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                        st.success("✅ Atividade adicionada com sucesso!")
                        st.rerun()
                else:
                    st.error("⚠️ Preencha todos os campos obrigatórios (marcados com *)")

def show_edit_activity_form():
    """Mostra o formulário para editar atividades existentes."""
    st.markdown("---")
    with st.expander("✏️ Editar Atividades", expanded=False):
        if st.session_state.df_atividades.empty:
            st.info("Nenhuma atividade para editar. Adicione atividades ou habilite um novo mês.")
            return

        atividades_para_editar = st.session_state.df_atividades['Obrigacao'].unique()
        atividade_selecionada = st.selectbox(
            "Selecione a atividade para editar", 
            atividades_para_editar, 
            key="edit_select"
        )

        if not atividade_selecionada:
            return

        # Obter dados da atividade selecionada
        atividade_row = st.session_state.df_atividades[
            st.session_state.df_atividades['Obrigacao'] == atividade_selecionada
        ].iloc[0]
        
        atividade_id = atividade_row['id']
        current_status = atividade_row['Status']
        current_prazo = atividade_row['Prazo'].date() if pd.notna(atividade_row['Prazo']) else datetime.now().date()

        col1, col2 = st.columns(2)
        with col1:
            novo_status = st.selectbox(
                "Novo Status", 
                ["Pendente", "Em Andamento", "Finalizado", "Fechado"],
                index=["Pendente", "Em Andamento", "Finalizado", "Fechado"].index(current_status), 
                key="status_select"
            )
        with col2:
            novo_prazo = st.date_input(
                "Novo Prazo Final", 
                value=current_prazo, 
                key="prazo_date"
            )

        if st.button("Atualizar Atividade Selecionada", key="update_activity_btn"):
            updates = {}
            
            if novo_status != current_status:
                updates['Status'] = novo_status
                
                # Atualizar datas de início/conclusão conforme o status
                if novo_status == "Em Andamento" and pd.isna(atividade_row['DataInicio']):
                    updates['DataInicio'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                elif novo_status != "Em Andamento" and pd.notna(atividade_row['DataInicio']):
                    updates['DataInicio'] = None
                
                if novo_status == "Finalizado":
                    updates['DataConclusao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                elif novo_status != "Finalizado" and pd.notna(atividade_row['DataConclusao']):
                    updates['DataConclusao'] = None
            
            if novo_prazo != current_prazo:
                updates['Prazo'] = datetime.combine(novo_prazo, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
            
            if updates:
                if update_activity_in_db(atividade_id, updates):
                    st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                    st.success("✅ Atividade atualizada com sucesso!")
                    st.rerun()
            else:
                st.info("Nenhuma alteração detectada para atualizar.")

def show_close_period_section():
    """Mostra a seção para fechar o período atual."""
    st.markdown("---")
    st.markdown('<div class="card animate-fadeIn"><h3>🗓️ Fechamento e Habilitação de Período</h3></div>', unsafe_allow_html=True)

    if st.session_state.df_atividades.empty:
        st.info("Nenhuma atividade para fechar. Habilite um mês primeiro.")
        return

    todas_finalizadas_ou_fechadas = all(
        st.session_state.df_atividades['Status'].isin(["Finalizado", "Fechado"])
    )

    if todas_finalizadas_ou_fechadas:
        st.success(f"🎉 Todas as atividades para {st.session_state.mes_ano_referencia} estão finalizadas ou fechadas!")
        
        if st.button("Fechar Período e Habilitar Próximo Mês", key="fechar_periodo_btn"):
            # Fechar todas as atividades do mês atual
            conn = create_connection()
            if conn is not None:
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

            # Avançar para o próximo mês
            st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)

            # Se não houver atividades para o novo mês, criar as padrão
            if st.session_state.df_atividades.empty:
                st.warning(f"Não há dados para {st.session_state.mes_ano_referencia}. Gerando atividades padrão...")
                initial_templates = load_initial_data_template()
                activities_to_insert = []
                
                for activity in initial_templates:
                    prazo_calculated = calculate_deadline(activity['Data Limite'], st.session_state.mes_ano_referencia)
                    activity['Prazo'] = prazo_calculated.strftime('%Y-%m-%d %H:%M:%S') if prazo_calculated else None
                    activity['MesAnoReferencia'] = st.session_state.mes_ano_referencia
                    activity['Data Início'] = None
                    activity['Data Conclusão'] = None
                    activities_to_insert.append(activity)
                
                insert_initial_data(activities_to_insert)
                st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                st.success(f"Período de {get_previous_month_year(st.session_state.mes_ano_referencia)} fechado e atividades para {st.session_state.mes_ano_referencia} habilitadas com sucesso!")
            else:
                st.success(f"Período de {get_previous_month_year(st.session_state.mes_ano_referencia)} fechado e mês {st.session_state.mes_ano_referencia} habilitado com atividades já existentes!")
            
            st.rerun()
    else:
        st.warning(f"Ainda há atividades pendentes ou em andamento para {st.session_state.mes_ano_referencia}. Finalize-as para fechar o período.")

def main():
    """Função principal que orquestra a aplicação."""
    st.markdown('<div class="header animate-fadeIn"><h1>📊 Controle de Atividades Fiscais - HÄFELE BRASIL</h1></div>', unsafe_allow_html=True)

    # Inicializar banco de dados e estado da sessão
    create_table()
    initialize_session_state()

    # Verificar se há dados para o mês atual
    if st.session_state.df_atividades.empty:
        st.warning(f"Não há atividades cadastradas para {st.session_state.mes_ano_referencia}.")
        if st.button(f"Habilitar Mês {st.session_state.mes_ano_referencia}", key="habilitar_mes_btn"):
            initial_templates = load_initial_data_template()
            activities_to_insert = []
            
            for activity in initial_templates:
                prazo_calculated = calculate_deadline(activity['Data Limite'], st.session_state.mes_ano_referencia)
                activity['Prazo'] = prazo_calculated.strftime('%Y-%m-%d %H:%M:%S') if prazo_calculated else None
                activity['MesAnoReferencia'] = st.session_state.mes_ano_referencia
                activity['Data Início'] = None
                activity['Data Conclusão'] = None
                activities_to_insert.append(activity)
            
            insert_initial_data(activities_to_insert)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            st.success(f"Atividades padrão para {st.session_state.mes_ano_referencia} habilitadas com sucesso!")
            st.rerun()

    # Mostrar componentes da interface
    show_navigation()
    show_metrics()
    show_charts()
    show_activities_table()
    show_add_activity_form()
    show_edit_activity_form()
    show_close_period_section()

if __name__ == "__main__":
    main()
