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
        try:
            # Lê o conteúdo do arquivo
            conteudo = arquivo.read()
            
            # Processa o arquivo
            resultado, total_linhas = processar_arquivo(conteudo, padroes)
            
            if resultado is not None:
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

# --- PROCESSADOR CT-E SEM ARMAZENAMENTO ---
class CTeProcessorDirect:
    def __init__(self):
        self.processed_data = []
    
    def extract_cte_data(self, xml_content, filename):
        """Extrai dados específicos do CT-e diretamente para planilha"""
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
                    
                    # Tentativa alternativa sem namespace
                    found = element.find(xpath.replace('cte:', ''))
                    if found is not None and found.text:
                        return found.text
                        
                    return None
                except Exception:
                    return None
            
            # Função para encontrar múltiplos elementos
            def find_all_elements(element, xpath):
                try:
                    elements = []
                    for prefix, uri in CTE_NAMESPACES.items():
                        full_xpath = xpath.replace('cte:', f'{{{uri}}}')
                        found_elements = element.findall(full_xpath)
                        if found_elements:
                            elements.extend(found_elements)
                    
                    if not elements:
                        # Tentativa alternativa sem namespace
                        found_elements = element.findall(xpath.replace('cte:', ''))
                        if found_elements:
                            elements.extend(found_elements)
                    
                    return elements
                except Exception:
                    return []
            
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
            
            # Extrai apenas o número da NFe da chave de acesso (últimos 9 dígitos)
            numero_nfe = None
            if infNFe_chave and len(infNFe_chave) >= 9:
                numero_nfe = infNFe_chave[-9:]
            
            # EXTRAIR PESO DA MERCADORIA - CORREÇÃO PARA A ESTRUTURA infQ
            peso_mercadoria = None
            tipo_peso = "N/A"
            
            # Busca por todas as tags infQ
            infQ_elements = find_all_elements(root, './/cte:infQ')
            
            for infQ in infQ_elements:
                # Verifica se é PESO BRUTO
                tpMed = infQ.find('.//{*}tpMed') or infQ.find('.//tpMed')
                qCarga = infQ.find('.//{*}qCarga') or infQ.find('.//qCarga')
                
                if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                    tipo_medida = tpMed.text.strip().upper()
                    if 'PESO' in tipo_medida or 'PESO BRUTO' in tipo_medida:
                        try:
                            peso_mercadoria = float(qCarga.text)
                            tipo_peso = tipo_medida
                            break  # Para no primeiro PESO BRUTO encontrado
                        except (ValueError, TypeError):
                            continue
            
            # Se não encontrou PESO BRUTO, tenta encontrar qualquer peso
            if peso_mercadoria is None:
                for infQ in infQ_elements:
                    qCarga = infQ.find('.//{*}qCarga') or infQ.find('.//qCarga')
                    if qCarga is not None and qCarga.text:
                        try:
                            peso_mercadoria = float(qCarga.text)
                            # Tenta identificar o tipo
                            tpMed = infQ.find('.//{*}tpMed') or infQ.find('.//tpMed')
                            tipo_peso = tpMed.text if tpMed is not None and tpMed.text else "PESO"
                            break
                        except (ValueError, TypeError):
                            continue
            
            # Formata peso para exibição
            peso_formatado = f"{peso_mercadoria:,.3f} kg" if peso_mercadoria is not None else "N/A"
            
            # Formata data no padrão DD/MM/AA
            data_formatada = None
            if dhEmi:
                try:
                    # Tenta diferentes formatos de data
                    try:
                        data_obj = datetime.strptime(dhEmi[:10], '%Y-%m-%d')
                    except:
                        try:
                            data_obj = datetime.strptime(dhEmi[:10], '%d/%m/%Y')
                        except:
                            data_obj = datetime.strptime(dhEmi[:10], '%d/%m/%y')
                    
                    data_formatada = data_obj.strftime('%d/%m/%y')
                except:
                    data_formatada = dhEmi[:10]  # Fallback para formato original
            
            # Converte valor para decimal
            try:
                vTPrest = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                vTPrest = 0.0
            
            # Retorna os dados estruturados
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
                'Remetente': rem_xNome or 'N/A',
                'Destinatário': dest_xNome or 'N/A',
                'Documento Destinatário': documento_destinatario,
                'Endereço Destinatário': endereco_destinatario,
                'Município Destino': dest_xMun or 'N/A',
                'UF Destino': dest_UF or 'N/A',
                'Chave NFe': infNFe_chave or 'N/A',
                'Número NFe': numero_nfe or 'N/A',
                'Peso Mercadoria (kg)': peso_mercadoria or 0.0,
                'Tipo Peso': tipo_peso,
                'Peso Formatado': peso_formatado,
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
        
        for uploaded_file in uploaded_files:
            success, message = self.process_single_file(uploaded_file)
            if success:
                results['success'] += 1
            else:
                results['errors'] += 1
            results['messages'].append(message)
        
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
    """Interface para o sistema de CT-e sem armazenamento"""
    # Inicializar processador
    processor = CTeProcessorDirect()
    
    st.title("🚚 Processador de CT-e para Power BI")
    st.markdown("### Processa arquivos XML de CT-e e gera planilha para análise")
    
    # Navegação por abas
    tab1, tab2, tab3 = st.tabs(["Upload", "Visualizar Dados", "Exportar"])
    
    with tab1:
        st.header("Upload de CT-es")
        upload_option = st.radio("Selecione o tipo de upload:", 
                                ["Upload Individual", "Upload em Lote"])
        
        if upload_option == "Upload Individual":
            uploaded_file = st.file_uploader("Selecione um arquivo XML de CT-e", type=['xml'], key="single_cte")
            if uploaded_file and st.button("📊 Processar CT-e", key="process_single"):
                with st.spinner("Processando CT-e..."):
                    success, message = processor.process_single_file(uploaded_file)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        
        else:
            uploaded_files = st.file_uploader("Selecione múltiplos arquivos XML de CT-e", 
                                            type=['xml'], 
                                            accept_multiple_files=True,
                                            key="multiple_cte")
            if uploaded_files and st.button("📊 Processar Todos", key="process_multiple"):
                with st.spinner(f"Processando {len(uploaded_files)} CT-es..."):
                    results = processor.process_multiple_files(uploaded_files)
                    
                    st.success(f"""
                    **Processamento concluído!**  
                    ✅ Sucessos: {results['success']}  
                    ❌ Erros: {results['errors']}
                    """)
                    
                    if results['errors'] > 0:
                        with st.expander("Ver mensagens detalhadas"):
                            for msg in results['messages']:
                                st.write(f"- {msg}")
        
        # Botão para limpar dados
        if st.button("🗑️ Limpar Dados Processados", type="secondary"):
            processor.clear_data()
            st.success("Dados limpos com sucesso!")
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
                emitente_filter = st.multiselect("Filtrar por Emitente", options=df['Emitente'].unique())
            
            # Aplicar filtros
            filtered_df = df.copy()
            if uf_filter:
                filtered_df = filtered_df[filtered_df['UF Início'].isin(uf_filter)]
            if uf_destino_filter:
                filtered_df = filtered_df[filtered_df['UF Destino'].isin(uf_destino_filter)]
            if emitente_filter:
                filtered_df = filtered_df[filtered_df['Emitente'].isin(emitente_filter)]
            
            # Exibir dataframe com colunas principais (incluindo peso)
            colunas_principais = [
                'Arquivo', 'nCT', 'Data Emissão', 'Emitente', 'Remetente', 
                'Destinatário', 'UF Início', 'UF Destino', 'Valor Prestação', 
                'Peso Formatado', 'Tipo Peso'
            ]
            
            st.dataframe(filtered_df[colunas_principais], use_container_width=True)
            
            # Detalhes expandíveis
            with st.expander("📋 Ver todos os campos detalhados"):
                st.dataframe(filtered_df, use_container_width=True)
            
            # Estatísticas (incluindo estatísticas de peso)
            st.subheader("📈 Estatísticas")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("Total Valor Prestação", f"R$ {filtered_df['Valor Prestação'].sum():,.2f}")
            col2.metric("Média por CT-e", f"R$ {filtered_df['Valor Prestação'].mean():,.2f}")
            col3.metric("Total Peso (kg)", f"{filtered_df['Peso Mercadoria (kg)'].sum():,.3f}")
            col4.metric("CT-es com Peso", f"{filtered_df[filtered_df['Peso Mercadoria (kg)'] > 0].shape[0]}")
            
            # Gráficos adicionais com informações de peso
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("📊 Distribuição por UF Destino")
                if not filtered_df.empty:
                    uf_counts = filtered_df['UF Destino'].value_counts()
                    fig_uf = px.pie(
                        values=uf_counts.values,
                        names=uf_counts.index,
                        title="Distribuição por UF de Destino"
                    )
                    st.plotly_chart(fig_uf, use_container_width=True)
            
            with col_chart2:
                st.subheader("⚖️ Peso por Emitente")
                if not filtered_df.empty:
                    peso_por_emitente = filtered_df.groupby('Emitente')['Peso Mercadoria (kg)'].sum().sort_values(ascending=False).head(10)
                    fig_peso = px.bar(
                        x=peso_por_emitente.values,
                        y=peso_por_emitente.index,
                        orientation='h',
                        title="Top 10 Emitentes por Peso (kg)",
                        labels={'x': 'Peso Total (kg)', 'y': 'Emitente'}
                    )
                    st.plotly_chart(fig_peso, use_container_width=True)
            
            # Gráficos adicionais
            col_chart3, col_chart4 = st.columns(2)
            
            with col_chart3:
                st.subheader("📈 Valor por Emitente")
                if not filtered_df.empty:
                    valor_por_emitente = filtered_df.groupby('Emitente')['Valor Prestação'].sum().sort_values(ascending=False).head(10)
                    fig_emitente = px.bar(
                        x=valor_por_emitente.values,
                        y=valor_por_emitente.index,
                        orientation='h',
                        title="Top 10 Emitentes por Valor",
                        labels={'x': 'Valor Total (R$)', 'y': 'Emitente'}
                    )
                    st.plotly_chart(fig_emitente, use_container_width=True)
            
            with col_chart4:
                st.subheader("📦 Relação Peso x Valor")
                if not filtered_df.empty:
                    fig_relacao = px.scatter(
                        filtered_df,
                        x='Peso Mercadoria (kg)',
                        y='Valor Prestação',
                        title="Relação entre Peso e Valor do Frete",
                        hover_data=['Emitente', 'Destinatário', 'Tipo Peso']
                    )
                    st.plotly_chart(fig_relacao, use_container_width=True)
            
            # Informações sobre os tipos de peso encontrados
            if not filtered_df.empty:
                with st.expander("📋 Informações sobre os Tipos de Peso"):
                    tipos_peso = filtered_df['Tipo Peso'].value_counts()
                    st.write("**Tipos de peso encontrados:**")
                    for tipo, quantidade in tipos_peso.items():
                        st.write(f"- {tipo}: {quantidade} CT-e(s)")
            
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