import streamlit as st
import pdfplumber
import xml.etree.ElementTree as ET
import re
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Conversor DUIMP PDF > XML SAP (V2)", layout="wide")

# --- FUNÇÕES AUXILIARES ---

def clean_text(text):
    """Remove quebras de linha excessivas e espaços extras."""
    if text:
        # Substitui quebras de linha por espaço e remove duplos espaços
        return re.sub(r'\s+', ' ', text).strip()
    return ""

def format_sap_number(value, length=15, decimal_places=2):
    """
    Converte 1.234,56 (PT-BR) -> 123456 (SAP Inteiro/Fixed Width).
    """
    if not value:
        return "0" * length
    
    try:
        if isinstance(value, str):
            # Remove pontos de milhar (1.000 -> 1000)
            clean_val = value.replace('.', '')
            # Troca vírgula decimal por ponto (1000,00 -> 1000.00)
            clean_val = clean_val.replace(',', '.')
            # Remove caracteres não numéricos exceto o ponto
            clean_val = re.sub(r'[^\d.]', '', clean_val)
            num = float(clean_val)
        else:
            num = float(value)

        # Multiplica pela precisão para remover o decimal (Ex: 10.50 * 100 = 1050)
        int_val = int(round(num * (10**decimal_places)))
        str_val = str(int_val)
        
        # Preenche com zeros à esquerda
        return str_val.zfill(length)
    except Exception:
        return "0" * length

def extract_field(text_block, pattern):
    """Extrai dados usando Regex. Retorna vazio se falhar."""
    if not text_block: 
        return ""
    match = re.search(pattern, text_block, re.IGNORECASE | re.DOTALL)
    if match:
        return clean_text(match.group(1))
    return ""

# --- LÓGICA DE EXTRAÇÃO (PARSE) ---

def parse_duimp_pdf(pdf_file):
    data = {
        "header": {},
        "itens": []
    }
    
    with pdfplumber.open(pdf_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # 1. Extração do Cabeçalho (Header)
    # Busca numero DUIMP no inicio do texto
    duimp_match = extract_field(full_text, r'Extrato da DUIMP\s+([0-9BR-]+)')
    data["header"]["numero_duimp"] = duimp_match.replace('-', '').replace('/', '') if duimp_match else "0000000000"
    
    # Importador
    data["header"]["cnpj_importador"] = extract_field(full_text, r'CNPJ do importador:\s*([\d\./-]+)').replace('.','').replace('/','').replace('-','')
    data["header"]["nome_importador"] = extract_field(full_text, r'Nome do importador:\s*(.*?)(?=Endereço)')
    
    # Pesos (Geral) - Pega a tabela de carga na primeira página
    # Regex ajustado para pegar o valor abaixo ou ao lado do cabeçalho
    peso_bruto = extract_field(full_text, r'Peso Bruto \(kg\):.*?([\d\.,]+)')
    data["header"]["peso_bruto_total"] = peso_bruto
    
    # 2. Divisão Inteligente dos Itens
    # O padrão nos seus arquivos é: "Extrato da Duimp ... : Item 00001"
    # Usamos re.split com parenteses () para manter o numero do item na lista resultante
    # Pattern: Quebra onde encontrar "Extrato da Duimp [qqer coisa] : Item [Digitos]"
    split_pattern = r'Extrato da Duimp .*?:\s*Item\s+(\d+)'
    
    parts = re.split(split_pattern, full_text, flags=re.DOTALL)
    
    # parts[0] = Tudo antes do primeiro item (Cabeçalho Geral)
    # parts[1] = Numero do Item 1 (ex: "00001")
    # parts[2] = Conteúdo do Item 1
    # parts[3] = Numero do Item 2
    # parts[4] = Conteúdo do Item 2
    # ...
    
    if len(parts) < 2:
        # Fallback: Tentar achar apenas "Item 00001" se o cabeçalho for diferente
        st.warning("Padrão de cabeçalho 'Extrato da Duimp' não encontrado para divisão de itens. Tentando padrão simplificado.")
        parts = re.split(r'Item\s+(\d+)', full_text, flags=re.DOTALL)

    # Loop pulando de 2 em 2 (Indice do numero e Indice do conteudo)
    for i in range(1, len(parts), 2):
        if i+1 >= len(parts): break # Segurança
        
        num_item = parts[i]      # Ex: 00001
        content_item = parts[i+1] # Texto do item
        
        item_data = {}
        item_data["numero_adicao"] = num_item
        
        # Extrações Específicas do Item
        item_data["codigo_produto"] = extract_field(content_item, r'Código do produto:\s*(.*?)(?=Versão|NCM)')
        item_data["ncm"] = extract_field(content_item, r'NCM:\s*(\d+)')
        item_data["descricao"] = extract_field(content_item, r'Detalhamento do Produto:\s*(.*?)(?=Número de Identificação|Código de Class)')
        item_data["pais_origem"] = extract_field(content_item, r'País de origem:\s*(.*?)(?=Código do Fabricante|Material|Fabricante)')
        
        # Valores
        item_data["peso_liquido"] = extract_field(content_item, r'Peso líquido \(kg\):\s*([\d\.,]+)')
        item_data["qtd_estatistica"] = extract_field(content_item, r'Quantidade na unidade estatística:\s*([\d\.,]+)')
        item_data["valor_total"] = extract_field(content_item, r'Valor total na condição de venda:\s*([\d\.,]+)')
        item_data["valor_unitario"] = extract_field(content_item, r'Valor unitário na condição de venda:\s*([\d\.,]+)')
        
        # Fabricante
        item_data["fabricante_nome"] = extract_field(content_item, r'Código do Fabricante/Produtor:\s*(.*?)(?=\(IT\)|\(CN\)|\(IN\)|\(AR\)|Endereço)')
        
        data["itens"].append(item_data)
        
    return data

# --- GERAÇÃO DO XML ---

def generate_sap_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")
    
    # Adições
    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")
        
        # Acrescimo (Exemplo fixo, extrair se necessario)
        acrescimo = ET.SubElement(adicao, "acrescimo")
        ET.SubElement(acrescimo, "codigoAcrescimo").text = "17"
        ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        ET.SubElement(acrescimo, "valorReais").text = format_sap_number("0", 15)
        
        # Impostos (Zerados por padrão se não encontrados, para não quebrar o SAP)
        ET.SubElement(adicao, "cideValorDevido").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA" 
        ET.SubElement(adicao, "condicaoVendaValorReais").text = format_sap_number(item.get("valor_total"), 15)
        
        # Dados Mercadoria
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = clean_text(item.get("ncm", "")).replace('.', '')
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_sap_number(item.get("peso_liquido"), 15, 5)
        
        ET.SubElement(adicao, "fornecedorNome").text = clean_text(item.get("fabricante_nome", "DESCONHECIDO"))[:60]
        
        # II
        ET.SubElement(adicao, "iiRegimeTributacaoCode").text = "1"
        ET.SubElement(adicao, "iiAliquotaValorRecolher").text = format_sap_number("0", 15)
        
        # Mercadoria Detalhe
        mercadoria = ET.SubElement(adicao, "mercadoria")
        desc = clean_text(item.get("descricao", "Item sem descrição"))
        ET.SubElement(mercadoria, "descricaoMercadoria").text = desc[:200] # Limite SAP
        ET.SubElement(mercadoria, "numeroSequencialItem").text = item.get("numero_adicao", "01")
        ET.SubElement(mercadoria, "quantidade").text = format_sap_number(item.get("qtd_estatistica"), 14, 5)
        ET.SubElement(mercadoria, "unidadeMedida").text = "UNIDADE"
        ET.SubElement(mercadoria, "valorUnitario").text = format_sap_number(item.get("valor_unitario"), 20, 8) # Unitario tem mais precisão
        
        # Chaves
        ET.SubElement(adicao, "numeroAdicao").text = item.get("numero_adicao", "1").zfill(3)
        ET.SubElement(adicao, "numeroDUIMP").text = data["header"]["numero_duimp"]
        ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = clean_text(item.get("pais_origem", ""))
        
        # PIS/COFINS/ICMS placeholders
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_sap_number("0", 15)
        ET.SubElement(adicao, "icmsBaseCalculoValor").text = format_sap_number("0", 15)
        
        # Reforma Tributária
        ET.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    # Finalização DUIMP (Tags de Rodapé)
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "PORTO DE PARANAGUA"
    ET.SubElement(duimp, "cargaPesoBruto").text = format_sap_number(data["header"]["peso_bruto_total"], 15, 5)
    ET.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
    ET.SubElement(duimp, "importadorNome").text = data["header"]["nome_importador"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj_importador"]
    ET.SubElement(duimp, "informacaoComplementar").text = f"DUIMP {data['header']['numero_duimp']} processada via conversor."
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["numero_duimp"]

    ET.indent(root, space="    ")
    return ET.tostring(root, encoding='utf-8', method='xml')

# --- INTERFACE ---
st.title("📄 Conversor DUIMP PDF > XML SAP (Corrigido)")
st.markdown("Extração robusta para Extratos DUIMP complexos.")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    with st.spinner('Processando...'):
        try:
            parsed_data = parse_duimp_pdf(uploaded_file)
            
            if not parsed_data["itens"]:
                st.error("Nenhum item foi encontrado. Verifique se o PDF é um Extrato de DUIMP válido.")
            else:
                st.success(f"Sucesso! DUIMP: {parsed_data['header']['numero_duimp']}")
                st.info(f"Itens encontrados: {len(parsed_data['itens'])}")
                
                # Preview simples
                with st.expander("Ver Itens Extraídos"):
                    st.write(parsed_data["itens"])

                xml_output = generate_sap_xml(parsed_data)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                file_name = f"M-DUIMP-{parsed_data['header']['numero_duimp']}_{timestamp}.xml"
                
                st.download_button("📥 Baixar XML SAP", xml_output, file_name, "application/xml")
                
        except Exception as e:
            st.error(f"Erro fatal: {str(e)}")
            st.warning("Dica: Se o erro persistir, o PDF pode ser uma imagem escaneada (sem texto selecionável).")
