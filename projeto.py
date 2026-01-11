import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# --- FUNÇÕES UTILITÁRIAS ---

def safe_extract(pattern, text, group=1, default=""):
    """
    Tenta extrair um valor usando regex. Se não encontrar, retorna o valor default.
    """
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            # Remove aspas e limpa espaços
            clean_val = match.group(group).replace('"', '').replace("'", "").strip()
            return clean_val
    except Exception:
        pass
    return default

def format_xml_number(value, length=15):
    """
    Formata valores para o padrão XML (sem vírgula, zeros à esquerda).
    Ex: '1.234,56' -> '000000000123456'
    """
    if not value:
        return "0" * length
    
    clean = re.sub(r'[^\d,]', '', str(value))
    clean = clean.replace(',', '')
    
    if len(clean) > length:
        return clean[-length:]
    return clean.zfill(length)

def clean_description(text):
    """Limpa a descrição removendo quebras de linha e espaços duplos"""
    if not text: return "MERCADORIA GERAL"
    return re.sub(r'\s+', ' ', text).strip()

# --- LÓGICA DE EXTRAÇÃO (PARSER) ---

def parse_pdf(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            # Extrai texto mantendo layout visual aproximado
            full_text += page.extract_text() or "" + "\n"

    data = {
        "header": {},
        "itens": []
    }

    # 1. Extração do Cabeçalho
    data["header"]["numero_processo"] = safe_extract(r"PROCESSO\s*#?(\d+)", full_text)
    data["header"]["importador_nome"] = safe_extract(r"IMPORTADOR\s*[:\n,]*[\"']?([\w\s]+)", full_text, default="HAFELE BRASIL LTDA")
    data["header"]["numero_duimp"] = safe_extract(r"Numero\s*[:\n,]*[\"']?([0-9BR]+)", full_text)
    data["header"]["cnpj"] = safe_extract(r"CNPJ\s*[:\n,]*[\"']?([\d\./-]+)", full_text).replace('.', '').replace('/', '').replace('-', '')

    # 2. Extração dos Itens
    # Divide o texto pelos blocos "ITENS DA DUIMP"
    raw_itens = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", full_text)
    
    if len(raw_itens) > 1:
        for i in range(1, len(raw_itens), 2):
            num_item = raw_itens[i]
            content = raw_itens[i+1] # Texto do item
            
            # --- LÓGICA DA DESCRIÇÃO COM PARTNUMBER ---
            
            # 1. Captura a descrição textual pura
            raw_desc = safe_extract(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+(?:CÓDIGO|DESCRICAO|FABRICANTE|VALOR)", content, group=1)
            raw_desc = clean_description(raw_desc)
            
            # 2. Captura o Código Interno / Partnumber
            # O regex busca por "CÓDIGO INTERNO (PARTNUMBER)" ou variações e pega números/pontos/hífens até a quebra de linha
            part_number = safe_extract(r"(?:CÓDIGO INTERNO|PARTNUMBER).*?[:\s]+([0-9A-Z\.\-\s]+?)(?:\n|$|[A-Z])", content, group=1)
            
            # 3. Monta a descrição final: "CODIGO - DESCRIÇÃO"
            if part_number and len(part_number) > 3: # Validação simples para evitar sujeira
                final_description = f"{part_number.strip()} - {raw_desc}"
            else:
                final_description = raw_desc

            item = {
                "numero_adicao": num_item.zfill(3),
                "ncm": safe_extract(r"NCM\s*[:\n,]*[\"']?([\d\.]+)", content, default="00000000").replace(".", ""),
                "valor_unitario": safe_extract(r"Valor Unit Cond Venda\s*[:\n,]*[\"']?([\d\.,]+)", content, default="0"),
                "quantidade": safe_extract(r"Qtde Unid\. Comercial\s*[:\n,]*[\"']?([\d\.,]+)", content, default="0"),
                "descricao": final_description, # Usamos a descrição composta aqui
                "peso_liquido": safe_extract(r"Peso Líquido \(KG\)\s*[:\n,]*[\"']?([\d\.,]+)", content, default="0"),
                "valor_total_moeda": safe_extract(r"Valor Tot\. Cond Venda\s*[:\n,]*[\"']?([\d\.,]+)", content, default="0"),
                
                # Impostos
                "pis_devido": safe_extract(r"PIS.*?Valor Devido.*?([\d\.,]+)", content, default="0"),
                "cofins_devido": safe_extract(r"COFINS.*?Valor Devido.*?([\d\.,]+)", content, default="0"),
            }
            
            data["itens"].append(item)
    else:
        st.warning("Não foi possível separar os itens. Verifique o layout do PDF.")

    return data

# --- LÓGICA DE GERAÇÃO DO XML ---

def create_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")

    # --- Loop Itens ---
    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")
        
        # Estrutura fixa preenchida com zeros
        ET.SubElement(adicao, "cideValorAliquotaEspecifica").text = "0"*11
        ET.SubElement(adicao, "cideValorDevido").text = "0"*15
        ET.SubElement(adicao, "cideValorRecolher").text = "0"*15
        ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
        ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
        
        # COFINS
        ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965"
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_xml_number(item["cofins_devido"], 15)
        
        # Condição de Venda
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
        ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
        ET.SubElement(adicao, "condicaoVendaValorMoeda").text = format_xml_number(item["valor_total_moeda"], 15)
        
        # Dados Mercadoria Globais
        ET.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item["ncm"]
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_xml_number(item["peso_liquido"], 15)
        
        # TAG <mercadoria> (AQUI VAI A DESCRIÇÃO COMPOSTA)
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(mercadoria, "numeroSequencialItem").text = item["numero_adicao"][-2:]
        ET.SubElement(mercadoria, "quantidade").text = format_xml_number(item["quantidade"], 14)
        ET.SubElement(mercadoria, "unidadeMedida").text = "UNIDADE"
        ET.SubElement(mercadoria, "valorUnitario").text = format_xml_number(item["valor_unitario"], 20)
        
        # Identificação
        ET.SubElement(adicao, "numeroAdicao").text = item["numero_adicao"]
        clean_duimp = data["header"]["numero_duimp"].replace("25BR", "")[:10]
        ET.SubElement(adicao, "numeroDUIMP").text = clean_duimp if clean_duimp else "0000000000"
        
        # PIS / Vinculos
        ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_xml_number(item["pis_devido"], 15)
        ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    # --- Dados Globais ---
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
    ET.SubElement(duimp, "importadorNome").text = data["header"]["importador_nome"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj"]
    
    info = ET.SubElement(duimp, "informacaoComplementar")
    info.text = f"PROCESSO: {data['header']['numero_processo']} - IMPORTACAO PROPRIA"
    
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["numero_duimp"]
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)

    return root

# --- INTERFACE STREAMLIT ---

def main():
    st.set_page_config(page_title="Gerador XML DUIMP (Com PartNumber)", layout="wide")
    st.title("Gerador de XML DUIMP v3")
    st.markdown("**Novidade:** Agora concatena 'CÓDIGO INTERNO (PARTNUMBER)' + Descrição.")

    uploaded_file = st.file_uploader("Carregar PDF", type="pdf")

    if uploaded_file:
        if st.button("Gerar XML"):
            with st.spinner("Processando..."):
                try:
                    data = parse_pdf(uploaded_file)
                    
                    if not data["itens"]:
                        st.warning("Nenhum item encontrado. Verifique se o PDF é selecionável.")
                    else:
                        xml_root = create_xml(data)
                        xml_str = ET.tostring(xml_root, 'utf-8')
                        parsed_xml = minidom.parseString(xml_str)
                        pretty_xml = parsed_xml.toprettyxml(indent="    ")
                        
                        st.success(f"XML Gerado! Processo {data['header']['numero_processo']}")
                        st.download_button("Baixar XML", pretty_xml, "M-DUIMP-CONVERTIDO.xml", "text/xml")
                        
                        # Debug: Mostrar como ficou a primeira descrição
                        if len(data['itens']) > 0:
                            st.info(f"Exemplo de Descrição Gerada (Item 1): {data['itens'][0]['descricao']}")

                except Exception as e:
                    st.error(f"Erro: {e}")

if __name__ == "__main__":
    main()
