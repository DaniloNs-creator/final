import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time

# --- DESIGN RESPONSIVO E ANIMAÇÕES AVANÇADAS ---
def apply_advanced_ui():
    st.markdown("""
    <style>
    /* Importação de fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Fundo com Gradiente Dinâmico */
    .stApp {
        background: radial-gradient(circle at top right, #6d5dfc, #f0f2f6 40%);
        background-attachment: fixed;
    }

    /* Container Principal Responsivo (Glassmorphism) */
    .main-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 2rem;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        margin-bottom: 2rem;
        animation: slideUp 0.8s ease-out;
    }

    /* Animação de Carregamento (Barra de Progresso) */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #6d5dfc, #a499ff);
        animation: progressFlow 2s linear infinite;
        background-size: 200% 100%;
    }

    @keyframes progressFlow {
        0% { background-position: 100% 0; }
        100% { background-position: 0% 0; }
    }

    @keyframes slideUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Estilo para Celular (Responsividade) */
    @media (max-width: 640px) {
        .main-card {
            padding: 1rem;
            margin: 0.5rem;
        }
        h1 { font-size: 1.5rem !important; }
    }

    /* Botão Vibrante */
    .stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background: #6d5dfc !important;
        color: white !important;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(109, 93, 252, 0.4);
    }

    /* Badge de Sucesso Animada */
    .success-badge {
        display: inline-block;
        padding: 5px 15px;
        background: #d4edda;
        color: #155724;
        border-radius: 20px;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE EXTRAÇÃO (MESMA ANTERIOR, ESTABILIZADA) ---
def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()

def format_xml_number(value, length=15):
    clean = re.sub(r'[^\d,]', '', str(value)).replace(',', '')
    return clean.zfill(length)

def clean_partnumber(text):
    if not text: return ""
    for word in ["CÓDIGO", "CODIGO", "INTERNO", "PARTNUMBER", "PRODUTO"]:
        text = re.sub(word, "", text, flags=re.IGNORECASE)
    text = text.replace("(", "").replace(")", "")
    return re.sub(r'\s+', ' ', text).strip().lstrip("- ").strip()

def parse_pdf(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() or "" + "\n"

    data = {"header": {}, "itens": []}
    data["header"]["processo"] = re.search(r"PROCESSO\s*#?(\d+)", full_text, re.I).group(1) if re.search(r"PROCESSO\s*#?(\d+)", full_text, re.I) else "00000"
    data["header"]["duimp"] = re.search(r"Numero\s*[:\n]*\s*([\dBR]+)", full_text, re.I).group(1) if re.search(r"Numero\s*[:\n]*\s*([\dBR]+)", full_text, re.I) else "00000"
    data["header"]["cnpj"] = "02473058000188"
    data["header"]["importador"] = "HAFELE BRASIL LTDA"

    raw_itens = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", full_text)

    if len(raw_itens) > 1:
        for i in range(1, len(raw_itens), 2):
            num_item = raw_itens[i]
            content = raw_itens[i+1]

            desc_pura = clean_text(re.search(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", content, re.S).group(1)) if re.search(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", content, re.S) else ""
            raw_code = re.search(r"PARTNUMBER\)\s*(.*?)\s*(?:PAIS|FABRICANTE|CONDICAO)", content, re.S).group(1) if re.search(r"PARTNUMBER\)\s*(.*?)\s*(?:PAIS|FABRICANTE|CONDICAO)", content, re.S) else ""
            codigo_limpo = clean_partnumber(raw_code)

            item = {
                "numero_adicao": num_item.zfill(3),
                "descricao": f"{codigo_limpo} - {desc_pura}" if codigo_limpo else desc_pura,
                "ncm": re.search(r"NCM\s*[:\n]*\s*([\d\.]+)", content).group(1).replace(".", "") if re.search(r"NCM\s*[:\n]*\s*([\d\.]+)", content) else "00000000",
                "quantidade": re.search(r"Qtde Unid\. Comercial\s*[:\n]*\s*([\d\.,]+)", content).group(1) if re.search(r"Qtde Unid\. Comercial\s*[:\n]*\s*([\d\.,]+)", content) else "0",
                "valor_unitario": re.search(r"Valor Unit Cond Venda\s*[:\n]*\s*([\d\.,]+)", content).group(1) if re.search(r"Valor Unit Cond Venda\s*[:\n]*\s*([\d\.,]+)", content) else "0",
                "valor_total": re.search(r"Valor Tot\. Cond Venda\s*[:\n]*\s*([\d\.,]+)", content).group(1) if re.search(r"Valor Tot\. Cond Venda\s*[:\n]*\s*([\d\.,]+)", content) else "0",
                "peso_liquido": re.search(r"Peso Líquido \(KG\)\s*[:\n]*\s*([\d\.,]+)", content).group(1) if re.search(r"Peso Líquido \(KG\)\s*[:\n]*\s*([\d\.,]+)", content) else "0",
                "pis": re.search(r"PIS.*?Valor Devido.*?([\d\.,]+)", content, re.S).group(1) if re.search(r"PIS.*?Valor Devido.*?([\d\.,]+)", content, re.S) else "0",
                "cofins": re.search(r"COFINS.*?Valor Devido.*?([\d\.,]+)", content, re.S).group(1) if re.search(r"COFINS.*?Valor Devido.*?([\d\.,]+)", content, re.S) else "0",
            }
            data["itens"].append(item)
    return data

def create_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")
    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")
        # Preenchimento automático de campos XML
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_xml_number(item["cofins"])
        ET.SubElement(adicao, "condicaoVendaValorMoeda").text = format_xml_number(item["valor_total"])
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item["ncm"]
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_xml_number(item["peso_liquido"])
        merc = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(merc, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(merc, "quantidade").text = format_xml_number(item["quantidade"], 14)
        ET.SubElement(merc, "valorUnitario").text = format_xml_number(item["valor_unitario"], 20)
        ET.SubElement(adicao, "numeroAdicao").text = item["numero_adicao"]
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_xml_number(item["pis"])
    
    ET.SubElement(duimp, "importadorNome").text = data["header"]["importador"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj"]
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)
    return root

# --- INTERFACE PRINCIPAL ---
def main():
    st.set_page_config(page_title="Siscomex PRO", page_icon="⚡", layout="centered")
    apply_advanced_ui()

    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<h1 style="text-align: center; color: #1e293b;">⚡ Siscomex XML Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #64748b;">Processamento inteligente de DUIMP para Häfele Brasil</p>', unsafe_allow_html=True)
    
    file = st.file_uploader("", type="pdf")
    
    if file:
        if st.button("Gerar XML Agora"):
            # Animação de processamento
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
                if i < 30: status_text.text("📑 Analisando estrutura do PDF...")
                elif i < 70: status_text.text("🔍 Extraindo PartNumbers e itens...")
                else: status_text.text("🛠️ Montando árvore XML...")

            try:
                res = parse_pdf(file)
                if res["itens"]:
                    xml_root = create_xml(res)
                    xml_str = ET.tostring(xml_root, 'utf-8')
                    pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
                    
                    status_text.markdown('<span class="success-badge">✅ Processamento Concluído!</span>', unsafe_allow_html=True)
                    st.balloons()
                    
                    # Layout em colunas para os resultados
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Itens Processados", len(res["itens"]))
                    with col2:
                        st.metric("Processo", res["header"]["processo"])

                    st.markdown("### 📄 Prévia da Descrição (Item 1)")
                    st.code(res["itens"][0]["descricao"], language="text")

                    st.download_button(
                        label="💾 BAIXAR ARQUIVO XML",
                        data=pretty,
                        file_name=f"DUIMP_{res['header']['processo']}.xml",
                        mime="text/xml"
                    )
                else:
                    st.error("Erro: Nenhum dado capturado. Verifique o PDF.")
            except Exception as e:
                st.error(f"Erro crítico: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
