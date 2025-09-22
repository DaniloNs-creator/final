import streamlit as st
import sqlite3
from datetime import datetime, timedelta, date
import pandas as pd
import plotly.express as px
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

# --- ANIMAÇÕES DE CARREGAMENTO ---
def show_loading_animation(message="Processando..."):
    """Exibe uma animação de carregamento"""
    with st.spinner(message):
        # Barra de progresso
        progress_bar = st.progress(0)
        
        # Simular progresso
        for i in range(100):
            time.sleep(0.01)  # Pequena pausa para animação
            progress_bar.progress(i + 1)
        
        progress_bar.empty()

def show_processing_animation(message="Analisando dados..."):
    """Exibe animação de processamento"""
    placeholder = st.empty()
    
    with placeholder.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info(f"⏳ {message}")
            # Spinner customizado
            spinner_placeholder = st.empty()
            
            # Animação de spinner
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
            # Dicionário de substituições
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN"
            }
            
            # Detecta o encoding
            encoding = detectar_encoding(conteudo)
            
            # Decodifica o conteúdo
            try:
                texto = conteudo.decode(encoding)
            except UnicodeDecodeError:
                texto = conteudo.decode('latin-1')
            
            # Processa as linhas
            linhas = texto.splitlines()
            linhas_processadas = []
            
            for linha in linhas:
                linha = linha.strip()
                # Verifica se a linha contém algum padrão a ser removido
                if not any(padrao in linha for padrao in padroes):
                    # Aplica as substituições
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
                # Animação de processamento
                show_loading_animation("Analisando arquivo TXT...")
                
                # Lê o conteúdo do arquivo
                conteudo = arquivo.read()
                
                # Processa o arquivo
                show_processing_animation("Processando linhas...")
                resultado, total_linhas = processar_arquivo(conteudo, padroes)
                
                if resultado is not None:
                    show_success_animation("Arquivo processado com sucesso!")
                    
                    # Mostra estatísticas
                    linhas_processadas = len(resultado.splitlines())
                    st.success(f"""
                    **Processamento concluído!**  
                    ✔️ Linhas originais: {total_linhas}  
                    ✔️ Linhas processadas: {linhas_processadas}  
                    ✔️ Linhas removidas: {total_linhas - linhas_processadas}
                    """)

                    # Prévia do resultado
                    st.subheader("Prévia do resultado")
                    st.text_area("Conteúdo processado", resultado, height=300)

                    # Botão de download
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

# --- PROCESSADOR CT-E COM EXTRAÇÃO DO PESO BRUTO ---
class CTeProcessorDirect:
    def __init__(self):
        self.processed_data = []
    
    def extract_nfe_number_from_key(self, chave_acesso):
        """
        Extrai o número da NF-e da chave de acesso conforme padrão oficial
        """
        if not chave_acesso or len(chave_acesso) != 44:
            return None
        
        try:
            numero_nfe = chave_acesso[25:34]
            return numero_nfe
        except Exception:
            return None
    
    def extract_peso_bruto(self, root):
        """Extrai o peso bruto do CT-e"""
        try:
            # Função auxiliar para encontrar texto com namespaces
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
            
            # Busca por todas as tags infQ (informações de quantidade)
            for prefix, uri in CTE_NAMESPACES.items():
                infQ_elements = root.findall(f'.//{{{uri}}}infQ')
                for infQ in infQ_elements:
                    tpMed = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
                    
                    if (tpMed is not None and tpMed.text == 'PESO BRUTO' and 
                        qCarga is not None and qCarga.text):
                        return float(qCarga.text)
            
            # Tentativa alternativa sem namespace
            infQ_elements = root.findall('.//infQ')
            for infQ in infQ_elements:
                tpMed = infQ.find('tpMed')
                qCarga = infQ.find('qCarga')
                
                if (tpMed is not None and tpMed.text == 'PESO BRUTO' and 
                    qCarga is not None and qCarga.text):
                    return float(qCarga.text)
            
            return 0.0
            
        except Exception as e:
            st.warning(f"Não foi possível extrair o peso bruto: {str(e)}")
            return 0.0
    
    def extract_cte_data(self, xml_content, filename):
        """Extrai dados específicos do CT-e incluindo peso bruto"""
        try:
            root = ET.fromstring(xml_content)
            
            # Registra namespaces
            for prefix, uri in CTE_NAMESPACES.items():
                ET.register_namespace(prefix, uri)
            
            # Função auxiliar para encontrar texto com namespaces
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
            
            # Extrai dados específicos do CT-e
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
            
            # Determina o documento do destinatário (CNPJ ou CPF)
            documento_destinatario = dest_CNPJ or dest_CPF or 'N/A'
            
            # Extrai endereço do destinatário
            dest_xLgr = find_text(root, './/cte:dest/cte:enderDest/cte:xLgr')
            dest_nro = find_text(root, './/cte:dest/cte:enderDest/cte:nro')
            dest_xBairro = find_text(root, './/cte:dest/cte:enderDest/cte:xBairro')
            dest_cMun = find_text(root, './/cte:dest/cte:enderDest/cte:cMun')
            dest_xMun = find_text(root, './/cte:dest/cte:enderDest/cte:xMun')
            dest_CEP = find_text(root, './/cte:dest/cte:enderDest/cte:CEP')
            dest_UF = find_text(root, './/cte:dest/cte:enderDest/cte:UF')
            
            # Monta endereço completo do destinatário
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
            
            # Extrai chave da NFe associada (se existir)
            infNFe_chave = find_text(root, './/cte:infNFe/cte:chave')
            
            # Extrai o número da NFe usando a função específica
            numero_nfe = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            
            # EXTRAI O PESO BRUTO
            peso_bruto = self.extract_peso_bruto(root)
            
            # Formata data no padrão DD/MM/AA
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
            
            # Retorna os dados estruturados incluindo peso bruto
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
                'Peso Bruto (kg)': peso_bruto,  # NOVO CAMPO ADICIONADO
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
            
            # Verifica se é um XML
            if not filename.lower().endswith('.xml'):
                return False, "Arquivo não é XML"
            
            # Verifica se é um CT-e
            content_str = file_content.decode('utf-8', errors='ignore')
            if 'CTe' not in content_str and 'conhecimento' not in content_str.lower():
                return False, "Arquivo não parece ser um CT-e"
            
            # Extrai dados
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
        
        # Barra de progresso para múltiplos arquivos
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

def processador_cte():
    """Interface para o sistema de CT-e com extração do peso bruto"""
    # Inicializar processador
    processor = CTeProcessorDirect()
    
    st.title("🚚 Processador de CT-e para Power BI")
    st.markdown("### Processa arquivos XML de CT-e e gera planilha para análise")
    
    # Informação sobre a extração do peso bruto
    with st.expander("ℹ️ Informações sobre a extração do Peso Bruto", expanded=False):
        st.markdown("""
        **Extração do Peso Bruto:**
        
        - O sistema agora extrai automaticamente o **Peso Bruto** do campo específico no XML
        - Localização no XML: `<infQ><tpMed>PESO BRUTO</tpMed><qCarga>319.8000</qCarga></infQ>`
        - O peso é convertido para quilogramas (kg) e incluído na planilha final
        
        **Exemplo de extração:**
        ```xml
        <infQ>
            <cUnid>01</cUnid>
            <tpMed>PESO BRUTO</tpMed>
            <qCarga>319.8000</qCarga>
        </infQ>
        ```
        **Resultado:** Peso Bruto = 319.80 kg
        """)
    
    # Navegação por abas
    tab1, tab2, tab3 = st.tabs(["📤 Upload", "👀 Visualizar Dados", "📥 Exportar"])
    
    with tab1:
        st.header("Upload de CT-es")
        upload_option = st.radio("Selecione o tipo de upload:", 
                                ["Upload Individual", "Upload em Lote"])
        
        if upload_option == "Upload Individual":
            uploaded_file = st.file_uploader("Selecione um arquivo XML de CT-e", type=['xml'], key="single_cte")
            if uploaded_file and st.button("📊 Processar CT-e", key="process_single"):
                show_loading_animation("Analisando estrutura do XML...")
                show_processing_animation("Extraindo dados do CT-e...")
                
                success, message = processor.process_single_file(uploaded_file)
                if success:
                    show_success_animation("CT-e processado com sucesso!")
                    
                    # Mostra exemplo da extração do peso bruto
                    df = processor.get_dataframe()
                    if not df.empty:
                        ultimo_cte = df.iloc[-1]
                        st.info(f"**Peso Bruto extraído:** {ultimo_cte['Peso Bruto (kg)']} kg")
                else:
                    st.error(message)
        
        else:
            uploaded_files = st.file_uploader("Selecione múltiplos arquivos XML de CT-e", 
                                            type=['xml'], 
                                            accept_multiple_files=True,
                                            key="multiple_cte")
            if uploaded_files and st.button("📊 Processar Todos", key="process_multiple"):
                show_loading_animation(f"Iniciando processamento de {len(uploaded_files)} arquivos...")
                
                results = processor.process_multiple_files(uploaded_files)
                
                show_success_animation("Processamento em lote concluído!")
                
                st.success(f"""
                **Processamento concluído!**  
                ✅ Sucessos: {results['success']}  
                ❌ Erros: {results['errors']}
                """)
                
                # Mostra estatísticas de extração
                df = processor.get_dataframe()
                if not df.empty:
                    ctes_com_nfe = df[df['Chave NFe'] != 'N/A'].shape[0]
                    peso_total = df['Peso Bruto (kg)'].sum()
                    st.info(f"""
                    **Estatísticas de extração:**
                    - CT-es com NF-e: {ctes_com_nfe}
                    - Peso bruto total: {peso_total:,.2f} kg
                    - Peso médio por CT-e: {df['Peso Bruto (kg)'].mean():,.2f} kg
                    """)
                
                if results['errors'] > 0:
                    with st.expander("Ver mensagens detalhadas"):
                        for msg in results['messages']:
                            st.write(f"- {msg}")
        
        # Botão para limpar dados
        if st.button("🗑️ Limpar Dados Processados", type="secondary"):
            processor.clear_data()
            st.success("Dados limpos com sucesso!")
            time.sleep(1)
            st.rerun()
    
    with tab2:
        st.header("Dados Processados")
        df = processor.get_dataframe()
        
        if not df.empty:
            st.write(f"Total de CT-es processados: {len(df)}")
            
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                uf_filter = st.multiselect("Filtrar por UF Início", options=df['UF Início'].unique())
            with col2:
                uf_destino_filter = st.multiselect("Filtrar por UF Destino", options=df['UF Destino'].unique())
            with col3:
                peso_filter = st.slider("Filtrar por Peso Bruto (kg)", 
                                      float(df['Peso Bruto (kg)'].min()), 
                                      float(df['Peso Bruto (kg)'].max()),
                                      (float(df['Peso Bruto (kg)'].min()), float(df['Peso Bruto (kg)'].max())))
            
            # Aplicar filtros
            filtered_df = df.copy()
            if uf_filter:
                filtered_df = filtered_df[filtered_df['UF Início'].isin(uf_filter)]
            if uf_destino_filter:
                filtered_df = filtered_df[filtered_df['UF Destino'].isin(uf_destino_filter)]
            filtered_df = filtered_df[
                (filtered_df['Peso Bruto (kg)'] >= peso_filter[0]) & 
                (filtered_df['Peso Bruto (kg)'] <= peso_filter[1])
            ]
            
            # Exibir dataframe com colunas principais incluindo Peso Bruto
            colunas_principais = [
                'Arquivo', 'nCT', 'Data Emissão', 'Emitente', 'Remetente', 
                'Destinatário', 'UF Início', 'UF Destino', 'Peso Bruto (kg)', 'Valor Prestação'
            ]
            
            st.dataframe(filtered_df[colunas_principais], use_container_width=True)
            
            # Detalhes expandíveis
            with st.expander("📋 Ver todos os campos detalhados"):
                st.dataframe(filtered_df, use_container_width=True)
            
            # Estatísticas
            st.subheader("📈 Estatísticas")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("Total Valor Prestação", f"R$ {filtered_df['Valor Prestação'].sum():,.2f}")
            col2.metric("Peso Bruto Total", f"{filtered_df['Peso Bruto (kg)'].sum():,.2f} kg")
            col3.metric("Média Peso/CT-e", f"{filtered_df['Peso Bruto (kg)'].mean():,.2f} kg")
            col4.metric("CT-es com NFe", f"{filtered_df[filtered_df['Chave NFe'] != 'N/A'].shape[0]}")
            
            # Exemplo de extração de peso
            if not filtered_df.empty:
                exemplo = filtered_df.iloc[0]
                st.info(f"**Exemplo de extração:** Peso Bruto = {exemplo['Peso Bruto (kg)']} kg")
            
            # Gráficos
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("📊 Distribuição por Peso Bruto")
                if not filtered_df.empty:
                    fig_peso = px.histogram(
                        filtered_df, 
                        x='Peso Bruto (kg)',
                        title="Distribuição dos CT-es por Peso Bruto",
                        nbins=20
                    )
                    st.plotly_chart(fig_peso, use_container_width=True)
            
            with col_chart2:
                st.subheader("📈 Relação Peso x Valor")
                if not filtered_df.empty:
                    fig_relacao = px.scatter(
                        filtered_df,
                        x='Peso Bruto (kg)',
                        y='Valor Prestação',
                        title="Relação entre Peso Bruto e Valor da Prestação",
                        trendline="lowess"
                    )
                    st.plotly_chart(fig_relacao, use_container_width=True)
            
        else:
            st.info("Nenhum CT-e processado ainda. Faça upload de arquivos na aba 'Upload'.")
    
    with tab3:
        st.header("Exportar para Excel")
        df = processor.get_dataframe()
        
        if not df.empty:
            st.success(f"Pronto para exportar {len(df)} registros")
            
            # Opções de exportação
            export_option = st.radio("Formato de exportação:", 
                                   ["Excel (.xlsx)", "CSV (.csv)"])
            
            # Seleção de colunas para exportação
            st.subheader("Selecionar Colunas para Exportação")
            todas_colunas = df.columns.tolist()
            colunas_selecionadas = st.multiselect(
                "Selecione as colunas para exportar:",
                options=todas_colunas,
                default=todas_colunas
            )
            
            df_export = df[colunas_selecionadas] if colunas_selecionadas else df
            
            if export_option == "Excel (.xlsx)":
                # Animação de geração do Excel
                show_processing_animation("Gerando arquivo Excel...")
                
                # Gerar Excel
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
                # Animação de geração do CSV
                show_processing_animation("Gerando arquivo CSV...")
                
                # Gerar CSV
                csv = df_export.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Baixar Arquivo CSV",
                    data=csv,
                    file_name="dados_cte.csv",
                    mime="text/csv"
                )
            
            # Prévia dos dados
            with st.expander("📋 Prévia dos dados a serem exportados"):
                st.dataframe(df_export.head(10))
                
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
        /* Animação personalizada */
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
    
    # Mostrar capa com a imagem
    st.markdown("""
    <div class="cover-container">
        <img src="https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png" class="cover-logo">
        <h1 class="cover-title">Sistema de Processamento de Arquivos</h1>
        <p class="cover-subtitle">Processamento de TXT e CT-e para análise de dados</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Menu de navegação
    tab1, tab2 = st.tabs(["📄 Processador TXT", "🚚 Processador CT-e"])
    
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