import streamlit as st
import sqlite3
import hashlib
import time
from datetime import datetime
import streamlit.components.v1 as components

# Configuração inicial do banco de dados
def init_db():
    conn = sqlite3.connect('tasks.db')
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
                 priority INTEGER,
                 completed INTEGER DEFAULT 0,
                 created_at TEXT,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

init_db()

# Funções do banco de dados
def create_user(username, password):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                 (username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", 
             (username, hashed_pw))
    user_id = c.fetchone()
    conn.close()
    return user_id[0] if user_id else None

def add_task(user_id, title, description, due_date, priority):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO tasks (user_id, title, description, due_date, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)",
             (user_id, title, description, due_date, priority, created_at))
    conn.commit()
    conn.close()

def get_tasks(user_id, show_completed=False):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    if show_completed:
        c.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY priority DESC, due_date", (user_id,))
    else:
        c.execute("SELECT * FROM tasks WHERE user_id = ? AND completed = 0 ORDER BY priority DESC, due_date", (user_id,))
    tasks = c.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, completed):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET completed = ? WHERE id = ?", (completed, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# CSS personalizado
def load_css():
    st.markdown("""
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #166088;
            --accent: #4fc3f7;
            --background: #f5f7fa;
            --card: #ffffff;
            --text: #333333;
            --success: #4caf50;
            --warning: #ff9800;
            --danger: #f44336;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: var(--background);
            color: var(--text);
        }
        
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }
        
        .auth-container {
            max-width: 500px;
            margin: 5rem auto;
            padding: 2rem;
            background-color: var(--card);
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            animation: fadeIn 0.6s ease-out;
        }
        
        .auth-title {
            text-align: center;
            color: var(--secondary);
            margin-bottom: 1.5rem;
            font-weight: 600;
        }
        
        .auth-input {
            margin-bottom: 1.5rem;
        }
        
        .auth-button {
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 8px;
            background-color: var(--primary);
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 1rem;
        }
        
        .auth-button:hover {
            background-color: var(--secondary);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .auth-link {
            text-align: center;
            margin-top: 1rem;
            color: var(--secondary);
            cursor: pointer;
            transition: color 0.3s ease;
        }
        
        .auth-link:hover {
            color: var(--primary);
            text-decoration: underline;
        }
        
        .task-container {
            max-width: 800px;
            margin: 2rem auto;
            animation: slideUp 0.5s ease-out;
        }
        
        .task-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }
        
        .task-title {
            color: var(--secondary);
            font-size: 2rem;
            font-weight: 600;
        }
        
        .task-card {
            background-color: var(--card);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            border-left: 4px solid var(--primary);
        }
        
        .task-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        
        .task-card-high {
            border-left-color: var(--danger);
        }
        
        .task-card-medium {
            border-left-color: var(--warning);
        }
        
        .task-card-low {
            border-left-color: var(--success);
        }
        
        .task-card-completed {
            border-left-color: #9e9e9e;
            opacity: 0.7;
        }
        
        .task-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .task-card-title {
            font-weight: 600;
            font-size: 1.2rem;
            color: var(--secondary);
        }
        
        .task-card-due {
            font-size: 0.9rem;
            color: #666;
        }
        
        .task-card-priority {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .priority-high {
            background-color: #ffebee;
            color: var(--danger);
        }
        
        .priority-medium {
            background-color: #fff8e1;
            color: var(--warning);
        }
        
        .priority-low {
            background-color: #e8f5e9;
            color: var(--success);
        }
        
        .task-card-description {
            margin: 1rem 0;
            color: #555;
            line-height: 1.5;
        }
        
        .task-card-actions {
            display: flex;
            gap: 0.5rem;
        }
        
        .task-button {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .task-button-complete {
            background-color: var(--success);
            color: white;
        }
        
        .task-button-complete:hover {
            background-color: #43a047;
        }
        
        .task-button-edit {
            background-color: var(--accent);
            color: white;
        }
        
        .task-button-edit:hover {
            background-color: #29b6f6;
        }
        
        .task-button-delete {
            background-color: #f5f5f5;
            color: var(--danger);
        }
        
        .task-button-delete:hover {
            background-color: #eeeeee;
        }
        
        .add-task-form {
            background-color: var(--card);
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
        }
        
        .form-title {
            color: var(--secondary);
            margin-bottom: 1rem;
            font-weight: 600;
        }
        
        .logout-button {
            background-color: var(--danger) !important;
            color: white !important;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(50px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .switch-container {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .switch-text {
            margin-left: 0.5rem;
            color: var(--text);
        }
        
        /* Responsividade */
        @media (max-width: 768px) {
            .auth-container {
                margin: 2rem auto;
                padding: 1.5rem;
            }
            
            .task-container {
                padding: 0 1rem;
            }
            
            .task-card-actions {
                flex-direction: column;
            }
        }
    </style>
    """, unsafe_allow_html=True)

# Página de autenticação
def auth_page():
    st.markdown("""
    <div class="auth-container">
        <h1 class="auth-title">📋 Organizador de Tarefas</h1>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Cadastro"])
    
    with tab1:
        with st.form("login_form"):
            st.markdown('<div class="auth-input">', unsafe_allow_html=True)
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.form_submit_button("Login", help="Clique para fazer login"):
                user_id = verify_user(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.page = "tasks"
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos")
    
    with tab2:
        with st.form("register_form"):
            st.markdown('<div class="auth-input">', unsafe_allow_html=True)
            new_username = st.text_input("Novo usuário")
            new_password = st.text_input("Nova senha", type="password")
            confirm_password = st.text_input("Confirmar senha", type="password")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.form_submit_button("Cadastrar", help="Clique para criar uma conta"):
                if new_password == confirm_password:
                    if create_user(new_username, new_password):
                        st.success("Conta criada com sucesso! Faça login para continuar.")
                    else:
                        st.error("Nome de usuário já existe")
                else:
                    st.error("As senhas não coincidem")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Página principal de tarefas
def tasks_page():
    st.markdown(f"""
    <div class="task-container">
        <div class="task-header">
            <h1 class="task-title">Olá, {st.session_state.username}!</h1>
            <button onclick="window.location.href='?logout=true'" class="auth-button logout-button">Sair</button>
        </div>
    """, unsafe_allow_html=True)
    
    # Adicionar nova tarefa
    with st.expander("➕ Adicionar Nova Tarefa", expanded=False):
        with st.form("add_task_form"):
            st.markdown('<div class="add-task-form">', unsafe_allow_html=True)
            st.markdown('<h3 class="form-title">Nova Tarefa</h3>', unsafe_allow_html=True)
            title = st.text_input("Título")
            description = st.text_area("Descrição")
            col1, col2 = st.columns(2)
            with col1:
                due_date = st.date_input("Data de Vencimento")
            with col2:
                priority = st.selectbox("Prioridade", ["Alta", "Média", "Baixa"], index=1)
            
            if st.form_submit_button("Adicionar Tarefa"):
                if title:
                    priority_map = {"Alta": 3, "Média": 2, "Baixa": 1}
                    add_task(st.session_state.user_id, title, description, due_date.strftime("%Y-%m-%d"), priority_map[priority])
                    st.success("Tarefa adicionada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("O título é obrigatório")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Mostrar tarefas
    show_completed = st.checkbox("Mostrar tarefas concluídas")
    tasks = get_tasks(st.session_state.user_id, show_completed)
    
    if not tasks:
        st.info("Nenhuma tarefa encontrada. Adicione uma nova tarefa para começar!")
    else:
        for task in tasks:
            task_id, _, title, description, due_date, priority, completed, created_at = task
            
            priority_class = ""
            if priority == 3:
                priority_class = "task-card-high priority-high"
            elif priority == 2:
                priority_class = "task-card-medium priority-medium"
            else:
                priority_class = "task-card-low priority-low"
            
            if completed:
                priority_class = "task-card-completed"
            
            st.markdown(f"""
            <div class="task-card {priority_class}">
                <div class="task-card-header">
                    <h3 class="task-card-title">{title}</h3>
                    <span class="task-card-priority {priority_class.split()[1]}">
                        {"Alta" if priority == 3 else "Média" if priority == 2 else "Baixa"}
                    </span>
                </div>
                <div class="task-card-due">
                    📅 {datetime.strptime(due_date, "%Y-%m-%d").strftime("%d/%m/%Y")}
                </div>
                <div class="task-card-description">
                    {description if description else "Sem descrição"}
                </div>
                <div class="task-card-actions">
                    {"<button class='task-button task-button-complete' onclick='window.location.href=\"?complete_task=false&task_id=" + str(task_id) + "\"'>Marcar como Pendente</button>" if completed else "<button class='task-button task-button-complete' onclick='window.location.href=\"?complete_task=true&task_id=" + str(task_id) + "\"'>Concluir</button>"}
                    <button class='task-button task-button-delete' onclick='window.location.href=\"?delete_task=true&task_id=" + str(task_id) + "\"'>Excluir</button>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Configuração inicial do Streamlit
st.set_page_config(page_title="Organizador de Tarefas", page_icon="📋", layout="wide")

# Carregar CSS
load_css()

# Gerenciamento de estado
if 'page' not in st.session_state:
    st.session_state.page = "auth"
    st.session_state.user_id = None
    st.session_state.username = None

# Verificar parâmetros de URL para ações
params = st.experimental_get_query_params()

if "logout" in params:
    st.session_state.page = "auth"
    st.session_state.user_id = None
    st.session_state.username = None
    st.experimental_set_query_params()
    st.rerun()

if "complete_task" in params and "task_id" in params:
    update_task_status(params["task_id"][0], int(params["complete_task"][0]))
    st.experimental_set_query_params()
    st.rerun()

if "delete_task" in params and "task_id" in params:
    delete_task(params["task_id"][0])
    st.experimental_set_query_params()
    st.rerun()

# Renderizar página apropriada
if st.session_state.page == "auth":
    auth_page()
else:
    tasks_page()

# Adicionar alguns efeitos JS para melhorar a experiência
components.html("""
<script>
    // Efeito de hover nos botões
    document.querySelectorAll('.task-button').forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.1)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
    });
    
    // Suavizar transições
    document.querySelectorAll('a, button').forEach(element => {
        element.style.transition = 'all 0.3s ease';
    });
</script>
""")
