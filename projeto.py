import streamlit as st
import fitz  # PyMuPDF
import pdfplumber
import re
import pandas as pd
import numpy as np
from lxml import etree
import tempfile
import os
import logging
from typing import Dict, List, Optional

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA (UNIFICADA)
# ==============================================================================
st.set_page_config(
    page_title="Sistema Integrado DUIMP 2026 (XML + Häfele)",
    page_icon="🚀",
    layout="wide"
)

# CSS Personalizado (Mistura dos dois estilos)
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1E3A8A; font-weight: bold; margin-bottom: 1rem; }
    .sub-header { font-size: 1.5rem; color: #2563EB; margin-top: 2rem; border-bottom: 2px solid #E5E7EB; }
    .section-card { background: #F8FAFC; border-radius: 8px; padding: 1rem; border: 1px solid #E2E8F0; margin-bottom: 1rem; }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #0F172A; }
    .metric-label { font-size: 0.9rem; color: #64748B; }
    .success-box { background-color: #D1FAE5; border: 1px solid #10B981; color: #065F46; padding: 10px; border-radius: 5px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# PARTE 1: CLASSES DO APP 2 (FONTE DE DADOS - HÄFELE)
# ==============================================================================

class HafelePDFParser:
    """Parser robusto para PDFs da Häfele (App 2 Original)"""
    
    def __init__(self):
        self.documento = {'cabecalho': {}, 'itens': [], 'totais': {}}
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text: all_text += text + "\n"
            
            self._process_full_text(all_text)
            return self.documento
            
    def _process_full_text(self, text: str):
        items = self._find_all_items(text)
        self.documento['itens'] = items
        self._calculate_totals()
    
    def _find_all_items(self, text: str) -> List[Dict]:
        items = []
        item_pattern = r'(?:^|\n)(\d+)\s+(\d{4}\.\d{2}\.\d{2})\s+(\d+)\s'
        matches = list(re.finditer(item_pattern, text))
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            item_text = text[start_pos:end_pos]
            item_data = self._parse_item(item_text, match.group(1), match.group(2), match.group(3))
            if item_data: items.append(item_data)
        return items
    
    def _parse_item(self, text: str, item_num: str, ncm: str, codigo: str) -> Optional[Dict]:
        try:
            item = {
                'numero_item': item_num,
                'ncm': ncm,
                'codigo_produto': codigo,
                'codigo_interno': '',
                'quantidade': 0,
                'peso_liquido': 0,
                'valor_total': 0,
                'local_aduaneiro': 0,
                'frete_internacional': 0,
                'seguro_internacional': 0,
                # Impostos
                'ii_valor_devido': 0, 'ipi_valor_devido': 0, 'pis_valor_devido': 0, 'cofins_valor_devido': 0,
                # Bases
                'ii_base_calculo': 0, 'ipi_base_calculo': 0, 'pis_base_calculo': 0, 'cofins_base_calculo': 0,
                # Alíquotas
                'ii_aliquota': 0, 'ipi_aliquota': 0, 'pis_aliquota': 0, 'cofins_aliquota': 0
            }
            
            # Extração Regex (Original do App 2)
            codigo_match = re.search(r'Código interno\s*(.*?)\s*(?=FABRICANTE|Conhecido|Pais)', text, re.IGNORECASE | re.DOTALL)
            if codigo_match:
                raw_code = codigo_match.group(1)
                item['codigo_interno'] = raw_code.replace('(PARTNUMBER)', '').replace('Código interno', '').replace('\n', '').strip()

            # Valores
            def get_val(pattern, txt):
                m = re.search(pattern, txt, re.IGNORECASE | re.DOTALL)
                return self._parse_valor(m.group(1)) if m else 0.0

            item['quantidade'] = get_val(r'Qtde Unid\. Comercial\s+([\d\.,]+)', text)
            item['peso_liquido'] = get_val(r'Peso Líquido \(KG\)\s+([\d\.,]+)', text)
            item['valor_total'] = get_val(r'Valor Tot\. Cond Venda\s+([\d\.,]+)', text)
            item['local_aduaneiro'] = get_val(r'Local Aduaneiro \(R\$\)\s*([\d\.,]+)', text)
            item['frete_internacional'] = get_val(r'Frete Internac\. \(R\$\)\s+([\d\.,]+)', text)
            item['seguro_internacional'] = get_val(r'Seguro Internac\. \(R\$\)\s+([\d\.,]+)', text)

            # Impostos Diretos
            tax_map = {
                'ii_valor_devido': r'II.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
                'ipi_valor_devido': r'IPI.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
                'pis_valor_devido': r'PIS.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
                'cofins_valor_devido': r'COFINS.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
                'ii_base_calculo': r'II.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
                'ipi_base_calculo': r'IPI.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
                'pis_base_calculo': r'PIS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
                'cofins_base_calculo': r'COFINS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
                'ii_aliquota': r'II.*?% Alíquota\s*([\d\.,]+)',
                'ipi_aliquota': r'IPI.*?% Alíquota\s*([\d\.,]+)',
                'pis_aliquota': r'PIS.*?% Alíquota\s*([\d\.,]+)',
                'cofins_aliquota': r'COFINS.*?% Alíquota\s*([\d\.,]+)'
            }
            
            for k, v in tax_map.items():
                item[k] = get_val(v, text)
                
            return item
        except: return None

    def _calculate_totals(self):
        # Simplificado para o essencial
        pass

    def _parse_valor(self, valor_str: str) -> float:
        try:
            return float(valor_str.replace('.', '').replace(',', '.'))
        except: return 0.0

class FinancialAnalyzer:
    def __init__(self, documento: Dict):
        self.documento = documento
    
    def get_dataframe(self):
        return pd.DataFrame(self.documento['itens'])

# ==============================================================================
# PARTE 2: CLASSES DO APP 1 (PROCESSAMENTO DUIMP E XML BUILDER)
# ==============================================================================

# Definições de constantes (Layout 8686)
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
    "informacaoComplementar": "Informações extraídas do Extrato DUIMP.",
    "localDescargaTotalDolares": "000000000000000",
    "localDescargaTotalReais": "000000000000000",
    "localEmbarqueTotalDolares": "000000000000000",
    "localEmbarqueTotalReais": "000000000000000",
    "modalidadeDespachoCodigo": "1",
    "modalidadeDespachoNome": "Normal",
    "numeroDUIMP": "",
    "operacaoFundap": "N",
    "pagamento": [], 
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
    def format_ncm(value):
        if not value: return "00000000"
        return re.sub(r'\D', '', value)[:8]

    @staticmethod
    def format_input_fiscal(value, length=15, is_percent=False):
        try:
            if isinstance(value, str):
                value = value.replace('.', '')
                value = value.replace(',', '.')
            
            val_float = float(value)
            val_int = int(round(val_float * 100))
            return str(val_int).zfill(length)
        except:
            return "0" * length

    @staticmethod
    def format_high_precision(value, length=15):
        try:
            if isinstance(value, str):
                value = value.replace('.', '')
                value = value.replace(',', '.')
            
            val_float = float(value)
            val_int = int(round(val_float * 10000000))
            return str(val_int).zfill(length)
        except:
            return "0" * length

    @staticmethod
    def format_quantity(value, length=14):
        try:
            if isinstance(value, str):
                value = value.replace('.', '')
                value = value.replace(',', '.')
            
            val_float = float(value)
            val_int = int(round(val_float * 100000))
            return str(val_int).zfill(length)
        except:
            return "0" * length

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
        data = {"fornecedorNome": "", "fornecedorLogradouro": "", "fornecedorNumero": "S/N", "fornecedorCidade": ""}
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
                if num_match: data["fornecedorNumero"] = num_match.group(0)
            else:
                data["fornecedorLogradouro"] = street_part
        return data

class DuimpPDFParser:
    """Parser específico para o Extrato DUIMP (App 1)"""
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
        chunks = re.split(r"Item\s+(\d+)", self.full_text)
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
                
                exp_match = re.search(r"Código do Exportador Estrangeiro:\s*(.+?)(?=\n\s*(?:Endereço|Dados))", content, re.DOTALL)
                item["fornecedor_raw"] = exp_match.group(1).strip() if exp_match else ""
                
                addr_match = re.search(r"Endereço:\s*(.+?)(?=\n\s*(?:Dados da Mercadoria|Aplicação))", content, re.DOTALL)
                item["endereco_raw"] = addr_match.group(1).strip() if addr_match else ""

                desc_match = re.search(r"Detalhamento do Produto:\s*(.+?)(?=\n\s*(?:Número de Identificação|Versão|Código de Class|Descrição complementar))", content, re.DOTALL)
                item["descricao"] = desc_match.group(1).strip() if desc_match else ""
                
                self.items.append(item)

    def _regex(self, pattern, text):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""

class XMLBuilder:
    def __init__(self, parser, edited_items=None):
        self.p = parser
        self.items_to_use = edited_items if edited_items else self.p.items
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self):
        h = self.p.header
        duimp_fmt = h.get("numeroDUIMP", "").split("/")[0].replace("-", "").replace(".", "")
        
        totals = {"frete": 0.0, "seguro": 0.0, "ii": 0.0, "ipi": 0.0, "pis": 0.0, "cofins": 0.0}

        def get_float(val):
            try: 
                if isinstance(val, str): val = val.replace('.', '').replace(',', '.')
                return float(val)
            except: return 0.0

        for it in self.items_to_use:
            totals["frete"] += get_float(it.get("Frete (R$)", 0))
            totals["seguro"] += get_float(it.get("Seguro (R$)", 0))
            totals["ii"] += get_float(it.get("II (R$)", 0))
            totals["ipi"] += get_float(it.get("IPI (R$)", 0))
            totals["pis"] += get_float(it.get("PIS (R$)", 0))
            totals["cofins"] += get_float(it.get("COFINS (R$)", 0))

        for it in self.items_to_use:
            adicao = etree.SubElement(self.duimp, "adicao")
            
            input_number = str(it.get("NUMBER", "")).strip()
            original_desc = DataFormatter.clean_text(it.get("descricao", ""))
            final_desc = f"{input_number} - {original_desc}" if input_number else original_desc

            val_total_venda_fmt = DataFormatter.format_high_precision(it.get("valorTotal", "0"), 11)
            val_unit_fmt = DataFormatter.format_high_precision(it.get("valorUnit", "0"), 20)
            qtd_fmt = DataFormatter.format_quantity(it.get("quantidade"), 14)
            peso_liq_fmt = DataFormatter.format_quantity(it.get("pesoLiq"), 15)
            base_total_reais_fmt = DataFormatter.format_input_fiscal(it.get("valorTotal", "0"), 15)
            
            raw_frete = get_float(it.get("Frete (R$)", 0))
            raw_seguro = get_float(it.get("Seguro (R$)", 0))
            raw_aduaneiro = get_float(it.get("Aduaneiro (R$)", 0))
            
            frete_fmt = DataFormatter.format_input_fiscal(raw_frete)
            seguro_fmt = DataFormatter.format_input_fiscal(raw_seguro)
            aduaneiro_fmt = DataFormatter.format_input_fiscal(raw_aduaneiro)

            ii_base_fmt = DataFormatter.format_input_fiscal(it.get("II Base (R$)", 0))
            ii_aliq_fmt = DataFormatter.format_input_fiscal(it.get("II Alíq. (%)", 0), 5, True)
            ii_val_fmt = DataFormatter.format_input_fiscal(get_float(it.get("II (R$)", 0)))

            ipi_aliq_fmt = DataFormatter.format_input_fiscal(it.get("IPI Alíq. (%)", 0), 5, True)
            ipi_val_fmt = DataFormatter.format_input_fiscal(get_float(it.get("IPI (R$)", 0)))

            pis_base_fmt = DataFormatter.format_input_fiscal(it.get("PIS Base (R$)", 0))
            pis_aliq_fmt = DataFormatter.format_input_fiscal(it.get("PIS Alíq. (%)", 0), 5, True)
            pis_val_fmt = DataFormatter.format_input_fiscal(get_float(it.get("PIS (R$)", 0)))

            cofins_aliq_fmt = DataFormatter.format_input_fiscal(it.get("COFINS Alíq. (%)", 0), 5, True)
            cofins_val_fmt = DataFormatter.format_input_fiscal(get_float(it.get("COFINS (R$)", 0)))

            icms_base_valor = ii_base_fmt if int(ii_base_fmt) > 0 else base_total_reais_fmt
            cbs_imposto, ibs_imposto = DataFormatter.calculate_cbs_ibs(icms_base_valor)
            
            supplier_data = DataFormatter.parse_supplier_info(it.get("fornecedor_raw"), it.get("endereco_raw"))

            extracted_map = {
                "numeroAdicao": str(it["numeroAdicao"])[-3:],
                "numeroDUIMP": duimp_fmt,
                "dadosMercadoriaCodigoNcm": DataFormatter.format_ncm(it.get("ncm")),
                "dadosMercadoriaMedidaEstatisticaQuantidade": qtd_fmt,
                "dadosMercadoriaMedidaEstatisticaUnidade": it.get("unidade", "").upper(),
                "dadosMercadoriaPesoLiquido": peso_liq_fmt,
                "condicaoVendaMoedaNome": it.get("moeda", "").upper(),
                "valorTotalCondicaoVenda": val_total_venda_fmt,
                "valorUnitario": val_unit_fmt,
                "condicaoVendaValorMoeda": base_total_reais_fmt,
                "condicaoVendaValorReais": aduaneiro_fmt if int(aduaneiro_fmt) > 0 else base_total_reais_fmt,
                "paisOrigemMercadoriaNome": it.get("paisOrigem", "").upper(),
                "paisAquisicaoMercadoriaNome": it.get("paisOrigem", "").upper(),
                "descricaoMercadoria": final_desc,
                "quantidade": qtd_fmt,
                "unidadeMedida": it.get("unidade", "").upper(),
                "dadosCargaUrfEntradaCodigo": h.get("urf", "0917800"),
                "fornecedorNome": supplier_data["fornecedorNome"][:60],
                "fornecedorLogradouro": supplier_data["fornecedorLogradouro"][:60],
                "fornecedorNumero": supplier_data["fornecedorNumero"][:10],
                "fornecedorCidade": supplier_data["fornecedorCidade"][:30],
                "freteValorReais": frete_fmt,
                "seguroValorReais": seguro_fmt,
                "iiBaseCalculo": ii_base_fmt,
                "iiAliquotaAdValorem": ii_aliq_fmt,
                "iiAliquotaValorDevido": ii_val_fmt,
                "iiAliquotaValorRecolher": ii_val_fmt,
                "ipiAliquotaAdValorem": ipi_aliq_fmt,
                "ipiAliquotaValorDevido": ipi_val_fmt,
                "ipiAliquotaValorRecolher": ipi_val_fmt,
                "pisCofinsBaseCalculoValor": pis_base_fmt,
                "pisPasepAliquotaAdValorem": pis_aliq_fmt,
                "pisPasepAliquotaValorDevido": pis_val_fmt,
                "pisPasepAliquotaValorRecolher": pis_val_fmt,
                "cofinsAliquotaAdValorem": cofins_aliq_fmt,
                "cofinsAliquotaValorDevido": cofins_val_fmt,
                "cofinsAliquotaValorRecolher": cofins_val_fmt,
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

        peso_bruto_fmt = DataFormatter.format_quantity(h.get("pesoBruto"), 15)
        peso_liq_total_fmt = DataFormatter.format_quantity(h.get("pesoLiquido"), 15)

        footer_map = {
            "numeroDUIMP": duimp_fmt,
            "importadorNome": h.get("nomeImportador", ""),
            "importadorNumero": DataFormatter.format_number(h.get("cnpj"), 14),
            "cargaPesoBruto": peso_bruto_fmt,
            "cargaPesoLiquido": peso_liq_total_fmt,
            "cargaPaisProcedenciaNome": h.get("paisProcedencia", "").upper(),
            "totalAdicoes": str(len(self.items_to_use)).zfill(3),
            "freteTotalReais": DataFormatter.format_input_fiscal(totals["frete"]),
            "seguroTotalReais": DataFormatter.format_input_fiscal(totals["seguro"]),
        }

        receita_codes = [
            {"code": "0086", "val": totals["ii"]},
            {"code": "1038", "val": totals["ipi"]},
            {"code": "5602", "val": totals["pis"]},
            {"code": "5629", "val": totals["cofins"]}
        ]

        for tag, default_val in FOOTER_TAGS.items():
            if tag == "pagamento":
                for rec in receita_codes:
                    if rec["val"] > 0:
                        pag = etree.SubElement(self.duimp, "pagamento")
                        etree.SubElement(pag, "agenciaPagamento").text = "3715"
                        etree.SubElement(pag, "bancoPagamento").text = "341"
                        etree.SubElement(pag, "codigoReceita").text = rec["code"]
                        etree.SubElement(pag, "valorReceita").text = DataFormatter.format_input_fiscal(rec["val"])
                continue

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
# MAIN APP INTEGRADO
# ==============================================================================

def main():
    st.markdown('<h1 class="main-header">🏭 Conversor DUIMP & Analisador Häfele (Versão Final 2026)</h1>', unsafe_allow_html=True)

    # --- INICIALIZAÇÃO DO STATE ---
    if "parsed_duimp" not in st.session_state: st.session_state["parsed_duimp"] = None
    if "parsed_hafele" not in st.session_state: st.session_state["parsed_hafele"] = None
    if "merged_df" not in st.session_state: st.session_state["merged_df"] = None

    # --- SIDEBAR DE UPLOAD ---
    with st.sidebar:
        st.header("📂 Arquivos de Entrada")
        file_hafele = st.file_uploader("1. Relatório Häfele (FONTE)", type="pdf")
        file_duimp = st.file_uploader("2. Extrato DUIMP (DESTINO)", type="pdf")
        st.info("Carregue ambos para ativar o botão 'VINCULAR'.")

    # --- PROCESSAMENTO APP 2 (HÄFELE) ---
    if file_hafele:
        # Processa apenas se mudou ou se ainda não processou
        # Salva em temp file para pdfplumber
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(file_hafele.getvalue())
            tmp_path = tmp_file.name

        try:
            parser_hafele = HafelePDFParser()
            doc_hafele = parser_hafele.parse_pdf(tmp_path)
            st.session_state["parsed_hafele"] = doc_hafele
            analyzer = FinancialAnalyzer(doc_hafele)
            df_hafele = analyzer.get_dataframe()
            
            # Exibe Metrics Rápidas
            with st.expander("📊 Visão Geral - Relatório Häfele (Dados Extraídos)", expanded=False):
                col1, col2, col3 = st.columns(3)
                totais = doc_hafele['totais']
                col1.metric("Itens", len(doc_hafele['itens']))
                # Recalcula totais rápidos caso o parser simplificado não tenha feito
                total_merc = df_hafele['valor_total'].sum()
                total_imp = df_hafele['ii_valor_devido'].sum() + df_hafele['ipi_valor_devido'].sum() + df_hafele['pis_valor_devido'].sum() + df_hafele['cofins_valor_devido'].sum()
                col2.metric("Total Mercadoria", f"R$ {total_merc:,.2f}")
                col3.metric("Total Impostos", f"R$ {total_imp:,.2f}")
                st.dataframe(df_hafele.head(5))

        except Exception as e:
            st.error(f"Erro no PDF Häfele: {e}")
        finally:
            if os.path.exists(tmp_path): os.unlink(tmp_path)

    # --- PROCESSAMENTO APP 1 (DUIMP) ---
    if file_duimp:
        if st.session_state["parsed_duimp"] is None or file_duimp.name != getattr(st.session_state.get("last_duimp_file"), "name", ""):
             try:
                p = DuimpPDFParser(file_duimp.read())
                p.preprocess()
                p.extract_header()
                p.extract_items()
                st.session_state["parsed_duimp"] = p
                st.session_state["last_duimp_file"] = file_duimp
                
                # Inicializa DataFrame do DUIMP
                df_duimp = pd.DataFrame(p.items)
                cols_fiscais = [
                    "NUMBER", "Frete (R$)", "Seguro (R$)", 
                    "II (R$)", "II Base (R$)", "II Alíq. (%)",
                    "IPI (R$)", "IPI Base (R$)", "IPI Alíq. (%)",
                    "PIS (R$)", "PIS Base (R$)", "PIS Alíq. (%)",
                    "COFINS (R$)", "COFINS Base (R$)", "COFINS Alíq. (%)",
                    "Aduaneiro (R$)"
                ]
                # Cria colunas vazias
                for col in cols_fiscais:
                    df_duimp[col] = 0.00
                    if col == "NUMBER": df_duimp[col] = ""

                st.session_state["merged_df"] = df_duimp

             except Exception as e:
                st.error(f"Erro no PDF DUIMP: {e}")

    # --- LÓGICA DE VINCULAÇÃO (O RECURSO SOLICITADO) ---
    st.divider()
    
    col_vinc, col_info = st.columns([1, 3])
    
    with col_vinc:
        if st.button("🔄 VINCULAR DADOS (Häfele -> DUIMP)", type="primary", use_container_width=True):
            if st.session_state["parsed_duimp"] and st.session_state["parsed_hafele"]:
                try:
                    df_dest = st.session_state["merged_df"].copy()
                    
                    # Convertendo dados do Häfele para dicionário indexado pelo 'numero_item' (int)
                    src_map = {}
                    for item in st.session_state["parsed_hafele"]['itens']:
                        try:
                            idx = int(item['numero_item'])
                            src_map[idx] = item
                        except: pass
                    
                    # Iterar e preencher
                    count = 0
                    for index, row in df_dest.iterrows():
                        try:
                            item_duimp = int(row['numeroAdicao'])
                            if item_duimp in src_map:
                                src = src_map[item_duimp]
                                
                                # PREENCHE O 'NUMBER' COM 'CODIGO_INTERNO'
                                df_dest.at[index, 'NUMBER'] = src.get('codigo_interno', '')
                                
                                # PREENCHE VALORES
                                df_dest.at[index, 'Frete (R$)'] = src.get('frete_internacional', 0.0)
                                df_dest.at[index, 'Seguro (R$)'] = src.get('seguro_internacional', 0.0)
                                df_dest.at[index, 'Aduaneiro (R$)'] = src.get('local_aduaneiro', 0.0)
                                
                                # PREENCHE IMPOSTOS (Valores, Bases e Alíquotas)
                                df_dest.at[index, 'II (R$)'] = src.get('ii_valor_devido', 0.0)
                                df_dest.at[index, 'II Base (R$)'] = src.get('ii_base_calculo', 0.0)
                                df_dest.at[index, 'II Alíq. (%)'] = src.get('ii_aliquota', 0.0)
                                
                                df_dest.at[index, 'IPI (R$)'] = src.get('ipi_valor_devido', 0.0)
                                df_dest.at[index, 'IPI Base (R$)'] = src.get('ipi_base_calculo', 0.0)
                                df_dest.at[index, 'IPI Alíq. (%)'] = src.get('ipi_aliquota', 0.0)
                                
                                df_dest.at[index, 'PIS (R$)'] = src.get('pis_valor_devido', 0.0)
                                df_dest.at[index, 'PIS Base (R$)'] = src.get('pis_base_calculo', 0.0)
                                df_dest.at[index, 'PIS Alíq. (%)'] = src.get('pis_aliquota', 0.0)
                                
                                df_dest.at[index, 'COFINS (R$)'] = src.get('cofins_valor_devido', 0.0)
                                df_dest.at[index, 'COFINS Base (R$)'] = src.get('cofins_base_calculo', 0.0)
                                df_dest.at[index, 'COFINS Alíq. (%)'] = src.get('cofins_aliquota', 0.0)
                                
                                count += 1
                        except Exception as e:
                            print(f"Erro item {index}: {e}")
                            
                    st.session_state["merged_df"] = df_dest
                    st.markdown(f'<div class="success-box">✅ Sucesso! {count} itens foram vinculados e preenchidos automaticamente.</div>', unsafe_allow_html=True)
                
                except Exception as e:
                    st.error(f"Erro na vinculação: {e}")
            else:
                st.warning("⚠️ Carregue os dois arquivos PDF primeiro.")

    with col_info:
        st.caption("Este botão cruza o **Número da Adição/Item** dos dois arquivos. Ele preenche automaticamente os campos fiscais e o NUMBER (usando o Código Interno do Häfele).")

    # --- EDITOR DE DADOS ---
    if st.session_state["merged_df"] is not None:
        st.markdown('<h3 class="sub-header">📝 Edição e Conferência Final</h3>', unsafe_allow_html=True)
        
        # Colunas para exibir
        cols_display = ["numeroAdicao", "NUMBER", "Frete (R$)", "Seguro (R$)", "II (R$)", "IPI (R$)", "PIS (R$)", "COFINS (R$)"]
        
        edited_df = st.data_editor(
            st.session_state["merged_df"],
            hide_index=True,
            column_config={
                "numeroAdicao": st.column_config.TextColumn("Item", disabled=True),
                "NUMBER": st.column_config.TextColumn("NUMBER (Cód. Interno)", help="Será concatenado na descrição"),
                "Frete (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Seguro (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "II (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            },
            use_container_width=True
        )

        # --- GERAÇÃO DO XML ---
        st.divider()
        if st.button("💾 Gerar XML Final (Layout 8686)", type="primary"):
            try:
                # Atualiza os itens originais do parser com os dados editados
                p = st.session_state["parsed_duimp"]
                records = edited_df.to_dict("records")
                
                # Merge cuidadoso
                for i, item in enumerate(p.items):
                    # Encontrar o record correspondente (assumindo ordem)
                    if i < len(records):
                        item.update(records[i])

                builder = XMLBuilder(p)
                xml_content = builder.build()
                
                numero_duimp = p.header.get("numeroDUIMP", "0000").replace("/", "-")
                filename = f"DUIMP_{numero_duimp}_INTEGRADO.xml"
                
                st.balloons()
                st.download_button("⬇️ Baixar XML", xml_content, filename, "text/xml")
                
            except Exception as e:
                st.error(f"Erro ao gerar XML: {e}")

    else:
        st.info("Aguardando carregamento do Extrato DUIMP...")

if __name__ == "__main__":
    main()
