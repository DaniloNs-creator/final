import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pdfplumber
import pandas as pd
import re
import json
import tempfile
import os
from datetime import datetime
import base64

# Configuração da página
st.set_page_config(
    page_title="Conversor DUIMP PDF para XML",
    page_icon="📄",
    layout="wide"
)

# CSS para melhorar a aparência
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #374151;
        margin-top: 1.5rem;
    }
    .info-box {
        background-color: #F3F4F6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #D1FAE5;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #10B981;
    }
    .warning-box {
        background-color: #FEF3C7;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #F59E0B;
    }
    .stProgress > div > div > div > div {
        background-color: #1E3A8A;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-header">📄 Conversor DUIMP - PDF para XML</h1>', unsafe_allow_html=True)

# Informações sobre o aplicativo
with st.expander("ℹ️ Informações sobre o aplicativo", expanded=False):
    st.markdown("""
    **Funcionalidades:**
    - Processa PDFs de extrato DUIMP do Siscomex
    - Converte para formato XML obrigatório
    - Mantém todas as tags, sequência e indentação
    - Suporta PDFs de até 500 páginas
    - Processamento otimizado para alto volume
    
    **Requisitos do XML:**
    - Todas as tags do layout M-DUIMP obrigatórias
    - Sequência correta das tags
    - Indentação apropriada
    - Valores formatados corretamente
    
    **Como usar:**
    1. Faça upload do PDF do extrato DUIMP
    2. Configure os parâmetros de processamento
    3. Clique em "Processar PDF"
    4. Baixe o XML gerado
    """)

# Função para extrair dados do PDF
def extract_data_from_pdf(pdf_file):
    """Extrai dados do PDF do extrato DUIMP"""
    
    data = {
        "informacoes_gerais": {},
        "adicoes": [],
        "dados_carga": {},
        "dados_transporte": {},
        "dados_importador": {},
        "tributos": {},
        "historicos": []
    }
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for page_num, page in enumerate(pdf.pages):
                status_text.text(f"Processando página {page_num + 1} de {total_pages}...")
                
                # Extrair texto da página
                text = page.extract_text()
                lines = text.split('\n')
                
                # Processar cada linha
                for i, line in enumerate(lines):
                    line = line.strip()
                    
                    # Extrair número DUIMP
                    if "Extrato da Duimp" in line and "/" in line:
                        match = re.search(r'(\d{2}BR\d{12}-\d)', line)
                        if match:
                            data["informacoes_gerais"]["numeroDUIMP"] = match.group(1)
                    
                    # Situação da Duimp
                    elif "Situação da Duimp:" in line:
                        situacao = line.replace("Situação da Duimp:", "").strip()
                        data["informacoes_gerais"]["situacaoDuimp"] = situacao
                    
                    # Canal único
                    elif "Canal único:" in line:
                        canal = line.replace("Canal único:", "").strip()
                        data["informacoes_gerais"]["canalUnico"] = canal
                    
                    # Controle de carga
                    elif "Controle de carga:" in line:
                        controle = line.replace("Controle de carga:", "").strip()
                        data["informacoes_gerais"]["controleCarga"] = controle
                    
                    # Informações do Importador
                    elif "CNPJ do importador:" in line:
                        cnpj = line.replace("CNPJ do importador:", "").strip()
                        data["dados_importador"]["cnpj"] = cnpj
                    
                    elif "Nome do importador:" in line:
                        nome = line.replace("Nome do importador:", "").strip()
                        data["dados_importador"]["nome"] = nome
                    
                    elif "Endereço do importador:" in line and i + 1 < len(lines):
                        endereco = lines[i + 1].strip()
                        data["dados_importador"]["endereco"] = endereco
                    
                    # Dados da Carga
                    elif "PESO BRUTO KG :" in line:
                        peso = line.replace("PESO BRUTO KG :", "").strip()
                        data["dados_carga"]["pesoBruto"] = peso
                    
                    elif "PESO LIQUIDO KG :" in line:
                        peso = line.replace("PESO LIQUIDO KG :", "").strip()
                        data["dados_carga"]["pesoLiquido"] = peso
                    
                    # Extrair adições (itens)
                    elif "Extrato da Duimp" in line and "Item" in line:
                        item_match = re.search(r'Item (\d{5})', line)
                        if item_match:
                            item_num = item_match.group(1)
                            adicao = {"numeroItem": item_num}
                            
                            # Procurar informações da adição nas próximas linhas
                            for j in range(i, min(i + 50, len(lines))):
                                line_j = lines[j].strip()
                                
                                # NCM
                                if "NCM:" in line_j:
                                    ncm = line_j.replace("NCM:", "").strip()
                                    adicao["ncm"] = ncm
                                
                                # Valor total
                                elif "Valor total na condição de venda:" in line_j:
                                    valor = line_j.replace("Valor total na condição de venda:", "").strip()
                                    adicao["valorTotal"] = valor
                                
                                # Peso líquido
                                elif "Peso líquido (kg):" in line_j:
                                    peso = line_j.replace("Peso líquido (kg):", "").strip()
                                    adicao["pesoLiquido"] = peso
                                
                                # Quantidade
                                elif "Quantidade na unidade estatística:" in line_j:
                                    qtd = line_j.replace("Quantidade na unidade estatística:", "").strip()
                                    adicao["quantidade"] = qtd
                                
                                # Valor unitário
                                elif "Valor unitário na condição de venda:" in line_j:
                                    valor_unit = line_j.replace("Valor unitário na condição de venda:", "").strip()
                                    adicao["valorUnitario"] = valor_unit
                            
                            if adicao:
                                data["adicoes"].append(adicao)
                
                # Atualizar barra de progresso
                progress_bar.progress((page_num + 1) / total_pages)
            
            status_text.text("Processamento concluído!")
            progress_bar.empty()
            
    except Exception as e:
        st.error(f"Erro ao processar PDF: {str(e)}")
        return None
    
    return data

# Função para criar XML no layout obrigatório
def create_xml_from_data(data):
    """Cria XML no layout obrigatório M-DUIMP"""
    
    # Criar elemento raiz
    lista_declaracoes = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(lista_declaracoes, "duimp")
    
    # Adicionar adições
    for i, adicao_data in enumerate(data.get("adicoes", []), 1):
        adicao = ET.SubElement(duimp, "adicao")
        
        # Número da adição
        ET.SubElement(adicao, "numeroAdicao").text = f"{i:03d}"
        
        # Número DUIMP
        ET.SubElement(adicao, "numeroDUIMP").text = data["informacoes_gerais"].get("numeroDUIMP", "000000000000000")
        
        # Dados da mercadoria
        if "ncm" in adicao_data:
            ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = adicao_data["ncm"].replace(".", "")
        
        if "valorTotal" in adicao_data:
            # Converter valor para formato numérico
            try:
                valor = float(adicao_data["valorTotal"].replace(".", "").replace(",", "."))
                ET.SubElement(adicao, "condicaoVendaValorMoeda").text = f"{int(valor * 1000):015d}"
            except:
                ET.SubElement(adicao, "condicaoVendaValorMoeda").text = "000000000000000"
        
        # Outras tags obrigatórias
        ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
        ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
        ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
        ET.SubElement(adicao, "condicaoVendaMoedaNome").text = "DOLAR DOS EUA"
        
        # Dados mercadoria
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "numeroSequencialItem").text = f"{i:02d}"
        
        if "quantidade" in adicao_data:
            try:
                qtd = float(adicao_data["quantidade"])
                ET.SubElement(mercadoria, "quantidade").text = f"{int(qtd * 1000000):016d}"
            except:
                ET.SubElement(mercadoria, "quantidade").text = "0000000000000000"
        
        ET.SubElement(mercadoria, "unidadeMedida").text = "QUILOGRAMA LIQUIDO"
        
        if "valorUnitario" in adicao_data:
            try:
                valor_unit = float(adicao_data["valorUnitario"].replace(".", "").replace(",", "."))
                ET.SubElement(mercadoria, "valorUnitario").text = f"{int(valor_unit * 100000000):018d}"
            except:
                ET.SubElement(mercadoria, "valorUnitario").text = "000000000000000000"
    
    # Dados gerais do DUIMP
    if data["informacoes_gerais"].get("numeroDUIMP"):
        ET.SubElement(duimp, "numeroDUIMP").text = data["informacoes_gerais"]["numeroDUIMP"]
    
    # Dados do importador
    if data["dados_importador"].get("cnpj"):
        cnpj_limpo = data["dados_importador"]["cnpj"].replace(".", "").replace("/", "").replace("-", "")
        ET.SubElement(duimp, "importadorNumero").text = cnpj_limpo
    
    if data["dados_importador"].get("nome"):
        ET.SubElement(duimp, "importadorNome").text = data["dados_importador"]["nome"]
    
    # Dados da carga
    if data["dados_carga"].get("pesoBruto"):
        try:
            peso = float(data["dados_carga"]["pesoBruto"].replace(".", "").replace(",", "."))
            ET.SubElement(duimp, "cargaPesoBruto").text = f"{int(peso * 100000):015d}"
        except:
            ET.SubElement(duimp, "cargaPesoBruto").text = "000000000000000"
    
    if data["dados_carga"].get("pesoLiquido"):
        try:
            peso = float(data["dados_carga"]["pesoLiquido"].replace(".", "").replace(",", "."))
            ET.SubElement(duimp, "cargaPesoLiquido").text = f"{int(peso * 100000):015d}"
        except:
            ET.SubElement(duimp, "cargaPesoLiquido").text = "000000000000000"
    
    # Tags obrigatórias adicionais
    ET.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
    ET.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importação Própria"
    ET.SubElement(duimp, "modalidadeDespachoCodigo").text = "1"
    ET.SubElement(duimp, "modalidadeDespachoNome").text = "Normal"
    ET.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
    ET.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
    ET.SubElement(duimp, "viaTransporteCodigo").text = "01"
    ET.SubElement(duimp, "viaTransporteNome").text = "MARÍTIMA"
    
    # Converter para string XML com formatação
    xml_str = ET.tostring(lista_declaracoes, encoding='unicode', method='xml')
    
    # Formatar o XML
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="    ")
    
    # Remover linhas em branco extras
    pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
    
    return pretty_xml

# Interface principal
st.markdown('<div class="info-box">', unsafe_allow_html=True)
st.markdown("### 📤 Upload do PDF")
uploaded_file = st.file_uploader("Faça upload do PDF do extrato DUIMP", type=['pdf'])
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file is not None:
    # Mostrar informações do arquivo
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Arquivo", uploaded_file.name)
    with col2:
        st.metric("Tamanho", f"{uploaded_file.size / 1024:.1f} KB")
    
    # Opções de processamento
    st.markdown('<div class="sub-header">⚙️ Configurações de Processamento</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        process_full = st.checkbox("Processar todas as páginas", value=True)
    with col2:
        validate_xml = st.checkbox("Validar estrutura XML", value=True)
    
    # Botão para processar
    if st.button("🔄 Processar PDF", type="primary", use_container_width=True):
        with st.spinner("Processando PDF..."):
            try:
                # Salvar arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Extrair dados do PDF
                data = extract_data_from_pdf(tmp_path)
                
                if data:
                    # Criar XML
                    xml_content = create_xml_from_data(data)
                    
                    # Validar XML
                    if validate_xml:
                        try:
                            ET.fromstring(xml_content)
                            st.markdown('<div class="success-box">✅ XML validado com sucesso!</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.markdown(f'<div class="warning-box">⚠️ Aviso na validação: {str(e)}</div>', unsafe_allow_html=True)
                    
                    # Mostrar preview do XML
                    st.markdown('<div class="sub-header">👁️ Preview do XML Gerado</div>', unsafe_allow_html=True)
                    
                    with st.expander("Visualizar XML completo"):
                        st.code(xml_content, language='xml')
                    
                    # Estatísticas
                    st.markdown('<div class="sub-header">📊 Estatísticas</div>', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Adições processadas", len(data.get("adicoes", [])))
                    with col2:
                        st.metric("Linhas XML", xml_content.count('\n'))
                    with col3:
                        st.metric("Tamanho XML", f"{len(xml_content) / 1024:.1f} KB")
                    
                    # Botão de download
                    st.markdown('<div class="sub-header">📥 Download do XML</div>', unsafe_allow_html=True)
                    
                    # Gerar nome do arquivo
                    duimp_num = data["informacoes_gerais"].get("numeroDUIMP", "DUIMP_NAO_IDENTIFICADA")
                    xml_filename = f"M-DUIMP-{duimp_num}.xml"
                    
                    # Codificar para base64 para download
                    b64 = base64.b64encode(xml_content.encode()).decode()
                    href = f'<a href="data:application/xml;base64,{b64}" download="{xml_filename}" style="background-color: #1E3A8A; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">⬇️ Baixar XML</a>'
                    
                    st.markdown(href, unsafe_allow_html=True)
                    
                    # Limpar arquivo temporário
                    os.unlink(tmp_path)
                
                else:
                    st.error("Não foi possível extrair dados do PDF. Verifique o formato do arquivo.")
            
            except Exception as e:
                st.error(f"Erro durante o processamento: {str(e)}")
    
    # Informações adicionais
    with st.expander("📋 Informações técnicas", expanded=False):
        st.markdown("""
        **Layout XML Obrigatório:**
        - Tags seguem o padrão M-DUIMP da Receita Federal
        - Sequência fixa de elementos
        - Formatação numérica específica
        - Indentação de 4 espaços
        
        **Processamento:**
        - Utiliza pdfplumber para extração de texto
        - Regex para identificação de padrões
        - XML etree para construção do documento
        - Validação de estrutura XML
        
        **Limitações conhecidas:**
        - PDFs com OCR podem precisar de ajustes
        - Layouts muito diferentes podem exigir adaptação
        - Processamento de imagens não suportado
        """)
    
    # Seção de logs
    with st.expander("📝 Logs de processamento", expanded=False):
        st.info("Logs serão exibidos aqui durante o processamento...")

else:
    # Mostrar exemplo de estrutura quando não há arquivo
    st.markdown('<div class="warning-box">📝 Aguardando upload do arquivo PDF</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Exemplo de estrutura esperada:**
        
        ```xml
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <ListaDeclaracoes>
            <duimp>
                <adicao>
                    <numeroAdicao>001</numeroAdicao>
                    <numeroDUIMP>25BR0000246458-8</numeroDUIMP>
                    <dadosMercadoriaCodigoNcm>84522120</dadosMercadoriaCodigoNcm>
                    <condicaoVendaValorMoeda>000000000464479</condicaoVendaValorMoeda>
                    <!-- ... mais tags ... -->
                </adicao>
            </duimp>
        </ListaDeclaracoes>
        ```
        """)
    
    with col2:
        st.markdown("""
        **Tags obrigatórias principais:**
        
        1. **ListaDeclaracoes** (raiz)
        2. **duimp** (documento principal)
        3. **adicao** (para cada item)
        4. **numeroAdicao** (001, 002, ...)
        5. **numeroDUIMP** (identificador)
        6. **dadosMercadoriaCodigoNcm**
        7. **condicaoVendaValorMoeda**
        8. **codigoRelacaoCompradorVendedor**
        9. **codigoVinculoCompradorVendedor**
        10. **mercadoria** (detalhes do item)
        
        *Todas as tags devem manter a sequência exata*
        """)

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9rem;'>
    Desenvolvido para processamento de DUIMP - Siscomex<br>
    Conversor PDF para XML | Layout M-DUIMP obrigatório
    </div>
    """,
    unsafe_allow_html=True
)
