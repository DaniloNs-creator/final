import streamlit as st
from streamlit import session_state as ss
import sqlite3
from datetime import datetime
import hashlib
import time
import pandas as pd
import plotly.express as px

# Configuração inicial do banco de dados
def init_db():
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT)''')
    
    # Tabela de tarefas
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  title TEXT,
                  description TEXT,
                  due_date TEXT,
                  due_time TEXT,
                  completed INTEGER DEFAULT 0,
                  created_at TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

init_db()

# Funções de autenticação
def create_user(username, password):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
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
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", 
             (username, hashed_password))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# Funções de tarefas
def add_task(user_id, title, description, due_date, due_time):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""INSERT INTO tasks 
                 (user_id, title, description, due_date, due_time, created_at) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
             (user_id, title, description, due_date, due_time, created_at))
    conn.commit()
    conn.close()

def get_tasks(user_id, filter_type="all"):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    
    if filter_type == "completed":
        c.execute("SELECT * FROM tasks WHERE user_id = ? AND completed = 1 ORDER BY due_date, due_time", (user_id,))
    elif filter_type == "pending":
        c.execute("SELECT * FROM tasks WHERE user_id = ? AND completed = 0 ORDER BY due_date, due_time", (user_id,))
    else:
        c.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY due_date, due_time", (user_id,))
    
    tasks = c.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, completed):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET completed = ? WHERE id = ?", (completed, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def get_task_stats(user_id):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,))
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1", (user_id,))
    completed = c.fetchone()[0]
    
    c.execute("""SELECT COUNT(*) FROM tasks 
                 WHERE user_id = ? AND completed = 0 
                 AND date(due_date) < date('now')""", (user_id,))
    overdue = c.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'completed': completed,
        'pending': total - completed,
        'overdue': overdue
    }

# Estilização CSS
def load_css():
    st.markdown("""
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #166088;
            --accent: #4fc3f7;
            --background: #f5f7fa;
            --text: #333333;
            --card: #ffffff;
            --success: #4caf50;
            --warning: #ff9800;
            --danger: #f44336;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--background);
            color: var(--text);
        }
        
        .stApp {
            background-color: var(--background);
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .auth-container {
            max-width: 500px;
            margin: 5rem auto;
            padding: 2rem;
            background-color: var(--card);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            animation: fadeIn 0.5s ease-in-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .task-card {
            background-color: var(--card);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            border-left: 4px solid var(--primary);
        }
        
        .task-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
        }
        
        .task-card.completed {
            border-left-color: var(--success);
            opacity: 0.8;
        }
        
        .task-card.overdue {
            border-left-color: var(--danger);
        }
        
        .task-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--secondary);
        }
        
        .task-due {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 0.5rem;
        }
        
        .task-actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 1rem;
        }
        
        .stats-card {
            background-color: var(--card);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        .stats-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary);
        }
        
        .stats-label {
            font-size: 0.9rem;
            color: #666;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background-color: var(--primary);
            color: white;
        }
        
        .btn-primary:hover {
            background-color: var(--secondary);
        }
        
        .btn-success {
            background-color: var(--success);
            color: white;
        }
        
        .btn-danger {
            background-color: var(--danger);
            color: white;
        }
        
        .btn-warning {
            background-color: var(--warning);
            color: white;
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-control {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }
        
        .filter-buttons {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--primary);
        }
        
        .user-info {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: var(--accent);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .progress-bar {
            height: 10px;
            background-color: #e0e0e0;
            border-radius: 5px;
            margin: 1rem 0;
            overflow: hidden;
        }
        
        .progress {
            height: 100%;
            background-color: var(--success);
            transition: width 0.5s ease;
        }
    </style>
    """, unsafe_allow_html=True)

# Página de autenticação
def auth_page():
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Cadastro"])
    
    with tab1:
        st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>Login</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Nome de usuário")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", type="primary")
            
            if submit:
                user_id = verify_user(username, password)
                if user_id:
                    ss.user_id = user_id
                    ss.username = username
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Tente novamente.")
    
    with tab2:
        st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>Cadastro</h2>", unsafe_allow_html=True)
        
        with st.form("register_form"):
            new_username = st.text_input("Escolha um nome de usuário")
            new_password = st.text_input("Escolha uma senha", type="password")
            confirm_password = st.text_input("Confirme a senha", type="password")
            submit = st.form_submit_button("Cadastrar", type="primary")
            
            if submit:
                if new_password != confirm_password:
                    st.error("As senhas não coincidem.")
                elif len(new_password) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres.")
                else:
                    if create_user(new_username, new_password):
                        st.success("Cadastro realizado com sucesso! Faça login para continuar.")
                    else:
                        st.error("Nome de usuário já existe. Escolha outro.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Página principal do aplicativo
def main_app():
    st.markdown("""
    <div class="header">
        <div class="logo">TaskMaster Pro</div>
        <div class="user-info">
            <div class="avatar pulse">{(ss.username[0].upper())}</div>
            <span>{ss.username}</span>
            <button class="btn btn-danger" onclick="window.streamlitApi.runMethod('logout')">Sair</button>
        </div>
    </div>
    """.format(ss.username), unsafe_allow_html=True)
    
    # Mostrar estatísticas
    stats = get_task_stats(ss.user_id)
    if stats['total'] > 0:
        completion_rate = (stats['completed'] / stats['total']) * 100
    else:
        completion_rate = 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-value">{stats['total']}</div>
            <div class="stats-label">Total de Tarefas</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-value" style="color: var(--success);">{stats['completed']}</div>
            <div class="stats-label">Concluídas</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-value" style="color: var(--warning);">{stats['pending']}</div>
            <div class="stats-label">Pendentes</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-value" style="color: var(--danger);">{stats['overdue']}</div>
            <div class="stats-label">Atrasadas</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="margin: 1.5rem 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span>Progresso geral</span>
            <span>{round(completion_rate, 1)}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress" style="width: {completion_rate}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Visualização de dados
    tasks_data = get_tasks(ss.user_id)
    if tasks_data:
        df = pd.DataFrame(tasks_data, columns=['id', 'user_id', 'title', 'description', 'due_date', 'due_time', 'completed', 'created_at'])
        df['due_datetime'] = pd.to_datetime(df['due_date'] + ' ' + df['due_time'])
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        fig = px.pie(df, names=df['completed'].map({0: 'Pendente', 1: 'Concluída'}), 
                     title="Distribuição de Tarefas",
                     hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de tarefas ao longo do tempo
        df['day'] = df['created_at'].dt.date
        timeline_df = df.groupby(['day', 'completed']).size().unstack().fillna(0)
        timeline_df.columns = ['Pendentes', 'Concluídas']
        
        fig2 = px.bar(timeline_df, x=timeline_df.index, y=['Pendentes', 'Concluídas'],
                      title="Tarefas Criadas ao Longo do Tempo",
                      labels={'value': 'Número de Tarefas', 'day': 'Data'})
        st.plotly_chart(fig2, use_container_width=True)
    
    # Filtros
    st.markdown("""
    <div class="filter-buttons">
        <button class="btn" onclick="window.streamlitApi.runMethod('set_filter', {filter: 'all'})">Todas</button>
        <button class="btn" onclick="window.streamlitApi.runMethod('set_filter', {filter: 'pending'})">Pendentes</button>
        <button class="btn" onclick="window.streamlitApi.runMethod('set_filter', {filter: 'completed'})">Concluídas</button>
    </div>
    """, unsafe_allow_html=True)
    
    # Adicionar nova tarefa
    with st.expander("➕ Adicionar Nova Tarefa", expanded=False):
        with st.form("new_task_form"):
            title = st.text_input("Título da Tarefa*", placeholder="O que precisa ser feito?")
            description = st.text_area("Descrição", placeholder="Detalhes da tarefa...")
            col1, col2 = st.columns(2)
            with col1:
                due_date = st.date_input("Data de Vencimento*", min_value=datetime.today())
            with col2:
                due_time = st.time_input("Hora de Vencimento*", value=datetime.strptime("23:59", "%H:%M"))
            
            submitted = st.form_submit_button("Adicionar Tarefa", type="primary")
            
            if submitted:
                if not title:
                    st.error("O título da tarefa é obrigatório!")
                else:
                    add_task(ss.user_id, title, description, str(due_date), due_time.strftime("%H:%M"))
                    st.success("Tarefa adicionada com sucesso!")
                    time.sleep(1)
                    st.rerun()
    
    # Lista de tarefas
    filter_type = ss.get('filter', 'all')
    tasks = get_tasks(ss.user_id, filter_type)
    
    if not tasks:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; color: #666;">
            <h3>Nenhuma tarefa encontrada</h3>
            <p>Adicione uma nova tarefa para começar!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for task in tasks:
            task_id, _, title, description, due_date, due_time, completed, created_at = task
            due_datetime = datetime.strptime(f"{due_date} {due_time}", "%Y-%m-%d %H:%M")
            is_overdue = not completed and due_datetime < datetime.now()
            
            card_class = "task-card"
            if completed:
                card_class += " completed"
            elif is_overdue:
                card_class += " overdue"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div class="task-title">{title}</div>
                <div class="task-due">
                    <strong>Prazo:</strong> {due_date} às {due_time}
                    {is_overdue and not completed and '<span style="color: var(--danger); margin-left: 0.5rem;">(Atrasada)</span>' or ''}
                </div>
                <p>{description or 'Sem descrição'}</p>
                <div class="task-actions">
                    <button class="btn {'btn-warning' if completed else 'btn-success'}" 
                            onclick="window.streamlitApi.runMethod('toggle_task', {{task_id: {task_id}, completed: {0 if completed else 1}}})">
                        {'Marcar como Pendente' if completed else 'Concluir'}
                    </button>
                    <button class="btn btn-danger" 
                            onclick="window.streamlitApi.runMethod('delete_task', {{task_id: {task_id}}})">
                        Excluir
                    </button>
                </div>
            </div>
            """, unsafe_allow_html=True)

# Configuração principal do Streamlit
def main():
    load_css()
    
    # Verificar parâmetros de query
    query_params = st.query_params
    
    if 'logout' in query_params:
        if 'user_id' in ss:
            del ss.user_id
            del ss.username
        st.query_params.clear()
        st.rerun()
    
    if 'toggle_task' in query_params:
        task_id = int(query_params['toggle_task']['task_id'])
        completed = int(query_params['toggle_task']['completed'])
        update_task_status(task_id, completed)
        st.query_params.clear()
        st.rerun()
    
    if 'delete_task' in query_params:
        task_id = int(query_params['delete_task']['task_id'])
        delete_task(task_id)
        st.query_params.clear()
        st.rerun()
    
    if 'set_filter' in query_params:
        ss.filter = query_params['set_filter']['filter']
        st.query_params.clear()
        st.rerun()
    
    # Verificar autenticação
    if 'user_id' not in ss:
        auth_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
