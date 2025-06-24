import streamlit as st
from streamlit.components.v1 import html
import sqlite3
import hashlib
import time
from datetime import datetime

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
                  priority INTEGER,
                  completed INTEGER DEFAULT 0,
                  created_at TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

init_db()

# Função para hash de senha
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Função para registrar novo usuário
def register_user(username, password):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# Função para verificar login
def verify_login(username, password):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    
    if result and result[1] == hash_password(password):
        return result[0]  # Retorna o ID do usuário
    return None

# Funções para gerenciamento de tarefas
def add_task(user_id, title, description, due_date, priority):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO tasks (user_id, title, description, due_date, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, title, description, due_date, priority, created_at))
    conn.commit()
    conn.close()

def get_tasks(user_id, filter_type="all"):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    
    if filter_type == "active":
        query = "SELECT * FROM tasks WHERE user_id = ? AND completed = 0 ORDER BY priority DESC, due_date"
    elif filter_type == "completed":
        query = "SELECT * FROM tasks WHERE user_id = ? AND completed = 1 ORDER BY priority DESC, due_date"
    else:
        query = "SELECT * FROM tasks WHERE user_id = ? ORDER BY priority DESC, due_date"
    
    c.execute(query, (user_id,))
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
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--background);
            color: var(--text);
        }
        
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        .login-container, .register-container {
            max-width: 400px;
            margin: 2rem auto;
            padding: 2rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            animation: fadeIn 0.5s ease-in-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .task-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            border-left: 4px solid var(--primary);
        }
        
        .task-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
        }
        
        .task-card.completed {
            opacity: 0.7;
            border-left-color: var(--success);
        }
        
        .task-card.high-priority {
            border-left-color: var(--danger);
        }
        
        .task-card.medium-priority {
            border-left-color: var(--warning);
        }
        
        .btn {
            border: none;
            border-radius: 5px;
            padding: 0.5rem 1rem;
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
            transform: translateY(-1px);
        }
        
        .btn-danger {
            background-color: var(--danger);
            color: white;
        }
        
        .btn-success {
            background-color: var(--success);
            color: white;
        }
        
        .header {
            color: var(--secondary);
            margin-bottom: 1.5rem;
        }
        
        .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stDateInput>div>div>input {
            border-radius: 5px !important;
            border: 1px solid #ddd !important;
            padding: 10px !important;
        }
        
        .st-bb {
            border-bottom: 1px solid #eee;
            padding-bottom: 1rem;
            margin-bottom: 1rem;
        }
        
        .floating-btn {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background-color: var(--accent);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            cursor: pointer;
            transition: all 0.3s;
            z-index: 100;
        }
        
        .floating-btn:hover {
            transform: scale(1.1) rotate(90deg);
            box-shadow: 0 6px 15px rgba(0, 0, 0, 0.3);
        }
        
        .priority-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: bold;
            margin-left: 0.5rem;
        }
        
        .high-priority-badge {
            background-color: #ffebee;
            color: var(--danger);
        }
        
        .medium-priority-badge {
            background-color: #fff8e1;
            color: var(--warning);
        }
        
        .low-priority-badge {
            background-color: #e8f5e9;
            color: var(--success);
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
        
        .shake {
            animation: shake 0.5s;
        }
        
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
            20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
    </style>
    """, unsafe_allow_html=True)

# Página de login
def login_page():
    st.markdown("""
    <div class="login-container">
        <h2 class="header" style="text-align: center;">Task Manager Pro</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Nome de usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Login", type="primary")
        
        if submitted:
            user_id = verify_login(username, password)
            if user_id:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user_id
                st.session_state['username'] = username
                st.rerun()
            else:
                st.error("Credenciais inválidas. Por favor, tente novamente.")
                st.markdown("<div class='shake'>", unsafe_allow_html=True)
    
    if st.button("Cadastre-se"):
        st.session_state['show_register'] = True
        st.rerun()

# Página de registro
def register_page():
    st.markdown("""
    <div class="register-container">
        <h2 class="header" style="text-align: center;">Criar nova conta</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("register_form"):
        new_username = st.text_input("Escolha um nome de usuário")
        new_password = st.text_input("Crie uma senha", type="password")
        confirm_password = st.text_input("Confirme a senha", type="password")
        submitted = st.form_submit_button("Registrar", type="primary")
        
        if submitted:
            if new_password != confirm_password:
                st.error("As senhas não coincidem!")
            else:
                success = register_user(new_username, new_password)
                if success:
                    st.success("Conta criada com sucesso! Faça login agora.")
                    st.session_state['show_register'] = False
                    st.rerun()
                else:
                    st.error("Nome de usuário já em uso. Escolha outro.")
    
    if st.button("Voltar para login"):
        st.session_state['show_register'] = False
        st.rerun()

# Página principal do aplicativo
def main_app():
    st.sidebar.title(f"Olá, {st.session_state['username']}")
    
    # Filtros
    filter_option = st.sidebar.radio("Filtrar tarefas:", ["Todas", "Ativas", "Concluídas"])
    
    # Adicionar nova tarefa
    if st.sidebar.button("➕ Nova Tarefa") or st.session_state.get('show_task_form', False):
        st.session_state['show_task_form'] = True
        with st.form("task_form"):
            st.subheader("Adicionar Nova Tarefa")
            title = st.text_input("Título*", key="task_title")
            description = st.text_area("Descrição", key="task_desc")
            col1, col2 = st.columns(2)
            with col1:
                due_date = st.date_input("Data de Vencimento", key="task_date")
            with col2:
                priority = st.selectbox("Prioridade", ["Alta", "Média", "Baixa"], key="task_priority")
            
            submitted = st.form_submit_button("Salvar Tarefa", type="primary")
            cancel = st.form_submit_button("Cancelar")
            
            if cancel:
                st.session_state['show_task_form'] = False
                st.rerun()
            
            if submitted:
                if not title:
                    st.error("O título é obrigatório!")
                else:
                    priority_map = {"Alta": 3, "Média": 2, "Baixa": 1}
                    add_task(
                        st.session_state['user_id'],
                        title,
                        description,
                        due_date.strftime("%Y-%m-%d"),
                        priority_map[priority]
                    )
                    st.session_state['show_task_form'] = False
                    st.success("Tarefa adicionada com sucesso!")
                    time.sleep(1)
                    st.rerun()
    
    # Mostrar tarefas
    st.header("Suas Tarefas")
    
    filter_map = {"Todas": "all", "Ativas": "active", "Concluídas": "completed"}
    tasks = get_tasks(st.session_state['user_id'], filter_map[filter_option])
    
    if not tasks:
        st.info("Nenhuma tarefa encontrada. Adicione uma nova tarefa para começar!")
    else:
        for task in tasks:
            task_id, _, title, description, due_date, priority, completed, created_at = task
            priority_text = {3: "Alta", 2: "Média", 1: "Baixa"}[priority]
            priority_class = {3: "high", 2: "medium", 1: "low"}[priority]
            
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None
            today = datetime.now().date()
            is_overdue = due_date_obj and due_date_obj < today and not completed
            
            card_class = f"task-card {priority_class}-priority {'completed' if completed else ''}"
            if is_overdue:
                card_class += " pulse"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; {'text-decoration: line-through;' if completed else ''}">
                        {title}
                        <span class="priority-badge {priority_class}-priority-badge">
                            {priority_text}
                        </span>
                    </h3>
                    <div>
                        <small>{due_date_obj.strftime('%d/%m/%Y') if due_date_obj else 'Sem data'}</small>
                        {'<span style="color: var(--danger); margin-left: 0.5rem;">⚠ Atrasada</span>' if is_overdue else ''}
                    </div>
                </div>
                {f'<p>{description}</p>' if description else ''}
                <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1,1,1])
            with col1:
                if st.button(f"{'✅' if completed else '☑️'} {'Concluída' if completed else 'Concluir'}", 
                           key=f"complete_{task_id}"):
                    update_task_status(task_id, 1 if not completed else 0)
                    st.rerun()
            with col2:
                if st.button("✏️ Editar", key=f"edit_{task_id}"):
                    st.session_state['edit_task'] = task_id
                    st.rerun()
            with col3:
                if st.button("🗑️ Excluir", key=f"delete_{task_id}"):
                    delete_task(task_id)
                    st.rerun()
            
            st.markdown("</div></div>", unsafe_allow_html=True)
    
    # Botão de logout
    if st.sidebar.button("🚪 Sair"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Página de edição de tarefa
def edit_task_page(task_id):
    conn = sqlite3.connect('task_manager.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = c.fetchone()
    conn.close()
    
    if not task:
        st.error("Tarefa não encontrada!")
        del st.session_state['edit_task']
        st.rerun()
        return
    
    _, _, title, description, due_date, priority, completed, _ = task
    
    st.subheader("Editar Tarefa")
    with st.form("edit_task_form"):
        new_title = st.text_input("Título*", value=title, key="edit_title")
        new_description = st.text_area("Descrição", value=description if description else "", key="edit_desc")
        
        col1, col2 = st.columns(2)
        with col1:
            new_due_date = st.date_input(
                "Data de Vencimento", 
                value=datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None,
                key="edit_date"
            )
        with col2:
            priority_map = {3: "Alta", 2: "Média", 1: "Baixa"}
            new_priority = st.selectbox(
                "Prioridade",
                ["Alta", "Média", "Baixa"],
                index=[3,2,1].index(priority),
                key="edit_priority"
            )
        
        submitted = st.form_submit_button("Salvar Alterações", type="primary")
        cancel = st.form_submit_button("Cancelar")
        
        if cancel:
            del st.session_state['edit_task']
            st.rerun()
        
        if submitted:
            if not new_title:
                st.error("O título é obrigatório!")
            else:
                conn = sqlite3.connect('task_manager.db')
                c = conn.cursor()
                priority_map = {"Alta": 3, "Média": 2, "Baixa": 1}
                c.execute("""
                    UPDATE tasks 
                    SET title = ?, description = ?, due_date = ?, priority = ?
                    WHERE id = ?
                """, (
                    new_title,
                    new_description,
                    new_due_date.strftime("%Y-%m-%d") if new_due_date else None,
                    priority_map[new_priority],
                    task_id
                ))
                conn.commit()
                conn.close()
                
                del st.session_state['edit_task']
                st.success("Tarefa atualizada com sucesso!")
                time.sleep(1)
                st.rerun()

# Configuração inicial da página
st.set_page_config(
    page_title="Task Manager Pro",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css()

# Verificar estado de autenticação
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Roteamento de páginas
if not st.session_state['logged_in']:
    if st.session_state.get('show_register', False):
        register_page()
    else:
        login_page()
else:
    if 'edit_task' in st.session_state:
        edit_task_page(st.session_state['edit_task'])
    else:
        main_app()

# Adicionar o botão flutuante apenas na página principal
if st.session_state.get('logged_in', False) and 'edit_task' not in st.session_state:
    st.markdown("""
    <div class="floating-btn" onclick="window.streamlitApi.runMethod('show_task_form', true)">+</div>
    <script>
        function showTaskForm() {
            window.streamlitApi.runMethod('show_task_form', true);
        }
    </script>
    """, unsafe_allow_html=True)
