import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time

# --- UI PROFESSIONAL & CLEAN (MODERN SAAS STYLE) ---
def apply_clean_ui():
    st.markdown("""
    <style>
    /* Reset e Fundo Sóbrio */
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
    }

    /* Container Principal */
    .main-box {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        margin-top: 2rem;
    }

    /* Cabeçalhos */
    h1 {
        color: #0f172a;
        font-weight: 700;
        font-size: 1.75rem !important;
        letter-spacing: -0.025em;
    }

    /* Botão Primário Estilo Profissional */
    .stButton > button {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 6px !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        font-weight: 500 !important;
        transition: background-color 0.2s;
    }
    .stButton > button:hover {
        background-color: #1d4ed8 !important;
    }

    /* Barra de Progresso Discreta */
    .stProgress > div > div > div > div {
        background-color: #2563eb;
    }

    /* Inputs e Upload */
    .stFileUploader {
        border: 1px dashed #cbd5e1;
        border-radius: 8px;
        padding: 10px;
    }

    /* Alertas e Badges */
    .stAlert {
        border-radius: 6px;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE APOIO ---
def clean_val(val):
    if not val: return "0"
    return re.sub(r'[^\d,]', '', str(val)).replace(',', '')

def format_xml_num(val, length):
    return clean_val(val).zfill(length)

def clean_partnumber(text):
    if not text: return ""
    # Remove rótulos preservando o código
    words = ["CÓDIGO", "CODIGO", "INTERNO", "PARTNUMBER", r"\(", r"\)"]
    for w in words:
        text = re.search(f"{w}(.*)", text, re.I).group(1) if re.search(w, text, re.I) else text
    return re.sub(r'\s+', ' ', text).strip().lstrip("- ").strip()

# --- EXTRAÇÃO DO PDF ---
def parse_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    
    data = {"header": {}, "itens": []}
    data["header"]["processo"] = re.search(r"PROCESSO\s*#?(\d+)", text, re.I).group(1) if re.search(r"PROCESSO\s*#?(\d+)", text, re.I) else "N/A"
    data["header"]["duimp"] = re.search(r"Numero\s*[:\n]*\s*([\dBR]+)", text, re.I).group(1) if re.search(r"Numero\s*[:\n]*\s*([\dBR]+)", text, re.I) else "N/A"
    
    parts = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", text)
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            num = parts[i]
            block = parts[i+1]
            
            raw_desc = re.search(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", block, re.S).group(1) if re.search(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", block, re.S) else ""
            raw_pn = re.search(r"PARTNUMBER\)\s*(.*?)\s*(?:PAIS|FABRICANTE|CONDICAO)", block, re.S).group(1) if re.search(r"PARTNUMBER\)\s*(.*?)\s*(?:PAIS|FABRICANTE|CONDICAO)", block, re.S) else ""
            
            pn = clean_partnumber(raw_pn)
            final_desc = f"{pn} - {re.sub(r'\s+', ' ', raw_desc).strip()}" if pn else raw_desc
            
            data["itens"].append({
                "seq": num,
                "descricao": final_desc,
                "ncm": re.search(r"NCM\s*[:\n]*\s*([\d\.]+)", block).group(1).replace(".", "") if re.search(r"NCM\s*[:\n]*\s*([\d\.]+)", block) else "00000000",
                "peso": re.search(r"Peso Líquido \(KG\)\s*[:\n]*\s*([\d\.,]+)", block).group(1) if re.search(r"Peso Líquido \(KG\)\s*[:\n]*\s*([\d\.,]+)", block) else "0",
                "qtd": re.search(r"Qtde Unid\. Comercial\s*[:\n]*\s*([\d\.,]+)", block).group(1) if re.search(r"Qtde Unid\. Comercial\s*[:\n]*\s*([\d\.,]+)", block) else "0",
                "v_unit": re.search(r"Valor Unit Cond Venda\s*[:\n]*\s*([\d\.,]+)", block).group(1) if re.search(r"Valor Unit Cond Venda\s*[:\n]*\s*([\d\.,]+)", block) else "0"
            })
    return data

# --- GERADOR XML (ESTRUTURA HAFELE OBRIGATÓRIA) ---
def generate_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")
    
    for item in data["itens"]:
        ad = ET.SubElement(duimp, "adicao")
        
        # Estrutura obrigatória conforme arquivo enviado
        acr = ET.SubElement(ad, "acrescimo")
        ET.SubElement(acr, "codigoAcrescimo").text = "17"
        ET.SubElement(acr, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        ET.SubElement(acr, "moedaNegociadaCodigo").text = "978"
        ET.SubElement(acr, "valorReais").text = "000000000106601"
        
        # Tags de controle e impostos
        ET.SubElement(ad, "codigoRelacaoCompradorVendedor").text = "3"
        ET.SubElement(ad, "codigoVinculoCompradorVendedor").text = "1"
        ET.SubElement(ad, "cofinsAliquotaAdValorem").text = "00965"
        ET.SubElement(ad, "dadosMercadoriaCodigoNcm").text = item["ncm"]
        ET.SubElement(ad, "dadosMercadoriaPesoLiquido").text = format_xml_num(item["peso"], 15)
        
        # Tag Mercadoria (Onde entra a Descrição + PN)
        merc = ET.SubElement(ad, "mercadoria")
        ET.SubElement(merc, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(merc, "numeroSequencialItem").text = item["seq"].zfill(2)
        ET.SubElement(merc, "quantidade").text = format_xml_num(item["qtd"], 14)
        ET.SubElement(merc, "unidadeMedida").text = "UNIDADE"
        ET.SubElement(merc, "valorUnitario").text = format_xml_num(item["v_unit"], 20)
        
        ET.SubElement(ad, "numeroAdicao").text = item["seq"].zfill(3)
        ET.SubElement(ad, "numeroDUIMP").text = data["header"]["duimp"].replace("25BR", "")[:10]
        ET.SubElement(ad, "pisPasepAliquotaAdValorem").text = "00210"

    ET.SubElement(duimp, "importadorNome").text = "HAFELE BRASIL LTDA"
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)
    ET.SubElement(duimp, "urfDespachoNome").text = "PORTO DE PARANAGUA"
    
    return root

# --- INTERFACE ---
def main():
    st.set_page_config(page_title="Hafele XML Parser", page_icon="📄", layout="centered")
    apply_clean_ui()
    
    st.markdown('<div class="main-box">', unsafe_allow_html=True)
    st.title("Conversor de DUIMP")
    st.markdown("Extração de dados para o layout XML Hafele.")
    
    uploaded_file = st.file_uploader("Selecione o Extrato de Conferência (PDF)", type="pdf")
    
    if uploaded_file:
        if st.button("PROCESSAR ARQUIVO"):
            with st.spinner("Extraindo dados..."):
                progress = st.progress(0)
                for i in range(100):
                    time.sleep(0.005)
                    progress.progress(i + 1)
                
                try:
                    res = parse_pdf(uploaded_file)
                    if res["itens"]:
                        xml_root = generate_xml(res)
                        xml_output = minidom.parseString(ET.tostring(xml_root, 'utf-8')).toprettyxml(indent="    ")
                        
                        st.success("Arquivo processado com sucesso.")
                        
                        col1, col2 = st.columns(2)
                        col1.metric("Total de Itens", len(res["itens"]))
                        col2.metric("Nº Processo", res["header"]["processo"])
                        
                        st.markdown("---")
                        st.markdown("**Validação de Descrição (Item 1):**")
                        st.text(res["itens"][0]["descricao"])
                        
                        st.download_button(
                            label="BAIXAR XML COMPATÍVEL",
                            data=xml_output,
                            file_name=f"DUIMP_{res['header']['processo']}.xml",
                            mime="text/xml"
                        )
                    else:
                        st.error("Nenhum item identificado no PDF.")
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
