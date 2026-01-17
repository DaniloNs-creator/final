import streamlit as st
import pdfplumber
import re
from lxml import etree
from xml.dom import minidom
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Häfele | DUIMP Converter V28 (Fix)", page_icon="🏗️", layout="wide")

# ==============================================================================
# 0. UI SETUP
# ==============================================================================
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
        h1 { color: #1e293b; font-weight: 700; }
        .stSuccess { border-left: 5px solid #28a745; }
        .stError { border-left: 5px solid #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. ESTRUTURA XML OBRIGATÓRIA (SEQUÊNCIA OBRIGATÓRIA)
# ==============================================================================

ADICAO_MAP = [
    {"tag": "acrescimo", "type": "complex", "children": [
        {"tag": "codigoAcrescimo", "default": "17"},
        {"tag": "denominacao", "default": "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"},
        {"tag": "moedaNegociadaCodigo", "default": "978"},
        {"tag": "moedaNegociadaNome", "default": "EURO/COM.EUROPEIA"},
        {"tag": "valorMoedaNegociada", "source": "v_frete_moeda"},
        {"tag": "valorReais", "source": "v_frete_reais"}
    ]},
    {"tag": "cideValorAliquotaEspecifica", "default": "00000000000"},
    {"tag": "cideValorDevido", "default": "000000000000000"},
    {"tag": "cideValorRecolher", "default": "000000000000000"},
    {"tag": "codigoRelacaoCompradorVendedor", "default": "3"},
    {"tag": "codigoVinculoCompradorVendedor", "default": "1"},
    {"tag": "cofinsAliquotaAdValorem", "source": "cofins_rate"}, 
    {"tag": "cofinsAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "cofinsAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "cofinsAliquotaReduzida", "default": "00000"},
    {"tag": "cofinsAliquotaValorDevido", "source": "cofins_val"},
    {"tag": "cofinsAliquotaValorRecolher", "source": "cofins_val"},
    {"tag": "condicaoVendaIncoterm", "default": "FCA"},
    {"tag": "condicaoVendaLocal", "default": ""},
    {"tag": "condicaoVendaMetodoValoracaoCodigo", "default": "01"},
    {"tag": "condicaoVendaMetodoValoracaoNome", "default": "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"},
    {"tag": "condicaoVendaMoedaCodigo", "default": "978"},
    {"tag": "condicaoVendaMoedaNome", "default": "EURO/COM.EUROPEIA"},
    {"tag": "condicaoVendaValorMoeda", "source": "v_total_reais"},
    {"tag": "condicaoVendaValorReais", "source": "v_total_reais"},
    {"tag": "dadosCambiaisCoberturaCambialCodigo", "default": "1"},
    {"tag": "dadosCambiaisCoberturaCambialNome", "default": "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"},
    {"tag": "dadosCambiaisInstituicaoFinanciadoraCodigo", "default": "00"},
    {"tag": "dadosCambiaisInstituicaoFinanciadoraNome", "default": "N/I"},
    {"tag": "dadosCambiaisMotivoSemCoberturaCodigo", "default": "00"},
    {"tag": "dadosCambiaisMotivoSemCoberturaNome", "default": "N/I"},
    {"tag": "dadosCambiaisValorRealCambio", "default": "000000000000000"},
    {"tag": "dadosCargaPaisProcedenciaCodigo", "default": "249"},
    {"tag": "dadosCargaUrfEntradaCodigo", "default": "0917800"},
    {"tag": "dadosCargaViaTransporteCodigo", "default": "01"},
    {"tag": "dadosCargaViaTransporteNome", "default": "MARÍTIMA"},
    {"tag": "dadosMercadoriaAplicacao", "default": "REVENDA"},
    {"tag": "dadosMercadoriaCodigoNaladiNCCA", "default": "0000000"},
    {"tag": "dadosMercadoriaCodigoNaladiSH", "default": "00000000"},
    {"tag": "dadosMercadoriaCodigoNcm", "source": "ncm"},
    {"tag": "dadosMercadoriaCondicao", "default": "NOVA"},
    {"tag": "dadosMercadoriaDescricaoTipoCertificado", "default": "Sem Certificado"},
    {"tag": "dadosMercadoriaIndicadorTipoCertificado", "default": "1"},
    {"tag": "dadosMercadoriaMedidaEstatisticaQuantidade", "source": "quantidade_fmt"},
    {"tag": "dadosMercadoriaMedidaEstatisticaUnidade", "default": "UNIDADE"},
    {"tag": "dadosMercadoriaNomeNcm", "default": "DESCRIÇÃO PADRÃO NCM"},
    {"tag": "dadosMercadoriaPesoLiquido", "source": "peso_fmt"},
    {"tag": "dcrCoeficienteReducao", "default": "00000"},
    {"tag": "dcrIdentificacao", "default": "00000000"},
    {"tag": "dcrValorDevido", "default": "000000000000000"},
    {"tag": "dcrValorDolar", "default": "000000000000000"},
    {"tag": "dcrValorReal", "default": "000000000000000"},
    {"tag": "dcrValorRecolher", "default": "000000000000000"},
    {"tag": "fornecedorCidade", "source": "fornecedor_cidade"},
    {"tag": "fornecedorLogradouro", "source": "fornecedor_logradouro"},
    {"tag": "fornecedorNome", "source": "fornecedor_nome"},
    {"tag": "fornecedorNumero", "source": "fornecedor_numero"},
    {"tag": "freteMoedaNegociadaCodigo", "default": "978"},
    {"tag": "freteMoedaNegociadaNome", "default": "EURO/COM.EUROPEIA"},
    {"tag": "freteValorMoedaNegociada", "default": "000000000000000"},
    {"tag": "freteValorReais", "default": "000000000000000"},
    {"tag": "iiAcordoTarifarioTipoCodigo", "default": "0"},
    {"tag": "iiAliquotaAcordo", "default": "00000"},
    {"tag": "iiAliquotaAdValorem", "source": "ii_rate"},
    {"tag": "iiAliquotaPercentualReducao", "default": "00000"},
    {"tag": "iiAliquotaReduzida", "default": "00000"},
    {"tag": "iiAliquotaValorCalculado", "default": "000000000000000"},
    {"tag": "iiAliquotaValorDevido", "source": "ii_val"},
    {"tag": "iiAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "iiAliquotaValorReduzido", "default": "000000000000000"},
    {"tag": "iiBaseCalculo", "default": "000000000000000"},
    {"tag": "iiFundamentoLegalCodigo", "default": "00"},
    {"tag": "iiMotivoAdmissaoTemporariaCodigo", "default": "00"},
    {"tag": "iiRegimeTributacaoCodigo", "default": "1"},
    {"tag": "iiRegimeTributacaoNome", "default": "RECOLHIMENTO INTEGRAL"},
    {"tag": "ipiAliquotaAdValorem", "source": "ipi_rate"},
    {"tag": "ipiAliquotaEspecificaCapacidadeRecipciente", "default": "00000"},
    {"tag": "ipiAliquotaEspecificaQuantidadeUnidadeMedida", "default": "000000000"},
    {"tag": "ipiAliquotaEspecificaTipoRecipienteCodigo", "default": "00"},
    {"tag": "ipiAliquotaEspecificaValorUnidadeMedida", "default": "0000000000"},
    {"tag": "ipiAliquotaNotaComplementarTIPI", "default": "00"},
    {"tag": "ipiAliquotaReduzida", "default": "00000"},
    {"tag": "ipiAliquotaValorDevido", "source": "ipi_val"},
    {"tag": "ipiAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "ipiRegimeTributacaoCodigo", "default": "4"},
    {"tag": "ipiRegimeTributacaoNome", "default": "SEM BENEFICIO"},
    {"tag": "mercadoria", "type": "complex", "children": [
        {"tag": "descricaoMercadoria", "source": "descricao_completa"}, 
        {"tag": "numeroSequencialItem", "default": "01"},
        {"tag": "quantidade", "source": "quantidade_fmt"},
        {"tag": "unidadeMedida", "source": "unidade"},
        {"tag": "valorUnitario", "source": "v_unit_fmt"}
    ]},
    {"tag": "numeroAdicao", "source": "numeroAdicao"},
    {"tag": "numeroDUIMP", "source": "numeroDUIMP"},
    {"tag": "numeroLI", "default": "0000000000"},
    {"tag": "paisAquisicaoMercadoriaCodigo", "default": "249"}, 
    {"tag": "paisAquisicaoMercadoriaNome", "default": "ESTADOS UNIDOS"},
    {"tag": "paisOrigemMercadoriaCodigo", "default": "249"},
    {"tag": "paisOrigemMercadoriaNome", "default": "ESTADOS UNIDOS"},
    {"tag": "pisCofinsBaseCalculoAliquotaICMS", "default": "00000"},
    {"tag": "pisCofinsBaseCalculoFundamentoLegalCodigo", "default": "00"},
    {"tag": "pisCofinsBaseCalculoPercentualReducao", "default": "00000"},
    {"tag": "pisCofinsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "pisCofinsFundamentoLegalReducaoCodigo", "default": "00"},
    {"tag": "pisCofinsRegimeTributacaoCodigo", "default": "1"},
    {"tag": "pisCofinsRegimeTributacaoNome", "default": "RECOLHIMENTO INTEGRAL"},
    {"tag": "pisPasepAliquotaAdValorem", "source": "pis_rate"},
    {"tag": "pisPasepAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "pisPasepAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "pisPasepAliquotaReduzida", "default": "00000"},
    {"tag": "pisPasepAliquotaValorDevido", "source": "pis_val"},
    {"tag": "pisPasepAliquotaValorRecolher", "source": "pis_val"},
    {"tag": "icmsBaseCalculoValor", "source": "icms_base"},
    {"tag": "icmsBaseCalculoAliquota", "default": "01800"},
    {"tag": "icmsBaseCalculoValorImposto", "default": "00000000000000"},
    {"tag": "icmsBaseCalculoValorDiferido", "default": "00000000000000"},
    {"tag": "cbsIbsCst", "default": "000"},
    {"tag": "cbsIbsClasstrib", "default": "000001"},
    {"tag": "cbsBaseCalculoValor", "source": "icms_base"},
    {"tag": "cbsBaseCalculoAliquota", "default": "00090"}, # 0.9%
    {"tag": "cbsBaseCalculoAliquotaReducao", "default": "00000"},
    {"tag": "cbsBaseCalculoValorImposto", "source": "cbs_val"}, 
    {"tag": "ibsBaseCalculoValor", "source": "icms_base"},
    {"tag": "ibsBaseCalculoAliquota", "default": "00010"}, # 0.1%
    {"tag": "ibsBaseCalculoAliquotaReducao", "default": "00000"},
    {"tag": "ibsBaseCalculoValorImposto", "source": "ibs_val"}, 
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
    {"tag": "valorTotalCondicaoVenda", "source": "v_total_11"},
    {"tag": "vinculoCompradorVendedor", "default": "Não há vinculação entre comprador e vendedor."}
]

# Tags de Rodapé
FOOTER_TEMPLATE = {
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
    
    # --- DADOS DO IMPORTADOR ---
    "importadorCodigoTipo": "1",
    "importadorCpfRepresentanteLegal": "00000000000",
    "importadorEnderecoBairro": "JARDIM PRIMAVERA",
    "importadorEnderecoCep": "83302000",
    "importadorEnderecoComplemento": "CONJ: 6 E 7;",
    "importadorEnderecoLogradouro": "JOAO LEOPOLDO JACOMEL",
    "importadorEnderecoMunicipio": "PIRAQUARA",
    "importadorEnderecoNumero": "4459",
    "importadorEnderecoUf": "PR",
    "importadorNome": "HAFELE BRASIL LTDA",
    "importadorNomeRepresentanteLegal": "PAULO HENRIQUE LEITE FERREIRA",
    "importadorNumero": "02473058000188",
    "importadorNumeroTelefone": "41 30348150",
    # ---------------------------
    
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
# 2. UTILS (DATAFORMATTER)
# ==============================================================================

class DataFormatter:
    @staticmethod
    def clean_text(text):
        if not text: return ""
        return re.sub(r'\s+', ' ', str(text).replace('\n', ' ')).strip()

    @staticmethod
    def format_number(value, length=15):
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
        except: return "00000"

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
            cbs_str = str(int(round(cbs_val * 100))).zfill(14)
            ibs_val = base_float * 0.001
            ibs_str = str(int(round(ibs_val * 100))).zfill(14)
            return cbs_str, ibs_str
        except: return "0".zfill(14), "0".zfill(14)

    @staticmethod
    def clean_partnumber(text):
        if not text: return ""
        match = re.search(r"(.*?)(?:PAIS|FABRICANTE)", text, re.I | re.S)
        if match: text = match.group(1)
        return re.sub(r'\s+', ' ', text).strip().lstrip("- ").strip()

    @staticmethod
    def get_pn_from_block(text):
        # Tenta pegar CÓDIGO INTERNO (PARTNUMBER)
        match = re.search(r"CÓDIGO INTERNO\s*\(PARTNUMBER\)\s*[:\n]?\s*(.+?)(?=\n)", text, re.I)
        if not match:
            # Fallback para PARTNUMBER)
            match = re.search(r"PARTNUMBER\)\s*(.+?)(?=\n|PAIS|FABRICANTE)", text, re.I | re.S)
        
        if match:
            return DataFormatter.clean_partnumber(match.group(1))
        return ""

    @staticmethod
    def get_desc_from_block(text):
        match = re.search(r"DENOMINACAO DO PRODUTO\s*[:\n]?\s*(.+?)(?=\n|CÓDIGO)", text, re.I | re.S)
        if match:
            return DataFormatter.clean_text(match.group(1))
        return ""

    @staticmethod
    def parse_supplier_info(raw_name):
        return {"fornecedorNome": "FORNECEDOR PADRAO", "fornecedorLogradouro": "RUA X", "fornecedorNumero": "00", "fornecedorCidade": "EXTERIOR"}

# ==============================================================================
# 3. EXTRAÇÃO ROBUSTA (PDFPLUMBER + STITCHING)
# ==============================================================================

class PDFProcessor:
    def __init__(self, file):
        self.file = file
        self.text = ""
        self.header = {}
        self.items = []

    def run(self):
        # 1. Leitura e Costura
        with pdfplumber.open(self.file) as pdf:
            pages = []
            total = len(pdf.pages)
            bar = st.progress(0)
            
            garbage = [
                r"Extrato de conferencia", r"Data, hora", r"Versão \d+", 
                r"--- PAGE \d+", r"^\s*\d+\s*$", r"^\s*\/ \d+\s*$"
            ]
            
            for i, page in enumerate(pdf.pages):
                txt = page.extract_text() or ""
                lines = [l for l in txt.split('\n') if not any(re.search(g, l, re.I) for g in garbage)]
                pages.append("\n".join(lines))
                if i % 5 == 0: bar.progress((i+1)/total)
            bar.progress(100)
            
        self.text = "\n".join(pages)
        
        # 2. Cabeçalho
        duimp = re.search(r"Numero\s*[:\n]*\s*([\dBR]+)", self.text, re.I)
        self.header["duimp"] = duimp.group(1) if duimp else "00000000000"
        
        imp_match = re.search(r"IMPORTADOR\s*[:\n,]*\s*\"?([A-Z\s\.]+)(?:\n|\"|CNPJ)", self.text, re.IGNORECASE)
        self.header["importadorNome"] = imp_match.group(1).strip() if imp_match else "HAFELE BRASIL LTDA"

        pb = re.search(r"PESO BRUTO KG\s*[:]?\s*([\d.,]+)", self.text, re.I)
        self.header["pb"] = pb.group(1) if pb else "0"
        pl = re.search(r"PESO LIQUIDO KG\s*[:]?\s*([\d.,]+)", self.text, re.I)
        self.header["pl"] = pl.group(1) if pl else "0"

        # 3. Itens
        # Usa regex para dividir por "Nº Adição X"
        splits = re.split(r"(Nº\s*Adição\s*[:\n]?\s*\d+)", self.text, flags=re.I)
        
        if len(splits) > 1:
            for i in range(1, len(splits), 2):
                marker = splits[i]
                content = splits[i+1] # Conteúdo do item
                
                adi_num = re.search(r"\d+", marker).group()
                
                pn = DataFormatter.get_pn_from_block(content)
                desc = DataFormatter.get_desc_from_block(content)
                full_desc = f"{pn} - {desc}" if pn else desc
                if not full_desc: full_desc = f"ITEM {adi_num}"
                
                ncm = re.search(r"NCM\s*[:\n]*\s*([\d\.]+)", content)
                qtd = re.search(r"Qtde Unid\. Estatística\s*[:\n]?\s*([\d.,]+)", content, re.I)
                peso = re.search(r"Peso Líquido \(KG\)\s*[:\n]?\s*([\d.,]+)", content, re.I)
                val_tot = re.search(r"Valor Tot\. Cond Venda\s*[:\n]?\s*([\d.,]+)", content, re.I)
                
                taxes = self._get_taxes(content)
                
                self.items.append({
                    "numeroAdicao": adi_num.zfill(3),
                    "descricao_completa": full_desc,
                    "ncm": ncm.group(1) if ncm else "00000000",
                    "quantidade_fmt": DataFormatter.format_number(qtd.group(1), 14) if qtd else "0"*14,
                    "peso_fmt": DataFormatter.format_number(peso.group(1), 15) if peso else "0"*15,
                    "unidade": "UNIDADE",
                    "v_total_reais": DataFormatter.format_number(val_tot.group(1), 15) if val_tot else "0"*15,
                    "v_total_11": DataFormatter.format_number(val_tot.group(1), 11) if val_tot else "0"*11,
                    "v_unit_fmt": DataFormatter.format_number("0", 20),
                    "v_frete_reais": "0"*15,
                    "v_frete_moeda": "0"*15,
                    "fornecedor_nome": "FORNECEDOR PADRAO",
                    "fornecedor_logradouro": "ENDERECO",
                    "fornecedor_numero": "00",
                    "fornecedor_cidade": "EXTERIOR",
                    **taxes
                })

    def _get_taxes(self, text):
        res = {}
        map_tax = {"ii": "IMPOSTO DE IMPORTAÇÃO", "ipi": "IPI", "pis": "PIS/PASEP", "cofins": "COFINS"}
        for k, label in map_tax.items():
            res[f"{k}_rate"] = "00000"
            res[f"{k}_val"] = "0"*15
            idx = text.find(label)
            if idx != -1:
                sub = text[idx:idx+300]
                nums = re.findall(r"([\d]{1,3}(?:[.]\d{3})*,\d{2,4})", sub)
                candidates = []
                for n in nums:
                    try: 
                        v = float(n.replace('.','').replace(',','.'))
                        candidates.append((v, n))
                    except: pass
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    res[f"{k}_rate"] = str(candidates[0][1])
                    if len(candidates) >= 2:
                        res[f"{k}_val"] = str(candidates[1][1])
        return res

# ==============================================================================
# 4. GERADOR XML
# ==============================================================================

class XMLGenerator:
    def generate(self, parser):
        root = etree.Element("ListaDeclaracoes")
        duimp = etree.SubElement(root, "duimp")
        
        # Itens
        for item in parser.items:
            ad = etree.SubElement(duimp, "adicao")
            cbs, ibs = DataFormatter.calculate_cbs_ibs(item["v_total_reais"])
            item["cbs_val"] = cbs
            item["ibs_val"] = ibs
            item["icms_base"] = item["v_total_reais"]
            item["numeroDUIMP"] = re.sub(r'[^a-zA-Z0-9]', '', parser.header["duimp"])

            for field in ADICAO_MAP:
                t = field["tag"]
                if field.get("type") == "complex":
                    parent = etree.SubElement(ad, t)
                    for child in field["children"]:
                        val = self._resolve_val(child, item)
                        etree.SubElement(parent, child["tag"]).text = val
                else:
                    val = self._resolve_val(field, item)
                    etree.SubElement(ad, t).text = val

        # Footer
        for tag, config in FOOTER_TEMPLATE.items():
            if isinstance(config, list):
                parent = etree.SubElement(duimp, tag)
                for sub in config: etree.SubElement(parent, sub["tag"]).text = sub["default"]
            elif isinstance(config, dict):
                parent = etree.SubElement(duimp, tag)
                etree.SubElement(parent, config["tag"]).text = config["default"]
            else:
                val = config
                if tag == "numeroDUIMP": val = re.sub(r'[^a-zA-Z0-9]', '', parser.header["duimp"])
                if tag == "cargaPesoBruto": val = DataFormatter.format_number(parser.header["pb"], 15)
                if tag == "cargaPesoLiquido": val = DataFormatter.format_number(parser.header["pl"], 15)
                if tag == "totalAdicoes": val = str(len(parser.items)).zfill(3)
                # O Importador já vem fixo do template
                etree.SubElement(duimp, tag).text = str(val)

        # Formatação Final
        raw = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
        try:
            parsed = minidom.parseString(raw)
            pretty = parsed.toprettyxml(indent="    ")
            return re.sub(r'<\?xml.*?\?>', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', pretty, count=1)
        except: return raw

    def _resolve_val(self, field_config, item_data):
        if "source" in field_config:
            src = field_config["source"]
            if src in item_data:
                raw_val = item_data[src]
                if "rate" in src: return DataFormatter.format_rate_xml(raw_val)
                if "val" in src and "fmt" not in src: return DataFormatter.format_number(raw_val, 15)
                return str(raw_val)
        return field_config["default"]

# ==============================================================================
# 5. EXECUÇÃO
# ==============================================================================

def main():
    apply_custom_ui()
    st.markdown('<div class="header-container"><h1>Häfele | DUIMP Converter</h1></div>', unsafe_allow_html=True)
    
    f = st.file_uploader("Upload PDF", type="pdf")
    if f and st.button("PROCESSAR"):
        with st.spinner("Processando..."):
            proc = PDFProcessor(f)
            proc.run()
            
            gen = XMLGenerator()
            xml = gen.generate(proc)
            
            st.success(f"Sucesso! {len(proc.items)} itens processados.")
            st.download_button("Baixar XML", xml, f"DUIMP_{proc.header['duimp']}.xml", "text/xml")

if __name__ == "__main__":
    main()
