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
import xml.etree.ElementTree as ET
import os
import hashlib
import xml.dom.minidom
from datetime import date
import traceback
from pathlib import Path

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Controle de atividades",
    page_icon="https://www.hafele.com.br/INTERSHOP/static/WFS/Haefele-HBR-Site/-/-/pt_BR/images/favicons/apple-touch-icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Namespaces para CT-e
CTE_NAMESPACES = {
    'cte': 'http://www.portalfiscal.inf.br/cte'
}

# Inicialização do estado da sessão
if 'selected_xml' not in st.session_state:
    st.session_state.selected_xml = None

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
            
            /* Estilo Post-it para atividades */
            .post-it-container {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }}
            
            .post-it {{
                width: 100%;
                min-height: 200px;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                position: relative;
                transition: all 0.3s ease;
                transform: rotate(-1deg);
                cursor: pointer;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }}
            
            .post-it:hover {{
                transform: rotate(0deg) scale(1.02);
                box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            }}
            
            .post-it.yellow {{
                background: linear-gradient(135deg, #fff8c9 0%, #fff176 100%);
                border-left: 5px solid #ffd54f;
            }}
            
            .post-it.blue {{
                background: linear-gradient(135deg, #bbdefb 0%, #90caf9 100%);
                border-left: 5px solid #2196f3;
            }}
            
            .post-it.green {{
                background: linear-gradient(135deg, #c8e6c9 0%, #a5d6a7 100%);
                border-left: 5px solid #4caf50;
            }}
            
            .post-it.pink {{
                background: linear-gradient(135deg, #f8bbd0 0%, #f48fb1 100%);
                border-left: 5px solid #e91e63;
            }}
            
            .post-it.purple {{
                background: linear-gradient(135deg, #e1bee7 0%, #ce93d8 100%);
                border-left: 5px solid #9c27b0;
            }}
            
            .post-it.completed {{
                opacity: 0.7;
                background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
                border-left: 5px solid #4caf50;
            }}
            
            .post-it-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 15px;
                border-bottom: 2px solid rgba(0,0,0,0.1);
                padding-bottom: 10px;
            }}
            
            .post-it-cliente {{
                font-weight: bold;
                font-size: 1.2em;
                color: #2c3e50;
                flex: 1;
            }}
            
            .post-it-responsavel {{
                font-size: 0.9em;
                color: #7f8c8d;
                background: rgba(255,255,255,0.5);
                padding: 4px 10px;
                border-radius: 12px;
                white-space: nowrap;
            }}
            
            .post-it-atividade {{
                margin: 10px 0;
                font-size: 1em;
                line-height: 1.4;
                color: #34495e;
                flex: 1;
                overflow-wrap: break-word;
            }}
            
            .post-it-footer {{
                margin-top: 15px;
            }}
            
            .post-it-data {{
                font-weight: bold;
                font-size: 0.9em;
                color: #2c3e50;
                margin-bottom: 5px;
            }}
            
            .post-it-mes {{
                background: rgba(0,0,0,0.1);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                color: #7f8c8d;
                display: inline-block;
            }}
            
            .post-it-status {{
                position: absolute;
                top: 10px;
                right: 10px;
                background: rgba(46, 204, 113, 0.9);
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.7em;
                font-weight: bold;
            }}
            
            /* Modal style for post-it details */
            .post-it-modal {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }}
            
            .post-it-modal-content {{
                background: white;
                padding: 2rem;
                border-radius: 12px;
                max-width: 600px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
            }}
        </style>
    """, unsafe_allow_html=True)

# --- CLASSES E FUNÇÕES DO SISTEMA CT-E ---
class CTeDatabase:
    def __init__(self, db_name="cte_database.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com as tabelas necessárias para CT-e"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Tabela para metadados dos XMLs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS xml_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE,
                    file_path TEXT,
                    file_size INTEGER,
                    content_hash TEXT,
                    upload_date TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Tabela para conteúdo dos XMLs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS xml_content (
                    id INTEGER PRIMARY KEY,
                    xml_content TEXT,
                    FOREIGN KEY (id) REFERENCES xml_files (id)
                )
            ''')
            
            # Tabela para dados estruturados específicos do CT-e
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cte_structured_data (
                    id INTEGER PRIMARY KEY,
                    xml_id INTEGER,
                    nCT TEXT,
                    dhEmi DATE,
                    cMunIni TEXT,
                    UFIni TEXT,
                    cMunFim TEXT,
                    UFFim TEXT,
                    emit_xNome TEXT,
                    vTPrest DECIMAL(15, 2),
                    rem_xNome TEXT,
                    infNFe_chave TEXT,
                    FOREIGN KEY (xml_id) REFERENCES xml_files (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Erro ao inicializar banco de dados: {str(e)}")
            return False
    
    def insert_xml(self, filename, file_path, file_size, content_hash, xml_content=None):
        """Insere um novo XML de CT-e no banco de dados"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO xml_files 
                (filename, file_path, file_size, content_hash, upload_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (filename, file_path, file_size, content_hash, datetime.now()))
            
            file_id = cursor.lastrowid
            
            # Se não houve inserção (arquivo duplicado), obter o ID existente
            if file_id == 0:
                cursor.execute('SELECT id FROM xml_files WHERE filename = ?', (filename,))
                result = cursor.fetchone()
                file_id = result[0] if result else None
            
            if file_id and xml_content:
                cursor.execute('''
                    INSERT OR REPLACE INTO xml_content (id, xml_content)
                    VALUES (?, ?)
                ''', (file_id, xml_content))
                
                # Extrai e armazena dados estruturados específicos do CT-e
                self.extract_cte_data(file_id, xml_content, conn)
            
            conn.commit()
            return file_id
            
        except sqlite3.IntegrityError:
            return None
        except Exception as e:
            st.error(f"Erro ao inserir CT-e: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()
    
    def extract_cte_data(self, xml_id, xml_content, conn):
        """Extrai dados específicos do CT-e para análise no Power BI"""
        try:
            root = ET.fromstring(xml_content)
            
            # Registra namespaces
            for prefix, uri in CTE_NAMESPACES.items():
                ET.register_namespace(prefix, uri)
            
            # Extrai dados específicos do CT-e com base nos campos solicitados
            nCT = self.find_text(root, './/cte:nCT')
            dhEmi = self.find_text(root, './/cte:dhEmi')
            cMunIni = self.find_text(root, './/cte:cMunIni')
            UFIni = self.find_text(root, './/cte:UFIni')
            cMunFim = self.find_text(root, './/cte:cMunFim')
            UFFim = self.find_text(root, './/cte:UFFim')
            emit_xNome = self.find_text(root, './/cte:emit/cte:xNome')
            vTPrest = self.find_text(root, './/cte:vTPrest')
            rem_xNome = self.find_text(root, './/cte:rem/cte:xNome')
            
            # Extrai chave da NFe associada (se existir)
            infNFe_chave = self.find_text(root, './/cte:infNFe/cte:chave')
            
            # Formata data se encontrada
            if dhEmi:
                dhEmi = dhEmi[:10]  # Pega apenas a data (YYYY-MM-DD)
            
            # Converte valor para decimal
            try:
                vTPrest = float(vTPrest) if vTPrest else None
            except (ValueError, TypeError):
                vTPrest = None
            
            # Insere os dados estruturados do CT-e
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO cte_structured_data 
                (xml_id, nCT, dhEmi, cMunIni, UFIni, cMunFim, UFFim, 
                 emit_xNome, vTPrest, rem_xNome, infNFe_chave)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (xml_id, nCT, dhEmi, cMunIni, UFIni, cMunFim, UFFim,
                 emit_xNome, vTPrest, rem_xNome, infNFe_chave))
            
        except Exception as e:
            st.error(f"Erro ao extrair dados do CT-e: {str(e)}")
    
    def find_text(self, element, xpath):
        """Encontra texto usando XPath com namespaces"""
        try:
            # Para cada namespace registrado, tentar encontrar o elemento
            for prefix, uri in CTE_NAMESPACES.items():
                full_xpath = xpath.replace('cte:', f'{{{uri}}}')
                found = element.find(full_xpath)
                if found is not None and found.text:
                    return found.text
            
            # Tentativa alternativa sem namespace
            found = element.find(xpath.replace('cte:', ''))
            if found is not None and found.text:
                return found.text
                
            return None
        except Exception:
            return None
    
    def get_all_files(self):
        """Retorna todos os arquivos do banco de dados"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, filename, file_size, upload_date FROM xml_files ORDER BY upload_date DESC')
            files = cursor.fetchall()
            
            conn.close()
            return files
        except Exception as e:
            st.error(f"Erro ao buscar arquivos: {str(e)}")
            return []
    
    def get_file_count(self):
        """Retorna o número total de arquivos"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM xml_files')
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
        except Exception as e:
            st.error(f"Erro ao contar arquivos: {str(e)}")
            return 0
    
    def search_files(self, search_term):
        """Busca arquivos por nome"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, filename, file_size, upload_date 
                FROM xml_files 
                WHERE filename LIKE ? 
                ORDER BY upload_date DESC
            ''', (f'%{search_term}%',))
            
            files = cursor.fetchall()
            conn.close()
            return files
        except Exception as e:
            st.error(f"Erro ao buscar arquivos: {str(e)}")
            return []
    
    def get_xml_content(self, file_id):
        """Retorna o conteúdo de um XML específico"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('SELECT xml_content FROM xml_content WHERE id = ?', (file_id,))
            result = cursor.fetchone()
            
            conn.close()
            return result[0] if result else None
        except Exception as e:
            st.error(f"Erro ao buscar conteúdo do XML: {str(e)}")
            return None
    
    def get_cte_data(self):
        """Retorna todos os dados estruturados de CT-e para Power BI"""
        try:
            conn = sqlite3.connect(self.db_name)
            
            query = '''
                SELECT 
                    xf.id,
                    xf.filename,
                    xf.upload_date,
                    cte.nCT,
                    cte.dhEmi,
                    cte.cMunIni,
                    cte.UFIni,
                    cte.cMunFim,
                    cte.UFFim,
                    cte.emit_xNome,
                    cte.vTPrest,
                    cte.rem_xNome,
                    cte.infNFe_chave
                FROM cte_structured_data cte
                JOIN xml_files xf ON cte.xml_id = xf.id
                ORDER BY cte.dhEmi DESC
            '''
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Erro ao carregar dados de CT-e: {str(e)}")
            return pd.DataFrame()
    
    def get_cte_data_by_date_range(self, start_date, end_date):
        """Retorna dados de CT-e filtrados por intervalo de datas"""
        try:
            conn = sqlite3.connect(self.db_name)
            
            query = '''
                SELECT 
                    xf.id,
                    xf.filename,
                    xf.upload_date,
                    cte.nCT,
                    cte.dhEmi,
                    cte.cMunIni,
                    cte.UFIni,
                    cte.cMunFim,
                    cte.UFFim,
                    cte.emit_xNome,
                    cte.vTPrest,
                    cte.rem_xNome,
                    cte.infNFe_chave
                FROM cte_structured_data cte
                JOIN xml_files xf ON cte.xml_id = xf.id
                WHERE date(cte.dhEmi) BETWEEN date(?) AND date(?)
                ORDER BY cte.dhEmi DESC
            '''
            
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
            conn.close()
            return df
        except Exception as e:
            st.error(f"Erro ao carregar dados por intervalo: {str(e)}")
            return pd.DataFrame()

class CTeProcessor:
    def __init__(self, storage_path="storage/cte_files"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def calculate_hash(self, file_content):
        """Calcula hash do conteúdo do arquivo para verificar duplicatas"""
        return hashlib.md5(file_content).hexdigest()
    
    def save_cte_file(self, file_content, filename):
        """Salva o arquivo XML de CT-e no sistema de arquivos"""
        try:
            file_path = self.storage_path / filename
            
            # Verifica se arquivo já existe
            if file_path.exists():
                existing_hash = self.calculate_hash(file_path.read_bytes())
                new_hash = self.calculate_hash(file_content)
                
                if existing_hash == new_hash:
                    return file_path, False  # Arquivo duplicado
            
            # Salva o arquivo
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            return file_path, True
        except Exception as e:
            st.error(f"Erro ao salvar arquivo: {str(e)}")
            return None, False
    
    def process_uploaded_file(self, uploaded_file, db):
        """Processa um arquivo XML de CT-e enviado"""
        try:
            file_content = uploaded_file.getvalue()
            filename = uploaded_file.name
            
            # Verifica se é um XML
            if not filename.lower().endswith('.xml'):
                return False, "Arquivo não é XML"
            
            # Verifica se é um CT-e pela estrutura do arquivo
            try:
                content_str = file_content.decode('utf-8', errors='ignore')
                if 'CTe' not in content_str and 'conhecimento' not in content_str.lower():
                    return False, "Arquivo não parece ser um CT-e"
            except:
                return False, "Erro ao verificar tipo do arquivo"
            
            # Calcula hash
            content_hash = self.calculate_hash(file_content)
            
            # Salva arquivo
            file_path, is_new = self.save_cte_file(file_content, filename)
            
            if not is_new:
                return False, "Arquivo duplicado"
            
            # Insere no banco de dados
            file_size = len(file_content)
            file_id = db.insert_xml(
                filename=filename,
                file_path=str(file_path),
                file_size=file_size,
                content_hash=content_hash,
                xml_content=content_str
            )
            
            if file_id:
                return True, f"CT-e {filename} armazenado com sucesso! ID: {file_id}"
            else:
                return False, "Erro ao armazenar no banco de dados"
        except Exception as e:
            return False, f"Erro ao processar arquivo: {str(e)}"
    
    def process_directory(self, directory_path, db):
        """Processa todos os CT-es de um diretório"""
        results = {
            'success': 0,
            'errors': 0,
            'duplicates': 0,
            'messages': []
        }
        
        try:
            directory_path = Path(directory_path)
            
            if not directory_path.exists():
                results['messages'].append("Diretório não encontrado")
                return results
            
            # Busca por arquivos XML
            xml_files = list(directory_path.glob("*.xml")) + list(directory_path.glob("*.XML"))
            
            for xml_file in xml_files:
                try:
                    file_content = xml_file.read_bytes()
                    filename = xml_file.name
                    
                    # Verifica se é um CT-e
                    content_str = file_content.decode('utf-8', errors='ignore')
                    if 'CTe' not in content_str and 'conhecimento' not in content_str.lower():
                        results['messages'].append(f"Ignorado (não é CT-e): {filename}")
                        continue
                    
                    content_hash = self.calculate_hash(file_content)
                    file_path, is_new = self.save_cte_file(file_content, filename)
                    
                    if not is_new:
                        results['duplicates'] += 1
                        results['messages'].append(f"Duplicado: {filename}")
                        continue
                    
                    file_size = len(file_content)
                    file_id = db.insert_xml(
                        filename=filename,
                        file_path=str(file_path),
                        file_size=file_size,
                        content_hash=content_hash,
                        xml_content=content_str
                    )
                    
                    if file_id:
                        results['success'] += 1
                        results['messages'].append(f"Sucesso: {filename} (ID: {file_id})")
                    else:
                        results['errors'] += 1
                        results['messages'].append(f"Erro BD: {filename}")
                        
                except Exception as e:
                    results['errors'] += 1
                    results['messages'].append(f"Erro processando {xml_file.name}: {str(e)}")
            
            return results
        except Exception as e:
            results['errors'] += 1
            results['messages'].append(f"Erro geral no processamento: {str(e)}")
            return results

# Inicialização
@st.cache_resource
def init_cte_database():
    return CTeDatabase()

@st.cache_resource
def init_cte_processor():
    return CTeProcessor()

# --- FUNÇÕES EXISTENTES DO SEU PROJETO ---
def inicializar_banco_dados():
    """Inicializa o banco de dados com tabelas necessárias."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Tabela de clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT,
                telefone TEXT,
                endereco TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de atividades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS atividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                descricao TEXT NOT NULL,
                responsavel TEXT NOT NULL,
                data_inicio DATE NOT NULL,
                data_entrega DATE NOT NULL,
                status TEXT DEFAULT 'Pendente',
                prioridade TEXT DEFAULT 'Média',
                observacoes TEXT,
                data_conclusao DATE,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id)
            )
        ''')
        
        conn.commit()

def obter_clientes():
    """Retorna todos os clientes do banco de dados."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM clientes ORDER BY nome")
        return cursor.fetchall()

def obter_atividades(filtro_status=None, filtro_responsavel=None):
    """Retorna atividades do banco de dados com filtros opcionais."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT a.id, c.nome, a.descricao, a.responsavel, 
                   a.data_inicio, a.data_entrega, a.status, a.prioridade
            FROM atividades a
            JOIN clientes c ON a.cliente_id = c.id
            WHERE 1=1
        """
        params = []
        
        if filtro_status and filtro_status != "Todos":
            query += " AND a.status = ?"
            params.append(filtro_status)
            
        if filtro_responsavel and filtro_responsavel != "Todos":
            query += " AND a.responsavel = ?"
            params.append(filtro_responsavel)
            
        query += " ORDER BY a.data_entrega"
        
        cursor.execute(query, params)
        return cursor.fetchall()

def inserir_cliente(nome, email, telefone, endereco):
    """Insere um novo cliente no banco de dados."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (nome, email, telefone, endereco) VALUES (?, ?, ?, ?)",
            (nome, email, telefone, endereco)
        )
        conn.commit()
        return cursor.lastrowid

def inserir_atividade(cliente_id, descricao, responsavel, data_inicio, data_entrega, prioridade, observacoes):
    """Insere uma nova atividade no banco de dados."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO atividades 
               (cliente_id, descricao, responsavel, data_inicio, data_entrega, prioridade, observacoes) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cliente_id, descricao, responsavel, data_inicio, data_entrega, prioridade, observacoes)
        )
        conn.commit()
        return cursor.lastrowid

def atualizar_status_atividade(atividade_id, status):
    """Atualiza o status de uma atividade."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        data_conclusao = datetime.now().date() if status == "Concluído" else None
        
        cursor.execute(
            "UPDATE atividades SET status = ?, data_conclusao = ? WHERE id = ?",
            (status, data_conclusao, atividade_id)
        )
        conn.commit()

def obter_estatisticas():
    """Retorna estatísticas do sistema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Total de clientes
        cursor.execute("SELECT COUNT(*) FROM clientes")
        total_clientes = cursor.fetchone()[0]
        
        # Total de atividades
        cursor.execute("SELECT COUNT(*) FROM atividades")
        total_atividades = cursor.fetchone()[0]
        
        # Atividades por status
        cursor.execute("SELECT status, COUNT(*) FROM atividades GROUP BY status")
        atividades_por_status = cursor.fetchall()
        
        # Atividades por responsável
        cursor.execute("SELECT responsavel, COUNT(*) FROM atividades GROUP BY responsavel")
        atividades_por_responsavel = cursor.fetchall()
        
        return {
            "total_clientes": total_clientes,
            "total_atividades": total_atividades,
            "atividades_por_status": atividades_por_status,
            "atividades_por_responsavel": atividades_por_responsavel
        }

# --- FUNÇÃO PRINCIPAL ---
def main():
    # Carregar CSS
    load_css()
    
    # Inicializar banco de dados
    inicializar_banco_dados()
    
    # Inicializar componentes do CT-e
    cte_db = init_cte_database()
    cte_processor = init_cte_processor()
    
    # Sidebar
    with st.sidebar:
        st.image("https://www.hafele.com.br/INTERSHOP/static/WFS/Haefele-HBR-Site/-/-/pt_BR/images/favicons/apple-touch-icon.png", width=100)
        st.title("Sistema de Gestão")
        
        # Navegação
        opcoes_menu = ["Dashboard", "Clientes", "Atividades", "Relatórios", "Sistema CT-e"]
        pagina_selecionada = st.radio("Navegação", opcoes_menu)
        
        # Estatísticas na sidebar
        st.divider()
        st.subheader("Estatísticas")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Total de clientes
            cursor.execute("SELECT COUNT(*) FROM clientes")
            total_clientes = cursor.fetchone()[0]
            st.metric("Total de Clientes", total_clientes)
            
            # Total de atividades
            cursor.execute("SELECT COUNT(*) FROM atividades")
            total_atividades = cursor.fetchone()[0]
            st.metric("Total de Atividades", total_atividades)
            
            # Atividades pendentes
            cursor.execute("SELECT COUNT(*) FROM atividades WHERE status != 'Concluído'")
            atividades_pendentes = cursor.fetchone()[0]
            st.metric("Atividades Pendentes", atividades_pendentes)
            
            # Próximas entregas
            st.divider()
            st.subheader("Próximas Entregas")
            
            hoje = datetime.now().date()
            amanha = hoje + timedelta(days=1)
            
            cursor.execute('''
                SELECT c.nome, a.descricao, a.data_entrega 
                FROM atividades a
                JOIN clientes c ON a.cliente_id = c.id
                WHERE a.data_entrega BETWEEN ? AND ? AND a.status != 'Concluído'
                ORDER BY a.data_entrega
                LIMIT 5
            ''', (hoje, amanha))
            
            proximas = cursor.fetchall()
            
            for cliente, descricao, data_entrega in proximas:
                st.markdown(f"""
                    <div class="proxima-entrega">
                        <strong>{cliente}</strong><br>
                        <small>{descricao[:30]}...</small><br>
                        <small>Entrega: {data_entrega}</small>
                    </div>
                """, unsafe_allow_html=True)
    
    # Conteúdo principal baseado na seleção
    if pagina_selecionada == "Dashboard":
        st.title("Dashboard de Atividades")
        
        # Estatísticas
        estatisticas = obter_estatisticas()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Clientes", estatisticas["total_clientes"])
        with col2:
            st.metric("Total de Atividades", estatisticas["total_atividades"])
        with col3:
            st.metric("Atividades Pendentes", sum(1 for status, count in estatisticas["atividades_por_status"] if status != "Concluído"))
        with col4:
            st.metric("Atividades Concluídas", sum(count for status, count in estatisticas["atividades_por_status"] if status == "Concluído"))
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de atividades por status
            df_status = pd.DataFrame(estatisticas["atividades_por_status"], columns=["Status", "Quantidade"])
            fig_status = px.pie(df_status, values="Quantidade", names="Status", title="Atividades por Status")
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Gráfico de atividades por responsável
            df_responsavel = pd.DataFrame(estatisticas["atividades_por_responsavel"], columns=["Responsável", "Quantidade"])
            fig_responsavel = px.bar(df_responsavel, x="Responsável", y="Quantidade", title="Atividades por Responsável")
            st.plotly_chart(fig_responsavel, use_container_width=True)
        
        # Lista de atividades recentes
        st.subheader("Atividades Recentes")
        atividades = obter_atividades()
        
        if atividades:
            for atividade in atividades[:5]:
                id_atividade, cliente, descricao, responsavel, data_inicio, data_entrega, status, prioridade = atividade
                
                st.markdown(f"""
                    <div class="card {'completed' if status == 'Concluído' else ''}">
                        <h3>{cliente} - {descricao}</h3>
                        <p><strong>Responsável:</strong> {responsavel} | <strong>Prioridade:</strong> {prioridade}</p>
                        <p><strong>Início:</strong> {data_inicio} | <strong>Entrega:</strong> {data_entrega}</p>
                        <p><strong>Status:</strong> {status}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nenhuma atividade cadastrada.")
            
    elif pagina_selecionada == "Clientes":
        st.title("Gestão de Clientes")
        
        tab1, tab2 = st.tabs(["Cadastrar Cliente", "Lista de Clientes"])
        
        with tab1:
            with st.form("form_cliente"):
                st.subheader("Novo Cliente")
                
                col1, col2 = st.columns(2)
                with col1:
                    nome = st.text_input("Nome completo*")
                    email = st.text_input("E-mail")
                with col2:
                    telefone = st.text_input("Telefone")
                    endereco = st.text_area("Endereço")
                
                if st.form_submit_button("Cadastrar Cliente"):
                    if nome:
                        cliente_id = inserir_cliente(nome, email, telefone, endereco)
                        st.success(f"Cliente {nome} cadastrado com sucesso! ID: {cliente_id}")
                    else:
                        st.error("O nome do cliente é obrigatório.")
        
        with tab2:
            st.subheader("Clientes Cadastrados")
            clientes = obter_clientes()
            
            if clientes:
                for cliente in clientes:
                    id_cliente, nome = cliente
                    st.markdown(f"""
                        <div class="card">
                            <h3>{nome}</h3>
                            <p><strong>ID:</strong> {id_cliente}</p>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhum cliente cadastrado.")
                
    elif pagina_selecionada == "Atividades":
        st.title("Gestão de Atividades")
        
        tab1, tab2 = st.tabs(["Nova Atividade", "Lista de Atividades"])
        
        with tab1:
            with st.form("form_atividade"):
                st.subheader("Nova Atividade")
                
                clientes = obter_clientes()
                cliente_opcoes = {nome: id for id, nome in clientes} if clientes else {}
                
                col1, col2 = st.columns(2)
                with col1:
                    if clientes:
                        cliente_nome = st.selectbox("Cliente*", options=list(cliente_opcoes.keys()))
                        cliente_id = cliente_opcoes[cliente_nome]
                    else:
                        st.info("Cadastre primeiro um cliente para criar atividades.")
                        cliente_id = None
                    
                    responsavel = st.text_input("Responsável*")
                    data_inicio = st.date_input("Data de Início*", value=datetime.now().date())
                
                with col2:
                    descricao = st.text_area("Descrição da Atividade*")
                    data_entrega = st.date_input("Data de Entrega*", value=datetime.now().date() + timedelta(days=7))
                    prioridade = st.selectbox("Prioridade", options=["Baixa", "Média", "Alta"])
                
                observacoes = st.text_area("Observações")
                
                if st.form_submit_button("Cadastrar Atividade") and cliente_id:
                    atividade_id = inserir_atividade(
                        cliente_id, descricao, responsavel, data_inicio, data_entrega, prioridade, observacoes
                    )
                    st.success(f"Atividade cadastrada com sucesso! ID: {atividade_id}")
        
        with tab2:
            st.subheader("Atividades Cadastradas")
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                filtro_status = st.selectbox("Filtrar por Status", options=["Todos", "Pendente", "Em Andamento", "Concluído"])
            with col2:
                atividades = obter_atividades()
                responsaveis = list(set([atividade[3] for atividade in atividades])) if atividades else []
                responsaveis.insert(0, "Todos")
                filtro_responsavel = st.selectbox("Filtrar por Responsável", options=responsaveis)
            
            # Lista de atividades
            atividades_filtradas = obter_atividades(
                filtro_status if filtro_status != "Todos" else None,
                filtro_responsavel if filtro_responsavel != "Todos" else None
            )
            
            if atividades_filtradas:
                for atividade in atividades_filtradas:
                    id_atividade, cliente, descricao, responsavel, data_inicio, data_entrega, status, prioridade = atividade
                    
                    st.markdown(f"""
                        <div class="card {'completed' if status == 'Concluído' else ''}">
                            <h3>{cliente} - {descricao}</h3>
                            <p><strong>Responsável:</strong> {responsavel} | <strong>Prioridade:</strong> {prioridade}</p>
                            <p><strong>Início:</strong> {data_inicio} | <strong>Entrega:</strong> {data_entrega}</p>
                            <p><strong>Status:</strong> {status}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Controles de status
                    col1, col2, col3, col4 = st.columns(4)
                    if col1.button("Marcar como Pendente", key=f"pendente_{id_atividade}"):
                        atualizar_status_atividade(id_atividade, "Pendente")
                        st.rerun()
                    if col2.button("Marcar como Em Andamento", key=f"andamento_{id_atividade}"):
                        atualizar_status_atividade(id_atividade, "Em Andamento")
                        st.rerun()
                    if col3.button("Marcar como Concluído", key=f"concluido_{id_atividade}"):
                        atualizar_status_atividade(id_atividade, "Concluído")
                        st.rerun()
            else:
                st.info("Nenhuma atividade encontrada com os filtros selecionados.")
                
    elif pagina_selecionada == "Relatórios":
        st.title("Relatórios e Análises")
        
        st.subheader("Relatório de Atividades por Período")
        
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data Início", value=datetime.now().date() - timedelta(days=30))
        with col2:
            data_fim = st.date_input("Data Fim", value=datetime.now().date())
        
        if st.button("Gerar Relatório"):
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT c.nome, a.descricao, a.responsavel, a.data_inicio, 
                           a.data_entrega, a.status, a.prioridade
                    FROM atividades a
                    JOIN clientes c ON a.cliente_id = c.id
                    WHERE a.data_inicio BETWEEN ? AND ?
                    ORDER BY a.data_inicio
                ''', (data_inicio, data_fim))
                
                atividades = cursor.fetchall()
                
                if atividades:
                    df = pd.DataFrame(atividades, columns=["Cliente", "Descrição", "Responsável", "Data Início", "Data Entrega", "Status", "Prioridade"])
                    st.dataframe(df)
                    
                    # Estatísticas do relatório
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total de Atividades", len(df))
                    with col2:
                        st.metric("Atividades Concluídas", len(df[df["Status"] == "Concluído"]))
                    with col3:
                        st.metric("Taxa de Conclusão", f"{len(df[df['Status'] == 'Concluído']) / len(df) * 100:.1f}%")
                    
                    # Gráfico de atividades por status
                    fig = px.pie(df, names="Status", title="Distribuição de Atividades por Status")
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.info("Nenhuma atividade encontrada no período selecionado.")
                    
    elif pagina_selecionada == "Sistema CT-e":
        st.title("📄 Sistema de Armazenamento de CT-e")
        st.markdown("### Armazene, consulte e exporte seus CT-es para Power BI")
        
        # Sidebar do CT-e
        st.sidebar.header("Estatísticas CT-e")
        total_files = cte_db.get_file_count()
        st.sidebar.metric("Total de CT-es Armazenados", total_files)
        
        # Navegação por abas
        tab1, tab2, tab3, tab4 = st.tabs(["Upload", "Consultar CT-es", "Visualizar CT-e", "Dados para Power BI"])
        
        # Tab 1 - Upload
        with tab1:
            st.header("Upload de CT-es")
            
            upload_option = st.radio("Selecione o tipo de upload:", 
                                    ["Upload Individual", "Upload em Lote", "Upload por Diretório"])
            
            if upload_option == "Upload Individual":
                uploaded_file = st.file_uploader(
                    "Selecione um arquivo XML de CT-e", 
                    type=['xml'],
                    help="Selecione um arquivo XML de CT-e para armazenar"
                )
                
                if uploaded_file:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.info(f"Arquivo selecionado: {uploaded_file.name}")
                        st.write(f"Tamanho: {len(uploaded_file.getvalue())} bytes")
                    
                    with col2:
                        if st.button("🔄 Armazenar CT-e", use_container_width=True):
                            with st.spinner("Processando arquivo..."):
                                success, message = cte_processor.process_uploaded_file(uploaded_file, cte_db)
                                
                                if success:
                                    st.success(message)
                                    st.balloons()
                                else:
                                    st.error(message)
                            
                            # Atualiza estatísticas
                            time.sleep(2)
                            st.rerun()
            
            elif upload_option == "Upload em Lote":
                uploaded_files = st.file_uploader(
                    "Selecione múltiplos arquivos XML de CT-e", 
                    type=['xml'],
                    accept_multiple_files=True,
                    help="Selecione vários arquivos XML de CT-e para armazenar"
                )
                
                if uploaded_files:
                    st.info(f"{len(uploaded_files)} arquivo(s) selecionado(s)")
                    
                    if st.button("🔄 Armazenar Todos", type="primary"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        success_count = 0
                        error_count = 0
                        
                        for i, uploaded_file in enumerate(uploaded_files):
                            progress = (i + 1) / len(uploaded_files)
                            progress_bar.progress(progress)
                            status_text.text(f"Processando {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
                            
                            success, message = cte_processor.process_uploaded_file(uploaded_file, cte_db)
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                            
                            time.sleep(0.1)
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        st.success(f"Processamento concluído!")
                        st.write(f"✅ Sucessos: {success_count}")
                        st.write(f"❌ Erros: {error_count}")
                        
                        time.sleep(2)
                        st.rerun()
            
            else:  # Upload por Diretório
                st.subheader("Para grandes volumes (50k+ CT-es)")
                st.info("Para processar 50 mil CT-es, recomendamos usar a opção de diretório")
                
                directory_path = st.text_input(
                    "Caminho do diretório com CT-es",
                    placeholder="Ex: C:/cte_files/ ou /home/usuario/cte_files/"
                )
                
                if st.button("📁 Processar Diretório", type="secondary"):
                    if directory_path and os.path.exists(directory_path):
                        with st.spinner("Processando diretório... Isso pode demorar para muitos arquivos"):
                            results = cte_processor.process_directory(directory_path, cte_db)
                            
                            st.success(f"Processamento do diretório concluído!")
                            st.write(f"✅ Sucessos: {results['success']}")
                            st.write(f"🔄 Duplicados: {results['duplicates']}")
                            st.write(f"❌ Erros: {results['errors']}")
                            
                            # Mostra últimas 10 mensagens
                            with st.expander("Ver detalhes do processamento"):
                                for msg in results['messages'][-10:]:
                                    st.write(msg)
                            
                            time.sleep(2)
                            st.rerun()
                    else:
                        st.error("Diretório não encontrado ou caminho inválido")
        
        # Tab 2 - Consultar CT-es
        with tab2:
            st.header("Consultar CT-es Armazenados")
            
            files = cte_db.get_all_files()
            
            if files:
                st.write(f"Total de arquivos: {len(files)}")
                
                # Filtros
                col1, col2, col3 = st.columns(3)
                with col1:
                    items_per_page = st.selectbox("Itens por página", [10, 25, 50, 100], key="items_page")
                with col2:
                    search_term = st.text_input("Buscar por nome", key="search_term")
                with col3:
                    sort_order = st.selectbox("Ordenar por", ["Data Upload (Mais Recente)", "Data Upload (Mais Antigo)", "Nome (A-Z)", "Nome (Z-A)"])
                
                # Aplicar filtro de busca
                if search_term:
                    filtered_files = cte_db.search_files(search_term)
                else:
                    filtered_files = files
                
                # Aplicar ordenação
                if sort_order == "Data Upload (Mais Recente)":
                    filtered_files = sorted(filtered_files, key=lambda x: x[3], reverse=True)
                elif sort_order == "Data Upload (Mais Antigo)":
                    filtered_files = sorted(filtered_files, key=lambda x: x[3])
                elif sort_order == "Nome (A-Z)":
                    filtered_files = sorted(filtered_files, key=lambda x: x[1])
                elif sort_order == "Nome (Z-A)":
                    filtered_files = sorted(filtered_files, key=lambda x: x[1], reverse=True)
                
                # Paginação
                total_pages = max(1, (len(filtered_files) + items_per_page - 1) // items_per_page)
                page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, key="page_num")
                
                start_idx = (page - 1) * items_per_page
                end_idx = min(start_idx + items_per_page, len(filtered_files))
                
                # Tabela de arquivos
                st.write(f"Mostrando {start_idx + 1}-{end_idx} de {len(filtered_files)} arquivos")
                
                for file in filtered_files[start_idx:end_idx]:
                    file_id, filename, file_size, upload_date = file
                    
                    with st.expander(f"📄 {filename}"):
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        
                        col1.write(f"**ID:** {file_id}")
                        col2.write(f"**Tamanho:** {file_size} bytes")
                        col3.write(f"**Data Upload:** {upload_date}")
                        
                        # Botão para visualizar
                        if col4.button("👁️ Visualizar", key=f"view_{file_id}"):
                            st.session_state.selected_xml = file_id
                            st.rerun()
                
                # Botão para exportar lista
                if st.button("📊 Exportar Lista para Excel"):
                    df = pd.DataFrame(filtered_files, columns=['ID', 'Nome do Arquivo', 'Tamanho (bytes)', 'Data de Upload'])
                    df['Data de Upload'] = pd.to_datetime(df['Data de Upload']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Criar arquivo Excel em memória
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name='CT-es', index=False)
                    
                    # Preparar para download
                    output.seek(0)
                    b64 = base64.b64encode(output.read()).decode()
                    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="lista_ctes.xlsx">📥 Baixar Lista de CT-es</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
            else:
                st.info("Nenhum arquivo armazenado ainda.")
        
        # Tab 3 - Visualizar CT-e
        with tab3:
            st.header("Visualizar Conteúdo do CT-e")
            
            # Se um CT-e foi selecionado para visualização
            if st.session_state.selected_xml:
                xml_content = cte_db.get_xml_content(st.session_state.selected_xml)
                
                if xml_content:
                    # Formatar o XML para melhor visualização
                    try:
                        parsed_xml = xml.dom.minidom.parseString(xml_content)
                        pretty_xml = parsed_xml.toprettyxml()
                        
                        st.text_area("Conteúdo do CT-e (formatado)", pretty_xml, height=500)
                        
                        # Botões de ação
                        col1, col2, col3 = st.columns(3)
                        
                        # Download do XML
                        b64_xml = base64.b64encode(xml_content.encode()).decode()
                        href = f'<a href="data:application/xml;base64,{b64_xml}" download="cte_{st.session_state.selected_xml}.xml">📥 Baixar CT-e</a>'
                        col1.markdown(href, unsafe_allow_html=True)
                        
                        # Copiar para área de transferência
                        if col2.button("📋 Copiar Conteúdo"):
                            st.code(xml_content)
                            st.success("Conteúdo copiado para a área de transferência!")
                        
                        # Voltar para a lista
                        if col3.button("↩️ Voltar para Lista"):
                            st.session_state.selected_xml = None
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Erro ao formatar CT-e: {e}")
                        st.text_area("Conteúdo do CT-e (original)", xml_content, height=500)
                else:
                    st.error("Conteúdo do CT-e não encontrado.")
                    if st.button("↩️ Voltar para Lista"):
                        st.session_state.selected_xml = None
                        st.rerun()
            else:
                st.info("Selecione um CT-e na aba 'Consultar CT-es' para visualizar seu conteúdo.")
        
        # Tab 4 - Dados para Power BI
        with tab4:
            st.header("Dados Estruturados para Power BI")
            
            st.info("""
            Esta seção fornece os dados estruturados extraídos dos CT-es para uso no Power BI.
            Os dados incluyen informações específicas de Conhecimento de Transporte Eletrônico.
            """)
            
            # Filtro por data
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Data inicial", value=date.today().replace(day=1))
            with col2:
                end_date = st.date_input("Data final", value=date.today())
            
            # Carregar dados
            if st.button("Carregar Dados CT-e", type="primary"):
                with st.spinner("Carregando dados de CT-e..."):
                    df = cte_db.get_cte_data_by_date_range(
                        start_date.strftime('%Y-%m-%d'), 
                        end_date.strftime('%Y-%m-%d')
                    )
                    
                    if not df.empty:
                        st.success(f"Dados carregados: {len(df)} registros encontrados")
                        
                        # Exibir dataframe
                        st.dataframe(df)
                        
                        # Estatísticas rápidas
                        st.subheader("📈 Estatísticas de CT-e")
                        col1, col2, col3 = st.columns(3)
                        
                        col1.metric("Total de CT-es", len(df))
                        if 'vTPrest' in df.columns:
                            col2.metric("Valor Total", f"R$ {df['vTPrest'].sum():,.2f}")
                            col3.metric("Valor Médio", f"R$ {df['vTPrest'].mean():,.2f}" if len(df) > 0 else "R$ 0,00")
                        else:
                            col2.metric("Valor Total", "N/A")
                            col3.metric("Valor Médio", "N/A")
                        
                        # Opções de exportação
                        st.subheader("📤 Exportar Dados")
                        
                        # Exportar para Excel
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df.to_excel(writer, sheet_name='Dados_CTe', index=False)
                        
                        output.seek(0)
                        b64 = base64.b64encode(output.read()).decode()
                        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="dados_cte_powerbi.xlsx">📥 Baixar para Excel</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
                        # Exportar para CSV
                        csv = df.to_csv(index=False)
                        b64_csv = base64.b64encode(csv.encode()).decode()
                        href_csv = f'<a href="data:file/csv;base64,{b64_csv}" download="dados_cte_powerbi.csv">📥 Baixar para CSV</a>'
                        st.markdown(href_csv, unsafe_allow_html=True)
                        
                        # Instruções para Power BI
                        with st.expander("🔧 Instruções para conectar ao Power BI"):
                            st.markdown("""
                            ### Como conectar esses dados ao Power BI:
                            
                            1. **Método 1: Arquivo Excel/CSV**
                               - Baixe os dados usando os botões acima
                               - No Power BI, selecione "Obter Dados" > "Arquivo" > "Excel" ou "Texto/CSV"
                               - Selecione o arquivo baixado
                            
                            2. **Método 2: Conexão direta com SQLite (Recomendado)**
                               - No Power BI, selecione "Obter Dados" > "Mais..." > "Banco de dados" > "SQLite"
                               - No campo "Banco de dados", digite o caminho completo para o arquivo `cte_database.db`
                               - Selecione a tabela `cte_structured_data`
                            
                            3. **Método 3: Conexão ODBC**
                               - Configure um driver ODBC para SQLite
                               - No Power BI, selecione "Obter Dados" > "ODBC"
                               - Selecione a fonte de dados configurada
                            
                            **Vantagem dos métodos 2 e 3:** Atualizações em tempo real sem precisar reimportar arquivos.
                            """)
                    else:
                        st.warning("Nenhum dado de CT-e encontrado para o período selecionado.")
        
        # Footer
        st.sidebar.divider()
        st.sidebar.info("""
        **💡 Dicas:**
        - Para 50k CT-es, use a opção de diretório
        - Conecte o Power BI diretamente ao banco SQLite
        - Dados armazenados permanentemente
        """)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {str(e)}")
        st.code(traceback.format_exc())