import streamlit as st
import sqlite3
import os
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, date
from pathlib import Path
import time
import pandas as pd
import xml.dom.minidom
import base64
from io import BytesIO
import traceback
from flask import Flask, jsonify, request
import threading
import requests
from waitress import serve
import json

# Configuração da aplicação Flask
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Configuração da página Streamlit
st.set_page_config(
    page_title="Sistema de CT-e com API",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização do estado da sessão
if 'selected_xml' not in st.session_state:
    st.session_state.selected_xml = None

class CTeDatabase:
    def __init__(self, db_name="cte_database.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com as tabelas necessárias para CT-e"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Verifica se a tabela existe e se tem a coluna upload_date
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cte_structured_data'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Verifica se a coluna upload_date existe na tabela
                cursor.execute("PRAGMA table_info(cte_structured_data)")
                columns = [column[1] for column in cursor.fetchall()]
                if 'upload_date' in columns:
                    # Remove a coluna upload_date se existir (ela deve estar apenas em xml_files)
                    cursor.execute('ALTER TABLE cte_structured_data DROP COLUMN upload_date')
            
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS xml_content (
                    id INTEGER PRIMARY KEY,
                    xml_content TEXT,
                    FOREIGN KEY (id) REFERENCES xml_files (id)
                )
            ''')
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
            if file_id == 0:
                cursor.execute('SELECT id FROM xml_files WHERE filename = ?', (filename,))
                result = cursor.fetchone()
                file_id = result[0] if result else None
            if file_id and xml_content:
                cursor.execute('''
                    INSERT OR REPLACE INTO xml_content (id, xml_content)
                    VALUES (?, ?)
                ''', (file_id, xml_content))
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
            namespaces = {
                'cte': 'http://www.portalfiscal.inf.br/cte'
            }
            def find_text(element, path):
                for prefix, uri in namespaces.items():
                    full_path = path.replace('cte:', f'{{{uri}}}')
                    found = element.find(full_path)
                    if found is not None and found.text:
                        return found.text
                found = element.find(path.replace('cte:', ''))
                if found is not None and found.text:
                    return found.text
                return None
            nCT = find_text(root, './/cte:nCT')
            dhEmi = find_text(root, './/cte:dhEmi')
            cMunIni = find_text(root, './/cte:cMunIni')
            UFIni = find_text(root, './/cte:UFIni')
            cMunFim = find_text(root, './/cte:cMunFim')
            UFFim = find_text(root, './/cte:UFFim')
            emit_xNome = find_text(root, './/cte:emit/cte:xNome')
            vTPrest = find_text(root, './/cte:vTPrest')
            rem_xNome = find_text(root, './/cte:rem/cte:xNome')
            infNFe_chave = find_text(root, './/cte:infNFe/cte:chave')
            if dhEmi:
                dhEmi = dhEmi[:10]
            try:
                vTPrest = float(vTPrest) if vTPrest else None
            except (ValueError, TypeError):
                vTPrest = None
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

    def get_all_files(self):
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
        try:
            conn = sqlite3.connect(self.db_name)
            query = '''
                SELECT 
                    csd.id,
                    csd.nCT,
                    csd.dhEmi,
                    csd.cMunIni,
                    csd.UFIni,
                    csd.cMunFim,
                    csd.UFFim,
                    csd.emit_xNome,
                    csd.vTPrest,
                    csd.rem_xNome,
                    csd.infNFe_chave,
                    xf.upload_date
                FROM cte_structured_data csd
                JOIN xml_files xf ON csd.xml_id = xf.id
                ORDER BY csd.dhEmi DESC
            '''
            df = pd.read_sql_query(query, conn)
            conn.close()
            # Extraia apenas o número da NF-e (9 dígitos, posições 26 a 34 da chave de 44 caracteres)
            if 'infNFe_chave' in df.columns:
                df['numero_nfe'] = df['infNFe_chave'].astype(str).str.replace(r'\D', '', regex=True).str[24:33]
            return df
        except Exception as e:
            st.error(f"Erro ao carregar dados de CT-e: {str(e)}")
            return pd.DataFrame()

    def get_cte_data_by_date_range(self, start_date, end_date):
        try:
            conn = sqlite3.connect(self.db_name)
            query = '''
                SELECT 
                    csd.id,
                    csd.nCT,
                    csd.dhEmi,
                    csd.cMunIni,
                    csd.UFIni,
                    csd.cMunFim,
                    csd.UFFim,
                    csd.emit_xNome,
                    csd.vTPrest,
                    csd.rem_xNome,
                    csd.infNFe_chave,
                    xf.upload_date
                FROM cte_structured_data csd
                JOIN xml_files xf ON csd.xml_id = xf.id
                WHERE date(csd.dhEmi) BETWEEN date(?) AND date(?)
                ORDER BY csd.dhEmi DESC
            '''
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
            conn.close()
            # Deixe a coluna infNFe_chave com apenas os 9 dígitos do número da NFe (posições 26 a 34, índice 25:34)
            if 'infNFe_chave' in df.columns:
                df['infNFe_chave'] = df['infNFe_chave'].astype(str).str.replace(r'\D', '', regex=True).str[25:34]
            return df
        except Exception as e:
            st.error(f"Erro ao carregar dados por intervalo: {str(e)}")
            return pd.DataFrame()

    def get_cte_data_api(self, limit=1000, offset=0, filters=None):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            query = '''
                SELECT 
                    csd.id,
                    csd.nCT,
                    csd.dhEmi,
                    csd.cMunIni,
                    csd.UFIni,
                    csd.cMunFim,
                    csd.UFFim,
                    csd.emit_xNome,
                    csd.vTPrest,
                    csd.rem_xNome,
                    csd.infNFe_chave,
                    xf.upload_date
                FROM cte_structured_data csd
                JOIN xml_files xf ON csd.xml_id = xf.id
                WHERE 1=1
            '''
            params = []
            if filters:
                if 'start_date' in filters and filters['start_date']:
                    query += " AND date(csd.dhEmi) >= date(?)"
                    params.append(filters['start_date'])
                if 'end_date' in filters and filters['end_date']:
                    query += " AND date(csd.dhEmi) <= date(?)"
                    params.append(filters['end_date'])
                if 'emitente' in filters and filters['emitente']:
                    query += " AND csd.emit_xNome LIKE ?"
                    params.append(f'%{filters["emitente"]}%')
            query += " ORDER BY csd.dhEmi DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor.execute(query, params)
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Contagem total com filtros
            count_query = '''
                SELECT COUNT(*) 
                FROM cte_structured_data csd
                JOIN xml_files xf ON csd.xml_id = xf.id
                WHERE 1=1
            '''
            count_params = []
            if filters:
                if 'start_date' in filters and filters['start_date']:
                    count_query += " AND date(csd.dhEmi) >= date(?)"
                    count_params.append(filters['start_date'])
                if 'end_date' in filters and filters['end_date']:
                    count_query += " AND date(csd.dhEmi) <= date(?)"
                    count_params.append(filters['end_date'])
                if 'emitente' in filters and filters['emitente']:
                    count_query += " AND csd.emit_xNome LIKE ?"
                    count_params.append(f'%{filters["emitente"]}%')
            
            cursor.execute(count_query, count_params)
            total_count = cursor.fetchone()[0]
            conn.close()
            
            return {
                "data": results,
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            return {"error": str(e)}

class CTeProcessor:
    def __init__(self, storage_path="storage/cte_files"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def calculate_hash(self, file_content):
        return hashlib.md5(file_content).hexdigest()
    
    def save_cte_file(self, file_content, filename):
        try:
            file_path = self.storage_path / filename
            if file_path.exists():
                existing_hash = self.calculate_hash(file_path.read_bytes())
                new_hash = self.calculate_hash(file_content)
                if existing_hash == new_hash:
                    return file_path, False
            with open(file_path, 'wb') as f:
                f.write(file_content)
            return file_path, True
        except Exception as e:
            st.error(f"Erro ao salvar arquivo: {str(e)}")
            return None, False
    
    def process_uploaded_file(self, uploaded_file, db):
        try:
            file_content = uploaded_file.getvalue()
            filename = uploaded_file.name
            if not filename.lower().endswith('.xml'):
                return False, "Arquivo não é XML"
            try:
                content_str = file_content.decode('utf-8', errors='ignore')
                if 'CTe' not in content_str and 'conhecimento' not in content_str.lower():
                    return False, "Arquivo não parece ser um CT-e"
            except:
                return False, "Erro ao verificar tipo do arquivo"
            content_hash = self.calculate_hash(file_content)
            file_path, is_new = self.save_cte_file(file_content, filename)
            if not is_new:
                return False, "Arquivo duplicado"
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
            xml_files = list(directory_path.glob("*.xml")) + list(directory_path.glob("*.XML"))
            for xml_file in xml_files:
                try:
                    file_content = xml_file.read_bytes()
                    filename = xml_file.name
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

# API Flask para integração com Power BI
@app.route('/api/cte', methods=['GET'])
def get_cte_data():
    try:
        limit = int(request.args.get('limit', 1000))
        offset = int(request.args.get('offset', 0))
        filters = {}
        if 'start_date' in request.args:
            filters['start_date'] = request.args.get('start_date')
        if 'end_date' in request.args:
            filters['end_date'] = request.args.get('end_date')
        if 'emitente' in request.args:
            filters['emitente'] = request.args.get('emitente')
        db = CTeDatabase()
        result = db.get_cte_data_api(limit, offset, filters)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cte/count', methods=['GET'])
def get_cte_count():
    try:
        db = CTeDatabase()
        count = db.get_file_count()
        return jsonify({"total_count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cte/fields', methods=['GET'])
def get_cte_fields():
    fields = [
        {"name": "id", "type": "integer", "description": "ID único do registro"},
        {"name": "nCT", "type": "string", "description": "Número do Conhecimento de Transporte"},
        {"name": "dhEmi", "type": "date", "description": "Data e hora de emissão"},
        {"name": "cMunIni", "type": "string", "description": "Código do município de início"},
        {"name": "UFIni", "type": "string", "description": "UF de início"},
        {"name": "cMunFim", "type": "string", "description": "Código do município de fim"},
        {"name": "UFFim", "type": "string", "description": "UF de fim"},
        {"name": "emit_xNome", "type": "string", "description": "Nome do emitente"},
        {"name": "vTPrest", "type": "number", "description": "Valor total da prestação"},
        {"name": "rem_xNome", "type": "string", "description": "Nome do remetente"},
        {"name": "infNFe_chave", "type": "string", "description": "Chave da NFe associada"},
        {"name": "upload_date", "type": "datetime", "description": "Data de upload do arquivo"}
    ]
    return jsonify(fields)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@st.cache_resource
def init_database():
    return CTeDatabase()

@st.cache_resource
def init_processor():
    return CTeProcessor()

def start_flask_app():
    try:
        serve(app, host='0.0.0.0', port=5000)
    except Exception as e:
        st.error(f"Erro ao iniciar servidor Flask: {e}")

def main():
    db = init_database()
    processor = init_processor()
    if 'flask_started' not in st.session_state:
        try:
            flask_thread = threading.Thread(target=start_flask_app, daemon=True)
            flask_thread.start()
            st.session_state.flask_started = True
            st.success("API Flask iniciada na porta 5000")
        except Exception as e:
            st.error(f"Erro ao iniciar API: {e}")

    st.title("📄 Sistema de Armazenamento de CT-e com API")
    st.markdown("### Armazene CT-es e acesse via API para integração com Power BI")

    st.sidebar.header("Estatísticas")
    total_files = db.get_file_count()
    st.sidebar.metric("Total de CT-es Armazenados", total_files)

    st.sidebar.header("API para Power BI")
    st.sidebar.info("""
    **Endpoints disponíveis:**
    - `GET /api/cte` - Dados dos CT-es
    - `GET /api/cte/count` - Contagem total
    - `GET /api/cte/fields` - Metadados dos campos
    - `GET /api/health` - Status da API

    **Exemplo de URL para Power BI:**
    ```
    http://localhost:5000/api/cte?limit=1000
    ```
    """)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Upload", "Consultar CT-es", "Visualizar CT-e", "Dados para Power BI", "API Info"])

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
                            success, message = processor.process_uploaded_file(uploaded_file, db)
                            if success:
                                st.success(message)
                                st.balloons()
                            else:
                                st.error(message)
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
                        success, message = processor.process_uploaded_file(uploaded_file, db)
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
        else:
            st.subheader("Para grandes volumes (50k+ CT-es)")
            st.info("Para processar 50 mil CT-es, recomendamos usar a opção de diretório")
            directory_path = st.text_input(
                "Caminho do diretório com CT-es",
                placeholder="Ex: C:/cte_files/ ou /home/usuario/cte_files/"
            )
            if st.button("📁 Processar Diretório", type="secondary"):
                if directory_path and os.path.exists(directory_path):
                    with st.spinner("Processando diretório... Isso pode demorar para muitos arquivos"):
                        results = processor.process_directory(directory_path, db)
                        st.success(f"Processamento do diretório concluído!")
                        st.write(f"✅ Sucessos: {results['success']}")
                        st.write(f"🔄 Duplicados: {results['duplicates']}")
                        st.write(f"❌ Erros: {results['errors']}")
                        with st.expander("Ver detalhes do processamento"):
                            for msg in results['messages'][-10:]:
                                st.write(msg)
                        time.sleep(2)
                        st.rerun()
                else:
                    st.error("Diretório não encontrado ou caminho inválido")

    with tab2:
        st.header("Consultar CT-es Armazenados")
        files = db.get_all_files()
        if files:
            st.write(f"Total de arquivos: {len(files)}")
            col1, col2, col3 = st.columns(3)
            with col1:
                items_per_page = st.selectbox("Itens por página", [10, 25, 50, 100], key="items_page")
            with col2:
                search_term = st.text_input("Buscar por nome", key="search_term")
            with col3:
                sort_order = st.selectbox("Ordenar por", ["Data Upload (Mais Recente)", "Data Upload (Mais Antigo)", "Nome (A-Z)", "Nome (Z-A)"])
            if search_term:
                filtered_files = db.search_files(search_term)
            else:
                filtered_files = files
            if sort_order == "Data Upload (Mais Recente)":
                filtered_files = sorted(filtered_files, key=lambda x: x[3], reverse=True)
            elif sort_order == "Data Upload (Mais Antigo)":
                filtered_files = sorted(filtered_files, key=lambda x: x[3])
            elif sort_order == "Nome (A-Z)":
                filtered_files = sorted(filtered_files, key=lambda x: x[1])
            elif sort_order == "Nome (Z-A)":
                filtered_files = sorted(filtered_files, key=lambda x: x[1], reverse=True)
            total_pages = max(1, (len(filtered_files) + items_per_page - 1) // items_per_page)
            page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, key="page_num")
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_files))
            st.write(f"Mostrando {start_idx + 1}-{end_idx} de {len(filtered_files)} arquivos")
            for file in filtered_files[start_idx:end_idx]:
                file_id, filename, file_size, upload_date = file
                with st.expander(f"📄 {filename}"):
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    col1.write(f"**ID:** {file_id}")
                    col2.write(f"**Tamanho:** {file_size} bytes")
                    col3.write(f"**Data Upload:** {upload_date}")
                    if col4.button("👁️ Visualizar", key=f"view_{file_id}"):
                        st.session_state.selected_xml = file_id
                        st.rerun()
            if st.button("📊 Exportar Lista para Excel"):
                df = pd.DataFrame(filtered_files, columns=['ID', 'Nome do Arquivo', 'Tamanho (bytes)', 'Data de Upload'])
                df['Data de Upload'] = pd.to_datetime(df['Data de Upload']).dt.strftime('%Y-%m-%d %H:%M:%S')
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='CT-es', index=False)
                output.seek(0)
                b64 = base64.b64encode(output.read()).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="lista_ctes.xlsx">📥 Baixar Lista de CT-es</a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("Nenhum arquivo armazenado ainda.")

    with tab3:
        st.header("Visualizar Conteúdo do CT-e")
        if st.session_state.selected_xml:
            xml_content = db.get_xml_content(st.session_state.selected_xml)
            if xml_content:
                try:
                    parsed_xml = xml.dom.minidom.parseString(xml_content)
                    pretty_xml = parsed_xml.toprettyxml()
                    st.text_area("Conteúdo do CT-e (formatado)", pretty_xml, height=500)
                    col1, col2, col3 = st.columns(3)
                    b64_xml = base64.b64encode(xml_content.encode()).decode()
                    href = f'<a href="data:application/xml;base64,{b64_xml}" download="cte_{st.session_state.selected_xml}.xml">📥 Baixar CT-e</a>'
                    col1.markdown(href, unsafe_allow_html=True)
                    if col2.button("📋 Copiar Conteúdo"):
                        st.code(xml_content)
                        st.success("Conteúdo copiado para a área de transferência!")
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

    with tab4:
        st.header("Dados Estruturados para Power BI")
        st.info("""
        Esta seção fornece os dados estruturados extraídos dos CT-es para uso no Power BI.
        Os dados incluem informações específicas de Conhecimento de Transporte Eletrônico.
        """)
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Data inicial", value=date.today().replace(day=1))
        with col2:
            end_date = st.date_input("Data final", value=date.today())
        if st.button("Carregar Dados CT-e", type="primary"):
            with st.spinner("Carregando dados de CT-e..."):
                df = db.get_cte_data_by_date_range(
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
                if not df.empty:
                    st.success(f"Dados carregados: {len(df)} registros encontrados")
                    st.dataframe(df)
                    st.subheader("📈 Estatísticas de CT-e")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total de CT-es", len(df))
                    if 'vTPrest' in df.columns:
                        col2.metric("Valor Total", f"R$ {df['vTPrest'].sum():,.2f}")
                        col3.metric("Valor Médio", f"R$ {df['vTPrest'].mean():,.2f}" if len(df) > 0 else "R$ 0,00")
                    else:
                        col2.metric("Valor Total", "N/A")
                        col3.metric("Valor Médio", "N/A")
                    st.subheader("📤 Exportar Dados")
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name='Dados_CTe', index=False)
                    output.seek(0)
                    b64 = base64.b64encode(output.read()).decode()
                    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="dados_cte_powerbi.xlsx">📥 Baixar para Excel</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    csv = df.to_csv(index=False)
                    b64_csv = base64.b64encode(csv.encode()).decode()
                    href_csv = f'<a href="data:file/csv;base64,{b64_csv}" download="dados_cte_powerbi.csv">📥 Baixar para CSV</a>'
                    st.markdown(href_csv, unsafe_allow_html=True)
                else:
                    st.warning("Nenhum dado de CT-e encontrado para o período selecionado.")

    with tab5:
        st.header("Informações da API para Power BI")
        st.info("""
        ## 📊 Como conectar o Power BI à API

        Agora seu sistema possui uma API RESTful que permite ao Power BI conectar-se diretamente
        aos dados dos CT-es sem necessidade de drivers ODBC complexos.
        """)
        st.subheader("📋 Endpoints da API")
        col1, col2 = st.columns(2)
        with col1:
            st.code("""
# Obter todos os CT-es (com paginação)
GET /api/cte?limit=1000&offset=0

# Filtrar por data
GET /api/cte?start_date=2024-01-01&end_date=2024-12-31

# Filtrar por emitente
GET /api/cte?emitente=NOME_DA_EMPRESA

# Obter contagem total
GET /api/cte/count

# Obter metadados dos campos
GET /api/cte/fields

# Verificar status da API
GET /api/health
            """, language="http")
        with col2:
            st.subheader("🔧 Configuração no Power BI")
            st.markdown("""
            1. No Power BI, selecione **"Obter Dados"** > **"Web"**
            2. Cole a URL: `http://localhost:5000/api/cte`
            3. Selecione **"OK"**
            4. Os dados serão carregados automaticamente

            **Vantagens:**
            - ✅ Conexão direta sem drivers
            - ✅ Filtros via parâmetros de URL
            - ✅ Atualização em tempo real
            - ✅ Suporte a paginação para grandes volumes
            - ✅ Metadados estruturados
            """)
        st.subheader("🧪 Testar Conexão da API")
        if st.button("Testar API", type="primary"):
            try:
                response = requests.get("http://localhost:5000/api/health")
                if response.status_code == 200:
                    st.success("✅ API está funcionando corretamente!")
                    st.json(response.json())
                else:
                    st.error(f"❌ API retornou erro: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Erro ao conectar na API: {e}")
        st.subheader("💡 Exemplo de Consulta no Power BI")
        st.code("""
let
    Fonte = Json.Document(Web.Contents("http://localhost:5000/api/cte", [
        Query = [
            limit = "10000",
            start_date = "2024-01-01",
            end_date = "2024-12-31"
        ]
    ])),
    data = Fonte[data],
    #"Convertido em Tabela" = Table.FromList(data, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Expandido" = Table.ExpandRecordColumn(#"Convertido em Tabela", "Column1", 
        {"id", "nCT", "dhEmi", "cMunIni", "UFIni", "cMunFim", "UFFim", 
         "emit_xNome", "vTPrest", "rem_xNome", "infNFe_chave", "upload_date"})
in
    #"Expandido"
        """, language="powerquery")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {str(e)}")
        st.code(traceback.format_exc())