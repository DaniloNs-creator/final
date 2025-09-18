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