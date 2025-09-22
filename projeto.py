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
    """Inicializa todas as variáveis do session_state de forma segura"""
    session_vars = {
        'batch_size': 100,
        'max_workers': min(32, (os.cpu_count() or 1) * 4),
        'max_memory_usage': 85,
        'selected_xml': None,
        'cte_data': None,
        'processed_files': set(),
        'processing_stats': {'success': 0, 'errors': 0, 'total': 0},
        'processor_initialized': False
    }
    
    for key, value in session_vars.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Inicializa o session_state antes de qualquer uso
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
    return get_memory_usage() < st.session_state["max_memory_usage"]  # Usar notação de dicionário

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

# --- FUNÇÕES DO PROCESSADOR DE ARQUIVOS ---
def processador_txt():
    st.title("📄 Processador de Arquivos TXT")
    
    def detectar_encoding(conteudo):
        resultado = chardet.detect(conteudo)
        return resultado['encoding']

    def processar_arquivo(conteudo, padroes):
        try:
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN"
            }
            
            encoding = detectar_encoding(conteudo)
            texto = conteudo.decode(encoding)
            
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

    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
    arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'])
    
    with st.expander("⚙️ Configurações avançadas", expanded=False):
        padroes_adicionais = st.text_input("Padrões adicionais para remoção (separados por vírgula)")
        padroes = padroes_default + [p.strip() for p in padroes_adicionais.split(",") if p.strip()] if padroes_adicionais else padroes_default

    if arquivo is not None and st.button("🔄 Processar Arquivo TXT"):
        try:
            conteudo = arquivo.read()
            resultado, total_linhas = processar_arquivo(conteudo, padroes)
            
            if resultado is not None:
                linhas_processadas = len(resultado.splitlines())
                st.success(f"**Processamento concluído!**  \n✔️ Linhas originais: {total_linhas}  \n✔️ Linhas processadas: {linhas_processadas}")
                
                st.text_area("Conteúdo processado", resultado, height=200)
                
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

# --- PROCESSADOR CT-E OTIMIZADO ---
class CTeProcessorOptimized:
    def __init__(self):
        self.processed_data = []
        # Garantir que processed_files está inicializado
        if "processed_files" not in st.session_state:
            st.session_state["processed_files"] = set()
    
    def _get_file_hash(self, content):
        return hashlib.md5(content).hexdigest()
    
    def _is_duplicate(self, content):
        file_hash = self._get_file_hash(content)
        if file_hash in st.session_state["processed_files"]:  # Notação de dicionário
            return True
        st.session_state["processed_files"].add(file_hash)  # Notação de dicionário
        return False
    
    def extract_peso_bruto(self, root):
        try:
            infQ_elements = []
            for uri in CTE_NAMESPACES.values():
                infQ_elements.extend(root.findall(f'.//{{{uri}}}infQ'))
            
            if not infQ_elements:
                infQ_elements.extend(root.findall('.//infQ'))
            
            for infQ in infQ_elements:
                for child in infQ:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if tag == 'tpMed' and child.text == 'PESO BRUTO':
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
        try:
            if b'CTe' not in xml_content and b'conhecimento' not in xml_content.lower():
                return None
            
            if self._is_duplicate(xml_content):
                return {'Arquivo': filename, 'Status': 'Duplicado'}
            
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError:
                return None
            
            data = {'Arquivo': filename}
            
            def fast_find_text(element, tags):
                for tag in tags:
                    try:
                        for uri in CTE_NAMESPACES.values():
                            found = element.find(f'.//{{{uri}}}{tag}')
                            if found is not None and found.text:
                                return found.text
                        found = element.find(f'.//{tag}')
                        if found is not None and found.text:
                            return found.text
                    except Exception:
                        continue
                return None
            
            # Extração de dados (mantida igual)
            data['nCT'] = fast_find_text(root, ['nCT']) or 'N/A'
            
            dhEmi = fast_find_text(root, ['dhEmi'])
            if dhEmi:
                try:
                    data['Data Emissão'] = datetime.strptime(dhEmi[:10], '%Y-%m-%d').strftime('%d/%m/%y')
                except:
                    data['Data Emissão'] = dhEmi[:10]
            else:
                data['Data Emissão'] = 'N/A'
            
            data['UF Início'] = fast_find_text(root, ['UFIni']) or 'N/A'
            data['Valor Prestação'] = float(fast_find_text(root, ['vTPrest']) or 0)
            data['Peso Bruto (kg)'] = self.extract_peso_bruto(root)
            data['Data Processamento'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            data['Status'] = 'Sucesso'
            
            return data
            
        except Exception as e:
            return {'Arquivo': filename, 'Status': f'Erro: {str(e)}'}
    
    def process_batch(self, files_batch):
        batch_results = {'success': 0, 'errors': 0, 'messages': []}
        
        for uploaded_file in files_batch:
            if not check_memory_limit():
                batch_results['messages'].append("Interrompido: limite de memória atingido")
                break
                
            try:
                file_content = uploaded_file.getvalue()
                filename = uploaded_file.name
                
                if not filename.lower().endswith('.xml'):
                    batch_results['errors'] += 1
                    continue
                
                cte_data = self.extract_cte_data_fast(file_content, filename)
                
                if cte_data and cte_data.get('Status') == 'Sucesso':
                    self.processed_data.append(cte_data)
                    batch_results['success'] += 1
                else:
                    batch_results['errors'] += 1
                    
            except Exception as e:
                batch_results['errors'] += 1
        
        return batch_results
    
    def process_multiple_files_optimized(self, uploaded_files):
        total_files = len(uploaded_files)
        st.session_state["processing_stats"] = {'success': 0, 'errors': 0, 'total': total_files}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        batches = [uploaded_files[i:i + st.session_state["batch_size"]] 
                  for i in range(0, total_files, st.session_state["batch_size"])]
        
        total_batches = len(batches)
        max_workers = min(st.session_state["max_workers"], total_batches)
        
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
                    st.session_state["processing_stats"]['success'] += batch_results['success']
                    st.session_state["processing_stats"]['errors'] += batch_results['errors']
                    
                    completed += 1
                    show_progress(
                        st.session_state["processing_stats"]['success'] + st.session_state["processing_stats"]['errors'],
                        total_files,
                        progress_bar,
                        f"Processando lote {batch_num + 1}/{total_batches}"
                    )
                    
                    if completed % 5 == 0:
                        gc.collect()
                    
                except Exception as e:
                    st.error(f"Erro no lote {batch_num}: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        return st.session_state["processing_stats"]
    
    def get_dataframe(self):
        if self.processed_data:
            df = pd.DataFrame(self.processed_data)
            numeric_cols = ['Valor Prestação', 'Peso Bruto (kg)']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        return pd.DataFrame()
    
    def clear_data(self):
        self.processed_data.clear()
        st.session_state["processed_files"].clear()
        st.session_state["processing_stats"] = {'success': 0, 'errors': 0, 'total': 0}
        gc.collect()

# --- INTERFACE PRINCIPAL DO PROCESSADOR CT-E ---
def processador_cte():
    # Reforçar inicialização
    initialize_session_state()
    
    # Inicializar processador no session_state
    if "processor" not in st.session_state:
        st.session_state["processor"] = CTeProcessorOptimized()
    
    processor = st.session_state["processor"]
    
    st.title("🚚 Processador de CT-e para Power BI")
    
    with st.expander("⚡ Informações de Performance", expanded=False):
        st.markdown(f"""
        **Configurações atuais:**
        - Lote: {st.session_state['batch_size']} arquivos
        - Threads: {st.session_state['max_workers']}
        - Memória: {st.session_state['max_memory_usage']}%
        """)
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload", "👀 Visualizar", "📥 Exportar"])
    
    with tab1:
        st.header("Upload de CT-es")
        uploaded_files = st.file_uploader("Selecione arquivos XML", type=['xml', 'zip'], accept_multiple_files=True)
        
        if uploaded_files:
            xml_files = []
            for file in uploaded_files:
                if file.name.lower().endswith('.xml'):
                    xml_files.append(file)
                elif file.name.lower().endswith('.zip'):
                    try:
                        with zipfile.ZipFile(file, 'r') as zf:
                            for file_info in zf.infolist():
                                if file_info.filename.lower().endswith('.xml'):
                                    with zf.open(file_info) as xml_file:
                                        xml_content = xml_file.read()
                                        virtual_file = BytesIO(xml_content)
                                        virtual_file.name = file_info.filename
                                        xml_files.append(virtual_file)
                    except Exception as e:
                        st.error(f"Erro ao extrair ZIP: {str(e)}")
            
            if xml_files and st.button("🚀 Processar Arquivos"):
                results = processor.process_multiple_files_optimized(xml_files)
                st.success(f"**Concluído!** Sucessos: {results['success']}, Erros: {results['errors']}")
    
    with tab2:
        st.header("Configurações")
        
        new_batch_size = st.slider("Tamanho do lote", 50, 500, st.session_state["batch_size"])
        new_max_workers = st.slider("Threads", 1, 32, st.session_state["max_workers"])
        new_memory_limit = st.slider("Limite de memória (%)", 50, 95, st.session_state["max_memory_usage"])
        
        if st.button("🔄 Aplicar Configurações"):
            st.session_state["batch_size"] = new_batch_size
            st.session_state["max_workers"] = new_max_workers
            st.session_state["max_memory_usage"] = new_memory_limit
            st.success("Configurações aplicadas!")
        
        if st.button("🗑️ Limpar Dados"):
            processor.clear_data()
            st.success("Dados limpos!")
    
    with tab3:
        st.header("Dados Processados")
        df = processor.get_dataframe()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.download_button(
                label="📥 Exportar CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name="ctes_processados.csv",
                mime="text/csv"
            )
        else:
            st.info("Nenhum dado processado")

# --- APLICAÇÃO PRINCIPAL ---
def main():
    initialize_session_state()  # Inicialização final
    
    st.markdown("""
    <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ed 100%); border-radius: 12px; margin-bottom: 2rem;'>
        <h1 style='color: #2c3e50;'>Sistema de Processamento de XML</h1>
        <p style='color: #7f8c8d;'>Otimizado para grandes volumes de arquivos</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📄 Processador TXT", "🚚 Processador CT-e"])
    
    with tab1:
        processador_txt()
    
    with tab2:
        processador_cte()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro: {str(e)}")
        st.code(traceback.format_exc())