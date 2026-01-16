import streamlit as st
import pdfplumber
import xml.etree.ElementTree as ET
import re
from io import BytesIO
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Conversor DUIMP PDF > XML SAP", layout="wide")

# --- FUNÇÕES AUXILIARES DE FORMATAÇÃO ---

def format_sap_number(value, length=15, decimal_places=2):
    """
    Formata um valor numérico (string ou float) para o padrão SAP:
    Ex: 100,50 -> Remove pontuação, ajusta decimais e preenche com zeros à esquerda.
    """
    if not value:
        return "0" * length
    
    # Limpeza básica da string vinda do PDF
    if isinstance(value, str):
        # Remove pontos de milhar e substitui vírgula decimal por ponto
        clean_val = value.replace('.', '').replace(',', '.')
        try:
            num = float(clean_val)
        except ValueError:
            return "0" * length
    else:
        num = float(value)

    # Converter para inteiro removendo o ponto decimal (multiplicando pela precisão)
    # O XML parece usar representação sem vírgula, apenas digitos.
    # Ex: 1066.01 -> 106601
    int_val = int(round(num * (10**decimal_places)))
    str_val = str(int_val)
    
    return str_val.zfill(length)

def clean_text(text):
    """Remove quebras de linha e espaços extras."""
    if text:
        return text.replace('\n', ' ').strip()
    return ""

def extract_field(text_block, pattern):
    """Extrai dados usando Regex de um bloco de texto."""
    match = re.search(pattern, text_block, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

# --- LÓGICA DE EXTRAÇÃO DO PDF ---

def parse_duimp_pdf(pdf_file):
    data = {
        "header": {},
        "itens": [],
        "tributos_gerais": {} # Caso haja tributos consolidados
    }
    
    with pdfplumber.open(pdf_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

        # --- 1. Extração Cabeçalho e Importador ---
        # DUIMP Numero
        duimp_match = re.search(r'Extrato da DUIMP\s+([0-9BR-]+)', full_text)
        data["header"]["numero_duimp"] = duimp_match.group(1).replace('-', '').replace('/', '') if duimp_match else "0000000000"
        
        # Importador
        data["header"]["cnpj_importador"] = extract_field(full_text, r'CNPJ do importador:\s*([\d\./-]+)').replace('.','').replace('/','').replace('-','')
        data["header"]["nome_importador"] = extract_field(full_text, r'Nome do importador:\s*(.+)')
        
        # Endereço (Simplificado via regex, pode precisar de ajuste fino dependendo da variação do endereço)
        endereco_match = re.search(r'Endereço do importador:\s*(.+?)(?=Informações Complementares|Carga)', full_text, re.DOTALL)
        data["header"]["endereco_importador"] = clean_text(endereco_match.group(1)) if endereco_match else ""

        # --- 2. Dados da Carga ---
        # Peso Bruto e Líquido (Geral) - Busca na tabela de carga
        peso_bruto_match = re.search(r'Peso Bruto \(kg\):\s*([\d\.,]+)', full_text)
        data["header"]["peso_bruto_total"] = peso_bruto_match.group(1) if peso_bruto_match else "0"
        
        peso_liq_match = re.search(r'Peso Liquido \(kg\):\s*([\d\.,]+)', full_text)
        data["header"]["peso_liquido_total"] = peso_liq_match.group(1) if peso_liq_match else "0"

        data["header"]["pais_procedencia"] = extract_field(full_text, r'País de Procedência:\s*(.+)')
        
        # --- 3. Extração dos Itens (Adições) ---
        # A lógica aqui procura por padrões "Item 00001", "Item 00002" etc.
        # Como o PDFplumber extrai texto linear, vamos dividir pelos marcadores de item.
        
        # Regex para identificar início de item
        item_splits = re.split(r'(Extrato da Duimp .* Item \d+)', full_text)
        
        # O primeiro split geralmente é o cabeçalho geral, ignoramos
        for i in range(1, len(item_splits), 2):
            header_item = item_splits[i] # O texto "Item 00001"
            content_item = item_splits[i+1] # O conteúdo do item
            
            item_data = {}
            
            # Numero Adição
            num_adicao_match = re.search(r'Item\s+(\d+)', header_item)
            item_data["numero_adicao"] = num_adicao_match.group(1) if num_adicao_match else f"{i:03d}"
            
            # Dados do Produto
            item_data["codigo_produto"] = extract_field(content_item, r'Código do produto:\s*(.+)')
            item_data["ncm"] = extract_field(content_item, r'NCM:\s*(\d+)')
            item_data["descricao"] = extract_field(content_item, r'Detalhamento do Produto:\s*(.+?)(?=Número de Identificação|Código de Class)')
            
            # País Origem
            item_data["pais_origem"] = extract_field(content_item, r'País de origem:\s*(.+?)(?=Código do Fabricante|Material)')
            
            # Valores e Pesos do Item
            peso_liq_item = extract_field(content_item, r'Peso líquido \(kg\):\s*([\d\.,]+)')
            item_data["peso_liquido"] = peso_liq_item if peso_liq_item else "0"
            
            qtd_est = extract_field(content_item, r'Quantidade na unidade estatística:\s*([\d\.,]+)')
            item_data["qtd_estatistica"] = qtd_est if qtd_est else "0"
            
            valor_unit = extract_field(content_item, r'Valor unitário na condição de venda:\s*([\d\.,]+)')
            item_data["valor_unitario"] = valor_unit if valor_unit else "0"
            
            valor_total = extract_field(content_item, r'Valor total na condição de venda:\s*([\d\.,]+)')
            item_data["valor_total_moeda"] = valor_total if valor_total else "0"
            
            # Fabricante
            fab_nome = extract_field(content_item, r'Código do Fabricante/Produtor:\s*(.+?)(?=Endereço)')
            item_data["fabricante_nome"] = clean_text(fab_nome)

            # TRIBUTOS (Simulação de extração - muitas vezes o PDF de extrato tem tabela vazia se for preliminar)
            # Aqui tentamos pegar a tabela de tributos se existir texto
            # Padrão: II, IPI, PIS, COFINS
            # Nota: No seu PDF de exemplo os tributos estavam vazios ou zerados. 
            # O código abaixo assume valores padrão zerados se não encontrar, para respeitar o XML.
            
            data["itens"].append(item_data)

    return data

# --- LÓGICA DE GERAÇÃO DO XML ---

def generate_sap_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")
    
    # 1. Loop das Adições (Itens)
    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")
        
        # --- Bloco Acrescimo (Exemplo fixo ou calculado) ---
        acrescimo = ET.SubElement(adicao, "acrescimo")
        ET.SubElement(acrescimo, "codigoAcrescimo").text = "17" # Padrão observado
        ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        # Valores simulados ou extraídos se disponíveis (Colocando placeholder formatado)
        ET.SubElement(acrescimo, "valorReais").text = format_sap_number("0", 15) 
        
        # --- CIDE ---
        ET.SubElement(adicao, "cideValorDevido").text = format_sap_number("0", 15)

        # --- Condição de Venda ---
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA" # Exemplo, ideal extrair do PDF se existir
        ET.SubElement(adicao, "condicaoVendaValorReais").text = format_sap_number(item["valor_total_moeda"], 15) # Simplificação: usando valor moeda como base
        
        # --- Dados Mercadoria ---
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item["ncm"].replace('.', '')
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_sap_number(item["peso_liquido"], 15, 5) # Peso costuma ter 5 casas no XML SAP
        
        # --- Fornecedor ---
        ET.SubElement(adicao, "fornecedorNome").text = item["fabricante_nome"][:60] # Limite caracteres
        
        # --- II (Imposto Importação) ---
        ET.SubElement(adicao, "iiRegimeTributacaoCode").text = "1"
        ET.SubElement(adicao, "iiAliquotaValorRecolher").text = format_sap_number("0", 15)

        # --- Mercadoria Detalhe ---
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = clean_text(item["descricao"])[:200]
        ET.SubElement(mercadoria, "numeroSequencialItem").text = item["numero_adicao"]
        ET.SubElement(mercadoria, "quantidade").text = format_sap_number(item["qtd_estatistica"], 14, 5)
        ET.SubElement(mercadoria, "unidadeMedida").text = "UNIDADE" # Padrão, extrair se possível
        ET.SubElement(mercadoria, "valorUnitario").text = format_sap_number(item["valor_unitario"], 20, 8)

        # --- Identificadores Chave ---
        ET.SubElement(adicao, "numeroAdicao").text = item["numero_adicao"].zfill(3)
        ET.SubElement(adicao, "numeroDUIMP").text = data["header"]["numero_duimp"]
        
        # --- Pais Origem ---
        ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = item["pais_origem"]

        # --- PIS/COFINS/ICMS (Placeholders estruturais conforme XML modelo) ---
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "icmsBaseCalculoValor").text = format_sap_number("0", 15)
        
        # --- CBS/IBS (Reforma Tributária - presente no seu PDF) ---
        ET.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
        
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    # 2. Dados Gerais da DUIMP (Tags finais do XML)
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "PORTO - RECINTO PADRAO" # Extrair do PDF se disponível
    ET.SubElement(duimp, "cargaPesoBruto").text = format_sap_number(data["header"]["peso_bruto_total"], 15, 5)
    ET.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA" # Fixo baseado no PDF exemplo ou extrair
    
    # Importador
    ET.SubElement(duimp, "importadorNome").text = data["header"]["nome_importador"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj_importador"]
    
    # Info Complementar
    ET.SubElement(duimp, "informacaoComplementar").text = f"DUIMP {data['header']['numero_duimp']} gerada via conversor PDF."
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["numero_duimp"]

    # Formatação final para string bonita
    # Python 3.9+ 
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding='utf-8', method='xml')

# --- INTERFACE STREAMLIT ---

st.title("📄 Conversor Extrato DUIMP (PDF) -> XML SAP")
st.markdown("""
Esta ferramenta extrai dados de **Extratos de DUIMP em PDF** e gera um arquivo **XML formatado** para importação em sistemas ERP (Padrão SAP/Comex).
""")

uploaded_file = st.file_uploader("Faça upload do PDF da DUIMP", type="pdf")

if uploaded_file is not None:
    with st.spinner('Lendo e processando PDF...'):
        try:
            # 1. Parse do PDF
            parsed_data = parse_duimp_pdf(uploaded_file)
            
            st.success(f"PDF Processado com sucesso! DUIMP: {parsed_data['header']['numero_duimp']}")
            
            # Preview dos dados extraídos
            st.subheader("Dados Extraídos (Preview)")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Importador:** {parsed_data['header']['nome_importador']}")
                st.info(f"**Peso Bruto Total:** {parsed_data['header']['peso_bruto_total']} kg")
            with col2:
                st.info(f"**Total de Itens Identificados:** {len(parsed_data['itens'])}")
            
            with st.expander("Ver detalhes dos Itens Extraídos"):
                st.json(parsed_data["itens"])

            # 2. Geração do XML
            xml_output = generate_sap_xml(parsed_data)
            
            st.subheader("Arquivo XML Gerado")
            st.text_area("XML Preview (Início)", value=xml_output.decode("utf-8")[:1000] + "...", height=200)
            
            # Botão de Download
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            file_name = f"M-DUIMP-{parsed_data['header']['numero_duimp']}_{timestamp}.xml"
            
            st.download_button(
                label="📥 Baixar XML Completo",
                data=xml_output,
                file_name=file_name,
                mime="application/xml"
            )

        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
            st.warning("Verifique se o PDF é um 'Extrato da DUIMP' válido e legível.")

# Rodapé
st.markdown("---")
st.caption("Desenvolvido para automação de processos de Comércio Exterior.")
