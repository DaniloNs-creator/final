import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit.components.v1 as components

# Configuração inicial do banco de dados
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 title TEXT NOT NULL,
                 description TEXT,
                 priority INTEGER,
                 due_date TEXT,
                 status TEXT DEFAULT 'pending',
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# CSS personalizado com animações
def local_css():
    st.markdown("""
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #166088;
            --accent: #4fc3f7;
            --light: #f8f9fa;
            --dark: #343a40;
            --success: #28a745;
            --warning: #ffc107;
            --danger: #dc3545;
        }
        
        /* Estilos gerais */
        .stApp {
            background-color: #f5f7fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        /* Header estilizado */
        .header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            padding: 1.5rem;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            animation: fadeInDown 0.8s ease-out;
        }
        
        /* Cards de tarefa */
        .task-card {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
            padding: 1.5rem;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
            border-left: 4px solid var(--primary);
        }
        
        .task-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .task-card.completed {
            border-left-color: var(--success);
            opacity: 0.8;
            background-color: #f8f9fa;
        }
        
        .task-card.high-priority {
            border-left-color: var(--danger);
        }
        
        .task-card.medium-priority {
            border-left-color: var(--warning);
        }
        
        /* Botões */
        .stButton>button {
            border-radius: 20px;
            padding: 0.5rem 1.5rem;
            transition: all 0.3s;
            border: none;
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        
        .primary-btn {
            background-color: var(--primary) !important;
            color: white !important;
        }
        
        .secondary-btn {
            background-color: var(--secondary) !important;
            color: white !important;
        }
        
        /* Animações */
        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0% {
                transform: scale(1);
            }
            50% {
                transform: scale(1.05);
            }
            100% {
                transform: scale(1);
            }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        /* Formulário */
        .stTextInput>div>div>input, 
        .stTextArea>div>div>textarea, 
        .stDateInput>div>div>input, 
        .stSelectbox>div>div>select {
            border-radius: 8px !important;
            padding: 10px !important;
            border: 1px solid #ced4da !important;
        }
        
        /* Progress bar */
        .stProgress>div>div>div {
            background-color: var(--primary) !important;
            border-radius: 10px;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px !important;
            padding: 10px 20px !important;
            transition: all 0.3s;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: var(--primary) !important;
            color: white !important;
        }
        
        /* Responsividade */
        @media (max-width: 768px) {
            .header {
                padding: 1rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)

# Funções CRUD para tarefas
def add_task(title, description, priority, due_date):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (title, description, priority, due_date) VALUES (?, ?, ?, ?)",
              (title, description, priority, due_date))
    conn.commit()
    conn.close()

def get_tasks(status=None):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    if status:
        c.execute("SELECT * FROM tasks WHERE status=? ORDER BY priority DESC, due_date ASC", (status,))
    else:
        c.execute("SELECT * FROM tasks ORDER BY priority DESC, due_date ASC")
    tasks = c.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def get_task_by_id(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
    task = c.fetchone()
    conn.close()
    return task

def update_task(task_id, title, description, priority, due_date):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET title=?, description=?, priority=?, due_date=? WHERE id=?",
              (title, description, priority, due_date, task_id))
    conn.commit()
    conn.close()

# Função para exibir estatísticas
def show_stats():
    conn = sqlite3.connect('tasks.db')
    df = pd.read_sql_query("SELECT status, COUNT(*) as count FROM tasks GROUP BY status", conn)
    conn.close()
    
    total_tasks = df['count'].sum()
    completed_tasks = df[df['status'] == 'completed']['count'].sum() if 'completed' in df['status'].values else 0
    pending_tasks = df[df['status'] == 'pending']['count'].sum() if 'pending' in df['status'].values else 0
    
    if total_tasks > 0:
        completion_rate = (completed_tasks / total_tasks) * 100
    else:
        completion_rate = 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Tarefas", total_tasks)
    with col2:
        st.metric("Tarefas Concluídas", completed_tasks)
    with col3:
        st.metric("Taxa de Conclusão", f"{completion_rate:.1f}%")
    
    st.progress(int(completion_rate))

# Função principal
def main():
    # Inicializar banco de dados e CSS
    init_db()
    local_css()
    
    # Header personalizado
    st.markdown("""
    <div class="header">
        <h1 style="margin:0; font-size:2.2rem;">📋 Organizador de Tarefas</h1>
        <p style="margin:0; opacity:0.8;">Gerencie suas tarefas de forma eficiente</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Abas para diferentes seções
    tab1, tab2, tab3, tab4 = st.tabs(["📌 Minhas Tarefas", "➕ Adicionar Tarefa", "📊 Estatísticas", "⚙️ Configurações"])
    
    with tab1:
        st.subheader("Suas Tarefas")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            filter_status = st.selectbox("Filtrar por status", ["Todas", "Pendentes", "Concluídas"])
        with col2:
            filter_priority = st.selectbox("Filtrar por prioridade", ["Todas", "Alta", "Média", "Baixa"])
        
        # Obter tarefas com base nos filtros
        if filter_status == "Todas":
            tasks = get_tasks()
        elif filter_status == "Pendentes":
            tasks = get_tasks("pending")
        else:
            tasks = get_tasks("completed")
        
        # Aplicar filtro de prioridade
        if filter_priority != "Todas":
            priority_map = {"Alta": 3, "Média": 2, "Baixa": 1}
            tasks = [task for task in tasks if task[3] == priority_map[filter_priority]]
        
        if not tasks:
            st.info("Nenhuma tarefa encontrada com os filtros selecionados.")
        else:
            for task in tasks:
                task_id, title, description, priority, due_date, status, created_at = task
                
                # Determinar classe CSS com base no status e prioridade
                card_class = "task-card"
                if status == "completed":
                    card_class += " completed"
                
                if priority == 3:
                    card_class += " high-priority"
                elif priority == 2:
                    card_class += " medium-priority"
                
                # Formatar data
                due_date_str = datetime.strptime(due_date, "%Y-%m-%d").strftime("%d/%m/%Y") if due_date else "Sem data"
                priority_str = {1: "Baixa", 2: "Média", 3: "Alta"}.get(priority, "Desconhecida")
                
                # Exibir card da tarefa
                st.markdown(f"""
                <div class="{card_class}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h3 style="margin:0;">{title}</h3>
                        <div style="display:flex; gap:10px;">
                            <span style="background:{'#28a745' if status == 'completed' else '#ffc107'}; color:white; padding:2px 8px; border-radius:10px; font-size:0.8rem;">
                                {'✅ Concluída' if status == 'completed' else '⏳ Pendente'}
                            </span>
                            <span style="background:#f8f9fa; color:#495057; padding:2px 8px; border-radius:10px; font-size:0.8rem;">
                                {priority_str} Prioridade
                            </span>
                        </div>
                    </div>
                    <p style="margin:10px 0; color:#495057;">{description or 'Sem descrição'}</p>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <small style="color:#6c757d;">📅 {due_date_str}</small>
                        <div style="display:flex; gap:5px;">
                """, unsafe_allow_html=True)
                
                col1, col2, col3, _ = st.columns([1,1,1,5])
                with col1:
                    if status == "pending":
                        if st.button("✅ Concluir", key=f"complete_{task_id}"):
                            update_task_status(task_id, "completed")
                            st.rerun()
                with col2:
                    if st.button("✏️ Editar", key=f"edit_{task_id}"):
                        st.session_state['edit_task_id'] = task_id
                        st.session_state['edit_title'] = title
                        st.session_state['edit_description'] = description
                        st.session_state['edit_priority'] = priority
                        st.session_state['edit_due_date'] = due_date
                        st.rerun()
                with col3:
                    if st.button("🗑️ Excluir", key=f"delete_{task_id}"):
                        delete_task(task_id)
                        st.rerun()
                
                st.markdown("""
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        st.subheader("Adicionar Nova Tarefa")
        
        # Formulário para adicionar nova tarefa
        with st.form("add_task_form", clear_on_submit=True):
            title = st.text_input("Título*", placeholder="Digite o título da tarefa")
            description = st.text_area("Descrição", placeholder="Digite uma descrição detalhada (opcional)")
            col1, col2 = st.columns(2)
            with col1:
                priority = st.selectbox("Prioridade*", [("Baixa", 1), ("Média", 2), ("Alta", 3)], format_func=lambda x: x[0])
                priority = priority[1]
            with col2:
                due_date = st.date_input("Data de Vencimento", min_value=datetime.today())
            
            submitted = st.form_submit_button("Adicionar Tarefa", type="primary")
            
            if submitted:
                if not title:
                    st.error("O título da tarefa é obrigatório!")
                else:
                    add_task(title, description, priority, due_date.strftime("%Y-%m-%d"))
                    st.success("Tarefa adicionada com sucesso!")
                    st.balloons()
    
    with tab3:
        st.subheader("Estatísticas de Produtividade")
        show_stats()
        
        # Gráfico de status
        conn = sqlite3.connect('tasks.db')
        df = pd.read_sql_query("SELECT status, COUNT(*) as count FROM tasks GROUP BY status", conn)
        conn.close()
        
        if not df.empty:
            st.bar_chart(df.set_index('status'))
        else:
            st.info("Nenhuma tarefa cadastrada para exibir estatísticas.")
    
    with tab4:
        st.subheader("Configurações")
        st.write("Personalize seu organizador de tarefas")
        
        # Tema
        theme = st.selectbox("Tema", ["Claro", "Escuro"], index=0)
        
        # Animations toggle
        animations = st.toggle("Ativar animações", value=True)
        
        if st.button("Limpar Todas as Tarefas", type="secondary"):
            if st.checkbox("Confirmar exclusão de TODAS as tarefas?"):
                conn = sqlite3.connect('tasks.db')
                c = conn.cursor()
                c.execute("DELETE FROM tasks")
                conn.commit()
                conn.close()
                st.success("Todas as tarefas foram removidas!")
    
    # Modal de edição (aparece quando um botão de editar é clicado)
    if 'edit_task_id' in st.session_state:
        with st.expander("✏️ Editar Tarefa", expanded=True):
            with st.form("edit_task_form"):
                title = st.text_input("Título*", value=st.session_state['edit_title'])
                description = st.text_area("Descrição", value=st.session_state['edit_description'])
                col1, col2 = st.columns(2)
                with col1:
                    priority = st.selectbox("Prioridade*", 
                                          [("Baixa", 1), ("Média", 2), ("Alta", 3)], 
                                          index=st.session_state['edit_priority']-1,
                                          format_func=lambda x: x[0])
                    priority = priority[1]
                with col2:
                    due_date = st.date_input("Data de Vencimento", 
                                           value=datetime.strptime(st.session_state['edit_due_date'], "%Y-%m-%d") if st.session_state['edit_due_date'] else datetime.today())
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Salvar Alterações", type="primary"):
                        if not title:
                            st.error("O título da tarefa é obrigatório!")
                        else:
                            update_task(st.session_state['edit_task_id'], title, description, priority, due_date.strftime("%Y-%m-%d"))
                            del st.session_state['edit_task_id']
                            st.rerun()
                with col2:
                    if st.form_submit_button("Cancelar"):
                        del st.session_state['edit_task_id']
                        st.rerun()

if __name__ == "__main__":
    main()
