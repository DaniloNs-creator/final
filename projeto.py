import streamlit as st
import fitz  # PyMuPDF
import re
from lxml import etree

# Configuração da Página
st.set_page_config(page_title="Conversor DUIMP PDF > XML (Formatado)", layout="wide")

class XmlFormatter:
    """Classe auxiliar para formatar dados conforme o padrão do XML modelo (M-DUIMP-8686868686.xml)"""
    
    @staticmethod
    def clean_text(text):
        """Remove quebras de linha e espaços extras."""
        if text:
            # Substitui quebras de linha por espaço e remove espaços duplicados
            return " ".join(text.split()).strip()
        return ""

    @staticmethod
    def format_number_xml(value, length=15):
        """
        Transforma '1.550,08' em '000000000155008' (padrão Siscomex/DUIMP).
        Remove pontos e vírgulas e preenche com zeros à esquerda.
        """
        if not value:
            return "0" * length
        
        # Remove caracteres não numéricos
        clean_val = re.sub(r'[^\d]', '', value)
        
        # Preenche com zeros à esquerda até o tamanho desejado
        return clean_val.zfill(length)

    @staticmethod
    def format_ncm(value):
        """Remove pontos do NCM: '3926.30.00' -> '39263000'"""
        if not value:
            return ""
        # Pega apenas os primeiros 8 dígitos numéricos
        clean = re.sub(r'[^\d]', '', value)
        return clean[:8]

    @staticmethod
    def format_cnpj(value):
        """Remove pontuação do CNPJ"""
        if not value:
            return ""
        return re.sub(r'[^\d]', '', value)

class DuimpParser:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.full_text = ""
        self.data = {
            "header": {},
            "adicoes": []
        }

    def extract_text_fast(self):
        """Extrai texto usando PyMuPDF."""
        doc = fitz.open(stream=self.pdf_file.read(), filetype="pdf")
        text_parts = []
        
        progress_bar = st.progress(0)
        total_pages = len(doc)
        
        for i, page in enumerate(doc):
            text_parts.append(page.get_text("text"))
            if i % 10 == 0:
                progress_bar.progress((i + 1) / total_pages)
                
        progress_bar.progress(100)
        self.full_text = "\n".join(text_parts)
        doc.close()

    def parse_header(self):
        """Extrai dados da capa da DUIMP."""
        text = self.full_text
        
        # Regex baseada no seu PDF (Extrato-DUIMP...) [cite: 1, 16, 17, 34, 134]
        patterns = {
            "numeroDUIMP": r"Extrato da DUIMP\s+([\w\-\/]+)",
            "cnpjImportador": r"CNPJ do importador:\s*\n\s*([\d\.\/\-]+)",
            "nomeImportador": r"Nome do importador:\s*\n\s*(.+)",
            "pesoBruto": r"Peso Bruto \(kg\):\s*\n\s*\"?([\d\.]+,\d+)\"?",
            "pesoLiquido": r"Peso Liquido \(kg\):\s*\n\s*\"?([\d\.]+,\d+)\"?",
            "paisProcedencia": r"País de Procedência:\s*\n\s*\"?([^\"]+)\"?",
            "unidadeDespacho": r"Unidade de despacho:\s*\n\s*([\d]+)" # Pega só o código numérico
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                raw_value = match.group(1).strip().replace('"', '')
                self.data["header"][key] = XmlFormatter.clean_text(raw_value)

    def parse_items(self):
        """Extrai as adições com lógica de limpeza agressiva."""
        # Divide o texto pelos itens
        item_chunks = re.split(r"Extrato da Duimp .+ : Item (\d+)", self.full_text)
        
        if len(item_chunks) > 1:
            for i in range(1, len(item_chunks), 2):
                item_num = item_chunks[i]
                content = item_chunks[i+1]
                
                adicao = {
                    "numeroAdicao": item_num.zfill(3), # Ex: 001
                    "mercadoria": {}
                }

                # Regex ajustados para parar no próximo rótulo e evitar capturar texto demais
                # Baseado nos campos do PDF [cite: 54, 86, 90, 94, 107]
                item_patterns = {
                    "codigoNcm": r"NCM:\s*\n\s*([\d\.]+)",
                    "paisOrigem": r"País de origem:\s*\n\s*(.+)",
                    "valorTotal": r"Valor total na condição de venda:\s*\n\s*([\d\.,]+)",
                    "valorUnitario": r"Valor unitário na condição de venda:\s*\n\s*([\d\.,]+)",
                    "quantidade": r"Quantidade na unidade estatística:\s*\n\s*([\d\.,]+)",
                    "unidadeMedida": r"Unidade estatística:\s*\n\s*(.+)",
                    # O detalhamento pega tudo até encontrar "Número de Identificação" ou "Código de Class"
                    "descricaoMercadoria": r"Detalhamento do Produto:\s*\n\s*(.+?)(?=\n\s*(?:Número de Identificação|Código de Class|Versão))",
                    "moeda": r"Moeda negociada:\s*\n\s*(.+)"
                }

                for key, pattern in item_patterns.items():
                    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
                    if match:
                        raw_value = match.group(1)
                        clean_val = XmlFormatter.clean_text(raw_value)
                        
                        if key == "descricaoMercadoria":
                            adicao["mercadoria"][key] = clean_val
                        else:
                            adicao[key] = clean_val
                
                self.data["adicoes"].append(adicao)

    def generate_xml(self):
        """Gera o XML seguindo a estrutura do arquivo M-DUIMP-8686868686.xml."""
        
        root = etree.Element("ListaDeclaracoes")
        duimp = etree.SubElement(root, "duimp")

        h = self.data["header"]
        
        # --- Iteração das Adições (Estrutura Principal) ---
        for item in self.data["adicoes"]:
            adicao_node = etree.SubElement(duimp, "adicao")
            
            # --- Campos Básicos da Adição ---
            # numeroAdicao: 001
            etree.SubElement(adicao_node, "numeroAdicao").text = item.get("numeroAdicao", "001")
            
            # numeroDUIMP: Limpo (Ex: 26BR00000011160)
            raw_duimp = h.get("numeroDUIMP", "").split("/")[0]
            etree.SubElement(adicao_node, "numeroDUIMP").text = XmlFormatter.format_cnpj(raw_duimp)

            # --- Dados de Carga (Herança do Cabeçalho) ---
            etree.SubElement(adicao_node, "dadosCargaPaisProcedenciaCodigo").text = "000" # Placeholder padrão ou extrair tabela de-para
            # País Procedência limpo [cite: 34]
            etree.SubElement(adicao_node, "dadosCargaPaisProcedenciaNome").text = h.get("paisProcedencia", "")
            etree.SubElement(adicao_node, "dadosCargaUrfEntradaCodigo").text = h.get("unidadeDespacho", "0000000")

            # --- Mercadoria (Nó Interno) ---
            # Estrutura baseada no modelo XML
            etree.SubElement(adicao_node, "dadosMercadoriaCodigoNcm").text = XmlFormatter.format_ncm(item.get("codigoNcm"))
            etree.SubElement(adicao_node, "dadosMercadoriaMedidaEstatisticaUnidade").text = item.get("unidadeMedida", "UNIDADE")
            # Quantidade formatada padrão XML (Ex: 00000004584200)
            etree.SubElement(adicao_node, "dadosMercadoriaMedidaEstatisticaQuantidade").text = XmlFormatter.format_number_xml(item.get("quantidade"), 14)
            
            # Nó <mercadoria>
            mercadoria_node = etree.SubElement(adicao_node, "mercadoria")
            # Descrição limpa e em uma linha
            etree.SubElement(mercadoria_node, "descricaoMercadoria").text = item["mercadoria"].get("descricaoMercadoria", "")
            etree.SubElement(mercadoria_node, "numeroSequencialItem").text = "01" # Default por item
            etree.SubElement(mercadoria_node, "quantidade").text = XmlFormatter.format_number_xml(item.get("quantidade"), 14)
            etree.SubElement(mercadoria_node, "unidadeMedida").text = "PECA" # Ou extrair unidade comercial
            etree.SubElement(mercadoria_node, "valorUnitario").text = XmlFormatter.format_number_xml(item.get("valorUnitario"), 20) # Valor unitário costuma ser maior no XML modelo

            # --- Valores Financeiros ---
            # Condição de venda (Moeda e Reais)
            etree.SubElement(adicao_node, "condicaoVendaMoedaNome").text = item.get("moeda", "")
            # No XML modelo, valorMoeda e valorReais são formatados com zeros
            etree.SubElement(adicao_node, "condicaoVendaValorMoeda").text = XmlFormatter.format_number_xml(item.get("valorTotal"), 15)
            # Nota: O PDF Extrato pode não ter o valor convertido em Reais por item explícito na mesma linha, 
            # aqui estou usando o valor moeda como placeholder ou você precisaria calcular se tiver a taxa.
            # Vou deixar o valor moeda duplicado para manter a tag preenchida conforme solicitado.
            etree.SubElement(adicao_node, "condicaoVendaValorReais").text = XmlFormatter.format_number_xml(item.get("valorTotal"), 15)

            # País de Origem
            etree.SubElement(adicao_node, "paisOrigemMercadoriaNome").text = item.get("paisOrigem", "")

        # --- Dados Gerais (Tags Soltas no final ou início do duimp) ---
        # Armazém
        armazem = etree.SubElement(duimp, "armazem")
        etree.SubElement(armazem, "nomeArmazem").text = "PADRAO" # Ajustar se houver no PDF
        
        # Pesos (Formatados com zeros) [cite: 34]
        etree.SubElement(duimp, "cargaPesoBruto").text = XmlFormatter.format_number_xml(h.get("pesoBruto"), 15)
        etree.SubElement(duimp, "cargaPesoLiquido").text = XmlFormatter.format_number_xml(h.get("pesoLiquido"), 15)
        
        # Importador [cite: 16, 17]
        etree.SubElement(duimp, "importadorNome").text = h.get("nomeImportador", "")
        etree.SubElement(duimp, "importadorNumero").text = XmlFormatter.format_cnpj(h.get("cnpjImportador"))

        return etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# --- Interface Streamlit ---

st.title("📄 Conversor DUIMP PDF > XML (Layout Rígido)")
st.markdown("Extração limpa e formatada conforme padrão XML de importação.")

uploaded_file = st.file_uploader("Arraste seu arquivo PDF aqui", type=["pdf"])

if uploaded_file is not None:
    if st.button("Converter"):
        with st.spinner("Processando..."):
            try:
                parser = DuimpParser(uploaded_file)
                parser.extract_text_fast()
                parser.parse_header()
                parser.parse_items()
                
                xml_content = parser.generate_xml()
                
                st.success("Conversão realizada com sucesso!")
                
                # Exibe prévia do JSON interno para conferência
                with st.expander("Ver Dados Extraídos (Depuração)"):
                    st.json(parser.data)

                # Download
                st.download_button(
                    label="📥 Baixar XML",
                    data=xml_content,
                    file_name="DUIMP_Processada.xml",
                    mime="application/xml"
                )
                
                # Visualização do XML
                st.text_area("XML Gerado:", value=xml_content.decode("utf-8"), height=400)
                
            except Exception as e:
                st.error(f"Erro: {str(e)}")
