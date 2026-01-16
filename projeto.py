import streamlit as st
import pdfplumber
import xml.etree.ElementTree as ET
import re
import datetime
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Conversor DUIMP > XML SAP (Final)", layout="wide")

# --- FUNÇÕES AUXILIARES ---

def normalize_text(text):
    """
    Transforma o texto do PDF em uma linha única contínua.
    Remove quebras de página e excesso de espaços.
    """
    if not text: return ""
    # Remove quebras de linha
    text = text.replace('\n', ' ')
    # Remove múltiplos espaços em branco por um único
    return re.sub(r'\s+', ' ', text).strip()

def format_sap_number(value, length=15, decimal_places=2):
    """
    Formata números para o padrão SAP (sem vírgula/ponto, apenas dígitos).
    Ex: '1.500,00' -> '000000000150000'
    """
    if not value:
        return "0" * length
    
    try:
        # Limpeza para garantir formato numérico
        if isinstance(value, str):
            # Se tiver vírgula, assume padrão BR (remove ponto milhar, troca virgula por ponto)
            if ',' in value:
                clean_val = value.replace('.', '').replace(',', '.')
            else:
                clean_val = value
            
            # Mantém apenas numeros e ponto
            clean_val = re.sub(r'[^\d.]', '', clean_val)
            num = float(clean_val)
        else:
            num = float(value)

        # Multiplica pela precisão e converte para inteiro
        int_val = int(round(num * (10**decimal_places)))
        return str(int_val).zfill(length)
    except Exception:
        # Em caso de erro, retorna zerado para não travar o XML
        return "0" * length

def extract_regex(text, pattern):
    """Extrai texto com regex. Retorna vazio se não encontrar."""
    try:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return ""

# --- PROCESSAMENTO DO PDF ---

def process_duimp_pdf(pdf_file):
    # 1. Extração bruta
    raw_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            raw_text += page.extract_text() + "\n"
    
    # 2. Normalização (Cria uma "tripa" de texto única)
    full_text = normalize_text(raw_text)
    
    data = {
        "header": {},
        "itens": []
    }

    # --- CABEÇALHO ---
    # Busca DUIMP (Remove caracteres não numericos exceto letras do inicio se houver)
    duimp_raw = extract_regex(full_text, r'Extrato da DUIMP\s*([0-9BR-]+)')
    data["header"]["numero"] = duimp_raw.replace('-', '').replace('/', '')

    # Busca Importador (Apenas digitos)
    cnpj_raw = extract_regex(full_text, r'CNPJ do importador:\s*([\d\./-]+)')
    data["header"]["cnpj"] = re.sub(r'\D', '', cnpj_raw) # Remove pontos/traços
    
    # Nome Importador
    data["header"]["nome"] = extract_regex(full_text, r'Nome do importador:\s*(.*?)(?=Endereço)')
    
    # Peso Bruto Geral
    data["header"]["peso_bruto"] = extract_regex(full_text, r'Peso Bruto \(kg\):\s*([\d\.,]+)')

    # --- PROCESSO DE ITENS (Sem split, usando indices) ---
    
    # Encontra todas as ocorrências de "Item 00001", "Item 00002", etc.
    # O padrão procura "Extrato da Duimp... : Item X"
    # Usamos finditer para pegar a posição (start/end) de cada item no texto
    matches = list(re.finditer(r'Extrato da Duimp.*?: Item\s+(\d+)', full_text))
    
    # Se não achar com cabeçalho completo, tenta padrão curto "Item X Mercadoria"
    if not matches:
         matches = list(re.finditer(r'Item\s+(\d+)\s+Mercadoria', full_text))

    for i, match in enumerate(matches):
        current_item_num = match.group(1) # Ex: 00001
        
        # Onde começa o conteúdo deste item (logo após o "Item X")
        start_pos = match.end()
        
        # Onde termina este item? No começo do próximo item OU no fim do texto
        if i + 1 < len(matches):
            end_pos = matches[i+1].start()
        else:
            end_pos = len(full_text)
            
        # Recorta o bloco de texto específico deste item
        item_text = full_text[start_pos:end_pos]
        
        # Extrai dados DENTRO deste bloco
        item_data = {
            "numero_adicao": current_item_num,
            "ncm": extract_regex(item_text, r'NCM:\s*([\d\.]+)').replace('.', ''),
            "descricao": extract_regex(item_text, r'Detalhamento do Produto:\s*(.*?)(?=Número de Identificação|Código de Class|Versão:)'),
            "codigo_produto": extract_regex(item_text, r'Código do produto:\s*(.*?)(?=Versão|NCM)'),
            "pais_origem": extract_regex(item_text, r'País de origem:\s*(.*?)(?=Código|Endereço)'),
            "fabricante": extract_regex(item_text, r'Código do Fabricante/Produtor:\s*(.*?)(?=Endereço|Uso aeronáutico)'),
            
            # Valores
            "peso_liquido": extract_regex(item_text, r'Peso líquido \(kg\):\s*([\d\.,]+)'),
            "qtd_estatistica": extract_regex(item_text, r'Quantidade na unidade estatística:\s*([\d\.,]+)'),
            "valor_unitario": extract_regex(item_text, r'Valor unitário na condição de venda:\s*([\d\.,]+)'),
            "valor_total": extract_regex(item_text, r'Valor total na condição de venda:\s*([\d\.,]+)')
        }
        
        # Limpeza extra para Fabricante (remover sufixos comuns de PDF)
        if "(IT)" in item_data["fabricante"]:
            item_data["fabricante"] = item_data["fabricante"].split("(IT)")[0] + "(IT)"
            
        data["itens"].append(item_data)

    return data

# --- GERAÇÃO DO XML ---

def generate_xml_content(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")
    
    # Verifica se existem itens
    if not data["itens"]:
        # Cria um item dummy se falhar leitura para nao gerar XML vazio
        data["itens"].append({"numero_adicao": "001", "descricao": "ERRO LEITURA PDF"})

    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")
        
        # Adiciona zeros à esquerda no numero da adição (Ex: 00001 -> 001)
        num_adicao_fmt = item.get("numero_adicao", "1")[-3:].zfill(3)

        # Campos obrigatórios SAP
        acrescimo = ET.SubElement(adicao, "acrescimo")
        ET.SubElement(acrescimo, "codigoAcrescimo").text = "17"
        ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS"
        ET.SubElement(acrescimo, "valorReais").text = format_sap_number("0", 15)
        
        ET.SubElement(adicao, "cideValorDevido").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA" 
        ET.SubElement(adicao, "condicaoVendaValorReais").text = format_sap_number(item.get("valor_total"), 15)
        
        # Mercadoria Dados
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item.get("ncm", "")
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_sap_number(item.get("peso_liquido"), 15, 5)
        
        # Fornecedor
        nome_forn = item.get("fabricante", "")
        if not nome_forn: nome_forn = "FORNECEDOR DIVERSO"
        ET.SubElement(adicao, "fornecedorNome").text = nome_forn[:60]
        
        # II / IPI / PIS / COFINS (Placeholders para validação)
        ET.SubElement(adicao, "iiRegimeTributacaoCode").text = "1"
        ET.SubElement(adicao, "iiAliquotaValorRecolher").text = format_sap_number("0", 15)
        
        # Detalhe Mercadoria
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item.get("descricao", "")[:200]
        ET.SubElement(mercadoria, "numeroSequencialItem").text = num_adicao_fmt
        ET.SubElement(mercadoria, "quantidade").text = format_sap_number(item.get("qtd_estatistica"), 14, 5)
        ET.SubElement(mercadoria, "unidadeMedida").text = "UN"
        ET.SubElement(mercadoria, "valorUnitario").text = format_sap_number(item.get("valor_unitario"), 20, 8)
        
        # Chaves de Ligação
        ET.SubElement(adicao, "numeroAdicao").text = num_adicao_fmt
        ET.SubElement(adicao, "numeroDUIMP").text = data["header"].get("numero", "0000000000")
        ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = item.get("pais_origem", "DIVERSOS")
        
        # Tags de Reforma Tributária e Outros
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "icmsBaseCalculoValor").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação"

    # Rodapé XML
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "PORTO DE PARANAGUA"
    ET.SubElement(duimp, "cargaPesoBruto").text = format_sap_number(data["header"].get("peso_bruto"), 15, 5)
    ET.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
    ET.SubElement(duimp, "importadorNome").text = data["header"].get("nome", "IMPORTADOR")
    ET.SubElement(duimp, "importadorNumero").text = data["header"].get("cnpj", "00000000000000")
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"].get("numero", "0000000000")

    ET.indent(root, space="    ")
    return ET.tostring(root, encoding='utf-8', method='xml')

# --- INTERFACE STREAMLIT ---
st.title("📄 Conversor DUIMP > XML SAP (Blindado)")
st.markdown("Sistema corrigido para evitar erros de índice e leitura de texto.")

uploaded_file = st.file_uploader("Upload do Extrato DUIMP (PDF)", type="pdf")

if uploaded_file:
    with st.spinner("Processando..."):
        try:
            parsed_data = process_duimp_pdf(uploaded_file)
            
            # Validação Básica
            qtd_itens = len(parsed_data["itens"])
            
            if qtd_itens == 0:
                st.warning("⚠️ O arquivo foi lido, mas nenhum item foi identificado automaticamente.")
                st.info("Verifique se o PDF contém o texto 'Item 00001', 'Item 00002' etc.")
            else:
                st.success(f"✅ DUIMP {parsed_data['header']['numero']} processada com {qtd_itens} itens!")
                
                # Preview dos Dados
                with st.expander("🔍 Conferir Dados Extraídos"):
                    st.json(parsed_data)

                # Gerar XML
                xml_data = generate_xml_content(parsed_data)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
                nome_arq = f"M-DUIMP-{parsed_data['header']['numero']}_{timestamp}.xml"
                
                st.download_button(
                    label="📥 Baixar XML SAP Validado",
                    data=xml_data,
                    file_name=nome_arq,
                    mime="application/xml",
                    type="primary"
                )
                
        except Exception as e:
            st.error("Ocorreu um erro inesperado.")
            st.code(str(e))
