import streamlit as st
import sqlite3
from datetime import datetime, timedelta, date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
import numpy as np
import zipfile

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Sistema de Processamento",
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
if 'cte_data' not in st.session_state:
    st.session_state.cte_data = None
if 'processed_txt_files' not in st.session_state:
    st.session_state.processed_txt_files = []
if 'processed_cte_files' not in st.session_state:
    st.session_state.processed_cte_files = []
if 'db_manager' not in st.session_state:
    st.session_state.db_manager = None

# --- BANCO DE DADOS PARA ARMAZENAMENTO PERMANENTE ---
class XMLDatabaseManager:
    def __init__(self, db_path="xml_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com tabelas otimizadas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela principal para armazenar XMLs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS xml_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                file_size INTEGER,
                xml_content TEXT NOT NULL,
                processed_date TEXT NOT NULL,
                import_date TEXT DEFAULT CURRENT_TIMESTAMP,
                tags TEXT,
                status TEXT DEFAULT 'active',
                nCT TEXT,
                chave_cte TEXT,
                emitente TEXT,
                remetente TEXT,
                destinatario TEXT,
                valor_prestacao REAL,
                peso_bruto REAL,
                uf_origem TEXT,
                uf_destino TEXT,
                data_emissao TEXT
            )
        ''')
        
        # Índices para otimização
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filename ON xml_files(filename)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON xml_files(file_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nCT ON xml_files(nCT)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chave_cte ON xml_files(chave_cte)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emitente ON xml_files(emitente)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_data_emissao ON xml_files(data_emissao)')
        
        conn.commit()
        conn.close()
    
    def calculate_file_hash(self, xml_content):
        """Calcula hash único para evitar duplicatas"""
        return hashlib.md5(xml_content.encode('utf-8')).hexdigest()
    
    def extract_cte_metadata(self, xml_content):
        """Extrai metadados importantes do CT-e para indexação"""
        try:
            root = ET.fromstring(xml_content)
            
            def find_text(element, xpath):
                try:
                    for prefix, uri in CTE_NAMESPACES.items():
                        full_xpath = xpath.replace('cte:', f'{{{uri}}}')
                        found = element.find(full_xpath)
                        if found is not None and found.text:
                            return found.text
                    found = element.find(xpath.replace('cte:', ''))
                    if found is not None and found.text:
                        return found.text
                    return None
                except:
                    return None
            
            # Extrai metadados importantes
            nCT = find_text(root, './/cte:nCT')
            chave_cte = find_text(root, './/cte:chCTe')
            emitente = find_text(root, './/cte:emit/cte:xNome')
            remetente = find_text(root, './/cte:rem/cte:xNome')
            destinatario = find_text(root, './/cte:dest/cte:xNome')
            valor_prestacao = find_text(root, './/cte:vTPrest')
            uf_origem = find_text(root, './/cte:UFIni')
            uf_destino = find_text(root, './/cte:UFFim')
            data_emissao = find_text(root, './/cte:dhEmi')
            
            # Extrai peso bruto
            peso_bruto = 0.0
            for prefix, uri in CTE_NAMESPACES.items():
                infQ_elements = root.findall(f'.//{{{uri}}}infQ')
                for infQ in infQ_elements:
                    tpMed = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
                    if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                        if 'PESO' in tpMed.text.upper():
                            try:
                                peso_bruto = float(qCarga.text)
                                break
                            except:
                                pass
            
            return {
                'nCT': nCT,
                'chave_cte': chave_cte,
                'emitente': emitente,
                'remetente': remetente,
                'destinatario': destinatario,
                'valor_prestacao': float(valor_prestacao) if valor_prestacao else 0.0,
                'peso_bruto': peso_bruto,
                'uf_origem': uf_origem,
                'uf_destino': uf_destino,
                'data_emissao': data_emissao[:10] if data_emissao else None
            }
        except Exception as e:
            print(f"Erro na extração de metadados: {e}")
            return {}
    
    def insert_xml(self, xml_content, filename, tags=None):
        """Insere um XML no banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            file_hash = self.calculate_file_hash(xml_content)
            
            # Verifica se arquivo já existe
            cursor.execute('SELECT id FROM xml_files WHERE file_hash = ?', (file_hash,))
            if cursor.fetchone():
                return False, "Arquivo já existe no banco de dados"
            
            # Extrai metadados
            metadata = self.extract_cte_metadata(xml_content)
            
            # Insere na tabela
            cursor.execute('''
                INSERT INTO xml_files 
                (filename, file_hash, file_size, xml_content, processed_date, tags,
                 nCT, chave_cte, emitente, remetente, destinatario, valor_prestacao,
                 peso_bruto, uf_origem, uf_destino, data_emissao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename, file_hash, len(xml_content), xml_content,
                datetime.now().isoformat(), tags,
                metadata.get('nCT'), metadata.get('chave_cte'),
                metadata.get('emitente'), metadata.get('remetente'),
                metadata.get('destinatario'), metadata.get('valor_prestacao'),
                metadata.get('peso_bruto'), metadata.get('uf_origem'),
                metadata.get('uf_destino'), metadata.get('data_emissao')
            ))
            
            conn.commit()
            return True, f"XML inserido com sucesso! ID: {cursor.lastrowid}"
            
        except Exception as e:
            conn.rollback()
            return False, f"Erro ao inserir XML: {str(e)}"
        finally:
            conn.close()
    
    def search_xml(self, search_term=None, search_type="all", limit=100):
        """Busca XMLs no banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if search_type == "all" or not search_term:
                cursor.execute('''
                    SELECT id, filename, nCT, emitente, valor_prestacao, peso_bruto,
                           data_emissao, import_date 
                    FROM xml_files 
                    WHERE status = 'active'
                    ORDER BY import_date DESC
                    LIMIT ?
                ''', (limit,))
            elif search_type == "filename":
                cursor.execute('''
                    SELECT id, filename, nCT, emitente, valor_prestacao, peso_bruto,
                           data_emissao, import_date 
                    FROM xml_files 
                    WHERE filename LIKE ? AND status = 'active'
                    ORDER BY import_date DESC
                    LIMIT ?
                ''', (f'%{search_term}%', limit))
            elif search_type == "nCT":
                cursor.execute('''
                    SELECT id, filename, nCT, emitente, valor_prestacao, peso_bruto,
                           data_emissao, import_date 
                    FROM xml_files 
                    WHERE nCT LIKE ? AND status = 'active'
                    ORDER BY import_date DESC
                    LIMIT ?
                ''', (f'%{search_term}%', limit))
            elif search_type == "emitente":
                cursor.execute('''
                    SELECT id, filename, nCT, emitente, valor_prestacao, peso_bruto,
                           data_emissao, import_date 
                    FROM xml_files 
                    WHERE emitente LIKE ? AND status = 'active'
                    ORDER BY import_date DESC
                    LIMIT ?
                ''', (f'%{search_term}%', limit))
            
            return cursor.fetchall()
        finally:
            conn.close()
    
    def get_xml_content(self, xml_id):
        """Recupera conteúdo completo do XML por ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT filename, xml_content FROM xml_files WHERE id = ?', (xml_id,))
            return cursor.fetchone()
        finally:
            conn.close()
    
    def get_database_stats(self):
        """Retorna estatísticas do banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        try:
            cursor.execute('SELECT COUNT(*) FROM xml_files WHERE status = "active"')
            stats['total_files'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(file_size) FROM xml_files WHERE status = "active"')
            stats['total_size_bytes'] = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT COUNT(DISTINCT emitente) FROM xml_files WHERE status = "active"')
            stats['unique_emitters'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(valor_prestacao) FROM xml_files WHERE status = "active"')
            stats['total_value'] = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(peso_bruto) FROM xml_files WHERE status = "active"')
            stats['total_weight'] = cursor.fetchone()[0] or 0
            
            return stats
        finally:
            conn.close()
    
    def export_to_dataframe(self, limit=1000):
        """Exporta dados para DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT filename, nCT, emitente, remetente, destinatario, 
                   valor_prestacao, peso_bruto, uf_origem, uf_destino, data_emissao
            FROM xml_files 
            WHERE status = 'active'
            ORDER BY import_date DESC
            LIMIT ?
        '''
        
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df

# --- ANIMAÇÕES DE CARREGAMENTO ---
def show_loading_animation(message="Processando..."):
    """Exibe uma animação de carregamento"""
    with st.spinner(message):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)
        progress_bar.empty()

def show_processing_animation(message="Analisando dados..."):
    """Exibe animação de processamento"""
    placeholder = st.empty()
    with placeholder.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info(f"⏳ {message}")
            spinner_placeholder = st.empty()
            spinner_chars = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
            for i in range(20):
                spinner_placeholder.markdown(f"<div style='text-align: center; font-size: 24px;'>{spinner_chars[i % 8]}</div>", unsafe_allow_html=True)
                time.sleep(0.1)
    placeholder.empty()

def show_success_animation(message="Concluído!"):
    """Exibe animação de sucesso"""
    success_placeholder = st.empty()
    with success_placeholder.container():
        st.success(f"✅ {message}")
        time.sleep(1.5)
    success_placeholder.empty()

# --- PROCESSADOR TXT COM SUPORTE A MÚLTIPLOS ARQUIVOS ---
class TXTProcessor:
    def __init__(self):
        self.processed_files = []
    
    def detectar_encoding(self, conteudo):
        """Detecta o encoding do conteúdo do arquivo"""
        resultado = chardet.detect(conteudo)
        return resultado['encoding']
    
    def processar_arquivo_txt(self, conteudo, filename, padroes):
        """
        Processa um único arquivo TXT removendo linhas indesejadas
        """
        try:
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN"
            }
            
            encoding = self.detectar_encoding(conteudo)
            
            try:
                texto = conteudo.decode(encoding)
            except UnicodeDecodeError:
                texto = conteudo.decode('latin-1')
            
            linhas = texto.splitlines()
            linhas_processadas = []
            
            for linha in linhas:
                linha = linha.strip()
                if not any(padrao in linha for padrao in padroes):
                    for original, substituto in substituicoes.items():
                        linha = linha.replace(original, substituto)
                    linhas_processadas.append(linha)
            
            resultado = "\n".join(linhas_processadas)
            
            return {
                'filename': filename,
                'conteudo': resultado,
                'linhas_originais': len(linhas),
                'linhas_processadas': len(linhas_processadas),
                'linhas_removidas': len(linhas) - len(linhas_processadas)
            }
        
        except Exception as e:
            return {
                'filename': filename,
                'erro': str(e),
                'conteudo': None
            }
    
    def processar_multiplos_arquivos(self, uploaded_files, padroes):
        """Processa múltiplos arquivos TXT"""
        resultados = {
            'sucessos': 0,
            'erros': 0,
            'arquivos': []
        }
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processando {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
            progress_bar.progress((i + 1) / len(uploaded_files))
            
            conteudo = uploaded_file.getvalue()
            resultado = self.processar_arquivo_txt(conteudo, uploaded_file.name, padroes)
            
            if 'erro' not in resultado:
                resultados['sucessos'] += 1
                self.processed_files.append(resultado)
            else:
                resultados['erros'] += 1
            
            resultados['arquivos'].append(resultado)
        
        progress_bar.empty()
        status_text.empty()
        
        return resultados
    
    def get_arquivos_processados(self):
        """Retorna lista de arquivos processados"""
        return self.processed_files
    
    def limpar_dados(self):
        """Limpa os dados processados"""
        self.processed_files = []

def processador_txt():
    st.title("📄 Processador de Arquivos TXT - Múltiplos Arquivos")
    st.markdown("""
    <div class="card">
        Remova linhas indesejadas de múltiplos arquivos TXT simultaneamente. 
        Carregue vários arquivos e defina os padrões a serem removidos.
    </div>
    """, unsafe_allow_html=True)
    
    processor = TXTProcessor()
    
    # Padrões padrão para remoção
    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
    
    # Upload de múltiplos arquivos
    uploaded_files = st.file_uploader(
        "Selecione os arquivos TXT (múltiplos)", 
        type=['txt'], 
        accept_multiple_files=True,
        key="txt_multiple_unique"
    )
    
    # Opções avançadas
    with st.expander("⚙️ Configurações avançadas", expanded=False):
        padroes_adicionais = st.text_input(
            "Padrões adicionais para remoção (separados por vírgula)",
            help="Exemplo: padrão1, padrão2, padrão3",
            key="padroes_adicionais_txt"
        )
        
        padroes = padroes_default + [
            p.strip() for p in padroes_adicionais.split(",") 
            if p.strip()
        ] if padroes_adicionais else padroes_default
        
        st.info(f"**Padrões ativos:** {', '.join(padroes)}")
    
    if uploaded_files:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔄 Processar Todos os Arquivos TXT", key="process_all_txt_unique"):
                try:
                    show_loading_animation(f"Iniciando processamento de {len(uploaded_files)} arquivos...")
                    
                    resultados = processor.processar_multiplos_arquivos(uploaded_files, padroes)
                    
                    show_success_animation("Processamento em lote concluído!")
                    
                    st.success(f"""
                    **Processamento concluído!**  
                    ✅ Arquivos processados com sucesso: {resultados['sucessos']}  
                    ❌ Arquivos com erro: {resultados['erros']}
                    """)
                    
                    # Salvar no session state
                    st.session_state.processed_txt_files = processor.get_arquivos_processados()
                    
                except Exception as e:
                    st.error(f"Erro inesperado: {str(e)}")
        
        with col2:
            if st.button("🗑️ Limpar Arquivos Processados", type="secondary", key="limpar_txt_unique"):
                processor.limpar_dados()
                st.session_state.processed_txt_files = []
                st.success("Dados limpos com sucesso!")
                time.sleep(1)
                st.rerun()
    
    # Exibir resultados
    arquivos_processados = st.session_state.processed_txt_files
    
    if arquivos_processados:
        st.subheader(f"📋 Resultados do Processamento ({len(arquivos_processados)} arquivos)")
        
        # Estatísticas gerais
        total_linhas_originais = sum(arq['linhas_originais'] for arq in arquivos_processados)
        total_linhas_processadas = sum(arq['linhas_processadas'] for arq in arquivos_processados)
        total_linhas_removidas = total_linhas_originais - total_linhas_processadas
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Arquivos", len(arquivos_processados))
        col2.metric("Linhas Originais", total_linhas_originais)
        col3.metric("Linhas Processadas", total_linhas_processadas)
        col4.metric("Linhas Removidas", total_linhas_removidas)
        
        # Tabs para navegação
        tab1, tab2, tab3 = st.tabs(["📊 Visualizar Arquivos", "👀 Prévia dos Conteúdos", "📥 Download em Lote"])
        
        with tab1:
            st.subheader("Lista de Arquivos Processados")
            dados_tabela = []
            for arq in arquivos_processados:
                dados_tabela.append({
                    'Arquivo': arq['filename'],
                    'Linhas Originais': arq['linhas_originais'],
                    'Linhas Processadas': arq['linhas_processadas'],
                    'Linhas Removidas': arq['linhas_removidas'],
                    'Taxa Redução': f"{(arq['linhas_removidas']/arq['linhas_originais']*100):.1f}%" if arq['linhas_originais'] > 0 else "0%"
                })
            
            df_arquivos = pd.DataFrame(dados_tabela)
            st.dataframe(df_arquivos, use_container_width=True)
        
        with tab2:
            st.subheader("Prévia dos Conteúdos Processados")
            
            arquivo_selecionado = st.selectbox(
                "Selecione um arquivo para visualizar:",
                options=[arq['filename'] for arq in arquivos_processados],
                key="select_arquivo_txt"
            )
            
            arquivo = next((arq for arq in arquivos_processados if arq['filename'] == arquivo_selecionado), None)
            
            if arquivo:
                st.write(f"**Arquivo:** {arquivo['filename']}")
                st.write(f"**Estatísticas:** {arquivo['linhas_originais']} → {arquivo['linhas_processadas']} linhas ({arquivo['linhas_removidas']} removidas)")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.text_area("Conteúdo Processado", arquivo['conteudo'], height=400, key="conteudo_processado_txt")
                
                with col2:
                    st.info("**Informações do processamento:**")
                    st.write(f"- Redução de: {arquivo['linhas_removidas']} linhas")
                    st.write(f"- Eficiência: {(arquivo['linhas_removidas']/arquivo['linhas_originais']*100):.1f}%")
        
        with tab3:
            st.subheader("Download dos Arquivos Processados")
            
            # Download individual
            st.write("**Download Individual:**")
            for i, arq in enumerate(arquivos_processados):
                buffer = BytesIO()
                buffer.write(arq['conteudo'].encode('utf-8'))
                buffer.seek(0)
                
                st.download_button(
                    label=f"⬇️ {arq['filename']}",
                    data=buffer,
                    file_name=f"processado_{arq['filename']}",
                    mime="text/plain",
                    key=f"download_txt_{i}"
                )
            
            # Download em lote (ZIP)
            st.write("**Download em Lote (ZIP):**")
            if st.button("📦 Gerar Pacote ZIP com Todos os Arquivos", key="zip_txt_unique"):
                show_processing_animation("Criando arquivo ZIP...")
                
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for arq in arquivos_processados:
                        zip_file.writestr(
                            f"processado_{arq['filename']}",
                            arq['conteudo'].encode('utf-8')
                        )
                
                zip_buffer.seek(0)
                
                st.download_button(
                    label="📥 Baixar Todos os Arquivos (ZIP)",
                    data=zip_buffer,
                    file_name="arquivos_processados.zip",
                    mime="application/zip",
                    key="download_zip_txt"
                )
    else:
        st.info("Nenhum arquivo TXT processado ainda. Faça upload de arquivos acima.")

# --- PROCESSADOR CT-E COM BANCO DE DADOS INTEGRADO ---
class CTeProcessorWithDB:
    def __init__(self, db_manager):
        self.processed_data = []
        self.db_manager = db_manager
    
    def extract_nfe_number_from_key(self, chave_acesso):
        """Extrai o número da NF-e da chave de acesso"""
        if not chave_acesso or len(chave_acesso) != 44:
            return None
        try:
            return chave_acesso[25:34]
        except Exception:
            return None
    
    def extract_peso_bruto(self, root):
        """Extrai o peso bruto do CT-e"""
        try:
            tipos_peso = ['PESO BRUTO', 'PESO BASE DE CALCULO', 'PESO BASE CÁLCULO', 'PESO']
            
            for prefix, uri in CTE_NAMESPACES.items():
                infQ_elements = root.findall(f'.//{{{uri}}}infQ')
                for infQ in infQ_elements:
                    tpMed = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
                    if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                        for tipo_peso in tipos_peso:
                            if tipo_peso in tpMed.text.upper():
                                return float(qCarga.text), tipo_peso
            
            infQ_elements = root.findall('.//infQ')
            for infQ in infQ_elements:
                tpMed = infQ.find('tpMed')
                qCarga = infQ.find('qCarga')
                if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                    for tipo_peso in tipos_peso:
                        if tipo_peso in tpMed.text.upper():
                            return float(qCarga.text), tipo_peso
            
            return 0.0, "Não encontrado"
        except Exception as e:
            return 0.0, "Erro na extração"
    
    def extract_cte_data(self, xml_content, filename):
        """Extrai dados específicos do CT-e"""
        try:
            root = ET.fromstring(xml_content)
            
            def find_text(element, xpath):
                try:
                    for prefix, uri in CTE_NAMESPACES.items():
                        full_xpath = xpath.replace('cte:', f'{{{uri}}}')
                        found = element.find(full_xpath)
                        if found is not None and found.text:
                            return found.text
                    found = element.find(xpath.replace('cte:', ''))
                    if found is not None and found.text:
                        return found.text
                    return None
                except:
                    return None
            
            # Extrai dados do CT-e
            nCT = find_text(root, './/cte:nCT')
            dhEmi = find_text(root, './/cte:dhEmi')
            UFIni = find_text(root, './/cte:UFIni')
            UFFim = find_text(root, './/cte:UFFim')
            emit_xNome = find_text(root, './/cte:emit/cte:xNome')
            vTPrest = find_text(root, './/cte:vTPrest')
            rem_xNome = find_text(root, './/cte:rem/cte:xNome')
            dest_xNome = find_text(root, './/cte:dest/cte:xNome')
            dest_CNPJ = find_text(root, './/cte:dest/cte:CNPJ')
            dest_CPF = find_text(root, './/cte:dest/cte:CPF')
            dest_xMun = find_text(root, './/cte:dest/cte:enderDest/cte:xMun')
            dest_UF = find_text(root, './/cte:dest/cte:enderDest/cte:UF')
            infNFe_chave = find_text(root, './/cte:infNFe/cte:chave')
            
            documento_destinatario = dest_CNPJ or dest_CPF or 'N/A'
            numero_nfe = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            peso_bruto, tipo_peso_encontrado = self.extract_peso_bruto(root)
            
            # Formata data
            data_formatada = None
            if dhEmi:
                try:
                    data_obj = datetime.strptime(dhEmi[:10], '%Y-%m-%d')
                    data_formatada = data_obj.strftime('%d/%m/%y')
                except:
                    data_formatada = dhEmi[:10]
            
            # Converte valor
            try:
                vTPrest = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                vTPrest = 0.0
            
            return {
                'Arquivo': filename,
                'nCT': nCT or 'N/A',
                'Data Emissão': data_formatada or dhEmi or 'N/A',
                'UF Início': UFIni or 'N/A',
                'UF Fim': UFFim or 'N/A',
                'Emitente': emit_xNome or 'N/A',
                'Valor Prestação': vTPrest,
                'Peso Bruto (kg)': peso_bruto,
                'Tipo de Peso Encontrado': tipo_peso_encontrado,
                'Remetente': rem_xNome or 'N/A',
                'Destinatário': dest_xNome or 'N/A',
                'Documento Destinatário': documento_destinatario,
                'Município Destino': dest_xMun or 'N/A',
                'UF Destino': dest_UF or 'N/A',
                'Chave NFe': infNFe_chave or 'N/A',
                'Número NFe': numero_nfe or 'N/A',
                'Data Processamento': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
        except Exception as e:
            st.error(f"Erro ao extrair dados do CT-e {filename}: {str(e)}")
            return None
    
    def process_single_file(self, uploaded_file, save_to_db=True, tags=None):
        """Processa um único arquivo XML de CT-e"""
        try:
            file_content = uploaded_file.getvalue()
            filename = uploaded_file.name
            
            if not filename.lower().endswith('.xml'):
                return False, "Arquivo não é XML"
            
            content_str = file_content.decode('utf-8', errors='ignore')
            if 'CTe' not in content_str and 'conhecimento' not in content_str.lower():
                return False, "Arquivo não parece ser um CT-e"
            
            # Salva no banco de dados
            if save_to_db:
                success, message = self.db_manager.insert_xml(content_str, filename, tags)
                if not success:
                    return False, message
            
            # Extrai dados para exibição
            cte_data = self.extract_cte_data(content_str, filename)
            
            if cte_data:
                self.processed_data.append(cte_data)
                db_msg = " e salvo no banco" if save_to_db else ""
                return True, f"CT-e {filename} processado com sucesso{db_msg}!"
            else:
                return False, f"Erro ao processar CT-e {filename}"
                
        except Exception as e:
            return False, f"Erro ao processar arquivo {filename}: {str(e)}"
    
    def process_multiple_files(self, uploaded_files, save_to_db=True, tags=None):
        """Processa múltiplos arquivos XML de CT-e"""
        results = {
            'success': 0,
            'errors': 0,
            'messages': []
        }
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processando {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
            progress_bar.progress((i + 1) / len(uploaded_files))
            
            success, message = self.process_single_file(uploaded_file, save_to_db, tags)
            if success:
                results['success'] += 1
            else:
                results['errors'] += 1
            results['messages'].append(message)
        
        progress_bar.empty()
        status_text.empty()
        
        return results
    
    def get_dataframe(self):
        """Retorna os dados processados como DataFrame"""
        if self.processed_data:
            return pd.DataFrame(self.processed_data)
        return pd.DataFrame()
    
    def clear_data(self):
        """Limpa os dados processados"""
        self.processed_data = []

# --- FUNÇÃO PARA CRIAR LINHA DE TENDÊNCIA ---
def add_simple_trendline(fig, x, y):
    """Adiciona uma linha de tendência simples"""
    try:
        mask = ~np.isnan(x) & ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) > 1:
            coefficients = np.polyfit(x_clean, y_clean, 1)
            polynomial = np.poly1d(coefficients)
            x_trend = np.linspace(x_clean.min(), x_clean.max(), 100)
            y_trend = polynomial(x_trend)
            
            fig.add_trace(go.Scatter(
                x=x_trend, y=y_trend, mode='lines', name='Linha de Tendência',
                line=dict(color='red', dash='dash'), opacity=0.7
            ))
    except Exception:
        pass

# --- INTERFACE DO BANCO DE DADOS ---
def setup_xml_database_interface(key_suffix=""):
    """Configura a interface do banco de dados"""
    st.title("💾 Banco de Dados de XML")
    
    # Inicializa o gerenciador do banco
    if st.session_state.db_manager is None:
        st.session_state.db_manager = XMLDatabaseManager()
    
    db_manager = st.session_state.db_manager
    
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Importar XML", "🔍 Buscar XML", "📊 Estatísticas", "⚙️ Manutenção"])
    
    with tab1:
        st.header("Importar XML para o Banco de Dados")
        
        uploaded_files = st.file_uploader(
            "Selecione os arquivos XML", 
            type=['xml'], 
            accept_multiple_files=True,
            key=f"db_upload{key_suffix}"
        )
        
        tags = st.text_input("Tags (opcional)", help="Tags para facilitar buscas futuras", 
                           key=f"tags_input{key_suffix}")
        
        if uploaded_files and st.button("💾 Salvar no Banco de Dados", key=f"save_db{key_suffix}"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0
            error_count = 0
            error_messages = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processando {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
                progress_bar.progress((i + 1) / len(uploaded_files))
                
                try:
                    xml_content = uploaded_file.getvalue().decode('utf-8')
                    success, message = db_manager.insert_xml(xml_content, uploaded_file.name, tags)
                    
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        error_messages.append(f"{uploaded_file.name}: {message}")
                        
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"{uploaded_file.name}: {str(e)}")
            
            progress_bar.empty()
            status_text.empty()
            
            st.success(f"""
            **Importação concluída!**  
            ✅ Sucessos: {success_count}  
            ❌ Erros: {error_count}
            """)
            
            if error_messages:
                with st.expander("Ver mensagens de erro"):
                    for msg in error_messages:
                        st.error(msg)
    
    with tab2:
        st.header("Buscar XML no Banco de Dados")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_term = st.text_input("Termo de busca", key=f"search_term{key_suffix}")
        
        with col2:
            search_type = st.selectbox(
                "Tipo de busca",
                ["all", "filename", "nCT", "emitente"],
                key=f"search_type{key_suffix}"
            )
        
        limit = st.slider("Limite de resultados", 10, 500, 100, key=f"limit_slider{key_suffix}")
        
        if st.button("🔍 Buscar", key=f"search_btn{key_suffix}") or search_term:
            results = db_manager.search_xml(search_term, search_type, limit)
            
            if results:
                st.write(f"**{len(results)} arquivos encontrados:**")
                
                # Converter para DataFrame para exibição
                df_results = pd.DataFrame(results, columns=[
                    'ID', 'Filename', 'nCT', 'Emitente', 'Valor', 'Peso', 
                    'Data Emissão', 'Data Importação'
                ])
                
                st.dataframe(df_results, use_container_width=True)
                
                # Seleção para visualização detalhada
                selected_id = st.selectbox("Selecionar XML para detalhes:", 
                                         [f"{r[0]} - {r[1]}" for r in results],
                                         key=f"select_xml{key_suffix}")
                
                if selected_id and st.button("Visualizar XML", key=f"view_xml{key_suffix}"):
                    xml_id = int(selected_id.split(' - ')[0])
                    xml_data = db_manager.get_xml_content(xml_id)
                    if xml_data:
                        st.text_area("Conteúdo XML", xml_data[1], height=300, key=f"xml_content{key_suffix}")
            else:
                st.info("Nenhum arquivo encontrado.")
    
    with tab3:
        st.header("Estatísticas do Banco de Dados")
        
        stats = db_manager.get_database_stats()
        
        if stats:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de Arquivos", stats['total_files'])
            
            with col2:
                size_mb = stats['total_size_bytes'] / (1024 * 1024)
                st.metric("Tamanho Total", f"{size_mb:.2f} MB")
            
            with col3:
                st.metric("Emitentes Únicos", stats['unique_emitters'])
            
            with col4:
                st.metric("Valor Total", f"R$ {stats['total_value']:,.2f}")
            
            col5, col6 = st.columns(2)
            with col5:
                st.metric("Peso Total", f"{stats['total_weight']:,.2f} kg")
            
            # Exportar dados
            st.subheader("Exportar Dados")
            if st.button("📊 Exportar para DataFrame", key=f"export_df{key_suffix}"):
                df = db_manager.export_to_dataframe()
                st.dataframe(df, use_container_width=True)
                
                # Download do DataFrame
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar CSV",
                    data=csv,
                    file_name="dados_cte_banco.csv",
                    mime="text/csv",
                    key=f"download_csv{key_suffix}"
                )
        else:
            st.info("Nenhum dado disponível no banco.")
    
    with tab4:
        st.header("Manutenção do Banco de Dados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Otimizar Banco", key=f"optimize_db{key_suffix}"):
                try:
                    conn = sqlite3.connect(db_manager.db_path)
                    conn.execute("VACUUM")
                    conn.close()
                    st.success("Banco otimizado com sucesso!")
                except Exception as e:
                    st.error(f"Erro: {e}")
            
            if st.button("📋 Informações do Sistema", key=f"system_info{key_suffix}"):
                st.info(f"**Caminho do banco:** {db_manager.db_path}")
                st.info("**Capacidade estimada:** Suporte a 50.000+ XMLs")
                st.info("**Recursos:** Prevenção de duplicatas, Busca indexada")
        
        with col2:
            if st.button("🧹 Limpar Cache da Sessão", key=f"clear_cache{key_suffix}"):
                st.session_state.processed_cte_files = []
                st.session_state.processed_txt_files = []
                st.success("Cache limpo com sucesso!")

# --- PROCESSADOR CT-E ATUALIZADO COM BANCO DE DADOS ---
def processador_cte():
    """Interface para o sistema de CT-e com banco de dados"""
    if st.session_state.db_manager is None:
        st.session_state.db_manager = XMLDatabaseManager()
    
    processor = CTeProcessorWithDB(st.session_state.db_manager)
    
    st.title("🚚 Processador de CT-e com Banco de Dados")
    
    with st.expander("ℹ️ Informações", expanded=True):
        st.markdown("""
        **Funcionalidades:**
        - **Armazenamento permanente** no banco de dados
        - **Prevenção de duplicatas** através de hash MD5
        - **Busca rápida** por múltiplos critérios
        - **Capacidade para 50.000+ XMLs**
        """)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload em Lote", "👀 Visualizar Dados", "📥 Exportar", "💾 Banco"])
    
    with tab1:
        st.header("Upload de Múltiplos CT-es")
        
        uploaded_files = st.file_uploader(
            "Selecione os arquivos XML de CT-e", 
            type=['xml'], 
            accept_multiple_files=True,
            key="cte_multiple_unique"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            save_to_db = st.checkbox("💾 Salvar no banco de dados", value=True, key="save_to_db_cte")
        with col2:
            tags = st.text_input("Tags para organização", value="cte,importado", key="tags_cte")
        
        if uploaded_files:
            st.info(f"📁 **{len(uploaded_files)} arquivo(s) selecionado(s)**")
            
            if st.button("📊 Processar e Salvar CT-es", key="process_cte_unique"):
                show_loading_animation(f"Processando {len(uploaded_files)} arquivos...")
                
                results = processor.process_multiple_files(uploaded_files, save_to_db, tags)
                show_success_animation("Processamento concluído!")
                
                st.success(f"""
                **Processamento concluído!**  
                ✅ Sucessos: {results['success']}  
                ❌ Erros: {results['errors']}
                """)
                
                # Salvar no session state para visualização
                df = processor.get_dataframe()
                if not df.empty:
                    st.session_state.processed_cte_files = df.to_dict('records')
                
                if results['errors'] > 0:
                    with st.expander("Ver mensagens detalhadas"):
                        for msg in results['messages']:
                            st.write(f"- {msg}")
        else:
            st.info("Selecione os arquivos XML de CT-e para processar.")
    
    with tab2:
        st.header("Dados Processados")
        
        # Opção de visualizar do banco ou da sessão
        view_option = st.radio("Fonte dos dados:", 
                              ["Sessão Atual", "Banco de Dados"],
                              key="view_option_cte")
        
        if view_option == "Sessão Atual" and st.session_state.processed_cte_files:
            df = pd.DataFrame(st.session_state.processed_cte_files)
            display_data_interface(df, "sessao")
        elif view_option == "Banco de Dados":
            limit = st.slider("Limite de registros", 10, 1000, 100, key="limit_bd_cte")
            df = st.session_state.db_manager.export_to_dataframe(limit)
            if not df.empty:
                display_data_interface(df, "banco")
            else:
                st.info("Nenhum dado encontrado no banco de dados.")
        else:
            st.info("Nenhum CT-e processado ainda.")
    
    with tab3:
        st.header("Exportar Dados")
        
        export_source = st.radio("Fonte para exportação:", 
                                ["Sessão Atual", "Banco de Dados"],
                                key="export_source_cte")
        
        if export_source == "Sessão Atual" and st.session_state.processed_cte_files:
            df_export = pd.DataFrame(st.session_state.processed_cte_files)
        else:
            df_export = st.session_state.db_manager.export_to_dataframe(1000)
        
        if not df_export.empty:
            st.success(f"📤 Pronto para exportar {len(df_export)} registros")
            
            export_option = st.radio("Formato:", ["Excel (.xlsx)", "CSV (.csv)"], key="export_format_cte")
            
            if export_option == "Excel (.xlsx)":
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, sheet_name='Dados_CTe', index=False)
                output.seek(0)
                
                st.download_button(
                    label="📥 Baixar Excel",
                    data=output,
                    file_name="dados_cte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_cte"
                )
            else:
                csv = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar CSV",
                    data=csv,
                    file_name="dados_cte.csv",
                    mime="text/csv",
                    key="download_csv_cte"
                )
        else:
            st.warning("Nenhum dado disponível para exportação.")
    
    with tab4:
        setup_xml_database_interface("_cte_tab")

def display_data_interface(df, source):
    """Interface para exibição dos dados"""
    st.write(f"📊 **Total de registros:** {len(df)}")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        uf_filter = st.multiselect("Filtrar por UF Início", options=df['UF Início'].unique(), key=f"uf_filter_{source}")
    with col2:
        uf_destino_filter = st.multiselect("Filtrar por UF Destino", options=df['UF Destino'].unique(), key=f"uf_dest_filter_{source}")
    with col3:
        if 'Tipo de Peso Encontrado' in df.columns:
            tipo_peso_filter = st.multiselect("Filtrar por Tipo de Peso", 
                                            options=df['Tipo de Peso Encontrado'].unique(),
                                            key=f"peso_filter_{source}")
    
    # Aplicar filtros
    filtered_df = df.copy()
    if uf_filter:
        filtered_df = filtered_df[filtered_df['UF Início'].isin(uf_filter)]
    if uf_destino_filter:
        filtered_df = filtered_df[filtered_df['UF Destino'].isin(uf_destino_filter)]
    if 'Tipo de Peso Encontrado' in df.columns and 'tipo_peso_filter' in locals():
        filtered_df = filtered_df[filtered_df['Tipo de Peso Encontrado'].isin(tipo_peso_filter)]
    
    # Exibir dados
    st.dataframe(filtered_df, use_container_width=True)
    
    # Estatísticas
    st.subheader("📈 Estatísticas")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Valor Total", f"R$ {filtered_df['Valor Prestação'].sum():,.2f}")
    col2.metric("Peso Total", f"{filtered_df['Peso Bruto (kg)'].sum():,.2f} kg")
    col3.metric("Média Peso", f"{filtered_df['Peso Bruto (kg)'].mean():,.2f} kg")
    col4.metric("Registros", len(filtered_df))

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
        .cover-gif {
            max-width: 200px;
            margin-bottom: 1.5rem;
        }
        .cover-title {
            font-size: 2.8rem;
            font-weight: 800;
            margin-bottom: 1rem;
            background: linear-gradient(90deg, #2c3e50, #3498db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .cover-subtitle {
            font-size: 1.2rem;
            color: #7f8c8d;
            margin-bottom: 0;
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
    
    st.markdown("""
    <div class="cover-container">
        <h1 class="cover-title">Sistema de Processamento com Banco de Dados</h1>
        <p class="cover-subtitle">Processamento ilimitado com armazenamento permanente</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📄 Processador TXT", "🚚 Processador CT-e", "💾 Banco de Dados"])
    
    with tab1:
        processador_txt()
    
    with tab2:
        processador_cte()
    
    with tab3:
        setup_xml_database_interface("_main")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {str(e)}")
        st.code(traceback.format_exc())