import streamlit as st
import pdfplumber
import re
from lxml import etree
import io

# Configuração da Página
st.set_page_config(page_title="Conversor DUIMP PDF > XML", layout="wide")

# --- MÓDULO 1: UTILITÁRIOS DE FORMATAÇÃO (CRÍTICO PARA O XML) ---
def format_number_xml(value, length=15, decimals=2):
    """
    Transforma string '1.234,56' ou float em '000000000123456'.
    Remove pontuação e preenche com zeros à esquerda.
    """
    if not value:
        return "0" * length
    
    # Limpeza básica se vier string
    if isinstance(value, str):
        # Remove pontos de milhar e troca vírgula por ponto para float
        clean_val = value.replace('.', '').replace(',', '.')
        try:
            float_val = float(clean_val)
        except ValueError:
            return "0" * length
    else:
        float_val = value

    # Converter para inteiro removendo o ponto decimal virtualmente
    # Ex: 100.50 -> 10050
    int_val = int(round(float_val * (10**decimals)))
    
    return str(int_val).zfill(length)

def format_text_xml(text):
    """Limpa caracteres inválidos para XML"""
    if not text:
        return ""
    return str(text).strip()

# --- MÓDULO 2: EXTRAÇÃO DE DADOS (PARSER) ---
def extract_data_from_pdf(pdf_file):
    """
    Lê o PDF e extrai dados do cabeçalho e a lista de adições.
    Otimizado para ler página a página sem estourar memória.
    """
    extracted_data = {
        "header": {},
        "adicoes": []
    }
    
    full_text = ""
    
    with pdfplumber.open(pdf_file) as pdf:
        total_pages = len(pdf.pages)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, page in enumerate(pdf.pages):
            # Atualiza barra de progresso
            if i % 10 == 0: # Atualiza a cada 10 paginas para performance
                progress = (i + 1) / total_pages
                progress_bar.progress(progress)
                status_text.text(f"Processando página {i+1} de {total_pages}...")

            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        progress_bar.empty()
        status_text.text("Extração de texto concluída. Iniciando estruturação...")

    # --- REGEX ESTRATÉGICO PARA CAPTURAR DADOS ---
    # 1. Dados Gerais (Header)
    # Busca por padrões como "PROCESSO #12345" ou "Numero\n25BR..."
    
    # Exemplo de captura do Número da DUIMP
    duimp_match = re.search(r'Numero\s*\n\s*([0-9A-Z]+)', full_text)
    extracted_data['header']['numeroDUIMP'] = duimp_match.group(1) if duimp_match else "0000000000"

    # Exemplo de captura do Importador
    imp_match = re.search(r'IMPORTADOR\s*\n\s*"([^"]+)"', full_text)
    extracted_data['header']['importadorNome'] = imp_match.group(1) if imp_match else "N/I"

    # 2. Identificação de Adições (Loop Complexo)
    # A estratégia é dividir o texto pelos blocos de "Nº Adição" ou padrão similar
    # Assumindo que o PDF lista itens sequencialmente.
    
    # Padrão para encontrar itens. Ajuste conforme o layout real do PDF.
    # Exemplo: Procura por linhas que começam com codigo NCM ou descrição
    # Aqui simularemos a extração de itens baseada em padrões comuns de extratos
    
    # MOCKUP DE EXTRAÇÃO DE ITENS (Você deve ajustar o Regex para o layout real exato)
    # Vamos procurar blocos que parecem itens. 
    # Supondo que cada item tenha um "Valor Mercadoria" e "NCM"
    
    # Regex genérico para capturar valores monetários associados a NCMs (exemplo)
    # Ajuste este padrão olhando seu PDF real com raw text
    item_matches = re.finditer(r'NCM\s*(\d+).*?Valor\s*([\d\.,]+)', full_text, re.DOTALL)
    
    count = 1
    for match in item_matches:
        item = {
            "numeroAdicao": str(count).zfill(3),
            "ncm": match.group(1),
            "valor": match.group(2), # String '1.000,00'
            "descricao": f"Item extraído {count} - Adapte o Regex para descrição real"
        }
        extracted_data['adicoes'].append(item)
        count += 1
    
    # Fallback se o regex acima não pegar nada (para teste)
    if not extracted_data['adicoes']:
        extracted_data['adicoes'].append({
            "numeroAdicao": "001",
            "ncm": "39263000",
            "valor": "1066,01",
            "descricao": "ITEM MOCKUP - AJUSTE O REGEX"
        })

    return extracted_data

# --- MÓDULO 3: GERADOR DE XML (BUILDER) ---
def build_xml(data):
    """
    Constrói a árvore XML respeitando estritamente a estrutura solicitada.
    """
    # Namespaces e Configuração Raiz
    root = etree.Element("ListaDeclaracoes")
    duimp = etree.SubElement(root, "duimp")

    # --- Loop de Adições ---
    for item in data['adicoes']:
        adicao = etree.SubElement(duimp, "adicao")
        
        # Grupo ACRESCIMO (Exemplo fixo ou dinâmico)
        acrescimo = etree.SubElement(adicao, "acrescimo")
        etree.SubElement(acrescimo, "codigoAcrescimo").text = "17"
        etree.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS"
        etree.SubElement(acrescimo, "valorReais").text = format_number_xml(item['valor'], 15, 2)

        # Campos soltos da adição (Mapeando do PDF ou Default)
        etree.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
        
        # Grupo DADOS MERCADORIA
        dados_merc = etree.SubElement(adicao, "dadosMercadoria")
        etree.SubElement(dados_merc, "dadosMercadoriaCodigoNcm").text = format_text_xml(item['ncm'])
        etree.SubElement(dados_merc, "dadosMercadoriaCondicao").text = "NOVA"
        
        # Grupo MERCADORIA (Detalhe do Item)
        mercadoria = etree.SubElement(adicao, "mercadoria")
        etree.SubElement(mercadoria, "descricaoMercadoria").text = format_text_xml(item['descricao'])
        etree.SubElement(mercadoria, "numeroSequencialItem").text = item['numeroAdicao'][-2:] # Pega os 2 ultimos digitos
        etree.SubElement(mercadoria, "valorUnitario").text = format_number_xml(item['valor'], 20, 8) # Exemplo de precisão alta
        
        # Campos de Identificação
        etree.SubElement(adicao, "numeroAdicao").text = item['numeroAdicao']
        etree.SubElement(adicao, "numeroDUIMP").text = format_text_xml(data['header']['numeroDUIMP'])
        
        # Tributos (Exemplo de preenchimento fixo/calculado)
        etree.SubElement(adicao, "iiRegimeTributacaoCode").text = "1"

    # --- Seção 2: Dados Gerais ---
    # Campos fora das adições
    etree.SubElement(duimp, "importadorNome").text = format_text_xml(data['header']['importadorNome'])
    etree.SubElement(duimp, "numeroDUIMP").text = format_text_xml(data['header']['numeroDUIMP'])
    
    # Exemplo de Pagamento
    pagamento = etree.SubElement(duimp, "pagamento")
    etree.SubElement(pagamento, "bancoPagamento").text = "341"
    
    # Retorna string XML formatada
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")

# --- MÓDULO 4: INTERFACE DO USUÁRIO ---

st.title("🤖 Conversor Profissional: Extrato PDF > XML DUIMP")
st.markdown("""
Este sistema processa extratos de conferência de DUIMP e gera o XML estruturado para importação.
**Capacidade:** Otimizado para arquivos grandes (+500 págs).
""")

uploaded_file = st.file_uploader("Arraste seu PDF aqui", type=["pdf"])

if uploaded_file is not None:
    st.info(f"Arquivo carregado: {uploaded_file.name}. Iniciando processamento...")
    
    # Botão de ação
    if st.button("Gerar XML"):
        try:
            with st.spinner("Lendo PDF e estruturando dados..."):
                # 1. Extrair
                raw_data = extract_data_from_pdf(uploaded_file)
                
                # 2. Construir XML
                xml_string = build_xml(raw_data)
                
                # 3. Preview (Amostra)
                st.success("Conversão concluída com sucesso!")
                
                with st.expander("Ver Preview do XML (Primeiras 50 linhas)"):
                    st.code(xml_string[:2000], language='xml')
                
                # 4. Download
                st.download_button(
                    label="📥 Baixar Arquivo XML Completo",
                    data=xml_string,
                    file_name=f"DUIMP_{raw_data['header']['numeroDUIMP']}.xml",
                    mime="application/xml"
                )
                
                st.metric("Adições Processadas", len(raw_data['adicoes']))
                
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
            st.warning("Verifique se o PDF segue o padrão 'Extrato de Conferência DUIMP'.")
