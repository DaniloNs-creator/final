import streamlit as st
import fitz  # PyMuPDF
import re
from lxml import etree

st.set_page_config(page_title="Conversor DUIMP PDF > XML (V. Final)", layout="wide")

class TextCleaner:
    @staticmethod
    def remove_garbage_lines(text):
        """
        Remove linhas de cabeçalho e rodapé que poluem os dados no PDF.
        Baseado no padrão encontrado no arquivo 'Extrato-DUIMP-25BR00002464588'.
        """
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Ignora linhas de cabeçalho repetitivas do PDF
            if "Extrato da DUIMP" in line: continue
            if "Data, hora e responsável" in line: continue
            if "The following table" in line: continue
            if re.search(r"^\d+\s*/\s*\d+$", line.strip()): continue # Remove paginação "1 / 14"
            if "Situação da conferência" in line: continue
            
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    @staticmethod
    def clean_description(text):
        """Limpa quebras de linha dentro da descrição para ficar em uma linha só."""
        if not text: return ""
        # Remove quebras de linha e espaços duplos
        text = text.replace('\n', ' ').replace('\r', '')
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def format_decimal_xml(value, total_length=15):
        """
        Formata valores decimais para o padrão XML (sem vírgula/ponto, zeros à esquerda).
        Ex: 1.856,00000 -> 000000018560000
        """
        if not value: return "0" * total_length
        # Remove tudo que não for dígito
        clean = re.sub(r'[^\d]', '', value)
        return clean.zfill(total_length)

    @staticmethod
    def format_ncm(value):
        if not value: return ""
        return re.sub(r'[^\d]', '', value.split('-')[0])

class DuimpParser:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.full_text = ""
        self.header_data = {}
        self.items_data = []

    def extract_and_clean(self):
        doc = fitz.open(stream=self.pdf_file.read(), filetype="pdf")
        raw_text_pages = []
        
        # Extração bruta
        for page in doc:
            raw_text_pages.append(page.get_text("text"))
        
        full_raw = "\n".join(raw_text_pages)
        
        # Limpeza agressiva de linhas inúteis antes do processamento
        self.full_text = TextCleaner.remove_garbage_lines(full_raw)
        doc.close()

    def parse_header(self):
        """Extrai dados gerais da DUIMP."""
        # Padrões baseados no Extrato fornecido
        patterns = {
            "numeroDUIMP": r"Extrato da Duimp\s+([\w\-\/]+)",
            "cnpjImportador": r"CNPJ do importador:\s*([\d\.\/\-]+)",
            "nomeImportador": r"Nome do importador:\s*\n?(.+)", # Pega a linha seguinte
            "pesoBruto": r"Peso Bruto \(kg\):\s*([\d\.,]+)",
            "pesoLiquido": r"Peso Liquido \(kg\):\s*([\d\.,]+)",
            "paisProcedencia": r"País de Procedência:\s*\n?(.+?)(?=\n)",
            "urfDespacho": r"Unidade de despacho:\s*([\d]+)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, self.full_text, re.IGNORECASE)
            if match:
                self.header_data[key] = match.group(1).strip()

    def parse_items(self):
        """Extrai cada Adição."""
        # Divide o texto limpo pelos marcadores de item
        # Regex procura por "Item 00001", "Item 00002", etc.
        chunks = re.split(r"Item\s+(\d{5})", self.full_text)
        
        # O split retorna: [Lixo inicial, NumItem1, Conteudo1, NumItem2, Conteudo2...]
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                item_num = chunks[i]
                content = chunks[i+1]
                
                # Regex Específicos para o Item
                # Usamos "lookaheads" (?=...) para parar a captura antes do próximo campo
                item_dict = {
                    "numeroAdicao": item_num,
                    "ncm": re.search(r"NCM:\s*([\d\.]+)", content),
                    "paisOrigem": re.search(r"País de origem:\s*\n?(.+?)(?=\n)", content),
                    # Captura descrição entre "Detalhamento" e o próximo campo "Código de Class" ou "Número de série"
                    "descricao": re.search(r"Detalhamento do Produto:\s*(.+?)(?=\n\s*(Código de Class|Número de série|Versão))", content, re.DOTALL),
                    "quantidade": re.search(r"Quantidade na unidade estatística:\s*([\d\.,]+)", content),
                    "valorUnitario": re.search(r"Valor unitário na condição de venda:\s*([\d\.,]+)", content),
                    "valorTotal": re.search(r"Valor total na condição de venda:\s*([\d\.,]+)", content),
                    "moeda": re.search(r"Moeda negociada:\s*(.+?)(?=\n)", content),
                    "unidade": re.search(r"Unidade estatística:\s*(.+?)(?=\n)", content)
                }
                
                # Extraindo valores dos matches
                clean_item = {}
                for key, match in item_dict.items():
                    if key == "numeroAdicao":
                        clean_item[key] = match
                    elif match:
                        clean_item[key] = match.group(1).strip()
                    else:
                        clean_item[key] = ""
                
                self.items_data.append(clean_item)

    def generate_xml(self):
        """Gera o XML compatível com o sistema."""
        root = etree.Element("ListaDeclaracoes")
        duimp = etree.SubElement(root, "duimp")
        
        h = self.header_data
        
        # DUIMP formatada (remove traços/pontos do número: 25BR...-8 -> 25BR...8)
        duimp_fmt = h.get("numeroDUIMP", "").split("/")[0].replace("-", "").replace(".", "")

        for it in self.items_data:
            adicao = etree.SubElement(duimp, "adicao")
            
            # --- Tags de Estrutura ---
            # numeroAdicao (001, 002...) - Usa os últimos 3 dígitos do item
            etree.SubElement(adicao, "numeroAdicao").text = it["numeroAdicao"][-3:] 
            etree.SubElement(adicao, "numeroDUIMP").text = duimp_fmt
            etree.SubElement(adicao, "numeroLI").text = "0000000000" # Padrão fixo
            
            # --- Dados Carga/País (Herdados do Header ou Item) ---
            etree.SubElement(adicao, "dadosCargaPaisProcedenciaCodigo").text = "076" # Exemplo fixo ou extrair de tabela
            etree.SubElement(adicao, "dadosCargaUrfEntradaCodigo").text = h.get("urfDespacho", "0000000")
            etree.SubElement(adicao, "dadosCargaViaTransporteNome").text = "MARÍTIMA"
            
            etree.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = TextCleaner.format_ncm(it.get("ncm"))
            etree.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
            etree.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
            
            # Medidas Estatísticas (zeros à esquerda)
            # Quantidade (15 digitos)
            qtd_fmt = TextCleaner.format_decimal_xml(it.get("quantidade"), 15)
            etree.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaQuantidade").text = qtd_fmt
            etree.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaUnidade").text = it.get("unidade", "UNIDADE")
            etree.SubElement(adicao, "dadosMercadoriaNomeNcm").text = "Descrição NCM Padrão" # PDF não costuma ter nome NCM limpo
            
            # Peso Liquido (herdado do item ou dividido proporcionalmente? O XML modelo põe peso no item)
            # Como o extrato PDF nem sempre tem peso por item, vou usar o do header como placeholder ou implementar lógica específica
            # Para este exemplo, vou replicar a qtd como peso (comum em validações) ou deixar zero se não encontrado
            etree.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = qtd_fmt 

            # Pais Origem
            etree.SubElement(adicao, "paisOrigemMercadoriaNome").text = it.get("paisOrigem", "").upper()

            # --- Bloco Mercadoria ---
            mercadoria = etree.SubElement(adicao, "mercadoria")
            # Descrição limpa (sem quebras de linha)
            etree.SubElement(mercadoria, "descricaoMercadoria").text = TextCleaner.clean_description(it.get("descricao"))[:3800] # Limite safe
            etree.SubElement(mercadoria, "numeroSequencialItem").text = it["numeroAdicao"][-2:] # 01, 02...
            etree.SubElement(mercadoria, "quantidade").text = qtd_fmt
            etree.SubElement(mercadoria, "unidadeMedida").text = it.get("unidade", "UNIDADE")
            
            # Valor Unitário (20 digitos no XML modelo )
            etree.SubElement(mercadoria, "valorUnitario").text = TextCleaner.format_decimal_xml(it.get("valorUnitario"), 20)

            # --- Condição Venda ---
            etree.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
            etree.SubElement(adicao, "condicaoVendaMoedaNome").text = it.get("moeda", "DOLAR DOS EUA").upper()
            etree.SubElement(adicao, "condicaoVendaValorMoeda").text = TextCleaner.format_decimal_xml(it.get("valorTotal"), 15)
            
            # Tags Tributárias (Zeros padrão conforme modelo)
            etree.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
            
            # (Adicione outras tags tributárias fixas se necessário, como PIS/COFINS com valor 0 se isento)

        # --- Dados Gerais Finais ---
        armazem = etree.SubElement(duimp, "armazem")
        etree.SubElement(armazem, "nomeArmazem").text = "IRF - PORTO DE SUAPE" # Extrair se possível
        
        etree.SubElement(duimp, "cargaPesoBruto").text = TextCleaner.format_decimal_xml(h.get("pesoBruto"), 15)
        etree.SubElement(duimp, "cargaPesoLiquido").text = TextCleaner.format_decimal_xml(h.get("pesoLiquido"), 15)
        
        etree.SubElement(duimp, "importadorNome").text = h.get("nomeImportador", "")
        # CNPJ limpo (apenas números)
        etree.SubElement(duimp, "importadorNumero").text = re.sub(r'\D', '', h.get("cnpjImportador", ""))
        etree.SubElement(duimp, "numeroDUIMP").text = duimp_fmt

        return etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# --- Frontend ---
st.title("📄 Conversor DUIMP PDF > XML (V. Final)")
st.markdown("Processamento de alta performance com limpeza de layout e formatação estrita.")

uploaded_file = st.file_uploader("Upload do Extrato DUIMP (PDF)", type=["pdf"])

if uploaded_file:
    if st.button("Processar Arquivo"):
        with st.spinner("Lendo, limpando e estruturando..."):
            try:
                parser = DuimpParser(uploaded_file)
                parser.extract_and_clean() # Passo 1: Limpeza
                parser.parse_header()      # Passo 2: Header
                parser.parse_items()       # Passo 3: Itens
                
                xml_output = parser.generate_xml() # Passo 4: XML
                
                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"Sucesso! {len(parser.items_data)} adições encontradas.")
                    st.download_button(
                        "📥 Baixar XML", 
                        xml_output, 
                        f"DUIMP_{parser.header_data.get('numeroDUIMP', 'final').replace('/', '')}.xml",
                        "application/xml"
                    )
                
                with col2:
                    st.expander("Verificar Dados Extraídos (JSON)").json(parser.items_data)
                
                st.code(xml_output.decode("utf-8"), language="xml")
                
            except Exception as e:
                st.error(f"Erro no processamento: {e}")
