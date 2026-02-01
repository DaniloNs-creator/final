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
from typing import Dict, List, Optional, Any

# ==============================================================================
# CONFIGURAÇÃO GERAL
# ==============================================================================
st.set_page_config(page_title="Sistema Unificado 2026 (Pro)", layout="wide")

# Estilos CSS
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1E3A8A; font-weight: bold; margin-bottom: 1rem; }
    .sub-header { font-size: 1.5rem; color: #2563EB; margin-top: 1.5rem; border-bottom: 2px solid #E5E7EB; }
    .section-card { background: #FFFFFF; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1rem; border: 1px solid #E5E7EB; }
    .success-box { background-color: #d1fae5; color: #065f46; padding: 10px; border-radius: 5px; margin: 10px 0; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# PARTE 1: PARSER APP 2 (HÄFELE/EXTRATO DUIMP)
# ==============================================================================

class HafelePDFParser:
    def __init__(self):
        self.documento = {'cabecalho': {}, 'itens': [], 'totais': {}}
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text(layout=False) 
                    if text: full_text += text + "\n"
            self._process_full_text(full_text)
            return self.documento
        except Exception as e:
            st.error(f"Erro ao ler o arquivo PDF: {str(e)}")
            return self.documento

    def _process_full_text(self, text: str):
        chunks = re.split(r'(ITENS\s+DA\s+DUIMP\s*-\s*\d+)', text, flags=re.IGNORECASE)
        items_found = []
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                header = chunks[i]
                content = chunks[i+1]
                item_num_match = re.search(r'(\d+)', header)
                item_num = int(item_num_match.group(1)) if item_num_match else i
                item_data = self._parse_item_block(item_num, content)
                if item_data: items_found.append(item_data)
        self.documento['itens'] = items_found

    def _parse_item_block(self, item_num: int, text: str) -> Dict:
        try:
            item = {
                'numero_item': item_num, 'ncm': '', 'codigo_interno': '', 'quantidade': 0.0,
                'quantidade_comercial': 0.0, 'peso_liquido': 0.0, 'valor_total': 0.0,
                'ii_valor_devido': 0.0, 'ii_base_calculo': 0.0, 'ii_aliquota': 0.0,
                'ipi_valor_devido': 0.0, 'ipi_base_calculo': 0.0, 'ipi_aliquota': 0.0,
                'pis_valor_devido': 0.0, 'pis_base_calculo': 0.0, 'pis_aliquota': 0.0,
                'cofins_valor_devido': 0.0, 'cofins_base_calculo': 0.0, 'cofins_aliquota': 0.0,
                'frete_internacional': 0.0, 'seguro_internacional': 0.0, 'local_aduaneiro': 0.0
            }
            code_match = re.search(r'Código interno\s*([\d\.]+)', text, re.IGNORECASE)
            if code_match: item['codigo_interno'] = code_match.group(1).replace('.', '')
            ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', text)
            if ncm_match: item['ncm'] = ncm_match.group(1).replace('.', '')
            
            qtd_com_match = re.search(r'Qtde Unid\. Comercial\s*([\d\.,]+)', text)
            if qtd_com_match: item['quantidade_comercial'] = self._parse_valor(qtd_com_match.group(1))
            
            val_match = re.search(r'Valor Tot\. Cond Venda\s*([\d\.,]+)', text)
            if val_match: item['valor_total'] = self._parse_valor(val_match.group(1))

            tax_patterns = re.findall(r'Base de Cálculo.*?\(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor.*?(?:Devido|A Recolher|Calculado).*?\(R\$\)\s*([\d\.,]+)', text, re.DOTALL | re.IGNORECASE)
            for base_str, aliq_str, val_str in tax_patterns:
                base, aliq, val = self._parse_valor(base_str), self._parse_valor(aliq_str), self._parse_valor(val_str)
                if 1.60 <= aliq <= 3.00: item['pis_aliquota'], item['pis_base_calculo'], item['pis_valor_devido'] = aliq, base, val
                elif 7.00 <= aliq <= 12.00: item['cofins_aliquota'], item['cofins_base_calculo'], item['cofins_valor_devido'] = aliq, base, val
                elif aliq > 12.00: item['ii_aliquota'], item['ii_base_calculo'], item['ii_valor_devido'] = aliq, base, val
                elif aliq >= 0 and item['ipi_aliquota'] == 0: item['ipi_aliquota'], item['ipi_base_calculo'], item['ipi_valor_devido'] = aliq, base, val
            return item
        except: return None

    def _parse_valor(self, valor_str: str) -> float:
        try:
            return float(valor_str.replace('.', '').replace(',', '.'))
        except: return 0.0

# ==============================================================================
# PARTE 2: PARSER APP 1 (DUIMP)
# ==============================================================================

def montar_descricao_final(desc_complementar, codigo_extra, detalhamento):
    return f"{str(desc_complementar).strip()} - {str(codigo_extra).strip()} - {str(detalhamento).strip()}"

class DuimpPDFParser:
    def __init__(self, file_stream):
        self.doc = fitz.open(stream=file_stream, filetype="pdf")
        self.full_text = ""
        self.header = {}
        self.items = []

    def preprocess(self):
        clean_lines = []
        for page in self.doc:
            lines = page.get_text("text").split('\n')
            for line in lines:
                l_strip = line.strip()
                if "Extrato da DUIMP" in l_strip or "Data, hora e responsável" in l_strip: continue
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
        for i in range(1, len(chunks), 2):
            content = chunks[i+1]
            item = {"numeroAdicao": chunks[i]}
            item["ncm"] = self._regex(r"NCM:\s*([\d\.]+)", content)
            item["paisOrigem"] = self._regex(r"País de origem:\s*\n?(.+)", content)
            item["quantidade"] = self._regex(r"Quantidade na unidade estatística:\s*([\d\.,]+)", content)
            item["quantidade_comercial"] = self._regex(r"Quantidade na unidade comercializada:\s*([\d\.,]+)", content)
            item["unidade"] = self._regex(r"Unidade estatística:\s*(.+)", content)
            item["pesoLiq"] = self._regex(r"Peso líquido \(kg\):\s*([\d\.,]+)", content)
            item["valorUnit"] = self._regex(r"Valor unitário na condição de venda:\s*([\d\.,]+)", content)
            item["valorTotal"] = self._regex(r"Valor total na condição de venda:\s*([\d\.,]+)", content)
            item["moeda"] = self._regex(r"Moeda negociada:\s*(.+)", content)
            desc_match = re.search(r"Detalhamento do Produto:\s*(.+?)(?=\n\s*(?:Número de Identificação|Versão|Código de Class|Descrição complementar))", content, re.DOTALL)
            item["descricao"] = desc_match.group(1).strip() if desc_match else ""
            compl_match = re.search(r"Descrição complementar da mercadoria:\s*(.+?)(?=\n|$)", content, re.DOTALL)
            item["desc_complementar"] = compl_match.group(1).strip() if compl_match else ""
            
            exp_match = re.search(r"Código do Exportador Estrangeiro:\s*(.+?)(?=\n\s*(?:Endereço|Dados))", content, re.DOTALL)
            item["fornecedor_raw"] = exp_match.group(1).strip() if exp_match else ""
            addr_match = re.search(r"Endereço:\s*(.+?)(?=\n\s*(?:Dados da Mercadoria|Aplicação))", content, re.DOTALL)
            item["endereco_raw"] = addr_match.group(1).strip() if addr_match else ""
            
            self.items.append(item)

    def _regex(self, pattern, text):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""

# ==============================================================================
# PARTE 3: XML BUILDER E CONSTANTES
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

class DataFormatter:
    @staticmethod
    def clean_text(text):
        if not text: return ""
        return re.sub(r'\s+', ' ', text.replace('\n', ' ').replace('\r', '')).strip()

    @staticmethod
    def format_number(value, length=15):
        clean = re.sub(r'\D', '', str(value))
        return clean.zfill(length)

    @staticmethod
    def format_input_fiscal(value, length=15, is_percent=False):
        try:
            if isinstance(value, str): value = value.replace('.', '').replace(',', '.')
            return str(int(round(float(value) * 100))).zfill(length)
        except: return "0" * length

    @staticmethod
    def format_high_precision(value, length=15):
        try:
            if isinstance(value, str): value = value.replace('.', '').replace(',', '.')
            return str(int(round(float(value) * 10000000))).zfill(length)
        except: return "0" * length

    @staticmethod
    def format_quantity(value, length=14):
        try:
            if isinstance(value, str): value = value.replace('.', '').replace(',', '.')
            return str(int(round(float(value) * 100000))).zfill(length)
        except: return "0" * length

class XMLBuilder:
    def __init__(self, parser, global_data, edited_items=None):
        self.p = parser
        self.g = global_data # Recebe os dados de input da tela
        self.items_to_use = edited_items if edited_items else self.p.items
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self):
        h = self.p.header
        duimp_fmt = h.get("numeroDUIMP", "").split("/")[0].replace("-", "").replace(".", "")
        
        for it in self.items_to_use:
            adicao = etree.SubElement(self.duimp, "adicao")
            final_desc = montar_descricao_final(it.get("desc_complementar", ""), it.get("NUMBER", ""), it.get("descricao", ""))
            
            extracted_map = {
                "numeroAdicao": str(it["numeroAdicao"])[-3:],
                "numeroDUIMP": duimp_fmt,
                "dadosMercadoriaCodigoNcm": DataFormatter.format_number(it.get("ncm"), 8),
                "dadosMercadoriaMedidaEstatisticaQuantidade": DataFormatter.format_quantity(it.get("quantidade")),
                "dadosMercadoriaPesoLiquido": DataFormatter.format_quantity(it.get("pesoLiq"), 15),
                "valorTotalCondicaoVenda": DataFormatter.format_high_precision(it.get("valorTotal", "0"), 11),
                "valorUnitario": DataFormatter.format_high_precision(it.get("valorUnit", "0"), 20),
                "descricaoMercadoria": final_desc,
                "quantidade": DataFormatter.format_quantity(it.get("quantidade_comercial") or it.get("quantidade")),
                "iiAliquotaValorDevido": DataFormatter.format_input_fiscal(it.get("II (R$)", 0)),
                # ... Outros mapeamentos fiscais seguem a mesma lógica ...
            }

            for field in ADICAO_FIELDS_ORDER:
                if field.get("type") == "complex":
                    parent = etree.SubElement(adicao, field["tag"])
                    for child in field["children"]:
                        etree.SubElement(parent, child["tag"]).text = extracted_map.get(child["tag"], child["default"])
                else:
                    etree.SubElement(adicao, field["tag"]).text = extracted_map.get(field["tag"], field["default"])

        # FOOTER E TAGS DE INPUT SOLICITADAS
        footer_map = {
            "numeroDUIMP": duimp_fmt,
            "cargaPesoBruto": DataFormatter.format_number(self.g['peso_bruto'], 15),
            "cargaPesoLiquido": DataFormatter.format_number(self.g['peso_liquido'], 15),
            "cargaDataChegada": self.g['data_chegada'].replace("-",""),
            "dataDesembaraco": self.g['data_desembaraco'].replace("-",""),
            "dataRegistro": self.g['data_registro'].replace("-",""),
            "conhecimentoCargaEmbarqueData": self.g['data_embarque'].replace("-",""),
            "localDescargaTotalDolares": DataFormatter.format_input_fiscal(self.g['descarga_usd']),
            "localDescargaTotalReais": DataFormatter.format_input_fiscal(self.g['descarga_brl']),
            "localEmbarqueTotalDolares": DataFormatter.format_input_fiscal(self.g['embarque_usd']),
            "localEmbarqueTotalReais": DataFormatter.format_input_fiscal(self.g['embarque_brl']),
        }

        # Tag Embalagem (Quantidade de Volume)
        emb = etree.SubElement(self.duimp, "embalagem")
        etree.SubElement(emb, "codigoTipoEmbalagem").text = "60"
        etree.SubElement(emb, "nomeEmbalagem").text = "PALLETS"
        etree.SubElement(emb, "quantidadeVolume").text = str(self.g['qtd_volume']).zfill(5)

        # Tag Pagamento (Siscomex 7811 e outros)
        pag = etree.SubElement(self.duimp, "pagamento")
        etree.SubElement(pag, "agenciaPagamento").text = str(self.g['agencia'])
        etree.SubElement(pag, "bancoPagamento").text = str(self.g['banco'])
        etree.SubElement(pag, "codigoReceita").text = str(self.g['receita'])
        etree.SubElement(pag, "valorReceita").text = DataFormatter.format_input_fiscal(self.g['valor_receita'])

        # Preencher demais tags do footer fixas ou mapeadas
        for tag, default in {
            "armazenamentoRecintoAduaneiroCodigo": "9801303",
            "cargaPesoBruto": "", "cargaPesoLiquido": "", "cargaDataChegada": "",
            "dataDesembaraco": "", "dataRegistro": "", "conhecimentoCargaEmbarqueData": "",
            "localDescargaTotalDolares": "", "localDescargaTotalReais": "",
            "localEmbarqueTotalDolares": "", "localEmbarqueTotalReais": ""
        }.items():
            val = footer_map.get(tag, default)
            if val != "": etree.SubElement(self.duimp, tag).text = val

        xml_content = etree.tostring(self.root, pretty_print=True, encoding="UTF-8")
        return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_content

# ==============================================================================
# MAIN APP
# ==============================================================================

def main():
    st.markdown('<div class="main-header">Sistema Integrado DUIMP 2026</div>', unsafe_allow_html=True)

    if "merged_df" not in st.session_state: st.session_state["merged_df"] = None
    if "parsed_duimp" not in st.session_state: st.session_state["parsed_duimp"] = None

    tab1, tab2, tab3 = st.tabs(["📂 Upload", "📋 Conferência", "💾 Exportar XML"])

    with tab1:
        file_duimp = st.file_uploader("Arquivo DUIMP (.pdf)", type="pdf")
        if file_duimp and st.session_state["parsed_duimp"] is None:
            p = DuimpPDFParser(file_duimp.read())
            p.preprocess(); p.extract_header(); p.extract_items()
            st.session_state["parsed_duimp"] = p
            st.session_state["merged_df"] = pd.DataFrame(p.items)

    with tab2:
        if st.session_state["merged_df"] is not None:
            st.session_state["merged_df"] = st.data_editor(st.session_state["merged_df"], use_container_width=True)

    with tab3:
        st.subheader("Configurações Globais do XML (Preenchimento de Tags)")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("**QUANTIDADE**")
            qtd_vol = st.number_input("Quantidade Volume", value=1)
        with c2:
            st.markdown("**DATAS**")
            dt_chegada = st.text_input("Data Chegada", "2025-11-20")
            dt_desemb = st.text_input("Data Desembaraço", "2025-11-24")
        with c3:
            st.markdown("**PESO**")
            p_bruto = st.text_input("Peso Bruto", "000002114187000")
            p_liquido = st.text_input("Peso Líquido", "000002114187000")
        with c4:
            st.markdown("**SISCOMEX 7811**")
            agencia = st.text_input("Agência", "3715")
            banco = st.text_input("Banco", "341")

        c5, c6 = st.columns(2)
        with c5:
            receita_cod = st.text_input("Código Receita", "7811")
            receita_val = st.number_input("Valor Receita", value=0.0)
            dt_reg = st.text_input("Data Registro", "2025-11-24")
            dt_emb = st.text_input("Data Embarque", "2025-10-25")
        with c6:
            desc_usd = st.number_input("Descarga Total USD", value=0.0)
            desc_brl = st.number_input("Descarga Total BRL", value=0.0)
            emb_usd = st.number_input("Embarque Total USD", value=0.0)
            emb_brl = st.number_input("Embarque Total BRL", value=0.0)

        if st.button("Gerar XML Final", type="primary"):
            global_data = {
                'qtd_volume': qtd_vol, 'data_chegada': dt_chegada, 'data_desembaraco': dt_desemb,
                'data_registro': dt_reg, 'data_embarque': dt_emb, 'peso_bruto': p_bruto,
                'peso_liquido': p_liquido, 'agencia': agencia, 'banco': banco,
                'receita': receita_cod, 'valor_receita': receita_val,
                'descarga_usd': desc_usd, 'descarga_brl': desc_brl,
                'embarque_usd': emb_usd, 'embarque_brl': emb_brl
            }
            builder = XMLBuilder(st.session_state["parsed_duimp"], global_data, st.session_state["merged_df"].to_dict('records'))
            xml_bytes = builder.build()
            st.download_button("⬇️ Baixar XML Integrado", data=xml_bytes, file_name="DUIMP_FINAL.xml", mime="text/xml")

if __name__ == "__main__":
    main()
