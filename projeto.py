import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- FUNÇÕES DE LIMPEZA E FORMATAÇÃO ---

def clean_text(text):
    """Remove quebras de linha e espaços duplos, deixando o texto em uma linha só."""
    if not text: return ""
    # Substitui quebras de linha por espaço
    text = text.replace('\n', ' ')
    # Remove espaços duplicados
    return re.sub(r'\s+', ' ', text).strip()

def format_xml_number(value, length=15):
    """
    Formata valores numéricos para o padrão XML (sem vírgula, zeros à esquerda).
    Ex: '1.234,56' -> '000000000123456'
    """
    if not value:
        return "0" * length
    # Mantém apenas dígitos e vírgula
    clean = re.sub(r'[^\d,]', '', str(value))
    # Remove a vírgula
    clean = clean.replace(',', '')
    # Preenche com zeros
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

# --- LÓGICA DE EXTRAÇÃO (PARSER) ---

def parse_pdf(pdf_file):
    full_text = ""
    # Abre o PDF e extrai todo o texto
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
    # Divide o texto gigante onde encontra "ITENS DA DUIMP" seguido de um número
    raw_itens = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", full_text)

    if len(raw_itens) > 1:
        # Pula o índice 0 (texto antes do primeiro item) e itera de 2 em 2
        for i in range(1, len(raw_itens), 2):
            num_item = raw_itens[i]
            content = raw_itens[i+1] # Texto contendo os dados do item

            # --- AQUI ESTÁ A MÁGICA DA DESCRIÇÃO ---
            
            # 1. Captura a Descrição Pura (Texto entre DENOMINACAO e CODIGO INTERNO)
            desc_pura = safe_extract(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+CÓDIGO INTERNO", content)
            desc_pura = clean_text(desc_pura)

            # 2. Captura o Código/PartNumber
            # Pega tudo entre "PARTNUMBER)" e o próximo campo (geralmente PAIS, FABRICANTE ou CONDICAO)
            # Isso garante que pegue "25053315 - 30 - 811.62.363" inteiro
            codigo_partnumber = safe_extract(r"PARTNUMBER\)\s+(.*?)\s+(?:PAIS|FABRICANTE|CONDICAO|VALOR|NCM)", content)
            codigo_partnumber = clean_text(codigo_partnumber)

            # 3. Concatena: "CODIGO - DESCRIÇÃO"
            if codigo_partnumber:
                descricao_final = f"{codigo_partnumber} - {desc_pura}"
            else:
                descricao_final = desc_pura # Fallback se não achar código

            # --- DEMAIS CAMPOS ---
            item = {
                "numero_adicao": num_item.zfill(3),
                "descricao": descricao_final, # Usa a descrição composta
                "ncm": safe_extract(r"NCM\s*[:\n]*\s*([\d\.]+)", content).replace(".", "") or "00000000",
                "quantidade": safe_extract(r"Qtde Unid\. Comercial\s*[:\n]*\s*([\d\.,]+)", content) or "0",
                "valor_unitario": safe_extract(r"Valor Unit Cond Venda\s*[:\n]*\s*([\d\.,]+)", content) or "0",
                "valor_total": safe_extract(r"Valor Tot\. Cond Venda\s*[:\n]*\s*([\d\.,]+)", content) or "0",
                "peso_liquido": safe_extract(r"Peso Líquido \(KG\)\s*[:\n]*\s*([\d\.,]+)", content) or "0",
                # Impostos
                "pis": safe_extract(r"PIS.*?Valor Devido.*?([\d\.,]+)", content) or "0",
                "cofins": safe_extract(r"COFINS.*?Valor Devido.*?([\d\.,]+)", content) or "0",
            }
            
            data["itens"].append(item)
            
    return data

# --- GERAÇÃO DO XML ---

def create_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")

    # --- ADIÇÕES ---
    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")

        # Campos fixos zerados
        ET.SubElement(adicao, "cideValorAliquotaEspecifica").text = "0"*11
        ET.SubElement(adicao, "cideValorDevido").text = "0"*15
        ET.SubElement(adicao, "cideValorRecolher").text = "0"*15
        ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
        ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
        
        # COFINS
        ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965"
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_xml_number(item["cofins"], 15)
        
        # Venda
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
        ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
        ET.SubElement(adicao, "condicaoVendaValorMoeda").text = format_xml_number(item["valor_total"], 15)
        
        # Mercadoria Global
        ET.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item["ncm"]
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_xml_number(item["peso_liquido"], 15)
        
        # --- TAG <mercadoria> COM A DESCRIÇÃO CORRETA ---
        mercadoria = ET.SubElement(adicao, "mercadoria")
        # Aqui entra "25053315 - 30 - 811.62.363 - CABIDEIRO..."
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(mercadoria, "numeroSequencialItem").text = item["numero_adicao"][-2:]
        ET.SubElement(mercadoria, "quantidade").text = format_xml_number(item["quantidade"], 14)
        ET.SubElement(mercadoria, "unidadeMedida").text = "UNIDADE"
        ET.SubElement(mercadoria, "valorUnitario").text = format_xml_number(item["valor_unitario"], 20)
        
        # Identificação
        ET.SubElement(adicao, "numeroAdicao").text = item["numero_adicao"]
        duimp_limpa = data["header"]["duimp"].replace("25BR", "")[:10]
        ET.SubElement(adicao, "numeroDUIMP").text = duimp_limpa if duimp_limpa else "0000000000"
        
        # PIS / Vinculos
        ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_xml_number(item["pis"], 15)
        ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    # --- DADOS GLOBAIS ---
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
    ET.SubElement(duimp, "importadorNome").text = data["header"]["importador"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj"]
    
    info = ET.SubElement(duimp, "informacaoComplementar")
    info.text = f"PROCESSO: {data['header']['processo']} - IMPORTACAO PROPRIA"
    
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["duimp"]
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)

    return root

# --- APP STREAMLIT ---

def main():
    st.set_page_config(page_title="Conversor XML DUIMP - PartNumber", layout="wide")
    st.title("Conversor DUIMP -> XML (Layout PartNumber)")
    st.markdown("Gera XML concatenando: **[CÓDIGO INTERNO] - [DESCRIÇÃO]**.")

    uploaded_file = st.file_uploader("Arraste o PDF aqui", type="pdf")

    if uploaded_file:
        if st.button("Processar Arquivo"):
            with st.spinner("Lendo PDF..."):
                try:
                    data = parse_pdf(uploaded_file)
                    
                    if not data["itens"]:
                        st.error("Erro: Nenhum item encontrado. Verifique se o PDF é selecionável.")
                    else:
                        # Gera XML
                        xml_root = create_xml(data)
                        xml_str = ET.tostring(xml_root, 'utf-8')
                        parsed = minidom.parseString(xml_str)
                        pretty_xml = parsed.toprettyxml(indent="    ")

                        st.success("Conversão concluída!")
                        
                        # Mostra exemplo do Item 1 para validação imediata
                        st.markdown("### Validação Visual (Primeiro Item)")
                        st.code(data["itens"][0]["descricao"], language="text")
                        
                        # Se houver item 74 (seu exemplo), mostra ele também
                        if len(data["itens"]) >= 74:
                            st.markdown("### Validação Visual (Item 74)")
                            # Indice 73 pois começa em 0
                            st.code(data["itens"][73]["descricao"], language="text")

                        st.download_button(
                            label="📥 Baixar XML Final",
                            data=pretty_xml,
                            file_name=f"M-DUIMP-{data['header']['processo']}.xml",
                            mime="text/xml"
                        )
                except Exception as e:
                    st.error(f"Erro: {e}")

if __name__ == "__main__":
    main()
