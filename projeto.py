import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- FUNÇÕES DE LIMPEZA E FORMATAÇÃO ---

def clean_text(text):
    if not text: return ""
    text = text.replace('\n', ' ')
    return re.sub(r'\s+', ' ', text).strip()

def format_xml_number(value, length=15):
    if not value: return "0" * length
    clean = re.sub(r'[^\d,]', '', str(value)).replace(',', '')
    return clean.zfill(length)

def safe_extract(pattern, text, group=1):
    """Extrai texto ignorando erros de sintaxe de regex mal formada."""
    try:
        # Usamos re.escape em partes fixas se necessário, 
        # mas aqui o ajuste foi na escrita da expressão.
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(group).strip()
    except Exception as e:
        print(f"Erro no regex: {e}")
    return ""

def clean_partnumber(text):
    """Remove rótulos e limpa o código interno."""
    if not text: return ""
    # Remove termos comuns que não fazem parte do código
    for word in ["CÓDIGO", "CODIGO", "INTERNO", "PARTNUMBER", "PRODUTO", r"\(", r"\)"]:
        text = re.sub(word, "", text, flags=re.IGNORECASE)
    
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove traços ou pontos que sobraram no início por erro de captura
    text = text.lstrip("- ").strip()
    return text

# --- PARSER ---

def parse_pdf(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() or "" + "\n"

    data = {"header": {}, "itens": []}

    # Cabeçalho
    data["header"]["processo"] = safe_extract(r"PROCESSO\s*#?(\d+)", full_text)
    data["header"]["duimp"] = safe_extract(r"Numero\s*[:\n]*\s*([\dBR]+)", full_text)
    data["header"]["cnpj"] = safe_extract(r"CNPJ\s*[:\n]*\s*([\d\./-]+)", full_text).replace('.', '').replace('/', '').replace('-', '')
    data["header"]["importador"] = "HAFELE BRASIL LTDA"

    # Itens - O split usa \d+ para o número do item
    raw_itens = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", full_text)

    if len(raw_itens) > 1:
        for i in range(1, len(raw_itens), 2):
            num_item = raw_itens[i]
            content = raw_itens[i+1]

            # 1. Descrição Pura
            # Ajustado para não quebrar com parênteses
            desc_pura = safe_extract(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", content)
            desc_pura = clean_text(desc_pura)

            # 2. Código (Partnumber)
            # Buscamos o que está entre a tag de código e a próxima tag de dados (PAIS ou FABRICANTE)
            raw_code = safe_extract(r"PARTNUMBER\)\s*(.*?)\s*(?:PAIS|FABRICANTE|CONDICAO|VALOR|NCM)", content)
            
            # Limpeza radical do código para tirar o "Código interno"
            codigo_limpo = clean_partnumber(raw_code)

            # 3. Montagem Final
            descricao_final = f"{codigo_limpo} - {desc_pura}" if codigo_limpo else desc_pura

            item = {
                "numero_adicao": num_item.zfill(3),
                "descricao": descricao_final,
                "ncm": safe_extract(r"NCM\s*[:\n]*\s*([\d\.]+)", content).replace(".", "") or "00000000",
                "quantidade": safe_extract(r"Qtde Unid\. Comercial\s*[:\n]*\s*([\d\.,]+)", content) or "0",
                "valor_unitario": safe_extract(r"Valor Unit Cond Venda\s*[:\n]*\s*([\d\.,]+)", content) or "0",
                "valor_total": safe_extract(r"Valor Tot\. Cond Venda\s*[:\n]*\s*([\d\.,]+)", content) or "0",
                "peso_liquido": safe_extract(r"Peso Líquido \(KG\)\s*[:\n]*\s*([\d\.,]+)", content) or "0",
                "pis": safe_extract(r"PIS.*?Valor Devido.*?([\d\.,]+)", content) or "0",
                "cofins": safe_extract(r"COFINS.*?Valor Devido.*?([\d\.,]+)", content) or "0",
            }
            data["itens"].append(item)
            
    return data

# --- XML ---

def create_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")

    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")
        
        # Tags Fixas conforme solicitado anteriormente
        ET.SubElement(adicao, "cideValorAliquotaEspecifica").text = "0"*11
        ET.SubElement(adicao, "cideValorDevido").text = "0"*15
        ET.SubElement(adicao, "cideValorRecolher").text = "0"*15
        ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
        ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
        ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965"
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_xml_number(item["cofins"], 15)
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
        ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
        ET.SubElement(adicao, "condicaoVendaValorMoeda").text = format_xml_number(item["valor_total"], 15)
        ET.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item["ncm"]
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_xml_number(item["peso_liquido"], 15)
        
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(mercadoria, "numeroSequencialItem").text = item["numero_adicao"][-2:]
        ET.SubElement(mercadoria, "quantidade").text = format_xml_number(item["quantidade"], 14)
        ET.SubElement(mercadoria, "unidadeMedida").text = "UNIDADE"
        ET.SubElement(mercadoria, "valorUnitario").text = format_xml_number(item["valor_unitario"], 20)
        
        ET.SubElement(adicao, "numeroAdicao").text = item["numero_adicao"]
        duimp_nr = data["header"]["duimp"].replace("25BR", "")[:10]
        ET.SubElement(adicao, "numeroDUIMP").text = duimp_nr
        ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_xml_number(item["pis"], 15)
        ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
    ET.SubElement(duimp, "importadorNome").text = data["header"]["importador"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj"]
    info = ET.SubElement(duimp, "informacaoComplementar")
    info.text = f"PROCESSO: {data['header']['processo']}"
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["duimp"]
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)

    return root

# --- INTERFACE ---

def main():
    st.set_page_config(page_title="DUIMP XML Fix", layout="wide")
    st.title("Gerador XML DUIMP - Versão Estável")
    
    file = st.file_uploader("Selecione o Extrato PDF", type="pdf")
    
    if file and st.button("Gerar XML"):
        try:
            res = parse_pdf(file)
            if res["itens"]:
                xml_data = create_xml(res)
                xml_str = ET.tostring(xml_data, 'utf-8')
                pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
                
                st.success("Processado com sucesso!")
                st.write("**Exemplo Item 1:**", res["itens"][0]["descricao"])
                
                st.download_button("Baixar XML", pretty, f"DUIMP_{res['header']['processo']}.xml", "text/xml")
            else:
                st.error("Não foram encontrados itens no PDF.")
        except Exception as e:
            st.error(f"Erro no processamento: {e}")

if __name__ == "__main__":
    main()
