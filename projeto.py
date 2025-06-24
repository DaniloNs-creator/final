import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit.components.v1 as components
import hashlib
import re

# Configuração inicial dos bancos de dados
def init_db():
    # Conexão para o banco de dados de usuários
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 email TEXT,
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    
    # Conexão para o banco de dados de tarefas (agora com user_id)
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 title TEXT NOT NULL,
                 description TEXT,
                 priority INTEGER,
                 due_date TEXT,
                 status TEXT DEFAULT 'pending',
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

# Função para hash de senha
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Função para verificar senha
def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Validação de email
def is_valid_email(email):
    regex = r'^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
    return re.match(regex, email)

# CSS personalizado com animações (mantido igual)
def local_css():
    st.markdown("""
    <style>
        /* Seu CSS existente permanece exatamente igual */
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
        
        /* Todos os outros estilos CSS permanecem iguais */
        /* ... */
    </style>
    """, unsafe_allow_html=True)

# Funções CRUD para usuários
def create_user(username, password, email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                  (username, make_hashes(password), email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()
    if data and check_hashes(password, data[0]):
        return True
    return False

def get_user_id(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = c.fetchone()[0]
    conn.close()
    return user_id

# Funções CRUD para tarefas (agora com user_id)
def add_task(user_id, title, description, priority, due_date):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (user_id, title, description, priority, due_date) VALUES (?, ?, ?, ?, ?)",
              (user_id, title, description, priority, due_date))
    conn.commit()
    conn.close()

def get_tasks(user_id, status=None):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    if status:
        c.execute("SELECT * FROM tasks WHERE user_id=? AND status=? ORDER BY priority DESC, due_date ASC", (user_id, status))
    else:
        c.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY priority DESC, due_date ASC", (user_id,))
    tasks = c.fetchall()
    conn.close()
    return tasks

def update_task_status(user_id, task_id, status):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=? WHERE id=? AND user_id=?", (status, task_id, user_id))
    conn.commit()
    conn.close()

def delete_task(user_id, task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
    conn.commit()
    conn.close()

def get_task_by_id(user_id, task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
    task = c.fetchone()
    conn.close()
    return task

def update_task(user_id, task_id, title, description, priority, due_date):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET title=?, description=?, priority=?, due_date=? WHERE id=? AND user_id=?",
              (title, description, priority, due_date, task_id, user_id))
    conn.commit()
    conn.close()

def delete_all_user_tasks(user_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# Função para exibir estatísticas (agora com user_id)
def show_stats(user_id):
    conn = sqlite3.connect('tasks.db')
    df = pd.read_sql_query("SELECT status, COUNT(*) as count FROM tasks WHERE user_id=? GROUP BY status", conn, params=(user_id,))
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

# Página de login
def login_page():
    st.title("📋 Organizador de Tarefas")
    st.subheader("Faça login para acessar suas tarefas")
    
    with st.form("Login"):
        username = st.text_input("Nome de usuário")
        password = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if verify_user(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['user_id'] = get_user_id(username)
                st.success(f"Bem-vindo, {username}!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")
    
    st.markdown("---")
    st.markdown("Não tem uma conta?")
    if st.button("Cadastre-se"):
        st.session_state['show_register'] = True
        st.rerun()

# Página de cadastro
def register_page():
    st.title("📝 Criar nova conta")
    
    with st.form("Registro"):
        new_username = st.text_input("Escolha um nome de usuário")
        new_email = st.text_input("Email (opcional)")
        new_password = st.text_input("Crie uma senha", type="password")
        confirm_password = st.text_input("Confirme a senha", type="password")
        submit_button = st.form_submit_button("Criar conta")
        
        if submit_button:
            if not new_username:
                st.error("Nome de usuário é obrigatório")
            elif new_email and not is_valid_email(new_email):
                st.error("Por favor, insira um email válido")
            elif not new_password:
                st.error("Senha é obrigatória")
            elif new_password != confirm_password:
                st.error("As senhas não coincidem")
            else:
                success = create_user(new_username, new_password, new_email if new_email else None)
                if success:
                    st.success("Conta criada com sucesso! Faça login para continuar.")
                    st.session_state['show_register'] = False
                    st.rerun()
                else:
                    st.error("Nome de usuário já existe")
    
    st.markdown("---")
    if st.button("Voltar para login"):
        st.session_state['show_register'] = False
        st.rerun()

# Página principal do aplicativo (após login)
def task_manager_page():
    # Inicializar CSS
    local_css()
    
    # Header personalizado
    st.markdown(f"""
    <div class="header">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h1 style="margin:0; font-size:2.2rem;">📋 Organizador de Tarefas</h1>
                <p style="margin:0; opacity:0.8;">Bem-vindo, {st.session_state['username']}</p>
            </div>
            <button onclick="logout()" style="background:var(--danger); color:white; border:none; padding:8px 16px; border-radius:20px; cursor:pointer;">Sair</button>
        </div>
    </div>
    
    <script>
    function logout() {{
        window.location.href = "?logout=true";
    }}
    </script>
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
            tasks = get_tasks(st.session_state['user_id'])
        elif filter_status == "Pendentes":
            tasks = get_tasks(st.session_state['user_id'], "pending")
        else:
            tasks = get_tasks(st.session_state['user_id'], "completed")
        
        # Aplicar filtro de prioridade
        if filter_priority != "Todas":
            priority_map = {"Alta": 3, "Média": 2, "Baixa": 1}
            tasks = [task for task in tasks if task[4] == priority_map[filter_priority]]
        
        if not tasks:
            st.info("Nenhuma tarefa encontrada com os filtros selecionados.")
        else:
            for task in tasks:
                task_id, user_id, title, description, priority, due_date, status, created_at = task
                
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
                            update_task_status(st.session_state['user_id'], task_id, "completed")
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
                        delete_task(st.session_state['user_id'], task_id)
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
                    add_task(st.session_state['user_id'], title, description, priority, due_date.strftime("%Y-%m-%d"))
                    st.success("Tarefa adicionada com sucesso!")
                    st.balloons()
    
    with tab3:
        st.subheader("Estatísticas de Produtividade")
        show_stats(st.session_state['user_id'])
        
        # Gráfico de status
        conn = sqlite3.connect('tasks.db')
        df = pd.read_sql_query("SELECT status, COUNT(*) as count FROM tasks WHERE user_id=? GROUP BY status", 
                              conn, params=(st.session_state['user_id'],))
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
                delete_all_user_tasks(st.session_state['user_id'])
                st.success("Todas as suas tarefas foram removidas!")
    
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
                            update_task(st.session_state['user_id'], st.session_state['edit_task_id'], 
                                      title, description, priority, due_date.strftime("%Y-%m-%d"))
                            del st.session_state['edit_task_id']
                            st.rerun()
                with col2:
                    if st.form_submit_button("Cancelar"):
                        del st.session_state['edit_task_id']
                        st.rerun()

# Função principal
def main():
    # Inicializar banco de dados
    init_db()
    
    # Verificar parâmetro de logout na URL
    if st.experimental_get_query_params().get("logout"):
        st.session_state.clear()
        st.experimental_set_query_params()
        st.rerun()
    
    # Verificar se o usuário está logado
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    # Mostrar página apropriada com base no estado de login
    if not st.session_state['logged_in']:
        if 'show_register' in st.session_state and st.session_state['show_register']:
            register_page()
        else:
            login_page()
    else:
        task_manager_page()

if __name__ == "__main__":
    main()
