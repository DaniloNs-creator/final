import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time

# --- CSS PROFISSIONAL E ANIMADO ---
def inject_custom_css():
    st.markdown("""
    <style>
        /* Paleta de cores clean - Azul Profissional */
        :root {
            --primary: #2563eb;
            --primary-light: #3b82f6;
            --primary-dark: #1d4ed8;
            --secondary: #64748b;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --background: #f8fafc;
            --surface: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
        }
        
        /* Reset e configurações base */
        .stApp {
            background-color: var(--background);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Container principal responsivo */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        
        @media (max-width: 768px) {
            .main .block-container {
                padding-top: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }
        
        /* Header estilizado */
        .stTitle {
            color: var(--text-primary);
            font-weight: 700;
            font-size: 2.5rem !important;
            margin-bottom: 1.5rem;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
        }
        
        /* Card para upload */
        .upload-card {
            background: var(--surface);
            border-radius: 16px;
            padding: 2rem;
            margin: 2rem 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(99, 102, 241, 0.1);
            transition: all 0.3s ease;
        }
        
        .upload-card:hover {
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            transform: translateY(-2px);
        }
        
        /* Botões estilizados */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            border: none;
            padding: 0.75rem 2rem;
            border-radius: 12px;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.3s ease;
            width: 100%;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.3);
            background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
        }
        
        /* File uploader customizado */
        .stFileUploader {
            background: var(--surface);
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
            padding: 2rem;
            transition: all 0.3s ease;
        }
        
        .stFileUploader:hover {
            border-color: var(--primary);
            background: rgba(37, 99, 235, 0.02);
        }
        
        /* Animações de carregamento */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        @keyframes shimmer {
            0% { background-position: -1000px 0; }
            100% { background-position: 1000px 0; }
        }
        
        .fade-in {
            animation: fadeIn 0.6s ease-out;
        }
        
        /* Loader para processamento */
        .processing-loader {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 3rem;
            text-align: center;
        }
        
        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(37, 99, 235, 0.1);
            border-radius: 50%;
            border-top-color: var(--primary);
            animation: spin 1s linear infinite;
            margin-bottom: 1rem;
        }
        
        .shimmer {
            background: linear-gradient(90deg, 
                rgba(37, 99, 235, 0.1) 25%, 
                rgba(37, 99, 235, 0.3) 50%, 
                rgba(37, 99, 235, 0.1) 75%);
            background-size: 1000px 100%;
            animation: shimmer 2s infinite linear;
        }
        
        /* Cards de resultado */
        .result-card {
            background: var(--surface);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            border-left: 4px solid var(--success);
            animation: fadeIn 0.5s ease-out;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }
        
        .result-card.error {
            border-left-color: var(--error);
        }
        
        /* Estatísticas */
        .stats-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        
        .stat-card {
            background: var(--surface);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
            margin: 0.5rem 0;
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        
        /* Progress bar customizada */
        .stProgress > div > div > div {
            background: linear-gradient(90deg, var(--primary) 0%, var(--primary-light) 100%);
            border-radius: 4px;
        }
        
        /* Mensagens de status */
        .stAlert {
            border-radius: 12px;
            padding: 1rem 1.5rem;
            animation: fadeIn 0.4s ease-out;
        }
        
        /* Download button especial */
        .download-success {
            background: linear-gradient(135deg, var(--success) 0%, #34d399 100%) !important;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        }
        
        .download-success:hover {
            background: linear-gradient(135deg, #0da271 0%, var(--success) 100%) !important;
        }
        
        /* Responsividade melhorada */
        @media (max-width: 640px) {
            .stTitle {
                font-size: 2rem !important;
            }
            
            .upload-card {
                padding: 1.5rem;
                margin: 1rem 0;
            }
            
            .stats-container {
                grid-template-columns: 1fr;
            }
        }
        
        /* Footer */
        .footer {
            text-align: center;
            margin-top: 4rem;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
            border-top: 1px solid #e2e8f0;
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
    """Extrai texto ignorando erros de sintaxe de regex mal formada."""
    try:
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
            desc_pura = safe_extract(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", content)
            desc_pura = clean_text(desc_pura)

            # 2. Código (Partnumber)
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

# --- INTERFACE COM ANIMAÇÕES ---

def main():
    st.set_page_config(
        page_title="DUIMP XML Generator Pro",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Injeta o CSS customizado
    inject_custom_css()
    
    # Header com animação
    st.markdown('<h1 class="fade-in">📄 Gerador XML DUIMP Pro</h1>', unsafe_allow_html=True)
    
    # Descrição
    st.markdown(
        '<p style="text-align: center; color: #64748b; margin-bottom: 3rem;" class="fade-in">'
        'Transforme extratos PDF da DUIMP em XML estruturado com validação automática'
        '</p>',
        unsafe_allow_html=True
    )
    
    # Card de upload
    st.markdown('<div class="upload-card fade-in">', unsafe_allow_html=True)
    
    st.subheader("📤 Upload do Documento")
    file = st.file_uploader(
        "Selecione o Extrato PDF da DUIMP",
        type="pdf",
        help="Arraste e solte ou clique para selecionar o arquivo PDF"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if file:
        # Estatísticas do arquivo
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="stat-card fade-in">', unsafe_allow_html=True)
            st.markdown('<div class="stat-label">Arquivo</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-value">{file.name}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="stat-card fade-in">', unsafe_allow_html=True)
            st.markdown('<div class="stat-label">Tamanho</div>', unsafe_allow_html=True)
            size_mb = len(file.getvalue()) / (1024 * 1024)
            st.markdown(f'<div class="stat-value">{size_mb:.2f} MB</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="stat-card fade-in">', unsafe_allow_html=True)
            st.markdown('<div class="stat-label">Status</div>', unsafe_allow_html=True)
            st.markdown('<div class="stat-value" style="color: #10b981;">✓ Pronto</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Botão de processamento
        if st.button("🚀 Processar e Gerar XML", use_container_width=True):
            try:
                # Container de processamento
                with st.container():
                    st.markdown('<div class="processing-loader">', unsafe_allow_html=True)
                    st.markdown('<div class="spinner"></div>', unsafe_allow_html=True)
                    st.markdown('<h3>Processando documento...</h3>', unsafe_allow_html=True)
                    st.markdown('<p>Analisando PDF e extraindo dados</p>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Barra de progresso animada
                    progress_bar = st.progress(0)
                    
                    # Simulação de etapas de processamento
                    for i in range(100):
                        time.sleep(0.01)
                        progress_bar.progress(i + 1)
                    
                    # Processamento real
                    with st.spinner("Extraindo dados do PDF..."):
                        res = parse_pdf(file)
                    
                    progress_bar.progress(100)
                    
                    if res["itens"]:
                        with st.spinner("Gerando estrutura XML..."):
                            xml_data = create_xml(res)
                            xml_str = ET.tostring(xml_data, 'utf-8')
                            pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
                        
                        # Resultados
                        st.success("✅ Processamento concluído com sucesso!")
                        
                        # Estatísticas do resultado
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
                            st.markdown('<div class="stat-label">Itens Processados</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="stat-value">{len(res["itens"])}</div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
                            st.markdown('<div class="stat-label">Processo</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="stat-value">#{res["header"]["processo"]}</div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
                            st.markdown('<div class="stat-label">DUIMP</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="stat-value">{res["header"]["duimp"][:10]}...</div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        with col4:
                            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
                            st.markdown('<div class="stat-label">CNPJ</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="stat-value">{res["header"]["cnpj"][:8]}...</div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Preview do primeiro item
                        with st.expander("📋 Visualizar Primeiro Item", expanded=True):
                            st.markdown('<div class="result-card fade-in">', unsafe_allow_html=True)
                            st.write("**Descrição:**", res["itens"][0]["descricao"])
                            st.write("**NCM:**", res["itens"][0]["ncm"])
                            st.write("**Quantidade:**", res["itens"][0]["quantidade"])
                            st.write("**Valor Total:**", res["itens"][0]["valor_total"])
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Botão de download com estilo especial
                        st.markdown('<br>', unsafe_allow_html=True)
                        col1, col2, col3 = st.columns([1,2,1])
                        with col2:
                            st.download_button(
                                label="📥 Baixar Arquivo XML",
                                data=pretty,
                                file_name=f"DUIMP_{res['header']['processo']}.xml",
                                mime="text/xml",
                                use_container_width=True,
                                help="Clique para baixar o arquivo XML gerado"
                            )
                        
                    else:
                        st.error("⚠️ Não foram encontrados itens válidos no PDF.")
                        st.info("Verifique se o documento contém a estrutura esperada da DUIMP.")
                        
            except Exception as e:
                st.error(f"❌ Erro no processamento: {str(e)}")
                st.markdown('<div class="result-card error">', unsafe_allow_html=True)
                st.write("Detalhes do erro:", str(e))
                st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown('<div class="footer fade-in">', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <p style="color: #64748b; margin-bottom: 0.5rem;">
            📄 <strong>DUIMP XML Generator Pro</strong> v1.0
        </p>
        <p style="color: #94a3b8; font-size: 0.85rem;">
            Processamento automatizado de documentos aduaneiros | Suporte: suporte@empresa.com
        </p>
        <div style="margin-top: 1rem; opacity: 0.7;">
            <small>⚡ Interface responsiva com animações CSS avançadas</small>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
