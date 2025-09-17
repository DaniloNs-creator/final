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
import tempfile
import base64
from io import BytesIO

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
        
        # Tabela para dados estruturados extraídos dos XMLs (para Power BI)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS xml_structured_data (
                id INTEGER PRIMARY KEY,
                xml_id INTEGER,
                chave_acesso TEXT,
                emitente_cnpj TEXT,
                emitente_nome TEXT,
                destinatario_cnpj TEXT,
                destinatario_nome TEXT,
                data_emissao DATE,
                valor_total DECIMAL(15, 2),
                natureza_operacao TEXT,
                FOREIGN KEY (xml_id) REFERENCES xml_files (id)
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
                
                # Extrai e armazena dados estruturados para Power BI
                self.extract_structured_data(file_id, xml_content, conn)
            
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
    
    def extract_structured_data(self, xml_id, xml_content, conn):
        """Extrai dados estruturados do XML para análise no Power BI"""
        try:
            root = ET.fromstring(xml_content)
            
            # Namespaces comuns em XMLs fiscais
            namespaces = {
                'nfe': 'http://www.portalfiscal.inf.br/nfe'
            }
            
            # Tenta encontrar a chave de acesso
            chave_acesso = None
            inf_nfe = root.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
            if inf_nfe is not None:
                chave_acesso = inf_nfe.attrib.get('Id', '').replace('NFe', '')
            
            # Tenta encontrar dados do emitente
            emitente = root.find(".//{http://www.portalfiscal.inf.br/nfe}emit")
            emitente_cnpj = None
            emitente_nome = None
            if emitente is not None:
                cnpj_elem = emitente.find("{http://www.portalfiscal.inf.br/nfe}CNPJ")
                if cnpj_elem is not None:
                    emitente_cnpj = cnpj_elem.text
                else:
                    cpf_elem = emitente.find("{http://www.portalfiscal.inf.br/nfe}CPF")
                    if cpf_elem is not None:
                        emitente_cnpj = cpf_elem.text
                nome_elem = emitente.find("{http://www.portalfiscal.inf.br/nfe}xNome")
                if nome_elem is not None:
                    emitente_nome = nome_elem.text
            
            # Tenta encontrar dados do destinatário
            destinatario = root.find(".//{http://www.portalfiscal.inf.br/nfe}dest")
            destinatario_cnpj = None
            destinatario_nome = None
            if destinatario is not None:
                cnpj_elem = destinatario.find("{http://www.portalfiscal.inf.br/nfe}CNPJ")
                if cnpj_elem is not None:
                    destinatario_cnpj = cnpj_elem.text
                else:
                    cpf_elem = destinatario.find("{http://www.portalfiscal.inf.br/nfe}CPF")
                    if cpf_elem is not None:
                        destinatario_cnpj = cpf_elem.text
                nome_elem = destinatario.find("{http://www.portalfiscal.inf.br/nfe}xNome")
                if nome_elem is not None:
                    destinatario_nome = nome_elem.text
            
            # Tenta encontrar data de emissão
            data_emissao = None
            ide = root.find(".//{http://www.portalfiscal.inf.br/nfe}ide")
            if ide is not None:
                dh_emi_elem = ide.find("{http://www.portalfiscal.inf.br/nfe}dhEmi")
                if dh_emi_elem is not None:
                    data_emissao = dh_emi_elem.text[:10]  # Pega apenas a data (YYYY-MM-DD)
                else:
                    d_emi_elem = ide.find("{http://www.portalfiscal.inf.br/nfe}dEmi")
                    if d_emi_elem is not None:
                        data_emissao = d_emi_elem.text
            
            # Tenta encontrar valor total
            valor_total = None
            total = root.find(".//{http://www.portalfiscal.inf.br/nfe}total")
            if total is not None:
                icms_tot = total.find("{http://www.portalfiscal.inf.br/nfe}ICMSTot")
                if icms_tot is not None:
                    v_nf_elem = icms_tot.find("{http://www.portalfiscal.inf.br/nfe}vNF")
                    if v_nf_elem is not None:
                        try:
                            valor_total = float(v_nf_elem.text)
                        except:
                            valor_total = None
            
            # Tenta encontrar natureza da operação
            natureza_operacao = None
            if ide is not None:
                nat_op_elem = ide.find("{http://www.portalfiscal.inf.br/nfe}natOp")
                if nat_op_elem is not None:
                    natureza_operacao = nat_op_elem.text
            
            # Insere os dados estruturados
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO xml_structured_data 
                (xml_id, chave_acesso, emitente_cnpj, emitente_nome, destinatario_cnpj, 
                 destinatario_nome, data_emissao, valor_total, natureza_operacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (xml_id, chave_acesso, emitente_cnpj, emitente_nome, destinatario_cnpj,
                 destinatario_nome, data_emissao, valor_total, natureza_operacao))
            
        except Exception as e:
            print(f"Erro ao extrair dados estruturados: {e}")
    
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
    
    def get_xml_content(self, file_id):
        """Retorna o conteúdo de um XML específico"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT xml_content FROM xml_content WHERE id = ?', (file_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None
    
    def get_structured_data(self):
        """Retorna todos os dados estruturados para Power BI"""
        conn = sqlite3.connect(self.db_name)
        
        query = '''
            SELECT 
                xf.id,
                xf.filename,
                xf.upload_date,
                xsd.chave_acesso,
                xsd.emitente_cnpj,
                xsd.emitente_nome,
                xsd.destinatario_cnpj,
                xsd.destinatario_nome,
                xsd.data_emissao,
                xsd.valor_total,
                xsd.natureza_operacao
            FROM xml_structured_data xsd
            JOIN xml_files xf ON xsd.xml_id = xf.id
            ORDER BY xsd.data_emissao DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_structured_data_by_date_range(self, start_date, end_date):
        """Retorna dados estruturados filtrados por intervalo de datas"""
        conn = sqlite3.connect(self.db_name)
        
        query = '''
            SELECT 
                xf.id,
                xf.filename,
                xf.upload_date,
                xsd.chave_acesso,
                xsd.emitente_cnpj,
                xsd.emitente_nome,
                xsd.destinatario_cnpj,
                xsd.destinatario_nome,
                xsd.data_emissao,
                xsd.valor_total,
                xsd.natureza_operacao
            FROM xml_structured_data xsd
            JOIN xml_files xf ON xsd.xml_id = xf.id
            WHERE date(xsd.data_emissao) BETWEEN date(?) AND date(?)
            ORDER BY xsd.data_emissao DESC
        '''
        
        try:
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            df = pd.DataFrame()
        
        conn.close()
        return df

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
st.markdown("### Armazene, consulte e exporte seus XMLs para Power BI")

# Sidebar
st.sidebar.header("Estatísticas")
total_files = db.get_file_count()
st.sidebar.metric("Total de XMLs Armazenados", total_files)

# Abas principais
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Upload", "Consultar XMLs", "Visualizar XML", "Dados para Power BI", "Sobre"])

# Tab 1 - Upload
with tab1:
    st.header("Upload de XMLs")
    
    upload_option = st.radio("Selecione o tipo de upload:", 
                            ["Upload Individual", "Upload em Lote", "Upload por Diretório"])
    
    if upload_option == "Upload Individual":
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
    
    elif upload_option == "Upload em Lote":
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
    
    else:  # Upload por Diretório
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

# Tab 2 - Consultar XMLs
with tab2:
    st.header("Consultar XMLs Armazenados")
    
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
                
                col1.write(f"**ID:** {file_id}")
                col2.write(f"**Tamanho:** {file_size} bytes")
                col3.write(f"**Data Upload:** {upload_date}")
                
                # Botão para visualizar
                if col4.button("👁️ Visualizar", key=f"view_{file_id}"):
                    st.session_state.selected_xml = file_id
                    st.switch_page(":📄: Visualizar XML")  # Isso vai redirecionar para a aba de visualização
        
        # Botão para exportar lista
        if st.button("📊 Exportar Lista para Excel"):
            df = pd.DataFrame(filtered_files, columns=['ID', 'Nome do Arquivo', 'Tamanho (bytes)', 'Data de Upload'])
            df['Data de Upload'] = pd.to_datetime(df['Data de Upload']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Criar arquivo Excel em memória
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='XMLs', index=False)
            
            # Preparar para download
            output.seek(0)
            b64 = base64.b64encode(output.read()).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="lista_xmls.xlsx">📥 Baixar Lista de XMLs</a>'
            st.markdown(href, unsafe_allow_html=True)
            
    else:
        st.info("Nenhum arquivo armazenado ainda.")

# Tab 3 - Visualizar XML
with tab3:
    st.header("Visualizar Conteúdo do XML")
    
    # Se um XML foi selecionado para visualização
    if 'selected_xml' in st.session_state:
        xml_content = db.get_xml_content(st.session_state.selected_xml)
        
        if xml_content:
            # Formatar o XML para melhor visualização
            try:
                parsed_xml = xml.dom.minidom.parseString(xml_content)
                pretty_xml = parsed_xml.toprettyxml()
                
                st.text_area("Conteúdo do XML (formatado)", pretty_xml, height=500)
                
                # Botões de ação
                col1, col2, col3 = st.columns(3)
                
                # Download do XML
                b64_xml = base64.b64encode(xml_content.encode()).decode()
                href = f'<a href="data:application/xml;base64,{b64_xml}" download="xml_{st.session_state.selected_xml}.xml">📥 Baixar XML</a>'
                col1.markdown(href, unsafe_allow_html=True)
                
                # Copiar para área de transferência
                if col2.button("📋 Copiar Conteúdo"):
                    st.code(xml_content)
                    st.success("Conteúdo copiado para a área de transferência!")
                
                # Voltar para a lista
                if col3.button("↩️ Voltar para Lista"):
                    del st.session_state.selected_xml
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Erro ao formatar XML: {e}")
                st.text_area("Conteúdo do XML (original)", xml_content, height=500)
        else:
            st.error("Conteúdo do XML não encontrado.")
            if st.button("↩️ Voltar para Lista"):
                del st.session_state.selected_xml
                st.rerun()
    else:
        st.info("Selecione um XML na aba 'Consultar XMLs' para visualizar seu conteúdo.")

# Tab 4 - Dados para Power BI
with tab4:
    st.header("Dados Estruturados para Power BI")
    
    st.info("""
    Esta seção fornece os dados estruturados extraídos dos XMLs para uso no Power BI.
    Os dados incluem informações como chave de acesso, emitente, destinatário, valores e datas.
    """)
    
    # Filtro por data
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Data inicial", value=date.today().replace(day=1))
    with col2:
        end_date = st.date_input("Data final", value=date.today())
    
    # Carregar dados
    if st.button("Carregar Dados", type="primary"):
        with st.spinner("Carregando dados..."):
            df = db.get_structured_data_by_date_range(
                start_date.strftime('%Y-%m-%d'), 
                end_date.strftime('%Y-%m-%d')
            )
            
            if not df.empty:
                st.success(f"Dados carregados: {len(df)} registros encontrados")
                
                # Exibir dataframe
                st.dataframe(df)
                
                # Estatísticas rápidas
                st.subheader("📈 Estatísticas")
                col1, col2, col3 = st.columns(3)
                
                col1.metric("Total de Registros", len(df))
                col2.metric("Valor Total", f"R$ {df['valor_total'].sum():,.2f}" if 'valor_total' in df.columns else "N/A")
                col3.metric("Valor Médio", f"R$ {df['valor_total'].mean():,.2f}" if 'valor_total' in df.columns and len(df) > 0 else "N/A")
                
                # Opções de exportação
                st.subheader("📤 Exportar Dados")
                
                # Exportar para Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Dados_XML', index=False)
                
                output.seek(0)
                b64 = base64.b64encode(output.read()).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="dados_xml_powerbi.xlsx">📥 Baixar para Excel</a>'
                st.markdown(href, unsafe_allow_html=True)
                
                # Exportar para CSV
                csv = df.to_csv(index=False)
                b64_csv = base64.b64encode(csv.encode()).decode()
                href_csv = f'<a href="data:file/csv;base64,{b64_csv}" download="dados_xml_powerbi.csv">📥 Baixar para CSV</a>'
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
                       - No campo "Banco de dados", digite o caminho completo para o arquivo `xml_database.db`
                       - Selecione a tabela `xml_structured_data`
                    
                    3. **Método 3: Conexão ODBC**
                       - Configure um driver ODBC para SQLite
                       - No Power BI, selecione "Obter Dados" > "ODBC"
                       - Selecione a fonte de dados configurada
                    
                    **Vantagem dos métodos 2 e 3:** Atualizações em tempo real sem precisar reimportar arquivos.
                    """)
            else:
                st.warning("Nenhum dado encontrado para o período selecionado.")

# Tab 5 - Sobre
with tab5:
    st.header("Sobre o Sistema")
    
    st.markdown("""
    ## Sistema de Armazenamento e Análise de XMLs
    
    Este sistema foi desenvolvido para armazenar, gerenciar e analisar grandes volumes de arquivos XML,
    com foco especial em integração com o Power BI para análise de dados.
    
    ### Funcionalidades Principais:
    
    - **Armazenamento seguro** de XMLs em banco de dados SQLite e sistema de arquivos
    - **Verificação de duplicatas** para evitar armazenamento redundante
    - **Extração automática** de dados estruturados para análise
    - **Interface intuitiva** para consulta e visualização
    - **Exportação para Power BI** via Excel, CSV ou conexão direta
    
    ### Como usar com Power BI:
    
    1. Armazene seus XMLs através das opções de upload
    2. Acesse a aba "Dados para Power BI"
    3. Filtre por período se necessário
    4. Exporte os dados ou conecte-se diretamente ao banco de dados
    
    ### Estrutura do Banco de Dados:
    
    - `xml_files`: Metadados dos arquivos
    - `xml_content`: Conteúdo completo dos XMLs
    - `xml_structured_data`: Dados extraídos para análise (esta é a tabela principal para o Power BI)
    
    ### Tecnologias Utilizadas:
    
    - Python 3.x
    - Streamlit para interface web
    - SQLite para armazenamento
    - Pandas para manipulação de dados
    - XML.etree para processamento de XML
    """)
    
    st.info("""
    💡 **Dica:** Para grandes volumes (50k+ XMLs), use a opção de upload por diretório 
    e conecte o Power BI diretamente ao banco de dados SQLite para melhor performance.
    """)

# Footer
st.sidebar.divider()
st.sidebar.info("""
**💡 Dicas:**
- Para 50k XMLs, use a opção de diretório
- Conecte o Power BI diretamente ao banco SQLite
- Dados armazenados permanentemente
""")

# Link para documentação
st.sidebar.markdown("---")
st.sidebar.markdown("[📚 Documentação Completa](#)")