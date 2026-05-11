import streamlit as st
import sqlite3
from datetime import datetime, timedelta, date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random
from typing import List, Tuple, Optional, Dict, Any
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
import fitz  # PyMuPDF
import pdfplumber
import re
from lxml import etree
import tempfile
import logging
import gc

# ==============================================================================
# CONFIGURAÇÃO AUTOMÁTICA DO SERVIDOR STREAMLIT
# ==============================================================================
def setup_streamlit_config():
    try:
        os.makedirs(".streamlit", exist_ok=True)
        config_path = os.path.join(".streamlit", "config.toml")
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("[server]\n")
                f.write("maxUploadSize = 1000\n")
                f.write("maxMessageSize = 1000\n")
    except Exception:
        pass

setup_streamlit_config()

# ==============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Sistema de Processamento Unificado 2026",
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
if "parsed_duimp" not in st.session_state:
    st.session_state["parsed_duimp"] = None
if "parsed_hafele" not in st.session_state:
    st.session_state["parsed_hafele"] = None
if "merged_df" not in st.session_state:
    st.session_state["merged_df"] = None
if "last_duimp_name" not in st.session_state:
    st.session_state["last_duimp_name"] = None
if "last_app2_name" not in st.session_state:
    st.session_state["last_app2_name"] = None
if "fonte_fiscal_escolhida" not in st.session_state:
    st.session_state["fonte_fiscal_escolhida"] = None

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# ANIMAÇÕES DE CARREGAMENTO
# ==============================================================================
def show_loading_animation(message="Processando..."):
    with st.spinner(message):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)
        progress_bar.empty()

def show_processing_animation(message="Analisando dados..."):
    placeholder = st.empty()
    with placeholder.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info(f"⏳ {message}")
            spinner_placeholder = st.empty()
            spinner_chars = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
            for i in range(20):
                spinner_placeholder.markdown(
                    f"<div style='text-align: center; font-size: 24px;'>{spinner_chars[i % 8]}</div>",
                    unsafe_allow_html=True
                )
                time.sleep(0.1)
    placeholder.empty()

def show_success_animation(message="Concluído!"):
    success_placeholder = st.empty()
    with success_placeholder.container():
        st.success(f"✅ {message}")
        time.sleep(1.5)
    success_placeholder.empty()

# ==============================================================================
# CSS
# ==============================================================================
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
        .cover-logo { max-width: 300px; margin-bottom: 1.5rem; }
        .cover-title {
            font-size: 2.8rem; font-weight: 800; margin-bottom: 1rem;
            background: linear-gradient(90deg, #2c3e50, #3498db);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .cover-subtitle { font-size: 1.2rem; color: #7f8c8d; margin-bottom: 0; }
        .header {
            font-size: 1.8rem; font-weight: 700; margin: 1.5rem 0 1rem 0;
            padding-left: 10px; border-left: 5px solid #2c3e50;
        }
        .card {
            background: white; border-radius: 12px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            padding: 1.8rem; margin-bottom: 1.8rem;
        }
        .stButton>button { width: 100%; }
        .main-header { font-size: 2.5rem; color: #1E3A8A; font-weight: bold; margin-bottom: 1rem; }
        .sub-header { font-size: 1.5rem; color: #2563EB; margin-top: 1.5rem; border-bottom: 2px solid #E5E7EB; }
        .section-card {
            background: #FFFFFF; border-radius: 12px; padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1rem;
            border: 1px solid #E5E7EB;
        }
        .success-box { background-color: #d1fae5; color: #065f46; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .info-box { background-color: #dbeafe; color: #1e40af; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# PARTE 1: PROCESSADOR DE ARQUIVOS TXT
# ==============================================================================
def processador_txt():
    st.title("📄 Processador de Arquivos TXT")
    st.markdown("""
    <div class="card">
        Remova linhas indesejadas de arquivos TXT. Carregue seu arquivo e defina os padrões a serem removidos.
    </div>
    """, unsafe_allow_html=True)

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

    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
    arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'])

    with st.expander("⚙️ Configurações avançadas", expanded=False):
        padroes_adicionais = st.text_input(
            "Padrões adicionais para remoção (separados por vírgula)",
            help="Exemplo: padrão1, padrão2, padrão3"
        )
        padroes = padroes_default + [
            p.strip() for p in padroes_adicionais.split(",") if p.strip()
        ] if padroes_adicionais else padroes_default

    if arquivo is not None:
        if st.button("🔄 Processar Arquivo TXT"):
            try:
                show_loading_animation("Analisando arquivo TXT...")
                conteudo = arquivo.read()
                show_processing_animation("Processando linhas...")
                resultado, total_linhas = processar_arquivo(conteudo, padroes)
                if resultado is not None:
                    show_success_animation("Arquivo processado com sucesso!")
                    linhas_processadas = len(resultado.splitlines())
                    st.success(f"""
                    **Processamento concluído!** ✔️ Linhas originais: {total_linhas}
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

# ==============================================================================
# PARTE 2: PROCESSADOR CT-E
# ==============================================================================
class CTeProcessorDirect:
    def __init__(self):
        self.processed_data = []

    def extract_nfe_number_from_key(self, chave_acesso):
        if not chave_acesso or len(chave_acesso) != 44:
            return None
        try:
            return chave_acesso[25:34]
        except Exception:
            return None

    def extract_peso_bruto(self, root):
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
            st.warning(f"Não foi possível extrair o peso: {str(e)}")
            return 0.0, "Erro na extração"

    def extract_cte_data(self, xml_content, filename):
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

            nCT = find_text(root, './/cte:nCT')
            dhEmi = find_text(root, './/cte:dhEmi')
            cMunIni = find_text(root, './/cte:cMunIni')
            UFIni = find_text(root, './/cte:UFIni')
            cMunFim = find_text(root, './/cte:cMunFim')
            UFFim = find_text(root, './/cte:UFFim')
            emit_xNome = find_text(root, './/cte:emit/cte:xNome')
            vTPrest = find_text(root, './/cte:vTPrest')
            rem_xNome = find_text(root, './/cte:rem/cte:xNome')
            dest_xNome = find_text(root, './/cte:dest/cte:xNome')
            dest_CNPJ = find_text(root, './/cte:dest/cte:CNPJ')
            dest_CPF = find_text(root, './/cte:dest/cte:CPF')
            documento_destinatario = dest_CNPJ or dest_CPF or 'N/A'
            dest_xLgr = find_text(root, './/cte:dest/cte:enderDest/cte:xLgr')
            dest_nro = find_text(root, './/cte:dest/cte:enderDest/cte:nro')
            dest_xBairro = find_text(root, './/cte:dest/cte:enderDest/cte:xBairro')
            dest_xMun = find_text(root, './/cte:dest/cte:enderDest/cte:xMun')
            dest_CEP = find_text(root, './/cte:dest/cte:enderDest/cte:CEP')
            dest_UF = find_text(root, './/cte:dest/cte:enderDest/cte:UF')

            endereco_destinatario = ""
            if dest_xLgr:
                endereco_destinatario += dest_xLgr
                if dest_nro: endereco_destinatario += f", {dest_nro}"
                if dest_xBairro: endereco_destinatario += f" - {dest_xBairro}"
                if dest_xMun: endereco_destinatario += f", {dest_xMun}"
                if dest_UF: endereco_destinatario += f"/{dest_UF}"
                if dest_CEP: endereco_destinatario += f" - CEP: {dest_CEP}"
            if not endereco_destinatario:
                endereco_destinatario = "N/A"

            infNFe_chave = find_text(root, './/cte:infNFe/cte:chave')
            numero_nfe = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            peso_bruto, tipo_peso_encontrado = self.extract_peso_bruto(root)

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
        results = {'success': 0, 'errors': 0, 'messages': []}
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
        if self.processed_data:
            return pd.DataFrame(self.processed_data)
        return pd.DataFrame()

    def clear_data(self):
        self.processed_data = []


def processador_cte():
    processor = CTeProcessorDirect()
    st.title("🚚 Processador de CT-e para Power BI")
    st.markdown("### Processa arquivos XML de CT-e e gera planilha para análise")

    with st.expander("ℹ️ Informações sobre a extração do Peso", expanded=True):
        st.markdown("""
        **Extração do Peso - Busca Inteligente:**
        O sistema busca o peso em **múltiplos campos** na seguinte ordem de prioridade:
        1. **PESO BRUTO** — Campo principal
        2. **PESO BASE DE CALCULO** — Campo alternativo 1
        3. **PESO BASE CÁLCULO** — Campo alternativo 2
        4. **PESO** — Campo genérico
        """)

    tab1, tab2, tab3 = st.tabs(["📤 Upload", "👀 Visualizar Dados", "📥 Exportar"])

    with tab1:
        st.header("Upload de CT-es")
        upload_option = st.radio("Selecione o tipo de upload:", ["Upload Individual", "Upload em Lote"])
        if upload_option == "Upload Individual":
            uploaded_file = st.file_uploader("Selecione um arquivo XML de CT-e", type=['xml'], key="single_cte")
            if uploaded_file and st.button("📊 Processar CT-e", key="process_single"):
                show_loading_animation("Analisando estrutura do XML...")
                show_processing_animation("Extraindo dados do CT-e...")
                success, message = processor.process_single_file(uploaded_file)
                if success:
                    show_success_animation("CT-e processado com sucesso!")
                    df = processor.get_dataframe()
                    if not df.empty:
                        ultimo_cte = df.iloc[-1]
                        st.info(f"""
                        **Extração bem-sucedida:**
                        - **Peso encontrado:** {ultimo_cte['Peso Bruto (kg)']} kg
                        - **Tipo de peso:** {ultimo_cte['Tipo de Peso Encontrado']}
                        """)
                else:
                    st.error(message)
        else:
            uploaded_files = st.file_uploader(
                "Selecione múltiplos arquivos XML de CT-e",
                type=['xml'], accept_multiple_files=True, key="multiple_cte"
            )
            if uploaded_files and st.button("📊 Processar Todos", key="process_multiple"):
                show_loading_animation(f"Iniciando processamento de {len(uploaded_files)} arquivos...")
                results = processor.process_multiple_files(uploaded_files)
                show_success_animation("Processamento em lote concluído!")
                st.success(f"""
                **Processamento concluído!** ✅ Sucessos: {results['success']}
                ❌ Erros: {results['errors']}
                """)
                df = processor.get_dataframe()
                if not df.empty:
                    tipos_peso = df['Tipo de Peso Encontrado'].value_counts()
                    peso_total = df['Peso Bruto (kg)'].sum()
                    st.info(f"""
                    **Estatísticas de extração:**
                    - Peso bruto total: {peso_total:,.2f} kg
                    - Peso médio por CT-e: {df['Peso Bruto (kg)'].mean():,.2f} kg
                    """)
                    for tipo, quantidade in tipos_peso.items():
                        st.write(f"  - **{tipo}**: {quantidade} CT-e(s)")
                if results['errors'] > 0:
                    with st.expander("Ver mensagens detalhadas"):
                        for msg in results['messages']:
                            st.write(f"- {msg}")

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
            col1, col2, col3 = st.columns(3)
            with col1:
                uf_filter = st.multiselect("Filtrar por UF Início", options=df['UF Início'].unique())
            with col2:
                uf_destino_filter = st.multiselect("Filtrar por UF Destino", options=df['UF Destino'].unique())
            with col3:
                tipo_peso_filter = st.multiselect("Filtrar por Tipo de Peso", options=df['Tipo de Peso Encontrado'].unique())
            st.subheader("Filtro por Peso Bruto")
            peso_min = float(df['Peso Bruto (kg)'].min())
            peso_max = float(df['Peso Bruto (kg)'].max())
            peso_filter = st.slider("Selecione a faixa de peso (kg)", peso_min, peso_max, (peso_min, peso_max))
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
            colunas_principais = [
                'Arquivo', 'nCT', 'Data Emissão', 'Emitente', 'Remetente',
                'Destinatário', 'UF Início', 'UF Destino', 'Peso Bruto (kg)',
                'Tipo de Peso Encontrado', 'Valor Prestação'
            ]
            st.dataframe(filtered_df[colunas_principais], use_container_width=True)
            with st.expander("📋 Ver todos os campos detalhados"):
                st.dataframe(filtered_df, use_container_width=True)
            st.subheader("📈 Estatísticas")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Valor Prestação", f"R$ {filtered_df['Valor Prestação'].sum():,.2f}")
            col2.metric("Peso Bruto Total", f"{filtered_df['Peso Bruto (kg)'].sum():,.2f} kg")
            col3.metric("Média Peso/CT-e", f"{filtered_df['Peso Bruto (kg)'].mean():,.2f} kg")
            col4.metric("Tipos de Peso", f"{filtered_df['Tipo de Peso Encontrado'].nunique()}")
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("📊 Distribuição por Tipo de Peso")
                if not filtered_df.empty:
                    tipo_counts = filtered_df['Tipo de Peso Encontrado'].value_counts()
                    fig_tipo = px.pie(values=tipo_counts.values, names=tipo_counts.index,
                                     title="Distribuição por Tipo de Peso Encontrado")
                    st.plotly_chart(fig_tipo, use_container_width=True)
            with col_chart2:
                st.subheader("📈 Relação Peso x Valor")
                if not filtered_df.empty:
                    fig_relacao = px.scatter(
                        filtered_df, x='Peso Bruto (kg)', y='Valor Prestação',
                        title="Relação entre Peso Bruto e Valor da Prestação",
                        color='Tipo de Peso Encontrado'
                    )
                    try:
                        x = filtered_df['Peso Bruto (kg)'].values
                        y = filtered_df['Valor Prestação'].values
                        mask = ~np.isnan(x) & ~np.isnan(y)
                        x_clean, y_clean = x[mask], y[mask]
                        if len(x_clean) > 1:
                            coefficients = np.polyfit(x_clean, y_clean, 1)
                            polynomial = np.poly1d(coefficients)
                            x_trend = np.linspace(x_clean.min(), x_clean.max(), 100)
                            fig_relacao.add_trace(go.Scatter(
                                x=x_trend, y=polynomial(x_trend),
                                mode='lines', name='Linha de Tendência',
                                line=dict(color='red', dash='dash'), opacity=0.7
                            ))
                    except Exception:
                        pass
                    st.plotly_chart(fig_relacao, use_container_width=True)
        else:
            st.info("Nenhum CT-e processado ainda. Faça upload de arquivos na aba 'Upload'.")

    with tab3:
        st.header("Exportar para Excel")
        df = processor.get_dataframe()
        if not df.empty:
            st.success(f"Pronto para exportar {len(df)} registros")
            export_option = st.radio("Formato de exportação:", ["Excel (.xlsx)", "CSV (.csv)"])
            st.subheader("Selecionar Colunas para Exportação")
            todas_colunas = df.columns.tolist()
            colunas_selecionadas = st.multiselect(
                "Selecione as colunas para exportar:", options=todas_colunas, default=todas_colunas
            )
            df_export = df[colunas_selecionadas] if colunas_selecionadas else df
            if export_option == "Excel (.xlsx)":
                show_processing_animation("Gerando arquivo Excel...")
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, sheet_name='Dados_CTe', index=False)
                output.seek(0)
                st.download_button(
                    label="📥 Baixar Planilha Excel", data=output,
                    file_name="dados_cte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                show_processing_animation("Gerando arquivo CSV...")
                csv = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar Arquivo CSV", data=csv,
                    file_name="dados_cte.csv", mime="text/csv"
                )
            with st.expander("📋 Prévia dos dados a serem exportados"):
                st.dataframe(df_export.head(10))
        else:
            st.warning("Nenhum dado disponível para exportação.")

# ==============================================================================
# PARTE 3: PARSER APP2 (HÄFELE / EXTRATO DUIMP)
# ==============================================================================
class HafelePDFParser:
    """Parser para o layout Extrato DUIMP (APP2.pdf)."""

    def __init__(self):
        self.documento = {'cabecalho': {}, 'itens': [], 'totais': {}}

    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            logger.info(f"Iniciando parsing APP2: {pdf_path}")
            text_chunks = []
            progress_text = st.empty()
            progress_bar = st.progress(0)
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                for i, page in enumerate(pdf.pages):
                    progress_text.text(f"Lendo página {i+1} de {total_pages} do Extrato Detalhado...")
                    progress_bar.progress((i + 1) / total_pages)
                    text = page.extract_text(layout=False)
                    if text:
                        text_chunks.append(text)
            progress_text.empty()
            progress_bar.empty()
            full_text = "\n".join(text_chunks)
            self._process_full_text(full_text)
            del text_chunks, full_text
            gc.collect()
            return self.documento
        except Exception as e:
            logger.error(f"Erro CRÍTICO no parsing APP2: {str(e)}")
            st.error(f"Erro ao ler o arquivo PDF: {str(e)}")
            return self.documento

    def _process_full_text(self, text: str):
        chunks = re.split(r'(ITENS\s+DA\s+DUIMP\s*-\s*\d+)', text, flags=re.IGNORECASE)
        items_found = []
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                header = chunks[i]
                content = chunks[i+1]
                item_num_match = re.search(r'(\d+)', header)
                item_num = int(item_num_match.group(1)) if item_num_match else i
                item_data = self._parse_item_block(item_num, content)
                if item_data:
                    items_found.append(item_data)
        else:
            st.warning("⚠️ O sistema não detectou o padrão 'ITENS DA DUIMP'. Verifique se o PDF está no formato correto.")
        self.documento['itens'] = items_found
        self._calculate_totals()

    def _parse_item_block(self, item_num: int, text: str) -> Dict:
        try:
            item = {
                'numero_item': item_num, 'ncm': '', 'codigo_interno': '',
                'nome_produto': '', 'quantidade': 0.0, 'quantidade_comercial': 0.0,
                'peso_liquido': 0.0, 'valor_total': 0.0,
                'ii_valor_devido': 0.0, 'ii_base_calculo': 0.0, 'ii_aliquota': 0.0,
                'ipi_valor_devido': 0.0, 'ipi_base_calculo': 0.0, 'ipi_aliquota': 0.0,
                'pis_valor_devido': 0.0, 'pis_base_calculo': 0.0, 'pis_aliquota': 0.0,
                'cofins_valor_devido': 0.0, 'cofins_base_calculo': 0.0, 'cofins_aliquota': 0.0,
                'frete_internacional': 0.0, 'seguro_internacional': 0.0, 'local_aduaneiro': 0.0,
                # Campos adicionais para leitura completa
                'valor_unitario': 0.0, 'moeda': 'DOLAR DOS EUA',
                'fornecedor_raw': '', 'endereco_raw': '', 'paisOrigem': '',
                'desc_complementar': '', 'descricao': '',
                'numero_serie': '', 'modelo': '', 'marca': '',
                'unidade_comercial': '', 'unidade_estatistica': '',
                'condicao_venda': '', 'incoterms': '',
                'data_embarque': '', 'local_embarque': '',
                'numero_conhecimento': '', 'numero_container': '',
                'peso_bruto_item': 0.0, 'volume_item': 0.0,
                'numero_li': '', 'numero_di': '',
                'taxa_cambio': 0.0, 'valor_fob_usd': 0.0,
                'valor_frete_usd': 0.0, 'valor_seguro_usd': 0.0,
                'valor_cif_usd': 0.0, 'valor_aduaneiro_brl': 0.0,
                'base_calculo_total': 0.0, 'total_impostos': 0.0,
                'valor_total_com_impostos': 0.0
            }

            # Extração aprimorada de código interno e NCM
            code_match = re.search(r'Código interno\s*([\d\.]+)', text, re.IGNORECASE)
            if code_match: item['codigo_interno'] = code_match.group(1).replace('.', '')

            ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', text)
            if ncm_match: item['ncm'] = ncm_match.group(1).replace('.', '')

            # Extração de nome do produto com mais padrões
            produto_patterns = [
                r'Nome do produto\s*[:\-]?\s*(.+?)(?=\n\s*(?:Código|Qtde|Valor|Peso|Frete|Seguro|II|IPI|PIS|COFINS|$))',
                r'Descrição\s*[:\-]?\s*(.+?)(?=\n\s*(?:Código|Qtde|Valor|Peso|Frete|Seguro|II|IPI|PIS|COFINS|$))',
                r'Produto\s*[:\-]?\s*(.+?)(?=\n\s*(?:Código|Qtde|Valor|Peso|Frete|Seguro|II|IPI|PIS|COFINS|$))'
            ]
            for pattern in produto_patterns:
                prod_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if prod_match:
                    item['nome_produto'] = re.sub(r'\s+', ' ', prod_match.group(1)).strip()
                    break

            # Quantidades com mais precisão
            qtd_com_match = re.search(r'Qtde Unid\. Comercial\s*([\d\.,]+)', text)
            if qtd_com_match: item['quantidade_comercial'] = self._parse_valor(qtd_com_match.group(1))

            qtd_est_match = re.search(r'Qtde Unid\. Estatística\s*([\d\.,]+)', text)
            if qtd_est_match: item['quantidade'] = self._parse_valor(qtd_est_match.group(1))
            else: item['quantidade'] = item['quantidade_comercial']

            # Valores totais e unitários
            val_match = re.search(r'Valor Tot\. Cond Venda\s*([\d\.,]+)', text)
            if val_match: item['valor_total'] = self._parse_valor(val_match.group(1))

            val_unit_match = re.search(r'Valor Unitário\s*([\d\.,]+)', text)
            if val_unit_match: item['valor_unitario'] = self._parse_valor(val_unit_match.group(1))

            # Pesos
            peso_match = re.search(r'Peso Líquido \(KG\)\s*([\d\.,]+)', text, re.IGNORECASE)
            if peso_match: item['peso_liquido'] = self._parse_valor(peso_match.group(1))

            peso_bruto_match = re.search(r'Peso Bruto \(KG\)\s*([\d\.,]+)', text, re.IGNORECASE)
            if peso_bruto_match: item['peso_bruto_item'] = self._parse_valor(peso_bruto_match.group(1))

            # Frete, Seguro e Aduaneiro
            frete_match = re.search(r'Frete Internac\. \(R\$\)\s*([\d\.,]+)', text)
            if frete_match: item['frete_internacional'] = self._parse_valor(frete_match.group(1))

            seg_match = re.search(r'Seguro Internac\. \(R\$\)\s*([\d\.,]+)', text)
            if seg_match: item['seguro_internacional'] = self._parse_valor(seg_match.group(1))

            aduana_match = re.search(r'Local Aduaneiro \(R\$\)\s*([\d\.,]+)', text)
            if aduana_match: item['local_aduaneiro'] = self._parse_valor(aduana_match.group(1))

            # Volume
            volume_match = re.search(r'Volume\s*\(M3\)\s*([\d\.,]+)', text, re.IGNORECASE)
            if volume_match: item['volume_item'] = self._parse_valor(volume_match.group(1))

            # Moeda
            moeda_match = re.search(r'Moeda\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if moeda_match: item['moeda'] = moeda_match.group(1).strip()

            # País de origem
            pais_match = re.search(r'País de origem\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if pais_match: item['paisOrigem'] = pais_match.group(1).strip()

            # Fornecedor e endereço
            fornecedor_match = re.search(r'Fornecedor\s*[:\-]?\s*(.+?)(?=\n\s*(?:Endereço|País|$))', text, re.IGNORECASE | re.DOTALL)
            if fornecedor_match: item['fornecedor_raw'] = fornecedor_match.group(1).strip()

            endereco_match = re.search(r'Endereço\s*[:\-]?\s*(.+?)(?=\n\s*(?:País|Código|$))', text, re.IGNORECASE | re.DOTALL)
            if endereco_match: item['endereco_raw'] = endereco_match.group(1).strip()

            # Descrição complementar
            desc_comp_match = re.search(r'Descrição complementar\s*[:\-]?\s*(.+?)(?=\n\s*(?:Nome|Produto|$))', text, re.IGNORECASE | re.DOTALL)
            if desc_comp_match: item['desc_complementar'] = desc_comp_match.group(1).strip()

            # Número de série, modelo, marca
            serie_match = re.search(r'Número de série\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if serie_match: item['numero_serie'] = serie_match.group(1).strip()

            modelo_match = re.search(r'Modelo\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if modelo_match: item['modelo'] = modelo_match.group(1).strip()

            marca_match = re.search(r'Marca\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if marca_match: item['marca'] = marca_match.group(1).strip()

            # Unidades
            unid_com_match = re.search(r'Unidade comercial\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if unid_com_match: item['unidade_comercial'] = unid_com_match.group(1).strip()

            unid_est_match = re.search(r'Unidade estatística\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if unid_est_match: item['unidade_estatistica'] = unid_est_match.group(1).strip()

            # Condição de venda e Incoterms
            cond_venda_match = re.search(r'Condição de venda\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if cond_venda_match: item['condicao_venda'] = cond_venda_match.group(1).strip()

            incoterms_match = re.search(r'Incoterms\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if incoterms_match: item['incoterms'] = incoterms_match.group(1).strip()

            # Datas e locais
            data_embarque_match = re.search(r'Data de embarque\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if data_embarque_match: item['data_embarque'] = data_embarque_match.group(1).strip()

            local_embarque_match = re.search(r'Local de embarque\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if local_embarque_match: item['local_embarque'] = local_embarque_match.group(1).strip()

            # Números de documentos
            conhecimento_match = re.search(r'Número do conhecimento\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if conhecimento_match: item['numero_conhecimento'] = conhecimento_match.group(1).strip()

            container_match = re.search(r'Número do container\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if container_match: item['numero_container'] = container_match.group(1).strip()

            li_match = re.search(r'Número LI\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if li_match: item['numero_li'] = li_match.group(1).strip()

            di_match = re.search(r'Número DI\s*[:\-]?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
            if di_match: item['numero_di'] = di_match.group(1).strip()

            # Valores em USD
            fob_usd_match = re.search(r'FOB \(USD\)\s*([\d\.,]+)', text)
            if fob_usd_match: item['valor_fob_usd'] = self._parse_valor(fob_usd_match.group(1))

            frete_usd_match = re.search(r'Frete \(USD\)\s*([\d\.,]+)', text)
            if frete_usd_match: item['valor_frete_usd'] = self._parse_valor(frete_usd_match.group(1))

            seguro_usd_match = re.search(r'Seguro \(USD\)\s*([\d\.,]+)', text)
            if seguro_usd_match: item['valor_seguro_usd'] = self._parse_valor(seguro_usd_match.group(1))

            cif_usd_match = re.search(r'CIF \(USD\)\s*([\d\.,]+)', text)
            if cif_usd_match: item['valor_cif_usd'] = self._parse_valor(cif_usd_match.group(1))

            # Taxa de câmbio
            cambio_match = re.search(r'Taxa de câmbio\s*[:\-]?\s*([\d\.,]+)', text, re.IGNORECASE)
            if cambio_match: item['taxa_cambio'] = self._parse_valor(cambio_match.group(1))

            # Impostos com padrões mais robustos
            tax_patterns = re.findall(
                r'Base de Cálculo.*?\(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor.*?(?:Devido|A Recolher|Calculado).*?\(R\$\)\s*([\d\.,]+)',
                text, re.DOTALL | re.IGNORECASE
            )
            for base_str, aliq_str, val_str in tax_patterns:
                base = self._parse_valor(base_str)
                aliq = self._parse_valor(aliq_str)
                val = self._parse_valor(val_str)
                if 1.60 <= aliq <= 3.00:
                    item['pis_aliquota'] = aliq; item['pis_base_calculo'] = base; item['pis_valor_devido'] = val
                elif 7.00 <= aliq <= 12.00:
                    item['cofins_aliquota'] = aliq; item['cofins_base_calculo'] = base; item['cofins_valor_devido'] = val
                elif aliq > 12.00:
                    item['ii_aliquota'] = aliq; item['ii_base_calculo'] = base; item['ii_valor_devido'] = val
                elif aliq >= 0:
                    if item['ipi_aliquota'] == 0:
                        item['ipi_aliquota'] = aliq; item['ipi_base_calculo'] = base; item['ipi_valor_devido'] = val

            # Cálculos finais
            item['base_calculo_total'] = item['valor_total'] + item['frete_internacional'] + item['seguro_internacional'] + item['local_aduaneiro']
            item['total_impostos'] = (item['ii_valor_devido'] + item['ipi_valor_devido'] +
                                      item['pis_valor_devido'] + item['cofins_valor_devido'])
            item['valor_total_com_impostos'] = item['valor_total'] + item['total_impostos']

            return item
        except Exception as e:
            logger.error(f"Erro item {item_num}: {e}")
            return None

    def _parse_valor(self, valor_str: str) -> float:
        try:
            if not valor_str: return 0.0
            return float(valor_str.replace('.', '').replace(',', '.'))
        except:
            return 0.0

    def _calculate_totals(self):
        if self.documento['itens']:
            self.documento['totais'] = {
                'valor_total_mercadoria': sum(i['valor_total'] for i in self.documento['itens']),
                'total_impostos': sum(i['total_impostos'] for i in self.documento['itens'])
            }

# ==============================================================================
# PARTE 4: PARSER SIGRAWEB (NOVO — equivalente ao HafelePDFParser)
# ==============================================================================
class SigrawebPDFParser:
    """
    Parser para o layout Sigraweb — Conferência do Processo Detalhado.
    Mesma interface de retorno que HafelePDFParser:
      { 'cabecalho': {}, 'itens': [], 'totais': {} }

    Estrutura do PDF Sigraweb:
      Pág. 1  → cabeçalho geral (DI, CNPJ, pesos, datas, taxa câmbio…)
      Pág. 2  → totais de tributos + tabela-resumo por adição
      Págs. 3+ → uma seção por adição iniciada por "Informações da Adição Nº: N"
                  com: alíquotas II/IPI/PIS/COFINS, Part Number, descrição,
                  quantidade, pesos, FOB/frete/seguro/aduaneiro em BRL.
    """

    def __init__(self):
        self.documento: Dict = {'cabecalho': {}, 'itens': [], 'totais': {}}

    # ── Entrada principal ──────────────────────────────────────────────────────
    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            logger.info(f"Iniciando parsing Sigraweb: {pdf_path}")
            text_chunks: List[str] = []
            progress_text = st.empty()
            progress_bar = st.progress(0)
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                for i, page in enumerate(pdf.pages):
                    progress_text.text(f"Lendo página {i+1} de {total_pages} do Sigraweb...")
                    progress_bar.progress((i + 1) / total_pages)
                    text = page.extract_text(layout=False)
                    if text:
                        text_chunks.append(text)
            progress_text.empty()
            progress_bar.empty()
            full_text = "\n".join(text_chunks)
            self._process_full_text(full_text)
            del text_chunks, full_text
            gc.collect()
            return self.documento
        except Exception as e:
            logger.error(f"Erro CRÍTICO no parsing Sigraweb: {e}")
            st.error(f"Erro ao ler o arquivo Sigraweb: {e}")
            return self.documento

    # ── Orquestrador ───────────────────────────────────────────────────────────
    def _process_full_text(self, text: str):
        self._extract_header(text)
        self._extract_items(text)
        self._calculate_totals()

    # ── Cabeçalho geral ────────────────────────────────────────────────────────
    def _extract_header(self, text: str):
        h = self.documento['cabecalho']
        h['numeroDUIMP']      = self._rx(r"Número DI:\s*([\w\/\-\.]+)", text)
        h['cnpj']             = self._rx(r"CNPJ:\s*([\d\.\/\-]+)", text)
        h['nomeImportador']   = self._rx(r"Nome da Empresa:\s*HAFELE BRASIL[^\n]*\n(.+)", text) \
                                or self._rx(r"Nome da Empresa:\s*(.+)", text)
        h['pesoBruto']        = self._rx(r"Peso Bruto:\s*([\d\.,]+)", text)
        h['pesoLiquido']      = self._rx(r"Peso Líquido:\s*([\d\.,]+)", text)
        h['volumes']          = self._rx(r"Volumes:\s*(\d+)", text)
        h['embalagem']        = self._rx(r"Embalagem:\s*(.+)", text)
        h['recinto']          = self._rx(r"Recinto:\s*([\d]+)", text)
        h['urf']              = self._rx(r"URF de Entrada:\s*([\d]+)", text)
        h['urfDespacho']      = self._rx(r"URF de Despacho:\s*([\d]+)", text)
        h['viaTransporte']    = self._rx(r"Via Transporte:\s*(.+)", text)
        h['incoterms']        = self._rx(r"Incoterms:\s*(\w+)", text)
        h['paisProcedencia']  = self._rx(r"País de Procedência:\s*[\d]+\s*(.+)", text)
        h['localEmbarque']    = self._rx(r"Local de Embarque:\s*(.+)", text)
        h['dataEmbarque']     = self._rx(r"Data de Embarque:\s*([\d\/]+)", text)
        h['taxaDolar']        = self._rx(r"Taxa do Dólar:\s*([\d\.,]+)", text)
        h['conhecimento']     = self._rx(r"IDT\.\s*Conhecimento:\s*([\w]+)", text)
        h['fobUSD']           = self._parse_valor(self._rx(r"FOB:\s*([\d\.,]+)\s*\(USD\)", text))
        h['fobBRL']           = self._parse_valor(self._rx(r"FOB:.*?\(USD\)\s*;\s*([\d\.,]+)\s*\(BRL\)", text))
        h['freteUSD']         = self._parse_valor(self._rx(r"Frete:\s*([\d\.,]+)\s*\(USD\)", text))
        h['freteBRL']         = self._parse_valor(self._rx(r"Frete:.*?\(USD\)\s*;\s*([\d\.,]+)\s*\(BRL\)", text))
        h['seguroUSD']        = self._parse_valor(self._rx(r"Seguro:\s*([\d\.,]+)\s*\(USD\)", text))
        h['seguroBRL']        = self._parse_valor(self._rx(r"Seguro:.*?\(USD\)\s*;\s*([\d\.,]+)\s*\(BRL\)", text))
        h['valorAduaneiroBRL']= self._parse_valor(self._rx(r"Valor Aduaneiro:.*?\(USD\);\s*([\d\.,]+)\s*\(BRL\)", text))
        h['iiTotal']          = self._parse_valor(self._rx(r"TOTAL DO.*?PIS A PAGAR.*?:\s*([\d\.,]+)", text))
        h['pisTotal']         = self._parse_valor(self._rx(r"TOTAL DO PIS A PAGAR.*?:\s*([\d\.,]+)", text))
        h['cofinsTotal']      = self._parse_valor(self._rx(r"TOTAL DO COFINS A PAGAR.*?:\s*([\d\.,]+)", text))
        h['siscomex']         = self._parse_valor(self._rx(r"SISCOMEX\s+([\d\.,]+)", text))

    # ── Itens por adição ───────────────────────────────────────────────────────
    def _extract_items(self, text: str):
        chunks = re.split(
            r"(Informações\s+da\s+Adição\s+Nº:\s*\d+)",
            text, flags=re.IGNORECASE
        )
        items_found = []
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                header  = chunks[i]
                content = chunks[i + 1] if (i + 1) < len(chunks) else ""
                num_m   = re.search(r"(\d+)", header)
                item_num = int(num_m.group(1)) if num_m else i
                item_data = self._parse_item_block(item_num, content)
                if item_data:
                    items_found.append(item_data)
        else:
            st.warning(
                "⚠️ O sistema não detectou o padrão 'Informações da Adição Nº'. "
                "Verifique se o PDF está no formato Sigraweb padrão."
            )
        self.documento['itens'] = items_found

    def _parse_item_block(self, item_num: int, text: str) -> Optional[Dict]:
        try:
            item = {
                'numero_item':          item_num,
                'ncm':                  '',
                'codigo_interno':       '',
                'nome_produto':         '',
                'quantidade':           0.0,
                'quantidade_comercial': 0.0,
                'peso_liquido':         0.0,
                'valor_total':          0.0,
                'valor_unitario':       0.0,
                'moeda':                'DOLAR DOS EUA',
                'frete_internacional':  0.0,
                'seguro_internacional': 0.0,
                'local_aduaneiro':      0.0,
                'ii_base_calculo':      0.0,
                'ii_aliquota':          0.0,
                'ii_valor_devido':      0.0,
                'ipi_base_calculo':     0.0,
                'ipi_aliquota':         0.0,
                'ipi_valor_devido':     0.0,
                'pis_base_calculo':     0.0,
                'pis_aliquota':         0.0,
                'pis_valor_devido':     0.0,
                'cofins_base_calculo':  0.0,
                'cofins_aliquota':      0.0,
                'cofins_valor_devido':  0.0,
                'fornecedor_raw':       'HAFELE ENGINEERING ASIA LTD.',
                'endereco_raw':         'EXTERIOR',
                'paisOrigem':           'China, Republica Popular',
                'desc_complementar':    '',
                'descricao':            '',
            }

            # NCM
            ncm_m = re.search(r"NR NCM:\s*([\d\.]+)", text)
            if ncm_m:
                item['ncm'] = ncm_m.group(1).replace('.', '')

            # Part Number → código interno e desc_complementar
            pn_m = re.search(r"Part Number:\s*([\d\.]+)", text)
            if pn_m:
                item['codigo_interno']    = pn_m.group(1).replace('.', '')
                item['desc_complementar'] = pn_m.group(1)

            # Descrição do produto
            desc_m = re.search(
                r"Part Number:.*?\|\s*Descrição:\s*(.+?)(?=\nFabricante:|\nMotivo:|\Z)",
                text, re.DOTALL
            )
            if desc_m:
                descricao_limpa = re.sub(r'\s+', ' ', desc_m.group(1)).strip()
                item['nome_produto'] = descricao_limpa
                item['descricao']    = descricao_limpa

            # Quantidade comercial ("Quantidade: 1.680,00")
            qtd_m = re.search(r"Quantidade:\s*([\d\.,]+)", text)
            if qtd_m:
                item['quantidade_comercial'] = self._parse_valor(qtd_m.group(1))
                item['quantidade']           = item['quantidade_comercial']

            # Quantidade estatística ("Qnt. Estatística: 1.211,77")
            qe_m = re.search(r"Qnt\.\s*Estat[íi]stica:\s*([\d\.,]+)", text)
            if qe_m:
                item['quantidade'] = self._parse_valor(qe_m.group(1))

            # Peso líquido
            pl_m = re.search(r"Peso\s*Líquido:\s*([\d\.,]+)", text)
            if pl_m:
                item['peso_liquido'] = self._parse_valor(pl_m.group(1))

            # Valor unitário
            vu_m = re.search(r"Valor\s*Unitário:\s*([\d\.,]+)", text)
            if vu_m:
                item['valor_unitario'] = self._parse_valor(vu_m.group(1))

            # FOB BRL
            fob_m = re.search(r"Valor\s*FOB\s*Real:\s*([\d\.,]+)\s*BRL", text)
            if fob_m:
                item['valor_total'] = self._parse_valor(fob_m.group(1))

            # Frete BRL
            frete_m = re.search(r"Valor\s*Frete\s*Real:\s*([\d\.,]+)\s*BRL", text)
            if frete_m:
                item['frete_internacional'] = self._parse_valor(frete_m.group(1))

            # Seguro BRL
            seg_m = re.search(r"Valor\s*Seguro\s*Real:\s*([\d\.,]+)\s*BRL", text)
            if seg_m:
                item['seguro_internacional'] = self._parse_valor(seg_m.group(1))

            # Valor aduaneiro BRL
            vad_m = re.search(r"Valor\s*Aduaneiro\s*Real:\s*([\d\.,]+)\s*BRL", text)
            if vad_m:
                item['local_aduaneiro'] = self._parse_valor(vad_m.group(1))

            # ── Tabela de alíquotas ─────────────────────────────────────────
            # Formato:  "II  14,4000  1.016,06  0,0000  0,00  0,0000  36.884,82  5.311,41"
            # Colunas:   tributo | alíq.adval | vl.alíq.adval | alíq.red | vl.alíq.red | %red | base | valor
            tax_pat = re.compile(
                r"^(II|IPI|PIS|COFINS)\s+"
                r"([\d\.,]+)\s+"   # alíquota ad valorem
                r"([\d\.,]+)\s+"   # valor alíq. ad valorem
                r"([\d\.,]+)\s+"   # alíquota reduzida
                r"([\d\.,]+)\s+"   # valor alíq. reduzida
                r"([\d\.,]+)\s+"   # % redução base
                r"([\d\.,]+)\s+"   # base de cálculo
                r"([\d\.,]+)",     # valor do tributo
                re.MULTILINE
            )
            for m in tax_pat.finditer(text):
                trib   = m.group(1).upper()
                aliq   = self._parse_valor(m.group(2))
                base   = self._parse_valor(m.group(7))
                valor  = self._parse_valor(m.group(8))
                if trib == "II":
                    item['ii_aliquota'] = aliq; item['ii_base_calculo'] = base; item['ii_valor_devido'] = valor
                elif trib == "IPI":
                    item['ipi_aliquota'] = aliq; item['ipi_base_calculo'] = base; item['ipi_valor_devido'] = valor
                elif trib == "PIS":
                    item['pis_aliquota'] = aliq; item['pis_base_calculo'] = base; item['pis_valor_devido'] = valor
                elif trib == "COFINS":
                    item['cofins_aliquota'] = aliq; item['cofins_base_calculo'] = base; item['cofins_valor_devido'] = valor

            # País de origem
            po_m = re.search(r"País\s*Origem:\s*(.+)", text)
            if po_m:
                item['paisOrigem'] = po_m.group(1).strip()

            # Totais
            item['total_impostos'] = (item['ii_valor_devido'] + item['ipi_valor_devido'] +
                                      item['pis_valor_devido'] + item['cofins_valor_devido'])
            item['valor_total_com_impostos'] = item['valor_total'] + item['total_impostos']
            return item

        except Exception as e:
            logger.error(f"Erro ao parsear adição Sigraweb {item_num}: {e}")
            return None

    def _calculate_totals(self):
        itens = self.documento['itens']
        if itens:
            self.documento['totais'] = {
                'valor_total_mercadoria': sum(i['valor_total']           for i in itens),
                'total_impostos':         sum(i['total_impostos']        for i in itens),
                'ii_total':               sum(i['ii_valor_devido']       for i in itens),
                'ipi_total':              sum(i['ipi_valor_devido']      for i in itens),
                'pis_total':              sum(i['pis_valor_devido']      for i in itens),
                'cofins_total':           sum(i['cofins_valor_devido']   for i in itens),
            }

    @staticmethod
    def _rx(pattern: str, text: str) -> str:
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _parse_valor(valor_str) -> float:
        try:
            if not valor_str: return 0.0
            return float(str(valor_str).replace('.', '').replace(',', '.'))
        except Exception:
            return 0.0

# ==============================================================================
# PARTE 5: PARSER APP 1 (DUIMP) E FUNÇÕES AUXILIARES
# ==============================================================================
def montar_descricao_final(desc_complementar, codigo_extra, detalhamento):
    parte1 = str(desc_complementar).strip()
    parte2 = str(codigo_extra).strip()
    parte3 = str(detalhamento).strip()
    return f"{parte1} - {parte2} - {parte3}"


class DuimpPDFParser:
    def __init__(self, file_stream):
        self.doc = fitz.open(stream=file_stream, filetype="pdf")
        self.full_text = ""
        self.header = {}
        self.items = []

    def preprocess(self):
        clean_lines = []
        for page in self.doc:
            text = page.get_text("text")
            lines = text.split('\n')
            for line in lines:
                l_strip = line.strip()
                if "Extrato da DUIMP" in l_strip: continue
                if "Data, hora e responsável" in l_strip: continue
                if re.match(r'^\d+\s*/\s*\d+$', l_strip): continue
                clean_lines.append(line)
        self.full_text = "\n".join(clean_lines)
        self.doc.close()
        gc.collect()

    def extract_header(self):
        txt = self.full_text
        self.header["numeroDUIMP"]    = self._regex(r"Extrato da Duimp\s+([\w\-\/]+)", txt)
        self.header["cnpj"]           = self._regex(r"CNPJ do importador:\s*([\d\.\/\-]+)", txt)
        self.header["nomeImportador"] = self._regex(r"Nome do importador:\s*\n?(.+)", txt)
        self.header["pesoBruto"]      = self._regex(r"Peso Bruto \(kg\):\s*([\d\.,]+)", txt)
        self.header["pesoLiquido"]    = self._regex(r"Peso Liquido \(kg\):\s*([\d\.,]+)", txt)
        self.header["urf"]            = self._regex(r"Unidade de despacho:\s*([\d]+)", txt)
        self.header["paisProcedencia"]= self._regex(r"País de Procedência:\s*\n?(.+)", txt)

    def extract_items(self):
        chunks = re.split(r"Item\s+(\d+)", self.full_text)
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                num = chunks[i]
                content = chunks[i+1]
                item = {"numeroAdicao": num}
                item["ncm"]                 = self._regex(r"NCM:\s*([\d\.]+)", content)
                item["paisOrigem"]          = self._regex(r"País de origem:\s*\n?(.+)", content)
                item["quantidade"]          = self._regex(r"Quantidade na unidade estatística:\s*([\d\.,]+)", content)
                item["quantidade_comercial"]= self._regex(r"Quantidade na unidade comercializada:\s*([\d\.,]+)", content)
                item["unidade"]             = self._regex(r"Unidade estatística:\s*(.+)", content)
                item["pesoLiq"]             = self._regex(r"Peso líquido \(kg\):\s*([\d\.,]+)", content)
                item["valorUnit"]           = self._regex(r"Valor unitário na condição de venda:\s*([\d\.,]+)", content)
                item["valorTotal"]          = self._regex(r"Valor total na condição de venda:\s*([\d\.,]+)", content)
                item["moeda"]               = self._regex(r"Moeda negociada:\s*(.+)", content)
                exp_match = re.search(
                    r"Código do Exportador Estrangeiro:\s*(.+?)(?=\n\s*(?:Endereço|Dados))", content, re.DOTALL
                )
                item["fornecedor_raw"] = exp_match.group(1).strip() if exp_match else ""
                addr_match = re.search(
                    r"Endereço:\s*(.+?)(?=\n\s*(?:Dados da Mercadoria|Aplicação))", content, re.DOTALL
                )
                item["endereco_raw"] = addr_match.group(1).strip() if addr_match else ""
                desc_match = re.search(
                    r"Detalhamento do Produto:\s*(.+?)(?=\n\s*(?:Número de Identificação|Versão|Código de Class|Descrição complementar))",
                    content, re.DOTALL
                )
                item["descricao"] = desc_match.group(1).strip() if desc_match else ""
                compl_match = re.search(
                    r"Descrição complementar da mercadoria:\s*(.+?)(?=\n|$)", content, re.DOTALL
                )
                item["desc_complementar"] = compl_match.group(1).strip() if compl_match else ""
                self.items.append(item)

    def _regex(self, pattern, text):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""

# ==============================================================================
# PARTE 6: XML BUILDER E CONSTANTES
# ==============================================================================
ADICAO_FIELDS_ORDER = [
    {"tag": "acrescimo", "type": "complex", "children": [
        {"tag": "codigoAcrescimo", "default": "17"},
        {"tag": "denominacao", "default": "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"},
        {"tag": "moedaNegociadaCodigo", "default": "978"},
        {"tag": "moedaNegociadaNome", "default": "EURO/COM.EUROPEIA"},
        {"tag": "valorMoedaNegociada", "default": "000000000000000"},
        {"tag": "valorReais", "default": "000000000000000"}
    ]},
    {"tag": "cideValorAliquotaEspecifica", "default": "00000000000"},
    {"tag": "cideValorDevido", "default": "000000000000000"},
    {"tag": "cideValorRecolher", "default": "000000000000000"},
    {"tag": "codigoRelacaoCompradorVendedor", "default": "3"},
    {"tag": "codigoVinculoCompradorVendedor", "default": "1"},
    {"tag": "cofinsAliquotaAdValorem", "default": "00965"},
    {"tag": "cofinsAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "cofinsAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "cofinsAliquotaReduzida", "default": "00000"},
    {"tag": "cofinsAliquotaValorDevido", "default": "000000000000000"},
    {"tag": "cofinsAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "condicaoVendaIncoterm", "default": "FCA"},
    {"tag": "condicaoVendaLocal", "default": ""},
    {"tag": "condicaoVendaMetodoValoracaoCodigo", "default": "01"},
    {"tag": "condicaoVendaMetodoValoracaoNome", "default": "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"},
    {"tag": "condicaoVendaMoedaCodigo", "default": "978"},
    {"tag": "condicaoVendaMoedaNome", "default": "EURO/COM.EUROPEIA"},
    {"tag": "condicaoVendaValorMoeda", "default": "000000000000000"},
    {"tag": "condicaoVendaValorReais", "default": "000000000000000"},
    {"tag": "dadosCambiaisCoberturaCambialCodigo", "default": "1"},
    {"tag": "dadosCambiaisCoberturaCambialNome", "default": "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"},
    {"tag": "dadosCambiaisInstituicaoFinanciadoraCodigo", "default": "00"},
    {"tag": "dadosCambiaisInstituicaoFinanciadoraNome", "default": "N/I"},
    {"tag": "dadosCambiaisMotivoSemCoberturaCodigo", "default": "00"},
    {"tag": "dadosCambiaisMotivoSemCoberturaNome", "default": "N/I"},
    {"tag": "dadosCambiaisValorRealCambio", "default": "000000000000000"},
    {"tag": "dadosCargaPaisProcedenciaCodigo", "default": "000"},
    {"tag": "dadosCargaUrfEntradaCodigo", "default": "0000000"},
    {"tag": "dadosCargaViaTransporteCodigo", "default": "01"},
    {"tag": "dadosCargaViaTransporteNome", "default": "MARÍTIMA"},
    {"tag": "dadosMercadoriaAplicacao", "default": "REVENDA"},
    {"tag": "dadosMercadoriaCodigoNaladiNCCA", "default": "0000000"},
    {"tag": "dadosMercadoriaCodigoNaladiSH", "default": "00000000"},
    {"tag": "dadosMercadoriaCodigoNcm", "default": "00000000"},
    {"tag": "dadosMercadoriaCondicao", "default": "NOVA"},
    {"tag": "dadosMercadoriaDescricaoTipoCertificado", "default": "Sem Certificado"},
    {"tag": "dadosMercadoriaIndicadorTipoCertificado", "default": "1"},
    {"tag": "dadosMercadoriaMedidaEstatisticaQuantidade", "default": "00000000000000"},
    {"tag": "dadosMercadoriaMedidaEstatisticaUnidade", "default": "UNIDADE"},
    {"tag": "dadosMercadoriaNomeNcm", "default": "DESCRIÇÃO PADRÃO NCM"},
    {"tag": "dadosMercadoriaPesoLiquido", "default": "000000000000000"},
    {"tag": "dcrCoeficienteReducao", "default": "00000"},
    {"tag": "dcrIdentificacao", "default": "00000000"},
    {"tag": "dcrValorDevido", "default": "000000000000000"},
    {"tag": "dcrValorDolar", "default": "000000000000000"},
    {"tag": "dcrValorReal", "default": "000000000000000"},
    {"tag": "dcrValorRecolher", "default": "000000000000000"},
    {"tag": "fornecedorCidade", "default": ""},
    {"tag": "fornecedorLogradouro", "default": ""},
    {"tag": "fornecedorNome", "default": ""},
    {"tag": "fornecedorNumero", "default": ""},
    {"tag": "freteMoedaNegociadaCodigo", "default": "978"},
    {"tag": "freteMoedaNegociadaNome", "default": "EURO/COM.EUROPEIA"},
    {"tag": "freteValorMoedaNegociada", "default": "000000000000000"},
    {"tag": "freteValorReais", "default": "000000000000000"},
    {"tag": "iiAcordoTarifarioTipoCodigo", "default": "0"},
    {"tag": "iiAliquotaAcordo", "default": "00000"},
    {"tag": "iiAliquotaAdValorem", "default": "00000"},
    {"tag": "iiAliquotaPercentualReducao", "default": "00000"},
    {"tag": "iiAliquotaReduzida", "default": "00000"},
    {"tag": "iiAliquotaValorCalculado", "default": "000000000000000"},
    {"tag": "iiAliquotaValorDevido", "default": "000000000000000"},
    {"tag": "iiAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "iiAliquotaValorReduzido", "default": "000000000000000"},
    {"tag": "iiBaseCalculo", "default": "000000000000000"},
    {"tag": "iiFundamentoLegalCodigo", "default": "00"},
    {"tag": "iiMotivoAdmissaoTemporariaCodigo", "default": "00"},
    {"tag": "iiRegimeTributacaoCodigo", "default": "1"},
    {"tag": "iiRegimeTributacaoNome", "default": "RECOLHIMENTO INTEGRAL"},
    {"tag": "ipiAliquotaAdValorem", "default": "00000"},
    {"tag": "ipiAliquotaEspecificaCapacidadeRecipciente", "default": "00000"},
    {"tag": "ipiAliquotaEspecificaQuantidadeUnidadeMedida", "default": "000000000"},
    {"tag": "ipiAliquotaEspecificaTipoRecipienteCodigo", "default": "00"},
    {"tag": "ipiAliquotaEspecificaValorUnidadeMedida", "default": "0000000000"},
    {"tag": "ipiAliquotaNotaComplementarTIPI", "default": "00"},
    {"tag": "ipiAliquotaReduzida", "default": "00000"},
    {"tag": "ipiAliquotaValorDevido", "default": "000000000000000"},
    {"tag": "ipiAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "ipiRegimeTributacaoCodigo", "default": "4"},
    {"tag": "ipiRegimeTributacaoNome", "default": "SEM BENEFICIO"},
    {"tag": "mercadoria", "type": "complex", "children": [
        {"tag": "descricaoMercadoria", "default": ""},
        {"tag": "numeroSequencialItem", "default": "01"},
        {"tag": "quantidade", "default": "00000000000000"},
        {"tag": "unidadeMedida", "default": "UNIDADE"},
        {"tag": "valorUnitario", "default": "00000000000000000000"}
    ]},
    {"tag": "numeroAdicao", "default": "001"},
    {"tag": "numeroDUIMP", "default": ""},
    {"tag": "numeroLI", "default": "0000000000"},
    {"tag": "paisAquisicaoMercadoriaCodigo", "default": "000"},
    {"tag": "paisAquisicaoMercadoriaNome", "default": ""},
    {"tag": "paisOrigemMercadoriaCodigo", "default": "000"},
    {"tag": "paisOrigemMercadoriaNome", "default": ""},
    {"tag": "pisCofinsBaseCalculoAliquotaICMS", "default": "00000"},
    {"tag": "pisCofinsBaseCalculoFundamentoLegalCodigo", "default": "00"},
    {"tag": "pisCofinsBaseCalculoPercentualReducao", "default": "00000"},
    {"tag": "pisCofinsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "pisCofinsFundamentoLegalReducaoCodigo", "default": "00"},
    {"tag": "pisCofinsRegimeTributacaoCodigo", "default": "1"},
    {"tag": "pisCofinsRegimeTributacaoNome", "default": "RECOLHIMENTO INTEGRAL"},
    {"tag": "pisPasepAliquotaAdValorem", "default": "00000"},
    {"tag": "pisPasepAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "pisPasepAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "pisPasepAliquotaReduzida", "default": "00000"},
    {"tag": "pisPasepAliquotaValorDevido", "default": "000000000000000"},
    {"tag": "pisPasepAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "icmsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "icmsBaseCalculoAliquota", "default": "00000"},
    {"tag": "icmsBaseCalculoValorImposto", "default": "00000000000000"},
    {"tag": "icmsBaseCalculoValorDiferido", "default": "00000000000000"},
    {"tag": "cbsIbsCst", "default": "000"},
    {"tag": "cbsIbsClasstrib", "default": "000001"},
    {"tag": "cbsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "cbsBaseCalculoAliquota", "default": "00000"},
    {"tag": "cbsBaseCalculoAliquotaReducao", "default": "00000"},
    {"tag": "cbsBaseCalculoValorImposto", "default": "00000000000000"},
    {"tag": "ibsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "ibsBaseCalculoAliquota", "default": "00000"},
    {"tag": "ibsBaseCalculoAliquotaReducao", "default": "00000"},
    {"tag": "ibsBaseCalculoValorImposto", "default": "00000000000000"},
    {"tag": "relacaoCompradorVendedor", "default": "Fabricante é desconhecido"},
    {"tag": "seguroMoedaNegociadaCodigo", "default": "220"},
    {"tag": "seguroMoedaNegociadaNome", "default": "DOLAR DOS EUA"},
    {"tag": "seguroValorMoedaNegociada", "default": "000000000000000"},
    {"tag": "seguroValorReais", "default": "000000000000000"},
    {"tag": "sequencialRetificacao", "default": "00"},
    {"tag": "valorMultaARecolher", "default": "000000000000000"},
    {"tag": "valorMultaARecolherAjustado", "default": "000000000000000"},
    {"tag": "valorReaisFreteInternacional", "default": "000000000000000"},
    {"tag": "valorReaisSeguroInternacional", "default": "000000000000000"},
    {"tag": "valorTotalCondicaoVenda", "default": "00000000000"},
    {"tag": "vinculoCompradorVendedor", "default": "Não há vinculação entre comprador e vendedor."}
]

FOOTER_TAGS = {
    "armazem": {"tag": "nomeArmazem", "default": "TCP"},
    "armazenamentoRecintoAduaneiroCodigo": "9801303",
    "armazenamentoRecintoAduaneiroNome": "TCP - TERMINAL",
    "armazenamentoSetor": "002",
    "canalSelecaoParametrizada": "001",
    "caracterizacaoOperacaoCodigoTipo": "1",
    "caracterizacaoOperacaoDescricaoTipo": "Importação Própria",
    "cargaDataChegada": "20251120",
    "cargaNumeroAgente": "N/I",
    "cargaPaisProcedenciaCodigo": "386",
    "cargaPaisProcedenciaNome": "",
    "cargaPesoBruto": "000000000000000",
    "cargaPesoLiquido": "000000000000000",
    "cargaUrfEntradaCodigo": "0917800",
    "cargaUrfEntradaNome": "PORTO DE PARANAGUA",
    "conhecimentoCargaEmbarqueData": "20251025",
    "conhecimentoCargaEmbarqueLocal": "EXTERIOR",
    "conhecimentoCargaId": "CE123456",
    "conhecimentoCargaIdMaster": "CE123456",
    "conhecimentoCargaTipoCodigo": "12",
    "conhecimentoCargaTipoNome": "HBL - House Bill of Lading",
    "conhecimentoCargaUtilizacao": "1",
    "conhecimentoCargaUtilizacaoNome": "Total",
    "dataDesembaraco": "20251124",
    "dataRegistro": "20251124",
    "documentoChegadaCargaCodigoTipo": "1",
    "documentoChegadaCargaNome": "Manifesto da Carga",
    "documentoChegadaCargaNumero": "1625502058594",
    "embalagem": [
        {"tag": "codigoTipoEmbalagem", "default": "60"},
        {"tag": "nomeEmbalagem", "default": "PALLETS"},
        {"tag": "quantidadeVolume", "default": "00001"}
    ],
    "freteCollect": "000000000000000",
    "freteEmTerritorioNacional": "000000000000000",
    "freteMoedaNegociadaCodigo": "978",
    "freteMoedaNegociadaNome": "EURO/COM.EUROPEIA",
    "fretePrepaid": "000000000000000",
    "freteTotalDolares": "000000000000000",
    "freteTotalMoeda": "000000000000000",
    "freteTotalReais": "000000000000000",
    "icms": [
        {"tag": "agenciaIcms", "default": "00000"},
        {"tag": "codigoTipoRecolhimentoIcms", "default": "3"},
        {"tag": "nomeTipoRecolhimentoIcms", "default": "Exoneração do ICMS"},
        {"tag": "numeroSequencialIcms", "default": "001"},
        {"tag": "ufIcms", "default": "PR"},
        {"tag": "valorTotalIcms", "default": "000000000000000"}
    ],
    "importadorCodigoTipo": "1",
    "importadorCpfRepresentanteLegal": "00000000000",
    "importadorEnderecoBairro": "CENTRO",
    "importadorEnderecoCep": "00000000",
    "importadorEnderecoComplemento": "",
    "importadorEnderecoLogradouro": "RUA PRINCIPAL",
    "importadorEnderecoMunicipio": "CIDADE",
    "importadorEnderecoNumero": "00",
    "importadorEnderecoUf": "PR",
    "importadorNome": "",
    "importadorNomeRepresentanteLegal": "REPRESENTANTE",
    "importadorNumero": "",
    "importadorNumeroTelefone": "0000000000",
    "informacaoComplementar": "Informações extraídas do Extrato DUIMP.",
    "localDescargaTotalDolares": "000000000000000",
    "localDescargaTotalReais": "000000000000000",
    "localEmbarqueTotalDolares": "000000000000000",
    "localEmbarqueTotalReais": "000000000000000",
    "modalidadeDespachoCodigo": "1",
    "modalidadeDespachoNome": "Normal",
    "numeroDUIMP": "",
    "operacaoFundap": "N",
    "pagamento": [],
    "seguroMoedaNegociadaCodigo": "220",
    "seguroMoedaNegociadaNome": "DOLAR DOS EUA",
    "seguroTotalDolares": "000000000000000",
    "seguroTotalMoedaNegociada": "000000000000000",
    "seguroTotalReais": "000000000000000",
    "sequencialRetificacao": "00",
    "situacaoEntregaCarga": "ENTREGA CONDICIONADA",
    "tipoDeclaracaoCodigo": "01",
    "tipoDeclaracaoNome": "CONSUMO",
    "totalAdicoes": "000",
    "urfDespachoCodigo": "0917800",
    "urfDespachoNome": "PORTO DE PARANAGUA",
    "valorTotalMultaARecolherAjustado": "000000000000000",
    "viaTransporteCodigo": "01",
    "viaTransporteMultimodal": "N",
    "viaTransporteNome": "MARÍTIMA",
    "viaTransporteNomeTransportador": "MAERSK A/S",
    "viaTransporteNomeVeiculo": "MAERSK",
    "viaTransportePaisTransportadorCodigo": "741",
    "viaTransportePaisTransportadorNome": "CINGAPURA"
}


class DataFormatter:
    @staticmethod
    def clean_text(text):
        if not text: return ""
        text = text.replace('\n', ' ').replace('\r', '')
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def format_number(value, length=15):
        if not value: return "0" * length
        clean = re.sub(r'\D', '', str(value))
        if not clean: return "0" * length
        return clean.zfill(length)

    @staticmethod
    def format_ncm(value):
        if not value: return "00000000"
        return re.sub(r'\D', '', value)[:8]

    @staticmethod
    def format_input_fiscal(value, length=15, is_percent=False):
        try:
            if isinstance(value, str):
                value = value.replace('.', '').replace(',', '.')
            val_float = float(value)
            val_int = int(round(val_float * 100))
            return str(val_int).zfill(length)
        except:
            return "0" * length

    @staticmethod
    def format_high_precision(value, length=15):
        try:
            if isinstance(value, str):
                value = value.replace('.', '').replace(',', '.')
            val_float = float(value)
            val_int = int(round(val_float * 10000000))
            return str(val_int).zfill(length)
        except:
            return "0" * length

    @staticmethod
    def format_quantity(value, length=14):
        try:
            if isinstance(value, str):
                value = value.replace('.', '').replace(',', '.')
            val_float = float(value)
            val_int = int(round(val_float * 100000))
            return str(val_int).zfill(length)
        except:
            return "0" * length

    @staticmethod
    def calculate_cbs_ibs(base_xml_string):
        try:
            base_int = int(base_xml_string)
            base_float = base_int / 100.0
            cbs_val = base_float * 0.009
            cbs_str = str(int(round(cbs_val * 100))).zfill(14)
            ibs_val = base_float * 0.001
            ibs_str = str(int(round(ibs_val * 100))).zfill(14)
            return cbs_str, ibs_str
        except:
            return "0".zfill(14), "0".zfill(14)

    @staticmethod
    def parse_supplier_info(raw_name, raw_addr):
        data = {"fornecedorNome": "", "fornecedorLogradouro": "", "fornecedorNumero": "S/N", "fornecedorCidade": ""}
        if raw_name:
            parts = raw_name.split('-', 1)
            data["fornecedorNome"] = parts[-1].strip() if len(parts) > 1 else raw_name.strip()
        if raw_addr:
            clean_addr = DataFormatter.clean_text(raw_addr)
            parts_dash = clean_addr.rsplit('-', 1)
            if len(parts_dash) > 1:
                data["fornecedorCidade"] = parts_dash[1].strip()
                street_part = parts_dash[0].strip()
            else:
                data["fornecedorCidade"] = "EXTERIOR"
                street_part = clean_addr
            comma_split = street_part.rsplit(',', 1)
            if len(comma_split) > 1:
                data["fornecedorLogradouro"] = comma_split[0].strip()
                num_match = re.search(r'\d+', comma_split[1])
                if num_match: data["fornecedorNumero"] = num_match.group(0)
            else:
                data["fornecedorLogradouro"] = street_part
        return data


class XMLBuilder:
    def __init__(self, parser, edited_items=None):
        self.p = parser
        self.items_to_use = edited_items if edited_items else self.p.items
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self, user_inputs=None):
        h = self.p.header
        duimp_fmt = h.get("numeroDUIMP", "").split("/")[0].replace("-", "").replace(".", "")
        totals = {"frete": 0.0, "seguro": 0.0, "ii": 0.0, "ipi": 0.0, "pis": 0.0, "cofins": 0.0}

        def get_float(val):
            try:
                if isinstance(val, str): val = val.replace('.', '').replace(',', '.')
                return float(val)
            except: return 0.0

        for it in self.items_to_use:
            totals["frete"]  += get_float(it.get("Frete (R$)"))
            totals["seguro"] += get_float(it.get("Seguro (R$)"))
            totals["ii"]     += get_float(it.get("II (R$)"))
            totals["ipi"]    += get_float(it.get("IPI (R$)"))
            totals["pis"]    += get_float(it.get("PIS (R$)"))
            totals["cofins"] += get_float(it.get("COFINS (R$)"))

        for it in self.items_to_use:
            adicao = etree.SubElement(self.duimp, "adicao")
            input_number  = str(it.get("NUMBER", "")).strip()
            original_desc = DataFormatter.clean_text(it.get("descricao", ""))
            desc_compl    = DataFormatter.clean_text(it.get("desc_complementar", ""))
            final_desc    = montar_descricao_final(desc_compl, input_number, original_desc)

            val_total_venda_fmt = DataFormatter.format_high_precision(it.get("valorTotal", "0"), 11)
            val_unit_fmt        = DataFormatter.format_high_precision(it.get("valorUnit", "0"), 20)
            qtd_comercial_raw   = it.get("quantidade_comercial") or it.get("quantidade")
            qtd_comercial_fmt   = DataFormatter.format_quantity(qtd_comercial_raw, 14)
            qtd_estatistica_fmt = DataFormatter.format_quantity(it.get("quantidade"), 14)
            peso_liq_fmt        = DataFormatter.format_quantity(it.get("pesoLiq"), 15)
            base_total_reais_fmt= DataFormatter.format_input_fiscal(it.get("valorTotal", "0"), 15)

            raw_frete    = get_float(it.get("Frete (R$)", 0))
            raw_seguro   = get_float(it.get("Seguro (R$)", 0))
            raw_aduaneiro= get_float(it.get("Aduaneiro (R$)", 0))
            frete_fmt    = DataFormatter.format_input_fiscal(raw_frete)
            seguro_fmt   = DataFormatter.format_input_fiscal(raw_seguro)
            aduaneiro_fmt= DataFormatter.format_input_fiscal(raw_aduaneiro)

            ii_base_fmt  = DataFormatter.format_input_fiscal(it.get("II Base (R$)", 0))
            ii_aliq_fmt  = DataFormatter.format_input_fiscal(it.get("II Alíq. (%)", 0), 5, True)
            ii_val_fmt   = DataFormatter.format_input_fiscal(get_float(it.get("II (R$)", 0)))
            ipi_aliq_fmt = DataFormatter.format_input_fiscal(it.get("IPI Alíq. (%)", 0), 5, True)
            ipi_val_fmt  = DataFormatter.format_input_fiscal(get_float(it.get("IPI (R$)", 0)))
            pis_base_fmt = DataFormatter.format_input_fiscal(it.get("PIS Base (R$)", 0))
            pis_aliq_fmt = DataFormatter.format_input_fiscal(it.get("PIS Alíq. (%)", 0), 5, True)
            pis_val_fmt  = DataFormatter.format_input_fiscal(get_float(it.get("PIS (R$)", 0)))
            cofins_aliq_fmt = DataFormatter.format_input_fiscal(it.get("COFINS Alíq. (%)", 0), 5, True)
            cofins_val_fmt  = DataFormatter.format_input_fiscal(get_float(it.get("COFINS (R$)", 0)))

            icms_base_valor = ii_base_fmt if int(ii_base_fmt) > 0 else base_total_reais_fmt
            cbs_imposto, ibs_imposto = DataFormatter.calculate_cbs_ibs(icms_base_valor)
            supplier_data = DataFormatter.parse_supplier_info(it.get("fornecedor_raw"), it.get("endereco_raw"))

            extracted_map = {
                "numeroAdicao": str(it["numeroAdicao"])[-3:],
                "numeroDUIMP": duimp_fmt,
                "dadosMercadoriaCodigoNcm": DataFormatter.format_ncm(it.get("ncm")),
                "dadosMercadoriaMedidaEstatisticaQuantidade": qtd_estatistica_fmt,
                "dadosMercadoriaMedidaEstatisticaUnidade": it.get("unidade", "").upper(),
                "dadosMercadoriaPesoLiquido": peso_liq_fmt,
                "condicaoVendaMoedaNome": it.get("moeda", "").upper(),
                "valorTotalCondicaoVenda": val_total_venda_fmt,
                "valorUnitario": val_unit_fmt,
                "condicaoVendaValorMoeda": base_total_reais_fmt,
                "condicaoVendaValorReais": aduaneiro_fmt if int(aduaneiro_fmt) > 0 else base_total_reais_fmt,
                "paisOrigemMercadoriaNome": it.get("paisOrigem", "").upper(),
                "paisAquisicaoMercadoriaNome": it.get("paisOrigem", "").upper(),
                "descricaoMercadoria": final_desc,
                "quantidade": qtd_comercial_fmt,
                "unidadeMedida": it.get("unidade", "").upper(),
                "dadosCargaUrfEntradaCodigo": h.get("urf", "0917800"),
                "fornecedorNome": supplier_data["fornecedorNome"][:60],
                "fornecedorLogradouro": supplier_data["fornecedorLogradouro"][:60],
                "fornecedorNumero": supplier_data["fornecedorNumero"][:10],
                "fornecedorCidade": supplier_data["fornecedorCidade"][:30],
                "freteValorReais": frete_fmt,
                "seguroValorReais": seguro_fmt,
                "iiBaseCalculo": ii_base_fmt,
                "iiAliquotaAdValorem": ii_aliq_fmt,
                "iiAliquotaValorCalculado": ii_val_fmt,
                "iiAliquotaValorDevido": ii_val_fmt,
                "iiAliquotaValorRecolher": ii_val_fmt,
                "ipiAliquotaAdValorem": ipi_aliq_fmt,
                "ipiAliquotaValorDevido": ipi_val_fmt,
                "ipiAliquotaValorRecolher": ipi_val_fmt,
                "pisCofinsBaseCalculoValor": pis_base_fmt,
                "pisPasepAliquotaAdValorem": pis_aliq_fmt,
                "pisPasepAliquotaValorDevido": pis_val_fmt,
                "pisPasepAliquotaValorRecolher": pis_val_fmt,
                "cofinsAliquotaAdValorem": cofins_aliq_fmt,
                "cofinsAliquotaValorDevido": cofins_val_fmt,
                "cofinsAliquotaValorRecolher": cofins_val_fmt,
                "icmsBaseCalculoValor": icms_base_valor,
                "icmsBaseCalculoAliquota": "01800",
                "cbsIbsClasstrib": "000001",
                "cbsBaseCalculoValor": icms_base_valor,
                "cbsBaseCalculoAliquota": "00090",
                "cbsBaseCalculoValorImposto": cbs_imposto,
                "ibsBaseCalculoValor": icms_base_valor,
                "ibsBaseCalculoAliquota": "00010",
                "ibsBaseCalculoValorImposto": ibs_imposto
            }

            for field in ADICAO_FIELDS_ORDER:
                tag_name = field["tag"]
                if field.get("type") == "complex":
                    parent = etree.SubElement(adicao, tag_name)
                    for child in field["children"]:
                        c_tag = child["tag"]
                        val = extracted_map.get(c_tag, child["default"])
                        etree.SubElement(parent, c_tag).text = val
                else:
                    val = extracted_map.get(tag_name, field["default"])
                    etree.SubElement(adicao, tag_name).text = val

        peso_bruto_fmt     = DataFormatter.format_quantity(h.get("pesoBruto"), 15)
        peso_liq_total_fmt = DataFormatter.format_quantity(h.get("pesoLiquido"), 15)

        footer_map = {
            "numeroDUIMP": duimp_fmt,
            "importadorNome": h.get("nomeImportador", ""),
            "importadorNumero": DataFormatter.format_number(h.get("cnpj"), 14),
            "cargaPesoBruto": peso_bruto_fmt,
            "cargaPesoLiquido": peso_liq_total_fmt,
            "cargaPaisProcedenciaNome": h.get("paisProcedencia", "").upper(),
            "totalAdicoes": str(len(self.items_to_use)).zfill(3),
            "freteTotalReais": DataFormatter.format_input_fiscal(totals["frete"]),
            "seguroTotalReais": DataFormatter.format_input_fiscal(totals["seguro"]),
        }

        if user_inputs:
            footer_map["cargaDataChegada"]               = user_inputs.get("cargaDataChegada", "20251120")
            footer_map["dataDesembaraco"]                 = user_inputs.get("dataDesembaraco", "20251124")
            footer_map["dataRegistro"]                    = user_inputs.get("dataRegistro", "20251124")
            footer_map["conhecimentoCargaEmbarqueData"]   = user_inputs.get("conhecimentoCargaEmbarqueData", "20251025")
            footer_map["cargaPesoBruto"]                  = user_inputs.get("cargaPesoBruto", peso_bruto_fmt)
            footer_map["cargaPesoLiquido"]                = user_inputs.get("cargaPesoLiquido", peso_liq_total_fmt)
            footer_map["localDescargaTotalDolares"]       = user_inputs.get("localDescargaTotalDolares", "000000000000000")
            footer_map["localDescargaTotalReais"]         = user_inputs.get("localDescargaTotalReais", "000000000000000")
            footer_map["localEmbarqueTotalDolares"]       = user_inputs.get("localEmbarqueTotalDolares", "000000000000000")
            footer_map["localEmbarqueTotalReais"]         = user_inputs.get("localEmbarqueTotalReais", "000000000000000")

        receita_codes = [
            {"code": "0086", "val": totals["ii"]},
            {"code": "1038", "val": totals["ipi"]},
            {"code": "5602", "val": totals["pis"]},
            {"code": "5629", "val": totals["cofins"]}
        ]
        if user_inputs and user_inputs.get("valorReceita7811", "0") not in ("0", "000000000000000", ""):
            try:
                receita_codes.append({"code": "7811", "val": float(user_inputs.get("valorReceita7811"))})
            except:
                pass

        for tag, default_val in FOOTER_TAGS.items():
            if tag == "embalagem" and user_inputs:
                parent = etree.SubElement(self.duimp, tag)
                for subfield in default_val:
                    val_to_use = subfield["default"]
                    if subfield["tag"] == "quantidadeVolume":
                        val_to_use = user_inputs.get("quantidadeVolume", val_to_use)
                    etree.SubElement(parent, subfield["tag"]).text = val_to_use
                continue

            if tag == "pagamento":
                agencia = user_inputs.get("agenciaPagamento", "3715") if user_inputs else "3715"
                banco   = user_inputs.get("bancoPagamento", "341") if user_inputs else "341"
                for rec in receita_codes:
                    if rec["val"] > 0:
                        pag = etree.SubElement(self.duimp, "pagamento")
                        etree.SubElement(pag, "agenciaPagamento").text = agencia
                        etree.SubElement(pag, "bancoPagamento").text = banco
                        etree.SubElement(pag, "codigoReceita").text = rec["code"]
                        if rec["code"] == "7811" and user_inputs:
                            etree.SubElement(pag, "valorReceita").text = user_inputs.get("valorReceita7811", "000000000000000").zfill(15)
                        else:
                            etree.SubElement(pag, "valorReceita").text = DataFormatter.format_input_fiscal(rec["val"])
                continue

            if tag in footer_map:
                etree.SubElement(self.duimp, tag).text = footer_map[tag]
                continue

            if user_inputs and tag in user_inputs:
                etree.SubElement(self.duimp, tag).text = user_inputs[tag]
                continue

            if isinstance(default_val, list):
                parent = etree.SubElement(self.duimp, tag)
                for subfield in default_val:
                    etree.SubElement(parent, subfield["tag"]).text = subfield["default"]
            elif isinstance(default_val, dict):
                parent = etree.SubElement(self.duimp, tag)
                etree.SubElement(parent, default_val["tag"]).text = default_val["default"]
            else:
                val = footer_map.get(tag, default_val)
                etree.SubElement(self.duimp, tag).text = val

        xml_content = etree.tostring(self.root, pretty_print=True, encoding="UTF-8", xml_declaration=False)
        header = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        return header + xml_content

# ==============================================================================
# PARTE 7: SISTEMA INTEGRADO DUIMP (com seleção de fonte fiscal)
# ==============================================================================
def sistema_integrado_duimp():
    st.markdown(
        '<div class="main-header">Sistema Integrado DUIMP 2026 (Versão Final Restaurada)</div>',
        unsafe_allow_html=True
    )

    tab1, tab2, tab3 = st.tabs(["📂 Upload e Vinculação", "📋 Conferência Detalhada", "💾 Exportar XML"])

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 1 — Upload e Vinculação
    # ──────────────────────────────────────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns(2)

        # ── Coluna 1: DUIMP (APP 1) ───────────────────────────────────────────
        with col1:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.info("**Passo 1:** Carregue o Extrato DUIMP (Siscomex)")
            file_duimp = st.file_uploader("Arquivo DUIMP (.pdf)", type="pdf", key="u1")
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Coluna 2: Fonte fiscal (APP2 ou Sigraweb) ─────────────────────────
        with col2:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.info("**Passo 2:** Escolha a fonte dos dados fiscais e carregue o arquivo")

            fonte_fiscal = st.radio(
                "Fonte dos dados fiscais:",
                options=["APP2 — Extrato Detalhado DUIMP", "Sigraweb — Conferência do Processo"],
                key="fonte_fiscal_radio",
                help=(
                    "APP2: PDF gerado pelo Extrato Detalhado do Siscomex (layout 'ITENS DA DUIMP - N').\n"
                    "Sigraweb: PDF gerado pelo Sigraweb (layout 'Informações da Adição Nº: N')."
                )
            )
            st.session_state["fonte_fiscal_escolhida"] = fonte_fiscal

            label_upload = (
                "Arquivo APP2 — Extrato Detalhado (.pdf)"
                if "APP2" in fonte_fiscal
                else "Arquivo Sigraweb — Conferência do Processo (.pdf)"
            )
            file_hafele = st.file_uploader(label_upload, type="pdf", key="u2")
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Processamento DUIMP (APP 1) ───────────────────────────────────────
        if file_duimp:
            if (st.session_state["parsed_duimp"] is None or
                    file_duimp.name != st.session_state.get("last_duimp_name")):
                try:
                    p = DuimpPDFParser(file_duimp.read())
                    p.preprocess()
                    p.extract_header()
                    p.extract_items()
                    st.session_state["parsed_duimp"]    = p
                    st.session_state["last_duimp_name"] = file_duimp.name

                    df = pd.DataFrame(p.items)
                    cols_fiscais = [
                        "NUMBER", "Frete (R$)", "Seguro (R$)",
                        "II (R$)", "II Base (R$)", "II Alíq. (%)",
                        "IPI (R$)", "IPI Base (R$)", "IPI Alíq. (%)",
                        "PIS (R$)", "PIS Base (R$)", "PIS Alíq. (%)",
                        "COFINS (R$)", "COFINS Base (R$)", "COFINS Alíq. (%)",
                        "Aduaneiro (R$)"
                    ]
                    for col in cols_fiscais:
                        df[col] = 0.00 if col != "NUMBER" else ""
                    st.session_state["merged_df"] = df

                    st.markdown(
                        f'<div class="success-box">✅ DUIMP lida com sucesso! '
                        f'{len(p.items)} adições encontradas.</div>',
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.error(f"Erro ao ler DUIMP: {e}")

        # ── Processamento da fonte fiscal (APP2 ou Sigraweb) ──────────────────
        if file_hafele:
            # Detecta troca de arquivo ou de fonte
            arquivo_mudou = file_hafele.name != st.session_state.get("last_app2_name")
            fonte_mudou   = fonte_fiscal != st.session_state.get("fonte_fiscal_escolhida_anterior", "")

            if st.session_state["parsed_hafele"] is None or arquivo_mudou or fonte_mudou:
                st.session_state["fonte_fiscal_escolhida_anterior"] = fonte_fiscal
                st.session_state["last_app2_name"] = file_hafele.name
                # Reseta vinculação anterior ao trocar arquivo
                if arquivo_mudou:
                    st.session_state["parsed_hafele"] = None

                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(file_hafele.getvalue())
                    tmp_path = tmp.name

                try:
                    if "Sigraweb" in fonte_fiscal:
                        parser_fonte = SigrawebPDFParser()
                        tipo_fonte   = "Sigraweb"
                    else:
                        parser_fonte = HafelePDFParser()
                        tipo_fonte   = "APP2"

                    doc_fonte = parser_fonte.parse_pdf(tmp_path)
                    st.session_state["parsed_hafele"] = doc_fonte

                    qtd_itens = len(doc_fonte['itens'])
                    if qtd_itens > 0:
                        st.markdown(
                            f'<div class="success-box">✅ {tipo_fonte} lido com sucesso! '
                            f'{qtd_itens} itens encontrados.</div>',
                            unsafe_allow_html=True
                        )
                        # Mostra prévia dos dados fiscais extraídos
                        with st.expander(f"👁️ Prévia dos dados extraídos do {tipo_fonte}", expanded=False):
                            df_prev = pd.DataFrame(doc_fonte['itens'])
                            cols_show = [c for c in [
                                'numero_item', 'codigo_interno', 'ncm', 'nome_produto',
                                'quantidade', 'peso_liquido', 'valor_total',
                                'ii_aliquota', 'ii_base_calculo', 'ii_valor_devido',
                                'pis_aliquota', 'pis_valor_devido',
                                'cofins_aliquota', 'cofins_valor_devido',
                                'frete_internacional', 'seguro_internacional'
                            ] if c in df_prev.columns]
                            st.dataframe(df_prev[cols_show], use_container_width=True)
                    else:
                        st.warning(
                            f"O PDF foi lido, mas nenhum item foi identificado no formato {tipo_fonte}. "
                            "Verifique se o arquivo está correto."
                        )

                except Exception as e:
                    st.error(f"Erro ao ler {tipo_fonte if 'tipo_fonte' in dir() else 'arquivo'}: {e}")
                    st.code(traceback.format_exc())
                finally:
                    if os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass

        st.divider()

        # ── Botão de vinculação ───────────────────────────────────────────────
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            btn_vincular = st.button(
                "🔗 VINCULAR DADOS (Cruzamento Automático)",
                type="primary", width='stretch'
            )
        with col_btn2:
            btn_limpar = st.button("🗑️ Limpar Sessão", width='stretch')

        if btn_limpar:
            for k in ["parsed_duimp", "parsed_hafele", "merged_df",
                      "last_duimp_name", "last_app2_name", "fonte_fiscal_escolhida"]:
                st.session_state[k] = None
            st.success("Sessão limpa com sucesso!")
            time.sleep(1)
            st.rerun()

        if btn_vincular:
            if st.session_state["merged_df"] is not None and st.session_state["parsed_hafele"] is not None:
                try:
                    df_dest = st.session_state["merged_df"].copy()
                    src_map = {}
                    for item in st.session_state["parsed_hafele"]['itens']:
                        try:
                            idx = int(item['numero_item'])
                            src_map[idx] = item
                        except Exception:
                            pass

                    count = 0
                    for idx, row in df_dest.iterrows():
                        try:
                            item_num = int(str(row['numeroAdicao']).strip())
                            if item_num in src_map:
                                src = src_map[item_num]
                                df_dest.at[idx, 'NUMBER']           = src.get('codigo_interno', '')
                                df_dest.at[idx, 'Frete (R$)']       = src.get('frete_internacional', 0.0)
                                df_dest.at[idx, 'Seguro (R$)']      = src.get('seguro_internacional', 0.0)
                                df_dest.at[idx, 'Aduaneiro (R$)']   = src.get('local_aduaneiro', 0.0)
                                df_dest.at[idx, 'II (R$)']          = src.get('ii_valor_devido', 0.0)
                                df_dest.at[idx, 'II Base (R$)']     = src.get('ii_base_calculo', 0.0)
                                df_dest.at[idx, 'II Alíq. (%)']     = src.get('ii_aliquota', 0.0)
                                df_dest.at[idx, 'IPI (R$)']         = src.get('ipi_valor_devido', 0.0)
                                df_dest.at[idx, 'IPI Base (R$)']    = src.get('ipi_base_calculo', 0.0)
                                df_dest.at[idx, 'IPI Alíq. (%)']    = src.get('ipi_aliquota', 0.0)
                                df_dest.at[idx, 'PIS (R$)']         = src.get('pis_valor_devido', 0.0)
                                df_dest.at[idx, 'PIS Base (R$)']    = src.get('pis_base_calculo', 0.0)
                                df_dest.at[idx, 'PIS Alíq. (%)']    = src.get('pis_aliquota', 0.0)
                                df_dest.at[idx, 'COFINS (R$)']      = src.get('cofins_valor_devido', 0.0)
                                df_dest.at[idx, 'COFINS Base (R$)'] = src.get('cofins_base_calculo', 0.0)
                                df_dest.at[idx, 'COFINS Alíq. (%)'] = src.get('cofins_aliquota', 0.0)
                                count += 1
                        except Exception:
                            continue

                    st.session_state["merged_df"] = df_dest
                    fonte_label = st.session_state.get("fonte_fiscal_escolhida", "fonte fiscal")
                    st.success(f"✅ {count} itens vinculados com sucesso via {fonte_label}!")

                    # Resumo dos totais vinculados
                    total_ii     = df_dest['II (R$)'].sum()
                    total_pis    = df_dest['PIS (R$)'].sum()
                    total_cofins = df_dest['COFINS (R$)'].sum()
                    total_frete  = df_dest['Frete (R$)'].sum()
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("II Total", f"R$ {total_ii:,.2f}")
                    c2.metric("PIS Total", f"R$ {total_pis:,.2f}")
                    c3.metric("COFINS Total", f"R$ {total_cofins:,.2f}")
                    c4.metric("Frete Total", f"R$ {total_frete:,.2f}")

                except Exception as e:
                    st.error(f"Erro na vinculação: {e}")
                    st.code(traceback.format_exc())
            else:
                st.warning("⚠️ Carregue os dois arquivos (DUIMP + fonte fiscal) antes de vincular.")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 2 — Conferência e Edição
    # ──────────────────────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Conferência e Edição")
        if st.session_state["merged_df"] is not None:
            fonte_label = st.session_state.get("fonte_fiscal_escolhida", "")
            if fonte_label:
                st.markdown(
                    f'<div class="info-box">📌 Dados fiscais carregados via: <strong>{fonte_label}</strong></div>',
                    unsafe_allow_html=True
                )

            col_config = {
                "numeroAdicao": st.column_config.TextColumn("Item", width="small", disabled=True),
                "NUMBER": st.column_config.TextColumn("Código Interno", width="medium"),
                "Frete (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Seguro (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Aduaneiro (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "II (R$)": st.column_config.NumberColumn(label="II Vlr", format="R$ %.2f"),
                "II Base (R$)": st.column_config.NumberColumn(label="II Base", format="R$ %.2f"),
                "II Alíq. (%)": st.column_config.NumberColumn(label="II Alíq %", format="%.4f"),
                "IPI (R$)": st.column_config.NumberColumn(label="IPI Vlr", format="R$ %.2f"),
                "IPI Alíq. (%)": st.column_config.NumberColumn(label="IPI Alíq %", format="%.4f"),
                "PIS (R$)": st.column_config.NumberColumn(label="PIS Vlr", format="R$ %.2f"),
                "PIS Base (R$)": st.column_config.NumberColumn(label="PIS Base", format="R$ %.2f"),
                "PIS Alíq. (%)": st.column_config.NumberColumn(label="PIS Alíq %", format="%.4f"),
                "COFINS (R$)": st.column_config.NumberColumn(label="COFINS Vlr", format="R$ %.2f"),
                "COFINS Base (R$)": st.column_config.NumberColumn(label="COFINS Base", format="R$ %.2f"),
                "COFINS Alíq. (%)": st.column_config.NumberColumn(label="COFINS Alíq %", format="%.4f"),
            }

            edited_df = st.data_editor(
                st.session_state["merged_df"],
                hide_index=True,
                column_config=col_config,
                width='stretch',
                height=600
            )

            # Recalcula valores de impostos com base em base × alíquota
            for tax in ['II', 'IPI', 'PIS', 'COFINS']:
                base_col = f"{tax} Base (R$)"
                aliq_col = f"{tax} Alíq. (%)"
                val_col  = f"{tax} (R$)"
                if base_col in edited_df.columns and aliq_col in edited_df.columns:
                    edited_df[base_col] = pd.to_numeric(edited_df[base_col], errors='coerce').fillna(0.0)
                    edited_df[aliq_col] = pd.to_numeric(edited_df[aliq_col], errors='coerce').fillna(0.0)
                    edited_df[val_col]  = edited_df[base_col] * (edited_df[aliq_col] / 100.0)

            st.session_state["merged_df"] = edited_df

            # Totalizadores
            st.divider()
            st.subheader("📊 Totais do Processo")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("II Total",     f"R$ {edited_df['II (R$)'].sum():,.2f}")
            c2.metric("IPI Total",    f"R$ {edited_df['IPI (R$)'].sum():,.2f}")
            c3.metric("PIS Total",    f"R$ {edited_df['PIS (R$)'].sum():,.2f}")
            c4.metric("COFINS Total", f"R$ {edited_df['COFINS (R$)'].sum():,.2f}")
            c5.metric("Frete Total",  f"R$ {edited_df['Frete (R$)'].sum():,.2f}")
        else:
            st.info("Nenhum dado para exibir. Realize o upload e a vinculação na aba anterior.")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 3 — Exportar XML
    # ──────────────────────────────────────────────────────────────────────────
    with tab3:
        st.subheader("Gerar XML Final (Configurações Manuais)")
        st.markdown("### Preenchimento Obrigatório das Tags")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**QUANTIDADE**")
            inp_qtd_volume = st.text_input("Quantidade Volume", value="00001", help="Preenche <quantidadeVolume>")
            st.markdown("**DATAS**")
            inp_dt_chegada = st.text_input("Data Chegada", value="20251120", help="<cargaDataChegada>")
            inp_dt_desemb  = st.text_input("Data Desembaraço", value="20251124", help="<dataDesembaraco>")
            inp_dt_reg     = st.text_input("Data Registro", value="20251124", help="<dataRegistro>")
            inp_dt_emb     = st.text_input("Data Embarque", value="20251025", help="<conhecimentoCargaEmbarqueData>")

        with c2:
            st.markdown("**PESO (KG)**")
            inp_peso_bruto = st.text_input("Peso Bruto", value="000002114187000", help="<cargaPesoBruto>")
            inp_peso_liq   = st.text_input("Peso Líquido", value="000002114187000", help="<cargaPesoLiquido>")
            st.markdown("**LOCAIS (Reais/Dólares)**")
            inp_loc_desc_dol = st.text_input("Local Descarga Total Dólares", value="000000000000000")
            inp_loc_desc_rea = st.text_input("Local Descarga Total Reais",   value="000000000000000")
            inp_loc_emb_dol  = st.text_input("Local Embarque Total Dólares", value="000000000000000")
            inp_loc_emb_rea  = st.text_input("Local Embarque Total Reais",   value="000000000000000")

        with c3:
            st.markdown("**SISCOMEX**")
            inp_agencia = st.text_input("Agência Pagamento", value="3715", help="<agenciaPagamento>")
            inp_banco   = st.text_input("Banco Pagamento",   value="341",  help="<bancoPagamento>")
            st.markdown("---")
            st.markdown("**SISCOMEX 7811**")
            inp_valor_7811 = st.text_input(
                "Valor Receita 7811", value="000000000000000",
                help="Preenche <valorReceita> para o código 7811 (deixe zerado para ignorar)"
            )

        user_xml_config = {
            "quantidadeVolume":             inp_qtd_volume,
            "cargaDataChegada":             inp_dt_chegada,
            "dataDesembaraco":              inp_dt_desemb,
            "dataRegistro":                 inp_dt_reg,
            "conhecimentoCargaEmbarqueData":inp_dt_emb,
            "cargaPesoBruto":               inp_peso_bruto,
            "cargaPesoLiquido":             inp_peso_liq,
            "agenciaPagamento":             inp_agencia,
            "bancoPagamento":               inp_banco,
            "valorReceita7811":             inp_valor_7811,
            "localDescargaTotalDolares":    inp_loc_desc_dol,
            "localDescargaTotalReais":      inp_loc_desc_rea,
            "localEmbarqueTotalDolares":    inp_loc_emb_dol,
            "localEmbarqueTotalReais":      inp_loc_emb_rea,
        }

        if st.session_state["merged_df"] is not None and st.session_state["parsed_duimp"] is not None:
            if st.button("⚙️ Gerar XML (Layout 8686)", type="primary"):
                try:
                    p = st.session_state["parsed_duimp"]
                    records = st.session_state["merged_df"].to_dict("records")
                    for i, item in enumerate(p.items):
                        if i < len(records):
                            item.update(records[i])

                    builder   = XMLBuilder(p)
                    xml_bytes = builder.build(user_inputs=user_xml_config)

                    duimp_num = p.header.get("numeroDUIMP", "0000").replace("/", "-")
                    file_name = f"DUIMP_{duimp_num}_INTEGRADO.xml"

                    st.download_button(
                        label="⬇️ Baixar XML",
                        data=xml_bytes,
                        file_name=file_name,
                        mime="text/xml"
                    )
                    st.success("✅ XML gerado com sucesso!")

                except Exception as e:
                    st.error(f"Erro na geração do XML: {e}")
                    st.code(traceback.format_exc())
        else:
            st.warning("⚠️ Realize o upload do DUIMP e a vinculação antes de gerar o XML.")

# ==============================================================================
# APLICAÇÃO PRINCIPAL
# ==============================================================================
def main():
    load_css()

    st.markdown("""
    <div class="cover-container">
        <img src="https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png" class="cover-logo">
        <h1 class="cover-title">Sistema de Processamento Unificado 2026</h1>
        <p class="cover-subtitle">Processamento de TXT, CT-e e DUIMP para análise de dados</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📄 Processador TXT", "🚚 Processador CT-e", "📊 Sistema Integrado DUIMP"])

    with tab1: processador_txt()
    with tab2: processador_cte()
    with tab3: sistema_integrado_duimp()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {str(e)}")
        st.code(traceback.format_exc())
