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

# Configuração da página
st.set_page_config(
    page_title="Sistema de CT-e",
    page_icon="📄",
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

class CTeDatabase:
    def _init_(self, db_name="cte_database.db"):
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
    def _init_(self, storage_path="storage/cte_files"):
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
            xml_files = list(directory_path.glob(".xml")) + list(directory_path.glob(".XML"))
            
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
def init_database():
    return CTeDatabase()

@st.cache_resource
def init_processor():
    return CTeProcessor()

def main():
    # Inicializar componentes
    db = init_database()
    processor = init_processor()
    
    st.title("📄 Sistema de Armazenamento de CT-e")
    st.markdown("### Armazene, consulte e exporte seus CT-es para Power BI")
    
    # Sidebar
    st.sidebar.header("Estatísticas")
    total_files = db.get_file_count()
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
                            success, message = processor.process_uploaded_file(uploaded_file, db)
                            
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
                        results = processor.process_directory(directory_path, db)
                        
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
        
        files = db.get_all_files()
        
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
                filtered_files = db.search_files(search_term)
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
                    
                    col1.write(f"*ID:* {file_id}")
                    col2.write(f"*Tamanho:* {file_size} bytes")
                    col3.write(f"*Data Upload:* {upload_date}")
                    
                    # Botão para visualizar
                    if col4.button("👁 Visualizar", key=f"view_{file_id}"):
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
            xml_content = db.get_xml_content(st.session_state.selected_xml)
            
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
                    if col3.button("↩ Voltar para Lista"):
                        st.session_state.selected_xml = None
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Erro ao formatar CT-e: {e}")
                    st.text_area("Conteúdo do CT-e (original)", xml_content, height=500)
            else:
                st.error("Conteúdo do CT-e não encontrado.")
                if st.button("↩ Voltar para Lista"):
                    st.session_state.selected_xml = None
                    st.rerun()
        else:
            st.info("Selecione um CT-e na aba 'Consultar CT-es' para visualizar seu conteúdo.")
    
    # Tab 4 - Dados para Power BI
    with tab4:
        st.header("Dados Estruturados para Power BI")
        
        st.info("""
        Esta seção fornece os dados estruturados extraídos dos CT-es para uso no Power BI.
        Os dados incluem informações específicas de Conhecimento de Transporte Eletrônico.
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
                df = db.get_cte_data_by_date_range(
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
                        
                        1. *Método 1: Arquivo Excel/CSV*
                           - Baixe os dados usando os botões acima
                           - No Power BI, selecione "Obter Dados" > "Arquivo" > "Excel" ou "Texto/CSV"
                           - Selecione o arquivo baixado
                        
                        2. *Método 2: Conexão direta com SQLite (Recomendado)*
                           - No Power BI, selecione "Obter Dados" > "Mais..." > "Banco de dados" > "SQLite"
                           - No campo "Banco de dados", digite o caminho completo para o arquivo cte_database.db
                           - Selecione a tabela cte_structured_data
                        
                        3. *Método 3: Conexão ODBC*
                           - Configure um driver ODBC para SQLite
                           - No Power BI, selecione "Obter Dados" > "ODBC"
                           - Selecione a fonte de dados configurada
                        
                        *Vantagem dos métodos 2 e 3:* Atualizações em tempo real sem precisar reimportar arquivos.
                        """)
                else:
                    st.warning("Nenhum dado de CT-e encontrado para o período selecionado.")
    
    # Footer
    st.sidebar.divider()
    st.sidebar.info("""
    *💡 Dicas:*
    - Para 50k CT-es, use a opção de diretório
    - Conecte o Power BI diretamente ao banco SQLite
    - Dados armazenados permanentemente
    """)

# Executar a aplicação
if _name_ == "_main_":
    try:
        main()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {str(e)}")
        st.code(traceback.format_exc())
