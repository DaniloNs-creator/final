import streamlit as st
import sqlite3
import hashlib
import uuid

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            task TEXT NOT NULL,
            due_date TEXT,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)

def add_user(username, password):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    try:
        user_id = str(uuid.uuid4())
        c.execute("INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
                  (user_id, username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Username already exists
    finally:
        conn.close()

def get_user(username):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user

def add_task(user_id, task, due_date, status):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    task_id = str(uuid.uuid4())
    c.execute("INSERT INTO tasks (id, user_id, task, due_date, status) VALUES (?, ?, ?, ?, ?)",
              (task_id, user_id, task, due_date, status))
    conn.commit()
    conn.close()

def get_tasks(user_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT id, task, due_date, status FROM tasks WHERE user_id = ?", (user_id,))
    tasks = c.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# --- CSS Styling and Animations ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    :root {
        --primary-color: #4CAF50;
        --secondary-color: #607D8B;
        --background-color: #f0f2f6;
        --card-background: #ffffff;
        --text-color: #333333;
        --light-text: #666666;
        --border-color: #e0e0e0;
        --success-color: #28a745;
        --error-color: #dc3545;
        --info-color: #17a2b8;
    }

    body {
        font-family: 'Poppins', sans-serif;
        background-color: var(--background-color);
        color: var(--text-color);
        margin: 0;
        padding: 0;
    }

    .stApp {
        background-color: var(--background-color);
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 700px;
        margin: auto;
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--primary-color);
        font-weight: 600;
        margin-bottom: 1rem;
    }

    /* Card styling */
    .stCard {
        background-color: var(--card-background);
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }

    .stCard:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
    }

    /* Input fields */
    .stTextInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div > select {
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        width: 100%;
        transition: border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }

    .stTextInput > div > div > input:focus,
    .stDateInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.2);
        outline: none;
    }

    /* Buttons */
    .stButton > button {
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.75rem 1.25rem;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.2s ease-in-out, transform 0.1s ease-in-out, box-shadow 0.2s ease-in-out;
        width: 100%;
        margin-top: 0.5rem;
    }

    .stButton > button:hover {
        background-color: #43A047;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }

    .stButton > button:active {
        transform: translateY(0);
        box-shadow: none;
    }

    /* Secondary buttons (e.g., Delete, Logout) */
    .stButton.delete-button > button {
        background-color: var(--error-color);
    }
    .stButton.delete-button > button:hover {
        background-color: #c82333;
    }

    .stButton.logout-button > button {
        background-color: var(--secondary-color);
    }
    .stButton.logout-button > button:hover {
        background-color: #546E7A;
    }

    /* Task list item */
    .task-item {
        background-color: var(--card-background);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }

    .task-item:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
    }

    .task-content {
        flex-grow: 1;
    }

    .task-content h4 {
        margin: 0 0 0.25rem 0;
        color: var(--text-color);
        font-weight: 600;
    }

    .task-content p {
        margin: 0;
        color: var(--light-text);
        font-size: 0.9em;
    }

    .task-actions {
        display: flex;
        gap: 0.5rem;
    }

    .task-actions .stButton > button {
        width: auto;
        padding: 0.5rem 0.75rem;
        font-size: 0.85rem;
        margin-top: 0;
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.3em 0.6em;
        border-radius: 4px;
        font-size: 0.75em;
        font-weight: 700;
        color: white;
        text-transform: uppercase;
        margin-left: 0.5rem;
    }

    .status-badge.pending {
        background-color: var(--info-color);
    }
    .status-badge.completed {
        background-color: var(--success-color);
    }
    .status-badge.in-progress {
        background-color: #ffc107; /* Warning color */
    }

    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .fade-in {
        animation: fadeIn 0.6s ease-out forwards;
    }

    /* Custom containers for centered content */
    .center-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh; /* Adjust as needed */
        flex-direction: column;
    }

    .login-form-container {
        width: 100%;
        max-width: 400px;
        padding: 2rem;
        background-color: var(--card-background);
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
        text-align: center;
    }

    .login-form-container h2 {
        color: var(--primary-color);
        margin-bottom: 1.5rem;
    }

    .stAlert {
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        font-weight: 500;
    }

    .stAlert.success {
        background-color: #d4edda;
        color: #155724;
        border-color: #c3e6cb;
    }

    .stAlert.error {
        background-color: #f8d7da;
        color: #721c24;
        border-color: #f5c6cb;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Streamlit App ---
def main():
    init_db()
    load_css()

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_id = None
        st.session_state.page = 'login' # Can be 'login' or 'register'

    if st.session_state.logged_in:
        task_organizer_page()
    else:
        auth_page()

def auth_page():
    st.markdown('<div class="center-container fade-in">', unsafe_allow_html=True)
    st.markdown('<div class="login-form-container">', unsafe_allow_html=True)

    if st.session_state.page == 'login':
        st.markdown("<h2>Login</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Login"):
                    user = get_user(username)
                    if user and verify_password(user[1], password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_id = user[0]
                        st.experimental_rerun() # Use rerun to clear form fields effectively
                    else:
                        st.markdown('<div class="stAlert error">Invalid username or password</div>', unsafe_allow_html=True)
            with col2:
                if st.form_submit_button("Register"):
                    st.session_state.page = 'register'
                    st.experimental_rerun()

    elif st.session_state.page == 'register':
        st.markdown("<h2>Register</h2>", unsafe_allow_html=True)
        with st.form("register_form"):
            new_username = st.text_input("New Username", key="register_username")
            new_password = st.text_input("New Password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Create Account"):
                    if new_password == confirm_password:
                        if add_user(new_username, new_password):
                            st.markdown('<div class="stAlert success">Account created successfully! Please login.</div>', unsafe_allow_html=True)
                            st.session_state.page = 'login'
                            st.experimental_rerun()
                        else:
                            st.markdown('<div class="stAlert error">Username already exists.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="stAlert error">Passwords do not match.</div>', unsafe_allow_html=True)
            with col2:
                if st.form_submit_button("Back to Login"):
                    st.session_state.page = 'login'
                    st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True) # close login-form-container
    st.markdown('</div>', unsafe_allow_html=True) # close center-container

def task_organizer_page():
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    col_header_left, col_header_right = st.columns([3, 1])
    with col_header_left:
        st.title(f"Olá, {st.session_state.username}! 👋")
    with col_header_right:
        if st.button("Logout", key="logout_button"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.user_id = None
            st.session_state.page = 'login'
            st.experimental_rerun()
    st.markdown("---")

    st.header("Adicionar Nova Tarefa")
    with st.form("task_form", clear_on_submit=True):
        task = st.text_input("Tarefa", placeholder="Descreva sua tarefa aqui...")
        due_date = st.date_input("Data de Vencimento", value=None)
        status = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluído"], index=0)
        submitted = st.form_submit_button("Adicionar Tarefa")
        if submitted and task:
            add_task(st.session_state.user_id, task, str(due_date) if due_date else None, status)
            st.markdown('<div class="stAlert success">Tarefa adicionada com sucesso!</div>', unsafe_allow_html=True)
            st.experimental_rerun()
        elif submitted and not task:
            st.markdown('<div class="stAlert error">A tarefa não pode estar vazia.</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.header("Minhas Tarefas")

    tasks = get_tasks(st.session_state.user_id)

    if tasks:
        # Filter and sort options
        filter_status = st.selectbox("Filtrar por Status", ["Todas", "Pendente", "Em Andamento", "Concluído"])

        display_tasks = []
        for task_id, task_desc, due_date, status in tasks:
            if filter_status == "Todas" or status == filter_status:
                display_tasks.append((task_id, task_desc, due_date, status))

        if not display_tasks:
            st.info("Nenhuma tarefa encontrada com o filtro selecionado.")
        else:
            for task_id, task_desc, due_date, status in display_tasks:
                status_class = status.replace(" ", "-").lower() # For CSS class
                st.markdown(f"""
                <div class="task-item fade-in">
                    <div class="task-content">
                        <h4>{task_desc} <span class="status-badge {status_class}">{status}</span></h4>
                        <p>Vencimento: {due_date if due_date else 'N/A'}</p>
                    </div>
                    <div class="task-actions">
                """, unsafe_allow_html=True)

                col1, col2 = st.columns([1, 1])
                with col1:
                    # Using unique keys for update buttons
                    new_status = st.selectbox(
                        "Status",
                        ["Pendente", "Em Andamento", "Concluído"],
                        index=["Pendente", "Em Andamento", "Concluído"].index(status),
                        key=f"status_{task_id}",
                        label_visibility="collapsed" # Hide label
                    )
                    if st.button("Atualizar", key=f"update_{task_id}"):
                        update_task_status(task_id, new_status)
                        st.success("Status da tarefa atualizado!")
                        st.experimental_rerun()
                with col2:
                    if st.button("Deletar", key=f"delete_{task_id}", type="secondary"):
                        delete_task(task_id)
                        st.warning("Tarefa deletada!")
                        st.experimental_rerun()
                st.markdown("</div></div>", unsafe_allow_html=True)
    else:
        st.info("Você ainda não tem tarefas. Adicione uma acima!")
    st.markdown('</div>', unsafe_allow_html=True) # close fade-in

if __name__ == "__main__":
    main()
    
