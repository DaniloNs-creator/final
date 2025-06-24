import streamlit as st
import sqlite3
import hashlib

# --- Funções do Banco de Dados ---
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            task TEXT NOT NULL,
            status TEXT DEFAULT 'Pendente',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Username already exists
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[1] == hash_password(password):
        return result[0] # Return user_id
    return None

def add_task(user_id, task):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (user_id, task) VALUES (?, ?)", (user_id, task))
    conn.commit()
    conn.close()

def get_tasks(user_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT id, task, status FROM tasks WHERE user_id = ?", (user_id,))
    tasks = c.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()
    conn.close()

def update_task_text(task_id, new_task_text):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET task = ? WHERE id = ?", (new_task_text, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# --- Estilo CSS e Animações ---
def set_styles():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

        :root {
            --primary-color: #6C63FF;
            --secondary-color: #E0E0E0;
            --background-color: #F8F9FA;
            --text-color: #333333;
            --card-background: #FFFFFF;
            --border-radius: 12px;
            --shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            --gradient-start: #7f6eec;
            --gradient-end: #6C63FF;
        }

        body {
            font-family: 'Poppins', sans-serif;
            background: var(--background-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        .stApp {
            background: linear-gradient(135deg, var(--gradient-start) 0%, var(--gradient-end) 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .stApp > header {
            display: none; /* Hide Streamlit's default header */
        }

        .stApp > footer {
            display: none; /* Hide Streamlit's default footer */
        }

        .stForm {
            background-color: var(--card-background);
            padding: 40px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            max-width: 500px;
            width: 100%;
            animation: fadeIn 0.8s ease-out;
            border: 1px solid #ddd;
        }

        .stForm h1, .stForm h2 {
            color: var(--primary-color);
            text-align: center;
            margin-bottom: 30px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .stButton button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
            margin-top: 15px;
            font-size: 16px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }

        .stButton button:hover {
            background-color: #5a53d1;
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }

        .stTextInput label {
            font-weight: 600;
            color: var(--text-color);
            margin-bottom: 8px;
            display: block;
        }

        .stTextInput input[type="text"],
        .stTextInput input[type="password"] {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid #cccccc;
            border-radius: 8px;
            font-size: 16px;
            box-sizing: border-box;
            transition: border-color 0.3s ease;
        }

        .stTextInput input[type="text"]:focus,
        .stTextInput input[type="password"]:focus {
            border-color: var(--primary-color);
            outline: none;
            box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.2);
        }

        /* Task List Specific Styles */
        .task-container {
            background-color: var(--card-background);
            padding: 30px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            max-width: 700px;
            width: 100%;
            animation: slideInUp 0.8s ease-out;
            border: 1px solid #ddd;
            margin-top: 20px;
        }

        .task-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
            transition: background-color 0.3s ease;
            margin-bottom: 10px;
            border-radius: 8px;
            background-color: #fcfcfc;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }

        .task-item:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }

        .task-item:hover {
            background-color: #f7f7f7;
        }

        .task-text {
            flex-grow: 1;
            font-size: 17px;
            color: var(--text-color);
            padding-right: 15px;
        }

        .task-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .task-actions button {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 18px;
            padding: 5px;
            border-radius: 50%;
            transition: background-color 0.3s ease, transform 0.2s ease;
            color: #666;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .task-actions button:hover {
            background-color: var(--secondary-color);
            transform: scale(1.1);
        }

        .task-actions .edit-btn { color: #FFA000; } /* Orange */
        .task-actions .delete-btn { color: #D32F2F; } /* Red */
        .task-actions .complete-btn { color: #4CAF50; } /* Green */
        .task-actions .pending-btn { color: #1976D2; } /* Blue */

        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-left: 10px;
        }

        .status-badge.Pendente {
            background-color: #ffe0b2;
            color: #ef6c00;
        }

        .status-badge.Concluída {
            background-color: #c8e6c9;
            color: #2e7d32;
        }

        .stAlert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 500;
            animation: fadeIn 0.5s ease-out;
        }

        .stAlert.info {
            background-color: #e3f2fd;
            color: #1565c0;
            border: 1px solid #90caf9;
        }

        .stAlert.success {
            background-color: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #a5d6a7;
        }

        .stAlert.error {
            background-color: #ffebee;
            color: #d32f2f;
            border: 1px solid #ef9a9a;
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes slideInUp {
            from { opacity: 0; transform: translateY(50px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .animated-heading {
            animation: pulse 1.5s infinite alternate;
            color: var(--primary-color);
        }

        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            100% { transform: scale(1.02); opacity: 0.95; }
        }

        /* Logout button */
        .stButton.logout button {
            background-color: #DC3545; /* Red color for logout */
        }
        .stButton.logout button:hover {
            background-color: #C82333;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Página de Login/Cadastro ---
def login_register_page():
    st.markdown(
        f"""
        <div class="stForm">
            <h1>Bem-vindo!</h1>
            <h2 class="animated-heading">Organizador de Tarefas</h2>
        """, unsafe_allow_html=True
    )

    if 'show_register' not in st.session_state:
        st.session_state.show_register = False

    if st.session_state.show_register:
        st.subheader("Crie sua conta")
        new_username = st.text_input("Novo Usuário", key="new_username_input")
        new_password = st.text_input("Nova Senha", type="password", key="new_password_input")
        confirm_password = st.text_input("Confirme a Senha", type="password", key="confirm_password_input")

        if st.button("Cadastrar", key="register_button"):
            if new_username and new_password and confirm_password:
                if new_password == confirm_password:
                    if add_user(new_username, new_password):
                        st.success("🎉 Usuário cadastrado com sucesso! Faça login para continuar.")
                        st.session_state.show_register = False # Switch back to login after successful registration
                        st.experimental_rerun()
                    else:
                        st.error("❌ Nome de usuário já existe. Por favor, escolha outro.")
                else:
                    st.error("⚠️ As senhas não coincidem.")
            else:
                st.warning("Preencha todos os campos para se cadastrar.")
        st.markdown("---", unsafe_allow_html=True)
        if st.button("Já tenho conta (Login)", key="back_to_login_button"):
            st.session_state.show_register = False
            st.experimental_rerun()
    else:
        st.subheader("Faça Login")
        username = st.text_input("Usuário", key="username_input")
        password = st.text_input("Senha", type="password", key="password_input")

        if st.button("Entrar", key="login_button"):
            user_id = verify_user(username, password)
            if user_id:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_id = user_id
                st.success(f"Bem-vindo, {username}!")
                st.experimental_rerun()
            else:
                st.error("❌ Usuário ou senha incorretos.")

        st.markdown("---", unsafe_allow_html=True)
        if st.button("Criar uma nova conta (Cadastrar)", key="go_to_register_button"):
            st.session_state.show_register = True
            st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- Página do Organizador de Tarefas ---
def task_organizer_page():
    st.markdown(
        f"""
        <div class="task-container">
            <h1 class="animated-heading">Olá, {st.session_state.username}!</h1>
            <h2>Suas Tarefas</h2>
        """, unsafe_allow_html=True
    )

    new_task = st.text_input("Adicionar nova tarefa", key="new_task_input")
    if st.button("Adicionar Tarefa", key="add_task_button"):
        if new_task:
            add_task(st.session_state.user_id, new_task)
            st.success("✅ Tarefa adicionada!")
            st.experimental_rerun()
        else:
            st.warning("Por favor, digite uma tarefa.")

    st.markdown("---", unsafe_allow_html=True)
    st.subheader("Lista de Tarefas")

    tasks = get_tasks(st.session_state.user_id)

    if not tasks:
        st.info("Você não tem tarefas. Que tal adicionar uma?")
    else:
        for task_id, task_text, status in tasks:
            col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
            with col1:
                st.markdown(
                    f"""
                    <div class="task-item">
                        <span class="task-text">{task_text}</span>
                        <span class="status-badge {status}">{status}</span>
                    </div>
                    """, unsafe_allow_html=True
                )
            with col2:
                current_status = status
                new_status = st.selectbox(
                    "Mudar Status",
                    ["Pendente", "Concluída"],
                    index=0 if current_status == "Pendente" else 1,
                    key=f"status_{task_id}",
                    label_visibility="collapsed"
                )
                if new_status != current_status:
                    update_task_status(task_id, new_status)
                    st.success(f"Status da tarefa '{task_text}' atualizado para '{new_status}'!")
                    st.experimental_rerun()
            with col3:
                st.markdown(
                    f"""
                    <div class="task-actions">
                    """, unsafe_allow_html=True
                )
                if st.button("✏️", key=f"edit_{task_id}"):
                    st.session_state.editing_task_id = task_id
                    st.session_state.editing_task_text = task_text
                    st.experimental_rerun()

                if st.session_state.get('editing_task_id') == task_id:
                    with st.form(key=f"edit_form_{task_id}", clear_on_submit=True):
                        edited_task_text = st.text_input("Editar tarefa", value=st.session_state.editing_task_text, key=f"edit_input_{task_id}")
                        col_edit1, col_edit2 = st.columns(2)
                        with col_edit1:
                            if st.form_submit_button("Salvar"):
                                if edited_task_text:
                                    update_task_text(task_id, edited_task_text)
                                    st.success("✅ Tarefa atualizada com sucesso!")
                                    st.session_state.editing_task_id = None
                                    st.session_state.editing_task_text = None
                                    st.experimental_rerun()
                                else:
                                    st.warning("A tarefa não pode estar vazia.")
                        with col_edit2:
                            if st.form_submit_button("Cancelar"):
                                st.session_state.editing_task_id = None
                                st.session_state.editing_task_text = None
                                st.experimental_rerun()

                if st.button("🗑️", key=f"delete_{task_id}"):
                    delete_task(task_id)
                    st.success(f"🗑️ Tarefa '{task_text}' excluída.")
                    st.experimental_rerun()
                st.markdown(
                    f"""
                    </div>
                    """, unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True) # Close task-item wrapper
            st.markdown("---", unsafe_allow_html=True) # Separator for tasks

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sair", key="logout_button", help="Clique para sair da sua conta"):
        st.session_state.logged_in = False
        del st.session_state.username
        del st.session_state.user_id
        st.success("👋 Você foi desconectado.")
        st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- Função Principal ---
def main():
    init_db()
    set_styles()

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        task_organizer_page()
    else:
        login_register_page()

if __name__ == "__main__":
    main()
    
