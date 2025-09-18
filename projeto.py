import streamlit as st 
import sqlite3
from datetime import datetime, timedelta, date
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
import traceback
from pathlib import Path

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Sistema de Gestão de Atividades",
    page_icon="📊",
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
if 'selected_atividade' not in st.session_state:
    st.session_state.selected_atividade = None

# --- BANCO DE DADOS PARA ATIVIDADES ---
class AtividadesDatabase:
    def __init__(self, db_name="atividades.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com as tabelas necessárias para atividades"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Tabela principal de atividades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS atividades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT NOT NULL,
                    responsavel TEXT NOT NULL,
                    atividade TEXT NOT NULL,
                    data_entrega DATE,
                    mes_referencia TEXT,
                    feito BOOLEAN DEFAULT FALSE,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    prioridade TEXT DEFAULT 'Média',
                    status TEXT DEFAULT 'Pendente',
                    categoria TEXT,
                    observacoes TEXT
                )
            ''')
            
            # Tabela para histórico de alterações
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS atividades_historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    atividade_id INTEGER,
                    campo_alterado TEXT,
                    valor_anterior TEXT,
                    valor_novo TEXT,
                    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario TEXT,
                    FOREIGN KEY (atividade_id) REFERENCES atividades (id)
                )
            ''')
            
            # Tabela para categorias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    descricao TEXT,
                    cor TEXT DEFAULT '#3498db'
                )
            ''')
            
            # Inserir categorias padrão
            categorias_padrao = [
                ('Administrativo', 'Atividades administrativas', '#3498db'),
                ('Financeiro', 'Atividades financeiras', '#2ecc71'),
                ('Comercial', 'Atividades comerciais', '#e74c3c'),
                ('Operacional', 'Atividades operacionais', '#f39c12'),
                ('Recursos Humanos', 'Atividades de RH', '#9b59b6')
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO categorias (nome, descricao, cor)
                VALUES (?, ?, ?)
            ''', categorias_padrao)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Erro ao inicializar banco de dados: {str(e)}")
            return False
    
    def insert_atividade(self, atividade_data):
        """Insere uma nova atividade no banco de dados"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO atividades 
                (cliente, responsavel, atividade, data_entrega, mes_referencia, 
                 prioridade, status, categoria, observacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                atividade_data['cliente'],
                atividade_data['responsavel'],
                atividade_data['atividade'],
                atividade_data['data_entrega'],
                atividade_data['mes_referencia'],
                atividade_data.get('prioridade', 'Média'),
                atividade_data.get('status', 'Pendente'),
                atividade_data.get('categoria'),
                atividade_data.get('observacoes')
            ))
            
            atividade_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return atividade_id
        except Exception as e:
            st.error(f"Erro ao inserir atividade: {str(e)}")
            return None
    
    def update_atividade(self, atividade_id, campo, novo_valor, usuario="Sistema"):
        """Atualiza uma atividade específica e registra no histórico"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Obter valor anterior
            cursor.execute(f'SELECT {campo} FROM atividades WHERE id = ?', (atividade_id,))
            valor_anterior = cursor.fetchone()[0]
            
            # Atualizar atividade
            cursor.execute(f'''
                UPDATE atividades 
                SET {campo} = ?, data_atualizacao = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (novo_valor, atividade_id))
            
            # Registrar no histórico
            cursor.execute('''
                INSERT INTO atividades_historico 
                (atividade_id, campo_alterado, valor_anterior, valor_novo, usuario)
                VALUES (?, ?, ?, ?, ?)
            ''', (atividade_id, campo, str(valor_anterior), str(novo_valor), usuario))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Erro ao atualizar atividade: {str(e)}")
            return False
    
    def delete_atividade(self, atividade_id):
        """Remove uma atividade do banco de dados"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM atividades WHERE id = ?', (atividade_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Erro ao excluir atividade: {str(e)}")
            return False
    
    def get_all_atividades(self, filtros=None):
        """Retorna todas as atividades com filtros opcionais"""
        try:
            conn = sqlite3.connect(self.db_name)
            
            query = '''
                SELECT 
                    id, cliente, responsavel, atividade, data_entrega,
                    mes_referencia, feito, data_criacao, data_atualizacao,
                    prioridade, status, categoria, observacoes
                FROM atividades
            '''
            
            params = []
            conditions = []
            
            if filtros:
                if filtros.get('mes_referencia') and filtros['mes_referencia'] != "Todos":
                    conditions.append('mes_referencia = ?')
                    params.append(filtros['mes_referencia'])
                
                if filtros.get('responsavel') and filtros['responsavel'] != "Todos":
                    conditions.append('responsavel = ?')
                    params.append(filtros['responsavel'])
                
                if filtros.get('status') and filtros['status'] != "Todos":
                    conditions.append('status = ?')
                    params.append(filtros['status'])
                
                if filtros.get('categoria') and filtros['categoria'] != "Todos":
                    conditions.append('categoria = ?')
                    params.append(filtros['categoria'])
                
                if filtros.get('feito') is not None:
                    conditions.append('feito = ?')
                    params.append(1 if filtros['feito'] else 0)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY data_criacao DESC'
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Erro ao buscar atividades: {str(e)}")
            return pd.DataFrame()
    
    def get_atividade_by_id(self, atividade_id):
        """Retorna uma atividade específica pelo ID"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM atividades WHERE id = ?
            ''', (atividade_id,))
            
            columns = [description[0] for description in cursor.description]
            atividade = cursor.fetchone()
            
            conn.close()
            
            if atividade:
                return dict(zip(columns, atividade))
            return None
        except Exception as e:
            st.error(f"Erro ao buscar atividade: {str(e)}")
            return None
    
    def get_estatisticas(self):
        """Retorna estatísticas das atividades"""
        try:
            conn = sqlite3.connect(self.db_name)
            
            estatisticas = {}
            
            # Total de atividades
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM atividades')
            estatisticas['total'] = cursor.fetchone()[0]
            
            # Atividades concluídas
            cursor.execute('SELECT COUNT(*) FROM atividades WHERE feito = 1')
            estatisticas['concluidas'] = cursor.fetchone()[0]
            
            # Atividades pendentes
            cursor.execute('SELECT COUNT(*) FROM atividades WHERE feito = 0')
            estatisticas['pendentes'] = cursor.fetchone()[0]
            
            # Percentual de conclusão
            if estatisticas['total'] > 0:
                estatisticas['percentual'] = (estatisticas['concluidas'] / estatisticas['total']) * 100
            else:
                estatisticas['percentual'] = 0
            
            # Atividades por status
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM atividades 
                GROUP BY status 
                ORDER BY count DESC
            ''')
            estatisticas['por_status'] = dict(cursor.fetchall())
            
            # Atividades por categoria
            cursor.execute('''
                SELECT categoria, COUNT(*) as count 
                FROM atividades 
                WHERE categoria IS NOT NULL
                GROUP BY categoria 
                ORDER BY count DESC
            ''')
            estatisticas['por_categoria'] = dict(cursor.fetchall())
            
            # Próximas entregas
            cursor.execute('''
                SELECT cliente, responsavel, atividade, data_entrega 
                FROM atividades 
                WHERE data_entrega >= date('now') AND feito = 0
                ORDER BY data_entrega ASC 
                LIMIT 5
            ''')
            estatisticas['proximas_entregas'] = cursor.fetchall()
            
            conn.close()
            return estatisticas
        except Exception as e:
            st.error(f"Erro ao buscar estatísticas: {str(e)}")
            return {}
    
    def get_categorias(self):
        """Retorna a lista de categorias"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('SELECT nome FROM categorias ORDER BY nome')
            categorias = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return ["Todos"] + categorias
        except Exception as e:
            st.error(f"Erro ao buscar categorias: {str(e)}")
            return ["Todos"]
    
    def get_responsaveis(self):
        """Retorna a lista de responsáveis únicos"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('SELECT DISTINCT responsavel FROM atividades ORDER BY responsavel')
            responsaveis = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return ["Todos"] + responsaveis
        except Exception as e:
            st.error(f"Erro ao buscar responsáveis: {str(e)}")
            return ["Todos"]
    
    def get_status_options(self):
        """Retorna as opções de status"""
        return ["Todos", "Pendente", "Em Andamento", "Concluído", "Cancelado"]

# --- BANCO DE DADOS PARA CT-E ---
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

# --- PROCESSADORES ---
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

# --- FUNÇÕES DO PROCESSADOR DE ARQUIVOS ---
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

def extrair_dados_xml(xml_file):
    """Extrai dados relevantes de um arquivo XML de NF-e modelo 55"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

        # Extrair número da NF-e
        inf_nfe = root.find('.//nfe:infNFe', ns)
        nfe_id = inf_nfe.get('Id')[3:] if inf_nfe is not None and inf_nfe.get('Id') else None

        # Extrair dados do destinatário
        dest = root.find('.//nfe:dest', ns)
        nome_dest = dest.find('nfe:xNome', ns).text if dest is not None and dest.find('nfe:xNome', ns) is not None else None
        uf_dest = dest.find('nfe:enderDest/nfe:UF', ns).text if dest is not None and dest.find('nfe:enderDest/nfe:UF', ns) is not None else None

        # Extrair valores de ICMS ST e DIFAL
        icms_st = root.find('.//nfe:ICMS/nfe:ICMS10/nfe:vICMSST', ns)
        icms_difal = root.find('.//nfe:ICMSUFDest/nfe:vICMSUFDest', ns)

        dados = {
            'Número NF-e': nfe_id,
            'Nome Destinatário': nome_dest,
            'UF Destinatário': uf_dest,
            'Valor ICMS ST': float(icms_st.text) if icms_st is not None else None,
            'Valor ICMS DIFAL': float(icms_difal.text) if icms_difal is not None else None
        }

        return dados
    except Exception as e:
        st.error(f"Erro ao processar arquivo {xml_file.name}: {str(e)}")
        return None

def processador_xml():
    st.title("📄 Processador de Arquivos XML (NF-e)")
    st.markdown("""
    <div class="card">
        Extrai informações de ICMS ST e DIFAL de arquivos XML de NF-e modelo 55. 
        Carregue os arquivos XML para extrair os dados relevantes.
    </div>
    """, unsafe_allow_html=True)

    # Upload de múltiplos arquivos XML
    uploaded_files = st.file_uploader(
        "Selecione os arquivos XML de NF-e", 
        type=['xml'], 
        accept_multiple_files=True,
        help="Selecione um ou mais arquivos XML de NF-e modelo 55"
    )

    if uploaded_files:
        dados_icms_st = []
        dados_icms_difal = []
        arquivos_com_erro = []

        for uploaded_file in uploaded_files:
            # Salva temporariamente o arquivo para processamento
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Processa o arquivo XML
            dados = extrair_dados_xml(uploaded_file.name)
            
            # Remove o arquivo temporário
            os.remove(uploaded_file.name)
            
            if dados is None:
                arquivos_com_erro.append(uploaded_file.name)
                continue
            
            # Adiciona aos conjuntos de dados apropriados
            if dados['Valor ICMS ST'] is not None:
                dados_icms_st.append(dados)
            if dados['Valor ICMS DIFAL'] is not None:
                dados_icms_difal.append(dados)

        # Mostra estatísticas
        st.success(f"""
        **Processamento concluído!**  
        ✔️ Arquivos processados: {len(uploaded_files)}  
        ✔️ Arquivos com ICMS ST: {len(dados_icms_st)}  
        ✔️ Arquivos com ICMS DIFAL: {len(dados_icms_difal)}  
        ❌ Arquivos com erro: {len(arquivos_com_erro)}
        """)

        if arquivos_com_erro:
            with st.expander("Ver arquivos com erro", expanded=False):
                st.write("Os seguintes arquivos não puderam ser processados corretamente:")
                for arquivo in arquivos_com_erro:
                    st.write(f"- {arquivo}")

        # Exibe tabelas com os dados extraídos
        if dados_icms_st:
            st.subheader("Tabela de ICMS ST")
            df_st = pd.DataFrame(dados_icms_st)
            st.dataframe(df_st)
            
            # Botão para download dos dados de ICMS ST
            csv_st = df_st.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Baixar dados de ICMS ST",
                data=csv_st,
                file_name="icms_st.csv",
                mime="text/csv"
            )

        if dados_icms_difal:
            st.subheader("Tabela de ICMS DIFAL")
            df_difal = pd.DataFrame(dados_icms_difal)
            st.dataframe(df_difal)
            
            # Botão para download dos dados de ICMS DIFAL
            csv_difal = df_difal.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Baixar dados de ICMS DIFAL",
                data=csv_difal,
                file_name="icms_difal.csv",
                mime="text/csv"
            )

# --- INTERFACE PARA ATIVIDADES ---
def mostrar_capa():
    """Exibe a capa profissional do sistema."""
    st.markdown("""
    <div class="cover-container">
        <img src="https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png" class="cover-logo">
        <h1 class="cover-title">Sistema de Gestão de Atividades</h1>
        <p class="cover-subtitle">Controle completo de atividades, CT-es e processamento de arquivos</p>
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

def cadastro_atividade(db):
    """Exibe o formulário para cadastro de novas atividades."""
    st.markdown('<div class="header">📝 Cadastro de Atividades</div>', unsafe_allow_html=True)
    
    with st.form("nova_atividade", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            cliente = st.text_input("Cliente*", placeholder="Nome do cliente")
            responsavel = st.text_input("Responsável*", placeholder="Nome do responsável")
            atividade = st.text_area("Atividade*", placeholder="Descrição detalhada da atividade", height=100)
        
        with col2:
            data_entrega = st.date_input("Data de Entrega", value=datetime.now())
            mes_referencia = st.selectbox("Mês de Referência", [
                f"{mes:02d}/{ano}" for ano in range(2023, 2026) for mes in range(1, 13)
            ])
            prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Urgente"])
            status = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluído", "Cancelado"])
            categoria = st.selectbox("Categoria", db.get_categorias()[1:])  # Exclui "Todos"
            observacoes = st.text_area("Observações", placeholder="Informações adicionais", height=80)
        
        st.markdown("<small>Campos marcados com * são obrigatórios</small>", unsafe_allow_html=True)
        
        if st.form_submit_button("Adicionar Atividade", use_container_width=True, type="primary"):
            if cliente and responsavel and atividade:
                atividade_data = {
                    'cliente': cliente,
                    'responsavel': responsavel,
                    'atividade': atividade,
                    'data_entrega': data_entrega.strftime('%Y-%m-%d'),
                    'mes_referencia': mes_referencia,
                    'prioridade': prioridade,
                    'status': status,
                    'categoria': categoria,
                    'observacoes': observacoes
                }
                
                atividade_id = db.insert_atividade(atividade_data)
                if atividade_id:
                    st.success(f"Atividade cadastrada com sucesso! ID: {atividade_id}")
                    st.rerun()
                else:
                    st.error("Erro ao cadastrar atividade")
            else:
                st.error("Preencha os campos obrigatórios!", icon="❌")

def lista_atividades(db):
    """Exibe a lista de atividades cadastradas com filtros."""
    st.markdown('<div class="header">📋 Lista de Atividades</div>', unsafe_allow_html=True)
    
    # Filtros
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        meses = sorted([f"{mes:02d}/{ano}" for ano in range(2023, 2026) for mes in range(1, 13)], reverse=True)
        mes_selecionado = st.selectbox("Mês de referência", ["Todos"] + meses, key="filtro_mes")
    
    with col2:
        responsaveis = db.get_responsaveis()
        responsavel_selecionado = st.selectbox("Responsável", responsaveis, key="filtro_responsavel")
    
    with col3:
        status_options = db.get_status_options()
        status_selecionado = st.selectbox("Status", status_options, key="filtro_status")
    
    with col4:
        categorias = db.get_categorias()
        categoria_selecionada = st.selectbox("Categoria", categorias, key="filtro_categoria")
    
    # Aplicar filtros
    filtros = {}
    if mes_selecionado != "Todos":
        filtros['mes_referencia'] = mes_selecionado
    if responsavel_selecionado != "Todos":
        filtros['responsavel'] = responsavel_selecionado
    if status_selecionado != "Todos":
        filtros['status'] = status_selecionado
    if categoria_selecionada != "Todos":
        filtros['categoria'] = categoria_selecionada
    
    # Buscar atividades
    atividades_df = db.get_all_atividades(filtros)
    
    if not atividades_df.empty:
        st.write(f"Total de atividades encontradas: {len(atividades_df)}")
        
        # Exibir tabela
        st.dataframe(
            atividades_df[['id', 'cliente', 'responsavel', 'atividade', 'data_entrega', 'status', 'prioridade']],
            use_container_width=True,
            hide_index=True
        )
        
        # Detalhes da atividade selecionada
        atividade_id = st.selectbox(
            "Selecione uma atividade para ver detalhes:",
            options=atividades_df['id'].tolist(),
            format_func=lambda x: f"ID {x} - {atividades_df[atividades_df['id'] == x]['cliente'].iloc[0]}"
        )
        
        if atividade_id:
            atividade = db.get_atividade_by_id(atividade_id)
            if atividade:
                with st.expander("Detalhes da Atividade", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Cliente:** {atividade['cliente']}")
                        st.write(f"**Responsável:** {atividade['responsavel']}")
                        st.write(f"**Atividade:** {atividade['atividade']}")
                        st.write(f"**Data de Entrega:** {atividade['data_entrega']}")
                        st.write(f"**Mês de Referência:** {atividade['mes_referencia']}")
                    
                    with col2:
                        st.write(f"**Status:** {atividade['status']}")
                        st.write(f"**Prioridade:** {atividade['prioridade']}")
                        st.write(f"**Categoria:** {atividade['categoria']}")
                        st.write(f"**Concluído:** {'Sim' if atividade['feito'] else 'Não'}")
                        if atividade['observacoes']:
                            st.write(f"**Observações:** {atividade['observacoes']}")
                    
                    # Ações
                    col_act1, col_act2, col_act3 = st.columns(3)
                    
                    with col_act1:
                        novo_status = st.selectbox(
                            "Alterar Status",
                            options=db.get_status_options()[1:],  # Exclui "Todos"
                            key=f"status_{atividade_id}"
                        )
                        if st.button("Atualizar Status", key=f"upd_status_{atividade_id}"):
                            if db.update_atividade(atividade_id, 'status', novo_status):
                                st.success("Status atualizado com sucesso!")
                                st.rerun()
                    
                    with col_act2:
                        concluido = st.checkbox("Marcar como concluído", value=bool(atividade['feito']), key=f"feito_{atividade_id}")
                        if st.button("Atualizar Conclusão", key=f"upd_feito_{atividade_id}"):
                            if db.update_atividade(atividade_id, 'feito', concluido):
                                st.success("Status de conclusão atualizado!")
                                st.rerun()
                    
                    with col_act3:
                        if st.button("Excluir Atividade", type="secondary", key=f"del_{atividade_id}"):
                            if db.delete_atividade(atividade_id):
                                st.success("Atividade excluída com sucesso!")
                                st.rerun()
    else:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.")

def mostrar_indicadores(db):
    """Exibe os indicadores de desempenho."""
    st.markdown('<div class="header">📊 Indicadores de Desempenho</div>', unsafe_allow_html=True)
    
    estatisticas = db.get_estatisticas()
    
    if estatisticas:
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total de Atividades", estatisticas['total'])
        col2.metric("Atividades Concluídas", estatisticas['concluidas'])
        col3.metric("Atividades Pendentes", estatisticas['pendentes'])
        col4.metric("Taxa de Conclusão", f"{estatisticas['percentual']:.1f}%")
        
        # Gráficos
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Distribuição por Status")
            if estatisticas['por_status']:
                fig_status = px.pie(
                    values=list(estatisticas['por_status'].values()),
                    names=list(estatisticas['por_status'].keys()),
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig_status, use_container_width=True)
        
        with col_chart2:
            st.subheader("Distribuição por Categoria")
            if estatisticas['por_categoria']:
                fig_cat = px.bar(
                    x=list(estatisticas['por_categoria'].keys()),
                    y=list(estatisticas['por_categoria'].values()),
                    labels={'x': 'Categoria', 'y': 'Quantidade'},
                    color_discrete_sequence=['#3498db']
                )
                st.plotly_chart(fig_cat, use_container_width=True)
        
        # Próximas entregas
        st.subheader("📅 Próximas Entregas")
        if estatisticas['proximas_entregas']:
            for entrega in estatisticas['proximas_entregas']:
                st.info(f"**{entrega[0]}** - {entrega[2]} | 📅 {entrega[3]} | 👤 {entrega[1]}")
        else:
            st.info("Nenhuma entrega próxima encontrada.")
    else:
        st.warning("Não há dados suficientes para exibir indicadores.")

# --- INTERFACE PARA CT-E ---
def processador_cte():
    """Interface para o sistema de CT-e"""
    # Inicializar componentes
    db = CTeDatabase()
    processor = CTeProcessor()
    
    st.title("📄 Sistema de Armazenamento de CT-e")
    st.markdown("### Armazene, consulte e exporte seus CT-es para Power BI")
    
    # Sidebar
    st.sidebar.header("Estatísticas")
    total_files = db.get_file_count()
    st.sidebar.metric("Total de CT-es Armazenados", total_files)
    
    # Navegação por abas
    tab1, tab2, tab3, tab4 = st.tabs(["Upload", "Consultar CT-es", "Visualizar CT-e", "Dados para Power BI"])
    
    with tab1:
        st.header("Upload de CT-es")
        upload_option = st.radio("Selecione o tipo de upload:", 
                                ["Upload Individual", "Upload em Lote", "Upload por Diretório"])
        
        if upload_option == "Upload Individual":
            uploaded_file = st.file_uploader("Selecione um arquivo XML de CT-e", type=['xml'])
            if uploaded_file and st.button("🔄 Armazenar CT-e"):
                success, message = processor.process_uploaded_file(uploaded_file, db)
                st.success(message) if success else st.error(message)
        
        elif upload_option == "Upload em Lote":
            uploaded_files = st.file_uploader("Selecione múltiplos arquivos XML de CT-e", type=['xml'], accept_multiple_files=True)
            if uploaded_files and st.button("🔄 Armazenar Todos"):
                for uploaded_file in uploaded_files:
                    success, message = processor.process_uploaded_file(uploaded_file, db)
        
        else:
            directory_path = st.text_input("Caminho do diretório com CT-es")
            if directory_path and st.button("📁 Processar Diretório"):
                results = processor.process_directory(directory_path, db)
                st.write(f"✅ Sucessos: {results['success']}")
                st.write(f"🔄 Duplicados: {results['duplicates']}")
                st.write(f"❌ Erros: {results['errors']}")
    
    with tab2:
        st.header("Consultar CT-es Armazenados")
        files = db.get_all_files()
        if files:
            for file in files:
                with st.expander(f"📄 {file[1]}"):
                    st.write(f"**ID:** {file[0]}")
                    st.write(f"**Tamanho:** {file[2]} bytes")
                    st.write(f"**Data Upload:** {file[3]}")
                    if st.button("👁️ Visualizar", key=f"view_{file[0]}"):
                        st.session_state.selected_xml = file[0]
                        st.rerun()
        else:
            st.info("Nenhum arquivo armazenado ainda.")
    
    with tab3:
        st.header("Visualizar Conteúdo do CT-e")
        if st.session_state.selected_xml:
            xml_content = db.get_xml_content(st.session_state.selected_xml)
            if xml_content:
                st.text_area("Conteúdo do CT-e", xml_content, height=500)
            else:
                st.error("Conteúdo do CT-e não encontrado.")
        else:
            st.info("Selecione um CT-e na aba 'Consultar CT-es' para visualizar seu conteúdo.")
    
    with tab4:
        st.header("Dados para Power BI")
        start_date = st.date_input("Data inicial", value=date.today().replace(day=1))
        end_date = st.date_input("Data final", value=date.today())
        
        if st.button("Carregar Dados CT-e"):
            df = db.get_cte_data_by_date_range(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            if not df.empty:
                st.dataframe(df)
                # Opções de exportação aqui...

# --- CSS E CONFIGURAÇÃO DE ESTILO ---
def load_css():
    st.markdown("""
    <style>
        .cover-container {
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ed 100%);
            padding: 3rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            text-align: center;
        }
        .cover-title {
            font-size: 2.8rem;
            font-weight: 800;
            margin-bottom: 1rem;
            background: linear-gradient(90deg, #2c3e50, #3498db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header {
            font-size: 1.8rem;
            font-weight: 700;
            margin: 1.5rem 0 1rem 0;
            padding-left: 10px;
            border-left: 5px solid #2c3e50;
        }
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            padding: 1.8rem;
            margin-bottom: 1.8rem;
        }
    </style>
    """, unsafe_allow_html=True)

# --- APLICAÇÃO PRINCIPAL ---
def main():
    """Função principal que gerencia o fluxo da aplicação."""
    load_css()
    
    # Inicializar bancos de dados
    atividades_db = AtividadesDatabase()
    atividades_db.init_database()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_section()
    else:
        mostrar_capa()
        
        # Menu de navegação
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📋 Atividades", 
            "📝 Nova Atividade", 
            "📊 Indicadores", 
            "📄 Processador TXT",
            "📑 Processador XML",
            "🚚 Sistema CT-e"
        ])
        
        with tab1:
            lista_atividades(atividades_db)
        
        with tab2:
            cadastro_atividade(atividades_db)
        
        with tab3:
            mostrar_indicadores(atividades_db)
        
        with tab4:
            processador_txt()
        
        with tab5:
            processador_xml()
        
        with tab6:
            processador_cte()
        
        # Sidebar
        with st.sidebar:
            st.header("Estatísticas")
            estatisticas = atividades_db.get_estatisticas()
            if estatisticas:
                st.metric("Total de Atividades", estatisticas['total'])
                st.metric("Taxa de Conclusão", f"{estatisticas['percentual']:.1f}%")
            
            if st.button("🚪 Sair", use_container_width=True):
                st.session_state.logged_in = False
                st.rerun()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {str(e)}")
        st.code(traceback.format_exc())