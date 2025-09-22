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
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
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

# --- INICIALIZAÇÃO COMPLETA DO SESSION_STATE ---
def initialize_session_state():
    """Inicializa todas as variáveis do session_state"""
    if 'batch_size' not in st.session_state:
        st.session_state.batch_size = 100
    if 'max_workers' not in st.session_state:
        st.session_state.max_workers = min(32, (os.cpu_count() or 1) * 4)
    if 'max_memory_usage' not in st.session_state:
        st.session_state.max_memory_usage = 85
    if 'selected_xml' not in st.session_state:
        st.session_state.selected_xml = None
    if 'cte_data' not in st.session_state:
        st.session_state.cte_data = None
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = set()
    if 'processing_stats' not in st.session_state:
        st.session_state.processing_stats = {'success': 0, 'errors': 0, 'total': 0}
    if 'processor_initialized' not in st.session_state:
        st.session_state.processor_initialized = False

# Inicializa o session_state
initialize_session_state()

# --- MONITORAMENTO DE MEMÓRIA ---
def get_memory_usage():
    """Obtém uso atual de memória"""
    try:
        import psutil
        return psutil.virtual_memory().percent
    except ImportError:
        return 0

def check_memory_limit():
    """Verifica se o uso de memória está dentro do limite"""
    return get_memory_usage() < st.session_state.max_memory_usage

# --- ANIMAÇÕES DE CARREGAMENTO OTIMIZADAS ---
def show_loading_animation(message="Processando...", progress=None):
    """Exibe uma animação de carregamento otimizada"""
    if progress is not None:
        progress.progress(0, text=message)
    else:
        with st.spinner(message):
            time.sleep(0.1)

def show_progress(current, total, progress_bar, message=""):
    """Atualiza barra de progresso"""
    progress = current / total
    progress_bar.progress(progress, text=f"{message} {current}/{total} ({progress:.1%})")

def show_success_animation(message="Concluído!"):
    """Exibe animação de sucesso rápida"""
    success_placeholder = st.empty()
    with success_placeholder.container():
        st.success(f"✅ {message}")
        time.sleep(1)
    success_placeholder.empty()

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
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN"
            }
            
            encoding = detectar_encoding(conteudo)
            
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
        if st.button("🔄 Processar Arquivo TXT"):
            try:
                show_loading_animation("Analisando arquivo TXT...")
                conteudo = arquivo.read()
                show_loading_animation("Processando linhas...")
                resultado, total_linhas = processar_arquivo(conteudo, padroes)
                
                if resultado is not None:
                    show_success_animation("Arquivo processado com sucesso!")
                    
                    linhas_processadas = len(resultado.splitlines())
                    st.success(f"""
                    **Processamento concluído!**  
                    ✔️ Linhas originais: {total_linhas}  
                    ✔️ Linhas processadas: {linhas_processadas}  
                    ✔️ Linhas removidas: {total_linhas - linhas_processadas}
                    """)

                    st.subheader("Prévia do resultado")
                    st.text_area("Conteúdo processado", resultado, height=300)

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

# --- PROCESSADOR CT-E OTIMIZADO PARA GRANDES VOLUMES ---
class CTeProcessorOptimized:
    def __init__(self):
        self.processed_data = []
        self._file_hashes = set()
        st.session_state.processor_initialized = True
    
    def _get_file_hash(self, content):
        """Gera hash único para evitar duplicatas"""
        return hashlib.md5(content).hexdigest()
    
    def _is_duplicate(self, content):
        """Verifica se arquivo já foi processado"""
        file_hash = self._get_file_hash(content)
        if file_hash in st.session_state.processed_files:
            return True
        st.session_state.processed_files.add(file_hash)
        return False
    
    def extract_nfe_number_from_key(self, chave_acesso):
        """Extrai o número da NF-e da chave de acesso"""
        if not chave_acesso or len(chave_acesso) != 44:
            return None
        
        try:
            numero_nfe = chave_acesso[25:34]
            return numero_nfe
        except Exception:
            return None
    
    def extract_peso_bruto(self, root):
        """Extrai o peso bruto do CT-e de forma otimizada"""
        try:
            # Busca direta por elementos infQ
            infQ_elements = []
            
            # Tentativa com namespace
            for uri in CTE_NAMESPACES.values():
                infQ_elements.extend(root.findall(f'.//{{{uri}}}infQ'))
            
            # Tentativa sem namespace
            if not infQ_elements:
                infQ_elements.extend(root.findall('.//infQ'))
            
            for infQ in infQ_elements:
                # Busca direta pelos elementos filhos
                for child in infQ:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if tag == 'tpMed' and child.text == 'PESO BRUTO':
                        # Encontrou o tipo de medida, agora busca o valor
                        for sibling in infQ:
                            sibling_tag = sibling.tag.split('}')[-1] if '}' in sibling.tag else sibling.tag
                            if sibling_tag == 'qCarga' and sibling.text:
                                try:
                                    return float(sibling.text)
                                except (ValueError, TypeError):
                                    return 0.0
            return 0.0
            
        except Exception:
            return 0.0
    
    def extract_cte_data_fast(self, xml_content, filename):
        """Extrai dados do CT-e de forma otimizada"""
        try:
            # Verifica se é CT-e antes de processar
            if b'CTe' not in xml_content and b'conhecimento' not in xml_content.lower():
                return None
            
            # Evita duplicatas
            if self._is_duplicate(xml_content):
                return {'Arquivo': filename, 'Status': 'Duplicado'}
            
            # Parsing otimizado
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError:
                return None
            
            # Dicionário para armazenar dados
            data = {'Arquivo': filename}
            
            # Função de busca otimizada
            def fast_find_text(element, tags):
                """Busca texto de forma eficiente em múltiplas tags"""
                for tag in tags:
                    try:
                        # Tentativa com namespace
                        for uri in CTE_NAMESPACES.values():
                            found = element.find(f'.//{{{uri}}}{tag}')
                            if found is not None and found.text:
                                return found.text
                        
                        # Tentativa sem namespace
                        found = element.find(f'.//{tag}')
                        if found is not None and found.text:
                            return found.text
                    except Exception:
                        continue
                return None
            
            # Extração otimizada dos dados principais
            data['nCT'] = fast_find_text(root, ['nCT']) or 'N/A'
            
            # Data de emissão
            dhEmi = fast_find_text(root, ['dhEmi'])
            if dhEmi:
                try:
                    data['Data Emissão'] = datetime.strptime(dhEmi[:10], '%Y-%m-%d').strftime('%d/%m/%y')
                except:
                    data['Data Emissão'] = dhEmi[:10]
            else:
                data['Data Emissão'] = 'N/A'
            
            # Dados básicos
            data['UF Início'] = fast_find_text(root, ['UFIni']) or 'N/A'
            data['UF Fim'] = fast_find_text(root, ['UFFim']) or 'N/A'
            data['Emitente'] = fast_find_text(root, ['xNome']) or 'N/A'
            data['Remetente'] = fast_find_text(root, ['xNome']) or 'N/A'
            
            # Valor da prestação
            vTPrest = fast_find_text(root, ['vTPrest'])
            try:
                data['Valor Prestação'] = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                data['Valor Prestação'] = 0.0
            
            # Peso bruto
            data['Peso Bruto (kg)'] = self.extract_peso_bruto(root)
            
            # Destinatário
            data['Destinatário'] = fast_find_text(root, ['xNome']) or 'N/A'
            data['UF Destino'] = fast_find_text(root, ['UF']) or 'N/A'
            
            # Chave NFe
            infNFe_chave = fast_find_text(root, ['chave'])
            data['Chave NFe'] = infNFe_chave or 'N/A'
            data['Número NFe'] = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else 'N/A'
            
            data['Data Processamento'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            data['Status'] = 'Sucesso'
            
            return data
            
        except Exception as e:
            return {'Arquivo': filename, 'Status': f'Erro: {str(e)}'}
    
    def process_single_file(self, uploaded_file):
        """Processa um único arquivo XML de CT-e"""
        try:
            file_content = uploaded_file.getvalue()
            filename = uploaded_file.name
            
            if not filename.lower().endswith('.xml'):
                return False, "Arquivo não é XML"
            
            cte_data = self.extract_cte_data_fast(file_content, filename)
            
            if cte_data and cte_data.get('Status') == 'Sucesso':
                self.processed_data.append(cte_data)
                return True, f"CT-e {filename} processado com sucesso!"
            else:
                status = cte_data.get('Status', 'Erro desconhecido') if cte_data else "Erro na extração"
                return False, f"Erro ao processar CT-e {filename}: {status}"
                
        except Exception as e:
            return False, f"Erro ao processar arquivo {filename}: {str(e)}"
    
    def process_batch(self, files_batch):
        """Processa um lote de arquivos"""
        batch_results = {'success': 0, 'errors': 0, 'messages': []}
        
        for uploaded_file in files_batch:
            # Verifica limite de memória
            if not check_memory_limit():
                batch_results['messages'].append("Interrompido: limite de memória atingido")
                break
                
            success, message = self.process_single_file(uploaded_file)
            if success:
                batch_results['success'] += 1
            else:
                batch_results['errors'] += 1
            batch_results['messages'].append(message)
        
        return batch_results
    
    def process_multiple_files_optimized(self, uploaded_files):
        """Processa múltiplos arquivos de forma otimizada"""
        total_files = len(uploaded_files)
        st.session_state.processing_stats = {'success': 0, 'errors': 0, 'total': total_files}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Divide os arquivos em lotes
        batches = [uploaded_files[i:i + st.session_state.batch_size] 
                  for i in range(0, total_files, st.session_state.batch_size)]
        
        total_batches = len(batches)
        
        # Garante que max_workers não seja maior que o número de lotes
        max_workers = min(st.session_state.max_workers, total_batches)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {
                executor.submit(self.process_batch, batch): i 
                for i, batch in enumerate(batches)
            }
            
            completed = 0
            for future in as_completed(future_to_batch):
                batch_num = future_to_batch[future]
                try:
                    batch_results = future.result()
                    
                    # Atualiza estatísticas
                    st.session_state.processing_stats['success'] += batch_results['success']
                    st.session_state.processing_stats['errors'] += batch_results['errors']
                    
                    completed += 1
                    
                    # Atualiza interface
                    show_progress(
                        st.session_state.processing_stats['success'] + st.session_state.processing_stats['errors'],
                        total_files,
                        progress_bar,
                        f"Processando lote {batch_num + 1}/{total_batches}"
                    )
                    
                    # Limpa memória periodicamente
                    if completed % 5 == 0:
                        gc.collect()
                    
                except Exception as e:
                    batch_size = len(batches[batch_num]) if batch_num < len(batches) else 0
                    st.session_state.processing_stats['errors'] += batch_size
                    st.error(f"Erro no lote {batch_num}: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        
        return st.session_state.processing_stats
    
    def get_dataframe(self):
        """Retorna os dados processados como DataFrame otimizado"""
        if self.processed_data:
            df = pd.DataFrame(self.processed_data)
            # Converte colunas numéricas para tipos otimizados
            numeric_cols = ['Valor Prestação', 'Peso Bruto (kg)']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        return pd.DataFrame()
    
    def clear_data(self):
        """Limpa os dados processados"""
        self.processed_data.clear()
        st.session_state.processed_files.clear()
        st.session_state.processing_stats = {'success': 0, 'errors': 0, 'total': 0}
        gc.collect()

# --- FUNÇÃO PARA CRIAR LINHA DE TENDÊNCIA SIMPLES ---
def add_simple_trendline(fig, x, y):
    """Adiciona uma linha de tendência simples usando regressão linear básica"""
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
                x=x_trend, 
                y=y_trend,
                mode='lines',
                name='Linha de Tendência',
                line=dict(color='red', dash='dash'),
                opacity=0.7
            ))
    except Exception:
        pass

# --- INTERFACE OTIMIZADA PARA PROCESSAMENTO DE CT-E ---
def processador_cte():
    """Interface otimizada para o sistema de CT-e"""
    
    # Garante que o session_state está inicializado
    initialize_session_state()
    
    # Inicializa o processador
    if 'processor' not in st.session_state or not st.session_state.processor_initialized:
        st.session_state.processor = CTeProcessorOptimized()
    
    processor = st.session_state.processor
    
    st.title("🚚 Processador de CT-e para Power BI (Otimizado)")
    st.markdown("### Processa grandes volumes de XMLs de CT-e de forma eficiente")
    
    # Informações de performance
    with st.expander("⚡ Informações de Performance", expanded=False):
        st.markdown(f"""
        **Configurações otimizadas para grandes volumes:**
        - Processamento em lotes de {st.session_state.batch_size} arquivos
        - Até {st.session_state.max_workers} threads simultâneas
        - Limite de memória: {st.session_state.max_memory_usage}%
        - Detecção automática de duplicatas
        """)
        
        if st.session_state.processing_stats['total'] > 0:
            st.info(f"""
            **Estatísticas da sessão:**
            - Total processado: {st.session_state.processing_stats['total']}
            - Sucessos: {st.session_state.processing_stats['success']}
            - Erros: {st.session_state.processing_stats['errors']}
            - Uso de memória: {get_memory_usage():.1f}%
            """)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "⚙️ Configurações", "👀 Visualizar", "📥 Exportar"])
    
    with tab1:
        st.header("Upload de CT-es")
        
        # Opções de upload para grandes volumes
        upload_option = st.radio("Selecione o tipo de upload:", 
                                ["Upload em Lote (Recomendado)", "Upload Individual"])
        
        if upload_option == "Upload Individual":
            uploaded_file = st.file_uploader("Selecione um arquivo XML de CT-e", type=['xml'], key="single_cte")
            if uploaded_file and st.button("📊 Processar CT-e", key="process_single"):
                success, message = processor.process_single_file(uploaded_file)
                if success:
                    st.success(message)
                    df = processor.get_dataframe()
                    if not df.empty:
                        st.info(f"**Total processado:** {len(df)} CT-es")
                else:
                    st.error(message)
        
        else:
            # Upload múltiplo otimizado
            st.markdown("**Para grandes volumes (>1000 arquivos):**")
            st.info("💡 **Dica:** Para mais de 1000 arquivos, considere compactar em ZIP")
            
            uploaded_files = st.file_uploader(
                "Selecione múltiplos arquivos XML de CT-e", 
                type=['xml', 'zip'],
                accept_multiple_files=True,
                key="multiple_cte"
            )
            
            if uploaded_files:
                # Separa arquivos ZIP e XML
                xml_files = [f for f in uploaded_files if f.name.lower().endswith('.xml')]
                zip_files = [f for f in uploaded_files if f.name.lower().endswith('.zip')]
                
                # Extrai arquivos ZIP
                for zip_file in zip_files:
                    try:
                        with zipfile.ZipFile(zip_file, 'r') as zf:
                            for file_info in zf.infolist():
                                if file_info.filename.lower().endswith('.xml'):
                                    with zf.open(file_info) as xml_file:
                                        # Cria um objeto similar ao uploaded_file
                                        xml_content = xml_file.read()
                                        virtual_file = BytesIO(xml_content)
                                        virtual_file.name = file_info.filename
                                        xml_files.append(virtual_file)
                    except Exception as e:
                        st.error(f"Erro ao extrair ZIP {zip_file.name}: {str(e)}")
                
                total_files = len(xml_files)
                st.info(f"**Total de arquivos XML encontrados:** {total_files}")
                
                if total_files > 0:
                    if st.button("🚀 Processar em Lote", type="primary"):
                        if total_files > 10000:
                            st.warning(f"⚠️ Processando {total_files} arquivos. Isso pode levar vários minutos.")
                        
                        start_time = time.time()
                        
                        results = processor.process_multiple_files_optimized(xml_files)
                        processing_time = time.time() - start_time
                        
                        success_rate = (results['success'] / total_files * 100) if total_files > 0 else 0
                        
                        st.success(f"""
                        **Processamento concluído em {processing_time:.1f}s!**  
                        ✅ Sucessos: {results['success']} ({success_rate:.1f}%)  
                        ❌ Erros: {results['errors']}  
                        ⚡ Velocidade: {results['success']/max(processing_time, 0.1):.1f} arquivos/segundo
                        """)
                        
                        df = processor.get_dataframe()
                        if not df.empty:
                            peso_total = df['Peso Bruto (kg)'].sum() if 'Peso Bruto (kg)' in df.columns else 0
                            valor_total = df['Valor Prestação'].sum()
                            st.info(f"""
                            **Dados carregados:** 
                            - {len(df)} registros válidos
                            - Peso total: {peso_total:,.2f} kg
                            - Valor total: R$ {valor_total:,.2f}
                            """)
    
    with tab2:
        st.header("Configurações de Performance")
        
        # Configurações ajustáveis
        new_batch_size = st.slider("Tamanho do lote", 50, 500, st.session_state.batch_size, 
                                 help="Número de arquivos processados por lote")
        new_max_workers = st.slider("Número de threads", 1, 32, st.session_state.max_workers,
                                  help="Número de threads simultâneas")
        new_memory_limit = st.slider("Limite de memória (%)", 50, 95, st.session_state.max_memory_usage,
                                   help="Limite máximo de uso de memória")
        
        if st.button("🔄 Aplicar Configurações"):
            st.session_state.batch_size = new_batch_size
            st.session_state.max_workers = new_max_workers
            st.session_state.max_memory_usage = new_memory_limit
            st.success("Configurações aplicadas!")
        
        st.subheader("Gerenciamento de Memória")
        memory_usage = get_memory_usage()
        st.info(f"Uso atual de memória: {memory_usage:.1f}%")
        
        if memory_usage > st.session_state.max_memory_usage:
            st.warning("⚠️ Uso de memória acima do limite recomendado!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Limpar Cache", help="Limpa cache de arquivos processados"):
                processor.clear_data()
                st.success("Cache limpo!")
        with col2:
            if st.button("🔁 Coletar Lixo", help="Força coleta de lixo do Python"):
                gc.collect()
                st.success("Coleta realizada!")
    
    with tab3:
        st.header("Dados Processados")
        df = processor.get_dataframe()
        
        if not df.empty:
            st.write(f"**Total de CT-es válidos:** {len(df)}")
            
            # Filtros otimizados
            col1, col2 = st.columns(2)
            with col1:
                uf_options = df['UF Início'].unique() if 'UF Início' in df.columns else []
                uf_filter = st.multiselect("Filtrar por UF", options=uf_options)
            with col2:
                if 'Peso Bruto (kg)' in df.columns:
                    peso_min = df['Peso Bruto (kg)'].min()
                    peso_max = df['Peso Bruto (kg)'].max()
                    peso_filter = st.slider("Filtrar por Peso Bruto (kg)", float(peso_min), float(peso_max), (float(peso_min), float(peso_max)))
            
            # Aplicar filtros
            filtered_df = df.copy()
            if uf_filter and 'UF Início' in df.columns:
                filtered_df = filtered_df[filtered_df['UF Início'].isin(uf_filter)]
            if 'Peso Bruto (kg)' in df.columns:
                filtered_df = filtered_df[
                    (filtered_df['Peso Bruto (kg)'] >= peso_filter[0]) & 
                    (filtered_df['Peso Bruto (kg)'] <= peso_filter[1])
                ]
            
            # Exibição otimizada
            st.dataframe(filtered_df.head(1000), use_container_width=True)
            
            if len(filtered_df) > 1000:
                st.info(f"Mostrando 1000 de {len(filtered_df)} registros")
            
            # Estatísticas rápidas
            if not filtered_df.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    valor_total = filtered_df['Valor Prestação'].sum() if 'Valor Prestação' in filtered_df.columns else 0
                    st.metric("Valor Total", f"R$ {valor_total:,.0f}")
                with col2:
                    if 'Peso Bruto (kg)' in filtered_df.columns:
                        peso_total = filtered_df['Peso Bruto (kg)'].sum()
                        st.metric("Peso Total", f"{peso_total:,.0f} kg")
                with col3:
                    valor_medio = filtered_df['Valor Prestação'].mean() if 'Valor Prestação' in filtered_df.columns else 0
                    st.metric("Média/CT-e", f"R$ {valor_medio:,.0f}")
        else:
            st.info("Nenhum CT-e processado ainda. Faça upload de arquivos na aba 'Upload'.")
    
    with tab4:
        st.header("Exportar Dados")
        df = processor.get_dataframe()
        
        if not df.empty:
            st.success(f"Pronto para exportar {len(df)} registros")
            
            # Opções de exportação otimizadas
            export_format = st.radio("Formato:", ["Parquet (Recomendado)", "Excel", "CSV"])
            
            if export_format == "Parquet (Recomendado)":
                buffer = BytesIO()
                df.to_parquet(buffer, index=False, compression='snappy')
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Baixar Parquet",
                    data=buffer,
                    file_name="dados_cte.parquet",
                    mime="application/octet-stream"
                )
                st.caption("Parquet é mais rápido e eficiente para grandes volumes")
            
            elif export_format == "Excel":
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='CTes')
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Baixar Excel",
                    data=buffer,
                    file_name="dados_cte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            else:  # CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar CSV",
                    data=csv,
                    file_name="dados_cte.csv",
                    mime="text/csv"
                )
            
            with st.expander("📋 Prévia dos dados a serem exportados"):
                st.dataframe(df.head(10))
                
        else:
            st.warning("Nenhum dado disponível para exportação.")

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
        .cover-subtitle {
            font-size: 1.2rem;
            color: #7f8c8d;
            margin-bottom: 0;
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
        .stButton>button {
            width: 100%;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .spinner {
            animation: spin 2s linear infinite;
            display: inline-block;
            font-size: 24px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- APLICAÇÃO PRINCIPAL ---
def main():
    """Função principal que gerencia o fluxo da aplicação."""
    # Inicializa o session_state
    initialize_session_state()
    
    load_css()
    
    st.markdown("""
    <div class="cover-container">
        <h1 class="cover-title">Sistema de Processamento de XML em Lote</h1>
        <p class="cover-subtitle">Otimizado para processar mais de 50.000 arquivos XML</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📄 Processador TXT", "🚚 Processador CT-e (Otimizado)"])
    
    with tab1:
        processador_txt()
    
    with tab2:
        processador_cte()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {str(e)}")
        st.code(traceback.format_exc())