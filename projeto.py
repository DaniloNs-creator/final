import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- FUNÇÕES DE LIMPEZA E FORMATAÇÃO ---

def clean_text(text):
    """Remove quebras de linha e espaços duplos."""
    if not text: return ""
    text = text.replace('\n', ' ')
    return re.sub(r'\s+', ' ', text).strip()

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

def safe_extract(pattern, text, group=1):
    """Extrai texto via Regex com segurança."""
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(group).strip()
    except:
        pass
    return ""

def clean_partnumber(text):
    """
    Remove explicitamente textos indesejados que possam ter vindo na captura,
    deixando apenas o código numérico/hífen.
    """
    if not text: return ""
    # Remove palavras chave que o usuário não quer
    bad_words = ["CÓDIGO", "CODIGO", "INTERNO", "PARTNUMBER", "(", ")", "PRODUTO"]
    for word in bad_words:
        text = re.sub(word, "", text, flags=re.IGNORECASE)
    
    # Remove espaços duplos e traços soltos no início
    text = re.sub(r'\s+', ' ', text).strip()
    if text.startswith("-"): text = text[1:].strip()
    
    return text

# --- LÓGICA DE EXTRAÇÃO (PARSER) ---

def parse_pdf(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() or "" + "\n"

    data = {
        "header": {},
        "itens": []
    }

    # 1. Cabeçalho
    data["header"]["processo"] = safe_extract(r"PROCESSO\s*#?(\d+)", full_text)
    data["header"]["importador"] = safe_extract(r"IMPORTADOR\s*[:\n]*\s*([A-Z\s\.]+)(?:CNPJ|$)", full_text) or "HAFELE BRASIL LTDA"
    data["header"]["cnpj"] = safe_extract(r"CNPJ\s*[:\n]*\s*([\d\./-]+)", full_text).replace('.', '').replace('/', '').replace('-', '')
    data["header"]["duimp"] = safe_extract(r"Numero\s*[:\n]*\s*([\dBR]+)", full_text)

    # 2. Separação dos Itens
    raw_itens = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", full_text)

    if len(raw_itens) > 1:
        for i in range(1, len(raw_itens), 2):
            num_item = raw_itens[i]
            content = raw_itens[i+1]

            # --- CORREÇÃO DA DESCRIÇÃO ---
            
            # 1. Captura a Descrição do Produto
            desc_pura = safe_extract(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+(?:CÓDIGO|CODIGO)", content)
            desc_pura = clean_text(desc_pura)

            # 2. Captura o Código (PartNumber) de forma ampla
            # Captura tudo após "PARTNUMBER)" até o próximo rótulo
            raw_code = safe_extract(r"(?:PARTNUMBER\)|CÓDIGO INTERNO)\s+(.*?)\s+(?:PAIS|FABRICANTE|CONDICAO|VALOR|NCM|UNIDADE)", content)
            
            # 3. LIMPEZA EXTRA: Remove texto "Código interno" se tiver sido capturado
            codigo_limpo = clean_partnumber(raw_code)

            # 4. Concatenação: "24980198 - DESCRIÇÃO"
            if codigo_limpo:
                descricao_final = f"{codigo_limpo} - {desc_pura}"
            else:
                descricao_final = desc_pura

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

# --- GERAÇÃO DO XML ---

def create_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")

    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")

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
        
        # --- TAG <mercadoria> COM FORMATO LIMPO ---
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(mercadoria, "numeroSequencialItem").text = item["numero_adicao"][-2:]
        ET.SubElement(mercadoria, "quantidade").text = format_xml_number(item["quantidade"], 14)
        ET.SubElement(mercadoria, "unidadeMedida").text = "UNIDADE"
        ET.SubElement(mercadoria, "valorUnitario").text = format_xml_number(item["valor_unitario"], 20)
        
        ET.SubElement(adicao, "numeroAdicao").text = item["numero_adicao"]
        duimp_clean = data["header"]["duimp"].replace("25BR", "")[:10]
        ET.SubElement(adicao, "numeroDUIMP").text = duimp_clean if duimp_clean else "0000000000"
        
        ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_xml_number(item["pis"], 15)
        ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
    ET.SubElement(duimp, "importadorNome").text = data["header"]["importador"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj"]
    
    info = ET.SubElement(duimp, "informacaoComplementar")
    info.text = f"PROCESSO: {data['header']['processo']} - IMPORTACAO PROPRIA"
    
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["duimp"]
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)

    return root

# --- INTERFACE ---

def main():
    st.set_page_config(page_title="Gerador XML DUIMP (Limpo)", layout="wide")
    st.title("Gerador de XML DUIMP (Código + Descrição Limpa)")
    st.markdown("Extrai: **24980198 - DESCRIÇÃO** (Remove 'Código interno')")

    uploaded_file = st.file_uploader("Carregar PDF", type="pdf")

    if uploaded_file:
        if st.button("Gerar XML"):
            with st.spinner("Processando..."):
                try:
                    data = parse_pdf(uploaded_file)
                    
                    if not data["itens"]:
                        st.error("Nenhum item encontrado.")
                    else:
                        xml_root = create_xml(data)
                        xml_str = ET.tostring(xml_root, 'utf-8')
                        parsed = minidom.parseString(xml_str)
                        pretty_xml = parsed.toprettyxml(indent="    ")

                        st.success("XML Gerado!")
                        
                        # Mostra exemplo do Item 1 para validação
                        if len(data["itens"]) > 0:
                            st.markdown(f"**Exemplo Item 1:** `{data['itens'][0]['descricao']}`")
                        
                        # Mostra exemplo do Item 74 (se houver)
                        if len(data["itens"]) >= 74:
                            st.markdown(f"**Exemplo Item 74:** `{data['itens'][73]['descricao']}`")

                        st.download_button(
                            label="📥 Baixar XML",
                            data=pretty_xml,
                            file_name=f"DUIMP_FINAL_{data['header']['processo']}.xml",
                            mime="text/xml"
                        )
                except Exception as e:
                    st.error(f"Erro: {e}")

if __name__ == "__main__":
    main()
