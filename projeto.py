import streamlit as st
import fitz  # PyMuPDF
import re
from lxml import etree
import pandas as pd  # NOVA IMPORTAÇÃO NECESSÁRIA

st.set_page_config(page_title="Conversor DUIMP (Fornecedor + Fiscal)", layout="wide")

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
    "informacaoComplementar": "Informações extraídas do Extrato DUIMP.",
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
        clean = re.sub(r'\D', '', str(value))
        if not clean: return "0" * length
        return clean.zfill(length)

    @staticmethod
    def format_currency_input(value, length=15):
        """Converte float/string da tabela (ex: 100.50) para formato XML (000...010050)"""
        try:
            if isinstance(value, str):
                value = value.replace(',', '.')
            val_float = float(value)
            # Multiplica por 100 para remover casas decimais
            val_int = int(round(val_float * 100))
            return str(val_int).zfill(length)
        except:
            return "0" * length

    @staticmethod
    def format_percent_input(value, length=5):
        """Converte percentual da tabela (ex: 18.0) para formato XML (01800)"""
        try:
            if isinstance(value, str):
                value = value.replace(',', '.')
            val_float = float(value)
            # Multiplica por 100 (ex: 9.65 -> 965, 18.0 -> 1800)
            val_int = int(round(val_float * 100))
            return str(val_int).zfill(length)
        except:
            return "0" * length

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
            "fornecedorNome": "",
            "fornecedorLogradouro": "",
            "fornecedorNumero": "S/N",
            "fornecedorCidade": ""
        }

        if raw_name:
            parts = raw_name.split('-', 1)
            data["fornecedorNome"] = parts[-1].strip() if len(parts) > 1 else raw_name.strip()

        if raw_addr:
            clean_addr = DataFormatter.clean_text(raw_addr)
            parts_dash = clean_addr.rsplit('-', 1)
            
            if len(parts_dash) > 1:
                data["fornecedorCidade"] = parts_dash[1].strip()
                street_part = parts_dash[0].strip()
            else:
                data["fornecedorCidade"] = "EXTERIOR"
                street_part = clean_addr

            comma_split = street_part.rsplit(',', 1)
            if len(comma_split) > 1:
                data["fornecedorLogradouro"] = comma_split[0].strip()
                num_match = re.search(r'\d+', comma_split[1])
                if num_match:
                    data["fornecedorNumero"] = num_match.group(0)
            else:
                num_match = re.search(r'(\d+)$', street_part)
                if num_match:
                    data["fornecedorNumero"] = num_match.group(1)
                    data["fornecedorLogradouro"] = street_part[:num_match.start()].strip()
                else:
                    data["fornecedorLogradouro"] = street_part

        return data

# ==============================================================================
# 3. PARSER
# ==============================================================================

class PDFParser:
    def __init__(self, file_stream):
        self.doc = fitz.open(stream=file_stream, filetype="pdf")
        self.full_text = ""
        self.header = {}
        self.items = []

    def preprocess(self):
        clean_lines = []
        for page in self.doc:
            text = page.get_text("text")
            lines = text.split('\n')
            for line in lines:
                l_strip = line.strip()
                if "Extrato da DUIMP" in l_strip: continue
                if "Data, hora e responsável" in l_strip: continue
                if re.match(r'^\d+\s*/\s*\d+$', l_strip): continue
                clean_lines.append(line)
        self.full_text = "\n".join(clean_lines)

    def extract_header(self):
        txt = self.full_text
        self.header["numeroDUIMP"] = self._regex(r"Extrato da Duimp\s+([\w\-\/]+)", txt)
        self.header["cnpj"] = self._regex(r"CNPJ do importador:\s*([\d\.\/\-]+)", txt)
        self.header["nomeImportador"] = self._regex(r"Nome do importador:\s*\n?(.+)", txt)
        self.header["pesoBruto"] = self._regex(r"Peso Bruto \(kg\):\s*([\d\.,]+)", txt)
        self.header["pesoLiquido"] = self._regex(r"Peso Liquido \(kg\):\s*([\d\.,]+)", txt)
        self.header["urf"] = self._regex(r"Unidade de despacho:\s*([\d]+)", txt)
        self.header["paisProcedencia"] = self._regex(r"País de Procedência:\s*\n?(.+)", txt)

    def extract_items(self):
        chunks = re.split(r"Item\s+(\d{5})", self.full_text)
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                num = chunks[i]
                content = chunks[i+1]
                item = {"numeroAdicao": num}
                
                item["ncm"] = self._regex(r"NCM:\s*([\d\.]+)", content)
                item["paisOrigem"] = self._regex(r"País de origem:\s*\n?(.+)", content)
                item["quantidade"] = self._regex(r"Quantidade na unidade estatística:\s*([\d\.,]+)", content)
                item["unidade"] = self._regex(r"Unidade estatística:\s*(.+)", content)
                item["pesoLiq"] = self._regex(r"Peso líquido \(kg\):\s*([\d\.,]+)", content)
                item["valorUnit"] = self._regex(r"Valor unitário na condição de venda:\s*([\d\.,]+)", content)
                item["valorTotal"] = self._regex(r"Valor total na condição de venda:\s*([\d\.,]+)", content)
                item["moeda"] = self._regex(r"Moeda negociada:\s*(.+)", content)
                
                # --- NOVAS CAPTURAS (FORNECEDOR) ---
                exp_match = re.search(r"Código do Exportador Estrangeiro:\s*(.+?)(?=\n\s*(?:Endereço|Dados))", content, re.DOTALL)
                item["fornecedor_raw"] = exp_match.group(1).strip() if exp_match else ""
                
                addr_match = re.search(r"Endereço:\s*(.+?)(?=\n\s*(?:Dados da Mercadoria|Aplicação))", content, re.DOTALL)
                item["endereco_raw"] = addr_match.group(1).strip() if addr_match else ""
                # -----------------------------------

                desc_match = re.search(r"Detalhamento do Produto:\s*(.+?)(?=\n\s*(?:Número de Identificação|Versão|Código de Class|Descrição complementar))", content, re.DOTALL)
                item["descricao"] = desc_match.group(1).strip() if desc_match else ""
                
                self.items.append(item)

    def _regex(self, pattern, text):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""

# ==============================================================================
# 4. XML BUILDER
# ==============================================================================

class XMLBuilder:
    def __init__(self, parser, edited_items=None):
        self.p = parser
        # Se houver itens editados manualmente, usa eles. Se não, usa os parseados.
        self.items_to_use = edited_items if edited_items else self.p.items
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self):
        h = self.p.header
        duimp_fmt = h.get("numeroDUIMP", "").split("/")[0].replace("-", "").replace(".", "")

        for it in self.items_to_use:
            adicao = etree.SubElement(self.duimp, "adicao")
            
            # --- PROCESSAMENTO ---
            # Usa o valor total original para calculos base se não houver input manual
            base_total_reais = DataFormatter.format_number(it.get("valorTotal"), 15)
            
            # Se o usuário preencheu "II Base (R$)", usa para o ICMS também, senão usa o total.
            # Nota: O input manual vem no dict `it` como float/string, precisamos formatar
            
            # Formatações Específicas dos Inputs Manuais
            val_frete = DataFormatter.format_currency_input(it.get("input_frete", 0))
            val_seguro = DataFormatter.format_currency_input(it.get("input_seguro", 0))
            val_aduaneiro = DataFormatter.format_currency_input(it.get("input_aduaneiro", 0))
            
            val_ii_base = DataFormatter.format_currency_input(it.get("input_ii_base", 0))
            val_ii_aliq = DataFormatter.format_percent_input(it.get("input_ii_aliq", 0))
            val_ii_devido = DataFormatter.format_currency_input(it.get("input_ii_val", 0))
            
            val_ipi_aliq = DataFormatter.format_percent_input(it.get("input_ipi_aliq", 0))
            val_ipi_devido = DataFormatter.format_currency_input(it.get("input_ipi_val", 0))
            
            val_pis_base = DataFormatter.format_currency_input(it.get("input_pis_base", 0))
            val_pis_aliq = DataFormatter.format_percent_input(it.get("input_pis_aliq", 0))
            val_pis_devido = DataFormatter.format_currency_input(it.get("input_pis_val", 0))
            
            val_cofins_aliq = DataFormatter.format_percent_input(it.get("input_cofins_aliq", 0))
            val_cofins_devido = DataFormatter.format_currency_input(it.get("input_cofins_val", 0))

            # Lógica CBS/IBS (mantida)
            icms_base_valor = val_ii_base if int(val_ii_base) > 0 else base_total_reais
            cbs_imposto, ibs_imposto = DataFormatter.calculate_cbs_ibs(icms_base_valor)
            
            supplier_data = DataFormatter.parse_supplier_info(it.get("fornecedor_raw"), it.get("endereco_raw"))

            # Mapa de Valores
            extracted_map = {
                "numeroAdicao": str(it["numeroAdicao"])[-3:], # garante string
                "numeroDUIMP": duimp_fmt,
                "dadosMercadoriaCodigoNcm": DataFormatter.format_ncm(it.get("ncm")),
                "dadosMercadoriaMedidaEstatisticaQuantidade": DataFormatter.format_number(it.get("quantidade"), 14),
                "dadosMercadoriaMedidaEstatisticaUnidade": it.get("unidade", "").upper(),
                "dadosMercadoriaMedidaEstatisticaPesoLiquido": DataFormatter.format_number(it.get("pesoLiq"), 15),
                "condicaoVendaMoedaNome": it.get("moeda", "").upper(),
                "condicaoVendaValorMoeda": base_total_reais,
                # Se Aduaneiro preenchido, usa ele, senão usa total
                "condicaoVendaValorReais": val_aduaneiro if int(val_aduaneiro) > 0 else base_total_reais,
                "paisOrigemMercadoriaNome": it.get("paisOrigem", "").upper(),
                "paisAquisicaoMercadoriaNome": it.get("paisOrigem", "").upper(),
                "valorTotalCondicaoVenda": DataFormatter.format_number(it.get("valorTotal"), 11),
                "descricaoMercadoria": DataFormatter.clean_text(it.get("descricao", "")),
                "quantidade": DataFormatter.format_number(it.get("quantidade"), 14),
                "unidadeMedida": it.get("unidade", "").upper(),
                "valorUnitario": DataFormatter.format_number(it.get("valorUnit"), 20),
                "dadosCargaUrfEntradaCodigo": h.get("urf", "0917800"),
                
                # --- FORNECEDOR ---
                "fornecedorNome": supplier_data["fornecedorNome"][:60],
                "fornecedorLogradouro": supplier_data["fornecedorLogradouro"][:60],
                "fornecedorNumero": supplier_data["fornecedorNumero"][:10],
                "fornecedorCidade": supplier_data["fornecedorCidade"][:30],

                # --- CAMPOS FISCAIS INJETADOS ---
                "freteValorReais": val_frete,
                "seguroValorReais": val_seguro,
                
                # II
                "iiBaseCalculo": val_ii_base,
                "iiAliquotaAdValorem": val_ii_aliq,
                "iiAliquotaValorDevido": val_ii_devido,
                "iiAliquotaValorRecolher": val_ii_devido, # Assume igual devido
                
                # IPI
                "ipiAliquotaAdValorem": val_ipi_aliq,
                "ipiAliquotaValorDevido": val_ipi_devido,
                "ipiAliquotaValorRecolher": val_ipi_devido,
                
                # PIS
                "pisCofinsBaseCalculoValor": val_pis_base, # Base compartilhada PIS/COFINS
                "pisPasepAliquotaAdValorem": val_pis_aliq,
                "pisPasepAliquotaValorDevido": val_pis_devido,
                "pisPasepAliquotaValorRecolher": val_pis_devido,
                
                # COFINS
                "cofinsAliquotaAdValorem": val_cofins_aliq,
                "cofinsAliquotaValorDevido": val_cofins_devido,
                "cofinsAliquotaValorRecolher": val_cofins_devido,

                # TRIBUTOS CBS/IBS
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

            # Preenchimento XML (Layout Rígido)
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
            "importadorNome": h.get("nomeImportador", ""),
            "importadorNumero": DataFormatter.format_number(h.get("cnpj"), 14),
            "cargaPesoBruto": DataFormatter.format_number(h.get("pesoBruto"), 15),
            "cargaPesoLiquido": DataFormatter.format_number(h.get("pesoLiquido"), 15),
            "cargaPaisProcedenciaNome": h.get("paisProcedencia", "").upper(),
            "totalAdicoes": str(len(self.items_to_use)).zfill(3)
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
# 5. APP
# ==============================================================================

st.title("Conversor DUIMP (Com Edição Fiscal)")

# Gerenciamento de Estado para persistir os dados entre interações
if 'parsed_items' not in st.session_state:
    st.session_state.parsed_items = None
if 'pdf_parser' not in st.session_state:
    st.session_state.pdf_parser = None

file = st.file_uploader("Upload PDF", type="pdf")

if file:
    # Se for um novo arquivo, reseta e processa
    if st.session_state.pdf_parser is None:
        try:
            p = PDFParser(file.read())
            p.preprocess()
            p.extract_header()
            p.extract_items()
            st.session_state.pdf_parser = p
            st.session_state.parsed_items = p.items
        except Exception as e:
            st.error(f"Erro ao ler PDF: {e}")

    # Se já temos itens processados, mostramos a tabela de edição
    if st.session_state.parsed_items:
        st.subheader("Preenchimento Obrigatório dos Campos Fiscais")
        st.info("Preencha os valores abaixo (Use ponto para decimais, ex: 100.50).")
        
        # Cria DataFrame para edição
        df = pd.DataFrame(st.session_state.parsed_items)
        
        # Define as colunas que queremos editar (inicializadas com 0.0)
        # Mapeando a tabela que você pediu
        edit_columns = [
            "numeroAdicao", "input_aduaneiro", "input_frete", "input_seguro", 
            "input_ii_val", "input_ipi_val", "input_pis_val", "input_cofins_val",
            "input_ii_base", "input_ii_aliq", 
            "input_ipi_base", "input_ipi_aliq",
            "input_pis_base", "input_pis_aliq", 
            "input_cofins_base", "input_cofins_aliq"
        ]
        
        # Inicializa colunas se não existirem
        for col in edit_columns:
            if col not in df.columns:
                df[col] = 0.0

        # Renomeia colunas para ficar igual sua imagem na visualização
        column_config = {
            "numeroAdicao": st.column_config.TextColumn("Item", disabled=True),
            "input_aduaneiro": st.column_config.NumberColumn("Aduaneiro (R$)", format="%.2f"),
            "input_frete": st.column_config.NumberColumn("Frete (R$)", format="%.2f"),
            "input_seguro": st.column_config.NumberColumn("Seguro (R$)", format="%.2f"),
            "input_ii_val": st.column_config.NumberColumn("II (R$)", format="%.2f"),
            "input_ipi_val": st.column_config.NumberColumn("IPI (R$)", format="%.2f"),
            "input_pis_val": st.column_config.NumberColumn("PIS (R$)", format="%.2f"),
            "input_cofins_val": st.column_config.NumberColumn("COFINS (R$)", format="%.2f"),
            "input_ii_base": st.column_config.NumberColumn("II Base (R$)", format="%.2f"),
            "input_ii_aliq": st.column_config.NumberColumn("II Alíq (%)", format="%.2f"),
            "input_ipi_base": st.column_config.NumberColumn("IPI Base (R$)", format="%.2f"), # Apenas visual, XML não tem tag especifica de base IPI na lista, mas usaremos para logica se precisar
            "input_ipi_aliq": st.column_config.NumberColumn("IPI Alíq (%)", format="%.2f"),
            "input_pis_base": st.column_config.NumberColumn("PIS Base (R$)", format="%.2f"),
            "input_pis_aliq": st.column_config.NumberColumn("PIS Alíq (%)", format="%.2f"),
            "input_cofins_base": st.column_config.NumberColumn("COFINS Base (R$)", format="%.2f"),
            "input_cofins_aliq": st.column_config.NumberColumn("COFINS Alíq (%)", format="%.2f"),
        }

        # Exibe editor
        edited_df = st.data_editor(
            df[edit_columns], 
            hide_index=True, 
            column_config=column_config,
            num_rows="fixed"
        )

        st.divider()

        if st.button("Gerar XML Final"):
            try:
                # Atualiza a lista de itens com os dados do DataFrame editado
                # Precisamos mesclar os dados originais (descrição, ncm, etc) com os novos inputs
                
                # Converte o DF editado para lista de dicts
                edited_records = edited_df.to_dict('records')
                
                # Mescla
                final_items = []
                for original, edited in zip(st.session_state.parsed_items, edited_records):
                    merged = {**original, **edited} # Atualiza original com inputs
                    final_items.append(merged)

                # Gera XML com os dados mesclados
                b = XMLBuilder(st.session_state.pdf_parser, edited_items=final_items)
                xml = b.build()
                
                numero_duimp = st.session_state.pdf_parser.header.get("numeroDUIMP", "00000000000").replace("/", "-")
                nome_arquivo = f"DUIMP_{numero_duimp}_CORRIGIDO.xml"

                st.success(f"XML Gerado com Sucesso! {len(final_items)} itens processados com dados fiscais.")
                st.download_button("Baixar XML", xml, nome_arquivo, "text/xml")
                
            except Exception as e:
                st.error(f"Erro ao gerar XML: {e}")
else:
    # Reseta se remover arquivo
    st.session_state.parsed_items = None
    st.session_state.pdf_parser = None
