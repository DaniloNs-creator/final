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

# CSS personalizado (mantido igual ao anterior)
st.markdown("""
<style>
    /* Seu CSS permanece exatamente igual */
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
    conn = create_connection()
    if conn:
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
            return True
        except sqlite3.Error as e:
            st.error(f"Erro ao adicionar atividade: {e}")
            return False
        finally:
            conn.close()
    return False

# ... (funções auxiliares como load_initial_data_template, get_next_month_year, etc. permanecem iguais)

def apply_status_style(status):
    status_map = {
        "Pendente": '<span class="status-badge status-pendente">Pendente</span>',
        "Em Andamento": '<span class="status-badge status-andamento">Em Andamento</span>',
        "Finalizado": '<span class="status-badge status-finalizado">Finalizado</span>',
        "Fechado": '<span class="status-badge status-fechado">Fechado</span>'
    }
    return status_map.get(status, f'<span class="status-badge">{status}</span>')

def apply_difficulty_style(dificuldade):
    dificuldade_map = {
        "Baixa": '<span class="dificuldade-badge dificuldade-baixa">Baixa</span>',
        "Média": '<span class="dificuldade-badge dificuldade-media">Média</span>',
        "Alta": '<span class="dificuldade-badge dificuldade-alta">Alta</span>'
    }
    return dificuldade_map.get(dificuldade, f'<span class="dificuldade-badge">{dificuldade}</span>')

def calculate_days_remaining(row):
    hoje = datetime.now()
    if pd.isna(row['Prazo']) or row['Status'] in ['Finalizado', 'Fechado']:
        return None
    prazo = row['Prazo']
    days = (prazo - hoje).days
    return days if days >= 0 else 0

def main():
    st.markdown('<div class="header animate-fadeIn"><h1>📊 Controle de Atividades Fiscais - HÄFELE BRASIL</h1></div>', unsafe_allow_html=True)

    # Inicialização do estado da sessão
    if 'mes_ano_referencia' not in st.session_state:
        st.session_state.mes_ano_referencia = datetime.now().strftime('%m/%Y')
    
    if 'df_atividades' not in st.session_state:
        st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)

    # Navegação entre meses
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("Mês Anterior ◀️"):
            st.session_state.mes_ano_referencia = get_previous_month_year(st.session_state.mes_ano_referencia)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            st.rerun()
    
    with col_nav2:
        st.markdown(f"<h2 style='text-align: center;'>Mês/Ano de Referência: {st.session_state.mes_ano_referencia}</h2>", unsafe_allow_html=True)
    
    with col_nav3:
        if st.button("Próximo Mês ▶️"):
            st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            st.rerun()

    # Seção de edição de atividades (revisada para corrigir o problema de atualização)
    st.markdown("---")
    with st.expander("✏️ Editar Atividades", expanded=True):
        if not st.session_state.df_atividades.empty:
            atividades_para_editar = st.session_state.df_atividades['Obrigacao'].unique()
            atividade_selecionada = st.selectbox(
                "Selecione a atividade para editar", 
                atividades_para_editar, 
                key="edit_select"
            )

            if atividade_selecionada:
                atividade_row = st.session_state.df_atividades[
                    st.session_state.df_atividades['Obrigacao'] == atividade_selecionada
                ].iloc[0]
                
                atividade_id = atividade_row['id']
                current_status = atividade_row['Status']
                
                # Obter a data atual como fallback
                current_prazo = atividade_row['Prazo'].date() if pd.notna(atividade_row['Prazo']) else datetime.now().date()
                current_data_inicio = atividade_row['DataInicio'].date() if pd.notna(atividade_row['DataInicio']) else None
                current_data_conclusao = atividade_row['DataConclusao'].date() if pd.notna(atividade_row['DataConclusao']) else None

                col1, col2 = st.columns(2)
                with col1:
                    novo_status = st.selectbox(
                        "Status",
                        ["Pendente", "Em Andamento", "Finalizado", "Fechado"],
                        index=["Pendente", "Em Andamento", "Finalizado", "Fechado"].index(current_status),
                        key="status_select"
                    )
                
                with col2:
                    novo_prazo = st.date_input(
                        "Prazo Final",
                        value=current_prazo,
                        key="prazo_date"
                    )

                # Atualizar datas automaticamente conforme o status
                data_inicio = current_data_inicio
                data_conclusao = current_data_conclusao
                
                if novo_status == "Em Andamento" and current_status != "Em Andamento":
                    data_inicio = datetime.now().date()
                
                if novo_status == "Finalizado" and current_status != "Finalizado":
                    data_conclusao = datetime.now().date()
                
                if st.button("Atualizar Atividade", key="update_activity_btn"):
                    updates = {
                        'Status': novo_status,
                        'Prazo': datetime.combine(novo_prazo, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Atualizar datas conforme necessário
                    if novo_status == "Em Andamento":
                        updates['DataInicio'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    elif novo_status != "Em Andamento" and current_status == "Em Andamento":
                        updates['DataInicio'] = None
                    
                    if novo_status == "Finalizado":
                        updates['DataConclusao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    elif novo_status != "Finalizado" and current_status == "Finalizado":
                        updates['DataConclusao'] = None
                    
                    if update_activity_in_db(atividade_id, updates):
                        st.success("Atividade atualizada com sucesso!")
                        # Recarregar os dados do banco
                        st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar atividade no banco de dados")
        else:
            st.info("Nenhuma atividade disponível para edição")

    # ... (restante do código permanece igual)

if __name__ == "__main__":
    create_table()  # Garante que a tabela existe
    main()
