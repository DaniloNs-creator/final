import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- CSS CRIATIVO E ANIMAÇÕES ---
def apply_custom_styles():
    st.markdown("""
    <style>
    /* Fundo animado com gradiente */
    .stApp {
        background: linear-gradient(-45deg, #f3f4f7, #e2e8f0, #ffffff);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }

    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Animação de entrada (Fade-in) */
    .main-card {
        animation: fadeIn 1.2s ease-out;
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Efeito flutuante no botão de download */
    .stDownloadButton button {
        transition: all 0.3s ease;
        border: none;
        background-color: #4CAF50 !important;
        color: white !important;
    }
    .stDownloadButton button:hover {
        transform: scale(1.05);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }

    /* Estilização de código para destaque */
    code {
        color: #e83e8c !important;
        background: #f8f9fa !important;
        padding: 5px;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

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
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(group).strip()
    except:
        pass
    return ""

def clean_partnumber(text):
    if not text: return ""
    # Remove termos indesejados e escapa parênteses para o regex
    for word in ["CÓDIGO", "CODIGO", "INTERNO", "PARTNUMBER", "PRODUTO"]:
        text = re.sub(word, "", text, flags=re.IGNORECASE)
    # Remove caracteres literais de parênteses e limpa espaços
    text = text.replace("(", "").replace(")", "")
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lstrip("- ").strip()

# --- PARSER ---
def parse_pdf(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() or "" + "\n"

    data = {"header": {}, "itens": []}
    data["header"]["processo"] = safe_extract(r"PROCESSO\s*#?(\d+)", full_text)
    data["header"]["duimp"] = safe_extract(r"Numero\s*[:\n]*\s*([\dBR]+)", full_text)
    data["header"]["cnpj"] = safe_extract(r"CNPJ\s*[:\n]*\s*([\d\./-]+)", full_text).replace('.', '').replace('/', '').replace('-', '')
    data["header"]["importador"] = "HAFELE BRASIL LTDA"

    raw_itens = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", full_text)

    if len(raw_itens) > 1:
        for i in range(1, len(raw_itens), 2):
            num_item = raw_itens[i]
            content = raw_itens[i+1]

            # Descrição e Código Interno
            desc_pura = safe_extract(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", content)
            desc_pura = clean_text(desc_pura)
            
            raw_code = safe_extract(r"PARTNUMBER\)\s*(.*?)\s*(?:PAIS|FABRICANTE|CONDICAO|VALOR|NCM)", content)
            codigo_limpo = clean_partnumber(raw_code)

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
        # Estrutura padrão XML
        for tag in ["cideValorAliquotaEspecifica", "cideValorDevido", "cideValorRecolher"]:
            ET.SubElement(adicao, tag).text = "0"*11 if "Aliquota" in tag else "0"*15
        
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
        
        merc = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(merc, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(merc, "numeroSequencialItem").text = item["numero_adicao"][-2:]
        ET.SubElement(merc, "quantidade").text = format_xml_number(item["quantidade"], 14)
        ET.SubElement(merc, "unidadeMedida").text = "UNIDADE"
        ET.SubElement(merc, "valorUnitario").text = format_xml_number(item["valor_unitario"], 20)
        
        ET.SubElement(adicao, "numeroAdicao").text = item["numero_adicao"]
        ET.SubElement(adicao, "numeroDUIMP").text = data["header"]["duimp"].replace("25BR", "")[:10]
        ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_xml_number(item["pis"], 15)
        ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
    ET.SubElement(duimp, "importadorNome").text = data["header"]["importador"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj"]
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["duimp"]
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)
    return root

# --- INTERFACE ---
def main():
    st.set_page_config(page_title="Häfele XML Converter", page_icon="📦", layout="centered")
    apply_custom_styles()

    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.title("📦 Häfele XML Converter")
    st.write("Converta seu PDF de conferência em XML para o Siscomex com um clique.")
    
    file = st.file_uploader("Arraste seu PDF aqui", type="pdf")
    
    if file:
        if st.button("🚀 Iniciar Processamento"):
            try:
                res = parse_pdf(file)
                if res["itens"]:
                    xml_root = create_xml(res)
                    xml_str = ET.tostring(xml_root, 'utf-8')
                    pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
                    
                    st.divider()
                    st.balloons()
                    st.success(f"Sucesso! Processo {res['header']['processo']} concluído.")
                    
                    # Exibição do exemplo limpo
                    st.markdown("### 🔍 Validação da Descrição")
                    st.info(f"**Item 1:** {res['itens'][0]['descricao']}")
                    
                    st.download_button(
                        label="📥 BAIXAR ARQUIVO XML",
                        data=pretty,
                        file_name=f"DUIMP_{res['header']['processo']}.xml",
                        mime="text/xml"
                    )
                else:
                    st.error("Nenhum item detectado. O PDF é original de texto?")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
