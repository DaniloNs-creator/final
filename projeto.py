import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import pdfplumber
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io
import re
from datetime import datetime
import json

# Configuração da página
st.set_page_config(
    page_title="PDF to XML Converter - DUIMP",
    page_icon="📄",
    layout="wide"
)

# Título da aplicação
st.title("📄 Conversor PDF para XML - DUIMP")
st.markdown("""
Esta aplicação extrai dados de arquivos PDF com layout específico e gera arquivos XML no formato obrigatório para DUIMP.
""")

# Sidebar para informações
with st.sidebar:
    st.header("Instruções")
    st.markdown("""
    1. Faça upload do arquivo PDF (layout fixo)
    2. A aplicação irá extrair automaticamente os dados
    3. Revise os dados extraídos
    4. Baixe o arquivo XML gerado
    5. Para processar múltiplos arquivos, faça upload um por um
    """)
    
    st.info("""
    **Layout do PDF esperado:**
    - Página 1: Informações gerais e resumo
    - Página 2: Dados de frete e embalagem
    - Página 3: Dados da mercadoria
    - Página 4: Dados complementares
    """)

# Funções para extração de dados do PDF
def extract_text_from_pdf(pdf_file):
    """Extrai texto do PDF usando PyMuPDF"""
    text = ""
    try:
        # Usando PyMuPDF para extração rápida
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()
    except Exception as e:
        st.error(f"Erro ao extrair texto: {e}")
    return text

def extract_tables_from_pdf(pdf_file):
    """Extrai tabelas do PDF usando pdfplumber"""
    tables = []
    try:
        pdf_file.seek(0)  # Reset file pointer
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
    except Exception as e:
        st.error(f"Erro ao extrair tabelas: {e}")
    return tables

def parse_pdf_content(pdf_text):
    """Analisa o texto extraído do PDF e estrutura os dados"""
    data = {
        "processo": "",
        "importador": {},
        "identificacao": {},
        "resumo": {},
        "dados_carga": {},
        "transporte": {},
        "seguro": {},
        "frete": {},
        "mercadoria": {},
        "tributos": {},
        "documentos": []
    }
    
    # Padrões regex para extração de dados
    patterns = {
        "processo": r"PROCESSO\s*#(\d+)",
        "cnpj_importador": r"HAFELE BRASIL\s*([\d\.\/\-]+)",
        "numero_duimp": r"Número\s*([\d\w/]+)",
        "data_registro": r"Data Registro\s*([\d/]+)",
        "operacao": r"Operacao\s*(\w+)",
        "tipo": r"Tipo\s*(\w+)",
        "responsavel_legal": r"Responsavel Legal\s*([\w\s\.]+)",
        "ref_importador": r"Ref\. Importador\s*([\w\s]+)",
        "data_cadastro": r"Data de Cadastro\s*([\d/]+)",
        "moeda_negociada": r"Moeda Negociada\s*([\d\s\-]+)",
        "cotacao": r"Cotacao\s*([\d\.]+)",
        "numero_adicao": r"Nº Adição\s*(\d+)",
        "numero_item": r"Nº do Item\s*(\d+)",
        "cif_usd": r"CIF \(US\$\)\s*([\d\.,]+)",
        "cif_brl": r"CIF \(R\$\)\s*([\d\.,]+)",
        "vmle_usd": r"VMLE \(US\$\)\s*([\d\.,]+)",
        "vmle_brl": r"VMLE \(R\$\)\s*([\d\.,]+)",
        "vmid_usd": r"VMLD \(US\$\)\s*([\d\.,]+)",
        "vmid_brl": r"VMLD \(R\$\)\s*([\d\.,]+)",
        "ii_calculado": r"II\s*([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)",
        "pis_calculado": r"PIS\s*([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)",
        "cofins_calculado": r"COFINS\s*([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)",
        "via_transporte": r"Via de Transporte\s*([\d\s\-]+)",
        "data_embarque": r"Data de Embarque\s*([\d/]+)",
        "peso_bruto": r"Peso Bruto\s*([\d\.,]+)",
        "pais_procedencia": r"País de Procedencia\s*([\w\s,\(\)]+)",
        "unidade_despacho": r"Unidade de Despacho\s*([\d\s\-]+)",
        "total_seguro_moeda": r"Total \(Moeda\)\s*([\d\.,]+)",
        "total_seguro_brl": r"Total \(R\$\)\s*([\d\.,]+)",
        "total_frete_moeda": r"Total \(Moeda\)\s*([\d\.,]+)",
        "total_frete_brl": r"Total \(R\$\)\s*([\d\.,]+)",
        "ncm": r"NCM\s*([\d\.]+)",
        "codigo_produto": r"Código Produto\s*([\d\w]+)",
        "cond_venda": r"Cond\. Venda\s*(\w+)",
        "fatura_invoice": r"Fatura/Invoice\s*([\d\w]+)",
        "denominacao_produto": r"DENOMINACAO DO PRODUTO\s*(.+)",
        "descricao_produto": r"DESCRICAO DO PRODUTO\s*(.+)",
        "codigo_interno": r"Código interno\s*([\d\.]+)",
        "pais_origem": r"País Origem\s*([\w\s]+)",
        "quantidade_estatistica": r"Qtde Unid\. Estatística\s*([\d\.,]+)",
        "unidade_estatistica": r"Unidad Estatística\s*([\w\s]+)",
        "quantidade_comercial": r"Qtde Unid\. Comercial\s*([\d\.,]+)",
        "unidade_comercial": r"Unidade Comercial\s*([\w\s]+)",
        "peso_liquido": r"Peso Líquido \(KG\)\s*([\d\.,]+)",
        "valor_unitario": r"Valor Unit Cond Venda\s*([\d\.,]+)",
        "valor_total": r"Valor Tot\. Cond Venda\s*([\d\.,]+)",
        "metodo_valoracao": r"Método de Valoração\s*(.+)",
        "condicao_venda_detalhe": r"Condição de Venda\s*(.+)",
        "valor_cond_venda_moeda": r"Vir Cond Venda \(Moeda\s*([\d\.,]+)",
        "valor_cond_venda_brl": r"Vir Cond Venda \(R\$\)\s*([\d\.,]+)",
        "frete_internacional": r"Frete Internac\. \(R\$\)\s*([\d\.,]+)",
        "seguro_internacional": r"Seguro Internac\. \(R\$\)\s*([\d\.,]+)",
        "cobertura_cambial": r"Cobertura Cambial\s*(.+)"
    }
    
    # Extrair dados usando regex
    for key, pattern in patterns.items():
        match = re.search(pattern, pdf_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            if key == "processo":
                data["processo"] = match.group(1)
            elif key == "cnpj_importador":
                data["importador"]["cnpj"] = match.group(1)
            elif key == "responsavel_legal":
                data["importador"]["responsavel_legal"] = match.group(1).strip()
            elif key == "ref_importador":
                data["importador"]["referencia"] = match.group(1).strip()
            # ... continue para outros campos
    
    return data

def create_xml_structure(data):
    """Cria a estrutura XML baseada no layout obrigatório"""
    
    # Criar elemento raiz
    lista_declaracoes = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(lista_declaracoes, "duimp")
    
    # Adicionar adicao (exemplo com dados básicos)
    adicao = ET.SubElement(duimp, "adicao")
    
    # Dados básicos da adição
    ET.SubElement(adicao, "numeroAdicao").text = "001"
    ET.SubElement(adicao, "numeroDUIMP").text = data.get("identificacao", {}).get("numero", "0000000000")
    
    # Informações do importador
    importador_elem = ET.SubElement(duimp, "importador")
    ET.SubElement(importador_elem, "importadorNome").text = "HAFELE BRASIL LTDA"
    ET.SubElement(importador_elem, "importadorNumero").text = data.get("importador", {}).get("cnpj", "02473058000188")
    
    # Dados da carga
    dados_carga = ET.SubElement(duimp, "carga")
    ET.SubElement(dados_carga, "cargaPesoBruto").text = data.get("dados_carga", {}).get("peso_bruto", "000000000000000")
    ET.SubElement(dados_carga, "cargaPesoLiquido").text = data.get("mercadoria", {}).get("peso_liquido", "000000000000000")
    
    # Mercadoria
    mercadoria_elem = ET.SubElement(adicao, "mercadoria")
    ET.SubElement(mercadoria_elem, "descricaoMercadoria").text = data.get("mercadoria", {}).get("descricao", "")
    ET.SubElement(mercadoria_elem, "numeroSequencialItem").text = "01"
    ET.SubElement(mercadoria_elem, "quantidade").text = data.get("mercadoria", {}).get("quantidade_comercial", "00000000000000")
    ET.SubElement(mercadoria_elem, "unidadeMedida").text = data.get("mercadoria", {}).get("unidade_comercial", "PECA").ljust(20)
    
    # Tributos
    tributos = ET.SubElement(adicao, "tributos")
    ET.SubElement(tributos, "iiAliquotaValorCalculado").text = data.get("tributos", {}).get("ii_calculado", "000000000000000")
    ET.SubElement(tributos, "pisPasepAliquotaValorDevido").text = data.get("tributos", {}).get("pis_devido", "000000000000000")
    ET.SubElement(tributos, "cofinsAliquotaValorDevido").text = data.get("tributos", {}).get("cofins_devido", "000000000000000")
    
    # Retornar XML formatado
    xml_str = ET.tostring(lista_declaracoes, encoding='unicode', method='xml')
    
    # Formatar o XML
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    return pretty_xml

# Interface principal
uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")

if uploaded_file is not None:
    # Mostrar informações do arquivo
    file_details = {
        "Nome do arquivo": uploaded_file.name,
        "Tipo do arquivo": uploaded_file.type,
        "Tamanho": f"{uploaded_file.size / 1024:.2f} KB"
    }
    
    st.subheader("📋 Detalhes do Arquivo")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nome", uploaded_file.name)
    with col2:
        st.metric("Tamanho", f"{uploaded_file.size / 1024:.2f} KB")
    with col3:
        st.metric("Tipo", "PDF")
    
    # Processar o PDF
    with st.spinner("Processando PDF..."):
        # Extrair texto
        pdf_text = extract_text_from_pdf(uploaded_file)
        
        # Extrair tabelas
        uploaded_file.seek(0)  # Reset file pointer
        tables = extract_tables_from_pdf(uploaded_file)
        
        # Parse dos dados
        data = parse_pdf_content(pdf_text)
        
        # Criar XML
        xml_content = create_xml_structure(data)
    
    # Abas para visualização
    tab1, tab2, tab3 = st.tabs(["📊 Dados Extraídos", "📄 XML Gerado", "🔍 Visualização Original"])
    
    with tab1:
        st.subheader("Dados Extraídos do PDF")
        
        # Mostrar dados em formato organizado
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Informações Gerais")
            if data.get("processo"):
                st.info(f"**Processo:** {data['processo']}")
            if data.get("importador", {}).get("cnpj"):
                st.info(f"**CNPJ Importador:** {data['importador']['cnpj']}")
            if data.get("identificacao", {}).get("numero"):
                st.info(f"**Número DUIMP:** {data['identificacao']['numero']}")
        
        with col2:
            st.markdown("#### Dados da Mercadoria")
            if data.get("mercadoria", {}).get("denominacao"):
                st.info(f"**Produto:** {data['mercadoria']['denominacao'][:50]}...")
            if data.get("mercadoria", {}).get("ncm"):
                st.info(f"**NCM:** {data['mercadoria']['ncm']}")
            if data.get("mercadoria", {}).get("valor_total"):
                st.info(f"**Valor Total:** R$ {data['mercadoria']['valor_total']}")
    
    with tab2:
        st.subheader("XML Gerado")
        
        # Editor de XML
        xml_editor = st.text_area(
            "Conteúdo XML",
            xml_content,
            height=400,
            help="Revise e edite o XML gerado se necessário"
        )
        
        # Botões de ação
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Baixar XML", use_container_width=True):
                # Criar arquivo para download
                st.download_button(
                    label="Clique para baixar",
                    data=xml_editor.encode('utf-8'),
                    file_name=f"DUIMP_{data.get('processo', 'NOVO')}.xml",
                    mime="application/xml",
                    key="download_xml"
                )
        
        with col2:
            if st.button("🔄 Validar XML", use_container_width=True):
                try:
                    ET.fromstring(xml_editor)
                    st.success("✅ XML válido!")
                except Exception as e:
                    st.error(f"❌ Erro na validação: {e}")
        
        with col3:
            if st.button("🗑️ Limpar", use_container_width=True):
                st.rerun()
    
    with tab3:
        st.subheader("Conteúdo Original do PDF")
        
        # Mostrar texto extraído
        with st.expander("Texto Extraído", expanded=False):
            st.text_area("", pdf_text[:5000], height=300)
        
        # Mostrar tabelas extraídas
        if tables:
            with st.expander("Tabelas Extraídas", expanded=False):
                for i, table in enumerate(tables[:3]):  # Limitar a 3 tabelas
                    st.write(f"**Tabela {i+1}:**")
                    df = pd.DataFrame(table)
                    st.dataframe(df, use_container_width=True)
        
        # Botão para visualizar mais
        if st.button("🔍 Ver PDF Completo"):
            # Mostrar PDF em visualizador
            base64_pdf = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf">'
            st.markdown(pdf_display, unsafe_allow_html=True)
    
    # Seção de logs
    with st.expander("📋 Logs do Processamento"):
        st.code(f"""
        Arquivo processado: {uploaded_file.name}
        Tamanho: {uploaded_file.size} bytes
        Páginas processadas: {len(pdf_text.split('\f'))}
        Tabelas encontradas: {len(tables)}
        Dados extraídos: {len(data.keys())} categorias
        """)
        
        # Mostrar estatísticas
        stats = {
            "Linhas de texto": len(pdf_text.split('\n')),
            "Palavras": len(pdf_text.split()),
            "Caracteres": len(pdf_text)
        }
        
        for stat, value in stats.items():
            st.metric(stat, value)

else:
    # Tela inicial quando nenhum arquivo foi carregado
    st.info("👆 Faça upload de um arquivo PDF para começar")
    
    # Exemplo de layout esperado
    with st.expander("📋 Exemplo do Layout Esperado do PDF"):
        st.markdown("""
        ### Estrutura do PDF Esperada:
        
        **Página 1:**
        - PROCESSO #28523
        - IMPORTADOR (HAFELE BRASIL)
        - IDENTIFICAÇÃO
        - MODAS/COTAÇÕES
        - RESUMO
        - CÁLCULOS DOS TRIBUTOS
        
        **Página 2:**
        - FRETE
        - COMPONENTES DO FRETE
        - EMBALAGEM
        - DOCUMENTOS
        
        **Página 3:**
        - DADOS DA MERCADORIA
        - CARACTERIZAÇÃO
        - DADOS DO EXPORTADOR
        - TRIBUTOS
        
        **Página 4:**
        - RESUMO COMPLETO
        - DOCUMENTOS
        - VALORES
        """)
    
    # Upload múltiplo de exemplo
    st.warning("⚠️ Apenas arquivos PDF com layout específico serão processados corretamente.")

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Desenvolvido para processamento de DUIMP | Conversor PDF → XML</p>
        <p>Versão 1.0 | Layout XML baseado na estrutura oficial</p>
    </div>
    """,
    unsafe_allow_html=True
)
