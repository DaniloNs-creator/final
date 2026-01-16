import streamlit as st
import pdfplumber
import xml.etree.ElementTree as ET
import re
import datetime
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Conversor DUIMP PDF > XML SAP (Robust)", layout="wide")

# --- FUNÇÕES DE LIMPEZA E FORMATAÇÃO ---

def normalize_text(text):
    """
    Remove quebras de linha e espaços duplos para facilitar o Regex.
    Transforma o texto em uma linha contínua.
    """
    if not text: return ""
    # Substitui quebras de linha por espaço
    text = text.replace('\n', ' ')
    # Remove múltiplos espaços
    return re.sub(r'\s+', ' ', text).strip()

def format_sap_number(value, length=15, decimal_places=2):
    """
    Converte valores (1.000,00 ou 1000.00) para formato SAP (apenas números).
    Ex: 10,00 -> 000000000001000 (considerando precisão)
    """
    if not value:
        return "0" * length
    
    try:
        if isinstance(value, str):
            # Limpa tudo que não for dígito ou vírgula/ponto
            # Padrão brasileiro: ponto separa milhar, virgula separa decimal
            # Mas às vezes o PDF traz misturado. Vamos assumir virgula como decimal principal se existir.
            
            clean_val = value.strip()
            if ',' in clean_val:
                # Padrão PT-BR: remove ponto de milhar, troca virgula por ponto
                clean_val = clean_val.replace('.', '').replace(',', '.')
            else:
                # Padrão US ou sem decimal visual: mantem
                pass
            
            # Remove caracteres estranhos
            clean_val = re.sub(r'[^\d.]', '', clean_val)
            num = float(clean_val)
        else:
            num = float(value)

        # Multiplica pela precisão (Ex: 2 casas decimais -> *100)
        int_val = int(round(num * (10**decimal_places)))
        str_val = str(int_val)
        
        return str_val.zfill(length)
    except Exception:
        return "0" * length

def extract_regex(text, pattern, default=""):
    """Tenta extrair um valor usando regex. Retorna default se falhar."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return default

# --- LÓGICA DE PROCESSAMENTO DO PDF ---

def process_duimp_pdf(pdf_file):
    # 1. Extração do Texto Bruto
    full_text_raw = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text_raw += page.extract_text() + "\n"
    
    # 2. Normalização (Crucial para o Regex funcionar)
    full_text_norm = normalize_text(full_text_raw)
    
    data = {
        "header": {},
        "itens": []
    }

    # --- EXTRAÇÃO DO CABEÇALHO ---
    
    # DUIMP
    data["header"]["numero"] = extract_regex(full_text_norm, r'Extrato da DUIMP\s*([0-9BR-]+)')
    data["header"]["numero"] = data["header"]["numero"].replace('-', '').replace('/', '')

    # Importador
    data["header"]["cnpj"] = extract_regex(full_text_norm, r'CNPJ do importador:\s*([\d\./-]+)').replace('\D', '') # Remove tudo que não é dígito
    data["header"]["nome"] = extract_regex(full_text_norm, r'Nome do importador:\s*(.*?)(?=Endereço)')
    
    # Carga (Geral)
    # Procurando na tabela de Procedência/Peso
    # O regex procura "Peso Bruto (kg):" seguido de algum valor numérico
    data["header"]["peso_bruto"] = extract_regex(full_text_norm, r'Peso Bruto \(kg\):\s*([\d\.,]+)')
    
    # --- EXTRAÇÃO DOS ITENS ---
    
    # Estratégia: Dividir o texto usando o marcador "Item 0000X"
    # O padrão no texto normalizado será algo como "... Versão 0001: Item 00001"
    
    # Encontrar todos os indices onde começa um Item
    item_matches = list(re.finditer(r'Extrato da Duimp.*?: Item\s+(\d+)', full_text_norm))
    
    if not item_matches:
        # Tenta padrão alternativo se o primeiro falhar
        item_matches = list(re.finditer(r'Item\s+(\d+)\s+Mercadoria', full_text_norm))

    for i, match in enumerate(item_matches):
        start_idx = match.end() # Começa logo depois de "Item X"
        
        # O fim deste item é o começo do próximo item, ou o fim do texto
        end_idx = item_matches[i+1].start() if i + 1 < len(item_matches) else len(full_text_norm)
        
        item_text = full_text_norm[start_idx:end_idx]
        num_item = match.group(1) # O número capturado (ex: 00001)

        # Extração de campos dentro do bloco do item
        item_data = {
            "numero_adicao": num_item,
            "ncm": extract_regex(item_text, r'NCM:\s*([\d\.]+)').replace('.', ''),
            "codigo_produto": extract_regex(item_text, r'Código do produto:\s*(.*?)(?=Versão|NCM)'),
            "descricao": extract_regex(item_text, r'Detalhamento do Produto:\s*(.*?)(?=Número de Identificação|Código de Class)'),
            "pais_origem": extract_regex(item_text, r'País de origem:\s*(.*?)(?=Código|Endereço)'),
            "fabricante": extract_regex(item_text, r'Código do Fabricante/Produtor:\s*(.*?)(?=\(IT\)|\(CN\)|\(IN\)|\(AR\)|Endereço)'),
            
            # Valores Numéricos
            "peso_liquido": extract_regex(item_text, r'Peso líquido \(kg\):\s*([\d\.,]+)'),
            "qtd_estatistica": extract_regex(item_text, r'Quantidade na unidade estatística:\s*([\d\.,]+)'),
            "valor_unitario": extract_regex(item_text, r'Valor unitário na condição de venda:\s*([\d\.,]+)'),
            "valor_total": extract_regex(item_text, r'Valor total na condição de venda:\s*([\d\.,]+)')
        }
        
        # Limpeza fina
        if not item_data["fabricante"]:
             # Tenta pegar a linha logo após "Código do Fabricante" se o regex falhou
             item_data["fabricante"] = extract_regex(item_text, r'Código do Fabricante/Produtor:\s*(.{10,50}?)Endereço')

        data["itens"].append(item_data)

    return data, full_text_norm

# --- GERAÇÃO DO XML ---

def generate_xml_content(data):
    # Namespaces e Estrutura Básica
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")
    
    # --- Loop de Adições ---
    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")
        
        # Campos Obrigatórios (Hardcoded ou Extraídos)
        acrescimo = ET.SubElement(adicao, "acrescimo")
        ET.SubElement(acrescimo, "codigoAcrescimo").text = "17"
        ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS"
        ET.SubElement(acrescimo, "valorReais").text = format_sap_number("0", 15)
        
        ET.SubElement(adicao, "cideValorDevido").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA" # Padrão do seu exemplo
        ET.SubElement(adicao, "condicaoVendaValorReais").text = format_sap_number(item["valor_total"], 15)
        
        # Dados Mercadoria
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item["ncm"]
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_sap_number(item["peso_liquido"], 15, 5)
        
        ET.SubElement(adicao, "fornecedorNome").text = item["fabricante"][:60] # Limita tamanho SAP
        
        # Impostos (II, IPI, PIS, COFINS) - Preenche com zeros se não tiver dados
        ET.SubElement(adicao, "iiRegimeTributacaoCode").text = "1"
        ET.SubElement(adicao, "iiAliquotaValorRecolher").text = format_sap_number("0", 15)
        
        # Tag Mercadoria
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item["descricao"][:200]
        ET.SubElement(mercadoria, "numeroSequencialItem").text = item["numero_adicao"][-3:] # Pega '001' de '00001'
        ET.SubElement(mercadoria, "quantidade").text = format_sap_number(item["qtd_estatistica"], 14, 5)
        ET.SubElement(mercadoria, "unidadeMedida").text = "UN"
        ET.SubElement(mercadoria, "valorUnitario").text = format_sap_number(item["valor_unitario"], 20, 8)
        
        # IDs
        ET.SubElement(adicao, "numeroAdicao").text = item["numero_adicao"][-3:].zfill(3)
        ET.SubElement(adicao, "numeroDUIMP").text = data["header"]["numero"]
        ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = item["pais_origem"]
        
        # Placeholders Tributários para validar no SAP
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "icmsBaseCalculoValor").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação"

    # --- Tags Gerais da DUIMP (Fim do arquivo) ---
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "PORTO DE PARANAGUA"
    ET.SubElement(duimp, "cargaPesoBruto").text = format_sap_number(data["header"]["peso_bruto"], 15, 5)
    ET.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
    ET.SubElement(duimp, "importadorNome").text = data["header"]["nome"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj"]
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["numero"]

    # Formatação (Indentation) para ficar legível
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding='utf-8', method='xml')

# --- INTERFACE ---
st.title("🚀 Conversor DUIMP > SAP XML (Versão Corrigida)")
st.markdown("""
Esta versão normaliza o texto do PDF antes de processar, garantindo que os dados sejam lidos 
mesmo com quebras de linha irregulares.
""")

uploaded_file = st.file_uploader("Arraste seu PDF aqui", type="pdf")

if uploaded_file:
    with st.spinner("Lendo e Mapeando Arquivo..."):
        try:
            # 1. Processar
            parsed_data, debug_text = process_duimp_pdf(uploaded_file)
            
            # 2. Verificações
            if not parsed_data["header"].get("numero"):
                st.error("Não foi possível ler o número da DUIMP. O PDF pode estar como imagem.")
            elif not parsed_data["itens"]:
                st.warning("Cabeçalho lido, mas nenhum ITEM foi encontrado. Verifique a aba 'Texto Debug'.")
            else:
                st.success(f"Sucesso! DUIMP {parsed_data['header']['numero']} lida com {len(parsed_data['itens'])} itens.")
                
                # Preview dos Dados
                with st.expander("🔍 Visualizar Dados Extraídos"):
                    st.write("**Cabeçalho:**", parsed_data["header"])
                    st.write("**Itens:**")
                    st.dataframe(parsed_data["itens"])
                
                # 3. Gerar XML
                xml_bytes = generate_xml_content(parsed_data)
                
                filename = f"M-DUIMP-{parsed_data['header']['numero']}.xml"
                st.download_button(
                    label="📥 BAIXAR XML SAP",
                    data=xml_bytes,
                    file_name=filename,
                    mime="application/xml",
                    type="primary"
                )

            # Debug Opcional
            with st.expander("🛠️ Texto Debug (O que o robô leu)"):
                st.text(debug_text[:3000]) # Mostra os primeiros 3000 caracteres

        except Exception as e:
            st.error(f"Ocorreu um erro técnico: {e}")
