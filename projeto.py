import streamlit as st
import pdfplumber
import re
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuração da Página
st.set_page_config(page_title="Conversor DUIMP PDF > XML", layout="wide")

st.title("🏭 Conversor Profissional: Extrato DUIMP (PDF) para XML")
st.markdown("""
Esta aplicação converte o **Extrato da DUIMP (PDF)** para o formato **XML** obrigatório para importação.
O sistema processa o cabeçalho e todas as adições (itens), mantendo a estrutura do layout `M-DUIMP`.
""")

# --- FUNÇÕES AUXILIARES DE FORMATAÇÃO ---

def clean_number(value_str):
    """
    Converte string '10.000,00' para float ou formato limpo.
    Baseado no XML exemplo, remove pontos e troca vírgula por ponto ou remove formatação.
    """
    if not value_str:
        return "0"
    # Remove pontos de milhar
    clean = value_str.replace('.', '')
    # Troca vírgula decimal por ponto
    clean = clean.replace(',', '.')
    return clean

def format_xml_value(value, padding=15):
    """
    Formata valores numéricos para o padrão do XML (muitas vezes zeros a esquerda e sem ponto, 
    ou formato float padrão). Aqui adotaremos o padrão 'clean' float.
    Para o layout exato de zeros (ex: 000000000014595), seria necessário saber a regra de precisão exata.
    Vou aplicar uma limpeza padrão que pode ser ajustada.
    """
    try:
        # Remove caracteres não numéricos exceto ponto
        val = float(clean_number(value))
        # Formata com zeros a esquerda se necessário (exemplo genérico)
        # O XML de exemplo mostra: 00000000000014514969 (sem ponto decimal, implicito?)
        # Visto a complexidade, retornaremos o float limpo para garantir a leitura matemática primeiro
        return f"{val:.5f}".replace('.', '') # Exemplo: Remove ponto e padroniza casas
    except:
        return "0"

def get_tag_text(text, pattern, default=""):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return default

# --- NÚCLEO DE EXTRAÇÃO (PDF) ---

def extract_duimp_data(pdf_file):
    """Lê o PDF e estrutura os dados em um dicionário Python."""
    
    full_text = ""
    # Barra de progresso para PDFs grandes
    with pdfplumber.open(pdf_file) as pdf:
        total_pages = len(pdf.pages)
        progress_bar = st.progress(0)
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                full_text += text + "\n"
            
            # Atualiza progresso
            if i % 10 == 0 or i == total_pages - 1:
                progress_bar.progress((i + 1) / total_pages)

    # 1. Extração do Cabeçalho (Dados Gerais)
    header_data = {
        "numeroDUIMP": get_tag_text(full_text, r"Extrato da DUIMP\s+([0-9A-Z-]+)"),
        "importadorNome": get_tag_text(full_text, r"Nome do importador:\s*(.*?)\n"),
        "importadorCNPJ": get_tag_text(full_text, r"CNPJ do importador:\s*([\d./-]+)"),
        "viaTransporte": get_tag_text(full_text, r"VIA DE TRANSPORTE\s*:\s*([\w-]+)", "01-MARITIMA"),
        "pesoBrutoTotal": get_tag_text(full_text, r"Peso Bruto \(kg\):\s*([\d.,]+)"),
        "pesoLiquidoTotal": get_tag_text(full_text, r"Peso Liquido \(kg\):\s*([\d.,]+)"),
        "paisProcedencia": get_tag_text(full_text, r"PAIS DE PROCEDENCIA\s*:\s*(.*?)\n"),
        "recintoAlfandegado": get_tag_text(full_text, r"RECINTO ALFANDEGADO\s*:\s*([\d]+)", "0000000"),
        "urfDespacho": get_tag_text(full_text, r"UNIDADE DE DESPACHO\s*:\s*([\d]+)", "0000000"),
    }

    # 2. Extração dos Itens (Adições)
    # A lógica é dividir o texto onde aparece "Extrato da Duimp ... Item X"
    # Regex para encontrar o início de cada item
    item_matches = list(re.finditer(r"Extrato da Duimp .*? Item (\d+)", full_text))
    
    adicoes = []
    
    for i in range(len(item_matches)):
        start_idx = item_matches[i].start()
        end_idx = item_matches[i+1].start() if i + 1 < len(item_matches) else len(full_text)
        
        item_text = full_text[start_idx:end_idx]
        item_num = item_matches[i].group(1)
        
        # Extrair dados específicos do item
        adicao = {
            "numeroAdicao": item_num,
            "codigoProduto": get_tag_text(item_text, r"Código do produto:\s*(.*?)\n"),
            "ncm": get_tag_text(item_text, r"NCM:\s*([\d.]+)").replace('.', ''),
            "descricaoMercadoria": get_tag_text(item_text, r"Detalhamento do Produto:\s*(.*?)(?:Código de Class|$)").replace('\n', ' '),
            "paisOrigem": get_tag_text(item_text, r"País de origem:\s*(.*?)\n"),
            "fabricanteNome": get_tag_text(item_text, r"Código do Fabricante/Produtor:\s*(.*?)\n"),
            "quantidade": get_tag_text(item_text, r"Quantidade na unidade estatística:\s*([\d.,]+)"),
            "unidadeMedida": get_tag_text(item_text, r"Unidade estatística:\s*(.*?)\n"),
            "pesoLiquido": get_tag_text(item_text, r"Peso líquido \(kg\):\s*([\d.,]+)"),
            "valorMoeda": get_tag_text(item_text, r"Valor total na condição de venda:\s*([\d.,]+)"),
            "valorUnitario": get_tag_text(item_text, r"Valor unitário na condição de venda:\s*([\d.,]+)"),
            "moeda": get_tag_text(item_text, r"Moeda negociada:\s*(.*?)\n"),
            "incoterm": "FCA", # Default ou extrair se disponível
            "condicaoVendaLocal": "SUAPE" # Pode extrair do 'Local de destino' se necessário
        }
        
        # Tentativa de pegar tributos (Exemplo simples, o PDF separa em tabelas complexas)
        # No cenário real, usaríamos pdfplumber table extraction para precisão
        adicao['pis_valor'] = get_tag_text(item_text, r"PIS\s*:\s*([\d.,]+)", "0")
        adicao['cofins_valor'] = get_tag_text(item_text, r"COFINS\s*:\s*([\d.,]+)", "0")
        adicao['ii_valor'] = get_tag_text(item_text, r"II\s*:\s*([\d.,]+)", "0") # Exemplo hipotetico se houver II explicito no texto do item
        
        adicoes.append(adicao)

    return header_data, adicoes

# --- GERAÇÃO DO XML (Layout M-DUIMP) ---

def generate_xml(header, adicoes):
    """
    Constrói o XML seguindo rigorosamente a estrutura do arquivo M-DUIMP.
    """
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")

    # Loop para criar as ADIÇÕES (Items)
    # Nota: No M-DUIMP, <adicao> vem primeiro, com dados aninhados.
    
    for item in adicoes:
        adicao = ET.SubElement(duimp, "adicao")
        
        # --- Grupo: Acrescimo (Exemplo estático/padrão conforme M-DUIMP ou dados reais se tiver) ---
        acrescimo = ET.SubElement(adicao, "acrescimo")
        ET.SubElement(acrescimo, "codigoAcrescimo").text = "17"
        ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        ET.SubElement(acrescimo, "moedaNegociadaCodigo").text = "220" if "DOLAR" in item['moeda'] else "978"
        ET.SubElement(acrescimo, "moedaNegociadaNome").text = item['moeda']
        ET.SubElement(acrescimo, "valorMoedaNegociada").text = "000000000000000" # Placeholder
        ET.SubElement(acrescimo, "valorReais").text = "000000000000000" # Placeholder

        # --- Tributos (Exemplo: COFINS) ---
        ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965" # Exemplo fixo ou extraído
        ET.SubElement(adicao, "cofinsAliquotaValorDevido").text = format_xml_value(item['cofins_valor'])
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_xml_value(item['cofins_valor'])
        
        # --- Condição de Venda ---
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = item['incoterm']
        ET.SubElement(adicao, "condicaoVendaLocal").text = item['condicaoVendaLocal']
        ET.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
        ET.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"
        ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "220" if "DOLAR" in item['moeda'] else "978"
        ET.SubElement(adicao, "condicaoVendaMoedaNome").text = item['moeda']
        # Valor Total do Item na Moeda
        ET.SubElement(adicao, "condicaoVendaValorMoeda").text = format_xml_value(item['valorMoeda'])
        
        # --- Dados Carga/Mercadoria ---
        ET.SubElement(adicao, "dadosCargaPaisProcedenciaCodigo").text = "076" if "CHINA" in header['paisProcedencia'].upper() else "000"
        ET.SubElement(adicao, "dadosCargaUrfEntradaCodigo").text = header['urfDespacho']
        ET.SubElement(adicao, "dadosCargaViaTransporteCodigo").text = "01"
        ET.SubElement(adicao, "dadosCargaViaTransporteNome").text = "MARÍTIMA"
        
        ET.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item['ncm']
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        
        # Quantidades e Pesos (Formatados)
        ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaQuantidade").text = format_xml_value(item['quantidade'])
        ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaUnidade").text = item['unidadeMedida']
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_xml_value(item['pesoLiquido'])
        
        # Dados Fornecedor (Simplificado, pegando do item)
        ET.SubElement(adicao, "fornecedorNome").text = item['fabricanteNome'].split('-')[-1].strip() if '-' in item['fabricanteNome'] else item['fabricanteNome']
        
        # Dados Tributos II/IPI (Preenchimento básico baseado no template)
        ET.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
        ET.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
        ET.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "4"
        ET.SubElement(adicao, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"
        
        # --- Tag Mercadoria (Detalhe) ---
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item['descricaoMercadoria'][:200] # Limite de caracteres comum
        ET.SubElement(mercadoria, "numeroSequencialItem").text = item['numeroAdicao'].zfill(2)
        ET.SubElement(mercadoria, "quantidade").text = format_xml_value(item['quantidade'])
        ET.SubElement(mercadoria, "unidadeMedida").text = item['unidadeMedida']
        ET.SubElement(mercadoria, "valorUnitario").text = format_xml_value(item['valorUnitario'])
        
        # Identificadores da Adição
        ET.SubElement(adicao, "numeroAdicao").text = item['numeroAdicao'].zfill(3)
        ET.SubElement(adicao, "numeroDUIMP").text = header['numeroDUIMP']
        ET.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = item['paisOrigem']
        ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = item['paisOrigem']
        
        # Vinculo
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    # --- Tags Finais de Fechamento da DUIMP (Nível Raiz DUIMP) ---
    ET.SubElement(duimp, "numeroDUIMP").text = header['numeroDUIMP']
    ET.SubElement(duimp, "totalAdicoes").text = str(len(adicoes)).zfill(3)
    
    # Importador
    ET.SubElement(duimp, "importadorNome").text = header['importadorNome']
    ET.SubElement(duimp, "importadorNumero").text = header['importadorCNPJ'].replace('.', '').replace('/', '').replace('-', '')
    
    # Informações Logísticas Totais
    ET.SubElement(duimp, "cargaPesoBruto").text = format_xml_value(header['pesoBrutoTotal'])
    ET.SubElement(duimp, "cargaPesoLiquido").text = format_xml_value(header['pesoLiquidoTotal'])
    
    # Gerar String
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    return xml_str

# --- INTERFACE PRINCIPAL ---

uploaded_file = st.file_uploader("Carregar Extrato DUIMP (PDF)", type="pdf")

if uploaded_file is not None:
    st.info("Arquivo carregado. Iniciando processamento...")
    
    try:
        # 1. Extrair
        with st.spinner("Lendo PDF e extraindo dados (isso pode levar alguns segundos para arquivos grandes)..."):
            header_data, adicoes_data = extract_duimp_data(uploaded_file)
        
        # Mostrar resumo
        col1, col2, col3 = st.columns(3)
        col1.metric("DUIMP", header_data.get("numeroDUIMP", "N/A"))
        col2.metric("Total de Itens", len(adicoes_data))
        col3.metric("Importador", header_data.get("importadorNome", "")[:20] + "...")
        
        st.divider()
        st.subheader("Prévia dos Dados Extraídos")
        st.dataframe(adicoes_data) # Mostra tabela com os dados encontrados
        
        # 2. Gerar XML
        if st.button("Gerar e Converter XML"):
            xml_output = generate_xml(header_data, adicoes_data)
            
            st.success("XML Gerado com Sucesso!")
            
            # Botão de Download
            st.download_button(
                label="📥 Baixar Arquivo XML (Layout M-DUIMP)",
                data=xml_output,
                file_name=f"M-DUIMP-{header_data.get('numeroDUIMP', 'conv')}.xml",
                mime="application/xml"
            )
            
            # Expander para ver o código
            with st.expander("Visualizar XML Bruto"):
                st.code(xml_output, language='xml')

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
