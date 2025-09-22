import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
import time
import xml.etree.ElementTree as ET
import traceback
import numpy as np
import os
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import zipfile
import threading
from threading import Lock
import json

# --- INICIALIZAÇÃO COMPLETA DO SESSION STATE ---
def initialize_session_state():
    """Inicializa todas as variáveis do session state"""
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = {
            'processed': 0, 
            'total': 0, 
            'errors': 0, 
            'current_file': '',
            'is_processing': False
        }
    
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = []
    
    if 'processing_lock' not in st.session_state:
        st.session_state.processing_lock = Lock()
    
    if 'stop_processing' not in st.session_state:
        st.session_state.stop_processing = False
    
    if 'current_batch' not in st.session_state:
        st.session_state.current_batch = 0
    
    if 'total_batches' not in st.session_state:
        st.session_state.total_batches = 0

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Sistema de Processamento Massivo",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar session state
initialize_session_state()

# Namespaces para CT-e
CTE_NAMESPACES = {'cte': 'http://www.portalfiscal.inf.br/cte'}

# --- SISTEMA DE CACHE E ARMAZENAMENTO OTIMIZADO ---
class CTEProcessorOptimized:
    def __init__(self):
        self.batch_size = 500  # Reduzido para melhor estabilidade
        self.max_workers = 2   # Reduzido para evitar sobrecarga
        self.chunk_size = 100
    
    def extract_nfe_number_from_key(self, chave_acesso):
        """Extrai o número da NF-e da chave de acesso"""
        if not chave_acesso or len(chave_acesso) != 44:
            return None
        try:
            return chave_acesso[25:34]
        except Exception:
            return None
    
    def extract_peso_bruto(self, root):
        """Extrai o peso bruto do CT-e - BUSCA EM MÚLTIPLOS CAMPOS"""
        try:
            tipos_peso = ['PESO BRUTO', 'PESO BASE DE CALCULO', 'PESO BASE CÁLCULO', 'PESO']
            
            # Busca com namespace
            for prefix, uri in CTE_NAMESPACES.items():
                infQ_elements = root.findall(f'.//{{{uri}}}infQ')
                for infQ in infQ_elements:
                    tpMed = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
                    
                    if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                        for tipo_peso in tipos_peso:
                            if tipo_peso in tpMed.text.upper():
                                return float(qCarga.text), tipo_peso
            
            # Busca sem namespace
            infQ_elements = root.findall('.//infQ')
            for infQ in infQ_elements:
                tpMed = infQ.find('tpMed')
                qCarga = infQ.find('qCarga')
                
                if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                    for tipo_peso in tipos_peso:
                        if tipo_peso in tpMed.text.upper():
                            return float(qCarga.text), tipo_peso
            
            return 0.0, "Não encontrado"
            
        except Exception:
            return 0.0, "Erro na extração"
    
    def extract_cte_data_fast(self, xml_content, filename):
        """Extrai dados do CT-e de forma otimizada"""
        try:
            # Parse rápido do XML
            root = ET.fromstring(xml_content)
            
            # Função auxiliar otimizada
            def find_text_fast(element, tag_name):
                try:
                    # Tentar com namespace primeiro
                    for prefix, uri in CTE_NAMESPACES.items():
                        found = element.find(f'.//{{{uri}}}{tag_name}')
                        if found is not None and found.text:
                            return found.text
                    # Tentar sem namespace
                    found = element.find(f'.//{tag_name}')
                    return found.text if found is not None and found.text else None
                except Exception:
                    return None
            
            # Extração otimizada dos dados
            nCT = find_text_fast(root, 'nCT')
            dhEmi = find_text_fast(root, 'dhEmi')
            emit_xNome = find_text_fast(root, 'xNome')  # Buscar em qualquer nível
            vTPrest = find_text_fast(root, 'vTPrest')
            rem_xNome = find_text_fast(root, 'xNome')  # Buscar remetente
            dest_xNome = find_text_fast(root, 'xNome')  # Buscar destinatário
            UFIni = find_text_fast(root, 'UFIni')
            UFFim = find_text_fast(root, 'UFFim')
            infNFe_chave = find_text_fast(root, 'chave')
            
            # Buscar mais específico para emitente, remetente, destinatário
            if not emit_xNome:
                emit_xNome = find_text_fast(root, 'emit/xNome')
            if not rem_xNome:
                rem_xNome = find_text_fast(root, 'rem/xNome')
            if not dest_xNome:
                dest_xNome = find_text_fast(root, 'dest/xNome')
            
            # Buscar CNPJ/CPF do destinatário
            dest_CNPJ = find_text_fast(root, 'dest/CNPJ')
            dest_CPF = find_text_fast(root, 'dest/CPF')
            
            # Extrai peso
            peso_bruto, tipo_peso = self.extract_peso_bruto(root)
            
            # Formatação otimizada da data
            data_formatada = None
            if dhEmi:
                try:
                    data_obj = datetime.strptime(dhEmi[:10], '%Y-%m-%d')
                    data_formatada = data_obj.strftime('%d/%m/%y')
                except:
                    try:
                        data_obj = datetime.strptime(dhEmi[:10], '%d/%m/%Y')
                        data_formatada = data_obj.strftime('%d/%m/%y')
                    except:
                        data_formatada = dhEmi[:10]
            
            # Conversão de valores
            try:
                vTPrest = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                vTPrest = 0.0
            
            documento_destinatario = dest_CNPJ or dest_CPF or 'N/A'
            numero_nfe = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            
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
                'Documento Destinatário': documento_destinatario,
                'Chave NFe': infNFe_chave or 'N/A',
                'Número NFe': numero_nfe or 'N/A',
                'Data Processamento': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
        except Exception as e:
            return {'error': f"Erro no arquivo {filename}: {str(e)}"}
    
    def process_single_file(self, file_content, filename):
        """Processa um único arquivo com verificação de parada"""
        try:
            # Verificar se o processamento foi interrompido
            if st.session_state.stop_processing:
                return {'error': 'Processamento interrompido pelo usuário'}
                
            content_str = file_content.decode('utf-8', errors='ignore')
            if 'CTe' not in content_str and 'conhecimento' not in content_str.lower():
                return {'error': f'Arquivo {filename} não é um CT-e válido'}
            
            return self.extract_cte_data_fast(content_str, filename)
            
        except Exception as e:
            return {'error': f'Erro ao processar {filename}: {str(e)}'}

# --- SISTEMA DE PROGRESSO E STATUS ---
def update_progress(current, total, current_file="", errors=0, is_processing=False):
    """Atualiza a barra de progresso e status de forma segura"""
    try:
        st.session_state.processing_status = {
            'processed': current,
            'total': total,
            'errors': errors,
            'current_file': current_file,
            'is_processing': is_processing
        }
    except Exception as e:
        print(f"Erro ao atualizar progresso: {e}")

def get_progress_status():
    """Retorna o status atual do processamento de forma segura"""
    try:
        return st.session_state.processing_status.copy()
    except Exception as e:
        print(f"Erro ao obter status: {e}")
        return {'processed': 0, 'total': 0, 'errors': 0, 'current_file': '', 'is_processing': False}

def reset_processing_state():
    """Reseta o estado de processamento"""
    initialize_session_state()
    st.session_state.stop_processing = False
    st.session_state.processing_status['is_processing'] = False

def show_progress_interface():
    """Exibe a interface de progresso de forma segura"""
    try:
        status = get_progress_status()
        
        if status['total'] > 0:
            progress = status['processed'] / status['total'] if status['total'] > 0 else 0
            
            # Barra de progresso principal
            progress_bar = st.progress(float(progress))
            
            # Estatísticas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Processados", f"{status['processed']:,}")
            with col2:
                st.metric("Total", f"{status['total']:,}")
            with col3:
                st.metric("Erros", f"{status['errors']:,}")
            with col4:
                success_rate = (status['processed'] - status['errors']) / status['processed'] * 100 if status['processed'] > 0 else 0
                st.metric("Sucesso", f"{success_rate:.1f}%")
            
            # Arquivo atual
            if status['current_file']:
                st.info(f"📄 Processando: {os.path.basename(status['current_file'])}")
            
            # Botão de parada
            if status['is_processing']:
                if st.button("🛑 Parar Processamento", key="stop_button", type="secondary"):
                    st.session_state.stop_processing = True
                    st.warning("Parando processamento... Aguarde a conclusão do lote atual.")
            
            return progress_bar
        return None
    except Exception as e:
        st.error(f"Erro na interface de progresso: {e}")
        return None

# --- PROCESSAMENTO EM MASSA SEGURO ---
def process_batch_safe(processor, batch_files, batch_number, total_batches):
    """Processa um lote de arquivos de forma segura"""
    results = []
    errors = []
    
    try:
        with ThreadPoolExecutor(max_workers=processor.max_workers) as executor:
            future_to_file = {
                executor.submit(processor.process_single_file, file_data, filename): filename 
                for file_data, filename in batch_files
            }
            
            for i, future in enumerate(as_completed(future_to_file)):
                filename = future_to_file[future]
                
                # Verificar parada a cada arquivo
                if st.session_state.stop_processing:
                    break
                
                try:
                    result = future.result(timeout=30)
                    if 'error' not in result:
                        results.append(result)
                    else:
                        errors.append(result['error'])
                except Exception as e:
                    errors.append(f"Timeout ou erro em {filename}: {str(e)}")
                
                # Atualizar progresso a cada 10 arquivos
                if i % 10 == 0:
                    current_processed = batch_number * processor.batch_size + i + 1
                    update_progress(
                        current_processed, 
                        st.session_state.processing_status['total'],
                        filename,
                        len(errors),
                        True
                    )
    
    except Exception as e:
        errors.append(f"Erro no lote {batch_number}: {str(e)}")
    
    return results, errors

def process_large_volume_safe(uploaded_files):
    """Processa um grande volume de arquivos XML de forma segura"""
    try:
        processor = CTEProcessorOptimized()
        total_files = len(uploaded_files)
        
        # Configuração inicial segura
        reset_processing_state()
        update_progress(0, total_files, "Iniciando...", 0, True)
        
        # Container para resultados
        all_results = []
        all_errors = []
        
        # Dividir arquivos em lotes
        batches = []
        for i in range(0, total_files, processor.batch_size):
            batch = []
            for j in range(i, min(i + processor.batch_size, total_files)):
                file = uploaded_files[j]
                batch.append((file.getvalue(), file.name))
            batches.append(batch)
        
        st.session_state.total_batches = len(batches)
        
        # Processar lotes
        for batch_num, batch_files in enumerate(batches):
            if st.session_state.stop_processing:
                st.error("Processamento interrompido pelo usuário")
                break
            
            # Atualizar status do lote
            st.session_state.current_batch = batch_num + 1
            update_progress(
                batch_num * processor.batch_size, 
                total_files, 
                f"Lote {batch_num + 1}/{len(batches)}",
                len(all_errors),
                True
            )
            
            # Processar lote
            results, errors = process_batch_safe(processor, batch_files, batch_num, len(batches))
            all_results.extend(results)
            all_errors.extend(errors)
            
            # Limpar memória
            gc.collect()
            
            # Pequena pausa para não sobrecarregar
            time.sleep(0.5)
            
            # Atualizar progresso final do lote
            current_processed = min((batch_num + 1) * processor.batch_size, total_files)
            update_progress(
                current_processed, 
                total_files, 
                f"Lote {batch_num + 1}/{len(batches)} concluído",
                len(all_errors),
                batch_num < len(batches) - 1  # Último lote?
            )
        
        # Finalizar processamento
        update_progress(total_files, total_files, "Processamento concluído", len(all_errors), False)
        st.session_state.stop_processing = False
        
        return all_results, all_errors
        
    except Exception as e:
        st.error(f"Erro crítico no processamento: {str(e)}")
        update_progress(0, total_files, "Erro crítico", len(all_errors), False)
        return [], [f"Erro crítico: {str(e)}"]

# --- INTERFACE PRINCIPAL SEGURA ---
def processador_cte_massivo():
    """Interface segura para processamento massivo de CT-es"""
    
    st.title("⚡ Processador Massivo de CT-e")
    st.markdown("### Sistema otimizado para grandes volumes de arquivos XML")
    
    # Verificar se há processamento em andamento
    status = get_progress_status()
    if status['is_processing'] and status['processed'] < status['total']:
        st.warning("🔄 Processamento em andamento...")
        show_progress_interface()
        return
    
    # Informações de performance
    with st.expander("🚀 Informações do Sistema", expanded=True):
        st.markdown("""
        **Capacidades:**
        - ✅ **Processamento em lote**: Grupos de 500 arquivos
        - ✅ **Processamento paralelo**: Até 2 arquivos simultaneamente  
        - ✅ **Controle de progresso**: Monitoramento em tempo real
        - ✅ **Interrupção segura**: Pare a qualquer momento
        - ✅ **Busca inteligente**: Peso bruto e base de cálculo
        
        **Limites recomendados:**
        - 📦 **Por lote**: Até 5.000 arquivos
        - ⏱️ **Tempo estimado**: 1.000 arquivos ≈ 2-3 minutos
        - 💾 **Memória**: Processamento eficiente
        """)
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload", "📊 Dashboard", "📥 Exportar"])
    
    with tab1:
        show_upload_interface()
    
    with tab2:
        show_dashboard_interface()
    
    with tab3:
        show_export_interface()

def show_upload_interface():
    """Interface de upload segura"""
    st.header("Upload de Arquivos XML")
    
    uploaded_files = st.file_uploader(
        "Selecione os arquivos XML de CT-e", 
        type=['xml'], 
        accept_multiple_files=True,
        key="mass_upload",
        help="Selecione até 10.000 arquivos por vez para melhor performance"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files):,} arquivos selecionados")
        
        # Verificar limites
        if len(uploaded_files) > 10000:
            st.warning("""
            ⚠️ **Número elevado de arquivos**
            Para melhor performance, recomendamos processar até 10.000 arquivos por vez.
            """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Iniciar Processamento", type="primary", use_container_width=True):
                if len(uploaded_files) > 50000:
                    st.error("❌ **Limite máximo excedido** - Máximo: 50.000 arquivos")
                else:
                    process_uploaded_files_safe(uploaded_files)
        
        with col2:
            if st.button("🔄 Reiniciar Sistema", type="secondary", use_container_width=True):
                reset_processing_state()
                st.rerun()

def process_uploaded_files_safe(uploaded_files):
    """Processa arquivos uploadados de forma segura"""
    try:
        # Container de progresso
        progress_placeholder = st.empty()
        
        with progress_placeholder.container():
            st.subheader("📈 Progresso do Processamento")
            progress_bar = show_progress_interface()
            
            # Processar arquivos
            with st.spinner("Iniciando processamento..."):
                results, errors = process_large_volume_safe(uploaded_files)
            
            # Resultados finais
            st.success(f"""
            **Processamento Concluído!**
            - ✅ Arquivos processados com sucesso: {len(results):,}
            - ❌ Erros encontrados: {len(errors):,}
            - 📊 Taxa de sucesso: {(len(results)/len(uploaded_files))*100:.1f}%
            """)
            
            # Salvar resultados
            st.session_state.processed_data = results
            
            # Mostrar erros se houver
            if errors:
                with st.expander("📋 Detalhes dos Erros (Primeiros 50)"):
                    for error in errors[:50]:
                        st.error(error)
                    if len(errors) > 50:
                        st.info(f"... e mais {len(errors) - 50} erros")
            
            # Limpar memória
            gc.collect()
            
    except Exception as e:
        st.error(f"Erro durante o processamento: {str(e)}")
        st.code(traceback.format_exc())

def show_dashboard_interface():
    """Dashboard seguro para dados processados"""
    if not st.session_state.processed_data:
        st.info("💡 Nenhum dado processado ainda. Faça upload de arquivos XML na aba 'Upload'.")
        return
    
    df = pd.DataFrame(st.session_state.processed_data)
    st.success(f"📊 Dashboard - {len(df):,} registros carregados")
    
    # Filtros rápidos
    col1, col2, col3 = st.columns(3)
    with col1:
        uf_options = [uf for uf in df['UF Início'].unique() if uf != 'N/A']
        uf_filter = st.multiselect("Filtrar por UF", options=uf_options)
    with col2:
        tipo_options = [tipo for tipo in df['Tipo de Peso Encontrado'].unique() if tipo != 'N/A']
        tipo_peso_filter = st.multiselect("Filtrar por Tipo de Peso", options=tipo_options)
    with col3:
        # Amostragem para grandes volumes
        if len(df) > 10000:
            sample_size = st.slider("Amostra para gráficos", 1000, 10000, 5000)
            df_display = df.sample(min(sample_size, len(df)))
        else:
            df_display = df
    
    # Aplicar filtros
    if uf_filter:
        df_display = df_display[df_display['UF Início'].isin(uf_filter)]
    if tipo_peso_filter:
        df_display = df_display[df_display['Tipo de Peso Encontrado'].isin(tipo_peso_filter)]
    
    # Métricas
    st.subheader("📈 Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor Total", f"R$ {df_display['Valor Prestação'].sum():,.0f}")
    col2.metric("Peso Total", f"{df_display['Peso Bruto (kg)'].sum():,.0f} kg")
    col3.metric("CT-es com NFe", f"{df_display[df_display['Chave NFe'] != 'N/A'].shape[0]:,}")
    col4.metric("Tipos de Peso", df_display['Tipo de Peso Encontrado'].nunique())
    
    # Gráficos
    if len(df_display) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de distribuição por UF
            uf_counts = df_display['UF Início'].value_counts().head(10)
            if len(uf_counts) > 0:
                fig_uf = px.bar(uf_counts, x=uf_counts.values, y=uf_counts.index, 
                               orientation='h', title="Top 10 UFs")
                st.plotly_chart(fig_uf, use_container_width=True)
        
        with col2:
            # Gráfico de tipos de peso
            tipo_counts = df_display['Tipo de Peso Encontrado'].value_counts()
            if len(tipo_counts) > 0:
                fig_tipo = px.pie(tipo_counts, values=tipo_counts.values, 
                                 names=tipo_counts.index, title="Distribuição por Tipo de Peso")
                st.plotly_chart(fig_tipo, use_container_width=True)
        
        # Tabela de preview
        with st.expander("📋 Visualizar Dados (Primeiras 100 linhas)"):
            st.dataframe(df_display.head(100), use_container_width=True)

def show_export_interface():
    """Interface de exportação segura"""
    if not st.session_state.processed_data:
        st.info("💡 Nenhum dado para exportar. Processe alguns arquivos primeiro.")
        return
    
    df = pd.DataFrame(st.session_state.processed_data)
    st.success(f"📥 Exportar {len(df):,} registros")
    
    # Opções de exportação
    export_option = st.radio("Formato de exportação:", 
                           ["CSV (.csv) - Recomendado para grandes volumes", 
                            "Excel (.xlsx) - Até 100.000 registros"])
    
    # Seleção de colunas
    st.subheader("Selecionar Colunas para Exportação")
    todas_colunas = df.columns.tolist()
    colunas_principais = [col for col in todas_colunas if col not in ['Data Processamento', 'Documento Destinatário']]
    
    colunas_selecionadas = st.multiselect(
        "Selecione as colunas para exportar:",
        options=todas_colunas,
        default=colunas_principais
    )
    
    if colunas_selecionadas and st.button("💾 Gerar Arquivo de Exportação", type="primary"):
        df_export = df[colunas_selecionadas]
        
        with st.spinner("Gerando arquivo de exportação..."):
            try:
                if export_option.startswith("CSV"):
                    csv_data = df_export.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"📥 Baixar CSV ({len(df_export):,} registros)",
                        data=csv_data,
                        file_name="dados_cte_massivo.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_export.to_excel(writer, sheet_name='Dados_CTe', index=False)
                    output.seek(0)
                    
                    st.download_button(
                        label=f"📥 Baixar Excel ({len(df_export):,} registros)",
                        data=output,
                        file_name="dados_cte_massivo.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
            except Exception as e:
                st.error(f"Erro na exportação: {str(e)}")

# --- CSS ---
def load_css():
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 800;
            text-align: center;
            margin: 1rem 0;
            background: linear-gradient(90deg, #2c3e50, #3498db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stButton>button {
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

# --- APLICAÇÃO PRINCIPAL ---
def main():
    """Função principal com tratamento seguro de erros"""
    try:
        # Garantir que o session state está inicializado
        initialize_session_state()
        
        load_css()
        
        st.markdown('<div class="main-header">⚡ Sistema de Processamento Massivo de CT-e</div>', 
                    unsafe_allow_html=True)
        st.markdown("### Processamento seguro para grandes volumes de XML")
        
        processador_cte_massivo()
        
    except Exception as e:
        st.error(f"Erro crítico na aplicação: {str(e)}")
        st.code(traceback.format_exc())
        
        # Tentar recuperar
        if st.button("🔄 Tentar Recuperar"):
            initialize_session_state()
            st.rerun()

if __name__ == "__main__":
    main()