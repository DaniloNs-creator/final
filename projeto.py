import streamlit as st
import sqlite3
import os
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import time

# Configuração da página
st.set_page_config(
    page_title="Sistema de Armazenamento de XML",
    page_icon="📄",
    layout="wide"
)

class XMLDatabase:
    def __init__(self, db_name="xml_database.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
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
                processed BOOLEAN DEFAULT FALSE,
                metadata TEXT
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
        
        conn.commit()
        conn.close()
    
    def insert_xml(self, filename, file_path, file_size, content_hash, xml_content=None):
        """Insere um novo XML no banco de dados"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Extrai metadados básicos do XML
            metadata = self.extract_basic_metadata(xml_content)
            
            cursor.execute('''
                INSERT INTO xml_files 
                (filename, file_path, file_size, content_hash, upload_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (filename, file_path, file_size, content_hash, datetime.now(), metadata))
            
            file_id = cursor.lastrowid
            
            if xml_content:
                cursor.execute('''
                    INSERT INTO xml_content (id, xml_content)
                    VALUES (?, ?)
                ''', (file_id, xml_content))
            
            conn.commit()
            return file_id
            
        except sqlite3.IntegrityError:
            print(f"Arquivo {filename} já existe no banco de dados")
            return None
        finally:
            conn.close()
    
    def extract_basic_metadata(self, xml_content):
        """Extrai metadados básicos do XML"""
        if not xml_content:
            return "{}"
        
        try:
            root = ET.fromstring(xml_content)
            metadata = {
                'root_tag': root.tag,
                'attributes': dict(root.attrib),
                'child_count': len(list(root))
            }
            return str(metadata)
        except:
            return "{}"
    
    def get_all_files(self):
        """Retorna todos os arquivos do banco de dados"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, filename, file_size, upload_date FROM xml_files ORDER BY upload_date DESC')
        files = cursor.fetchall()
        
        conn.close()
        return files
    
    def get_file_count(self):
        """Retorna o número total de arquivos"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM xml_files')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def search_files(self, search_term):
        """Busca arquivos por nome"""
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

class XMLProcessor:
    def __init__(self, storage_path="storage/xml_files"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def calculate_hash(self, file_content):
        """Calcula hash do conteúdo do arquivo para verificar duplicatas"""
        return hashlib.md5(file_content).hexdigest()
    
    def save_xml_file(self, file_content, filename):
        """Salva o arquivo XML no sistema de arquivos"""
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
    
    def process_uploaded_file(self, uploaded_file, db):
        """Processa um arquivo XML enviado"""
        file_content = uploaded_file.getvalue()
        filename = uploaded_file.name
        
        # Verifica se é um XML
        if not filename.lower().endswith('.xml'):
            return False, "Arquivo não é XML"
        
        # Calcula hash
        content_hash = self.calculate_hash(file_content)
        
        # Salva arquivo
        file_path, is_new = self.save_xml_file(file_content, filename)
        
        if not is_new:
            return False, "Arquivo duplicado"
        
        # Insere no banco de dados
        file_size = len(file_content)
        file_id = db.insert_xml(
            filename=filename,
            file_path=str(file_path),
            file_size=file_size,
            content_hash=content_hash,
            xml_content=file_content.decode('utf-8', errors='ignore')
        )
        
        if file_id:
            return True, f"Arquivo {filename} armazenado com sucesso! ID: {file_id}"
        else:
            return False, "Erro ao armazenar no banco de dados"
    
    def process_directory(self, directory_path, db):
        """Processa todos os XMLs de um diretório"""
        directory_path = Path(directory_path)
        results = {
            'success': 0,
            'errors': 0,
            'duplicates': 0,
            'messages': []
        }
        
        if not directory_path.exists():
            results['messages'].append("Diretório não encontrado")
            return results
        
        xml_files = list(directory_path.glob("*.xml")) + list(directory_path.glob("*.XML"))
        
        for xml_file in xml_files:
            try:
                file_content = xml_file.read_bytes()
                filename = xml_file.name
                
                content_hash = self.calculate_hash(file_content)
                file_path, is_new = self.save_xml_file(file_content, filename)
                
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
                    xml_content=file_content.decode('utf-8', errors='ignore')
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

# Inicialização
@st.cache_resource
def init_database():
    return XMLDatabase()

@st.cache_resource
def init_processor():
    return XMLProcessor()

db = init_database()
processor = init_processor()

# Interface principal
st.title("📄 Sistema de Armazenamento de XML")
st.markdown("### Armazene e gerencie seus XMLs de forma permanente")

# Sidebar
st.sidebar.header("Estatísticas")
total_files = db.get_file_count()
st.sidebar.metric("Total de XMLs Armazenados", total_files)

# Abas principais
tab1, tab2, tab3, tab4 = st.tabs(["Upload Individual", "Upload em Lote", "Gerenciar Arquivos", "Buscar Arquivos"])

# Tab 1 - Upload Individual
with tab1:
    st.header("Upload Individual de XML")
    
    uploaded_file = st.file_uploader(
        "Selecione um arquivo XML", 
        type=['xml'],
        help="Selecione um arquivo XML para armazenar"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info(f"Arquivo selecionado: {uploaded_file.name}")
            st.write(f"Tamanho: {len(uploaded_file.getvalue())} bytes")
        
        with col2:
            if st.button("🔄 Armazenar XML", use_container_width=True):
                with st.spinner("Processando arquivo..."):
                    success, message = processor.process_uploaded_file(uploaded_file, db)
                    
                    if success:
                        st.success(message)
                        st.balloons()
                    else:
                        st.error(message)
                
                # Atualiza estatísticas
                st.rerun()

# Tab 2 - Upload em Lote
with tab2:
    st.header("Upload em Lote de XMLs")
    
    uploaded_files = st.file_uploader(
        "Selecione múltiplos arquivos XML", 
        type=['xml'],
        accept_multiple_files=True,
        help="Selecione vários arquivos XML para armazenar"
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
                
                time.sleep(0.1)  # Pequena pausa para visualização
            
            progress_bar.empty()
            status_text.empty()
            
            st.success(f"Processamento concluído!")
            st.write(f"✅ Sucessos: {success_count}")
            st.write(f"❌ Erros: {error_count}")
            
            st.rerun()
    
    st.divider()
    
    # Upload de diretório (para grandes quantidades)
    st.subheader("Para grandes volumes (50k+ XMLs)")
    st.info("Para processar 50 mil XMLs, recomendamos usar a opção de diretório")
    
    directory_path = st.text_input(
        "Caminho do diretório com XMLs",
        placeholder="Ex: C:/xml_files/ ou /home/usuario/xml_files/"
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
                
                st.rerun()
        else:
            st.error("Diretório não encontrado ou caminho inválido")

# Tab 3 - Gerenciar Arquivos
with tab3:
    st.header("Gerenciar Arquivos Armazenados")
    
    files = db.get_all_files()
    
    if files:
        st.write(f"Total de arquivos: {len(files)}")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            items_per_page = st.selectbox("Itens por página", [10, 25, 50, 100])
        with col2:
            search_term = st.text_input("Buscar por nome")
        
        # Aplicar filtro de busca
        if search_term:
            filtered_files = db.search_files(search_term)
        else:
            filtered_files = files
        
        # Paginação
        total_pages = max(1, (len(filtered_files) + items_per_page - 1) // items_per_page)
        page = st.number_input("Página", min_value=1, max_value=total_pages, value=1)
        
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(filtered_files))
        
        # Tabela de arquivos
        st.write(f"Mostrando {start_idx + 1}-{end_idx} de {len(filtered_files)} arquivos")
        
        for file in filtered_files[start_idx:end_idx]:
            file_id, filename, file_size, upload_date = file
            
            with st.expander(f"📄 {filename}"):
                col1, col2, col3 = st.columns(3)
                
                col1.write(f"**ID:** {file_id}")
                col2.write(f"**Tamanho:** {file_size} bytes")
                col3.write(f"**Data:** {upload_date}")
                
                # Botão para visualizar (simplificado)
                if st.button("👁️ Visualizar", key=f"view_{file_id}"):
                    st.info("Funcionalidade de visualização completa seria implementada aqui")
                
                if st.button("🗑️ Excluir", key=f"delete_{file_id}"):
                    st.warning("Funcionalidade de exclusão seria implementada aqui")
    else:
        st.info("Nenhum arquivo armazenado ainda.")

# Tab 4 - Buscar Arquivos
with tab4:
    st.header("Buscar Arquivos")
    
    search_query = st.text_input(
        "Digite o nome ou parte do nome do arquivo",
        placeholder="Ex: nfe, nota fiscal, etc."
    )
    
    if search_query:
        results = db.search_files(search_query)
        
        if results:
            st.success(f"Encontrados {len(results)} resultado(s)")
            
            for file in results:
                file_id, filename, file_size, upload_date = file
                
                st.write(f"**{filename}**")
                st.write(f"ID: {file_id} | Tamanho: {file_size} bytes | Data: {upload_date}")
                st.divider()
        else:
            st.warning("Nenhum arquivo encontrado com o termo buscado.")

# Footer
st.sidebar.divider()
st.sidebar.info("""
**💡 Dicas:**
- Para 50k XMLs, use a opção de diretório
- Sistema otimizado para grandes volumes
- Dados armazenados permanentemente
""")