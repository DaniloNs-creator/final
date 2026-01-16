import streamlit as st
import pdfplumber
import re
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuração da Página
st.set_page_config(page_title="Conversor DUIMP PDF > XML", layout="wide")

st.title("🏭 Conversor DUIMP Blindado: PDF para XML")
st.markdown("""
Esta versão possui tratamento de erros avançado para evitar falhas de "Index Out of Range".
""")

# --- FUNÇÕES AUXILIARES ---

def clean_number(value_str):
    """Limpa strings numéricas para conversão segura."""
    if not value_str:
        return "0"
    try:
        clean = value_str.replace('.', '').replace(',', '.')
        return clean
    except:
        return "0"

def format_xml_value(value):
    """Formata valor para o XML (float limpo)."""
    try:
        val = float(clean_number(value))
        return f"{val:.5f}".replace('.', '')
    except:
        return "0"

def get_tag_text(text, pattern, default=""):
    """Busca texto via Regex com proteção contra None."""
    if not text:
        return default
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL) # DOTALL ajuda a pegar multi-linhas
    if match:
        # Pega o grupo 1, remove espaços e quebras de linha extras
        return match.group(1).strip()
    return default

def safe_split_get(text, delimiter, index, default=""):
    """Faz o split de uma string e pega um índice de forma segura."""
    if not text:
        return default
    parts = text.split(delimiter)
    if index < 0: # Caso índice reverso (ex: -1)
        if abs(index) <= len(parts):
            return parts[index].strip()
    elif index < len(parts):
        return parts[index].strip()
    return default if default else text # Retorna o texto original se falhar o split

# --- EXTRAÇÃO (PDF) ---

def extract_duimp_data(pdf_file):
    full_text = ""
    
    # Leitura do PDF
    with pdfplumber.open(pdf_file) as pdf:
        total_pages = len(pdf.pages)
        if total_pages == 0:
            st.error("O PDF parece estar vazio ou corrompido.")
            return {}, []
            
        progress_bar = st.progress(0)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                full_text += text + "\n"
            progress_bar.progress((i + 1) / total_pages)

    # Debug: Verificar se leu texto
    if len(full_text) < 100:
        st.warning("Atenção: Pouco texto extraído do PDF. Verifique se é um arquivo de imagem.")

    # 1. Cabeçalho
    header_data = {
        "numeroDUIMP": get_tag_text(full_text, r"Extrato da DUIMP\s+([0-9A-Z-]+)"),
        "importadorNome": get_tag_text(full_text, r"Nome do importador:\s*(.*?)\n"),
        "importadorCNPJ": get_tag_text(full_text, r"CNPJ do importador:\s*([\d./-]+)"),
        "viaTransporte": get_tag_text(full_text, r"VIA DE TRANSPORTE\s*:\s*([\w-]+)", "01-MARITIMA"),
        "pesoBrutoTotal": get_tag_text(full_text, r"PESO BRUTO KG\s*[:\n]*\s*([\d.,]+)"),
        "pesoLiquidoTotal": get_tag_text(full_text, r"PESO LIQUIDO KG\s*[:\n]*\s*([\d.,]+)"),
        "paisProcedencia": get_tag_text(full_text, r"PAIS DE PROCEDENCIA\s*[:\n]*\s*(.*?)\n"),
        "recintoAlfandegado": get_tag_text(full_text, r"RECINTO ALFANDEGADO\s*[:\n]*\s*([\d]+)", "0000000"),
        "urfDespacho": get_tag_text(full_text, r"UNIDADE DE DESPACHO\s*[:\n]*\s*([\d]+)", "0000000"),
    }

    # 2. Itens (Adições)
    # Encontra todas as ocorrências de "Item 00001", "Item 00002"
    # Usa finditer para pegar as posições
    item_matches = list(re.finditer(r"(?:Extrato da Duimp .*?)?Item\s+(\d+)", full_text))
    
    adicoes = []
    
    for i in range(len(item_matches)):
        try:
            # Lógica Segura de Inicio e Fim
            start_idx = item_matches[i].start()
            
            # Se for o último item, vai até o final do texto. Se não, vai até o início do próximo item.
            if i + 1 < len(item_matches):
                end_idx = item_matches[i+1].start()
            else:
                end_idx = len(full_text)
            
            item_text = full_text[start_idx:end_idx]
            item_num = item_matches[i].group(1) # O número do item (ex: 00001)

            # Extração dos campos do item
            fabricante_raw = get_tag_text(item_text, r"Código do Fabricante/Produtor:\s*(.*?)\n")
            
            adicao = {
                "numeroAdicao": item_num,
                "codigoProduto": get_tag_text(item_text, r"Código do produto:\s*(.*?)\n"),
                "ncm": get_tag_text(item_text, r"NCM:\s*([\d.]+)").replace('.', ''),
                "descricaoMercadoria": get_tag_text(item_text, r"Detalhamento do Produto:\s*(.*?)(?:Código de Class|$)").replace('\n', ' '),
                "paisOrigem": get_tag_text(item_text, r"País de origem:\s*(.*?)\n"),
                "fabricanteNomeRaw": fabricante_raw,
                # Usa split seguro para evitar erro se não tiver hífen
                "fabricanteNome": safe_split_get(fabricante_raw, '-', -1, default=fabricante_raw),
                "quantidade": get_tag_text(item_text, r"Quantidade na unidade estatística:\s*([\d.,]+)"),
                "unidadeMedida": get_tag_text(item_text, r"Unidade estatística:\s*(.*?)\n"),
                "pesoLiquido": get_tag_text(item_text, r"Peso liquido \(kg\):\s*([\d.,]+)"),
                "valorMoeda": get_tag_text(item_text, r"Valor total na condição de venda:\s*([\d.,]+)"),
                "valorUnitario": get_tag_text(item_text, r"Valor unitário na condição de venda:\s*([\d.,]+)"),
                "moeda": get_tag_text(item_text, r"Moeda negociada:\s*(.*?)\n"),
                "incoterm": "FCA", 
                "condicaoVendaLocal": "SUAPE"
            }
            
            # Tributos (PIS/COFINS) - Regex ajustado para pegar na tabela
            adicao['cofins_valor'] = get_tag_text(item_text, r"COFINS\s*[:\n\",]*\s*([\d.,]+)", "0")
            
            adicoes.append(adicao)
            
        except Exception as e:
            st.error(f"Erro ao processar Item {i+1}: {str(e)}")
            continue # Pula para o próximo item se um falhar

    return header_data, adicoes

# --- GERAÇÃO XML ---

def generate_xml(header, adicoes):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")

    for item in adicoes:
        adicao = ET.SubElement(duimp, "adicao")
        
        # Acrescimo
        acrescimo = ET.SubElement(adicao, "acrescimo")
        ET.SubElement(acrescimo, "codigoAcrescimo").text = "17"
        ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        ET.SubElement(acrescimo, "moedaNegociadaCodigo").text = "220" if "DOLAR" in str(item['moeda']).upper() else "978"
        ET.SubElement(acrescimo, "moedaNegociadaNome").text = str(item['moeda']).strip()
        ET.SubElement(acrescimo, "valorMoedaNegociada").text = "0"
        ET.SubElement(acrescimo, "valorReais").text = "0"

        # COFINS
        ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965"
        ET.SubElement(adicao, "cofinsAliquotaValorDevido").text = format_xml_value(item['cofins_valor'])
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_xml_value(item['cofins_valor'])
        
        # Condição Venda
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = item['incoterm']
        ET.SubElement(adicao, "condicaoVendaLocal").text = item['condicaoVendaLocal']
        ET.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
        ET.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = "METODO 1"
        ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "220" if "DOLAR" in str(item['moeda']).upper() else "978"
        ET.SubElement(adicao, "condicaoVendaMoedaNome").text = str(item['moeda']).strip()
        ET.SubElement(adicao, "condicaoVendaValorMoeda").text = format_xml_value(item['valorMoeda'])
        
        # Dados Carga
        pais_cod = "076" if "CHINA" in str(header.get('paisProcedencia', '')).upper() else "000"
        ET.SubElement(adicao, "dadosCargaPaisProcedenciaCodigo").text = pais_cod
        ET.SubElement(adicao, "dadosCargaUrfEntradaCodigo").text = str(header.get('urfDespacho', ''))
        ET.SubElement(adicao, "dadosCargaViaTransporteCodigo").text = "01"
        ET.SubElement(adicao, "dadosCargaViaTransporteNome").text = "MARÍTIMA"
        
        # Mercadoria Dados
        ET.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item['ncm']
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaQuantidade").text = format_xml_value(item['quantidade'])
        ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaUnidade").text = item['unidadeMedida']
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_xml_value(item['pesoLiquido'])
        
        # Fornecedor
        ET.SubElement(adicao, "fornecedorNome").text = item['fabricanteNome']
        
        # Regimes
        ET.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
        ET.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
        ET.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "4"
        ET.SubElement(adicao, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"
        
        # Mercadoria Tag
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item['descricaoMercadoria'][:250]
        ET.SubElement(mercadoria, "numeroSequencialItem").text = str(item['numeroAdicao']).zfill(2)
        ET.SubElement(mercadoria, "quantidade").text = format_xml_value(item['quantidade'])
        ET.SubElement(mercadoria, "unidadeMedida").text = item['unidadeMedida']
        ET.SubElement(mercadoria, "valorUnitario").text = format_xml_value(item['valorUnitario'])
        
        # Identificadores
        ET.SubElement(adicao, "numeroAdicao").text = str(item['numeroAdicao']).zfill(3)
        ET.SubElement(adicao, "numeroDUIMP").text = header.get('numeroDUIMP', '')
        ET.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = item['paisOrigem']
        ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = item['paisOrigem']
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    # Footer DUIMP
    ET.SubElement(duimp, "numeroDUIMP").text = header.get('numeroDUIMP', '')
    ET.SubElement(duimp, "totalAdicoes").text = str(len(adicoes)).zfill(3)
    ET.SubElement(duimp, "importadorNome").text = header.get('importadorNome', '')
    cnpj_limpo = str(header.get('importadorCNPJ', '')).replace('.', '').replace('/', '').replace('-', '')
    ET.SubElement(duimp, "importadorNumero").text = cnpj_limpo
    ET.SubElement(duimp, "cargaPesoBruto").text = format_xml_value(header.get('pesoBrutoTotal', '0'))
    ET.SubElement(duimp, "cargaPesoLiquido").text = format_xml_value(header.get('pesoLiquidoTotal', '0'))
    
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    return xml_str

# --- INTERFACE ---

uploaded_file = st.file_uploader("Carregar Extrato DUIMP (PDF)", type="pdf")

if uploaded_file is not None:
    st.info("Arquivo carregado. Iniciando processamento...")
    
    try:
        with st.spinner("Lendo PDF..."):
            header_data, adicoes_data = extract_duimp_data(uploaded_file)
        
        if not adicoes_data:
            st.error("Nenhum item foi encontrado no PDF. Verifique se o arquivo é um Extrato de DUIMP válido.")
        else:
            col1, col2 = st.columns(2)
            col1.metric("Número DUIMP", header_data.get("numeroDUIMP", "Não encontrado"))
            col2.metric("Itens Encontrados", len(adicoes_data))
            
            st.write("---")
            st.subheader("Prévia dos Itens (Primeiros 5)")
            st.dataframe(adicoes_data[:5])
            
            if st.button("Gerar XML"):
                xml_output = generate_xml(header_data, adicoes_data)
                st.success("XML Gerado!")
                st.download_button(
                    label="Baixar XML",
                    data=xml_output,
                    file_name=f"DUIMP_{header_data.get('numeroDUIMP', 'export')}.xml",
                    mime="application/xml"
                )

    except Exception as e:
        st.error(f"Erro Crítico: {e}")
