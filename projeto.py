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
        key="txt_multiple"
    )
    
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
        
        st.info(f"**Padrões ativos:** {', '.join(padroes)}")
    
    if uploaded_files:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔄 Processar Todos os Arquivos TXT", key="process_all_txt"):
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
            if st.button("🗑️ Limpar Arquivos Processados", type="secondary"):
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
                options=[arq['filename'] for arq in arquivos_processados]
            )
            
            arquivo = next((arq for arq in arquivos_processados if arq['filename'] == arquivo_selecionado), None)
            
            if arquivo:
                st.write(f"**Arquivo:** {arquivo['filename']}")
                st.write(f"**Estatísticas:** {arquivo['linhas_originais']} → {arquivo['linhas_processadas']} linhas ({arquivo['linhas_removidas']} removidas)")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.text_area("Conteúdo Processado", arquivo['conteudo'], height=400)
                
                with col2:
                    # Exemplo das primeiras linhas removidas (se aplicável)
                    st.info("**Informações do processamento:**")
                    st.write(f"- Redução de: {arquivo['linhas_removidas']} linhas")
                    st.write(f"- Eficiência: {(arquivo['linhas_removidas']/arquivo['linhas_originais']*100):.1f}%")
        
        with tab3:
            st.subheader("Download dos Arquivos Processados")
            
            # Download individual
            st.write("**Download Individual:**")
            for arq in arquivos_processados:
                buffer = BytesIO()
                buffer.write(arq['conteudo'].encode('utf-8'))
                buffer.seek(0)
                
                st.download_button(
                    label=f"⬇️ {arq['filename']}",
                    data=buffer,
                    file_name=f"processado_{arq['filename']}",
                    mime="text/plain",
                    key=f"download_{arq['filename']}"
                )
            
            # Download em lote (ZIP)
            st.write("**Download em Lote (ZIP):**")
            if st.button("📦 Gerar Pacote ZIP com Todos os Arquivos"):
                show_processing_animation("Criando arquivo ZIP...")
                
                import zipfile
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
                    mime="application/zip"
                )

# --- PROCESSADOR CT-E COM SUPORTE A MÚLTIPLOS ARQUIVOS ---
class CTeProcessorDirect:
    def __init__(self):
        self.processed_data = []
    
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
        """Extrai o peso bruto do CT-e - BUSCA EM PESO BRUTO E PESO BASE DE CÁLCULO"""
        try:
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
                except Exception:
                    return None
            
            # Lista de tipos de peso a serem procurados (em ordem de prioridade)
            tipos_peso = ['PESO BRUTO', 'PESO BASE DE CALCULO', 'PESO BASE CÁLCULO', 'PESO']
            
            # Busca por todas as tags infQ com namespaces
            for prefix, uri in CTE_NAMESPACES.items():
                infQ_elements = root.findall(f'.//{{{uri}}}infQ')
                for infQ in infQ_elements:
                    tpMed = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
                    
                    if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                        # Verifica cada tipo de peso na ordem de prioridade
                        for tipo_peso in tipos_peso:
                            if tipo_peso in tpMed.text.upper():
                                peso = float(qCarga.text)
                                return peso, tipo_peso  # Retorna o peso e o tipo encontrado
            
            # Tentativa alternativa sem namespace
            infQ_elements = root.findall('.//infQ')
            for infQ in infQ_elements:
                tpMed = infQ.find('tpMed')
                qCarga = infQ.find('qCarga')
                
                if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                    for tipo_peso in tipos_peso:
                        if tipo_peso in tpMed.text.upper():
                            peso = float(qCarga.text)
                            return peso, tipo_peso
            
            return 0.0, "Não encontrado"
            
        except Exception as e:
            st.warning(f"Não foi possível extrair o peso: {str(e)}")
            return 0.0, "Erro na extração"
    
    def extract_cte_data(self, xml_content, filename):
        """Extrai dados específicos do CT-e incluindo peso bruto"""
        try:
            root = ET.fromstring(xml_content)
            
            for prefix, uri in CTE_NAMESPACES.items():
                ET.register_namespace(prefix, uri)
            
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
                except Exception:
                    return None
            
            # Extrai dados do CT-e
            nCT = find_text(root, './/cte:nCT')
            dhEmi = find_text(root, './/cte:dhEmi')
            cMunIni = find_text(root, './/cte:cMunIni')
            UFIni = find_text(root, './/cte:UFIni')
            cMunFim = find_text(root, './/cte:cMunFim')
            UFFim = find_text(root, './/cte:UFFim')
            emit_xNome = find_text(root, './/cte:emit/cte:xNome')
            vTPrest = find_text(root, './/cte:vTPrest')
            rem_xNome = find_text(root, './/cte:rem/cte:xNome')
            
            # Extrai dados do destinatário
            dest_xNome = find_text(root, './/cte:dest/cte:xNome')
            dest_CNPJ = find_text(root, './/cte:dest/cte:CNPJ')
            dest_CPF = find_text(root, './/cte:dest/cte:CPF')
            
            documento_destinatario = dest_CNPJ or dest_CPF or 'N/A'
            
            # Extrai endereço do destinatário
            dest_xLgr = find_text(root, './/cte:dest/cte:enderDest/cte:xLgr')
            dest_nro = find_text(root, './/cte:dest/cte:enderDest/cte:nro')
            dest_xBairro = find_text(root, './/cte:dest/cte:enderDest/cte:xBairro')
            dest_cMun = find_text(root, './/cte:dest/cte:enderDest/cte:cMun')
            dest_xMun = find_text(root, './/cte:dest/cte:enderDest/cte:xMun')
            dest_CEP = find_text(root, './/cte:dest/cte:enderDest/cte:CEP')
            dest_UF = find_text(root, './/cte:dest/cte:enderDest/cte:UF')
            
            # Monta endereço completo
            endereco_destinatario = ""
            if dest_xLgr:
                endereco_destinatario += f"{dest_xLgr}"
                if dest_nro:
                    endereco_destinatario += f", {dest_nro}"
                if dest_xBairro:
                    endereco_destinatario += f" - {dest_xBairro}"
                if dest_xMun:
                    endereco_destinatario += f", {dest_xMun}"
                if dest_UF:
                    endereco_destinatario += f"/{dest_UF}"
                if dest_CEP:
                    endereco_destinatario += f" - CEP: {dest_CEP}"
            
            if not endereco_destinatario:
                endereco_destinatario = "N/A"
            
            infNFe_chave = find_text(root, './/cte:infNFe/cte:chave')
            numero_nfe = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            
            # EXTRAI O PESO BRUTO - AGORA COM BUSCA EM MÚLTIPLOS CAMPOS
            peso_bruto, tipo_peso_encontrado = self.extract_peso_bruto(root)
            
            # Formata data
            data_formatada = None
            if dhEmi:
                try:
                    try:
                        data_obj = datetime.strptime(dhEmi[:10], '%Y-%m-%d')
                    except:
                        try:
                            data_obj = datetime.strptime(dhEmi[:10], '%d/%m/%Y')
                        except:
                            data_obj = datetime.strptime(dhEmi[:10], '%d/%m/%y')
                    data_formatada = data_obj.strftime('%d/%m/%y')
                except:
                    data_formatada = dhEmi[:10]
            
            # Converte valor para decimal
            try:
                vTPrest = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                vTPrest = 0.0
            
            return {
                'Arquivo': filename,
                'nCT': nCT or 'N/A',
                'Data Emissão': data_formatada or dhEmi or 'N/A',
                'Código Município Início': cMunIni or 'N/A',
                'UF Início': UFIni or 'N/A',
                'Código Município Fim': cMunFim or 'N/A',
                'UF Fim': UFFim or 'N/A',
                'Emitente': emit_xNome or 'N/A',
                'Valor Prestação': vTPrest,
                'Peso Bruto (kg)': peso_bruto,
                'Tipo de Peso Encontrado': tipo_peso_encontrado,
                'Remetente': rem_xNome or 'N/A',
                'Destinatário': dest_xNome or 'N/A',
                'Documento Destinatário': documento_destinatario,
                'Endereço Destinatário': endereco_destinatario,
                'Município Destino': dest_xMun or 'N/A',
                'UF Destino': dest_UF or 'N/A',
                'Chave NFe': infNFe_chave or 'N/A',
                'Número NFe': numero_nfe or 'N/A',
                'Data Processamento': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
        except Exception as e:
            st.error(f"Erro ao extrair dados do CT-e {filename}: {str(e)}")
            return None
    
    def process_single_file(self, uploaded_file):
        """Processa um único arquivo XML de CT-e"""
        try:
            file_content = uploaded_file.getvalue()
            filename = uploaded_file.name
            
            if not filename.lower().endswith('.xml'):
                return False, "Arquivo não é XML"
            
            content_str = file_content.decode('utf-8', errors='ignore')
            if 'CTe' not in content_str and 'conhecimento' not in content_str.lower():
                return False, "Arquivo não parece ser um CT-e"
            
            cte_data = self.extract_cte_data(content_str, filename)
            
            if cte_data:
                self.processed_data.append(cte_data)
                return True, f"CT-e {filename} processado com sucesso!"
            else:
                return False, f"Erro ao processar CT-e {filename}"
                
        except Exception as e:
            return False, f"Erro ao processar arquivo {filename}: {str(e)}"
    
    def process_multiple_files(self, uploaded_files):
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
            
            success, message = self.process_single_file(uploaded_file)
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

# --- FUNÇÃO PARA CRIAR LINHA DE TENDÊNCIA SIMPLES SEM STATSMODELS ---
def add_simple_trendline(fig, x, y):
    """Adiciona uma linha de tendência simples usando regressão linear básica"""
    try:
        # Remove valores NaN
        mask = ~np.isnan(x) & ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) > 1:
            # Regressão linear simples
            coefficients = np.polyfit(x_clean, y_clean, 1)
            polynomial = np.poly1d(coefficients)
            
            # Gera pontos para a linha de tendência
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
        # Se houver erro, simplesmente não adiciona a linha de tendência
        pass

def processador_cte():
    """Interface para o sistema de CT-e com extração do peso bruto"""
    processor = CTeProcessorDirect()
    
    st.title("🚚 Processador de CT-e para Power BI - Múltiplos Arquivos")
    st.markdown("### Processa múltiplos arquivos XML de CT-e simultaneamente e gera planilha para análise")
    
    with st.expander("ℹ️ Informações sobre a extração do Peso", expanded=True):
        st.markdown("""
        **Extração do Peso - Busca Inteligente:**
        
        O sistema agora busca o peso em **múltiplos campos** na seguinte ordem de prioridade:
        
        1. **PESO BRUTO** - Campo principal
        2. **PESO BASE DE CALCULO** - Campo alternativo 1
        3. **PESO BASE CÁLCULO** - Campo alternativo 2  
        4. **PESO** - Campo genérico
        
        **Exemplos de campos reconhecidos:**
        ```xml
        <infQ>
            <tpMed>PESO BRUTO</tpMed>
            <qCarga>319.8000</qCarga>
        </infQ>
        ```
        ```xml
        <infQ>
            <tpMed>PESO BASE DE CALCULO</tpMed>
            <qCarga>250.5000</qCarga>
        </infQ>
        ```
        
        **Resultado:** O sistema mostrará qual tipo de peso foi encontrado em cada CT-e
        """)
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload em Lote", "👀 Visualizar Dados", "📥 Exportar"])
    
    with tab1:
        st.header("Upload de Múltiplos CT-es")
        
        uploaded_files = st.file_uploader(
            "Selecione os arquivos XML de CT-e (múltiplos)", 
            type=['xml'], 
            accept_multiple_files=True,
            key="cte_multiple"
        )
        
        if uploaded_files:
            st.info(f"📁 **{len(uploaded_files)} arquivo(s) selecionado(s)**")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("📊 Processar Todos os CT-es", key="process_all_cte"):
                    show_loading_animation(f"Iniciando processamento de {len(uploaded_files)} arquivos...")
                    
                    results = processor.process_multiple_files(uploaded_files)
                    show_success_animation("Processamento em lote concluído!")
                    
                    st.success(f"""
                    **Processamento concluído!**  
                    ✅ Sucessos: {results['success']}  
                    ❌ Erros: {results['errors']}
                    """)
                    
                    # Salvar no session state
                    st.session_state.processed_cte_files = processor.get_dataframe().to_dict('records')
                    
                    if results['errors'] > 0:
                        with st.expander("Ver mensagens detalhadas"):
                            for msg in results['messages']:
                                st.write(f"- {msg}")
            
            with col2:
                if st.button("🗑️ Limpar Dados Processados", type="secondary"):
                    processor.clear_data()
                    st.session_state.processed_cte_files = []
                    st.success("Dados limpos com sucesso!")
                    time.sleep(1)
                    st.rerun()
    
    with tab2:
        st.header("Dados Processados")
        
        if st.session_state.processed_cte_files:
            df = pd.DataFrame(st.session_state.processed_cte_files)
            st.write(f"📊 **Total de CT-es processados:** {len(df)}")
            
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                uf_filter = st.multiselect("Filtrar por UF Início", options=df['UF Início'].unique())
            with col2:
                uf_destino_filter = st.multiselect("Filtrar por UF Destino", options=df['UF Destino'].unique())
            with col3:
                tipo_peso_filter = st.multiselect("Filtrar por Tipo de Peso", options=df['Tipo de Peso Encontrado'].unique())
            
            # Filtro de peso
            st.subheader("Filtro por Peso Bruto")
            peso_min = float(df['Peso Bruto (kg)'].min())
            peso_max = float(df['Peso Bruto (kg)'].max())
            peso_filter = st.slider("Selecione a faixa de peso (kg)", peso_min, peso_max, (peso_min, peso_max))
            
            # Aplicar filtros
            filtered_df = df.copy()
            if uf_filter:
                filtered_df = filtered_df[filtered_df['UF Início'].isin(uf_filter)]
            if uf_destino_filter:
                filtered_df = filtered_df[filtered_df['UF Destino'].isin(uf_destino_filter)]
            if tipo_peso_filter:
                filtered_df = filtered_df[filtered_df['Tipo de Peso Encontrado'].isin(tipo_peso_filter)]
            filtered_df = filtered_df[
                (filtered_df['Peso Bruto (kg)'] >= peso_filter[0]) & 
                (filtered_df['Peso Bruto (kg)'] <= peso_filter[1])
            ]
            
            # Exibir dataframe
            colunas_principais = [
                'Arquivo', 'nCT', 'Data Emissão', 'Emitente', 'Remetente', 
                'Destinatário', 'UF Início', 'UF Destino', 'Peso Bruto (kg)', 
                'Tipo de Peso Encontrado', 'Valor Prestação'
            ]
            
            st.dataframe(filtered_df[colunas_principais], use_container_width=True)
            
            with st.expander("📋 Ver todos os campos detalhados"):
                st.dataframe(filtered_df, use_container_width=True)
            
            # Estatísticas
            st.subheader("📈 Estatísticas")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("Total Valor Prestação", f"R$ {filtered_df['Valor Prestação'].sum():,.2f}")
            col2.metric("Peso Bruto Total", f"{filtered_df['Peso Bruto (kg)'].sum():,.2f} kg")
            col3.metric("Média Peso/CT-e", f"{filtered_df['Peso Bruto (kg)'].mean():,.2f} kg")
            col4.metric("Tipos de Peso", f"{filtered_df['Tipo de Peso Encontrado'].nunique()}")
            
            # Gráficos
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("📊 Distribuição por Tipo de Peso")
                if not filtered_df.empty:
                    tipo_counts = filtered_df['Tipo de Peso Encontrado'].value_counts()
                    fig_tipo = px.pie(
                        values=tipo_counts.values,
                        names=tipo_counts.index,
                        title="Distribuição por Tipo de Peso Encontrado"
                    )
                    st.plotly_chart(fig_tipo, use_container_width=True)
            
            with col_chart2:
                st.subheader("📈 Relação Peso x Valor")
                if not filtered_df.empty:
                    fig_relacao = px.scatter(
                        filtered_df,
                        x='Peso Bruto (kg)',
                        y='Valor Prestação',
                        title="Relação entre Peso Bruto e Valor da Prestação",
                        color='Tipo de Peso Encontrado'
                    )
                    
                    if st.checkbox("Mostrar linha de tendência", key="trendline"):
                        add_simple_trendline(fig_relacao, 
                                           filtered_df['Peso Bruto (kg)'].values, 
                                           filtered_df['Valor Prestação'].values)
                    
                    st.plotly_chart(fig_relacao, use_container_width=True)
            
        else:
            st.info("📝 Nenhum CT-e processado ainda. Faça upload de arquivos na aba 'Upload em Lote'.")
    
    with tab3:
        st.header("Exportar para Excel")
        
        if st.session_state.processed_cte_files:
            df = pd.DataFrame(st.session_state.processed_cte_files)
            st.success(f"📤 Pronto para exportar {len(df)} registros")
            
            export_option = st.radio("Formato de exportação:", 
                                   ["Excel (.xlsx)", "CSV (.csv)"])
            
            st.subheader("Selecionar Colunas para Exportação")
            todas_colunas = df.columns.tolist()
            colunas_selecionadas = st.multiselect(
                "Selecione as colunas para exportar:",
                options=todas_colunas,
                default=todas_colunas
            )
            
            df_export = df[colunas_selecionadas] if colunas_selecionadas else df
            
            if export_option == "Excel (.xlsx)":
                show_processing_animation("Gerando arquivo Excel...")
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, sheet_name='Dados_CTe', index=False)
                
                output.seek(0)
                
                st.download_button(
                    label="📥 Baixar Planilha Excel",
                    data=output,
                    file_name="dados_cte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            else:
                show_processing_animation("Gerando arquivo CSV...")
                
                csv = df_export.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Baixar Arquivo CSV",
                    data=csv,
                    file_name="dados_cte.csv",
                    mime="text/csv"
                )
            
            with st.expander("📋 Prévia dos dados a serem exportados"):
                st.dataframe(df_export.head(10))
                
        else:
            st.warning("⚠️ Nenhum dado disponível para exportação.")

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
        .cover-logo {
            max-width: 300px;
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
    load_css()
    
    st.markdown("""
    <div class="cover-container">
        <img src="https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png" class="cover-logo">
        <h1 class="cover-title">Sistema de Processamento de Múltiplos Arquivos</h1>
        <p class="cover-subtitle">Processamento ilimitado de TXT e CT-e para análise de dados</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📄 Processador TXT (Múltiplos)", "🚚 Processador CT-e (Múltiplos)"])
    
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