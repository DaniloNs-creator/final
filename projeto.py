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
import tempfile
import gc
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing
from functools import partial
import psutil
import zipfile

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Sistema de Processamento Massivo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Namespaces para CT-e
CTE_NAMESPACES = {
    'cte': 'http://www.portalfiscal.inf.br/cte'
}

# Configurações para processamento em lote
BATCH_SIZE = 1000  # Processar em lotes de 1000 arquivos
MAX_WORKERS = min(multiprocessing.cpu_count(), 8)  # Limitar número de workers
MEMORY_THRESHOLD = 85  # Percentual de memória para limpar cache

# Inicialização do estado da sessão
if 'processed_batches' not in st.session_state:
    st.session_state.processed_batches = []
if 'total_files' not in st.session_state:
    st.session_state.total_files = 0
if 'current_batch' not in st.session_state:
    st.session_state.current_batch = 0
if 'temp_files' not in st.session_state:
    st.session_state.temp_files = []

# --- MONITORAMENTO DE RECURSOS ---
def get_memory_usage():
    """Retorna o uso de memória em percentual"""
    return psutil.virtual_memory().percent

def cleanup_memory():
    """Limpa memória e força coleta de lixo"""
    gc.collect()
    
def check_memory_limit():
    """Verifica se o uso de memória está acima do limite"""
    return get_memory_usage() > MEMORY_THRESHOLD

# --- GERENCIAMENTO DE ARQUIVOS TEMPORÁRIOS ---
def save_batch_to_temp(batch_data, batch_number):
    """Salva um lote de dados em arquivo temporário"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'_batch_{batch_number}.parquet')
    batch_data.to_parquet(temp_file.name)
    st.session_state.temp_files.append(temp_file.name)
    return temp_file.name

def load_batch_from_temp(temp_file):
    """Carrega um lote de dados do arquivo temporário"""
    return pd.read_parquet(temp_file)

def cleanup_temp_files():
    """Remove todos os arquivos temporários"""
    for temp_file in st.session_state.temp_files:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except:
            pass
    st.session_state.temp_files = []

# --- PROCESSADOR OTIMIZADO PARA GRANDES VOLUMES ---
class OptimizedCTeProcessor:
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        self.current_batch = []
        self.batch_files = []
    
    def extract_nfe_number_from_key(self, chave_acesso):
        """Extrai o número da NF-e da chave de acesso"""
        if not chave_acesso or len(chave_acesso) != 44:
            return None
        try:
            return chave_acesso[25:34]
        except Exception:
            return None
    
    def quick_xml_check(self, content_str):
        """Verificação rápida se é um CT-e válido"""
        return 'CTe' in content_str or 'conhecimento' in content_str.lower()
    
    def extract_peso_bruto(self, root):
        """Extrai o peso bruto do CT-e de forma otimizada"""
        try:
            # Busca direta sem namespaces primeiro (mais rápido)
            infQ_elements = root.findall('.//infQ')
            if not infQ_elements:
                # Busca com namespaces se necessário
                for prefix, uri in CTE_NAMESPACES.items():
                    infQ_elements = root.findall(f'.//{{{uri}}}infQ')
                    if infQ_elements:
                        break
            
            tipos_peso = ['PESO BRUTO', 'PESO BASE DE CALCULO', 'PESO BASE CÁLCULO', 'PESO']
            
            for infQ in infQ_elements:
                # Busca direta pelos elementos filhos
                for child in infQ:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if tag == 'tpMed' and child.text:
                        for tipo_peso in tipos_peso:
                            if tipo_peso in child.text.upper():
                                # Encontra o qCarga correspondente
                                for qchild in infQ:
                                    qtag = qchild.tag.split('}')[-1] if '}' in qchild.tag else qchild.tag
                                    if qtag == 'qCarga' and qchild.text:
                                        try:
                                            peso = float(qchild.text)
                                            return peso, tipo_peso
                                        except ValueError:
                                            continue
            return 0.0, "Não encontrado"
            
        except Exception:
            return 0.0, "Erro na extração"
    
    def parse_xml_fast(self, xml_content):
        """Parsing otimizado de XML"""
        try:
            # Remove declaração XML para parsing mais rápido
            if xml_content.startswith('<?xml'):
                xml_content = xml_content.split('?>', 1)[1]
            return ET.fromstring(xml_content.strip())
        except Exception:
            return None
    
    def extract_cte_data_fast(self, xml_content, filename):
        """Extrai dados do CT-e de forma otimizada"""
        try:
            root = self.parse_xml_fast(xml_content)
            if root is None:
                return None
            
            def find_text_fast(element, tag_name):
                """Busca texto de forma otimizada"""
                # Busca direta
                elem = element.find(tag_name)
                if elem is not None and elem.text:
                    return elem.text
                
                # Busca com namespace se necessário
                for uri in CTE_NAMESPACES.values():
                    ns_tag = f'{{{uri}}}{tag_name}'
                    elem = element.find(ns_tag)
                    if elem is not None and elem.text:
                        return elem.text
                return None
            
            # Extração otimizada dos dados principais
            nCT = find_text_fast(root, 'nCT')
            dhEmi = find_text_fast(root, 'dhEmi')
            UFIni = find_text_fast(root, 'UFIni')
            UFFim = find_text_fast(root, 'UFFim')
            emit_xNome = find_text_fast(root, 'xNome')
            vTPrest = find_text_fast(root, 'vTPrest')
            rem_xNome = find_text_fast(root, 'xNome')  # Será sobrescrito se encontrar no remetente
            
            # Extração do remetente
            rem = root.find('rem') or root.find(f'{{{CTE_NAMESPACES["cte"]}}}rem')
            if rem is not None:
                rem_xNome = find_text_fast(rem, 'xNome') or rem_xNome
            
            # Extração do destinatário
            dest = root.find('dest') or root.find(f'{{{CTE_NAMESPACES["cte"]}}}dest')
            dest_xNome = None
            if dest is not None:
                dest_xNome = find_text_fast(dest, 'xNome')
            
            # Extração do peso
            peso_bruto, tipo_peso = self.extract_peso_bruto(root)
            
            # Formatação otimizada da data
            data_formatada = None
            if dhEmi:
                try:
                    data_obj = datetime.strptime(dhEmi[:10], '%Y-%m-%d')
                    data_formatada = data_obj.strftime('%d/%m/%y')
                except:
                    data_formatada = dhEmi[:10]
            
            # Conversão de valor
            try:
                vTPrest = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                vTPrest = 0.0
            
            return {
                'Arquivo': filename,
                'nCT': nCT or 'N/A',
                'Data Emissão': data_formatada or 'N/A',
                'UF Início': UFIni or 'N/A',
                'UF Fim': UFFim or 'N/A',
                'Emitente': emit_xNome or 'N/A',
                'Valor Prestação': vTPrest,
                'Peso Bruto (kg)': peso_bruto,
                'Tipo de Peso Encontrado': tipo_peso,
                'Remetente': rem_xNome or 'N/A',
                'Destinatário': dest_xNome or 'N/A',
                'Data Processamento': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
        except Exception as e:
            return None
    
    def process_single_file_optimized(self, file_data):
        """Processa um único arquivo de forma otimizada"""
        filename, content = file_data
        try:
            if not self.quick_xml_check(content):
                return None
            
            cte_data = self.extract_cte_data_fast(content, filename)
            return cte_data
            
        except Exception:
            return None
    
    def process_batch_parallel(self, batch_files, progress_callback=None):
        """Processa um lote de arquivos em paralelo"""
        batch_data = []
        
        # Prepara dados para processamento
        file_data_list = []
        for uploaded_file in batch_files:
            try:
                content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
                file_data_list.append((uploaded_file.name, content))
            except Exception:
                continue
        
        # Processamento paralelo
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(self.process_single_file_optimized, file_data) 
                      for file_data in file_data_list]
            
            for i, future in enumerate(as_completed(futures)):
                if progress_callback:
                    progress_callback(i + 1, len(futures))
                
                result = future.result()
                if result:
                    batch_data.append(result)
        
        return batch_data
    
    def process_large_volume(self, uploaded_files, progress_callback=None, batch_callback=None):
        """Processa grandes volumes de arquivos em lotes"""
        total_files = len(uploaded_files)
        batches = [uploaded_files[i:i + BATCH_SIZE] 
                  for i in range(0, total_files, BATCH_SIZE)]
        
        all_results = []
        
        for batch_num, batch_files in enumerate(batches):
            if progress_callback:
                progress_callback(f"Processando lote {batch_num + 1}/{len(batches)}")
            
            # Processa o lote atual
            batch_results = self.process_batch_parallel(
                batch_files, 
                lambda current, total: progress_callback(f"Lote {batch_num + 1}: {current}/{total}")
            )
            
            # Converte para DataFrame e salva temporariamente
            if batch_results:
                batch_df = pd.DataFrame(batch_results)
                temp_file = save_batch_to_temp(batch_df, batch_num)
                all_results.append(temp_file)
                
                # Limpa memória
                del batch_results, batch_df
                cleanup_memory()
            
            if batch_callback:
                batch_callback(batch_num + 1, len(batches))
        
        return all_results

# --- INTERFACE OTIMIZADA ---
def show_optimized_loading(message, progress=None):
    """Exibe loading otimizado"""
    placeholder = st.empty()
    with placeholder.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            if progress is not None:
                st.info(f"⏳ {message} - {progress}%")
                st.progress(progress / 100)
            else:
                st.info(f"⏳ {message}")
    return placeholder

def processador_cte_optimizado():
    """Interface otimizada para processamento massivo"""
    processor = OptimizedCTeProcessor()
    
    st.title("🚚 Processador de CT-e para Grandes Volumes")
    st.markdown("### Processa mais de 50.000 arquivos XML de CT-e de forma eficiente")
    
    # Informações do sistema
    with st.expander("ℹ️ Informações do Sistema", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("CPU Cores", multiprocessing.cpu_count())
        with col2:
            st.metric("Memória Livre", f"{100 - get_memory_usage():.1f}%")
        with col3:
            st.metric("Tamanho do Lote", BATCH_SIZE)
    
    # Upload de arquivos
    st.header("📤 Upload de Arquivos")
    
    upload_option = st.radio("Selecione o método de upload:", 
                           ["Upload Direto", "Upload via ZIP"])
    
    if upload_option == "Upload Direto":
        uploaded_files = st.file_uploader(
            "Selecione os arquivos XML de CT-e", 
            type=['xml'], 
            accept_multiple_files=True,
            key="mass_upload"
        )
    else:
        zip_file = st.file_uploader("Selecione arquivo ZIP com XMLs", type=['zip'])
        uploaded_files = []
        
        if zip_file:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Lista arquivos XML extraídos
                xml_files = list(Path(temp_dir).rglob("*.xml"))
                if xml_files:
                    st.info(f"Encontrados {len(xml_files)} arquivos XML no ZIP")
                    
                    # Cria file-like objects para os arquivos extraídos
                    for xml_file in xml_files:
                        try:
                            with open(xml_file, 'rb') as f:
                                file_data = f.read()
                            
                            # Cria um UploadedFile simulado
                            class SimulatedUploadedFile:
                                def __init__(self, name, data):
                                    self.name = name
                                    self._data = data
                                
                                def getvalue(self):
                                    return self._data
                            
                            simulated_file = SimulatedUploadedFile(xml_file.name, file_data)
                            uploaded_files.append(simulated_file)
                        except Exception as e:
                            st.error(f"Erro ao processar {xml_file.name}: {str(e)}")
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} arquivos prontos para processamento")
        
        # Configurações de processamento
        with st.expander("⚙️ Configurações Avançadas"):
            global BATCH_SIZE, MAX_WORKERS
            BATCH_SIZE = st.slider("Tamanho do lote", 100, 5000, BATCH_SIZE)
            MAX_WORKERS = st.slider("Número de processos paralelos", 1, 16, MAX_WORKERS)
        
        if st.button("🚀 Iniciar Processamento Massivo", type="primary"):
            # Interface de progresso
            progress_placeholder = st.empty()
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_placeholder = st.empty()
            
            def update_progress(message, progress=None):
                with progress_placeholder.container():
                    if progress is not None:
                        st.info(f"⏳ {message} - {progress}%")
                        progress_bar.progress(progress / 100)
                    else:
                        st.info(f"⏳ {message}")
                status_text.text(message)
            
            try:
                # Processamento em lotes
                total_files = len(uploaded_files)
                batches = list(range(0, total_files, BATCH_SIZE))
                
                all_batch_files = []
                
                for i, start_idx in enumerate(batches):
                    end_idx = min(start_idx + BATCH_SIZE, total_files)
                    batch_files = uploaded_files[start_idx:end_idx]
                    
                    progress_pct = (i * 100) // len(batches)
                    update_progress(f"Processando lote {i+1}/{len(batches)}", progress_pct)
                    
                    # Processa o lote atual
                    batch_results = processor.process_batch_parallel(
                        batch_files,
                        lambda current, total: update_progress(
                            f"Lote {i+1}: {current}/{len(batch_files)} arquivos"
                        )
                    )
                    
                    if batch_results:
                        batch_df = pd.DataFrame(batch_results)
                        temp_file = save_batch_to_temp(batch_df, i)
                        all_batch_files.append(temp_file)
                        
                        # Atualiza resultados parciais
                        with results_placeholder.container():
                            st.success(f"✅ Lote {i+1} processado: {len(batch_results)} arquivos")
                    
                    # Limpeza de memória
                    cleanup_memory()
                
                # Consolida resultados finais
                update_progress("Consolidando resultados...", 95)
                
                if all_batch_files:
                    # Carrega todos os lotes
                    final_dfs = []
                    for temp_file in all_batch_files:
                        final_dfs.append(load_batch_from_temp(temp_file))
                    
                    final_df = pd.concat(final_dfs, ignore_index=True)
                    
                    update_progress("Processamento concluído!", 100)
                    
                    # Exibe estatísticas
                    st.balloons()
                    st.success(f"""
                    **Processamento massivo concluído!**
                    - ✅ Arquivos processados: {len(final_df)}
                    - ❌ Arquivos com erro: {total_files - len(final_df)}
                    - ⏱️ Tempo total: {time.strftime('%H:%M:%S', time.gmtime(time.time() - start_time))}
                    """)
                    
                    # Salva DataFrame final na sessão
                    st.session_state.final_df = final_df
                    st.session_state.processed_count = len(final_df)
                    
                else:
                    st.error("Nenhum arquivo foi processado com sucesso.")
                    
            except Exception as e:
                st.error(f"Erro durante o processamento: {str(e)}")
                st.code(traceback.format_exc())
            
            finally:
                # Limpeza final
                cleanup_temp_files()
                cleanup_memory()
    
    # Visualização de dados
    if hasattr(st.session_state, 'final_df') and st.session_state.final_df is not None:
        st.header("📊 Dados Processados")
        
        df = st.session_state.final_df
        st.write(f"Total de CT-es processados: {len(df)}")
        
        # Filtros simplificados para performance
        col1, col2 = st.columns(2)
        with col1:
            uf_filter = st.multiselect("Filtrar por UF Início", options=df['UF Início'].unique())
        with col2:
            tipo_peso_filter = st.multiselect("Filtrar por Tipo de Peso", options=df['Tipo de Peso Encontrado'].unique())
        
        # Aplica filtros
        filtered_df = df.copy()
        if uf_filter:
            filtered_df = filtered_df[filtered_df['UF Início'].isin(uf_filter)]
        if tipo_peso_filter:
            filtered_df = filtered_df[filtered_df['Tipo de Peso Encontrado'].isin(tipo_peso_filter)]
        
        # Exibe dados com paginação
        st.dataframe(filtered_df.head(1000), use_container_width=True)  # Limita a 1000 registros para performance
        
        # Estatísticas
        st.subheader("📈 Estatísticas Resumidas")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Valor", f"R$ {filtered_df['Valor Prestação'].sum():,.0f}")
        col2.metric("Peso Total", f"{filtered_df['Peso Bruto (kg)'].sum():,.0f} kg")
        col3.metric("Média Peso", f"{filtered_df['Peso Bruto (kg)'].mean():,.0f} kg")
        col4.metric("CT-es Válidos", len(filtered_df))
        
        # Exportação
        st.header("📥 Exportar Dados")
        
        if st.button("💾 Exportar para Parquet (Recomendado)"):
            buffer = BytesIO()
            filtered_df.to_parquet(buffer)
            buffer.seek(0)
            
            st.download_button(
                label="⬇️ Baixar Parquet",
                data=buffer,
                file_name="cte_massivo.parquet",
                mime="application/octet-stream"
            )
        
        if st.button("📊 Exportar para Excel (Limite: 50k linhas)"):
            if len(filtered_df) <= 50000:
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    filtered_df.to_excel(writer, index=False)
                buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Baixar Excel",
                    data=buffer,
                    file_name="cte_massivo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("Excel suporta apenas até 50.000 linhas. Use exportação Parquet.")

# --- CSS OTIMIZADO ---
def load_optimized_css():
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(90deg, #2c3e50, #3498db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin: 1rem 0;
        }
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 0.5rem 0;
        }
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
        }
        .success-metric {
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
        }
        .warning-metric {
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
        }
    </style>
    """, unsafe_allow_html=True)

# --- APLICAÇÃO PRINCIPAL OTIMIZADA ---
def main_optimized():
    """Função principal otimizada"""
    load_optimized_css()
    
    st.markdown('<div class="main-header">Sistema de Processamento Massivo de CT-e</div>', 
                unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; color: #666; margin-bottom: 2rem;'>
        Processe mais de 50.000 arquivos XML de CT-e com eficiência máxima
    </div>
    """, unsafe_allow_html=True)
    
    # Verifica memória disponível
    mem_usage = get_memory_usage()
    if mem_usage > 90:
        st.warning(f"⚠️ Uso de memória elevado ({mem_usage}%). Considere fechar outras aplicações.")
    
    processador_cte_optimizado()
    
    # Limpeza ao finalizar
    if st.button("🧹 Limpar Cache e Sair"):
        cleanup_temp_files()
        cleanup_memory()
        st.success("Cache limpo com sucesso!")
        time.sleep(2)
        st.rerun()

if __name__ == "__main__":
    try:
        # Variável global para tempo inicial
        start_time = time.time()
        main_optimized()
    except Exception as e:
        st.error(f"Erro crítico: {str(e)}")
        st.code(traceback.format_exc())
    finally:
        # Garante limpeza ao sair
        cleanup_temp_files()