import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# --- FUNÇÕES UTILITÁRIAS ---

def safe_extract(pattern, text, group=1, default=""):
    """
    Tenta extrair um valor usando regex. Se não encontrar, retorna o valor default
    em vez de gerar erro.
    """
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            # Remove aspas extras e quebras de linha que possam vir da tabela
            clean_val = match.group(group).replace('"', '').replace("'", "").strip()
            return clean_val
    except Exception:
        pass
    return default

def format_xml_number(value, length=15):
    """
    Formata valores para o padrão XML (sem vírgula, zeros à esquerda).
    Ex: '1.234,56' -> '000000000123456'
    """
    if not value:
        return "0" * length
    
    # Remove tudo que não for dígito ou vírgula
    clean = re.sub(r'[^\d,]', '', str(value))
    
    # Remove a vírgula para ficar apenas números corridos (formato Siscomex/Duimp)
    clean = clean.replace(',', '')
    
    if len(clean) > length:
        return clean[-length:]
    return clean.zfill(length)

def clean_description(text):
    """Limpa a descrição do produto removendo quebras de linha de tabelas"""
    if not text: return "MERCADORIA GERAL"
    # Substitui quebras de linha por espaço e remove espaços duplos
    return re.sub(r'\s+', ' ', text).strip()

# --- LÓGICA DE EXTRAÇÃO (PARSER) ---

def parse_pdf(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            # Extração simples de texto (melhor para layouts lineares)
            full_text += page.extract_text() or "" + "\n"
            
            # (Opcional) Debug: imprimir texto no terminal para ver como está saindo
            # print(page.extract_text()) 

    data = {
        "header": {},
        "itens": []
    }

    # 1. Extração do Cabeçalho (Usando safe_extract para não dar erro)
    data["header"]["numero_processo"] = safe_extract(r"PROCESSO\s*#?(\d+)", full_text)
    # Tenta pegar o importador ignorando caracteres de tabela csv-like
    data["header"]["importador_nome"] = safe_extract(r"IMPORTADOR\s*[:\n,]*[\"']?([\w\s]+)", full_text, default="HAFELE BRASIL LTDA")
    data["header"]["numero_duimp"] = safe_extract(r"Numero\s*[:\n,]*[\"']?([0-9BR]+)", full_text)
    data["header"]["cnpj"] = safe_extract(r"CNPJ\s*[:\n,]*[\"']?([\d\./-]+)", full_text).replace('.', '').replace('/', '').replace('-', '')
    
    # Frete Total (Procura por FRETE BASICO ou similar no resumo)
    data["header"]["frete_total"] = safe_extract(r"Total \(R\$\)\s*([\d\.,]+)", full_text)

    # 2. Extração dos Itens
    # Divide o texto onde aparece "ITENS DA DUIMP" seguido de números
    # O regex captura o número do item para usarmos de referência
    raw_itens = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", full_text)
    
    # Se o split funcionou, raw_itens terá: [texto_intro, "00001", texto_item_1, "00002", texto_item_2...]
    if len(raw_itens) > 1:
        for i in range(1, len(raw_itens), 2):
            num_item = raw_itens[i]
            content = raw_itens[i+1] # Texto correspondente ao item
            
            item = {
                "numero_adicao": num_item.zfill(3),
                # Regex ajustado para pegar valores que podem estar na linha de baixo (\n) ou entre aspas
                "ncm": safe_extract(r"NCM\s*[:\n,]*[\"']?([\d\.]+)", content, default="00000000").replace(".", ""),
                "valor_unitario": safe_extract(r"Valor Unit Cond Venda\s*[:\n,]*[\"']?([\d\.,]+)", content, default="0"),
                "quantidade": safe_extract(r"Qtde Unid\. Comercial\s*[:\n,]*[\"']?([\d\.,]+)", content, default="0"),
                # Descrição: Pega tudo entre "DENOMINACAO DO PRODUTO" e "CÓDIGO INTERNO"
                "descricao": safe_extract(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+(?:CÓDIGO|DESCRICAO|FABRICANTE)", content, group=1),
                "peso_liquido": safe_extract(r"Peso Líquido \(KG\)\s*[:\n,]*[\"']?([\d\.,]+)", content, default="0"),
                "valor_total_moeda": safe_extract(r"Valor Tot\. Cond Venda\s*[:\n,]*[\"']?([\d\.,]+)", content, default="0"),
                
                # Impostos (Procura padrões como "PIS ... Valor Devido ... 100,00")
                # Nota: O texto do PDF pode estar bagunçado, tentamos pegar o número mais próximo da tag
                "pis_devido": safe_extract(r"PIS.*?Valor Devido.*?([\d\.,]+)", content, default="0"),
                "cofins_devido": safe_extract(r"COFINS.*?Valor Devido.*?([\d\.,]+)", content, default="0"),
            }
            
            item["descricao"] = clean_description(item["descricao"])
            data["itens"].append(item)
    else:
        # Fallback caso o split não funcione (ex: layout diferente)
        st.warning("Não foi possível separar os itens automaticamente. Verifique se o PDF contém 'ITENS DA DUIMP'.")

    return data

# --- LÓGICA DE GERAÇÃO DO XML ---

def create_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")

    # --- Loop Itens (Adições) ---
    for item in data["itens"]:
        adicao = ET.SubElement(duimp, "adicao")
        
        # Preenchimento seguro com zeros
        ET.SubElement(adicao, "cideValorAliquotaEspecifica").text = "0"*11
        ET.SubElement(adicao, "cideValorDevido").text = "0"*15
        ET.SubElement(adicao, "cideValorRecolher").text = "0"*15
        
        # Códigos fixos do seu exemplo
        ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
        ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
        
        # COFINS
        ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965"
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_xml_number(item["cofins_devido"], 15)
        
        # Condição de Venda
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
        ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
        ET.SubElement(adicao, "condicaoVendaValorMoeda").text = format_xml_number(item["valor_total_moeda"], 15)
        
        # Dados Mercadoria
        ET.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
        ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item["ncm"]
        ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_xml_number(item["peso_liquido"], 15)
        
        # Tag <mercadoria>
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(mercadoria, "numeroSequencialItem").text = item["numero_adicao"][-2:]
        ET.SubElement(mercadoria, "quantidade").text = format_xml_number(item["quantidade"], 14)
        ET.SubElement(mercadoria, "unidadeMedida").text = "UNIDADE" # Padrão, pode extrair se variar
        ET.SubElement(mercadoria, "valorUnitario").text = format_xml_number(item["valor_unitario"], 20)
        
        # Identificação
        ET.SubElement(adicao, "numeroAdicao").text = item["numero_adicao"]
        # Limpa o numero da duimp para caber no campo (remove 25BR e limita caracteres)
        clean_duimp = data["header"]["numero_duimp"].replace("25BR", "")[:10]
        ET.SubElement(adicao, "numeroDUIMP").text = clean_duimp if clean_duimp else "0000000000"
        
        # PIS
        ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_xml_number(item["pis_devido"], 15)
        
        ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    # --- Dados Globais (Irmãos das Adições) ---
    
    # Armazem
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
    
    # Importador
    ET.SubElement(duimp, "importadorNome").text = data["header"]["importador_nome"]
    ET.SubElement(duimp, "importadorNumero").text = data["header"]["cnpj"]
    
    # Informação Complementar
    info = ET.SubElement(duimp, "informacaoComplementar")
    info_text = f"PROCESSO: {data['header']['numero_processo']}\n"
    info_text += f"IMPORTADOR: {data['header']['importador_nome']}\n"
    info_text += "GERADO AUTOMATICAMENTE VIA STREAMLIT"
    info.text = info_text
    
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["numero_duimp"]
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)

    return root

# --- INTERFACE ---

def main():
    st.set_page_config(page_title="Gerador XML DUIMP (Blindado)", layout="wide")
    st.title("Gerador de XML DUIMP (V2 - Safe Mode)")
    
    st.markdown("""
    **Instruções:** Carregue o PDF "Extrato de conferência". 
    O sistema irá ignorar campos vazios em vez de travar e gerará o XML no layout do sistema.
    """)

    uploaded_file = st.file_uploader("Carregar PDF", type="pdf")

    if uploaded_file:
        if st.button("Gerar XML"):
            with st.spinner("Processando..."):
                try:
                    data = parse_pdf(uploaded_file)
                    
                    if not data["itens"]:
                        st.warning("Nenhum item foi encontrado. O layout do PDF pode ser imagem (scaneado)? Este script requer PDF de texto selecionável.")
                    else:
                        st.info(f"Processo: {data['header']['numero_processo']} | Itens encontrados: {len(data['itens'])}")
                        
                        xml_root = create_xml(data)
                        
                        # Pretty Print
                        xml_str = ET.tostring(xml_root, 'utf-8')
                        parsed_xml = minidom.parseString(xml_str)
                        pretty_xml = parsed_xml.toprettyxml(indent="    ")
                        
                        st.download_button(
                            "📥 Baixar XML Corrigido",
                            pretty_xml,
                            f"DUIMP_{data['header'].get('numero_processo', 'novo')}.xml",
                            "text/xml"
                        )
                        
                        with st.expander("Ver Dados Extraídos"):
                            st.json(data)

                except Exception as e:
                    st.error(f"Erro inesperado: {str(e)}")
                    st.write("Detalhes do erro para suporte:", e)

if __name__ == "__main__":
    main()
