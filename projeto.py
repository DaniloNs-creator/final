import streamlit as st
import fitz  # PyMuPDF
import re
from lxml import etree

st.set_page_config(page_title="Conversor DUIMP V9 (State Machine)", layout="wide")

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
    {"tag": "cofinsAliquotaAdValorem", "default": "00000"},
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
        return re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()

    @staticmethod
    def format_number(value, length=15):
        if not value: return "0" * length
        clean = re.sub(r'\D', '', value)
        return clean.zfill(length)
    
    @staticmethod
    def format_rate_xml(value):
        if not value: return "00000"
        val_clean = value.replace(",", ".").strip()
        try:
            val_float = float(val_clean)
            val_int = int(round(val_float * 100))
            return str(val_int).zfill(5)
        except:
            return "00000"

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
            ibs_val = base_float * 0.001
            return str(int(round(cbs_val * 100))).zfill(14), str(int(round(ibs_val * 100))).zfill(14)
        except:
            return "0".zfill(14), "0".zfill(14)

    @staticmethod
    def parse_supplier_info(raw_name):
        data = {"fornecedorNome": "FORNECEDOR PADRAO", "fornecedorLogradouro": "", "fornecedorNumero": "", "fornecedorCidade": "EXTERIOR"}
        if raw_name:
            parts = raw_name.split("PAIS:")
            data["fornecedorNome"] = parts[0].strip()[:60]
            if len(parts) > 1:
                data["fornecedorCidade"] = parts[1].split("-")[0].strip()[:30]
        return data

# ==============================================================================
# 3. PARSER V9 (STATE MACHINE - PROCESSO CONTINUO)
# ==============================================================================

class PDFParserV9:
    def __init__(self, file_stream):
        self.doc = fitz.open(stream=file_stream, filetype="pdf")
        self.header = {}
        self.items = []

    def extract_header_from_first_page(self):
        """Extrai dados do cabeçalho da primeira página."""
        if len(self.doc) == 0: return
        
        page1_text = self.doc[0].get_text("text")
        
        duimp_match = re.search(r"Numero\s*[:\n]?\s*([\w\d]+)", page1_text, re.IGNORECASE)
        self.header["numeroDUIMP"] = duimp_match.group(1) if duimp_match else "00000000000"

        imp_match = re.search(r"IMPORTADOR\s*[:\n]?\s*(.+)", page1_text, re.IGNORECASE)
        self.header["importadorNome"] = imp_match.group(1).strip() if imp_match else ""
        
        cnpj_match = re.search(r"CNPJ\s*[:\n]?\s*([\d./-]+)", page1_text, re.IGNORECASE)
        self.header["cnpj"] = cnpj_match.group(1) if cnpj_match else ""
        
        # Pesos podem estar em outras páginas, então deixamos padrão se não achar
        self.header["pesoBruto"] = "0"
        self.header["pesoLiquido"] = "0"
        self.header["fornecedorGlobal"] = ""

    def _extract_data_from_block(self, block_text):
        """
        Processa um bloco de texto que sabemos conter UM item inteiro.
        """
        item = {}
        
        # Identificação
        adi_match = re.search(r"Nº\s*Adição\s*[:\n]?\s*(\d+)", block_text, re.IGNORECASE)
        item["numeroAdicao"] = adi_match.group(1).zfill(3) if adi_match else "000"
        
        # NCM
        ncm_match = re.search(r"(\d{4}\.\d{2}\.\d{2})", block_text)
        item["ncm"] = ncm_match.group(1) if ncm_match else "00000000"
        
        # Descrição
        desc_match = re.search(r"DENOMINACAO DO PRODUTO\s*[:\n]?\s*(.+?)(?=\n)", block_text, re.IGNORECASE)
        item["descricao"] = desc_match.group(1).strip() if desc_match else f"ITEM {item['numeroAdicao']}"
        
        # Quantidade
        qtd_match = re.search(r"Qtde Unid\. Estatística\s*[:\n]?\s*([\d.,]+)", block_text, re.IGNORECASE)
        item["quantidade"] = qtd_match.group(1) if qtd_match else "0"
        
        # Unidade
        unid_match = re.search(r"Unidad Estatística\s*[:\n]?\s*([A-Z]+)", block_text, re.IGNORECASE)
        item["unidade"] = unid_match.group(1) if unid_match else "UN"
        
        # Peso
        peso_match = re.search(r"Peso Líquido \(KG\)\s*[:\n]?\s*([\d.,]+)", block_text, re.IGNORECASE)
        item["pesoLiq"] = peso_match.group(1) if peso_match else "0"
        
        # Valor
        val_match = re.search(r"Valor Tot\. Cond Venda\s*[:\n]?\s*([\d.,]+)", block_text, re.IGNORECASE)
        item["valorTotal"] = val_match.group(1) if val_match else "0"
        
        # Fornecedor
        forn_spec = re.search(r"EXPORTADOR ESTRANGEIRO\s*[:\n]?\s*(.+?)(?=\n)", block_text, re.IGNORECASE)
        item["fornecedor_raw"] = forn_spec.group(1).strip() if forn_spec else self.header.get("fornecedorGlobal", "")
        
        # --- IMPOSTOS (SCANNER POR PROXIMIDADE) ---
        item.update(self._scan_taxes(block_text))
        
        return item

    def _scan_taxes(self, block_text):
        taxes = {
            "ii_rate": "00000", "ii_val": "0"*15,
            "ipi_rate": "00000", "ipi_val": "0"*15,
            "pis_rate": "00000", "pis_val": "0"*15,
            "cofins_rate": "00000", "cofins_val": "0"*15
        }
        
        tax_map = {
            "II": ("ii_rate", "ii_val"),
            "IMPOSTO DE IMPORTAÇÃO": ("ii_rate", "ii_val"),
            "IPI": ("ipi_rate", "ipi_val"),
            "PIS": ("pis_rate", "pis_val"),
            "PIS/PASEP": ("pis_rate", "pis_val"),
            "COFINS": ("cofins_rate", "cofins_val")
        }

        for tax_label, (k_rate, k_val) in tax_map.items():
            # Encontra todas as ocorrências do imposto no bloco
            # Pega a última ou varre
            idx = block_text.find(tax_label)
            if idx != -1:
                # Pega 200 chars à frente
                snippet = block_text[idx:idx+200]
                # Acha numeros (ex: 1.000,00 ou 9,65)
                nums = re.findall(r"([\d]{1,3}(?:[.]\d{3})*,\d{2,4})", snippet)
                
                candidates = []
                for n in nums:
                    try:
                        val = float(n.replace('.', '').replace(',', '.'))
                        candidates.append((val, n))
                    except: pass
                
                if len(candidates) >= 2:
                    candidates.sort(key=lambda x: x[0])
                    # Menor = Alíquota, Maior = Valor
                    rate = candidates[0][1]
                    val = candidates[1][1] if len(candidates) >= 2 else candidates[0][1]
                    
                    taxes[k_rate] = rate
                    taxes[k_val] = val
        return taxes

    def process_all_pages(self):
        """
        Motor de Estado: Percorre página por página, linha por linha.
        Acumula linhas em 'current_item_buffer'.
        Quando encontra um NOVO 'Nº Adição', processa o buffer anterior e limpa.
        """
        self.extract_header_from_first_page()
        
        current_item_buffer = ""
        # Regex flexível para achar "Nº Adição X"
        start_item_pattern = re.compile(r"N.?.?Adi..o", re.IGNORECASE)
        
        # Barra de progresso visual
        prog_bar = st.progress(0)
        total_pages = len(self.doc)
        
        for i, page in enumerate(self.doc):
            # sort=True é CRUCIAL para tabelas
            text = page.get_text("text", sort=True)
            lines = text.splitlines()
            
            for line in lines:
                # Se achou início de item
                if start_item_pattern.search(line):
                    # Se já tinha algo no buffer (item anterior), processa ele
                    if current_item_buffer:
                        # Verifica se o buffer tem conteudo real de item
                        if "DENOMINACAO" in current_item_buffer or "NCM" in current_item_buffer or "Nº" in current_item_buffer:
                             self.items.append(self._extract_data_from_block(current_item_buffer))
                    
                    # Começa novo buffer com a linha atual (que tem o Nº Adição)
                    current_item_buffer = line + "\n"
                else:
                    # Continua acumulando linhas no buffer do item atual
                    current_item_buffer += line + "\n"
            
            # Atualiza progresso a cada 10 paginas
            if i % 10 == 0:
                prog_bar.progress((i + 1) / total_pages)

        # Processa o último item que ficou no buffer
        if current_item_buffer:
             self.items.append(self._extract_data_from_block(current_item_buffer))
        
        prog_bar.progress(100)

# ==============================================================================
# 4. XML BUILDER (MANTIDO FIEL AO LAYOUT)
# ==============================================================================

class XMLBuilder:
    def __init__(self, parser):
        self.p = parser
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self):
        h = self.p.header
        duimp_fmt = re.sub(r'[^a-zA-Z0-9]', '', h.get("numeroDUIMP", ""))

        for it in self.p.items:
            adicao = etree.SubElement(self.duimp, "adicao")
            
            base_total_reais = DataFormatter.format_number(it.get("valorTotal"), 15)
            icms_base_valor = base_total_reais 
            cbs_imposto, ibs_imposto = DataFormatter.calculate_cbs_ibs(icms_base_valor)
            supplier_data = DataFormatter.parse_supplier_info(it.get("fornecedor_raw"))

            extracted_map = {
                "numeroAdicao": it["numeroAdicao"],
                "numeroDUIMP": duimp_fmt,
                "dadosMercadoriaCodigoNcm": DataFormatter.format_ncm(it.get("ncm")),
                "dadosMercadoriaMedidaEstatisticaQuantidade": DataFormatter.format_number(it.get("quantidade"), 14),
                "dadosMercadoriaMedidaEstatisticaUnidade": it.get("unidade", "UN"),
                "dadosMercadoriaPesoLiquido": DataFormatter.format_number(it.get("pesoLiq"), 15),
                "condicaoVendaMoedaNome": "DOLAR DOS EUA",
                "condicaoVendaValorMoeda": base_total_reais,
                "condicaoVendaValorReais": base_total_reais,
                "paisOrigemMercadoriaNome": "EXTERIOR",
                "paisAquisicaoMercadoriaNome": "EXTERIOR",
                "valorTotalCondicaoVenda": DataFormatter.format_number(it.get("valorTotal"), 11),
                "descricaoMercadoria": DataFormatter.clean_text(it.get("descricao")),
                "quantidade": DataFormatter.format_number(it.get("quantidade"), 14),
                "unidadeMedida": it.get("unidade", "UN"),
                "valorUnitario": DataFormatter.format_number(it.get("valorTotal"), 20),
                "dadosCargaUrfEntradaCodigo": "0000000",
                
                "fornecedorNome": supplier_data["fornecedorNome"][:60],
                "fornecedorLogradouro": supplier_data["fornecedorLogradouro"][:60],
                "fornecedorNumero": supplier_data["fornecedorNumero"][:10],
                "fornecedorCidade": supplier_data["fornecedorCidade"][:30],

                "iiAliquotaAdValorem": DataFormatter.format_rate_xml(it["ii_rate"]),
                "iiAliquotaValorDevido": DataFormatter.format_number(it["ii_val"], 15),
                "ipiAliquotaAdValorem": DataFormatter.format_rate_xml(it["ipi_rate"]),
                "ipiAliquotaValorDevido": DataFormatter.format_number(it["ipi_val"], 15),
                "pisPasepAliquotaAdValorem": DataFormatter.format_rate_xml(it["pis_rate"]),
                "pisPasepAliquotaValorDevido": DataFormatter.format_number(it["pis_val"], 15),
                "pisPasepAliquotaValorRecolher": DataFormatter.format_number(it["pis_val"], 15),
                "cofinsAliquotaAdValorem": DataFormatter.format_rate_xml(it["cofins_rate"]),
                "cofinsAliquotaValorDevido": DataFormatter.format_number(it["cofins_val"], 15),
                "cofinsAliquotaValorRecolher": DataFormatter.format_number(it["cofins_val"], 15),

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
# 5. APP
# ==============================================================================

st.title("Conversor DUIMP V9.0 (State Machine)")
st.markdown("Algoritmo de varredura página-a-página para capturar 100% dos itens e impostos.")

file = st.file_uploader("Upload PDF (Grande Volume)", type="pdf")

if file:
    if st.button("Processar Arquivo Completo"):
        try:
            with st.spinner("Iniciando varredura profunda..."):
                # Inicializa e processa
                p = PDFParserV9(file.read())
                p.process_all_pages() # A mágica acontece aqui
                
                b = XMLBuilder(p)
                xml = b.build()
                
                numero_duimp = p.header.get("numeroDUIMP", "000000").replace("/", "-")
                nome_arquivo = f"DUIMP_{numero_duimp}.xml"

                st.success(f"FINALIZADO! {len(p.items)} itens encontrados e processados.")
                st.download_button("Baixar XML", xml, nome_arquivo, "text/xml")
            
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
