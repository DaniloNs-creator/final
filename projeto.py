import streamlit as st
import pdfplumber
import re
from lxml import etree
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Häfele | DUIMP Converter Pro", page_icon="📦", layout="wide")

# --- ESTILOS ---
def apply_custom_ui():
    st.markdown("""
    <style>
        .main { background-color: #f8fafc; }
        .stApp { font-family: 'Inter', sans-serif; }
        .header-container {
            background: #ffffff;
            padding: 2rem;
            border-radius: 15px;
            border-left: 8px solid #d3003c;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
            border: 1px solid #e2e8f0;
        }
        h1 { color: #1e293b; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. ESTRUTURA XML OBRIGATÓRIA (LAYOUT RÍGIDO)
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
    {"tag": "cofinsAliquotaAdValorem", "default": "00000"}, # SCANNER
    {"tag": "cofinsAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "cofinsAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "cofinsAliquotaReduzida", "default": "00000"},
    {"tag": "cofinsAliquotaValorDevido", "default": "000000000000000"}, # SCANNER
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
    {"tag": "iiAliquotaAdValorem", "default": "00000"}, # SCANNER
    {"tag": "iiAliquotaPercentualReducao", "default": "00000"},
    {"tag": "iiAliquotaReduzida", "default": "00000"},
    {"tag": "iiAliquotaValorCalculado", "default": "000000000000000"},
    {"tag": "iiAliquotaValorDevido", "default": "000000000000000"}, # SCANNER
    {"tag": "iiAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "iiAliquotaValorReduzido", "default": "000000000000000"},
    {"tag": "iiBaseCalculo", "default": "000000000000000"},
    {"tag": "iiFundamentoLegalCodigo", "default": "00"},
    {"tag": "iiMotivoAdmissaoTemporariaCodigo", "default": "00"},
    {"tag": "iiRegimeTributacaoCodigo", "default": "1"},
    {"tag": "iiRegimeTributacaoNome", "default": "RECOLHIMENTO INTEGRAL"},
    {"tag": "ipiAliquotaAdValorem", "default": "00000"}, # SCANNER
    {"tag": "ipiAliquotaEspecificaCapacidadeRecipciente", "default": "00000"},
    {"tag": "ipiAliquotaEspecificaQuantidadeUnidadeMedida", "default": "000000000"},
    {"tag": "ipiAliquotaEspecificaTipoRecipienteCodigo", "default": "00"},
    {"tag": "ipiAliquotaEspecificaValorUnidadeMedida", "default": "0000000000"},
    {"tag": "ipiAliquotaNotaComplementarTIPI", "default": "00"},
    {"tag": "ipiAliquotaReduzida", "default": "00000"},
    {"tag": "ipiAliquotaValorDevido", "default": "000000000000000"}, # SCANNER
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
    {"tag": "pisPasepAliquotaAdValorem", "default": "00000"}, # SCANNER
    {"tag": "pisPasepAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "pisPasepAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "pisPasepAliquotaReduzida", "default": "00000"},
    {"tag": "pisPasepAliquotaValorDevido", "default": "000000000000000"}, # SCANNER
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
# 2. UTILS DE FORMATAÇÃO E CÁLCULO
# ==============================================================================

class DataFormatter:
    @staticmethod
    def clean_text(text):
        if not text: return ""
        return re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()

    @staticmethod
    def clean_val(val):
        if not val: return "0"
        return re.sub(r'[^\d,]', '', str(val)).replace(',', '')

    @staticmethod
    def format_number(value, length=15):
        if not value: return "0" * length
        clean = re.sub(r'\D', '', str(value))
        return clean.zfill(length)
    
    @staticmethod
    def format_rate_xml(value):
        if not value: return "00000"
        val_clean = str(value).replace(",", ".").strip()
        try:
            val_float = float(val_clean)
            val_int = int(round(val_float * 100))
            return str(val_int).zfill(5)
        except:
            return "00000"

    @staticmethod
    def format_ncm(value):
        if not value: return "00000000"
        return re.sub(r'\D', '', str(value))[:8]

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
# 3. EXTRAÇÃO (PDFPLUMBER + REGEX DO SEU EXEMPLO)
# ==============================================================================

class PDFParserPlumber:
    def __init__(self, file_stream):
        self.file_stream = file_stream
        self.full_text = ""
        self.header = {}
        self.items = []

    def extract_all(self):
        # 1. Extrai Texto com pdfplumber (Robusto para 450pgs)
        with pdfplumber.open(self.file_stream) as pdf:
            text_parts = []
            total = len(pdf.pages)
            prog = st.progress(0)
            
            for i, page in enumerate(pdf.pages):
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
                if i % 10 == 0:
                    prog.progress((i+1)/total)
            prog.progress(100)
            
        self.full_text = "\n".join(text_parts)
        
        # 2. Extrai Cabeçalho
        self.header["processo"] = re.search(r"PROCESSO\s*#?(\d+)", self.full_text, re.I).group(1) if re.search(r"PROCESSO\s*#?(\d+)", self.full_text, re.I) else "N/A"
        
        # Tenta pegar DUIMP. Se falhar, tenta formatos alternativos
        duimp_match = re.search(r"Numero\s*[:\n]*\s*([\dBR]+)", self.full_text, re.I)
        self.header["duimp"] = duimp_match.group(1) if duimp_match else "00000000000"
        
        # Importador / CNPJ
        imp_match = re.search(r"IMPORTADOR\s*\n\s*(.+)", self.full_text, re.IGNORECASE)
        self.header["importadorNome"] = imp_match.group(1).strip() if imp_match else ""
        cnpj_match = re.search(r"CNPJ\s*\n\s*([\d./-]+)", self.full_text, re.IGNORECASE)
        self.header["cnpj"] = cnpj_match.group(1) if cnpj_match else ""
        
        # Pesos
        peso_b_match = re.search(r"PESO BRUTO KG\s*[:]?\s*([\d.,]+)", self.full_text, re.IGNORECASE)
        self.header["pesoBruto"] = peso_b_match.group(1) if peso_b_match else "0"
        peso_l_match = re.search(r"PESO LIQUIDO KG\s*[:]?\s*([\d.,]+)", self.full_text, re.IGNORECASE)
        self.header["pesoLiquido"] = peso_l_match.group(1) if peso_l_match else "0"
        
        # Fornecedor Global
        forn_match = re.search(r"EXPORTADOR ESTRANGEIRO\s*[:\n]?\s*(.+?)(?=\n)", self.full_text, re.IGNORECASE)
        self.header["fornecedorGlobal"] = forn_match.group(1).strip() if forn_match else ""

        # 3. Extrai Itens usando a lógica de split (SUA LÓGICA)
        # Dividimos o texto pelos marcadores de item
        parts = re.split(r"ITENS DA DUIMP\s*[-–]?\s*(\d+)", self.full_text)
        
        # Caso o split principal falhe, tenta o fallback "Nº Adição"
        if len(parts) <= 1:
             parts = re.split(r"Nº Adição\s*[:\n]?\s*(\d+)", self.full_text)

        if len(parts) > 1:
            # parts[0] é lixo inicial. parts[1] é NumItem, parts[2] é Conteudo...
            for i in range(1, len(parts), 2):
                if i+1 >= len(parts): break
                
                num = parts[i]
                block = parts[i+1]
                
                item = {}
                item["numeroAdicao"] = num.zfill(3)
                
                # Dados Básicos (Regex do seu exemplo + ajustes)
                raw_desc = re.search(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+(?:C[ÓO]DIGO|DETALHAMENTO)", block, re.S | re.I)
                item["descricao"] = raw_desc.group(1).replace('\n', ' ').strip() if raw_desc else f"ITEM {num}"
                
                ncm_match = re.search(r"NCM\s*[:\n]*\s*([\d\.]+)", block)
                item["ncm"] = ncm_match.group(1).replace(".", "") if ncm_match else "00000000"
                
                peso_match = re.search(r"Peso Líquido \(KG\)\s*[:\n]*\s*([\d\.,]+)", block, re.I)
                item["pesoLiq"] = peso_match.group(1) if peso_match else "0"
                
                qtd_match = re.search(r"Qtde Unid\. Comercial\s*[:\n]*\s*([\d\.,]+)", block, re.I)
                if not qtd_match: qtd_match = re.search(r"Qtde Unid\. Estatística\s*[:\n]*\s*([\d\.,]+)", block, re.I)
                item["quantidade"] = qtd_match.group(1) if qtd_match else "0"
                
                v_unit_match = re.search(r"Valor Unit Cond Venda\s*[:\n]*\s*([\d\.,]+)", block, re.I)
                item["v_unit"] = v_unit_match.group(1) if v_unit_match else "0"
                
                v_total_match = re.search(r"Valor Tot\. Cond Venda\s*[:\n]*\s*([\d\.,]+)", block, re.I)
                item["v_total"] = v_total_match.group(1) if v_total_match else "0"
                
                # Fornecedor
                forn_spec = re.search(r"EXPORTADOR ESTRANGEIRO\s*[:\n]?\s*(.+?)(?=\n)", block, re.IGNORECASE)
                item["fornecedor_raw"] = forn_spec.group(1).strip() if forn_spec else self.header.get("fornecedorGlobal", "")

                # 4. SCANNER FISCAL (Minha Lógica Integrada)
                item.update(self._scan_taxes(block))
                
                self.items.append(item)

    def _scan_taxes(self, block_text):
        taxes = {
            "ii_rate": "00000", "ii_val": "0"*15,
            "ipi_rate": "00000", "ipi_val": "0"*15,
            "pis_rate": "00000", "pis_val": "0"*15,
            "cofins_rate": "00000", "cofins_val": "0"*15
        }
        
        tax_map = {
            "II": ("ii_rate", "ii_val"), "IMPOSTO DE IMPORTAÇÃO": ("ii_rate", "ii_val"),
            "IPI": ("ipi_rate", "ipi_val"),
            "PIS": ("pis_rate", "pis_val"), "PIS/PASEP": ("pis_rate", "pis_val"),
            "COFINS": ("cofins_rate", "cofins_val")
        }

        for tax_label, (k_rate, k_val) in tax_map.items():
            idx = block_text.find(tax_label)
            if idx != -1:
                snippet = block_text[idx:idx+200]
                nums = re.findall(r"([\d]{1,3}(?:[.]\d{3})*,\d{2,4})", snippet)
                if len(nums) >= 2:
                    candidates = []
                    for n in nums:
                        try:
                            val = float(n.replace('.', '').replace(',', '.'))
                            candidates.append((val, n))
                        except: pass
                    if candidates:
                        candidates.sort(key=lambda x: x[0])
                        taxes[k_rate] = candidates[0][1] # Menor = Rate
                        taxes[k_val] = candidates[1][1] if len(candidates) >= 2 else candidates[0][1] # Maior = Valor
        return taxes

# ==============================================================================
# 4. XML BUILDER (ROBUSTO & COMPATÍVEL)
# ==============================================================================

class XMLBuilder:
    def __init__(self, parser):
        self.p = parser
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self):
        h = self.p.header
        duimp_fmt = re.sub(r'[^a-zA-Z0-9]', '', h.get("duimp", "00000000000"))

        for it in self.p.items:
            adicao = etree.SubElement(self.duimp, "adicao")
            
            # Formatações
            v_total_reais = DataFormatter.format_number(it.get("v_total", "0"), 15)
            icms_base = v_total_reais
            cbs, ibs = DataFormatter.calculate_cbs_ibs(icms_base)
            supplier = DataFormatter.parse_supplier_info(it.get("fornecedor_raw"))

            # Mapeamento dinâmico
            extracted_map = {
                "numeroAdicao": it["numeroAdicao"],
                "numeroDUIMP": duimp_fmt,
                "dadosMercadoriaCodigoNcm": it["ncm"],
                "dadosMercadoriaMedidaEstatisticaQuantidade": DataFormatter.format_number(it["quantidade"], 14),
                "dadosMercadoriaMedidaEstatisticaUnidade": "UNIDADE",
                "dadosMercadoriaPesoLiquido": DataFormatter.format_number(it["pesoLiq"], 15),
                "condicaoVendaMoedaNome": "DOLAR DOS EUA",
                "condicaoVendaValorMoeda": v_total_reais,
                "condicaoVendaValorReais": v_total_reais,
                "paisOrigemMercadoriaNome": "EXTERIOR",
                "paisAquisicaoMercadoriaNome": "EXTERIOR",
                "valorTotalCondicaoVenda": DataFormatter.format_number(it.get("v_total", "0"), 11),
                "descricaoMercadoria": it["descricao"],
                "quantidade": DataFormatter.format_number(it["quantidade"], 14),
                "unidadeMedida": "UNIDADE",
                "valorUnitario": DataFormatter.format_number(it.get("v_unit", "0"), 20),
                "dadosCargaUrfEntradaCodigo": "0000000",
                
                # Fornecedor
                "fornecedorNome": supplier["fornecedorNome"],
                "fornecedorLogradouro": supplier["fornecedorLogradouro"],
                "fornecedorNumero": supplier["fornecedorNumero"],
                "fornecedorCidade": supplier["fornecedorCidade"],

                # Tributos Reais
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

                # IBS/CBS
                "icmsBaseCalculoValor": icms_base,
                "icmsBaseCalculoAliquota": "01800",
                "cbsIbsClasstrib": "000001",
                "cbsBaseCalculoValor": icms_base,
                "cbsBaseCalculoAliquota": "00090",
                "cbsBaseCalculoValorImposto": cbs,
                "ibsBaseCalculoValor": icms_base,
                "ibsBaseCalculoAliquota": "00010",
                "ibsBaseCalculoValorImposto": ibs
            }

            # Preenchimento rigoroso
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

        # Footer
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
# 5. APP PRINCIPAL
# ==============================================================================

def main():
    apply_custom_ui()
    
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    st.image("https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png", width=200)
    st.title("Sistema Integrado DUIMP")
    st.markdown("Conversão de Extratos de Conferência (PDF) para XML Layout Rígido.")
    st.markdown('</div>', unsafe_allow_html=True)

    file = st.file_uploader("Upload PDF (Suporta 450+ Págs)", type="pdf")

    if file:
        if st.button("🚀 INICIAR PROCESSAMENTO"):
            try:
                with st.spinner("Lendo PDF e mapeando itens (pode demorar um pouco)..."):
                    # 1. Instancia Parser
                    p = PDFParserPlumber(file)
                    
                    # 2. Extração
                    p.extract_all()
                    
                    if not p.items:
                        st.error("Erro: Nenhum item encontrado. Verifique se o PDF contém 'ITENS DA DUIMP'.")
                    else:
                        # 3. Build XML
                        b = XMLBuilder(p)
                        xml = b.build()
                        
                        # Nome Arquivo
                        duimp_clean = p.header.get("duimp", "000").replace("/", "-")
                        fname = f"DUIMP_{duimp_clean}.xml"
                        
                        st.success(f"SUCESSO! {len(p.items)} itens processados com tributos.")
                        
                        # Preview
                        with st.expander("Verificar Dados Extraídos"):
                            st.json(p.items[:2]) # Mostra só 2 primeiros
                            
                        st.download_button(
                            label="📥 BAIXAR XML FINAL",
                            data=xml,
                            file_name=fname,
                            mime="text/xml"
                        )
            
            except Exception as e:
                st.error(f"Erro Fatal: {e}")

if __name__ == "__main__":
    main()
