import streamlit as st
import fitz  # PyMuPDF
import re
from lxml import etree

st.set_page_config(page_title="Conversor DUIMP 2.0 (Extrato Conferência)", layout="wide")

# ==============================================================================
# 1. ESQUELETO MESTRE (LAYOUT OBRIGATÓRIO - INTACTO)
# ==============================================================================
ADICAO_FIELDS_ORDER = [
    {"tag": "acrescimo", "type": "complex", "children": [
        {"tag": "codigoAcrescimo", "default": "17"},
        {"tag": "denominacao", "default": "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"},
        {"tag": "moedaNegociadaCodigo", "default": "978"},
        {"tag": "moedaNegociadaNome", "default": "EURO/COM.EUROPEIA"},
        {"tag": "valorMoedaNegociada", "default": "000000000000000"},
        {"tag": "valorReais", "default": "000000000000000"}
    ]},
    {"tag": "cideValorAliquotaEspecifica", "default": "00000000000"},
    {"tag": "cideValorDevido", "default": "000000000000000"},
    {"tag": "cideValorRecolher", "default": "000000000000000"},
    {"tag": "codigoRelacaoCompradorVendedor", "default": "3"},
    {"tag": "codigoVinculoCompradorVendedor", "default": "1"},
    {"tag": "cofinsAliquotaAdValorem", "default": "00965"},
    {"tag": "cofinsAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "cofinsAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "cofinsAliquotaReduzida", "default": "00000"},
    {"tag": "cofinsAliquotaValorDevido", "default": "000000000000000"},
    {"tag": "cofinsAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "condicaoVendaIncoterm", "default": "FCA"},
    {"tag": "condicaoVendaLocal", "default": ""},
    {"tag": "condicaoVendaMetodoValoracaoCodigo", "default": "01"},
    {"tag": "condicaoVendaMetodoValoracaoNome", "default": "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"},
    {"tag": "condicaoVendaMoedaCodigo", "default": "978"},
    {"tag": "condicaoVendaMoedaNome", "default": "EURO/COM.EUROPEIA"},
    {"tag": "condicaoVendaValorMoeda", "default": "000000000000000"},
    {"tag": "condicaoVendaValorReais", "default": "000000000000000"},
    {"tag": "dadosCambiaisCoberturaCambialCodigo", "default": "1"},
    {"tag": "dadosCambiaisCoberturaCambialNome", "default": "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"},
    {"tag": "dadosCambiaisInstituicaoFinanciadoraCodigo", "default": "00"},
    {"tag": "dadosCambiaisInstituicaoFinanciadoraNome", "default": "N/I"},
    {"tag": "dadosCambiaisMotivoSemCoberturaCodigo", "default": "00"},
    {"tag": "dadosCambiaisMotivoSemCoberturaNome", "default": "N/I"},
    {"tag": "dadosCambiaisValorRealCambio", "default": "000000000000000"},
    {"tag": "dadosCargaPaisProcedenciaCodigo", "default": "000"},
    {"tag": "dadosCargaUrfEntradaCodigo", "default": "0000000"},
    {"tag": "dadosCargaViaTransporteCodigo", "default": "01"},
    {"tag": "dadosCargaViaTransporteNome", "default": "MARÍTIMA"},
    {"tag": "dadosMercadoriaAplicacao", "default": "REVENDA"},
    {"tag": "dadosMercadoriaCodigoNaladiNCCA", "default": "0000000"},
    {"tag": "dadosMercadoriaCodigoNaladiSH", "default": "00000000"},
    {"tag": "dadosMercadoriaCodigoNcm", "default": "00000000"},
    {"tag": "dadosMercadoriaCondicao", "default": "NOVA"},
    {"tag": "dadosMercadoriaDescricaoTipoCertificado", "default": "Sem Certificado"},
    {"tag": "dadosMercadoriaIndicadorTipoCertificado", "default": "1"},
    {"tag": "dadosMercadoriaMedidaEstatisticaQuantidade", "default": "00000000000000"},
    {"tag": "dadosMercadoriaMedidaEstatisticaUnidade", "default": "UNIDADE"},
    {"tag": "dadosMercadoriaNomeNcm", "default": "DESCRIÇÃO PADRÃO NCM"},
    {"tag": "dadosMercadoriaPesoLiquido", "default": "000000000000000"},
    {"tag": "dcrCoeficienteReducao", "default": "00000"},
    {"tag": "dcrIdentificacao", "default": "00000000"},
    {"tag": "dcrValorDevido", "default": "000000000000000"},
    {"tag": "dcrValorDolar", "default": "000000000000000"},
    {"tag": "dcrValorReal", "default": "000000000000000"},
    {"tag": "dcrValorRecolher", "default": "000000000000000"},
    {"tag": "fornecedorCidade", "default": ""},
    {"tag": "fornecedorLogradouro", "default": ""},
    {"tag": "fornecedorNome", "default": ""},
    {"tag": "fornecedorNumero", "default": ""},
    {"tag": "freteMoedaNegociadaCodigo", "default": "978"},
    {"tag": "freteMoedaNegociadaNome", "default": "EURO/COM.EUROPEIA"},
    {"tag": "freteValorMoedaNegociada", "default": "000000000000000"},
    {"tag": "freteValorReais", "default": "000000000000000"},
    {"tag": "iiAcordoTarifarioTipoCodigo", "default": "0"},
    {"tag": "iiAliquotaAcordo", "default": "00000"},
    {"tag": "iiAliquotaAdValorem", "default": "00000"},
    {"tag": "iiAliquotaPercentualReducao", "default": "00000"},
    {"tag": "iiAliquotaReduzida", "default": "00000"},
    {"tag": "iiAliquotaValorCalculado", "default": "000000000000000"},
    {"tag": "iiAliquotaValorDevido", "default": "000000000000000"},
    {"tag": "iiAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "iiAliquotaValorReduzido", "default": "000000000000000"},
    {"tag": "iiBaseCalculo", "default": "000000000000000"},
    {"tag": "iiFundamentoLegalCodigo", "default": "00"},
    {"tag": "iiMotivoAdmissaoTemporariaCodigo", "default": "00"},
    {"tag": "iiRegimeTributacaoCodigo", "default": "1"},
    {"tag": "iiRegimeTributacaoNome", "default": "RECOLHIMENTO INTEGRAL"},
    {"tag": "ipiAliquotaAdValorem", "default": "00000"},
    {"tag": "ipiAliquotaEspecificaCapacidadeRecipciente", "default": "00000"},
    {"tag": "ipiAliquotaEspecificaQuantidadeUnidadeMedida", "default": "000000000"},
    {"tag": "ipiAliquotaEspecificaTipoRecipienteCodigo", "default": "00"},
    {"tag": "ipiAliquotaEspecificaValorUnidadeMedida", "default": "0000000000"},
    {"tag": "ipiAliquotaNotaComplementarTIPI", "default": "00"},
    {"tag": "ipiAliquotaReduzida", "default": "00000"},
    {"tag": "ipiAliquotaValorDevido", "default": "000000000000000"},
    {"tag": "ipiAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "ipiRegimeTributacaoCodigo", "default": "4"},
    {"tag": "ipiRegimeTributacaoNome", "default": "SEM BENEFICIO"},
    {"tag": "mercadoria", "type": "complex", "children": [
        {"tag": "descricaoMercadoria", "default": ""},
        {"tag": "numeroSequencialItem", "default": "01"},
        {"tag": "quantidade", "default": "00000000000000"},
        {"tag": "unidadeMedida", "default": "UNIDADE"},
        {"tag": "valorUnitario", "default": "00000000000000000000"}
    ]},
    {"tag": "numeroAdicao", "default": "001"},
    {"tag": "numeroDUIMP", "default": ""},
    {"tag": "numeroLI", "default": "0000000000"},
    {"tag": "paisAquisicaoMercadoriaCodigo", "default": "000"},
    {"tag": "paisAquisicaoMercadoriaNome", "default": ""},
    {"tag": "paisOrigemMercadoriaCodigo", "default": "000"},
    {"tag": "paisOrigemMercadoriaNome", "default": ""},
    {"tag": "pisCofinsBaseCalculoAliquotaICMS", "default": "00000"},
    {"tag": "pisCofinsBaseCalculoFundamentoLegalCodigo", "default": "00"},
    {"tag": "pisCofinsBaseCalculoPercentualReducao", "default": "00000"},
    {"tag": "pisCofinsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "pisCofinsFundamentoLegalReducaoCodigo", "default": "00"},
    {"tag": "pisCofinsRegimeTributacaoCodigo", "default": "1"},
    {"tag": "pisCofinsRegimeTributacaoNome", "default": "RECOLHIMENTO INTEGRAL"},
    {"tag": "pisPasepAliquotaAdValorem", "default": "00000"},
    {"tag": "pisPasepAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "pisPasepAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "pisPasepAliquotaReduzida", "default": "00000"},
    {"tag": "pisPasepAliquotaValorDevido", "default": "000000000000000"},
    {"tag": "pisPasepAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "icmsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "icmsBaseCalculoAliquota", "default": "00000"},
    {"tag": "icmsBaseCalculoValorImposto", "default": "00000000000000"},
    {"tag": "icmsBaseCalculoValorDiferido", "default": "00000000000000"},
    {"tag": "cbsIbsCst", "default": "000"},
    {"tag": "cbsIbsClasstrib", "default": "000001"},
    {"tag": "cbsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "cbsBaseCalculoAliquota", "default": "00000"},
    {"tag": "cbsBaseCalculoAliquotaReducao", "default": "00000"},
    {"tag": "cbsBaseCalculoValorImposto", "default": "00000000000000"},
    {"tag": "ibsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "ibsBaseCalculoAliquota", "default": "00000"},
    {"tag": "ibsBaseCalculoAliquotaReducao", "default": "00000"},
    {"tag": "ibsBaseCalculoValorImposto", "default": "00000000000000"},
    {"tag": "relacaoCompradorVendedor", "default": "Fabricante é desconhecido"},
    {"tag": "seguroMoedaNegociadaCodigo", "default": "220"},
    {"tag": "seguroMoedaNegociadaNome", "default": "DOLAR DOS EUA"},
    {"tag": "seguroValorMoedaNegociada", "default": "000000000000000"},
    {"tag": "seguroValorReais", "default": "000000000000000"},
    {"tag": "sequencialRetificacao", "default": "00"},
    {"tag": "valorMultaARecolher", "default": "000000000000000"},
    {"tag": "valorMultaARecolherAjustado", "default": "000000000000000"},
    {"tag": "valorReaisFreteInternacional", "default": "000000000000000"},
    {"tag": "valorReaisSeguroInternacional", "default": "000000000000000"},
    {"tag": "valorTotalCondicaoVenda", "default": "00000000000"},
    {"tag": "vinculoCompradorVendedor", "default": "Não há vinculação entre comprador e vendedor."}
]

# Tags de Rodapé
FOOTER_TAGS = {
    "armazem": {"tag": "nomeArmazem", "default": "TCP"},
    "armazenamentoRecintoAduaneiroCodigo": "9801303",
    "armazenamentoRecintoAduaneiroNome": "TCP - TERMINAL",
    "armazenamentoSetor": "002",
    "canalSelecaoParametrizada": "001",
    "caracterizacaoOperacaoCodigoTipo": "1",
    "caracterizacaoOperacaoDescricaoTipo": "Importação Própria",
    "cargaDataChegada": "20251120",
    "cargaNumeroAgente": "N/I",
    "cargaPaisProcedenciaCodigo": "386",
    "cargaPaisProcedenciaNome": "",
    "cargaPesoBruto": "000000000000000",
    "cargaPesoLiquido": "000000000000000",
    "cargaUrfEntradaCodigo": "0917800",
    "cargaUrfEntradaNome": "PORTO DE PARANAGUA",
    "conhecimentoCargaEmbarqueData": "20251025",
    "conhecimentoCargaEmbarqueLocal": "EXTERIOR",
    "conhecimentoCargaId": "CE123456",
    "conhecimentoCargaIdMaster": "CE123456",
    "conhecimentoCargaTipoCodigo": "12",
    "conhecimentoCargaTipoNome": "HBL - House Bill of Lading",
    "conhecimentoCargaUtilizacao": "1",
    "conhecimentoCargaUtilizacaoNome": "Total",
    "dataDesembaraco": "20251124",
    "dataRegistro": "20251124",
    "documentoChegadaCargaCodigoTipo": "1",
    "documentoChegadaCargaNome": "Manifesto da Carga",
    "documentoChegadaCargaNumero": "1625502058594",
    "embalagem": [{"tag": "codigoTipoEmbalagem", "default": "60"}, {"tag": "nomeEmbalagem", "default": "PALLETS"}, {"tag": "quantidadeVolume", "default": "00001"}],
    "freteCollect": "000000000000000",
    "freteEmTerritorioNacional": "000000000000000",
    "freteMoedaNegociadaCodigo": "978",
    "freteMoedaNegociadaNome": "EURO/COM.EUROPEIA",
    "fretePrepaid": "000000000000000",
    "freteTotalDolares": "000000000000000",
    "freteTotalMoeda": "000000000000000",
    "freteTotalReais": "000000000000000",
    "icms": [{"tag": "agenciaIcms", "default": "00000"}, {"tag": "codigoTipoRecolhimentoIcms", "default": "3"}, {"tag": "nomeTipoRecolhimentoIcms", "default": "Exoneração do ICMS"}, {"tag": "numeroSequencialIcms", "default": "001"}, {"tag": "ufIcms", "default": "PR"}, {"tag": "valorTotalIcms", "default": "000000000000000"}],
    "importadorCodigoTipo": "1",
    "importadorCpfRepresentanteLegal": "00000000000",
    "importadorEnderecoBairro": "CENTRO",
    "importadorEnderecoCep": "00000000",
    "importadorEnderecoComplemento": "",
    "importadorEnderecoLogradouro": "RUA PRINCIPAL",
    "importadorEnderecoMunicipio": "CIDADE",
    "importadorEnderecoNumero": "00",
    "importadorEnderecoUf": "PR",
    "importadorNome": "",
    "importadorNomeRepresentanteLegal": "REPRESENTANTE",
    "importadorNumero": "",
    "importadorNumeroTelefone": "0000000000",
    "informacaoComplementar": "Informações extraídas do Extrato Conferência.",
    "localDescargaTotalDolares": "000000000000000",
    "localDescargaTotalReais": "000000000000000",
    "localEmbarqueTotalDolares": "000000000000000",
    "localEmbarqueTotalReais": "000000000000000",
    "modalidadeDespachoCodigo": "1",
    "modalidadeDespachoNome": "Normal",
    "numeroDUIMP": "",
    "operacaoFundap": "N",
    "pagamento": [{"tag": "agenciaPagamento", "default": "3715"}, {"tag": "bancoPagamento", "default": "341"}, {"tag": "codigoReceita", "default": "0086"}, {"tag": "valorReceita", "default": "000000000000000"}],
    "seguroMoedaNegociadaCodigo": "220",
    "seguroMoedaNegociadaNome": "DOLAR DOS EUA",
    "seguroTotalDolares": "000000000000000",
    "seguroTotalMoedaNegociada": "000000000000000",
    "seguroTotalReais": "000000000000000",
    "sequencialRetificacao": "00",
    "situacaoEntregaCarga": "ENTREGA CONDICIONADA",
    "tipoDeclaracaoCodigo": "01",
    "tipoDeclaracaoNome": "CONSUMO",
    "totalAdicoes": "000",
    "urfDespachoCodigo": "0917800",
    "urfDespachoNome": "PORTO DE PARANAGUA",
    "valorTotalMultaARecolherAjustado": "000000000000000",
    "viaTransporteCodigo": "01",
    "viaTransporteMultimodal": "N",
    "viaTransporteNome": "MARÍTIMA",
    "viaTransporteNomeTransportador": "MAERSK A/S",
    "viaTransporteNomeVeiculo": "MAERSK",
    "viaTransportePaisTransportadorCodigo": "741",
    "viaTransportePaisTransportadorNome": "CINGAPURA"
}

# ==============================================================================
# 2. UTILS
# ==============================================================================

class DataFormatter:
    @staticmethod
    def clean_text(text):
        if not text: return ""
        text = text.replace('\n', ' ').replace('\r', '')
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def format_number(value, length=15):
        if not value: return "0" * length
        clean = re.sub(r'\D', '', value)
        if not clean: return "0" * length
        return clean.zfill(length)

    @staticmethod
    def format_ncm(value):
        if not value: return "00000000"
        return re.sub(r'\D', '', value)[:8]

    @staticmethod
    def calculate_cbs_ibs(base_xml_string):
        try:
            base_int = int(base_xml_string)
            base_float = base_int / 100.0
            
            cbs_val = base_float * 0.009
            cbs_str = str(int(round(cbs_val * 100))).zfill(14)
            
            ibs_val = base_float * 0.001
            ibs_str = str(int(round(ibs_val * 100))).zfill(14)
            
            return cbs_str, ibs_str
        except:
            return "0".zfill(14), "0".zfill(14)

    @staticmethod
    def parse_supplier_info(raw_name, raw_addr):
        data = {
            "fornecedorNome": "FORNECEDOR PADRAO",
            "fornecedorLogradouro": "ENDERECO PADRAO",
            "fornecedorNumero": "S/N",
            "fornecedorCidade": "EXTERIOR"
        }
        
        # Lógica simplificada para quando o PDF tem o fornecedor em campo único ou global
        if raw_name:
            data["fornecedorNome"] = raw_name.strip()[:60]
            
        return data

# ==============================================================================
# 3. PARSER V2 (Extrato Conferência)
# ==============================================================================

class PDFParserV2:
    def __init__(self, file_stream):
        self.doc = fitz.open(stream=file_stream, filetype="pdf")
        self.full_text = ""
        self.header = {}
        self.items = []

    def preprocess(self):
        """Lê todas as páginas concatenadas."""
        raw_text = []
        for page in self.doc:
            raw_text.append(page.get_text("text"))
        self.full_text = "\n".join(raw_text)

    def extract_header(self):
        txt = self.full_text
        
        # Padrões específicos do Extrato de Conferência
        # Busca "Numero" geralmente associado à DUIMP na seção de Identificação
        duimp_match = re.search(r"Numero\s*\n\s*([\w\d]+)", txt, re.IGNORECASE)
        if not duimp_match:
             # Tenta formato alternativo caso a quebra de linha seja diferente
             duimp_match = re.search(r"Numero\s*[:]\s*([\w\d]+)", txt, re.IGNORECASE)
        self.header["numeroDUIMP"] = duimp_match.group(1) if duimp_match else ""

        # Importador
        imp_match = re.search(r"IMPORTADOR\s*\n\s*(.+)", txt, re.IGNORECASE)
        self.header["importadorNome"] = imp_match.group(1).strip() if imp_match else ""
        
        cnpj_match = re.search(r"CNPJ\s*\n\s*([\d./-]+)", txt, re.IGNORECASE)
        self.header["cnpj"] = cnpj_match.group(1) if cnpj_match else ""

        # Pesos e Informações Complementares (geralmente no final)
        # O parser varre o texto todo procurando essas chaves
        peso_b_match = re.search(r"PESO BRUTO KG\s*[:]?\s*([\d.,]+)", txt, re.IGNORECASE)
        self.header["pesoBruto"] = peso_b_match.group(1) if peso_b_match else "0"
        
        peso_l_match = re.search(r"PESO LIQUIDO KG\s*[:]?\s*([\d.,]+)", txt, re.IGNORECASE)
        self.header["pesoLiquido"] = peso_l_match.group(1) if peso_l_match else "0"
        
        # Fornecedor Global (neste relatório costuma aparecer nas info complementares)
        forn_match = re.search(r"FORNECEDOR\s*[:]?\s*(.+)", txt, re.IGNORECASE)
        self.header["fornecedorGlobal"] = forn_match.group(1).strip() if forn_match else ""

    def extract_items(self):
        """
        Estratégia para Itens no Extrato de Conferência:
        Geralmente listados em blocos ou linhas.
        Procura por padrões de NCM e Valores para criar os itens.
        """
        # Regex flexível para capturar itens. 
        # Assume que cada item tem pelo menos um NCM e um Valor visíveis.
        # Exemplo de linha detectada: "8452.2120 ... 4.644,79"
        
        # Divide o texto em blocos baseados em palavras chaves de item se possível
        # Se não, varre linha a linha procurando NCMs
        
        lines = self.full_text.split('\n')
        current_item = {}
        
        item_counter = 1
        
        for i, line in enumerate(lines):
            # Tenta detectar inicio de item ou NCM
            # Padrão NCM: 8 dígitos, as vezes com ponto
            ncm_match = re.search(r"(\d{4}[.]\d{2}\d{2})", line)
            
            if ncm_match:
                # Achou um potencial item
                current_item = {
                    "numeroAdicao": str(item_counter).zfill(3),
                    "ncm": ncm_match.group(1),
                    "descricao": "DESCRIÇÃO GENÉRICA (ITEM " + str(item_counter) + ")", # Default se não achar
                    "quantidade": "1",
                    "valorTotal": "0",
                    "unidade": "UN",
                    "fornecedor_raw": self.header.get("fornecedorGlobal", "")
                }
                
                # Tenta achar valor na mesma linha ou próximas (Valor monetário)
                # Procura valor com virgula decimal grande
                val_match = re.search(r"([\d]{1,3}(?:[.]\d{3})*,\d{2})", line)
                if val_match:
                    current_item["valorTotal"] = val_match.group(1)
                
                # Tenta pegar descrição na linha anterior ou mesma linha
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if len(prev_line) > 5: # Evita pegar linhas vazias ou curtas demais
                        current_item["descricao"] = prev_line
                
                self.items.append(current_item)
                item_counter += 1

# ==============================================================================
# 4. XML BUILDER
# ==============================================================================

class XMLBuilder:
    def __init__(self, parser):
        self.p = parser
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self):
        h = self.p.header
        # Limpeza do numero DUIMP
        duimp_fmt = re.sub(r'[^a-zA-Z0-9]', '', h.get("numeroDUIMP", ""))

        for it in self.p.items:
            adicao = etree.SubElement(self.duimp, "adicao")
            
            # --- PROCESSAMENTO ---
            base_total_reais = DataFormatter.format_number(it.get("valorTotal"), 15)
            icms_base_valor = base_total_reais 
            cbs_imposto, ibs_imposto = DataFormatter.calculate_cbs_ibs(icms_base_valor)
            
            # Fornecedor (Usa o global extraido do header se o item não tiver especifico)
            supplier_data = DataFormatter.parse_supplier_info(it.get("fornecedor_raw"), "")

            # Mapa de Valores
            extracted_map = {
                "numeroAdicao": it["numeroAdicao"][-3:],
                "numeroDUIMP": duimp_fmt,
                "dadosMercadoriaCodigoNcm": DataFormatter.format_ncm(it.get("ncm")),
                "dadosMercadoriaMedidaEstatisticaQuantidade": DataFormatter.format_number(it.get("quantidade"), 14),
                "dadosMercadoriaMedidaEstatisticaUnidade": it.get("unidade", "").upper(),
                "dadosMercadoriaPesoLiquido": DataFormatter.format_number(it.get("pesoLiq", "0"), 15),
                "condicaoVendaMoedaNome": "DOLAR DOS EUA", # Default comum neste relatório ou extrair se possível
                "condicaoVendaValorMoeda": base_total_reais,
                "condicaoVendaValorReais": base_total_reais,
                "paisOrigemMercadoriaNome": "EXTERIOR",
                "paisAquisicaoMercadoriaNome": "EXTERIOR",
                "valorTotalCondicaoVenda": DataFormatter.format_number(it.get("valorTotal"), 11),
                "descricaoMercadoria": DataFormatter.clean_text(it.get("descricao", "")),
                "quantidade": DataFormatter.format_number(it.get("quantidade"), 14),
                "unidadeMedida": it.get("unidade", "").upper(),
                "valorUnitario": DataFormatter.format_number(it.get("valorTotal"), 20), # Simplificação: Unit = Total se Qtd=1
                "dadosCargaUrfEntradaCodigo": "0000000",
                
                # --- FORNECEDOR ---
                "fornecedorNome": supplier_data["fornecedorNome"][:60],
                "fornecedorLogradouro": supplier_data["fornecedorLogradouro"][:60],
                "fornecedorNumero": supplier_data["fornecedorNumero"][:10],
                "fornecedorCidade": supplier_data["fornecedorCidade"][:30],

                # --- TRIBUTOS ---
                "icmsBaseCalculoValor": icms_base_valor,
                "icmsBaseCalculoAliquota": "01800",
                "cbsIbsClasstrib": "000001",
                "cbsBaseCalculoValor": icms_base_valor,
                "cbsBaseCalculoAliquota": "00090",
                "cbsBaseCalculoValorImposto": cbs_imposto,
                "ibsBaseCalculoValor": icms_base_valor,
                "ibsBaseCalculoAliquota": "00010",
                "ibsBaseCalculoValorImposto": ibs_imposto
            }

            # Preenchimento XML
            for field in ADICAO_FIELDS_ORDER:
                tag_name = field["tag"]
                if field.get("type") == "complex":
                    parent = etree.SubElement(adicao, tag_name)
                    for child in field["children"]:
                        c_tag = child["tag"]
                        val = extracted_map.get(c_tag, child["default"])
                        etree.SubElement(parent, c_tag).text = val
                else:
                    val = extracted_map.get(tag_name, field["default"])
                    etree.SubElement(adicao, tag_name).text = val

        # Rodapé
        footer_map = {
            "numeroDUIMP": duimp_fmt,
            "importadorNome": h.get("importadorNome", ""),
            "importadorNumero": DataFormatter.format_number(h.get("cnpj"), 14),
            "cargaPesoBruto": DataFormatter.format_number(h.get("pesoBruto"), 15),
            "cargaPesoLiquido": DataFormatter.format_number(h.get("pesoLiquido"), 15),
            "totalAdicoes": str(len(self.p.items)).zfill(3)
        }

        for tag, default_val in FOOTER_TAGS.items():
            if isinstance(default_val, list):
                parent = etree.SubElement(self.duimp, tag)
                for subfield in default_val:
                    etree.SubElement(parent, subfield["tag"]).text = subfield["default"]
            elif isinstance(default_val, dict):
                parent = etree.SubElement(self.duimp, tag)
                etree.SubElement(parent, default_val["tag"]).text = default_val["default"]
            else:
                val = footer_map.get(tag, default_val)
                etree.SubElement(self.duimp, tag).text = val

        return etree.tostring(self.root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# ==============================================================================
# 5. APP V2
# ==============================================================================

st.title("Conversor DUIMP V2.0 (Novo Layout)")
st.markdown("Processa PDFs do tipo 'Extrato de Conferência' e gera XML com layout obrigatório.")

file = st.file_uploader("Upload PDF (Extrato Conferência)", type="pdf")

if file:
    if st.button("Gerar XML"):
        try:
            # Usa o Parser V2
            p = PDFParserV2(file.read())
            p.preprocess()
            p.extract_header()
            p.extract_items()
            
            b = XMLBuilder(p)
            xml = b.build()
            
            numero_duimp = p.header.get("numeroDUIMP", "000000").replace("/", "-")
            nome_arquivo = f"DUIMP_{numero_duimp}.xml"

            st.success(f"V2.0 Sucesso! {len(p.items)} itens encontrados.")
            st.download_button("Baixar XML", xml, nome_arquivo, "text/xml")
            
        except Exception as e:
            st.error(f"Erro: {e}")
