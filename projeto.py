import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
import plotly.express as px
from streamlit.components.v1 import html

# Configuração inicial do banco de dados
def init_db():
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de tarefas
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            due_date TIMESTAMP,
            priority INTEGER DEFAULT 2,
            status INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Funções de autenticação
def create_user(username, password):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                 (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    c.execute('SELECT id FROM users WHERE username = ? AND password = ?', 
             (username, hashed_password))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# Funções de gerenciamento de tarefas
def add_task(user_id, title, description, due_date, priority):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO tasks (user_id, title, description, due_date, priority)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, title, description, due_date, priority))
    conn.commit()
    conn.close()

def get_tasks(user_id, status=None):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    
    if status is not None:
        c.execute('''
            SELECT id, title, description, due_date, priority, status 
            FROM tasks 
            WHERE user_id = ? AND status = ?
            ORDER BY due_date, priority
        ''', (user_id, status))
    else:
        c.execute('''
            SELECT id, title, description, due_date, priority, status 
            FROM tasks 
            WHERE user_id = ? 
            ORDER BY due_date, priority
        ''', (user_id,))
    
    tasks = c.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

# Funções para análise de progresso
def get_task_stats(user_id):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    
    # Total de tarefas
    c.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (user_id,))
    total = c.fetchone()[0]
    
    # Tarefas completas
    c.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 1', (user_id,))
    completed = c.fetchone()[0]
    
    # Tarefas por prioridade
    c.execute('''
        SELECT priority, COUNT(*) 
        FROM tasks 
        WHERE user_id = ? AND status = 0
        GROUP BY priority
        ORDER BY priority
    ''', (user_id,))
    priority_counts = c.fetchall()
    
    conn.close()
    
    return {
        'total': total,
        'completed': completed,
        'priority_counts': priority_counts
    }

# CSS personalizado e animações
def load_css():
    st.markdown("""
        <style>
            :root {
                --primary: #4a6fa5;
                --secondary: #166088;
                --accent: #4fc3f7;
                --background: #f5f7fa;
                --text: #333333;
                --success: #4caf50;
                --warning: #ff9800;
                --danger: #f44336;
            }
            
            /* Estilos gerais */
            .stApp {
                background-color: var(--background);
                color: var(--text);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            /* Header */
            .header {
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                color: white;
                padding: 1rem;
                border-radius: 0 0 10px 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 2rem;
                animation: fadeIn 0.5s ease-in-out;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            /* Cards de tarefa */
            .task-card {
                background: white;
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1rem;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                transition: all 0.3s ease;
                border-left: 4px solid var(--primary);
            }
            
            .task-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
            }
            
            .task-card.high-priority {
                border-left-color: var(--danger);
            }
            
            .task-card.medium-priority {
                border-left-color: var(--warning);
            }
            
            .task-card.low-priority {
                border-left-color: var(--success);
            }
            
            /* Botões */
            .stButton>button {
                border-radius: 20px;
                border: none;
                padding: 0.5rem 1rem;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            
            .stButton>button:hover {
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
            
            .primary-button {
                background-color: var(--primary) !important;
                color: white !important;
            }
            
            .secondary-button {
                background-color: var(--secondary) !important;
                color: white !important;
            }
            
            /* Formulários */
            .stTextInput>div>div>input, 
            .stTextArea>div>div>textarea,
            .stDateInput>div>div>input,
            .stTimeInput>div>div>input,
            .stSelectbox>div>div>select {
                border-radius: 8px !important;
                border: 1px solid #ddd !important;
                padding: 0.5rem 1rem !important;
            }
            
            /* Progresso */
            .progress-container {
                background: white;
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1rem;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }
            
            /* Animações */
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            .pulse {
                animation: pulse 2s infinite;
            }
            
            /* Login container */
            .login-container {
                max-width: 400px;
                margin: 0 auto;
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                animation: slideUp 0.5s ease-out;
            }
            
            @keyframes slideUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            /* Responsividade */
            @media (max-width: 768px) {
                .login-container {
                    padding: 1rem;
                }
            }
        </style>
    """, unsafe_allow_html=True)

# Página de login/cadastro
def login_page():
    load_css()
    
    st.markdown("""
        <div class="login-container">
            <h2 style="text-align: center; color: var(--primary); margin-bottom: 1.5rem;">Organizador de Tarefas</h2>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Cadastro"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Nome de usuário")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", type="primary")
            
            if submit:
                user_id = verify_user(username, password)
                if user_id:
                    st.session_state['user_id'] = user_id
                    st.session_state['username'] = username
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Por favor, tente novamente.")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Escolha um nome de usuário")
            new_password = st.text_input("Crie uma senha", type="password")
            confirm_password = st.text_input("Confirme a senha", type="password")
            register = st.form_submit_button("Cadastrar", type="primary")
            
            if register:
                if new_password != confirm_password:
                    st.error("As senhas não coincidem.")
                elif len(new_password) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres.")
                else:
                    if create_user(new_username, new_password):
                        st.success("Cadastro realizado com sucesso! Faça login para continuar.")
                    else:
                        st.error("Nome de usuário já em uso. Por favor, escolha outro.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Página principal do aplicativo
def main_app():
    load_css()
    
    # Header
    st.markdown(f"""
        <div class="header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h1 style="margin: 0;">Organizador de Tarefas</h1>
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <span style="font-weight: 500;">Olá, {st.session_state['username']}</span>
                    <button onclick="logout()" style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 0.5rem 1rem; border-radius: 20px; cursor: pointer; transition: all 0.3s;">Sair</button>
                </div>
            </div>
        </div>
        
        <script>
            function logout() {
                window.location.href = window.location.href.split('?')[0] + '?logout=true';
            }
        </script>
    """, unsafe_allow_html=True)
    
    # Verificar se o usuário clicou em sair
    query_params = st.query_params
    if 'logout' in query_params and query_params['logout'] == 'true':
        del st.session_state['user_id']
        del st.session_state['username']
        st.rerun()
    
    # Abas principais
    tab1, tab2, tab3 = st.tabs(["Minhas Tarefas", "Adicionar Tarefa", "Progresso"])
    
    with tab1:
        st.subheader("Minhas Tarefas")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            filter_status = st.selectbox("Filtrar por status", ["Todas", "Pendentes", "Concluídas"])
        
        # Lista de tarefas
        if filter_status == "Todas":
            tasks = get_tasks(st.session_state['user_id'])
        elif filter_status == "Pendentes":
            tasks = get_tasks(st.session_state['user_id'], 0)
        else:
            tasks = get_tasks(st.session_state['user_id'], 1)
        
        if not tasks:
            st.info("Nenhuma tarefa encontrada.")
        else:
            for task in tasks:
                task_id, title, description, due_date, priority, status = task
                
                priority_class = ""
                if priority == 1:
                    priority_class = "high-priority"
                elif priority == 2:
                    priority_class = "medium-priority"
                elif priority == 3:
                    priority_class = "low-priority"
                
                due_date_str = datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M") if due_date else "Sem data definida"
                
                st.markdown(f"""
                    <div class="task-card {priority_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <h3 style="margin: 0;">{title}</h3>
                            <div style="display: flex; gap: 0.5rem;">
                                <button onclick="completeTask({task_id})" style="background: var(--success); color: white; border: none; border-radius: 20px; padding: 0.25rem 0.75rem; cursor: pointer; font-size: 0.8rem;">{'✔️ Concluída' if status else '✓ Concluir'}</button>
                                <button onclick="deleteTask({task_id})" style="background: var(--danger); color: white; border: none; border-radius: 20px; padding: 0.25rem 0.75rem; cursor: pointer; font-size: 0.8rem;">🗑️ Excluir</button>
                            </div>
                        </div>
                        <p style="margin: 0.5rem 0; color: #555;">{description or 'Sem descrição'}</p>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <small style="color: #777;">{due_date_str}</small>
                            <small style="color: #777;">{'Alta prioridade' if priority == 1 else 'Média prioridade' if priority == 2 else 'Baixa prioridade'}</small>
                        </div>
                    </div>
                    
                    <script>
                        function completeTask(taskId) {
                            window.location.href = window.location.href.split('?')[0] + '?complete_task=' + taskId;
                        }
                        
                        function deleteTask(taskId) {
                            if (confirm('Tem certeza que deseja excluir esta tarefa?')) {
                                window.location.href = window.location.href.split('?')[0] + '?delete_task=' + taskId;
                            }
                        }
                    </script>
                """, unsafe_allow_html=True)
        
        # Verificar ações nas tarefas
        if 'complete_task' in query_params:
            task_id = int(query_params['complete_task'])
            update_task_status(task_id, 1)
            st.rerun()
        
        if 'delete_task' in query_params:
            task_id = int(query_params['delete_task'])
            delete_task(task_id)
            st.rerun()
    
    with tab2:
        st.subheader("Adicionar Nova Tarefa")
        
        with st.form("add_task_form", clear_on_submit=True):
            title = st.text_input("Título da Tarefa*", placeholder="Digite o título da tarefa")
            description = st.text_area("Descrição", placeholder="Detalhes sobre a tarefa (opcional)")
            col1, col2 = st.columns(2)
            with col1:
                due_date = st.date_input("Data de Vencimento")
            with col2:
                due_time = st.time_input("Hora de Vencimento")
            priority = st.selectbox("Prioridade", ["Alta", "Média", "Baixa"], index=1)
            
            submitted = st.form_submit_button("Adicionar Tarefa", type="primary")
            
            if submitted:
                if not title:
                    st.error("O título da tarefa é obrigatório!")
                else:
                    due_datetime = datetime.combine(due_date, due_time) if due_date and due_time else None
                    priority_map = {"Alta": 1, "Média": 2, "Baixa": 3}
                    
                    add_task(
                        st.session_state['user_id'],
                        title,
                        description,
                        due_datetime.strftime("%Y-%m-%d %H:%M:%S") if due_datetime else None,
                        priority_map[priority]
                    )
                    
                    st.success("Tarefa adicionada com sucesso!")
                    st.balloons()
    
    with tab3:
        st.subheader("Meu Progresso")
        
        stats = get_task_stats(st.session_state['user_id'])
        
        if stats['total'] == 0:
            st.info("Você ainda não tem tarefas cadastradas.")
        else:
            # Progresso geral
            progress = (stats['completed'] / stats['total']) * 100 if stats['total'] > 0 else 0
            st.markdown(f"""
                <div class="progress-container">
                    <h3 style="margin-top: 0;">Progresso Geral</h3>
                    <div style="background: #e0e0e0; border-radius: 20px; height: 20px; margin-bottom: 0.5rem;">
                        <div style="background: linear-gradient(90deg, var(--primary), var(--accent)); width: {progress}%; height: 100%; border-radius: 20px; transition: width 1s ease;"></div>
                    </div>
                    <p style="text-align: center; font-weight: 500; margin: 0;">{stats['completed']} de {stats['total']} tarefas concluídas ({progress:.1f}%)</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Gráfico de prioridades
            if stats['priority_counts']:
                df_priority = pd.DataFrame(stats['priority_counts'], columns=['Prioridade', 'Quantidade'])
                df_priority['Prioridade'] = df_priority['Prioridade'].map({1: 'Alta', 2: 'Média', 3: 'Baixa'})
                
                fig = px.pie(
                    df_priority, 
                    values='Quantidade', 
                    names='Prioridade', 
                    title='Tarefas Pendentes por Prioridade',
                    color='Prioridade',
                    color_discrete_map={'Alta': '#f44336', 'Média': '#ff9800', 'Baixa': '#4caf50'}
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Tarefas recentes
            recent_tasks = get_tasks(st.session_state['user_id'])[:5]
            if recent_tasks:
                st.subheader("Tarefas Recentes")
                for task in recent_tasks:
                    task_id, title, _, due_date, priority, status = task
                    due_date_str = datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y") if due_date else "Sem data"
                    st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem;">
                            <span>{title}</span>
                            <div style="display: flex; align-items: center; gap: 1rem;">
                                <small>{due_date_str}</small>
                                <span style="color: {'var(--success)' if status else 'var(--danger)'}; font-size: 0.8rem;">
                                    {'✔️ Concluída' if status else '⏳ Pendente'}
                                </span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

# Ponto de entrada do aplicativo
def main():
    if 'user_id' not in st.session_state:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
