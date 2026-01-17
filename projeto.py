import streamlit as st
import fitz  # PyMuPDF
import re
from lxml import etree

st.set_page_config(page_title="Conversor DUIMP 2.0 (Extrato Conferência)", layout="wide")

# ==============================================================================
# 1. ESQUELETO MESTRE (LAYOUT OBRIGATÓRIO - INTACTO)
# ==============================================================================
# A ordem e estrutura destas listas garantem a fidelidade ao XML modelo.

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
        # Neste layout, o endereço muitas vezes não vem detalhado (Rua, Num).
        # Extraímos o que é possível (Nome e País) e deixamos o resto vazio/padrão
        # para não quebrar a estrutura do XML.
        data = {
            "fornecedorNome": "FORNECEDOR PADRAO",
            "fornecedorLogradouro": "",
            "fornecedorNumero": "",
            "fornecedorCidade": "EXTERIOR"
        }
        
        if raw_name:
            # Ex: "HAFELE SE & CO KG PAIS: DE ALEMANHA"
            parts = raw_name.split("PAIS:")
            data["fornecedorNome"] = parts[0].strip()[:60]
            if len(parts) > 1:
                # Tenta extrair o país/cidade
                data["fornecedorCidade"] = parts[1].split("-")[0].strip()[:30]
            
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
        """Lê o PDF completo."""
        raw_text = []
        for page in self.doc:
            raw_text.append(page.get_text("text"))
        self.full_text = "\n".join(raw_text)

    def extract_header(self):
        txt = self.full_text
        
        # Regex específicos para o layout "Extrato de Conferência"
        
        # DUIMP (Procura por "Numero" e pega o valor na linha seguinte ou mesma linha)
        duimp_match = re.search(r"Numero\s*\n\s*([\w\d]+)", txt, re.IGNORECASE)
        if not duimp_match:
             duimp_match = re.search(r"Numero\s*[:]\s*([\w\d]+)", txt, re.IGNORECASE)
        self.header["numeroDUIMP"] = duimp_match.group(1) if duimp_match else ""

        # Importador
        imp_match = re.search(r"IMPORTADOR\s*\n\s*\"?(.+?)\"?(?=\n)", txt, re.IGNORECASE)
        self.header["importadorNome"] = imp_match.group(1).strip() if imp_match else ""
        
        cnpj_match = re.search(r"CNPJ\s*\n\s*\"?([\d./-]+)\"?", txt, re.IGNORECASE)
        self.header["cnpj"] = cnpj_match.group(1) if cnpj_match else ""

        # Pesos (Geralmente no final, nas informações complementares)
        peso_b_match = re.search(r"PESO BRUTO KG\s*[:]?\s*([\d.,]+)", txt, re.IGNORECASE)
        self.header["pesoBruto"] = peso_b_match.group(1) if peso_b_match else "0"
        
        peso_l_match = re.search(r"PESO LIQUIDO KG\s*[:]?\s*([\d.,]+)", txt, re.IGNORECASE)
        self.header["pesoLiquido"] = peso_l_match.group(1) if peso_l_match else "0"
        
        # Fornecedor Global (Captura genérica se houver no cabeçalho)
        forn_match = re.search(r"EXPORTADOR ESTRANGEIRO\s*\n\s*(.+?)(?=\n)", txt, re.IGNORECASE)
        self.header["fornecedorGlobal"] = forn_match.group(1).strip() if forn_match else ""

    def extract_items(self):
        """
        Extrai itens dividindo o texto pelos marcadores 'ITENS DA DUIMP'.
        Estratégia: O NCM do Item X geralmente está no bloco do Item X-1 (tabela anterior).
        """
        # 1. Extrair todos os NCMs presentes nas tabelas CSV-like
        # Procura linhas como: "1",,"3926.30.00"
        ncms = re.findall(r"\"\d+\",,\"([\d\.]+)\"", self.full_text)
        if not ncms:
            # Tenta formato alternativo sem aspas/vírgulas se o PDF for diferente
            ncms = re.findall(r"(\d{4}\.\d{2}\.\d{2})", self.full_text)

        # 2. Dividir em blocos de itens
        chunks = re.split(r"ITENS DA DUIMP", self.full_text)
        
        # O primeiro chunk é cabeçalho. Os seguintes são itens.
        # chunks[1] = Item 1 Details, chunks[2] = Item 2 Details...
        
        if len(chunks) > 1:
            for i in range(1, len(chunks)):
                content = chunks[i]
                
                # Associa NCM pelo índice (Item 1 usa o 1º NCM encontrado, etc)
                # Proteção de índice
                ncm_val = ncms[i-1] if (i-1) < len(ncms) else "00000000"
                
                item = {
                    "numeroAdicao": str(i).zfill(3),
                    "ncm": ncm_val,
                    "fornecedor_raw": self.header.get("fornecedorGlobal", "")
                }

                # Extração de Campos Específicos dentro do bloco do item
                
                # Descrição
                desc_match = re.search(r"DENOMINACAO DO PRODUTO\s*\n\s*(.+?)(?=\n\s*DESCRICAO DO PRODUTO|CÓDIGO INTERNO)", content, re.DOTALL | re.IGNORECASE)
                item["descricao"] = desc_match.group(1).strip() if desc_match else "DESCRIÇÃO NÃO ENCONTRADA"

                # Quantidade Estatística
                qtd_match = re.search(r"Qtde Unid. Estatística\s*\n\s*\"?([\d.,]+)", content, re.IGNORECASE)
                item["quantidade"] = qtd_match.group(1) if qtd_match else "0"

                # Unidade
                unid_match = re.search(r"Unidad Estatística\s*\n\s*\"?(.+?)\"", content, re.IGNORECASE)
                item["unidade"] = unid_match.group(1) if unid_match else "UN"

                # Peso Líquido
                peso_match = re.search(r"Peso Líquido \(KG\)\s*\n\s*\"?([\d.,]+)", content, re.IGNORECASE)
                item["pesoLiq"] = peso_match.group(1) if peso_match else "0"

                # Valor Total (Condição de Venda)
                val_match = re.search(r"Valor Tot. Cond Venda\s*\n\s*\"?([\d.,]+)", content, re.IGNORECASE)
                item["valorTotal"] = val_match.group(1) if val_match else "0"
                
                # Fornecedor Específico do Item (se houver)
                forn_item_match = re.search(r"EXPORTADOR ESTRANGEIRO\s*\n\s*(.+?)(?=\n)", content, re.IGNORECASE)
                if forn_item_match:
                    item["fornecedor_raw"] = forn_item_match.group(1).strip()

                self.items.append(item)

# ==============================================================================
# 4. XML BUILDER (REUTILIZADO E INTACTO)
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
            
            # Fornecedor
            supplier_data = DataFormatter.parse_supplier_info(it.get("fornecedor_raw"), "")

            # Mapa de Valores
            extracted_map = {
                "numeroAdicao": it["numeroAdicao"][-3:],
                "numeroDUIMP": duimp_fmt,
                "dadosMercadoriaCodigoNcm": DataFormatter.format_ncm(it.get("ncm")),
                "dadosMercadoriaMedidaEstatisticaQuantidade": DataFormatter.format_number(it.get("quantidade"), 14),
                "dadosMercadoriaMedidaEstatisticaUnidade": it.get("unidade", "").upper(),
                "dadosMercadoriaPesoLiquido": DataFormatter.format_number(it.get("pesoLiq"), 15),
                "condicaoVendaMoedaNome": "DOLAR DOS EUA", # Default comum ou extrair se possível
                "condicaoVendaValorMoeda": base_total_reais,
                "condicaoVendaValorReais": base_total_reais,
                "paisOrigemMercadoriaNome": "EXTERIOR",
                "paisAquisicaoMercadoriaNome": "EXTERIOR",
                "valorTotalCondicaoVenda": DataFormatter.format_number(it.get("valorTotal"), 11),
                "descricaoMercadoria": DataFormatter.clean_text(it.get("descricao", "")),
                "quantidade": DataFormatter.format_number(it.get("quantidade"), 14),
                "unidadeMedida": it.get("unidade", "").upper(),
                "valorUnitario": DataFormatter.format_number(it.get("valorTotal"), 20), # Simplificação
                "dadosCargaUrfEntradaCodigo": "0000000",
                
                # --- FORNECEDOR ---
                "fornecedorNome": supplier_data["fornecedorNome"],
                "fornecedorLogradouro": supplier_data["fornecedorLogradouro"],
                "fornecedorNumero": supplier_data["fornecedorNumero"],
                "fornecedorCidade": supplier_data["fornecedorCidade"],

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
