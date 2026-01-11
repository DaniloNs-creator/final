import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time

# --- CSS PROFISSIONAL COM ANIMAÇÕES ---
def apply_custom_styles():
    st.markdown("""
    <style>
    /* Fundo profissional com gradiente suave */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f2 100%);
        min-height: 100vh;
    }
    
    /* Container principal com sombra e bordas suaves */
    .main-container {
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        padding: 30px;
        margin: 20px auto;
        max-width: 1000px;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    /* Animação de entrada suave */
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .slide-up {
        animation: slideUp 0.6s ease-out;
    }
    
    /* Animação de pulse para elementos importantes */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
    
    /* Header estilizado */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z' fill='%239C92AC' fill-opacity='0.1' fill-rule='evenodd'/%3E%3C/svg%3E");
        opacity: 0.3;
    }
    
    /* Botões modernos */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 50px;
        font-weight: 600;
        font-size: 16px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:active {
        transform: translateY(-1px);
    }
    
    /* Botão de download especial */
    .download-btn {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%) !important;
    }
    
    /* Uploader estilizado */
    .uploader-box {
        border: 2px dashed #667eea;
        border-radius: 15px;
        padding: 40px;
        text-align: center;
        background: rgba(102, 126, 234, 0.05);
        margin: 20px 0;
        transition: all 0.3s ease;
    }
    
    .uploader-box:hover {
        background: rgba(102, 126, 234, 0.1);
        border-color: #764ba2;
    }
    
    /* Cards de informação */
    .info-card {
        background: linear-gradient(135deg, #f8f9ff 0%, #f1f3ff 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 3px 10px rgba(0,0,0,0.05);
    }
    
    /* Animações de loading */
    .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px;
        background: rgba(255,255,255,0.9);
        border-radius: 15px;
        margin: 20px 0;
    }
    
    .spinner {
        width: 70px;
        height: 70px;
        border: 5px solid #f3f3f3;
        border-top: 5px solid #667eea;
        border-radius: 50%;
        animation: spin 1.5s linear infinite;
        margin-bottom: 20px;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .loading-text {
        font-size: 18px;
        color: #333;
        font-weight: 500;
        margin-bottom: 10px;
    }
    
    .loading-dots {
        display: flex;
        gap: 8px;
    }
    
    .loading-dots span {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #667eea;
        animation: bounce 1.4s infinite ease-in-out both;
    }
    
    .loading-dots span:nth-child(1) { animation-delay: -0.32s; }
    .loading-dots span:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes bounce {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
    }
    
    /* Progress bar animada */
    .progress-container {
        width: 100%;
        height: 6px;
        background: #e0e0e0;
        border-radius: 3px;
        margin: 20px 0;
        overflow: hidden;
    }
    
    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #667eea, #764ba2);
        width: 0%;
        animation: progressAnimation 2s ease-in-out infinite;
        border-radius: 3px;
    }
    
    @keyframes progressAnimation {
        0% { width: 0%; transform: translateX(-100%); }
        50% { width: 100%; transform: translateX(0%); }
        100% { width: 0%; transform: translateX(100%); }
    }
    
    /* Badges e tags */
    .badge {
        display: inline-block;
        padding: 5px 12px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin: 0 5px;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .main-container {
            padding: 20px;
            margin: 10px;
            border-radius: 15px;
        }
        
        .main-header {
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .uploader-box {
            padding: 20px;
        }
        
        .stButton > button {
            padding: 10px 20px;
            font-size: 14px;
        }
    }
    
    /* Animações de sucesso */
    @keyframes successAnimation {
        0% { transform: scale(0.5); opacity: 0; }
        70% { transform: scale(1.1); }
        100% { transform: scale(1); opacity: 1; }
    }
    
    .success-animation {
        animation: successAnimation 0.6s ease-out;
    }
    
    /* Tooltips e hints */
    .hint {
        background: #e8f4fd;
        border-left: 4px solid #2196F3;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 10px 0;
        font-size: 14px;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #e0e0e0;
        color: #666;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ANIMAÇÃO DE PROCESSAMENTO ---
def show_processing_animation(message="Processando PDF..."):
    """Mostra uma animação de processamento elegante"""
    html = f"""
    <div class="loading-container slide-up">
        <div class="spinner"></div>
        <div class="loading-text">{message}</div>
        <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <div class="progress-container">
            <div class="progress-bar"></div>
        </div>
        <div style="margin-top: 20px; color: #666; font-size: 14px;">
            Isso pode levar alguns segundos...
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

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
    st.set_page_config(
        page_title="Häfele XML Converter",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    apply_custom_styles()

    # Container principal
    st.markdown('<div class="main-container slide-up">', unsafe_allow_html=True)
    
    # Header com gradiente
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem;">📦 Häfele XML Converter</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 1.1rem;">
            Converta PDFs de conferência em XML para o Siscomex com precisão e velocidade
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Informações importantes
    with st.expander("ℹ️ Como usar"):
        st.markdown("""
        <div class="hint">
        1. **Faça upload** do PDF da DUIMP (Documento Único de Importação)<br>
        2. **Clique em processar** para converter automaticamente<br>
        3. **Baixe o XML** gerado pronto para importação<br>
        4. **Verifique** os dados antes de usar no Siscomex
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="uploader-box">', unsafe_allow_html=True)
        file = st.file_uploader(
            "**📤 ARRASTE OU SELECIONE O PDF**",
            type="pdf",
            help="Selecione o arquivo PDF da conferência da DUIMP"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-card">
            <h4 style="margin-top: 0;">📊 Dados Extraídos</h4>
            <p><strong>• Número do Processo</strong><br>
            <strong>• CNPJ do Importador</strong><br>
            <strong>• Número da DUIMP</strong><br>
            <strong>• Itens da Declaração</strong><br>
            <strong>• Valores e Impostos</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    if file:
        # Mostra informações do arquivo
        st.markdown(f"""
        <div class="info-card">
            <h4 style="margin-top: 0;">📄 Arquivo Carregado</h4>
            <p><strong>Nome:</strong> {file.name}<br>
            <strong>Tamanho:</strong> {file.size / 1024:.1f} KB<br>
            <strong>Tipo:</strong> PDF Document</p>
            <span class="badge">Pronto para processar</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 INICIAR CONVERSÃO PARA XML", key="process"):
            try:
                # Mostra animação de processamento
                with st.spinner(""):
                    show_processing_animation("Analisando estrutura do PDF...")
                    time.sleep(1)  # Simula processamento
                    
                    show_processing_animation("Extraindo dados da DUIMP...")
                    res = parse_pdf(file)
                    
                    show_processing_animation("Gerando estrutura XML...")
                    if res["itens"]:
                        xml_root = create_xml(res)
                        xml_str = ET.tostring(xml_root, 'utf-8')
                        pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
                        
                        # Limpa a animação
                        st.empty()
                        
                        # Mostra resultados com animação
                        st.markdown('<div class="success-animation">', unsafe_allow_html=True)
                        
                        st.balloons()
                        
                        # Cards de resultados
                        col_s1, col_s2, col_s3 = st.columns(3)
                        
                        with col_s1:
                            st.markdown("""
                            <div class="info-card" style="text-align: center;">
                                <h3 style="color: #667eea;">✅</h3>
                                <h4>Processo</h4>
                                <p style="font-size: 1.2rem; font-weight: bold;">{}</p>
                            </div>
                            """.format(res['header']['processo'] or "N/A"), unsafe_allow_html=True)
                        
                        with col_s2:
                            st.markdown("""
                            <div class="info-card" style="text-align: center;">
                                <h3 style="color: #4CAF50;">📦</h3>
                                <h4>Itens</h4>
                                <p style="font-size: 1.2rem; font-weight: bold;">{} itens</p>
                            </div>
                            """.format(len(res['itens'])), unsafe_allow_html=True)
                        
                        with col_s3:
                            st.markdown("""
                            <div class="info-card" style="text-align: center;">
                                <h3 style="color: #764ba2;">⚡</h3>
                                <h4>Status</h4>
                                <p style="font-size: 1.2rem; font-weight: bold;">Concluído</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Exemplo de dados
                        st.markdown("### 🔍 Validação dos Dados Extraídos")
                        
                        tab1, tab2, tab3 = st.tabs(["📝 Descrição", "📊 Dados", "📄 XML Preview"])
                        
                        with tab1:
                            if res['itens']:
                                st.info(f"**Item 1 - Descrição:**\n\n{res['itens'][0]['descricao']}")
                        
                        with tab2:
                            if res['itens']:
                                item = res['itens'][0]
                                st.json({
                                    "numero_adicao": item['numero_adicao'],
                                    "ncm": item['ncm'],
                                    "quantidade": item['quantidade'],
                                    "valor_unitario": item['valor_unitario'],
                                    "valor_total": item['valor_total']
                                })
                        
                        with tab3:
                            st.code(pretty[:1000] + "..." if len(pretty) > 1000 else pretty, language="xml")
                        
                        # Botão de download estilizado
                        st.markdown("---")
                        col_d1, col_d2, col_d3 = st.columns([1,2,1])
                        with col_d2:
                            st.download_button(
                                label="📥 BAIXAR ARQUIVO XML",
                                data=pretty,
                                file_name=f"DUIMP_{res['header']['processo'] or 'CONVERSAO'}.xml",
                                mime="text/xml",
                                key="download_xml"
                            )
                    else:
                        st.error("❌ Nenhum item detectado no PDF. Verifique se o arquivo é um PDF de texto original.")
                
            except Exception as e:
                st.error(f"⚠️ Erro durante o processamento: {str(e)}")
                st.markdown("""
                <div class="hint">
                <strong>Sugestões para resolver:</strong><br>
                1. Verifique se o PDF não está escaneado (deve ser texto selecionável)<br>
                2. Confirme que é um PDF válido da DUIMP<br>
                3. Tente converter o PDF para um formato de texto mais limpo
                </div>
                """, unsafe_allow_html=True)
    
    else:
        # Estado inicial - sem arquivo
        st.markdown("""
        <div style="text-align: center; padding: 50px 20px;">
            <h3 style="color: #666;">📁 Nenhum arquivo selecionado</h3>
            <p style="color: #888;">Faça upload de um PDF para começar a conversão</p>
            <div style="font-size: 60px; margin: 30px;">👇</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>Häfele XML Converter v1.0 • Desenvolvido para processamento de DUIMP • Seguro e Confiável</p>
        <p style="font-size: 12px; opacity: 0.7;">© 2024 Sistema de Conversão XML - Todos os direitos reservados</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
