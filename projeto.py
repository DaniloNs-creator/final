import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit.components.v1 as components
import hashlib
import re

# --- Configuração Inicial dos Bancos de Dados ---
def init_db():
    """
    Inicializa os bancos de dados de usuários e tarefas.
    Cria as tabelas se elas não existirem.
    """
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

# --- Funções de Autenticação e Utilitários ---
def make_hashes(password):
    """Gera um hash SHA256 da senha."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    """Verifica se a senha fornecida corresponde ao hash."""
    return make_hashes(password) == hashed_text

def is_valid_email(email):
    """Valida o formato do e-mail usando regex."""
    regex = r'^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
    return re.match(regex, email)

# --- CSS Personalizado com Animações ---
def local_css():
    """Aplica estilos CSS personalizados ao aplicativo Streamlit."""
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

        body {
            font-family: 'Segoe UI', sans-serif;
            background-color: #f0f2f6;
            color: var(--dark);
        }

        .stApp {
            background-color: #f0f2f6;
        }

        /* Sidebar Styling */
        .stSidebar > div:first-child {
            background-color: var(--secondary);
            color: var(--light);
        }

        /* Header Styling */
        .header {
            background-color: var(--primary);
            padding: 20px 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            color: white;
            animation: fadeInDown 0.8s ease-out;
        }

        .header h1 {
            color: white;
            font-size: 2.5rem;
            margin-bottom: 5px;
        }

        /* Card Styling for Tasks */
        .task-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
            border-left: 5px solid var(--accent);
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            animation: fadeInUp 0.5s ease-out;
        }

        .task-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }

        .task-card.completed {
            border-left-color: var(--success);
            opacity: 0.8;
        }

        .task-card.high-priority {
            border-left-color: var(--danger);
        }

        .task-card.medium-priority {
            border-left-color: var(--warning);
        }

        .task-card h3 {
            color: var(--primary);
            margin-top: 0;
            margin-bottom: 10px;
        }

        .task-card p {
            color: var(--dark);
        }

        /* Buttons Styling */
        .stButton button {
            background-color: var(--secondary);
            color: white;
            border-radius: 5px;
            border: none;
            padding: 8px 15px;
            cursor: pointer;
            transition: background-color 0.2s ease-in-out, transform 0.1s ease-in-out;
        }

        .stButton button:hover {
            background-color: var(--primary);
            transform: translateY(-2px);
        }

        .stButton button:active {
            transform: translateY(0);
        }
        
        /* Specific button colors */
        .stButton button[data-testid="stFormSubmitButton"] {
            background-color: var(--primary);
        }
        .stButton button[data-testid="stFormSubmitButton"]:hover {
            background-color: var(--secondary);
        }

        /* Streamlit Widgets Styling */
        .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea, .stDateInput>div>div>input {
            border-radius: 5px;
            border: 1px solid #ced4da;
            padding: 8px 12px;
        }

        .stTextInput>div>div>input:focus, .stSelectbox>div>div>select:focus, .stTextArea>div>div>textarea:focus, .stDateInput>div>div>input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 0.2rem rgba(74, 111, 165, 0.25);
        }

        /* Animations */
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Progress Bar */
        .stProgress > div > div > div > div {
            background-color: var(--accent);
        }

        /* Expander */
        .stExpander {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stExpander button {
            background-color: transparent !important;
            color: var(--primary) !important;
            font-weight: bold;
        }
        .stExpander button:hover {
            background-color: #f0f0f0 !important;
        }

    </style>
    """, unsafe_allow_html=True)

# --- Funções CRUD para Usuários ---
def create_user(username, password, email):
    """
    Cria um novo usuário no banco de dados.
    Retorna True se o usuário for criado com sucesso, False caso contrário (e.g., username já existe).
    """
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
    """Verifica as credenciais do usuário."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()
    if data and check_hashes(password, data[0]):
        return True
    return False

def get_user_id(username):
    """Obtém o ID do usuário pelo nome de usuário."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = c.fetchone()[0]
    conn.close()
    return user_id

# --- Funções CRUD para Tarefas (agora com user_id) ---
def add_task(user_id, title, description, priority, due_date):
    """Adiciona uma nova tarefa ao banco de dados."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (user_id, title, description, priority, due_date) VALUES (?, ?, ?, ?, ?)",
              (user_id, title, description, priority, due_date))
    conn.commit()
    conn.close()

def get_tasks(user_id, status=None):
    """
    Recupera as tarefas de um usuário.
    Pode filtrar por status (pendente, concluída) ou retornar todas.
    """
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
    """Atualiza o status de uma tarefa (pendente/concluída)."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=? WHERE id=? AND user_id=?", (status, task_id, user_id))
    conn.commit()
    conn.close()

def delete_task(user_id, task_id):
    """Deleta uma tarefa específica de um usuário."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
    conn.commit()
    conn.close()

def get_task_by_id(user_id, task_id):
    """Obtém uma tarefa específica pelo ID."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
    task = c.fetchone()
    conn.close()
    return task

def update_task(user_id, task_id, title, description, priority, due_date):
    """Atualiza os detalhes de uma tarefa."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET title=?, description=?, priority=?, due_date=? WHERE id=? AND user_id=?",
              (title, description, priority, due_date, task_id, user_id))
    conn.commit()
    conn.close()

def delete_all_user_tasks(user_id):
    """Deleta todas as tarefas associadas a um usuário."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# --- Funções de Exibição e Páginas ---
def show_stats(user_id):
    """Exibe estatísticas de produtividade do usuário."""
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

def login_page():
    """Página de login do aplicativo."""
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

def register_page():
    """Página de cadastro de nova conta."""
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

def task_manager_page():
    """Página principal do aplicativo, exibida após o login."""
    local_css() # Aplicar CSS personalizado
    
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
        window.location.href = "?logout=true"; // Adiciona o parâmetro 'logout' na URL
    }}
    </script>
    """, unsafe_allow_html=True)
    
    # Abas para diferentes seções do aplicativo
    tab1, tab2, tab3, tab4 = st.tabs(["📌 Minhas Tarefas", "➕ Adicionar Tarefa", "📊 Estatísticas", "⚙️ Configurações"])
    
    with tab1:
        st.subheader("Suas Tarefas")
        
        # Filtros para exibição das tarefas
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
            # Exibir cada tarefa como um card
            for task in tasks:
                task_id, user_id, title, description, priority, due_date, status, created_at = task
                
                # Determinar classe CSS com base no status e prioridade para estilização
                card_class = "task-card"
                if status == "completed":
                    card_class += " completed"
                
                if priority == 3:
                    card_class += " high-priority"
                elif priority == 2:
                    card_class += " medium-priority"
                
                # Formatar data e prioridade para exibição
                due_date_str = datetime.strptime(due_date, "%Y-%m-%d").strftime("%d/%m/%Y") if due_date else "Sem data"
                priority_str = {1: "Baixa", 2: "Média", 3: "Alta"}.get(priority, "Desconhecida")
                
                # Renderizar o card da tarefa com Markdown e botões
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
                
                # Botões de ação para cada tarefa
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
                # O Streamlit retorna a tupla selecionada, então pegamos o segundo elemento (o valor numérico)
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
        
        # Gráfico de status das tarefas
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
        st.write("Personalize seu organizador de tarefas e gerencie dados.")
        
        # Tema (funcionalidade pode ser expandida com CSS dinâmico)
        theme = st.selectbox("Tema (funcionalidade em desenvolvimento)", ["Claro", "Escuro"], index=0)
        
        # Animations toggle (controla a visibilidade das animações CSS)
        animations = st.toggle("Ativar animações visuais (requer recarregar a página para efeito total)", value=True)
        
        st.markdown("---")
        st.warning("⚠️ **Zona de Perigo:** As ações abaixo são irreversíveis!")
        
        # Opção para limpar todas as tarefas
        if st.button("Limpar Todas as Minhas Tarefas", type="secondary"):
            confirm_clear = st.checkbox("Eu entendo que esta ação é irreversível e desejo excluir TODAS as minhas tarefas.")
            if confirm_clear:
                delete_all_user_tasks(st.session_state['user_id'])
                st.success("Todas as suas tarefas foram removidas com sucesso!")
                st.rerun() # Recarrega a página para atualizar a lista de tarefas

    # --- Modal de Edição de Tarefa (Exibido quando uma tarefa é selecionada para edição) ---
    if 'edit_task_id' in st.session_state:
        st.markdown("---")
        st.header("✏️ Editar Tarefa Selecionada")
        
        # Puxa os dados da tarefa a ser editada da session_state
        task_to_edit_id = st.session_state['edit_task_id']
        current_title = st.session_state['edit_title']
        current_description = st.session_state['edit_description']
        current_priority = st.session_state['edit_priority']
        current_due_date = st.session_state['edit_due_date']

        # Converte a data para o formato de objeto datetime para o st.date_input
        try:
            date_obj = datetime.strptime(current_due_date, "%Y-%m-%d").date() if current_due_date else datetime.today().date()
        except ValueError:
            date_obj = datetime.today().date() # Fallback se a data estiver em formato inválido
        
        with st.form("edit_task_form"):
            title = st.text_input("Título*", value=current_title)
            description = st.text_area("Descrição", value=current_description)
            col1, col2 = st.columns(2)
            with col1:
                priority_options = [("Baixa", 1), ("Média", 2), ("Alta", 3)]
                # Encontra o índice correto para pré-selecionar no selectbox
                current_priority_index = next((i for i, (name, val) in enumerate(priority_options) if val == current_priority), 0)
                priority_selected = st.selectbox("Prioridade*", 
                                               priority_options, 
                                               index=current_priority_index,
                                               format_func=lambda x: x[0])
                priority = priority_selected[1] # Pega o valor numérico da prioridade
            with col2:
                due_date = st.date_input("Data de Vencimento", 
                                       value=date_obj,
                                       min_value=datetime.today().date())
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Salvar Alterações", type="primary"):
                    if not title:
                        st.error("O título da tarefa é obrigatório!")
                    else:
                        update_task(st.session_state['user_id'], task_to_edit_id, 
                                  title, description, priority, due_date.strftime("%Y-%m-%d"))
                        st.success("Tarefa atualizada com sucesso!")
                        del st.session_state['edit_task_id'] # Limpa o estado de edição
                        st.rerun() # Recarrega para mostrar a tarefa atualizada
            with col2:
                if st.form_submit_button("Cancelar"):
                    del st.session_state['edit_task_id'] # Limpa o estado de edição
                    st.rerun() # Recarrega para fechar o formulário de edição

# --- Função Principal do Aplicativo ---
def main():
    """
    Função principal que gerencia o fluxo do aplicativo (login, cadastro, gerenciamento de tarefas).
    """
    init_db() # Garante que os bancos de dados estão inicializados
    
    # **Correção Aplicada Aqui:** Usando `st.query_params` para verificar e limpar parâmetros da URL.
    if "logout" in st.query_params:
        st.session_state.clear() # Limpa todas as informações da sessão
        st.query_params.clear()  # Limpa o parâmetro 'logout' da URL
        st.rerun() # Recarrega o aplicativo para a página de login

    # Inicializa o estado de login se não existir
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    # Gerencia qual página exibir (login, cadastro ou gerenciador de tarefas)
    if not st.session_state['logged_in']:
        if 'show_register' in st.session_state and st.session_state['show_register']:
            register_page()
        else:
            login_page()
    else:
        task_manager_page()

# Garante que a função principal seja executada quando o script é rodado
if __name__ == "__main__":
    main()
