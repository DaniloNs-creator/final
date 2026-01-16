import streamlit as st
import fitz  # PyMuPDF
import re
from lxml import etree

# --- Configuração da Página ---
st.set_page_config(page_title="Conversor DUIMP XML (Layout Mapeado)", layout="wide")

# --- LISTA MESTRA DE TAGS (ORDEM ESTRITA DO MAPEAMENTO) ---
# Qualquer tag fora desta lista não será gerada. A ordem é sagrada.

TAGS_ADICAO = [
    "acrescimo", "cideValorAliquotaEspecifica", "cideValorDevido", "cideValorRecolher",
    "codigoRelacaoCompradorVendedor", "codigoVinculoCompradorVendedor", "cofinsAliquotaAdValorem",
    "cofinsAliquotaEspecificaQuantidadeUnidade", "cofinsAliquotaEspecificaValor", "cofinsAliquotaReduzida",
    "cofinsAliquotaValorDevido", "cofinsAliquotaValorRecolher", "condicaoVendaIncoterm",
    "condicaoVendaLocal", "condicaoVendaMetodoValoracaoCodigo", "condicaoVendaMetodoValoracaoNome",
    "condicaoVendaMoedaCodigo", "condicaoVendaMoedaNome", "condicaoVendaValorMoeda",
    "condicaoVendaValorReais", "dadosCambiaisCoberturaCambialCodigo", "dadosCambiaisCoberturaCambialNome",
    "dadosCambiaisInstituicaoFinanciadoraCodigo", "dadosCambiaisInstituicaoFinanciadoraNome",
    "dadosCambiaisMotivoSemCoberturaCodigo", "dadosCambiaisMotivoSemCoberturaNome",
    "dadosCambiaisValorRealCambio", "dadosCargaPaisProcedenciaCodigo", "dadosCargaUrfEntradaCodigo",
    "dadosCargaViaTransporteCodigo", "dadosCargaViaTransporteNome", "dadosMercadoriaAplicacao",
    "dadosMercadoriaCodigoNaladiNCCA", "dadosMercadoriaCodigoNaladiSH", "dadosMercadoriaCodigoNcm",
    "dadosMercadoriaCondicao", "dadosMercadoriaDescricaoTipoCertificado", "dadosMercadoriaIndicadorTipoCertificado",
    "dadosMercadoriaMedidaEstatisticaQuantidade", "dadosMercadoriaMedidaEstatisticaUnidade",
    "dadosMercadoriaNomeNcm", "dadosMercadoriaPesoLiquido", "dcrCoeficienteReducao",
    "dcrIdentificacao", "dcrValorDevido", "dcrValorDolar", "dcrValorReal", "dcrValorRecolher",
    "fornecedorCidade", "fornecedorLogradouro", "fornecedorNome", "fornecedorNumero",
    "freteMoedaNegociadaCodigo", "freteMoedaNegociadaNome", "freteValorMoedaNegociada",
    "freteValorReais", "iiAcordoTarifarioTipoCodigo", "iiAliquotaAcordo", "iiAliquotaAdValorem",
    "iiAliquotaPercentualReducao", "iiAliquotaReduzida", "iiAliquotaValorCalculado",
    "iiAliquotaValorDevido", "iiAliquotaValorRecolher", "iiAliquotaValorReduzido",
    "iiBaseCalculo", "iiFundamentoLegalCodigo", "iiMotivoAdmissaoTemporariaCodigo",
    "iiRegimeTributacaoCodigo", "iiRegimeTributacaoNome", "ipiAliquotaAdValorem",
    "ipiAliquotaEspecificaCapacidadeRecipciente", "ipiAliquotaEspecificaQuantidadeUnidadeMedida",
    "ipiAliquotaEspecificaTipoRecipienteCodigo", "ipiAliquotaEspecificaValorUnidadeMedida",
    "ipiAliquotaNotaComplementarTIPI", "ipiAliquotaReduzida", "ipiAliquotaValorDevido",
    "ipiAliquotaValorRecolher", "ipiRegimeTributacaoCodigo", "ipiRegimeTributacaoNome",
    "mercadoria", # Tag complexa (abre sub-nós)
    "numeroAdicao", "numeroDUIMP", "numeroLI", "paisAquisicaoMercadoriaCodigo",
    "paisAquisicaoMercadoriaNome", "paisOrigemMercadoriaCodigo", "paisOrigemMercadoriaNome",
    "pisCofinsBaseCalculoAliquotaICMS", "pisCofinsBaseCalculoFundamentoLegalCodigo",
    "pisCofinsBaseCalculoPercentualReducao", "pisCofinsBaseCalculoValor",
    "pisCofinsFundamentoLegalReducaoCodigo", "pisCofinsRegimeTributacaoCodigo",
    "pisCofinsRegimeTributacaoNome", "pisPasepAliquotaAdValorem",
    "pisPasepAliquotaEspecificaQuantidadeUnidade", "pisPasepAliquotaEspecificaValor",
    "pisPasepAliquotaReduzida", "pisPasepAliquotaValorDevido", "pisPasepAliquotaValorRecolher",
    "icmsBaseCalculoValor", "icmsBaseCalculoAliquota", "icmsBaseCalculoValorImposto",
    "icmsBaseCalculoValorDiferido", "cbsIbsCst", "cbsIbsClasstrib", "cbsBaseCalculoValor",
    "cbsBaseCalculoAliquota", "cbsBaseCalculoAliquotaReducao", "cbsBaseCalculoValorImposto",
    "ibsBaseCalculoValor", "ibsBaseCalculoAliquota", "ibsBaseCalculoAliquotaReducao",
    "ibsBaseCalculoValorImposto", "relacaoCompradorVendedor", "seguroMoedaNegociadaCodigo",
    "seguroMoedaNegociadaNome", "seguroValorMoedaNegociada", "seguroValorReais",
    "sequencialRetificacao", "valorMultaARecolher", "valorMultaARecolherAjustado",
    "valorReaisFreteInternacional", "valorReaisSeguroInternacional", "valorTotalCondicaoVenda",
    "vinculoCompradorVendedor"
]

# --- Classes Auxiliares ---

class DataFormatter:
    @staticmethod
    def clean_text(text):
        """Limpa quebras de linha e espaços múltiplos."""
        if not text: return ""
        return " ".join(text.split()).strip()

    @staticmethod
    def format_number(value, length=15):
        """Formata para o padrão 000000000100000 (sem virgula/ponto)."""
        if not value: return "0" * length
        clean = re.sub(r'\D', '', value)
        if not clean: return "0" * length
        return clean.zfill(length)

    @staticmethod
    def format_ncm(value):
        if not value: return "00000000"
        return re.sub(r'\D', '', value)[:8]

class PDFParser:
    def __init__(self, file_stream):
        self.doc = fitz.open(stream=file_stream, filetype="pdf")
        self.full_text = ""
        self.header = {}
        self.items = []

    def preprocess(self):
        """Remove cabeçalhos e rodapés de todas as páginas antes de processar."""
        clean_lines = []
        for page in self.doc:
            text = page.get_text("text")
            lines = text.split('\n')
            for line in lines:
                l_strip = line.strip()
                # Filtros de lixo baseados no seu PDF
                if "Extrato da DUIMP" in l_strip: continue
                if "Data, hora e responsável" in l_strip: continue
                if "Extrato da Duimp" in l_strip and "Versão" in l_strip: continue
                if re.match(r'^\d+\s*/\s*\d+$', l_strip): continue # Paginação 1/9
                if "The following table" in l_strip: continue
                
                clean_lines.append(line)
        self.full_text = "\n".join(clean_lines)

    def extract_header(self):
        txt = self.full_text
        # Regex para dados gerais
        self.header["numeroDUIMP"] = self._regex(r"Extrato da Duimp\s+([\w\-\/]+)", txt)
        self.header["cnpj"] = self._regex(r"CNPJ do importador:\s*([\d\.\/\-]+)", txt)
        self.header["nomeImportador"] = self._regex(r"Nome do importador:\s*\n?(.+)", txt)
        self.header["pesoBruto"] = self._regex(r"Peso Bruto \(kg\):\s*([\d\.,]+)", txt)
        self.header["pesoLiquido"] = self._regex(r"Peso Liquido \(kg\):\s*([\d\.,]+)", txt)
        self.header["urf"] = self._regex(r"Unidade de despacho:\s*([\d]+)", txt)
        self.header["paisProcedencia"] = self._regex(r"País de Procedência:\s*\n?(.+)", txt)

    def extract_items(self):
        # Separa por "Item 00001"
        chunks = re.split(r"Item\s+(\d{5})", self.full_text)
        
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                num = chunks[i]
                content = chunks[i+1]
                
                item = {"numeroAdicao": num}
                
                # Regex Item
                item["ncm"] = self._regex(r"NCM:\s*([\d\.]+)", content)
                item["paisOrigem"] = self._regex(r"País de origem:\s*\n?(.+)", content)
                item["quantidade"] = self._regex(r"Quantidade na unidade estatística:\s*([\d\.,]+)", content)
                item["unidade"] = self._regex(r"Unidade estatística:\s*(.+)", content)
                item["pesoLiq"] = self._regex(r"Peso líquido \(kg\):\s*([\d\.,]+)", content)
                item["valorUnit"] = self._regex(r"Valor unitário na condição de venda:\s*([\d\.,]+)", content)
                item["valorTotal"] = self._regex(r"Valor total na condição de venda:\s*([\d\.,]+)", content)
                item["moeda"] = self._regex(r"Moeda negociada:\s*(.+)", content)
                # Descrição limpa
                desc_match = re.search(r"Detalhamento do Produto:\s*(.+?)(?=\n\s*(?:Número de Identificação|Versão|Código de Class|Descrição complementar))", content, re.DOTALL)
                item["descricao"] = desc_match.group(1).strip() if desc_match else ""
                
                self.items.append(item)

    def _regex(self, pattern, text):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""

class XMLBuilder:
    def __init__(self, parser):
        self.p = parser
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self):
        h = self.p.header
        duimp_fmt = h.get("numeroDUIMP", "").split("/")[0].replace("-", "").replace(".", "")

        # --- Geração das Adições ---
        for it in self.p.items:
            adicao = etree.SubElement(self.duimp, "adicao")
            
            # Mapeamento de Valores REAIS extraídos
            # O que não estiver aqui será preenchido com DEFAULT
            vals = {
                "numeroAdicao": it["numeroAdicao"][-3:],
                "numeroDUIMP": duimp_fmt,
                "numeroLI": "0000000000",
                "dadosCargaPaisProcedenciaCodigo": "000",
                "dadosCargaUrfEntradaCodigo": h.get("urf", "0000000"),
                "dadosCargaViaTransporteCodigo": "01",
                "dadosCargaViaTransporteNome": "MARÍTIMA",
                "dadosMercadoriaAplicacao": "REVENDA",
                "dadosMercadoriaCodigoNcm": DataFormatter.format_ncm(it.get("ncm")),
                "dadosMercadoriaCondicao": "NOVA",
                "dadosMercadoriaMedidaEstatisticaQuantidade": DataFormatter.format_number(it.get("quantidade"), 14),
                "dadosMercadoriaMedidaEstatisticaUnidade": it.get("unidade", "UNIDADE").upper(),
                "dadosMercadoriaNomeNcm": "DESCRIÇÃO NCM",
                "dadosMercadoriaPesoLiquido": DataFormatter.format_number(it.get("pesoLiq"), 15),
                "condicaoVendaIncoterm": "FCA",
                "condicaoVendaMoedaNome": it.get("moeda", "EURO").upper(),
                "condicaoVendaValorMoeda": DataFormatter.format_number(it.get("valorTotal"), 15),
                "condicaoVendaValorReais": DataFormatter.format_number(it.get("valorTotal"), 15), # Placeholder
                "paisOrigemMercadoriaNome": it.get("paisOrigem", "").upper(),
                "paisAquisicaoMercadoriaNome": it.get("paisOrigem", "").upper(),
                "valorTotalCondicaoVenda": DataFormatter.format_number(it.get("valorTotal"), 11),
                "vinculoCompradorVendedor": "Não há vinculação entre comprador e vendedor.",
                # Valores Fixos para validação (zeros)
                "iiRegimeTributacaoNome": "RECOLHIMENTO INTEGRAL",
                "pisCofinsRegimeTributacaoNome": "RECOLHIMENTO INTEGRAL",
                "ipiRegimeTributacaoNome": "SEM BENEFICIO"
            }

            # Loop Mestre de Tags
            for tag in TAGS_ADICAO:
                if tag == "acrescimo":
                    # Bloco complexo Acresicmo
                    node = etree.SubElement(adicao, "acrescimo")
                    etree.SubElement(node, "codigoAcrescimo").text = "17"
                    etree.SubElement(node, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
                    etree.SubElement(node, "moedaNegociadaCodigo").text = "978"
                    etree.SubElement(node, "moedaNegociadaNome").text = "EURO/COM.EUROPEIA"
                    etree.SubElement(node, "valorMoedaNegociada").text = "000000000000000"
                    etree.SubElement(node, "valorReais").text = "000000000000000"
                
                elif tag == "mercadoria":
                    # Bloco complexo Mercadoria
                    node = etree.SubElement(adicao, "mercadoria")
                    desc = DataFormatter.clean_text(it.get("descricao", ""))
                    etree.SubElement(node, "descricaoMercadoria").text = desc
                    etree.SubElement(node, "numeroSequencialItem").text = "01"
                    etree.SubElement(node, "quantidade").text = DataFormatter.format_number(it.get("quantidade"), 14)
                    etree.SubElement(node, "unidadeMedida").text = it.get("unidade", "UNIDADE").upper()
                    etree.SubElement(node, "valorUnitario").text = DataFormatter.format_number(it.get("valorUnit"), 20)
                
                else:
                    # Tags simples
                    if tag in vals:
                        etree.SubElement(adicao, tag).text = vals[tag]
                    else:
                        # Preenchimento padrão para tags faltantes
                        if "Valor" in tag or "Quantidade" in tag or "Peso" in tag or "BaseCalculo" in tag:
                            etree.SubElement(adicao, tag).text = "0" * 15 # Zeros padrão financeiro
                        elif "Aliquota" in tag:
                             etree.SubElement(adicao, tag).text = "00000"
                        elif "Codigo" in tag:
                             etree.SubElement(adicao, tag).text = "00"
                        else:
                            etree.SubElement(adicao, tag).text = "" # Vazio

        # --- Tags Gerais (Pós-Adições) ---
        # Armazem
        armazem = etree.SubElement(self.duimp, "armazem")
        etree.SubElement(armazem, "nomeArmazem").text = "TCP"
        
        # Campos Gerais
        etree.SubElement(self.duimp, "armazenamentoRecintoAduaneiroCodigo").text = "9801303"
        etree.SubElement(self.duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL"
        etree.SubElement(self.duimp, "armazenamentoSetor").text = "002"
        etree.SubElement(self.duimp, "canalSelecaoParametrizada").text = "001"
        etree.SubElement(self.duimp, "cargaDataChegada").text = "20251120"
        etree.SubElement(self.duimp, "cargaPesoBruto").text = DataFormatter.format_number(h.get("pesoBruto"), 15)
        etree.SubElement(self.duimp, "cargaPesoLiquido").text = DataFormatter.format_number(h.get("pesoLiquido"), 15)
        etree.SubElement(self.duimp, "cargaUrfEntradaCodigo").text = h.get("urf", "0917800")
        etree.SubElement(self.duimp, "importadorNome").text = h.get("nomeImportador", "")
        etree.SubElement(self.duimp, "importadorNumero").text = DataFormatter.format_number(h.get("cnpj"), 14)
        etree.SubElement(self.duimp, "numeroDUIMP").text = duimp_fmt
        
        # Pagamentos (Exemplo de repetição estruturada)
        pgto = etree.SubElement(self.duimp, "pagamento")
        etree.SubElement(pgto, "codigoReceita").text = "0086"
        etree.SubElement(pgto, "valorReceita").text = "000000000000000"
        
        etree.SubElement(self.duimp, "totalAdicoes").text = str(len(self.p.items)).zfill(3)
        etree.SubElement(self.duimp, "viaTransporteNome").text = "MARÍTIMA"

        return etree.tostring(self.root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# --- Interface ---
st.title("Extrator DUIMP (XML Mapeado)")
st.markdown("Extração de PDF e Geração de XML seguindo estritamente o layout `M-DUIMP-8686868686`.")

file = st.file_uploader("PDF da DUIMP", type="pdf")

if file:
    if st.button("Gerar XML"):
        try:
            p = PDFParser(file.read())
            p.preprocess()
            p.extract_header()
            p.extract_items()
            
            b = XMLBuilder(p)
            xml = b.build()
            
            st.success("Sucesso!")
            st.download_button("Baixar XML", xml, "DUIMP_Mapeada.xml", "text/xml")
            
            st.text_area("XML", xml.decode(), height=500)
        except Exception as e:
            st.error(f"Erro: {e}")
