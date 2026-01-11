import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time

# --- UI RESPONSIVA E ANIMAÇÕES ---
def apply_ui():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: white;
    }
    .main-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem;
        animation: fadeIn 1s ease-in-out;
    }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #3b82f6, #2563eb) !important;
        border: none; color: white !important;
        transition: 0.3s;
    }
    .stButton > button:hover { transform: scale(1.02); }
    
    /* Progress Bar Animada */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(45deg, rgba(255,255,255,.15) 25%, transparent 25%, transparent 50%, rgba(255,255,255,.15) 50%, rgba(255,255,255,.15) 75%, transparent 75%, transparent);
        background-size: 1rem 1rem;
        animation: progress-bar-stripes 1s linear infinite;
    }
    @keyframes progress-bar-stripes { from { background-position: 1rem 0; } to { background-position: 0 0; } }
    </style>
    """, unsafe_allow_html=True)

# --- LIMPEZA E EXTRAÇÃO ---
def clean_val(val):
    if not val: return "0"
    return re.sub(r'[^\d,]', '', str(val)).replace(',', '')

def format_xml_num(val, length):
    return clean_val(val).zfill(length)

def clean_partnumber(text):
    if not text: return ""
    bad_words = ["CÓDIGO", "CODIGO", "INTERNO", "PARTNUMBER", r"\(", r"\)"]
    for word in bad_words:
        text = re.sub(word, "", text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', text).strip().lstrip("- ").strip()

# --- PARSER DO PDF ---
def parse_pdf(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() or ""
    
    data = {"header": {}, "itens": []}
    # Captura simplificada de cabeçalho
    data["header"]["processo"] = re.search(r"PROCESSO\s*#?(\d+)", full_text, re.I).group(1) if re.search(r"PROCESSO\s*#?(\d+)", full_text, re.I) else "N/A"
    data["header"]["duimp"] = re.search(r"Numero\s*[:\n]*\s*([\dBR]+)", full_text, re.I).group(1) if re.search(r"Numero\s*[:\n]*\s*([\dBR]+)", full_text, re.I) else "N/A"
    
    itens_raw = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", full_text)
    if len(itens_raw) > 1:
        for i in range(1, len(itens_raw), 2):
            content = itens_raw[i+1]
            desc = re.search(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", content, re.S).group(1) if re.search(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", content, re.S) else ""
            raw_pn = re.search(r"PARTNUMBER\)\s*(.*?)\s*(?:PAIS|FABRICANTE|CONDICAO)", content, re.S).group(1) if re.search(r"PARTNUMBER\)\s*(.*?)\s*(?:PAIS|FABRICANTE|CONDICAO)", content, re.S) else ""
            pn = clean_partnumber(raw_pn)
            
            data["itens"].append({
                "seq": itens_raw[i],
                "descricao": f"{pn} - {re.sub(r'\s+', ' ', desc).strip()}" if pn else desc,
                "ncm": re.search(r"NCM\s*[:\n]*\s*([\d\.]+)", content).group(1).replace(".", "") if re.search(r"NCM\s*[:\n]*\s*([\d\.]+)", content) else "00000000",
                "valor_tot": re.search(r"Valor Tot\. Cond Venda\s*[:\n]*\s*([\d\.,]+)", content).group(1) if re.search(r"Valor Tot\. Cond Venda\s*[:\n]*\s*([\d\.,]+)", content) else "0",
                "peso": re.search(r"Peso Líquido \(KG\)\s*[:\n]*\s*([\d\.,]+)", content).group(1) if re.search(r"Peso Líquido \(KG\)\s*[:\n]*\s*([\d\.,]+)", content) else "0",
                "unid_venda": re.search(r"Qtde Unid\. Comercial\s*[:\n]*\s*([\d\.,]+)", content).group(1) if re.search(r"Qtde Unid\. Comercial\s*[:\n]*\s*([\d\.,]+)", content) else "0",
                "unid_valor": re.search(r"Valor Unit Cond Venda\s*[:\n]*\s*([\d\.,]+)", content).group(1) if re.search(r"Valor Unit Cond Venda\s*[:\n]*\s*([\d\.,]+)", content) else "0",
            })
    return data

# --- GERADOR DE XML (LAYOUT PADRÃO HAFELE) ---
def build_hafele_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")
    
    for item in data["itens"]:
        ad = ET.SubElement(duimp, "adicao")
        
        # Estrutura de Acréscimo (exemplo do layout)
        acr = ET.SubElement(ad, "acrescimo")
        ET.SubElement(acr, "codigoAcrescimo").text = "17"
        ET.SubElement(acr, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        ET.SubElement(acr, "moedaNegociadaCodigo").text = "978"
        ET.SubElement(acr, "valorReais").text = "000000000106601"
        
        # Tags Obrigatórias Zeradas ou Fixas conforme layout
        ET.SubElement(ad, "cideValorAliquotaEspecifica").text = "0"*11
        ET.SubElement(ad, "cideValorDevido").text = "0"*15
        ET.SubElement(ad, "cideValorRecolher").text = "0"*15
        ET.SubElement(ad, "codigoRelacaoCompradorVendedor").text = "3"
        ET.SubElement(ad, "codigoVinculoCompradorVendedor").text = "1"
        
        # Cofins / PIS
        ET.SubElement(ad, "cofinsAliquotaAdValorem").text = "00965"
        ET.SubElement(ad, "cofinsAliquotaValorRecolher").text = "0"*15
        
        # Dados Mercadoria
        ET.SubElement(ad, "dadosMercadoriaAplicacao").text = "REVENDA"
        ET.SubElement(ad, "dadosMercadoriaCodigoNcm").text = item["ncm"]
        ET.SubElement(ad, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(ad, "dadosMercadoriaPesoLiquido").text = format_xml_num(item["peso"], 15)
        
        # TAG CRÍTICA: DESCRIÇÃO COM PARTNUMBER
        merc = ET.SubElement(ad, "mercadoria")
        ET.SubElement(merc, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(merc, "numeroSequencialItem").text = item["seq"].zfill(2)
        ET.SubElement(merc, "quantidade").text = format_xml_num(item["unid_venda"], 14)
        ET.SubElement(merc, "unidadeMedida").text = "UNIDADE"
        ET.SubElement(merc, "valorUnitario").text = format_xml_num(item["unid_valor"], 20)
        
        ET.SubElement(ad, "numeroAdicao").text = item["seq"].zfill(3)
        ET.SubElement(ad, "numeroDUIMP").text = data["header"]["duimp"].replace("25BR", "")[:10]
        ET.SubElement(ad, "pisPasepAliquotaAdValorem").text = "00210"

    # Rodapé do DUIMP
    ET.SubElement(duimp, "importadorNome").text = "HAFELE BRASIL LTDA"
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)
    ET.SubElement(duimp, "urfDespachoNome").text = "PORTO DE PARANAGUA"
    
    return root

# --- APP ---
def main():
    st.set_page_config(page_title="Häfele Layout Oficial", layout="centered")
    apply_ui()
    
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.title("📑 DUIMP Official Layout")
    st.write("Gerador seguindo o padrão XML Hafele com PartNumber na descrição.")
    
    file = st.file_uploader("Upload PDF de Conferência", type="pdf")
    
    if file and st.button("PROCESSAR PARA XML"):
        bar = st.progress(0)
        with st.spinner("Sincronizando com Layout Oficial..."):
            for p in range(100):
                time.sleep(0.01); bar.progress(p+1)
            
            res = parse_pdf(file)
            xml_data = build_hafele_xml(res)
            
            xml_str = ET.tostring(xml_data, 'utf-8')
            pretty = minidom.parseString(xml_str).toprettyxml(indent="    ")
            
            st.balloons()
            st.success("XML gerado seguindo o arquivo padrão!")
            st.markdown(f"**Exemplo de Descrição:** `{res['itens'][0]['descricao']}`")
            
            st.download_button("📥 BAIXAR XML OFICIAL", pretty, f"DUIMP_{res['header']['processo']}.xml", "text/xml")
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
