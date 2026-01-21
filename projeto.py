import streamlit as st
import fitz  # PyMuPDF
import pdfplumber
import re
from lxml import etree
import pandas as pd
import numpy as np
import tempfile
import os
import logging
from typing import Dict, List, Optional, Any

# ==============================================================================
# CONFIGURAÇÃO GERAL E ESTILOS
# ==============================================================================
st.set_page_config(page_title="Sistema Integrado DUIMP 2026 (Final)", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2rem; color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; margin-bottom: 1rem; }
    .success-box { background-color: #d1fae5; color: #065f46; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; }
    .warning-box { background-color: #fef3c7; color: #92400e; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; }
    .stButton>button { width: 100%; border-radius: 0.375rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. CONSTANTES DO APP 1 (LAYOUT XML 8686)
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

# ==============================================================================
# 2. PARSERS E ANÁLISE
# ==============================================================================

class DuimpPDFParser:
    """Parser do App 1 (DUIMP SISCOMEX) - Inalterado"""
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

class HafelePDFParser:
    """Parser Híbrido: Combina a estrutura do código original do usuário com a inteligência para ler o PDF específico."""
    
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
        # TENTA O PADRÃO ORIGINAL DO USUÁRIO
        items_orig = self._find_all_items_original(text)
        
        # TENTA O PADRÃO NOVO (ITENS DA DUIMP) SE O ORIGINAL FALHAR
        items_new = self._find_all_items_robust(text)
        
        # Usa o que retornou dados
        if len(items_new) > len(items_orig):
            self.documento['itens'] = items_new
        else:
            self.documento['itens'] = items_orig
            
        self._calculate_totals()
    
    def _find_all_items_original(self, text: str) -> List[Dict]:
        """Lógica original do App 2 (Regex do usuário)"""
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

    def _find_all_items_robust(self, text: str) -> List[Dict]:
        """Lógica robusta para o PDF 'APP2.pdf' que usa 'ITENS DA DUIMP'"""
        items = []
        chunks = re.split(r"ITENS DA DUIMP-(\d+)", text)
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                item_num_str = chunks[i]
                content = chunks[i+1]
                try: item_num = int(item_num_str)
                except: item_num = 0
                item_data = self._parse_item(content, str(item_num), "", "") # NCM e Codigo vazios pois serao extraidos dentro
                if item_data: items.append(item_data)
        return items
    
    def _parse_item(self, text: str, item_num: str, ncm: str, codigo: str) -> Optional[Dict]:
        """Parse unificado com Regex que tolera quebras de linha (para o PDF problemático)"""
        try:
            item = {
                'numero_item': int(item_num),
                'ncm': ncm,
                'codigo_produto': codigo,
                'codigo_interno': '',
                'frete_internacional': 0.0,
                'seguro_internacional': 0.0,
                'local_aduaneiro': 0.0,
                'ii_valor_devido': 0.0, 'ii_base_calculo': 0.0, 'ii_aliquota': 0.0,
                'ipi_valor_devido': 0.0, 'ipi_base_calculo': 0.0, 'ipi_aliquota': 0.0,
                'pis_valor_devido': 0.0, 'pis_base_calculo': 0.0, 'pis_aliquota': 0.0,
                'cofins_valor_devido': 0.0, 'cofins_base_calculo': 0.0, 'cofins_aliquota': 0.0,
                'valor_total': 0.0, 'peso_liquido': 0.0, 'quantidade': 0.0, 'total_impostos': 0.0
            }

            # 1. Extração Específica para o Layout "ITENS DA DUIMP"
            code_match = re.search(r'Código interno\s*[\n\r]*([0-9\.]+)', text)
            if code_match: item['codigo_interno'] = code_match.group(1).strip()

            def get_val(pattern, txt):
                m = re.search(pattern, txt, re.IGNORECASE | re.DOTALL)
                return self._parse_valor(m.group(1)) if m else 0.0

            item['frete_internacional'] = get_val(r'Frete Internac\.\s*\(R\$\)\s*([\d\.,]+)', text)
            item['seguro_internacional'] = get_val(r'Seguro Internac\.\s*\(R\$\)\s*([\d\.,]+)', text)
            item['local_aduaneiro'] = get_val(r'Local Aduaneiro\s*\(R\$\)\s*([\d\.,]+)', text)

            # Separação por Blocos de Impostos (Crucial para não misturar valores)
            idx_ii = text.find("II")
            idx_ipi = text.find("IPI")
            match_pis = re.search(r'PIS[\s\n]', text)
            idx_pis = match_pis.start() if match_pis else -1
            idx_cofins = text.find("COFINS")

            def get_block(start, ends):
                if start == -1: return ""
                valid = [x for x in ends if x > start]
                end = min(valid) if valid else len(text)
                return text[start:end]

            txt_ii = get_block(idx_ii, [idx_ipi, idx_pis, idx_cofins])
            txt_ipi = get_block(idx_ipi, [idx_pis, idx_cofins])
            txt_pis = get_block(idx_pis, [idx_cofins])
            txt_cofins = text[idx_cofins:] if idx_cofins != -1 else ""

            def extract_tax(subtext, prefix):
                if not subtext: return
                val = get_val(r'Valor Devido \(R\$\)[^\d]*([\d\.,]+)', subtext)
                base = get_val(r'Base de Cálculo \(R\$\)[^\d]*([\d\.,]+)', subtext)
                aliq = get_val(r'% Alíquota[^\d]*([\d\.,]+)', subtext)
                item[f'{prefix}_valor_devido'] = val
                item[f'{prefix}_base_calculo'] = base
                item[f'{prefix}_aliquota'] = aliq

            extract_tax(txt_ii, 'ii')
            extract_tax(txt_ipi, 'ipi')
            extract_tax(txt_pis, 'pis')
            extract_tax(txt_cofins, 'cofins')

            return item
        except: return None

    def _calculate_totals(self):
        # Totais simples para exibição
        pass

    def _parse_valor(self, valor_str: str) -> float:
        if not valor_str: return 0.0
        try: return float(valor_str.replace('.', '').replace(',', '.'))
        except: return 0.0

class FinancialAnalyzer:
    """Analisador Financeiro do App 2 (Mantido)"""
    def __init__(self, documento: Dict):
        self.documento = documento
    
    def prepare_dataframe(self):
        return pd.DataFrame(self.documento['itens'])

# ==============================================================================
# 3. XML BUILDER (HEADER CORRIGIDO)
# ==============================================================================

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
        
        xml_content = etree.tostring(self.root, pretty_print=True, encoding="UTF-8", xml_declaration=False)
        header = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        return header + xml_content

# ==============================================================================
# MAIN APP
# ==============================================================================

def main():
    st.markdown('<div class="main-header">Sistema Integrado DUIMP 2026</div>', unsafe_allow_html=True)

    if "parsed_duimp" not in st.session_state: st.session_state["parsed_duimp"] = None
    if "parsed_hafele" not in st.session_state: st.session_state["parsed_hafele"] = None
    if "merged_df" not in st.session_state: st.session_state["merged_df"] = None

    tab1, tab2, tab3 = st.tabs(["📂 Upload", "📋 Conferência", "💾 Exportar"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            file_duimp = st.file_uploader("1. Extrato DUIMP (Siscomex)", type="pdf", key="u1")
        with col2:
            file_hafele = st.file_uploader("2. Relatório Häfele (Original)", type="pdf", key="u2")

        if file_duimp:
            if st.session_state["parsed_duimp"] is None or file_duimp.name != getattr(st.session_state.get("last_duimp"), "name", ""):
                try:
                    p = DuimpPDFParser(file_duimp.read())
                    p.preprocess()
                    p.extract_header()
                    p.extract_items()
                    st.session_state["parsed_duimp"] = p
                    st.session_state["last_duimp"] = file_duimp
                    
                    df = pd.DataFrame(p.items)
                    cols_fiscais = ["NUMBER", "Frete (R$)", "Seguro (R$)", "II (R$)", "II Base (R$)", "II Alíq. (%)", "IPI (R$)", "IPI Base (R$)", "IPI Alíq. (%)", "PIS (R$)", "PIS Base (R$)", "PIS Alíq. (%)", "COFINS (R$)", "COFINS Base (R$)", "COFINS Alíq. (%)", "Aduaneiro (R$)"]
                    for col in cols_fiscais: df[col] = 0.00 if col != "NUMBER" else ""
                    st.session_state["merged_df"] = df
                    st.success("DUIMP Lida com Sucesso!")
                except Exception as e: st.error(f"Erro DUIMP: {e}")

        if file_hafele and st.session_state["parsed_hafele"] is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(file_hafele.getvalue())
                tmp_path = tmp.name
            try:
                parser_h = HafelePDFParser()
                doc_h = parser_h.parse_pdf(tmp_path)
                st.session_state["parsed_hafele"] = doc_h
                st.success(f"Häfele: {len(doc_h['itens'])} itens encontrados.")
            except Exception as e: st.error(f"Erro Häfele: {e}")
            finally: 
                if os.path.exists(tmp_path): os.unlink(tmp_path)

        if st.button("🔗 VINCULAR AGORA"):
            if st.session_state["merged_df"] is not None and st.session_state["parsed_hafele"] is not None:
                try:
                    df_dest = st.session_state["merged_df"].copy()
                    src_map = {int(it['numero_item']): it for it in st.session_state["parsed_hafele"]['itens']}
                    count = 0
                    for idx, row in df_dest.iterrows():
                        try:
                            item_num = int(row['numeroAdicao'])
                            if item_num in src_map:
                                src = src_map[item_num]
                                df_dest.at[idx, 'NUMBER'] = src.get('codigo_interno', '')
                                df_dest.at[idx, 'Frete (R$)'] = src.get('frete_internacional', 0.0)
                                df_dest.at[idx, 'Seguro (R$)'] = src.get('seguro_internacional', 0.0)
                                df_dest.at[idx, 'Aduaneiro (R$)'] = src.get('local_aduaneiro', 0.0)
                                df_dest.at[idx, 'II (R$)'] = src.get('ii_valor_devido', 0.0)
                                df_dest.at[idx, 'II Base (R$)'] = src.get('ii_base_calculo', 0.0)
                                df_dest.at[idx, 'II Alíq. (%)'] = src.get('ii_aliquota', 0.0)
                                df_dest.at[idx, 'IPI (R$)'] = src.get('ipi_valor_devido', 0.0)
                                df_dest.at[idx, 'IPI Base (R$)'] = src.get('ipi_base_calculo', 0.0)
                                df_dest.at[idx, 'IPI Alíq. (%)'] = src.get('ipi_aliquota', 0.0)
                                df_dest.at[idx, 'PIS (R$)'] = src.get('pis_valor_devido', 0.0)
                                df_dest.at[idx, 'PIS Base (R$)'] = src.get('pis_base_calculo', 0.0)
                                df_dest.at[idx, 'PIS Alíq. (%)'] = src.get('pis_aliquota', 0.0)
                                df_dest.at[idx, 'COFINS (R$)'] = src.get('cofins_valor_devido', 0.0)
                                df_dest.at[idx, 'COFINS Base (R$)'] = src.get('cofins_base_calculo', 0.0)
                                df_dest.at[idx, 'COFINS Alíq. (%)'] = src.get('cofins_aliquota', 0.0)
                                count += 1
                        except: continue
                    st.session_state["merged_df"] = df_dest
                    st.success(f"Vinculado: {count} itens.")
                except Exception as e: st.error(f"Erro vinculo: {e}")

    with tab2:
        if st.session_state["merged_df"] is not None:
            edited_df = st.data_editor(st.session_state["merged_df"], hide_index=True, use_container_width=True)
            st.session_state["merged_df"] = edited_df

    with tab3:
        if st.session_state["merged_df"] is not None:
            if st.button("Gerar XML"):
                try:
                    p = st.session_state["parsed_duimp"]
                    records = st.session_state["merged_df"].to_dict("records")
                    for i, item in enumerate(p.items):
                        if i < len(records): item.update(records[i])
                    builder = XMLBuilder(p)
                    xml_bytes = builder.build()
                    st.download_button("Baixar XML", xml_bytes, "DUIMP_FINAL.xml", "text/xml")
                except Exception as e: st.error(f"Erro XML: {e}")

if __name__ == "__main__":
    main()
