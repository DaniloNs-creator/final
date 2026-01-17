import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Extrator DUIMP Profissional", layout="wide")

# --- CLASSES DE UTILIDADE E FORMATAÇÃO ---
class Utils:
    @staticmethod
    def format_money_xml(value_str, length=15):
        """Limpa R$, pontos e vírgulas e formata para XML (sem decimal, zeros a esquerda)"""
        if not value_str: return "0" * length
        # Remove caracteres não numéricos exceto virgula se houver para referencia
        # Assumindo formato brasileiro 1.000,00
        clean = re.sub(r'[^\d]', '', value_str)
        return clean.zfill(length)

    @staticmethod
    def format_weight_xml(value_str, length=14):
        """Formata peso para 5 casas decimais implícitas (padrão Siscomex)"""
        if not value_str: return "0" * length
        clean = re.sub(r'[^\d]', '', value_str)
        return clean.zfill(length)

    @staticmethod
    def clean_text(text):
        if not text: return ""
        return " ".join(text.split()).upper()

    @staticmethod
    def get_code_from_lookup(key, lookup_dict, default="000"):
        """Busca o código baseado no texto extraído (ex: 'ITALIA' -> '386')"""
        if not key: return default
        # Normaliza chave para busca
        key_norm = Utils.clean_text(key)
        for k, v in lookup_dict.items():
            if k in key_norm:
                return v
        return default

# --- LOOKUPS (TABELAS DE DOMÍNIO OBRIGATÓRIAS) ---
# O PDF traz o NOME, o XML exige o CÓDIGO.
LOOKUPS = {
    "PAISES": {"ITALIA": "386", "BRASIL": "105", "ESTADOS UNIDOS": "249", "CINGAPURA": "741", "ALEMANHA": "023"},
    "MOEDAS": {"EURO": "978", "DOLAR": "220", "REAL": "790"},
    "VIAS": {"MARITIMA": "01", "AEREA": "04", "RODOVIARIA": "10"},
    "RECINTOS": {"TCP": "9801303"},
    "INCOTERMS": {"FCA": "FCA", "EXW": "EXW", "FOB": "FOB", "CIF": "CIF"}
}

# --- EXTRATOR INTELIGENTE ---
class PdfExtractor:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.text = ""
        self.data = {
            "capa": {},
            "adicoes": []
        }

    def load_pdf(self):
        with pdfplumber.open(self.pdf_file) as pdf:
            all_text = []
            for page in pdf.pages:
                all_text.append(page.extract_text())
            self.text = "\n".join(all_text)
            
    def extract_field(self, regex_pattern, text_block=None, default=""):
        """Busca um valor usando Regex. Se text_block não for passado, usa o texto completo."""
        source = text_block if text_block else self.text
        match = re.search(regex_pattern, source, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
        return default

    def run_extraction(self):
        # 1. DADOS DE CAPA (HEADER)
        self.data['capa']['numero_duimp'] = self.extract_field(r"DUIMP[:\s]*(\d[\d\.-]*)").replace('.', '').replace('-', '')
        self.data['capa']['data_registro'] = self.extract_field(r"Data de Registro[:\s]*(\d{2}/\d{2}/\d{4})").replace('/', '')
        self.data['capa']['importador_nome'] = self.extract_field(r"Importador[:\s]*(.*)")
        self.data['capa']['importador_cnpj'] = self.extract_field(r"CNPJ[:\s]*([\d\./-]+)").replace('.', '').replace('/', '').replace('-', '')
        
        # Logística Capa
        self.data['capa']['peso_bruto'] = self.extract_field(r"Peso Bruto[:\s]*([\d,\.]+)").replace(',', '').replace('.', '')
        self.data['capa']['peso_liquido'] = self.extract_field(r"Peso Líquido Total[:\s]*([\d,\.]+)").replace(',', '').replace('.', '')
        self.data['capa']['navio'] = self.extract_field(r"Navio[:\s]*(.*)")
        self.data['capa']['chegada'] = self.extract_field(r"Chegada[:\s]*(\d{2}/\d{2}/\d{4})").replace('/', '')
        
        # Valores Totais Capa
        self.data['capa']['valor_fob'] = self.extract_field(r"Valor FOB Total[:\s]*([\d,\.]+)").replace('.', '').replace(',', '')
        self.data['capa']['valor_frete'] = self.extract_field(r"Valor Frete Total[:\s]*([\d,\.]+)").replace('.', '').replace(',', '')
        self.data['capa']['valor_seguro'] = self.extract_field(r"Valor Seguro Total[:\s]*([\d,\.]+)").replace('.', '').replace(',', '')

        # 2. ADIÇÕES (LOOP INTELIGENTE)
        # Identifica onde começam as adições. Geralmente padrão "Adição: 001" ou "Item 001"
        # Quebra o texto em blocos de adição
        adicoes_blocks = re.split(r"(?:Adição|Item)\s*[:#]?\s*(\d{3})", self.text)
        
        # O split gera [lixo_inicial, num_001, texto_001, num_002, texto_002...]
        if len(adicoes_blocks) > 1:
            # Pula o primeiro elemento (cabeçalho antes da primeira adição)
            for i in range(1, len(adicoes_blocks), 2):
                num_adicao = adicoes_blocks[i]
                block_text = adicoes_blocks[i+1]
                
                adicao = {
                    "numero": num_adicao,
                    "ncm": self.extract_field(r"NCM[:\s]*(\d[\d\.]*)", block_text).replace('.', ''),
                    "incoterm": self.extract_field(r"Incoterm[:\s]*([A-Z]{3})", block_text, "FCA"),
                    "valor_mercadoria": self.extract_field(r"Valor Mercadoria[:\s]*([\d,\.]+)", block_text),
                    "peso_liquido": self.extract_field(r"Peso Líquido[:\s]*([\d,\.]+)", block_text),
                    "quantidade": self.extract_field(r"Quantidade[:\s]*([\d,\.]+)", block_text),
                    "descricao": self.extract_field(r"Descrição[:\s]*(.*?)(?:\n|$)", block_text),
                    "pais_origem": self.extract_field(r"País de Origem[:\s]*(.*)", block_text),
                    
                    # Tributos Específicos da Adição
                    "ii_recolher": self.extract_field(r"II.*?A Recolher[:\s]*([\d,\.]+)", block_text),
                    "ipi_recolher": self.extract_field(r"IPI.*?A Recolher[:\s]*([\d,\.]+)", block_text),
                    "pis_recolher": self.extract_field(r"PIS.*?A Recolher[:\s]*([\d,\.]+)", block_text),
                    "cofins_recolher": self.extract_field(r"COFINS.*?A Recolher[:\s]*([\d,\.]+)", block_text)
                }
                
                # Tratamento de Moeda da Adição (Busca se é Euro ou Dolar no texto)
                moeda_nome = self.extract_field(r"Moeda[:\s]*([A-Z]+)", block_text, "EURO")
                adicao["moeda_nome"] = moeda_nome
                adicao["moeda_codigo"] = Utils.get_code_from_lookup(moeda_nome, LOOKUPS["MOEDAS"], "978")
                
                self.data['adicoes'].append(adicao)

# --- GERADOR XML ---
class XmlBuilder:
    def __init__(self, data):
        self.data = data
        self.root = ET.Element("ListaDeclaracoes")
        self.duimp = ET.SubElement(self.root, "duimp")

    def build(self):
        d = self.data
        capa = d['capa']

        # Loop Adições
        for item in d['adicoes']:
            adi = ET.SubElement(self.duimp, "adicao")
            
            # --- Acréscimo ---
            acr = ET.SubElement(adi, "acrescimo")
            ET.SubElement(acr, "codigoAcrescimo").text = "17" # Fixo ou extrair se variável
            ET.SubElement(acr, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
            ET.SubElement(acr, "moedaNegociadaCodigo").text = item["moeda_codigo"]
            ET.SubElement(acr, "moedaNegociadaNome").text = item["moeda_nome"] + "/COM.EUROPEIA"
            ET.SubElement(acr, "valorMoedaNegociada").text = Utils.format_money_xml("0") # Extrair se disponível
            ET.SubElement(acr, "valorReais").text = Utils.format_money_xml("0")

            # --- Condição de Venda ---
            ET.SubElement(adi, "condicaoVendaIncoterm").text = item["incoterm"]
            ET.SubElement(adi, "condicaoVendaLocal").text = "BRUGNERA" # Ideal extrair do PDF
            ET.SubElement(adi, "condicaoVendaMetodoValoracaoCodigo").text = "01"
            ET.SubElement(adi, "condicaoVendaMetodoValoracaoNome").text = "METODO 1 - ART. 1 DO ACORDO"
            ET.SubElement(adi, "condicaoVendaMoedaCodigo").text = item["moeda_codigo"]
            ET.SubElement(adi, "condicaoVendaMoedaNome").text = item["moeda_nome"]
            ET.SubElement(adi, "condicaoVendaValorMoeda").text = Utils.format_money_xml(item.get("valor_mercadoria"))
            ET.SubElement(adi, "condicaoVendaValorReais").text = Utils.format_money_xml(item.get("valor_mercadoria")) # Ajustar câmbio se necessário

            # --- Dados Mercadoria ---
            ET.SubElement(adi, "dadosMercadoriaAplicacao").text = "REVENDA"
            ET.SubElement(adi, "dadosMercadoriaCodigoNcm").text = item["ncm"]
            ET.SubElement(adi, "dadosMercadoriaCondicao").text = "NOVA"
            ET.SubElement(adi, "dadosMercadoriaMedidaEstatisticaQuantidade").text = Utils.format_weight_xml(item["quantidade"])
            ET.SubElement(adi, "dadosMercadoriaMedidaEstatisticaUnidade").text = "QUILOGRAMA LIQUIDO"
            ET.SubElement(adi, "dadosMercadoriaNomeNcm").text = item["descricao"][:50] # Truncado para caber
            ET.SubElement(adi, "dadosMercadoriaPesoLiquido").text = Utils.format_weight_xml(item["peso_liquido"])

            # --- Fornecedor (Fixo ou Extrair se houver campo "Fornecedor" na adição) ---
            ET.SubElement(adi, "fornecedorCidade").text = "BRUGNERA"
            ET.SubElement(adi, "fornecedorLogradouro").text = "VIALE EUROPA"
            ET.SubElement(adi, "fornecedorNome").text = "ITALIANA FERRAMENTA S.R.L."
            ET.SubElement(adi, "fornecedorNumero").text = "17"

            # --- Tributos (II, IPI, PIS, COFINS) ---
            # II
            ET.SubElement(adi, "iiAliquotaValorRecolher").text = Utils.format_money_xml(item["ii_recolher"])
            ET.SubElement(adi, "iiRegimeTributacaoCodigo").text = "1"
            ET.SubElement(adi, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
            
            # IPI
            ET.SubElement(adi, "ipiAliquotaValorRecolher").text = Utils.format_money_xml(item["ipi_recolher"])
            ET.SubElement(adi, "ipiRegimeTributacaoCodigo").text = "4"
            
            # PIS
            ET.SubElement(adi, "pisPasepAliquotaValorRecolher").text = Utils.format_money_xml(item["pis_recolher"])
            
            # COFINS
            ET.SubElement(adi, "cofinsAliquotaValorRecolher").text = Utils.format_money_xml(item["cofins_recolher"])

            # Tags Identificadoras da Adição
            ET.SubElement(adi, "numeroAdicao").text = item["numero"]
            ET.SubElement(adi, "numeroDUIMP").text = capa.get("numero_duimp", "0000000000")
            
            # País Origem/Aquisição
            pais_cod = Utils.get_code_from_lookup(item.get("pais_origem", "ITALIA"), LOOKUPS["PAISES"])
            ET.SubElement(adi, "paisAquisicaoMercadoriaCodigo").text = pais_cod
            ET.SubElement(adi, "paisAquisicaoMercadoriaNome").text = item.get("pais_origem", "ITALIA").upper()
            ET.SubElement(adi, "paisOrigemMercadoriaCodigo").text = pais_cod
            ET.SubElement(adi, "paisOrigemMercadoriaNome").text = item.get("pais_origem", "ITALIA").upper()

            # --- Mercadoria Detalhe ---
            merc = ET.SubElement(adi, "mercadoria")
            ET.SubElement(merc, "descricaoMercadoria").text = Utils.clean_text(item["descricao"])
            ET.SubElement(merc, "numeroSequencialItem").text = "01"
            ET.SubElement(merc, "quantidade").text = Utils.format_weight_xml(item["quantidade"])
            ET.SubElement(merc, "unidadeMedida").text = "PECA" # Extrair se variável
            ET.SubElement(merc, "valorUnitario").text = Utils.format_money_xml("0", 20) # Calcular: Valor / Qtd

        # --- DADOS GERAIS DUIMP (FORA DO LOOP) ---
        ET.SubElement(self.duimp, "numeroDUIMP").text = capa.get("numero_duimp")
        ET.SubElement(self.duimp, "dataRegistro").text = capa.get("data_registro")
        ET.SubElement(self.duimp, "cargaPesoBruto").text = Utils.format_weight_xml(capa.get("peso_bruto"))
        ET.SubElement(self.duimp, "cargaPesoLiquido").text = Utils.format_weight_xml(capa.get("peso_liquido"))
        
        imp = ET.SubElement(self.duimp, "importadorNome")
        imp.text = capa.get("importador_nome")
        
        ET.SubElement(self.duimp, "freteTotalReais").text = Utils.format_money_xml(capa.get("valor_frete"))
        
        # Tags de Infraestrutura (Armazem, etc - Se não estiver no PDF, usar o padrão do projeto)
        armazem = ET.SubElement(self.duimp, "armazem")
        ET.SubElement(armazem, "nomeArmazem").text = "TCP" # Padrão mencionado
        
        return ET.tostring(self.root, encoding='utf-8')

# --- INTERFACE ---
st.title("🏭 Conversor Layout DUIMP (PDF -> XML Full)")

uploaded_file = st.file_uploader("Carregar PDF Padrão DUIMP", type="pdf")

if uploaded_file:
    try:
        # 1. Extrair
        extractor = PdfExtractor(uploaded_file)
        extractor.load_pdf()
        extractor.run_extraction()
        
        st.info(f"Dados Extraídos: {len(extractor.data['adicoes'])} itens encontrados.")
        # st.json(extractor.data) # Debug: Ver o que foi extraído

        # 2. Gerar XML
        builder = XmlBuilder(extractor.data)
        xml_bytes = builder.build()
        
        # 3. Formatar (Pretty Print)
        parsed = minidom.parseString(xml_bytes)
        xml_str = parsed.toprettyxml(indent="    ")

        st.success("XML Gerado com sucesso!")
        st.download_button("Baixar XML", xml_str, "duimp_output.xml", "application/xml")
        
        with st.expander("Ver XML"):
            st.code(xml_str, language='xml')

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
