import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO
import hashlib
import zipfile
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time
import os

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Sistema de Processamento de XML",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZAÇÃO ROBUSTA DO SESSION_STATE ---
def initialize_session_state():
    """Inicializa todas as variáveis do session_state de forma segura"""
    default_values = {
        'batch_size': 100,
        'max_workers': min(8, (os.cpu_count() or 1) * 2),
        'max_memory_usage': 80,
        'processed_files': set(),
        'processing_stats': {'success': 0, 'errors': 0, 'total': 0},
        'processor_data': [],
        'initialized': True
    }
    
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Inicializar imediatamente
initialize_session_state()

# Namespaces para CT-e
CTE_NAMESPACES = {
    'cte': 'http://www.portalfiscal.inf.br/cte'
}

# --- PROCESSADOR CT-E SIMPLIFICADO E ROBUSTO ---
class SimpleCTeProcessor:
    def __init__(self):
        # Garantir que session_state está inicializado
        initialize_session_state()
    
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
    
    def extract_cte_data(self, xml_content, filename):
        """Extrai dados básicos do CT-e de forma robusta"""
        try:
            # Verificação rápida se é CT-e
            content_str = xml_content.decode('utf-8', errors='ignore') if isinstance(xml_content, bytes) else xml_content
            if 'CTe' not in content_str:
                return None
            
            # Verificar duplicata
            if self._is_duplicate(xml_content):
                return {'Arquivo': filename, 'Status': 'Duplicado'}
            
            # Parsing seguro
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e:
                return {'Arquivo': filename, 'Status': f'Erro XML: {str(e)}'}
            
            # Dicionário para resultados
            data = {'Arquivo': filename}
            
            # Função auxiliar para buscar texto
            def find_text(tag_name):
                try:
                    # Tentar com namespace
                    for uri in CTE_NAMESPACES.values():
                        element = root.find(f'.//{{{uri}}}{tag_name}')
                        if element is not None and element.text:
                            return element.text
                    
                    # Tentar sem namespace
                    element = root.find(f'.//{tag_name}')
                    if element is not None and element.text:
                        return element.text
                    
                    return None
                except Exception:
                    return None
            
            # Extrair dados básicos
            data['nCT'] = find_text('nCT') or 'N/A'
            
            # Data de emissão
            dh_emi = find_text('dhEmi')
            if dh_emi:
                try:
                    data['Data Emissão'] = datetime.strptime(dh_emi[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
                except:
                    data['Data Emissão'] = dh_emi[:10]
            else:
                data['Data Emissão'] = 'N/A'
            
            # Valores numéricos
            vTPrest = find_text('vTPrest')
            try:
                data['Valor Prestação'] = float(vTPrest) if vTPrest else 0.0
            except:
                data['Valor Prestação'] = 0.0
            
            # Peso bruto (busca simplificada)
            data['Peso Bruto (kg)'] = 0.0
            try:
                # Buscar infQ
                for uri in CTE_NAMESPACES.values():
                    infq_elements = root.findall(f'.//{{{uri}}}infQ')
                    for infq in infq_elements:
                        tp_med = infq.find(f'{{{uri}}}tpMed')
                        q_carga = infq.find(f'{{{uri}}}qCarga')
                        if (tp_med is not None and tp_med.text == 'PESO BRUTO' and 
                            q_carga is not None and q_carga.text):
                            data['Peso Bruto (kg)'] = float(q_carga.text)
                            break
            except:
                pass
            
            data['UF Início'] = find_text('UFIni') or 'N/A'
            data['UF Fim'] = find_text('UFFim') or 'N/A'
            data['Emitente'] = find_text('xNome') or 'N/A'
            data['Data Processamento'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            data['Status'] = 'Sucesso'
            
            return data
            
        except Exception as e:
            return {'Arquivo': filename, 'Status': f'Erro geral: {str(e)}'}
    
    def process_single_file(self, uploaded_file):
        """Processa um único arquivo"""
        try:
            file_content = uploaded_file.getvalue()
            filename = uploaded_file.name
            
            if not filename.lower().endswith('.xml'):
                return False, f"{filename}: Não é arquivo XML"
            
            result = self.extract_cte_data(file_content, filename)
            
            if result and result.get('Status') == 'Sucesso':
                # Adicionar aos dados processados
                if 'processor_data' not in st.session_state:
                    st.session_state.processor_data = []
                st.session_state.processor_data.append(result)
                return True, f"{filename}: Processado com sucesso"
            else:
                status = result.get('Status', 'Erro desconhecido') if result else "Falha na extração"
                return False, f"{filename}: {status}"
                
        except Exception as e:
            return False, f"{filename}: Erro - {str(e)}"
    
    def process_batch(self, files_batch):
        """Processa um lote de arquivos"""
        batch_results = {'success': 0, 'errors': 0, 'messages': []}
        
        for uploaded_file in files_batch:
            success, message = self.process_single_file(uploaded_file)
            if success:
                batch_results['success'] += 1
            else:
                batch_results['errors'] += 1
            batch_results['messages'].append(message)
        
        return batch_results
    
    def process_files_parallel(self, uploaded_files):
        """Processa arquivos em paralelo"""
        total_files = len(uploaded_files)
        
        # Atualizar estatísticas
        st.session_state.processing_stats = {
            'success': 0, 
            'errors': 0, 
            'total': total_files
        }
        
        # Barra de progresso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Dividir em lotes
        batch_size = st.session_state.batch_size
        batches = [uploaded_files[i:i + batch_size] 
                  for i in range(0, total_files, batch_size)]
        
        total_batches = len(batches)
        max_workers = min(st.session_state.max_workers, total_batches)
        
        # Processar em paralelo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {
                executor.submit(self.process_batch, batch): i 
                for i, batch in enumerate(batches)
            }
            
            completed = 0
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_result = future.result()
                    
                    # Atualizar estatísticas
                    st.session_state.processing_stats['success'] += batch_result['success']
                    st.session_state.processing_stats['errors'] += batch_result['errors']
                    
                    completed += 1
                    progress = (completed / total_batches)
                    progress_bar.progress(progress)
                    
                    status_text.text(f"Lote {completed}/{total_batches} - "
                                   f"Sucessos: {st.session_state.processing_stats['success']}, "
                                   f"Erros: {st.session_state.processing_stats['errors']}")
                    
                    # Limpar memória periodicamente
                    if completed % 3 == 0:
                        gc.collect()
                        
                except Exception as e:
                    st.error(f"Erro no lote {batch_idx}: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        
        return st.session_state.processing_stats
    
    def get_dataframe(self):
        """Retorna dados como DataFrame"""
        if 'processor_data' in st.session_state and st.session_state.processor_data:
            df = pd.DataFrame(st.session_state.processor_data)
            # Converter colunas numéricas
            numeric_cols = ['Valor Prestação', 'Peso Bruto (kg)']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        return pd.DataFrame()
    
    def clear_data(self):
        """Limpa todos os dados"""
        if 'processor_data' in st.session_state:
            st.session_state.processor_data = []
        if 'processed_files' in st.session_state:
            st.session_state.processed_files = set()
        if 'processing_stats' in st.session_state:
            st.session_state.processing_stats = {'success': 0, 'errors': 0, 'total': 0}
        gc.collect()

# --- INTERFACE DO USUÁRIO ---
def main():
    # Inicialização final
    initialize_session_state()
    
    # CSS simples
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Cabeçalho
    st.markdown("""
    <div class="main-header">
        <h1>🚚 Processador de CT-e</h1>
        <p>Processamento otimizado para grandes volumes de XML</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializar processador
    if 'processor' not in st.session_state:
        st.session_state.processor = SimpleCTeProcessor()
    
    processor = st.session_state.processor
    
    # Abas principais
    tab1, tab2, tab3 = st.tabs(["📤 Upload e Processamento", "⚙️ Configurações", "📊 Resultados"])
    
    with tab1:
        st.header("Upload de Arquivos CT-e")
        
        # Upload de arquivos
        uploaded_files = st.file_uploader(
            "Selecione arquivos XML ou ZIP",
            type=['xml', 'zip'],
            accept_multiple_files=True,
            help="Selecione arquivos XML individuais ou ZIP contendo XMLs"
        )
        
        if uploaded_files:
            # Processar arquivos ZIP
            all_xml_files = []
            for file in uploaded_files:
                if file.name.lower().endswith('.zip'):
                    try:
                        with zipfile.ZipFile(file, 'r') as zf:
                            for file_info in zf.infolist():
                                if file_info.filename.lower().endswith('.xml'):
                                    with zf.open(file_info) as xml_file:
                                        content = xml_file.read()
                                        virtual_file = BytesIO(content)
                                        virtual_file.name = file_info.filename
                                        all_xml_files.append(virtual_file)
                    except Exception as e:
                        st.error(f"Erro ao extrair {file.name}: {str(e)}")
                else:
                    all_xml_files.append(file)
            
            st.info(f"📁 **{len(all_xml_files)}** arquivos XML prontos para processamento")
            
            # Configurações rápidas
            col1, col2 = st.columns(2)
            with col1:
                batch_size = st.number_input("Tamanho do lote", min_value=10, max_value=500, 
                                           value=st.session_state.batch_size)
            with col2:
                max_workers = st.number_input("Número de threads", min_value=1, max_value=16,
                                            value=st.session_state.max_workers)
            
            # Botão de processamento
            if st.button("🚀 Iniciar Processamento", type="primary", use_container_width=True):
                if all_xml_files:
                    # Atualizar configurações
                    st.session_state.batch_size = batch_size
                    st.session_state.max_workers = max_workers
                    
                    # Processar
                    start_time = time.time()
                    results = processor.process_files_parallel(all_xml_files)
                    processing_time = time.time() - start_time
                    
                    # Resultados
                    success_rate = (results['success'] / results['total'] * 100) if results['total'] > 0 else 0
                    
                    st.success(f"""
                    **✅ Processamento Concluído!**
                    
                    - **Tempo total:** {processing_time:.1f} segundos
                    - **Arquivos processados:** {results['total']}
                    - **Sucessos:** {results['success']} ({success_rate:.1f}%)
                    - **Erros:** {results['errors']}
                    - **Velocidade:** {results['success']/max(processing_time, 0.1):.1f} arquivos/segundo
                    """)
    
    with tab2:
        st.header("Configurações de Performance")
        
        st.subheader("Configurações Atuais")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tamanho do Lote", st.session_state.batch_size)
        with col2:
            st.metric("Threads", st.session_state.max_workers)
        with col3:
            st.metric("Limite Memória", f"{st.session_state.max_memory_usage}%")
        
        st.subheader("Ajustar Configurações")
        new_batch_size = st.slider("Tamanho do lote", 10, 500, st.session_state.batch_size)
        new_max_workers = st.slider("Número de threads", 1, 16, st.session_state.max_workers)
        new_memory_limit = st.slider("Limite de memória", 50, 95, st.session_state.max_memory_usage)
        
        if st.button("💾 Salvar Configurações"):
            st.session_state.batch_size = new_batch_size
            st.session_state.max_workers = new_max_workers
            st.session_state.max_memory_usage = new_memory_limit
            st.success("Configurações salvas!")
        
        st.subheader("Gerenciamento")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Limpar Todos os Dados", use_container_width=True):
                processor.clear_data()
                st.success("Dados limpos com sucesso!")
                st.rerun()
        with col2:
            if st.button("🔄 Coletar Lixo", use_container_width=True):
                gc.collect()
                st.success("Memória liberada!")
    
    with tab3:
        st.header("Resultados e Exportação")
        
        df = processor.get_dataframe()
        
        if not df.empty:
            st.success(f"📊 **{len(df)}** registros processados")
            
            # Estatísticas rápidas
            col1, col2, col3 = st.columns(3)
            with col1:
                total_value = df['Valor Prestação'].sum()
                st.metric("Valor Total", f"R$ {total_value:,.2f}")
            with col2:
                total_weight = df['Peso Bruto (kg)'].sum()
                st.metric("Peso Total", f"{total_weight:,.1f} kg")
            with col3:
                avg_value = df['Valor Prestação'].mean()
                st.metric("Valor Médio", f"R$ {avg_value:,.2f}")
            
            # Filtros
            st.subheader("Filtros")
            col1, col2 = st.columns(2)
            with col1:
                uf_filter = st.multiselect("Filtrar por UF", options=df['UF Início'].unique())
            with col2:
                if 'Peso Bruto (kg)' in df.columns:
                    min_weight = df['Peso Bruto (kg)'].min()
                    max_weight = df['Peso Bruto (kg)'].max()
                    weight_range = st.slider("Filtrar por peso (kg)", min_weight, max_weight, (min_weight, max_weight))
            
            # Aplicar filtros
            filtered_df = df.copy()
            if uf_filter:
                filtered_df = filtered_df[filtered_df['UF Início'].isin(uf_filter)]
            if 'Peso Bruto (kg)' in df.columns:
                filtered_df = filtered_df[
                    (filtered_df['Peso Bruto (kg)'] >= weight_range[0]) & 
                    (filtered_df['Peso Bruto (kg)'] <= weight_range[1])
                ]
            
            # Exibir dados
            st.dataframe(filtered_df, use_container_width=True, height=400)
            
            # Exportação
            st.subheader("Exportar Dados")
            export_format = st.radio("Formato de exportação:", ["CSV", "Excel", "Parquet"])
            
            if export_format == "CSV":
                csv_data = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar CSV",
                    data=csv_data,
                    file_name="ctes_processados.csv",
                    mime="text/csv"
                )
            elif export_format == "Excel":
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    filtered_df.to_excel(writer, index=False, sheet_name='CTes')
                excel_buffer.seek(0)
                st.download_button(
                    label="📥 Baixar Excel",
                    data=excel_buffer,
                    file_name="ctes_processados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:  # Parquet
                parquet_buffer = BytesIO()
                filtered_df.to_parquet(parquet_buffer, index=False)
                parquet_buffer.seek(0)
                st.download_button(
                    label="📥 Baixar Parquet",
                    data=parquet_buffer,
                    file_name="ctes_processados.parquet",
                    mime="application/octet-stream"
                )
        else:
            st.info("📝 Nenhum dado processado. Faça upload de arquivos na aba de Upload.")

# Executar aplicação
if __name__ == "__main__":
    # Garantir inicialização final
    initialize_session_state()
    main()