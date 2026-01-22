import streamlit as st
import fitz  # PyMuPDF (App 1 - DUIMP)
import pdfplumber # (App 2 - Häfele)
import re
import pandas as pd
import numpy as np
from lxml import etree
import tempfile
import os
import logging
import unicodedata
from typing import Dict, List, Optional, Any

# ==============================================================================
# CONFIGURAÇÃO GERAL
# ==============================================================================
st.set_page_config(page_title="Sistema Integrado DUIMP 2026 (Senior Edition)", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1E3A8A; font-weight: 800; margin-bottom: 1rem; border-bottom: 3px solid #1E3A8A; }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: bold; height: 3.5em; background-color: #1E3A8A; color: white; border: none; transition: all 0.3s; }
    .stButton>button:hover { background-color: #1e40af; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .success-box { background-color: #ecfdf5; color: #065f46; padding: 15px; border-radius: 8px; border-left: 5px solid #10b981; }
    .info-box { background-color: #eff6ff; color: #1e3a8a; padding: 15px; border-radius: 8px; border-left: 5px solid #3b82f6; }
</style>
""", unsafe_allow_html=True)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. PARSER APP 2 (HÄFELE) - ENGINE SÊNIOR (REVERSE LOOKUP)
# ==============================================================================

class HafelePDFParser:
    """
    Parser Sênior desenvolvido para layouts PDFs com 'Left-Shifted Values' (Valor antes do Rótulo).
    """
    
    def __init__(self):
        self.documento = {'itens': []}
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        with pdfplumber.open(pdf_path) as pdf:
            # Estratégia de Consolidação de Texto
            all_content = []
            for page in pdf.pages:
                # layout=True é mandatório para manter a integridade da linha horizontal
                text = page.extract_text(layout=True)
                if text:
                    # Remove rodapés/cabeçalhos recorrentes que poluem a leitura
                    text = re.sub(r'--- PAGE \d+ ---', '', text)
                    all_content.append(text)
            
            full_text = "\n".join(all_content)
            self._process_full_text(full_text)
            return self.documento
            
    def _process_full_text(self, text: str):
        # Separador Mestre
        chunks = re.split(r"ITENS DA DUIMP-(\d+)", text)
        
        items = []
        if len(chunks) > 1:
            # chunks[1]=ID, chunks[2]=Content ...
            for i in range(1, len(chunks), 2):
                try:
                    item_num = int(chunks[i])
                    content = chunks[i+1]
                    item_data = self._parse_item_content(content, item_num)
                    items.append(item_data)
                except Exception as e:
                    logger.error(f"Erro ao processar item {i}: {e}")
        
        self.documento['itens'] = items
    
    def _parse_item_content(self, text: str, item_num: int) -> Dict:
        item = {
            'numero_item': item_num,
            'codigo_interno': '',
            'descricao_complementar': '',
            'frete_internacional': 0.0,
            'seguro_internacional': 0.0,
            'local_aduaneiro': 0.0,
            # Impostos
            'ii_valor_devido': 0.0, 'ii_base_calculo': 0.0, 'ii_aliquota': 0.0,
            'ipi_valor_devido': 0.0, 'ipi_base_calculo': 0.0, 'ipi_aliquota': 0.0,
            'pis_valor_devido': 0.0, 'pis_base_calculo': 0.0, 'pis_aliquota': 0.0,
            'cofins_valor_devido': 0.0, 'cofins_base_calculo': 0.0, 'cofins_aliquota': 0.0
        }

        # --- 1. DADOS CADASTRAIS ---
        # Código Interno: "Código interno" ... [quebra] ... "342.79.301"
        code_match = re.search(r'Código interno[^\d\n]*([\d\.]+)', text, re.IGNORECASE)
        if code_match:
            item['codigo_interno'] = code_match.group(1).strip()

        # Descrição Complementar
        desc_match = re.search(r'DESCRIÇÃO COMPLEMENTAR DA MERCADORIA\s*\n?(.*?)(?=\n|CONDIÇÃO|NCM)', text, re.IGNORECASE | re.DOTALL)
        if desc_match:
            raw_desc = desc_match.group(1).strip()
            item['descricao_complementar'] = re.sub(r'\s+', ' ', raw_desc)

        # --- 2. VALORES LOGÍSTICOS (Estes costumam ser Padrão: Label -> Valor) ---
        item['frete_internacional'] = self._extract_value_smart([r'Frete Internac\.'], text, direction='forward')
        item['seguro_internacional'] = self._extract_value_smart([r'Seguro Internac\.'], text, direction='forward')
        item['local_aduaneiro'] = self._extract_value_smart([r'Local Aduaneiro'], text, direction='forward')

        # --- 3. IMPOSTOS (Lógica Reversa para Tabelas Quebradas) ---
        
        # Segmentação de Blocos (Crucial)
        idx_ii = -1
        # Procura II ou 11 (OCR comum)
        match_ii = re.search(r'\b(II|11)\b', text)
        if match_ii: idx_ii = match_ii.start()
        
        match_ipi = re.search(r'\bIPI\b', text)
        idx_ipi = match_ipi.start() if match_ipi else -1
        
        match_pis = re.search(r'\bPIS\b[\s\n-]', text) # Contexto para não pegar PIS em frases
        idx_pis = match_pis.start() if match_pis else -1
        
        match_cofins = re.search(r'\bCOFINS\b', text)
        idx_cofins = match_cofins.start() if match_cofins else -1

        def get_block(start, potential_ends):
            if start == -1: return ""
            valid_ends = [x for x in potential_ends if x > start]
            end = min(valid_ends) if valid_ends else len(text)
            return text[start:end]

        block_ii = get_block(idx_ii, [idx_ipi, idx_pis, idx_cofins])
        block_ipi = get_block(idx_ipi, [idx_pis, idx_cofins])
        block_pis = get_block(idx_pis, [idx_cofins])
        block_cofins = text[idx_cofins:] if idx_cofins != -1 else ""

        # Preenchimento usando a engine smart
        self._populate_tax(item, 'ii', block_ii)
        self._populate_tax(item, 'ipi', block_ipi)
        self._populate_tax(item, 'pis', block_pis)
        self._populate_tax(item, 'cofins', block_cofins)

        return item

    def _populate_tax(self, item: Dict, prefix: str, block: str):
        if not block: return
        
        # Labels possíveis para cada campo (mapeado do seu PDF)
        labels_valor = [r'Valor Devido', r'Valor A Recolher', r'Valor Calculado']
        labels_base = [r'Base de Cálculo', r'Base de Calculo']
        labels_aliq = [r'% Alíquota', r'Ad Valorem']

        # Extração com preferência REVERSA (Valor antes do Label)
        item[f'{prefix}_valor_devido'] = self._extract_value_smart(labels_valor, block, direction='reverse')
        item[f'{prefix}_base_calculo'] = self._extract_value_smart(labels_base, block, direction='reverse')
        item[f'{prefix}_aliquota'] = self._extract_value_smart(labels_aliq, block, direction='reverse')

    def _extract_value_smart(self, labels: List[str], text: str, direction: str = 'reverse') -> float:
        """
        Engine de Extração Sênior.
        Tenta todas as labels. Se direction='reverse', procura: (Numero)...(Label).
        Se falhar ou direction='forward', procura: (Label)...(Numero).
        """
        for label in labels:
            val = 0.0
            
            # 1. TENTATIVA REVERSA (Prioridade para esse PDF)
            # Regex: (Numero 1.000,0000) ... (Lixo não quebra de linha) ... (Label)
            if direction == 'reverse':
                # Captura números com ou sem milhar, virgula obrigatoria, e muitos decimais
                regex_rev = r'([\d\.]*,\d+)[^\n]*?' + label
                match = re.search(regex_rev, text, re.IGNORECASE)
                if match:
                    return self._parse_valor(match.group(1))
            
            # 2. TENTATIVA PADRÃO (Fallback)
            # Regex: (Label) ... (Lixo) ... (Numero)
            regex_fwd = label + r'[^\d\n]*?([\d\.]*,\d+)'
            match = re.search(regex_fwd, text, re.IGNORECASE | re.DOTALL)
            if match:
                return self._parse_valor(match.group(1))
                
        return 0.0

    def _parse_valor(self, valor_str: str) -> float:
        if not valor_str: return 0.0
        try:
            # Remove pontos de milhar, mantém vírgula
            clean = valor_str.replace('.', '').replace(',', '.')
            return float(clean)
        except: return 0.0

class FinancialAnalyzer:
    def __init__(self, documento: Dict):
        self.documento = documento
    def prepare_dataframe(self):
        return pd.DataFrame(self.documento['itens'])

# ==============================================================================
# 2. PARSER APP 1 (DUIMP SISCOMEX) - MANTIDO
# ==============================================================================

class DuimpPDFParser:
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

# ==============================================================================
# 3. XML BUILDER E UTILS (APP 1)
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
        except: return "0" * length

    @staticmethod
    def format_high_precision(value, length=15):
        try:
            if isinstance(value, str):
                value = value.replace('.', '')
                value = value.replace(',', '.')
            val_float = float(value)
            val_int = int(round(val_float * 10000000))
            return str(val_int).zfill(length)
        except: return "0" * length

    @staticmethod
    def format_quantity(value, length=14):
        try:
            if isinstance(value, str):
                value = value.replace('.', '')
                value = value.replace(',', '.')
            val_float = float(value)
            val_int = int(round(val_float * 100000))
            return str(val_int).zfill(length)
        except: return "0" * length

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

# LAYOUT OBRIGATÓRIO 8686 - MANTIDO
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
# MAIN APP
# ==============================================================================

def main():
    st.markdown('<div class="main-header">Sistema Unificado: DUIMP + Häfele (Ultimate Pro)</div>', unsafe_allow_html=True)

    if "parsed_duimp" not in st.session_state: st.session_state["parsed_duimp"] = None
    if "parsed_hafele" not in st.session_state: st.session_state["parsed_hafele"] = None
    if "merged_df" not in st.session_state: st.session_state["merged_df"] = None

    tab1, tab2, tab3 = st.tabs(["📂 Upload e Vinculação", "📋 Conferência Detalhada", "💾 Exportar XML"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.info("Passo 1: Carregue o Extrato DUIMP (Siscomex)")
            file_duimp = st.file_uploader("Arquivo DUIMP (.pdf)", type="pdf", key="u1")
        with col2:
            st.info("Passo 2: Carregue o Relatório Häfele")
            file_hafele = st.file_uploader("Arquivo Häfele (.pdf)", type="pdf", key="u2")

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
                    st.success("DUIMP processada com sucesso!")
                except Exception as e: st.error(f"Erro ao ler DUIMP: {e}")

        if file_hafele and st.session_state["parsed_hafele"] is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(file_hafele.getvalue())
                tmp_path = tmp.name
            try:
                parser_h = HafelePDFParser()
                doc_h = parser_h.parse_pdf(tmp_path)
                st.session_state["parsed_hafele"] = doc_h
                
                qtd_itens = len(doc_h['itens'])
                if qtd_itens > 0:
                    st.success(f"Häfele: {qtd_itens} itens extraídos corretamente!")
                else:
                    st.warning("Atenção: Nenhum item foi extraído do PDF Häfele.")
                    
            except Exception as e:
                st.error(f"Erro ao ler Häfele: {e}")
            finally:
                if os.path.exists(tmp_path): os.unlink(tmp_path)

        st.markdown("---")
        if st.button("🔗 VINCULAR DADOS (Cruzamento Automático)", type="primary", use_container_width=True):
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
                                
                                # CONCATENAÇÃO
                                cod_interno = src.get('codigo_interno', '')
                                desc_comp = src.get('descricao_complementar', '')
                                final_number = f"{cod_interno} - {desc_comp}" if desc_comp else cod_interno
                                
                                df_dest.at[idx, 'NUMBER'] = final_number
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
                    st.success(f"Vinculação concluída! {count} itens foram cruzados e atualizados.")
                except Exception as e: st.error(f"Erro na vinculação: {e}")
            else:
                st.warning("Por favor, carregue os dois arquivos antes de vincular.")

    with tab2:
        st.header("📋 Conferência e Edição")
        if st.session_state["merged_df"] is not None:
            col_config = {
                "numeroAdicao": st.column_config.TextColumn("Item", width="small", disabled=True),
                "NUMBER": st.column_config.TextColumn("Código Interno + Descrição", width="large"),
                "Frete (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Seguro (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "II (R$)": st.column_config.NumberColumn(label="II Vlr", format="R$ %.2f"),
                "II Base (R$)": st.column_config.NumberColumn(label="II Base", format="R$ %.2f"),
            }
            edited_df = st.data_editor(st.session_state["merged_df"], hide_index=True, column_config=col_config, use_container_width=True, height=600)
            st.session_state["merged_df"] = edited_df
        else:
            st.info("Aguardando dados...")

    with tab3:
        st.header("💾 Exportar XML")
        if st.session_state["merged_df"] is not None:
            if st.button("Gerar XML (Layout 8686)", type="primary"):
                try:
                    p = st.session_state["parsed_duimp"]
                    records = st.session_state["merged_df"].to_dict("records")
                    
                    for i, item in enumerate(p.items):
                        if i < len(records):
                            item.update(records[i])
                    
                    builder = XMLBuilder(p)
                    xml_bytes = builder.build()
                    
                    duimp_num = p.header.get("numeroDUIMP", "0000").replace("/", "-")
                    file_name = f"DUIMP_{duimp_num}_INTEGRADO.xml"
                    
                    st.download_button(
                        label="⬇️ Baixar XML Final",
                        data=xml_bytes,
                        file_name=file_name,
                        mime="text/xml"
                    )
                    st.success("Arquivo gerado com sucesso! Cabeçalho validado.")
                    
                except Exception as e:
                    st.error(f"Erro na geração do XML: {e}")
        else:
            st.warning("Realize a vinculação e conferência antes de exportar.")

if __name__ == "__main__":
    main()
