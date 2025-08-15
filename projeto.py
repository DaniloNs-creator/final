import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import random
from typing import List, Tuple, Optional
import io
import contextlib
import chardet
from io import BytesIO
import base64
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Controle de atividades",
    page_icon="https://www.hafele.com.br/INTERSHOP/static/WFS/Haefele-HBR-Site/-/-/pt_BR/images/favicons/apple-touch-icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Gerenciador de Conexão Segura ---
@contextlib.contextmanager
def get_db_connection():
    """Gerenciador de contexto para conexão segura com o banco de dados."""
    conn = None
    try:
        conn = sqlite3.connect('clientes.db', check_same_thread=False, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")  # Melhora o desempenho com múltiplas conexões
        yield conn
    except sqlite3.Error as e:
        st.error(f"Erro de conexão com o banco de dados: {e}")
        raise
    finally:
        if conn:
            conn.close()

# --- CSS PROFISSIONAL ANIMADO ---
def load_css():
    st.markdown(f"""
        <style>
            :root {{
                --primary-color: #2c3e50;
                --secondary-color: #3498db;
                --accent-color: #e74c3c;
                --success-color: #2ecc71;
                --warning-color: #f39c12;
                --dark-color: #2c3e50;
                --light-color: #ecf0f1;
                --background-gradient: linear-gradient(135deg, #f5f7fa 0%, #e4e8ed 100%);
                --card-shadow: 0 10px 20px rgba(0,0,0,0.1), 0 6px 6px rgba(0,0,0,0.05);
                --transition: all 0.3s cubic-bezier(.25,.8,.25,1);
                --sidebar-bg: linear-gradient(180deg, #2c3e50 0%, #1a252f 100%);
            }}
            
            /* Estilo da capa profissional */
            .cover-container {{
                background: var(--background-gradient);
                padding: 3rem;
                border-radius: 12px;
                margin-bottom: 2rem;
                box-shadow: var(--card-shadow);
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .cover-container::before {{
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 5px;
                background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
            }}
            
            .cover-logo {{
                max-width: 300px;
                margin: 0 auto 1.5rem;
                display: block;
            }}
            
            .cover-title {{
                color: var(--dark-color);
                font-size: 2.8rem;
                font-weight: 800;
                margin-bottom: 1rem;
                background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                animation: fadeIn 1s ease-in-out;
            }}
            
            .cover-subtitle {{
                color: var(--dark-color);
                font-size: 1.2rem;
                opacity: 0.8;
                margin-bottom: 1.5rem;
            }}
            
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(-20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            /* Menu de navegação profissional */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 0;
                background: var(--light-color);
                padding: 0.5rem;
                border-radius: 12px;
                margin-bottom: 2rem;
                box-shadow: var(--card-shadow);
            }}
            
            .stTabs [data-baseweb="tab"] {{
                padding: 0.75rem 1.5rem;
                border-radius: 8px !important;
                background-color: transparent !important;
                transition: var(--transition);
                border: none !important;
                font-weight: 600;
                color: var(--dark-color) !important;
                margin: 0 !important;
            }}
            
            .stTabs [data-baseweb="tab"]:hover {{
                background-color: rgba(52, 152, 219, 0.1) !important;
            }}
            
            .stTabs [aria-selected="true"] {{
                background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)) !important;
                color: white !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            
            .stTabs [aria-selected="true"] [data-testid="stMarkdownContainer"] p {{
                color: white !important;
            }}
            
            /* Estilos gerais */
            .main {{
                background: var(--background-gradient);
                color: var(--dark-color);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            .header {{
                color: var(--dark-color);
                font-size: 1.8rem;
                font-weight: 700;
                margin: 1.5rem 0 1rem 0;
                padding-left: 10px;
                border-left: 5px solid var(--primary-color);
                animation: slideIn 0.5s ease-out;
            }}
            
            @keyframes slideIn {{
                from {{ transform: translateX(-20px); opacity: 0; }}
                to {{ transform: translateX(0); opacity: 1; }}
            }}
            
            .card {{
                background: white;
                border-radius: 12px;
                box-shadow: var(--card-shadow);
                padding: 1.8rem;
                margin-bottom: 1.8rem;
                transition: var(--transition);
                border: none;
                animation: popIn 0.4s ease-out;
            }}
            
            @keyframes popIn {{
                0% {{ transform: scale(0.95); opacity: 0; }}
                100% {{ transform: scale(1); opacity: 1; }}
            }}
            
            .card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 30px rgba(0,0,0,0.15);
            }}
            
            .completed {{
                background-color: rgba(46, 204, 113, 0.1);
                border-left: 5px solid var(--success-color);
                position: relative;
                overflow: hidden;
            }}
            
            .completed::after {{
                content: "✓ CONCLUÍDO";
                position: absolute;
                top: 10px;
                right: -30px;
                background: var(--success-color);
                color: white;
                padding: 3px 30px;
                font-size: 0.7rem;
                font-weight: bold;
                transform: rotate(45deg);
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            }}
            
            /* Sidebar styling */
            [data-testid="stSidebar"] {{
                background: var(--sidebar-bg) !important;
                color: white !important;
                padding: 1.5rem !important;
            }}
            
            /* Estilo para as métricas na sidebar */
            .sidebar-metric {{
                color: white !important;
            }}
            
            .sidebar-metric-label {{
                color: white !important;
                font-size: 1rem !important;
                margin-bottom: 0.5rem !important;
            }}
            
            .sidebar-metric-value {{
                color: white !important;
                font-size: 1.5rem !important;
                font-weight: bold !important;
            }}
            
            /* Estilo específico para as próximas entregas */
            .proxima-entrega {{
                background: white;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                color: black !important;
            }}
            
            .proxima-entrega strong, 
            .proxima-entrega small {{
                color: black !important;
            }}
            
            /* Formulários */
            .form-label {{
                font-weight: 600;
                margin-bottom: 0.5rem;
                color: var(--dark-color);
                display: block;
                position: relative;
                padding-left: 15px;
            }}
            
            .form-label::before {{
                content: "";
                position: absolute;
                left: 0;
                top: 50%;
                transform: translateY(-50%);
                width: 8px;
                height: 8px;
                background: var(--primary-color);
                border-radius: 50%;
            }}
            
            /* Botões */
            .stButton>button {{
                background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
                color: white;
                font-weight: 600;
                border: none;
                border-radius: 8px;
                padding: 0.7rem 1.5rem;
                transition: var(--transition);
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                width: 100%;
            }}
            
            .stButton>button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 7px 14px rgba(0,0,0,0.15);
                background: linear-gradient(135deg, var(--secondary-color), var(--primary-color));
            }}
            
            .stButton>button:active {{
                transform: translateY(0);
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            
            .danger-button {{
                background: linear-gradient(135deg, var(--accent-color), #c0392b) !important;
            }}
            
            .danger-button:hover {{
                background: linear-gradient(135deg, #c0392b, var(--accent-color)) !important;
            }}
            
            /* Inputs */
            .stTextInput>div>div>input, 
            .stSelectbox>div>div>select,
            .stDateInput>div>div>input,
            .stNumberInput>div>div>input {{
                background-color: white;
                border: 2px solid #dfe6e9;
                border-radius: 8px;
                padding: 0.7rem 1rem;
                transition: var(--transition);
            }}
            
            .stTextInput>div>div>input:focus, 
            .stSelectbox>div>div>select:focus,
            .stDateInput>div>div>input:focus {{
                border-color: var(--primary-color);
                box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
                outline: none;
            }}
            
            /* Mensagens */
            .success-message {{
                background-color: rgba(46, 204, 113, 0.2);
                color: var(--dark-color);
                padding: 1rem;
                border-radius: 8px;
                border-left: 5px solid var(--success-color);
                margin: 1rem 0;
                animation: fadeIn 0.5s ease-in;
            }}
            
            .error-message {{
                background-color: rgba(231, 76, 60, 0.2);
                color: var(--dark-color);
                padding: 1rem;
                border-radius: 8px;
                border-left: 5px solid var(--accent-color);
                margin: 1rem 0;
                animation: shake 0.5s ease-in;
            }}
            
            @keyframes shake {{
                0%, 100% {{ transform: translateX(0); }}
                20%, 60% {{ transform: translateX(-5px); }}
                40%, 80% {{ transform: translateX(5px); }}
            }}
            
            .info-message {{
                background-color: rgba(52, 152, 219, 0.2);
                color: var(--dark-color);
                padding: 1rem;
                border-radius: 8px;
                border-left: 5px solid var(--primary-color);
                margin: 1rem 0;
                animation: fadeIn 0.5s ease-in;
            }}
            
            /* Expanders */
            .stExpander [data-testid="stExpander"] {{
                border: none !important;
                box-shadow: var(--card-shadow);
                border-radius: 12px !important;
                margin-bottom: 1rem;
                transition: var(--transition);
            }}
            
            .stExpander [data-testid="stExpander"]:hover {{
                box-shadow: 0 15px 30px rgba(0,0,0,0.15);
            }}
            
            .stExpander [data-testid="stExpanderDetails"] {{
                padding: 1.5rem !important;
            }}
            
            /* DataFrames */
            .stDataFrame {{
                border-radius: 12px !important;
                box-shadow: var(--card-shadow) !important;
            }}
            
            /* Efeito de onda nos botões */
            .ripple {{
                position: relative;
                overflow: hidden;
            }}
            
            .ripple:after {{
                content: "";
                display: block;
                position: absolute;
                width: 100%;
                height: 100%;
                top: 0;
                left: 0;
                pointer-events: none;
                background-image: radial-gradient(circle, #fff 10%, transparent 10.01%);
                background-repeat: no-repeat;
                background-position: 50%;
                transform: scale(10, 10);
                opacity: 0;
                transition: transform .5s, opacity 1s;
            }}
            
            .ripple:active:after {{
                transform: scale(0, 0);
                opacity: 0.3;
                transition: 0s;
            }}
            
            /* Sidebar buttons */
            [data-testid="stSidebar"] .stButton>button {{
                background: linear-gradient(135deg, var(--secondary-color), #2980b9) !important;
            }}
            
            [data-testid="stSidebar"] .stButton>button:hover {{
                background: linear-gradient(135deg, #2980b9, var(--secondary-color)) !important;
            }}
            
            /* Custom scrollbar */
            ::-webkit-scrollbar {{
                width: 8px;
                height: 8px;
            }}
            
            ::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 10px;
            }}
            
            ::-webkit-scrollbar-thumb {{
                background: var(--primary-color);
                border-radius: 10px;
            }}
            
            ::-webkit-scrollbar-thumb:hover {{
                background: #2980b9;
            }}
            
            /* Pulse animation for important elements */
            @keyframes pulse {{
                0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(52, 152, 219, 0.7); }}
                70% {{ transform: scale(1.02); box-shadow: 0 0 0 10px rgba(52, 152, 219, 0); }}
                100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(52, 152, 219, 0); }}
            }}
            
            .pulse {{
                animation: pulse 2s infinite;
            }}
            
            /* Responsive adjustments */
            @media (max-width: 768px) {{
                .title {{
                    font-size: 2rem;
                }}
                
                .header {{
                    font-size: 1.5rem;
                }}
            }}
        </style>
    """, unsafe_allow_html=True)

# =============================================
# FUNÇÕES DO PROCESSADOR DE ARQUIVOS TXT
# =============================================

def processador_txt():
    st.title("📄 Processador de Arquivos TXT")
    st.markdown("""
    <div class="card">
        Remova linhas indesejadas de arquivos TXT. Carregue seu arquivo e defina os padrões a serem removidos.
    </div>
    """, unsafe_allow_html=True)

    def detectar_encoding(conteudo):
        """Detecta o encoding do conteúdo do arquivo"""
        resultado = chardet.detect(conteudo)
        return resultado['encoding']

    def processar_arquivo(conteudo, padroes):
        """
        Processa o conteúdo do arquivo removendo linhas indesejadas e realizando substituições
        """
        try:
            # Dicionário de substituições
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN"
            }
            
            # Detecta o encoding
            encoding = detectar_encoding(conteudo)
            
            # Decodifica o conteúdo
            try:
                texto = conteudo.decode(encoding)
            except UnicodeDecodeError:
                texto = conteudo.decode('latin-1')
            
            # Processa as linhas
            linhas = texto.splitlines()
            linhas_processadas = []
            
            for linha in linhas:
                linha = linha.strip()
                # Verifica se a linha contém algum padrão a ser removido
                if not any(padrao in linha for padrao in padroes):
                    # Aplica as substituições
                    for original, substituto in substituicoes.items():
                        linha = linha.replace(original, substituto)
                    linhas_processadas.append(linha)
            
            return "\n".join(linhas_processadas), len(linhas)
        
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            return None, 0

    # Padrões padrão para remoção
    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
    
    # Upload do arquivo
    arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'])
    
    # Opções avançadas
    with st.expander("⚙️ Configurações avançadas", expanded=False):
        padroes_adicionais = st.text_input(
            "Padrões adicionais para remoção (separados por vírgula)",
            help="Exemplo: padrão1, padrão2, padrão3"
        )
        
        padroes = padroes_default + [
            p.strip() for p in padroes_adicionais.split(",") 
            if p.strip()
        ] if padroes_adicionais else padroes_default

    if arquivo is not None:
        try:
            # Lê o conteúdo do arquivo
            conteudo = arquivo.read()
            
            # Processa o arquivo
            resultado, total_linhas = processar_arquivo(conteudo, padroes)
            
            if resultado is not None:
                # Mostra estatísticas
                linhas_processadas = len(resultado.splitlines())
                st.success(f"""
                **Processamento concluído!**  
                ✔️ Linhas originais: {total_linhas}  
                ✔️ Linhas processadas: {linhas_processadas}  
                ✔️ Linhas removidas: {total_linhas - linhas_processadas}
                """)

                # Prévia do resultado
                st.subheader("Prévia do resultado")
                st.text_area("Conteúdo processado", resultado, height=300)

                # Botão de download
                buffer = BytesIO()
                buffer.write(resultado.encode('utf-8'))
                buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Baixar arquivo processado",
                    data=buffer,
                    file_name=f"processado_{arquivo.name}",
                    mime="text/plain"
                )
        
        except Exception as e:
            st.error(f"Erro inesperado: {str(e)}")
            st.info("Tente novamente ou verifique o arquivo.")

# --- BANCO DE DADOS ---
def init_db():
    """Inicializa o banco de dados, criando a tabela se necessário."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS atividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                responsavel TEXT NOT NULL,
                atividade TEXT NOT NULL,
                data_entrega TEXT,
                mes_referencia TEXT,
                feito INTEGER DEFAULT 0,
                data_criacao TEXT NOT NULL
            )
        ''')
        conn.commit()

# --- FUNÇÕES DO SISTEMA ---
def adicionar_atividade(campos: Tuple) -> bool:
    """Adiciona uma nova atividade ao banco de dados."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            campos_completos = campos + (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),)
            
            c.execute('''
                INSERT INTO atividades (
                    cliente, responsavel, atividade, data_entrega, mes_referencia, data_criacao
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', campos_completos)
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return True
    except sqlite3.Error as e:
        st.error(f"Erro ao adicionar atividade: {e}")
        return False

def adicionar_atividades_em_lote(dados: List[Tuple]) -> bool:
    """Adiciona múltiplas atividades ao banco de dados em lote."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Preparar os dados com data de criação
            dados_completos = [
                (*linha, datetime.now().strftime('%Y-%m-%d %H:%M:%S')) 
                for linha in dados
            ]
            
            # Iniciar transação
            c.execute("BEGIN TRANSACTION")
            
            try:
                c.executemany('''
                    INSERT INTO atividades (
                        cliente, responsavel, atividade, data_entrega, mes_referencia, data_criacao
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', dados_completos)
                
                conn.commit()
                st.session_state.atualizar_lista = True  # Flag para atualizar a lista
                return True
            except sqlite3.Error as e:
                conn.rollback()
                st.error(f"Erro durante a inserção em lote: {e}")
                return False
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return False

def excluir_atividade(id: int) -> bool:
    """Remove uma atividade do banco de dados pelo ID."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM atividades WHERE id = ?', (id,))
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao excluir atividade: {e}")
        return False

def excluir_todas_atividades() -> bool:
    """Remove todas as atividades do banco de dados."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM atividades')
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return True
    except sqlite3.Error as e:
        st.error(f"Erro ao excluir atividades: {e}")
        return False

def marcar_feito(id: int, feito: bool) -> bool:
    """Atualiza o status de conclusão de uma atividade."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE atividades SET feito = ? WHERE id = ?', (1 if feito else 0, id))
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False

def atualizar_data_entrega(id: int, nova_data: str) -> bool:
    """Atualiza a data de entrega de uma atividade."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE atividades SET data_entrega = ? WHERE id = ?', (nova_data, id))
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar data de entrega: {e}")
        return False

def atualizar_mes_referencia(id: int, novo_mes: str) -> bool:
    """Atualiza o mês de referência de uma atividade."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE atividades SET mes_referencia = ? WHERE id = ?', (novo_mes, id))
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar mês de referência: {e}")
        return False

def processar_proximo_mes(id: int) -> bool:
    """Atualiza a data de entrega e o mês de referência para o próximo mês."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Obter a atividade atual
            c.execute('SELECT data_entrega, mes_referencia FROM atividades WHERE id = ?', (id,))
            atividade = c.fetchone()
            
            if not atividade:
                return False
                
            data_entrega = atividade[0]
            mes_referencia = atividade[1]
            
            # Converter para objetos de data
            if data_entrega:
                data_obj = datetime.strptime(data_entrega, '%Y-%m-%d')
                nova_data = (data_obj.replace(day=1) + timedelta(days=32)).replace(day=data_obj.day).strftime('%Y-%m-%d')
            else:
                nova_data = None
            
            if mes_referencia:
                mes, ano = mes_referencia.split('/')
                mes_obj = datetime.strptime(f"01/{mes}/{ano}", '%d/%m/%Y')
                novo_mes_obj = mes_obj + timedelta(days=32)
                novo_mes = novo_mes_obj.strftime('%m/%Y')
            else:
                novo_mes = None
            
            # Atualizar no banco de dados
            c.execute('''
                UPDATE atividades 
                SET data_entrega = ?, mes_referencia = ? 
                WHERE id = ?
            ''', (nova_data, novo_mes, id))
            
            conn.commit()
            st.session_state.atualizar_lista = True  # Flag para atualizar a lista
            return c.rowcount > 0
    except Exception as e:
        st.error(f"Erro ao processar próximo mês: {e}")
        return False

def get_atividades(filtro_mes: str = None, filtro_responsavel: str = None) -> List[Tuple]:
    """Retorna todas as atividades ordenadas por data de criação com filtros opcionais."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            query = 'SELECT * FROM atividades'
            params = []
            
            conditions = []
            if filtro_mes and filtro_mes != "Todos":
                conditions.append('mes_referencia = ?')
                params.append(filtro_mes)
            if filtro_responsavel and filtro_responsavel != "Todos":
                conditions.append('responsavel = ?')
                params.append(filtro_responsavel)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY data_criacao DESC'
            
            c.execute(query, tuple(params))
            return c.fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar atividades: {e}")
        return []

def get_clientes() -> List[str]:
    """Retorna a lista de clientes únicos."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT DISTINCT cliente FROM atividades ORDER BY cliente')
            return ["Todos"] + [row[0] for row in c.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar clientes: {e}")
        return ["Todos"]

def get_responsaveis() -> List[str]:
    """Retorna a lista de responsáveis únicos."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT DISTINCT responsavel FROM atividades ORDER BY responsavel')
            return ["Todos"] + [row[0] for row in c.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Erro ao recuperar responsáveis: {e}")
        return ["Todos"]
        
def get_entregas_gerais(start_date: str, end_date: str) -> pd.DataFrame:
    """Retorna os dados de entregas gerais para um período selecionado."""
    try:
        with get_db_connection() as conn:
            query = '''
                SELECT 
                    cliente,
                    responsavel, 
                    atividade, 
                    data_entrega,
                    mes_referencia
                FROM atividades
                WHERE data_entrega BETWEEN ? AND ?
                ORDER BY data_entrega DESC
            '''
            df = pd.read_sql(query, conn, params=(start_date, end_date))
            return df
    except Exception as e:
        st.error(f"Erro ao gerar dados de entregas gerais: {e}")
        return pd.DataFrame()

def get_dados_indicadores() -> pd.DataFrame:
    """Retorna dados para os indicadores de entrega."""
    try:
        with get_db_connection() as conn:
            query = '''
                SELECT 
                    mes_referencia,
                    SUM(feito) as concluidas,
                    COUNT(*) as total,
                    (SUM(feito) * 100.0 / COUNT(*)) as percentual
                FROM atividades
                GROUP BY mes_referencia
                ORDER BY SUBSTR(mes_referencia, 4) || SUBSTR(mes_referencia, 1, 2)
            '''
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erro ao gerar indicadores: {e}")
        return pd.DataFrame()

def get_dados_responsaveis() -> pd.DataFrame:
    """Retorna dados para análise por responsável."""
    try:
        with get_db_connection() as conn:
            query = '''
                SELECT 
                    responsavel,
                    SUM(feito) as concluidas,
                    COUNT(*) as total,
                    (SUM(feito) * 100.0 / COUNT(*)) as percentual
                FROM atividades
                GROUP BY responsavel
                ORDER BY percentual DESC
            '''
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erro ao gerar dados por responsável: {e}")
        return pd.DataFrame()

# --- COMPONENTES DA INTERFACE ---
def mostrar_capa():
    """Exibe a capa profissional do sistema."""
    st.markdown("""
    <div class="cover-container">
        <img src="https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png" class="cover-logo">
        <h1 class="cover-title">Controle de atividades</h1>
        <p class="cover-subtitle">Painel de Gestão de Atividades e Entregas</p>
    </div>
    """, unsafe_allow_html=True)

def login_section():
    """Exibe a seção de login."""
    mostrar_capa()
    
    with st.container():
        with st.form("login_form"):
            col1, col2 = st.columns(2)
            username = col1.text_input("Usuário", key="username")
            password = col2.text_input("Senha", type="password", key="password")
            
            if st.form_submit_button("Entrar", use_container_width=True):
                if username == "admin" and password == "reali":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Tente novamente.", icon="⚠️")

def upload_atividades():
    """Exibe o formulário para upload de atividades em Excel."""
    st.markdown('<div class="header">📤 Upload de Atividades</div>', unsafe_allow_html=True)
    
    with st.expander("📝 Instruções para Upload", expanded=False):
        st.markdown("""
            **Como preparar seu arquivo Excel:**
            1. O arquivo deve conter as colunas obrigatórias:
               - `Cliente` (texto)
               - `Responsável` (texto)
               - `Atividade` (texto)
               - `Data de Entrega` (data no formato YYYY-MM-DD)
               - `Mês de Referência` (texto no formato MM/YYYY)
            2. Salve o arquivo no formato .xlsx ou .xls
        """)
    
    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel com as atividades", 
        type=["xlsx", "xls"],
        accept_multiple_files=False,
        help="Arraste e solte ou clique para selecionar o arquivo"
    )
    
    if uploaded_file is not None:
        try:
            # Lê o arquivo Excel
            df = pd.read_excel(uploaded_file)
            
            # Mapeia os nomes das colunas
            column_mapping = {
                'CLIENTE': 'cliente',
                'RESPONSÁVEL': 'responsavel',
                'ATIVIDADE': 'atividade',
                'DATA DE ENTREGA': 'data_entrega',
                'MÊS DE REFERÊNCIA': 'mes_referencia'
            }

            # Garante que as colunas existam no dataframe, usando um valor padrão se não
            for col_excel, col_db in column_mapping.items():
                if col_excel not in df.columns:
                    df[col_excel] = None
            
            # Mostra pré-visualização
            st.markdown("**Pré-visualização dos dados (5 primeiras linhas):**")
            st.dataframe(df.head())
            
            # Prepara dados para inserção
            atividades = []
            for _, row in df.iterrows():
                atividades.append((
                    row['CLIENTE'],
                    row['RESPONSÁVEL'],
                    row['ATIVIDADE'],
                    row['DATA DE ENTREGA'].strftime('%Y-%m-%d') if pd.notna(row['DATA DE ENTREGA']) else None,
                    row['MÊS DE REFERÊNCIA']
                ))
            
            # Botão para confirmar importação
            if st.button("Confirmar Importação", type="primary", use_container_width=True):
                if adicionar_atividades_em_lote(atividades):
                    st.success(f"✅ {len(atividades)} atividades importadas com sucesso!")
                    st.rerun()  # Força a atualização da lista de atividades
                else:
                    st.error("Ocorreu um erro ao importar as atividades")
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

def cadastro_atividade():
    """Exibe o formulário para cadastro de novas atividades."""
    st.markdown('<div class="header">📝 Cadastro de Atividades</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Formulário Manual", "Upload em Lote"])
    
    with tab1:
        with st.form("nova_atividade", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cliente = st.text_input("Cliente*", placeholder="Nome do cliente")
                responsavel = st.text_input("Responsável*", placeholder="Nome do responsável")
                
            with col2:
                atividade = st.text_input("Atividade*", placeholder="Descrição da atividade")
                data_entrega = st.date_input("Data de Entrega", value=datetime.now())
                mes_referencia = st.selectbox("Mês de Referência", [
                    f"{mes:02d}/{ano}" 
                    for ano in range(2023, 2026) 
                    for mes in range(1, 13)
                ])
            
            st.markdown("<small>Campos marcados com * são obrigatórios</small>", unsafe_allow_html=True)
            
            if st.form_submit_button("Adicionar Atividade", use_container_width=True, type="primary"):
                if cliente and responsavel and atividade:
                    campos = (
                        cliente,
                        responsavel, 
                        atividade,
                        data_entrega.strftime('%Y-%m-%d'),
                        mes_referencia
                    )
                    if adicionar_atividade(campos):
                        st.success("Atividade cadastrada com sucesso!", icon="✅")
                        st.rerun()  # Força a atualização da lista de atividades
                else:
                    st.error("Preencha os campos obrigatórios!", icon="❌")
    
    with tab2:
        upload_atividades()

def lista_atividades():
    """Exibe a lista de atividades cadastradas com filtros."""
    st.markdown('<div class="header">📋 Lista de Atividades</div>', unsafe_allow_html=True)
    
    # Botão para excluir todas as atividades
    if st.button("🗑️ Excluir Todas as Atividades", type="primary", use_container_width=True, key="delete_all", 
               help="CUIDADO: Esta ação não pode ser desfeita!"):
        if excluir_todas_atividades():
            st.success("Todas as atividades foram excluídas com sucesso!")
            time.sleep(1)
            st.rerun()
    
    col1, col2 = st.columns(2)
    
    with col1:
        meses = sorted([
            f"{mes:02d}/{ano}" 
            for ano in range(2023, 2026) 
            for mes in range(1, 13)
        ], reverse=True)
        mes_selecionado = st.selectbox("Filtrar por mês de referência:", ["Todos"] + meses)
    
    with col2:
        responsaveis = get_responsaveis()
        responsavel_selecionado = st.selectbox("Filtrar por responsável:", responsaveis)
    
    atividades = get_atividades(mes_selecionado if mes_selecionado != "Todos" else None,
                              responsavel_selecionado if responsavel_selecionado != "Todos" else None)
    
    if not atividades:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.", icon="ℹ️")
        return
    
    for row in atividades:
        id = row[0]
        cliente = row[1]
        responsavel = row[2]
        atividade = row[3]
        data_entrega = row[4]
        mes_referencia = row[5]
        feito = bool(row[6])
        data_criacao = row[7]
        
        with st.expander(f"{'✅' if feito else '📌'} {cliente} - {responsavel} - {atividade} - {mes_referencia}", expanded=False):
            st.markdown(f'<div class="card{" completed" if feito else ""}">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Cliente:** {cliente}")
                st.markdown(f"**Responsável:** {responsavel}")
                st.markdown(f"**Atividade:** {atividade}")
                
                # Edição da data de entrega
                nova_data = st.date_input(
                    "Data de Entrega",
                    value=datetime.strptime(data_entrega, '%Y-%m-%d') if data_entrega else datetime.now(),
                    key=f"data_{id}"
                )
                if st.button("Atualizar Data", key=f"update_data_{id}"):
                    if atualizar_data_entrega(id, nova_data.strftime('%Y-%m-%d')):
                        st.success("Data de entrega atualizada com sucesso!")
                        time.sleep(1)
                        st.rerun()
                
                # Edição do mês de referência
                novo_mes = st.selectbox(
                    "Mês de Referência",
                    [f"{mes:02d}/{ano}" for ano in range(2023, 2026) for mes in range(1, 13)],
                    index=[f"{mes:02d}/{ano}" for ano in range(2023, 2026) for mes in range(1, 13)].index(mes_referencia) if mes_referencia else 0,
                    key=f"mes_{id}"
                )
                if st.button("Atualizar Mês", key=f"update_mes_{id}"):
                    if atualizar_mes_referencia(id, novo_mes):
                        st.success("Mês de referência atualizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                
                # Botão para processar próximo mês
                if st.button("Processar Próximo Mês", key=f"process_{id}", type="primary"):
                    if processar_proximo_mes(id):
                        st.success("Atividade atualizada para o próximo mês!")
                        time.sleep(1)
                        st.rerun()
                
                st.markdown(f"**Data de Criação:** {data_criacao}")
                
            with col2:
                # Checkbox para marcar/desmarcar como concluído
                novo_status = st.checkbox(
                    "Marcar como concluído",
                    value=feito,
                    key=f"feito_{id}",
                    on_change=lambda id=id, feito=feito: marcar_feito(id, not feito)
                )
                
                if st.button("Excluir", key=f"del_{id}", use_container_width=True):
                    if excluir_atividade(id):
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

def mostrar_entregas_gerais():
    """Exibe a tabela de entregas gerais com filtro de período."""
    st.markdown('<div class="header">📦 Entregas Gerais</div>', unsafe_allow_html=True)

    today = datetime.now()
    start_date = st.date_input("Data de Início", value=today - timedelta(days=30))
    end_date = st.date_input("Data de Fim", value=today)

    if start_date > end_date:
        st.error("A data de início não pode ser posterior à data de fim.")
        return

    df = get_entregas_gerais(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    if df.empty:
        st.info("Nenhuma entrega encontrada no período selecionado.")
    else:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Baixar como CSV",
            data=csv,
            file_name=f'entregas_gerais_{start_date}_{end_date}.csv',
            mime='text/csv',
        )

def mostrar_indicadores():
    """Exibe os indicadores de entrega."""
    st.markdown('<div class="header">📊 Indicadores de Entrega</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📅 Por Mês", "👤 Por Responsável"])
    
    with tab1:
        dados_mes = get_dados_indicadores()
        
        if dados_mes.empty:
            st.warning("Não há dados suficientes para exibir os indicadores por mês.")
        else:
            st.subheader("Entregas por Mês")
            fig_bar = px.bar(
                dados_mes,
                x='mes_referencia',
                y=['concluidas', 'total'],
                barmode='group',
                labels={'value': 'Quantidade', 'mes_referencia': 'Mês de Referência'},
                color_discrete_map={'concluidas': '#2ecc71', 'total': '#3498db'}
            )
            fig_bar.update_layout(
                showlegend=True, 
                legend_title_text='',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#f1f1f1')
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.subheader("Percentual de Conclusão")
            fig_pie = px.pie(
                dados_mes,
                values='percentual',
                names='mes_referencia',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Greens
            )
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                marker=dict(line=dict(color='#fff', width=2))
            )
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.subheader("Detalhamento por Mês")
            dados_mes['percentual'] = dados_mes['percentual'].round(2)
            st.dataframe(
                dados_mes[['mes_referencia', 'concluidas', 'total', 'percentual']]
                .rename(columns={
                    'mes_referencia': 'Mês',
                    'concluidas': 'Concluídas',
                    'total': 'Total',
                    'percentual': '% Conclusão'
                }),
                use_container_width=True,
                height=400
            )
    
    with tab2:
        dados_responsaveis = get_dados_responsaveis()
        
        if dados_responsaveis.empty:
            st.warning("Não há dados suficientes para exibir os indicadores por responsável.")
        else:
            st.subheader("Entregas por Responsável")
            fig_bar_resp = px.bar(
                dados_responsaveis,
                x='responsavel',
                y=['concluidas', 'total'],
                barmode='group',
                labels={'value': 'Quantidade', 'responsavel': 'Responsável'},
                color_discrete_map={'concluidas': '#2ecc71', 'total': '#3498db'}
            )
            fig_bar_resp.update_layout(
                showlegend=True, 
                legend_title_text='',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#f1f1f1')
            )
            st.plotly_chart(fig_bar_resp, use_container_width=True)
            
            st.subheader("Distribuição de Atividades")
            fig_pie_resp = px.pie(
                dados_responsaveis,
                values='total',
                names='responsavel',
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie_resp.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                marker=dict(line=dict(color='#fff', width=2))
            )
            fig_pie_resp.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie_resp, use_container_width=True)
            
            st.subheader("Performance por Responsável")
            fig_hbar = px.bar(
                dados_responsaveis,
                x='percentual',
                y='responsavel',
                orientation='h',
                text='percentual',
                labels={'percentual': '% Conclusão', 'responsavel': 'Responsável'},
                color='percentual',
                color_continuous_scale='Greens'
            )
            fig_hbar.update_traces(
                texttemplate='%{x:.1f}%', 
                textposition='outside',
                marker=dict(line=dict(color='rgba(0,0,0,0.1)', width=1))
            )
            fig_hbar.update_layout(
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_hbar, use_container_width=True)
            
            st.subheader("Detalhamento por Responsável")
            dados_responsaveis['percentual'] = dados_responsaveis['percentual'].round(2)
            st.dataframe(
                dados_responsaveis[['responsavel', 'concluidas', 'total', 'percentual']]
                .rename(columns={
                    'responsavel': 'Responsável',
                    'concluidas': 'Concluídas',
                    'total': 'Total',
                    'percentual': '% Conclusão'
                }),
                use_container_width=True,
                height=400
            )

def mostrar_sidebar():
    """Exibe a barra lateral com estatísticas e próximas entregas."""
    with st.sidebar:
        st.markdown("## Configurações")
        
        if st.button("🚪 Sair", use_container_width=True, type="primary"):
            st.session_state.logged_in = False
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Estatísticas Rápidas")
        
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                c.execute("SELECT COUNT(*) FROM atividades")
                total = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM atividades WHERE feito = 1")
                concluidas = c.fetchone()[0]
                
                percentual = (concluidas / total * 100) if total > 0 else 0
                
                # Exibindo as métricas com texto branco
                st.markdown(f"""
                    <div class="sidebar-metric-label">Total de Atividades</div>
                    <div class="sidebar-metric-value">{total}</div>
                    <div class="sidebar-metric-label">Atividades Concluídas</div>
                    <div class="sidebar-metric-value">{concluidas} ({percentual:.1f}%)</div>
                """, unsafe_allow_html=True)
                
                # Próximas entregas
                hoje = datetime.now().strftime('%Y-%m-%d')
                c.execute('''
                    SELECT cliente, responsavel, atividade, data_entrega 
                    FROM atividades 
                    WHERE data_entrega >= ? AND feito = 0
                    ORDER BY data_entrega ASC
                    LIMIT 5
                ''', (hoje,))
                proximas = c.fetchall()
                
                if proximas:
                    st.markdown("### Próximas Entregas")
                    for cliente, responsavel, atividade, data in proximas:
                        st.markdown(f"""
                            <div class="proxima-entrega">
                                <strong>{cliente} - {responsavel}</strong><br>
                                {atividade}<br>
                                <small>📅 {data}</small>
                            </div>
                        """, unsafe_allow_html=True)
        except sqlite3.Error as e:
            st.error(f"Erro ao carregar estatísticas: {e}")

# --- APLICAÇÃO PRINCIPAL ---
def main():
    """Função principal que gerencia o fluxo da aplicação."""
    load_css()
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_section()
    else:
        # Menu de navegação profissional
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Lista de Atividades", 
            "📝 Cadastrar Atividades", 
            "📊 Indicadores de Entrega", 
            "📦 Entregas Gerais",
            "📄 Processador TXT"
        ])
        
        with tab1:
            lista_atividades()
        
        with tab2:
            cadastro_atividade()
        
        with tab3:
            mostrar_indicadores()

        with tab4:
            mostrar_entregas_gerais()
            
        with tab5:
            processador_txt()

        mostrar_sidebar()

if __name__ == "__main__":
    main()
