import streamlit as st
import fitz  # PyMuPDF (App 1)
import pdfplumber # (App 2)
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
st.set_page_config(page_title="Sistema Integrado DUIMP 2026 (Enterprise)", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; color: #003366; font-weight: bold; margin-bottom: 1rem; border-bottom: 2px solid #003366; }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: bold; height: 3.5em; background-color: #003366; color: white; border: 1px solid #002244; }
    .stButton>button:hover { background-color: #002244; border-color: #003366; }
    .success-box { background-color: #d1fae5; color: #065f46; padding: 15px; border-radius: 8px; border-left: 5px solid #10b981; margin-bottom: 10px; }
    .info-box { background-color: #eff6ff; color: #1e40af; padding: 15px; border-radius: 8px; border-left: 5px solid #3b82f6; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. PARSER APP 2 (HÄFELE) - ENGINE SÊNIOR (REVERSE SCANNING)
# ==============================================================================

class HafelePDFParser:
    """
    Parser Sênior desenvolvido especificamente para o layout Häfele onde:
    1. Os valores numéricos aparecem ANTES dos rótulos (Left-Shifted).
    2. As tabelas são quebradas por item.
    3. Impostos (II, IPI...) estão em blocos de texto distintos.
    """
    
    def __init__(self):
        self.documento = {'itens': []}
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Estratégia de Consolidação: Juntar tudo para tratar itens que quebram página
                full_text_list = []
                for page in pdf.pages:
                    # layout=True é mandatório para preservar a "sujeira" visual que contém os dados
                    text = page.extract_text(layout=True)
                    if text:
                        # Removemos cabeçalhos de página repetitivos que poluem a regex
                        text = re.sub(r'--- PAGE \d+ ---', '', text)
                        full_text_list.append(text)
                
                raw_text = "\n".join(full_text_list)
                self._process_full_text(raw_text)
                
            return self.documento
        except Exception as e:
            logger.error(f"Erro fatal no parser: {e}")
            return {'itens': []}

    def _process_full_text(self, text: str):
        # Separador Mestre: "ITENS DA DUIMP-XXXXX" ou "Item Integracao"
        # O split gera: [Lixo, Num1, Conteudo1, Num2, Conteudo2...]
        chunks = re.split(r"(?:ITENS DA DUIMP-|Item\s*\n\s*Integracao)\s*0*(\d+)", text)
        
        items = []
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                try:
                    item_num_str = chunks[i]
                    content_block = chunks[i+1]
                    
                    # Normalização do número do item
                    item_num = int(item_num_str) if item_num_str.isdigit() else 0
                    
                    # Processamento isolado do bloco
                    item_data = self._parse_single_item(content_block, item_num)
                    if item_data['codigo_interno']: # Filtra itens vazios/falsos positivos
                        items.append(item_data)
                except Exception as e:
                    logger.warning(f"Falha ao processar bloco {i}: {e}")

        self.documento['itens'] = items

    def _parse_single_item(self, block: str, item_num: int) -> Dict:
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

        # --- 1. DADOS DE IDENTIFICAÇÃO ---
        
        # Código Interno: Busca "Código interno" ... quebra ... numero
        code_match = re.search(r'Código interno[^\d\n]*([\d\.]+)', block, re.IGNORECASE)
        if code_match:
            item['codigo_interno'] = code_match.group(1).strip()

        # Descrição Complementar: Captura entre o título e a próxima seção (NCM ou Condição)
        desc_match = re.search(r'DESCRIÇÃO COMPLEMENTAR DA MERCADORIA\s*\n?(.*?)(?=\n\s*(?:CONDIÇÃO|NCM|M[ée]todo))', block, re.IGNORECASE | re.DOTALL)
        if desc_match:
            raw_desc = desc_match.group(1).strip()
            item['descricao_complementar'] = re.sub(r'\s+', ' ', raw_desc)

        # --- 2. VALORES LOGÍSTICOS ---
        # Estes geralmente seguem o padrão Label -> Valor, mas usaremos a engine smart
        item['frete_internacional'] = self._extract_value_smart([r'Frete Internac'], block)
        item['seguro_internacional'] = self._extract_value_smart([r'Seguro Internac'], block)
        item['local_aduaneiro'] = self._extract_value_smart([r'Local Aduaneiro'], block)

        # --- 3. ENGINE DE IMPOSTOS (SEGMENTAÇÃO DE BLOCOS) ---
        # Isolamos o texto de cada imposto para evitar contaminação cruzada
        
        # Índices de início
        idx_ii = -1
        match_ii = re.search(r'\b(II|11)\b[\s\n]', block) # II ou 11 (OCR)
        if match_ii: idx_ii = match_ii.start()
        
        idx_ipi = -1
        match_ipi = re.search(r'\bIPI\b[\s\n]', block)
        if match_ipi: idx_ipi = match_ipi.start()
        
        idx_pis = -1
        match_pis = re.search(r'\bPIS\b[\s\n-]', block) # PIS isolado
        if match_pis: idx_pis = match_pis.start()
        
        idx_cofins = -1
        match_cofins = re.search(r'\bCOFINS\b[\s\n]', block)
        if match_cofins: idx_cofins = match_cofins.start()

        # Função de recorte
        def get_slice(start, breakpoints):
            if start == -1: return ""
            # Pega o próximo breakpoint válido que seja maior que o start
            valid = [b for b in breakpoints if b > start]
            end = min(valid) if valid else len(block)
            return block[start:end]

        sub_ii = get_slice(idx_ii, [idx_ipi, idx_pis, idx_cofins])
        sub_ipi = get_slice(idx_ipi, [idx_pis, idx_cofins])
        sub_pis = get_slice(idx_pis, [idx_cofins])
        sub_cofins = block[idx_cofins:] if idx_cofins != -1 else ""

        # Preenchimento dos dados
        self._populate_tax(item, 'ii', sub_ii)
        self._populate_tax(item, 'ipi', sub_ipi)
        self._populate_tax(item, 'pis', sub_pis)
        self._populate_tax(item, 'cofins', sub_cofins)

        return item

    def _populate_tax(self, item: Dict, prefix: str, text_block: str):
        if not text_block: return
        
        # Labels mapeadas do seu PDF
        labels_valor = [r'Valor Devido', r'Valor A Recolher', r'Valor Calculado']
        labels_base = [r'Base de Cálculo', r'Base de Calculo', r'Base de C[áa]lculo']
        labels_aliq = [r'% Alíquota', r'Ad Valorem', r'% Al[íi]quota']

        # A engine smart decide se o valor está antes ou depois
        # Para o seu PDF, a prioridade é REVERSA (Valor antes do Label)
        item[f'{prefix}_valor_devido'] = self._extract_value_smart(labels_valor, text_block, prioritize_reverse=True)
        item[f'{prefix}_base_calculo'] = self._extract_value_smart(labels_base, text_block, prioritize_reverse=True)
        item[f'{prefix}_aliquota'] = self._extract_value_smart(labels_aliq, text_block, prioritize_reverse=True)

    def _extract_value_smart(self, labels: List[str], text: str, prioritize_reverse: bool = False) -> float:
        """
        Engine de Extração Bidirecional.
        Tenta encontrar o valor associado ao rótulo, seja antes (Reverse) ou depois (Forward).
        """
        for label in labels:
            val = 0.0
            
            # Regex Reversa: (Numero) ... (Lixo na mesma linha ou proxima) ... (Label)
            # Ex: 531,0000 ... Valor Devido
            # ([\d\.]*,\d+) -> Captura 1.000,0000
            regex_rev = r'([\d\.]*,\d+)[^\n\d]*?' + label
            match_rev = re.search(regex_rev, text, re.IGNORECASE)
            
            # Regex Padrão: (Label) ... (Lixo) ... (Numero)
            regex_fwd = label + r'[^\d\n]*?([\d\.]*,\d+)'
            match_fwd = re.search(regex_fwd, text, re.IGNORECASE | re.DOTALL)

            val_rev = self._parse_br_float(match_rev.group(1)) if match_rev else 0.0
            val_fwd = self._parse_br_float(match_fwd.group(1)) if match_fwd else 0.0

            # Lógica de decisão
            if prioritize_reverse:
                if val_rev > 0: return val_rev
                if val_fwd > 0: return val_fwd
            else:
                if val_fwd > 0: return val_fwd
                if val_rev > 0: return val_rev
                
        return 0.0

    def _parse_br_float(self, val_str: str) -> float:
        if not val_str: return 0.0
        try:
            # Remove pontos de milhar e troca virgula por ponto
            clean = val_str.replace('.', '').replace(',', '.')
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
# MAIN APP - INTEGRAÇÃO FINAL
# ==============================================================================

def main():
    st.markdown('<div class="main-header">Sistema Unificado: DUIMP + Häfele (Final Pro)</div>', unsafe_allow_html=True)

    # Estado da Sessão
    if "parsed_duimp" not in st.session_state: st.session_state["parsed_duimp"] = None
    if "parsed_hafele" not in st.session_state: st.session_state["parsed_hafele"] = None
    if "merged_df" not in st.session_state: st.session_state["merged_df"] = None

    # Abas
    tab1, tab2, tab3 = st.tabs(["📂 Upload e Vinculação", "📋 Conferência Detalhada", "💾 Exportar XML"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="info-box"><strong>Passo 1:</strong> Carregue o Extrato DUIMP (Siscomex)</div>', unsafe_allow_html=True)
            file_duimp = st.file_uploader("", type="pdf", key="u1")
        with col2:
            st.markdown('<div class="info-box"><strong>Passo 2:</strong> Carregue o Relatório Häfele</div>', unsafe_allow_html=True)
            file_hafele = st.file_uploader("", type="pdf", key="u2")

        # Processamento DUIMP
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
                    st.markdown(f'<div class="success-box">✅ DUIMP processada: {len(p.items)} itens</div>', unsafe_allow_html=True)
                except Exception as e: st.error(f"Erro ao ler DUIMP: {e}")

        # Processamento Häfele
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
                    st.markdown(f'<div class="success-box">✅ Häfele processado: {qtd_itens} itens (Lógica Reversa Ativada)</div>', unsafe_allow_html=True)
                else:
                    st.warning("Atenção: Nenhum item extraído. Verifique o layout do PDF.")
            except Exception as e:
                st.error(f"Erro ao ler Häfele: {e}")
            finally:
                if os.path.exists(tmp_path): os.unlink(tmp_path)

        st.markdown("---")
        # Botão de Vinculação
        if st.button("🔗 VINCULAR DADOS (Cruzamento Automático)"):
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
                                cod = src.get('codigo_interno', '')
                                desc = src.get('descricao_complementar', '')
                                final_number = f"{cod} - {desc}" if desc else cod
                                
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
                    st.success(f"Vinculação concluída! {count} itens atualizados com sucesso.")
                    
                except Exception as e: st.error(f"Erro na vinculação: {e}")
            else:
                st.warning("Carregue os dois arquivos antes de vincular.")

    with tab2:
        st.header("📋 Conferência")
        if st.session_state["merged_df"] is not None:
            col_config = {
                "numeroAdicao": st.column_config.TextColumn("Item", width="small", disabled=True),
                "NUMBER": st.column_config.TextColumn("Código + Descrição", width="large"),
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
            if st.button("Gerar XML (Layout 8686)"):
                try:
                    p = st.session_state["parsed_duimp"]
                    records = st.session_state["merged_df"].to_dict("records")
                    for i, item in enumerate(p.items):
                        if i < len(records): item.update(records[i])
                    
                    builder = XMLBuilder(p)
                    xml_bytes = builder.build()
                    duimp_num = p.header.get("numeroDUIMP", "0000").replace("/", "-")
                    
                    st.download_button(label="⬇️ Baixar XML Final", data=xml_bytes, file_name=f"DUIMP_{duimp_num}_INTEGRADO.xml", mime="text/xml")
                    st.balloons()
                except Exception as e: st.error(f"Erro XML: {e}")
        else:
            st.warning("Realize a vinculação primeiro.")

if __name__ == "__main__":
    main()
