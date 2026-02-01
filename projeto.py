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
    """
    Parser BLINDADO para o layout Extrato DUIMP (APP2.pdf).
    """
    
    def __init__(self):
        self.documento = {
            'cabecalho': {},
            'itens': [],
            'totais': {}
        }
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            logger.info(f"Iniciando parsing do layout DUIMP/APP2: {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text(layout=False) 
                    if text:
                        full_text += text + "\n"
            
            self._process_full_text(full_text)
            return self.documento
            
        except Exception as e:
            logger.error(f"Erro CRÍTICO no parsing: {str(e)}")
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
                if item_data:
                    items_found.append(item_data)
        else:
            st.warning("⚠️ O sistema não detectou o padrão 'ITENS DA DUIMP'. Verifique se o PDF está no formato correto.")
        
        self.documento['itens'] = items_found
        self._calculate_totals()

    def _parse_item_block(self, item_num: int, text: str) -> Dict:
        try:
            item = {
                'numero_item': item_num,
                'ncm': '',
                'codigo_interno': '',
                'nome_produto': '',
                'quantidade': 0.0,
                'quantidade_comercial': 0.0,
                'peso_liquido': 0.0,
                'valor_total': 0.0,
                
                'ii_valor_devido': 0.0, 'ii_base_calculo': 0.0, 'ii_aliquota': 0.0,
                'ipi_valor_devido': 0.0, 'ipi_base_calculo': 0.0, 'ipi_aliquota': 0.0,
                'pis_valor_devido': 0.0, 'pis_base_calculo': 0.0, 'pis_aliquota': 0.0,
                'cofins_valor_devido': 0.0, 'cofins_base_calculo': 0.0, 'cofins_aliquota': 0.0,
                
                'frete_internacional': 0.0,
                'seguro_internacional': 0.0,
                'local_aduaneiro': 0.0
            }

            # Identificadores
            code_match = re.search(r'Código interno\s*([\d\.]+)', text, re.IGNORECASE)
            if code_match: item['codigo_interno'] = code_match.group(1).replace('.', '')

            ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', text)
            if ncm_match: item['ncm'] = ncm_match.group(1).replace('.', '')

            # Valores
            qtd_com_match = re.search(r'Qtde Unid\. Comercial\s*([\d\.,]+)', text)
            if qtd_com_match: item['quantidade_comercial'] = self._parse_valor(qtd_com_match.group(1))
            
            qtd_est_match = re.search(r'Qtde Unid\. Estatística\s*([\d\.,]+)', text)
            if qtd_est_match: item['quantidade'] = self._parse_valor(qtd_est_match.group(1))
            else: item['quantidade'] = item['quantidade_comercial']

            val_match = re.search(r'Valor Tot\. Cond Venda\s*([\d\.,]+)', text)
            if val_match: item['valor_total'] = self._parse_valor(val_match.group(1))

            peso_match = re.search(r'Peso Líquido \(KG\)\s*([\d\.,]+)', text, re.IGNORECASE)
            if peso_match: item['peso_liquido'] = self._parse_valor(peso_match.group(1))

            frete_match = re.search(r'Frete Internac\. \(R\$\)\s*([\d\.,]+)', text)
            if frete_match: item['frete_internacional'] = self._parse_valor(frete_match.group(1))

            seg_match = re.search(r'Seguro Internac\. \(R\$\)\s*([\d\.,]+)', text)
            if seg_match: item['seguro_internacional'] = self._parse_valor(seg_match.group(1))

            aduana_match = re.search(r'Local Aduaneiro \(R\$\)\s*([\d\.,]+)', text)
            if aduana_match: item['local_aduaneiro'] = self._parse_valor(aduana_match.group(1))

            # --- IMPOSTOS ---
            tax_patterns = re.findall(
                r'Base de Cálculo.*?\(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor.*?(?:Devido|A Recolher|Calculado).*?\(R\$\)\s*([\d\.,]+)', 
                text, 
                re.DOTALL | re.IGNORECASE
            )

            for base_str, aliq_str, val_str in tax_patterns:
                base = self._parse_valor(base_str)
                aliq = self._parse_valor(aliq_str)
                val = self._parse_valor(val_str)

                if 1.60 <= aliq <= 3.00: 
                    item['pis_aliquota'] = aliq
                    item['pis_base_calculo'] = base
                    item['pis_valor_devido'] = val
                elif 7.00 <= aliq <= 12.00:
                    item['cofins_aliquota'] = aliq
                    item['cofins_base_calculo'] = base
                    item['cofins_valor_devido'] = val
                elif aliq > 12.00: # II (Ex: 16%)
                    item['ii_aliquota'] = aliq
                    item['ii_base_calculo'] = base
                    item['ii_valor_devido'] = val
                elif aliq >= 0:
                    if item['ipi_aliquota'] == 0: 
                        item['ipi_aliquota'] = aliq
                        item['ipi_base_calculo'] = base
                        item['ipi_valor_devido'] = val

            item['total_impostos'] = (item['ii_valor_devido'] + item['ipi_valor_devido'] + 
                                    item['pis_valor_devido'] + item['cofins_valor_devido'])
            item['valor_total_com_impostos'] = item['valor_total'] + item['total_impostos']

            return item
            
        except Exception as e:
            logger.error(f"Erro item {item_num}: {e}")
            return None

    def _parse_valor(self, valor_str: str) -> float:
        try:
            if not valor_str: return 0.0
            limpo = valor_str.replace('.', '').replace(',', '.')
            return float(limpo)
        except: return 0.0

    def _calculate_totals(self):
        if self.documento['itens']:
            self.documento['totais'] = {
                'valor_total_mercadoria': sum(i['valor_total'] for i in self.documento['itens']),
                'total_impostos': sum(i['total_impostos'] for i in self.documento['itens'])
            }

# ==============================================================================
# PARTE 2: PARSER APP 1 (DUIMP)
# ==============================================================================

def montar_descricao_final(desc_complementar, codigo_extra, detalhamento):
    parte1 = str(desc_complementar).strip()
    parte2 = str(codigo_extra).strip()
    parte3 = str(detalhamento).strip()
    return f"{parte1} - {parte2} - {parte3}"

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
                item["quantidade_comercial"] = self._regex(r"Quantidade na unidade comercializada:\s*([\d\.,]+)", content)
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
                
                compl_match = re.search(r"Descrição complementar da mercadoria:\s*(.+?)(?=\n|$)", content, re.DOTALL)
                item["desc_complementar"] = compl_match.group(1).strip() if compl_match else ""

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

# Mantemos os valores padrão caso o usuário não preencha nada, mas agora o XMLBuilder aceitará dados externos.
FOOTER_TAGS = {
    "armazem": {"tag": "nomeArmazem", "default": "TCP"},
    "armazenamentoRecintoAduaneiroCodigo": "9801303",
    "armazenamentoRecintoAduaneiroNome": "TCP - TERMINAL",
    "armazenamentoSetor": "002",
    "canalSelecaoParametrizada": "001",
    "caracterizacaoOperacaoCodigoTipo": "1",
    "caracterizacaoOperacaoDescricaoTipo": "Importação Própria",
    "cargaNumeroAgente": "N/I",
    "cargaPaisProcedenciaCodigo": "386",
    "cargaPaisProcedenciaNome": "",
    "cargaUrfEntradaCodigo": "0917800",
    "cargaUrfEntradaNome": "PORTO DE PARANAGUA",
    "conhecimentoCargaEmbarqueLocal": "EXTERIOR",
    "conhecimentoCargaId": "CE123456",
    "conhecimentoCargaIdMaster": "CE123456",
    "conhecimentoCargaTipoCodigo": "12",
    "conhecimentoCargaTipoNome": "HBL - House Bill of Lading",
    "conhecimentoCargaUtilizacao": "1",
    "conhecimentoCargaUtilizacaoNome": "Total",
    "documentoChegadaCargaCodigoTipo": "1",
    "documentoChegadaCargaNome": "Manifesto da Carga",
    "documentoChegadaCargaNumero": "1625502058594",
    # Embalagem será tratada dinamicamente agora
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
                item["quantidade_comercial"] = self._regex(r"Quantidade na unidade comercializada:\s*([\d\.,]+)", content)
                
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

                compl_match = re.search(r"Descrição complementar da mercadoria:\s*(.+?)(?=\n|$)", content, re.DOTALL)
                item["desc_complementar"] = compl_match.group(1).strip() if compl_match else ""
                
                self.items.append(item)

    def _regex(self, pattern, text):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""

class XMLBuilder:
    # ALTERAÇÃO AQUI: Adicionado parametro custom_data para receber os inputs da tela
    def __init__(self, parser, edited_items=None, custom_data=None):
        self.p = parser
        self.items_to_use = edited_items if edited_items else self.p.items
        self.custom_data = custom_data if custom_data else {}
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
            
            desc_compl = DataFormatter.clean_text(it.get("desc_complementar", ""))
            final_desc = montar_descricao_final(desc_compl, input_number, original_desc)

            val_total_venda_fmt = DataFormatter.format_high_precision(it.get("valorTotal", "0"), 11)
            val_unit_fmt = DataFormatter.format_high_precision(it.get("valorUnit", "0"), 20)
            
            qtd_comercial_raw = it.get("quantidade_comercial")
            if not qtd_comercial_raw: qtd_comercial_raw = it.get("quantidade")
            
            qtd_comercial_fmt = DataFormatter.format_quantity(qtd_comercial_raw, 14)
            qtd_estatistica_fmt = DataFormatter.format_quantity(it.get("quantidade"), 14)

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
                "dadosMercadoriaMedidaEstatisticaQuantidade": qtd_estatistica_fmt, 
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
                "quantidade": qtd_comercial_fmt, 
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
                "iiAliquotaValorCalculado": ii_val_fmt, 
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

        # Mescla dados automáticos com os manuais (custom_data)
        footer_map = {
            "numeroDUIMP": duimp_fmt,
            "importadorNome": h.get("nomeImportador", ""),
            "importadorNumero": DataFormatter.format_number(h.get("cnpj"), 14),
            "cargaPaisProcedenciaNome": h.get("paisProcedencia", "").upper(),
            "totalAdicoes": str(len(self.items_to_use)).zfill(3),
            "freteTotalReais": DataFormatter.format_input_fiscal(totals["frete"]),
            "seguroTotalReais": DataFormatter.format_input_fiscal(totals["seguro"]),
        }
        
        # Injeta os dados customizados da UI no mapa
        footer_map.update(self.custom_data)

        receita_codes = [
            {"code": "0086", "val": totals["ii"]},
            {"code": "1038", "val": totals["ipi"]},
            {"code": "5602", "val": totals["pis"]},
            {"code": "5629", "val": totals["cofins"]}
        ]

        for tag, default_val in FOOTER_TAGS.items():
            if tag == "pagamento":
                # Pagamentos automáticos (Impostos)
                for rec in receita_codes:
                    if rec["val"] > 0:
                        pag = etree.SubElement(self.duimp, "pagamento")
                        etree.SubElement(pag, "agenciaPagamento").text = "3715"
                        etree.SubElement(pag, "bancoPagamento").text = "341"
                        etree.SubElement(pag, "codigoReceita").text = rec["code"]
                        etree.SubElement(pag, "valorReceita").text = DataFormatter.format_input_fiscal(rec["val"])
                
                # --- SISCOMEX 7811 (Valores vindos da tela) ---
                siscomex_val = self.custom_data.get("siscomex_valor", "000000000000000")
                pag_siscomex = etree.SubElement(self.duimp, "pagamento")
                etree.SubElement(pag_siscomex, "agenciaPagamento").text = self.custom_data.get("siscomex_agencia", "3715")
                etree.SubElement(pag_siscomex, "bancoPagamento").text = self.custom_data.get("siscomex_banco", "341")
                etree.SubElement(pag_siscomex, "codigoReceita").text = self.custom_data.get("siscomex_codigo", "7811")
                etree.SubElement(pag_siscomex, "valorReceita").text = siscomex_val
                # -----------------------------------------------
                continue

            if tag == "embalagem":
                 # --- EMBALAGEM (Valores vindos da tela) ---
                 parent = etree.SubElement(self.duimp, "embalagem")
                 etree.SubElement(parent, "codigoTipoEmbalagem").text = "60"
                 etree.SubElement(parent, "nomeEmbalagem").text = "PALLETS"
                 # Usa o valor da tela
                 etree.SubElement(parent, "quantidadeVolume").text = self.custom_data.get("quantidadeVolume", "00001")
                 continue

            if isinstance(default_val, list):
                parent = etree.SubElement(self.duimp, tag)
                for subfield in default_val:
                    etree.SubElement(parent, subfield["tag"]).text = subfield["default"]
            elif isinstance(default_val, dict):
                parent = etree.SubElement(self.duimp, tag)
                etree.SubElement(parent, default_val["tag"]).text = default_val["default"]
            else:
                # Prioridade: 1. Custom Data (Tela), 2. Footer Map (Calculado), 3. Default (Static)
                val = footer_map.get(tag, default_val)
                etree.SubElement(self.duimp, tag).text = val
        
        xml_content = etree.tostring(self.root, pretty_print=True, encoding="UTF-8", xml_declaration=False)
        header = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        return header + xml_content

# ==============================================================================
# MAIN APP - INTEGRAÇÃO FINAL
# ==============================================================================

def main():
    st.markdown('<div class="main-header">Sistema Integrado DUIMP 2026 (Versão Final Restaurada)</div>', unsafe_allow_html=True)

    if "parsed_duimp" not in st.session_state: st.session_state["parsed_duimp"] = None
    if "parsed_hafele" not in st.session_state: st.session_state["parsed_hafele"] = None
    if "merged_df" not in st.session_state: st.session_state["merged_df"] = None

    tab1, tab2, tab3 = st.tabs(["📂 Upload e Vinculação", "📋 Conferência Detalhada", "💾 Exportar XML"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.info("Passo 1: Carregue o Extrato DUIMP (Siscomex)")
            file_duimp = st.file_uploader("Arquivo DUIMP (.pdf)", type="pdf", key="u1")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.info("Passo 2: Carregue o Relatório Häfele (ou Extrato Detalhado)")
            file_hafele = st.file_uploader("Arquivo APP2 (.pdf)", type="pdf", key="u2")
            st.markdown('</div>', unsafe_allow_html=True)

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
                    cols_fiscais = [
                        "NUMBER", "Frete (R$)", "Seguro (R$)", 
                        "II (R$)", "II Base (R$)", "II Alíq. (%)",
                        "IPI (R$)", "IPI Base (R$)", "IPI Alíq. (%)",
                        "PIS (R$)", "PIS Base (R$)", "PIS Alíq. (%)",
                        "COFINS (R$)", "COFINS Base (R$)", "COFINS Alíq. (%)",
                        "Aduaneiro (R$)"
                    ]
                    for col in cols_fiscais:
                        df[col] = 0.00 if col != "NUMBER" else ""
                    st.session_state["merged_df"] = df
                    st.markdown(f'<div class="success-box">✅ DUIMP Lida com Sucesso! {len(p.items)} adições encontradas.</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Erro ao ler DUIMP: {e}")

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
                    st.markdown(f'<div class="success-box">✅ APP2 (Extrato) Lido com Sucesso! {qtd_itens} itens encontrados.</div>', unsafe_allow_html=True)
                else:
                    st.warning("O PDF foi lido, mas nenhum item 'ITENS DA DUIMP' foi identificado automaticamente.")
            except Exception as e:
                st.error(f"Erro ao ler APP2: {e}")
            finally:
                if os.path.exists(tmp_path): 
                    try: os.unlink(tmp_path) 
                    except: pass

        st.divider()

        if st.button("🔗 VINCULAR DADOS (Cruzamento Automático)", type="primary", use_container_width=True):
            if st.session_state["merged_df"] is not None and st.session_state["parsed_hafele"] is not None:
                try:
                    df_dest = st.session_state["merged_df"].copy()
                    src_map = {}
                    for item in st.session_state["parsed_hafele"]['itens']:
                        try:
                            idx = int(item['numero_item'])
                            src_map[idx] = item
                        except: pass
                    
                    count = 0
                    for idx, row in df_dest.iterrows():
                        try:
                            raw_num = str(row['numeroAdicao']).strip()
                            item_num = int(raw_num)
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
                        except Exception as e: continue
                    
                    st.session_state["merged_df"] = df_dest
                    st.success(f"Sucesso! {count} itens foram vinculados e preenchidos.")
                except Exception as e:
                    st.error(f"Erro na vinculação: {e}")
            else:
                st.warning("Carregue os dois arquivos antes de vincular.")

    with tab2:
        st.subheader("Conferência e Edição")
        if st.session_state["merged_df"] is not None:
            col_config = {
                "numeroAdicao": st.column_config.TextColumn("Item", width="small", disabled=True),
                "NUMBER": st.column_config.TextColumn("Código Interno", width="medium"),
                "Frete (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Seguro (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "II (R$)": st.column_config.NumberColumn(label="II Vlr", format="R$ %.2f"),
            }
            edited_df = st.data_editor(
                st.session_state["merged_df"],
                hide_index=True,
                column_config=col_config,
                use_container_width=True,
                height=600
            )
            taxes = ['II', 'IPI', 'PIS', 'COFINS']
            for tax in taxes:
                base_col = f"{tax} Base (R$)"
                aliq_col = f"{tax} Alíq. (%)"
                val_col = f"{tax} (R$)"
                if base_col in edited_df.columns and aliq_col in edited_df.columns:
                    edited_df[base_col] = pd.to_numeric(edited_df[base_col], errors='coerce').fillna(0.0)
                    edited_df[aliq_col] = pd.to_numeric(edited_df[aliq_col], errors='coerce').fillna(0.0)
                    edited_df[val_col] = edited_df[base_col] * (edited_df[aliq_col] / 100.0)
            st.session_state["merged_df"] = edited_df
        else:
            st.info("Nenhum dado para exibir.")

    with tab3:
        st.subheader("Gerar XML Final")
        if st.session_state["merged_df"] is not None:
            
            # --- ÁREA DE INPUTS SOLICITADA ---
            with st.expander("📝 DADOS GERAIS (Preenchimento Manual)", expanded=True):
                st.info("Preencha os dados abaixo que serão habilitados no XML.")
                
                c_vol, c_peso1, c_peso2 = st.columns(3)
                qtd_volume = c_vol.text_input("Quantidade Volume", value="00001")
                peso_bruto = c_peso1.text_input("Peso Bruto Total", value="000002114187000")
                peso_liquido = c_peso2.text_input("Peso Líquido Total", value="000002114187000")

                st.divider()
                st.markdown("**Datas:**")
                c_date1, c_date2, c_date3, c_date4 = st.columns(4)
                dt_chegada = c_date1.text_input("Data Chegada", value="20251120")
                dt_desembaraco = c_date2.text_input("Data Desembaraço", value="20251124")
                dt_registro = c_date3.text_input("Data Registro", value="20251124")
                dt_embarque = c_date4.text_input("Data Embarque (Conhec.)", value="20251025")

                st.divider()
                st.markdown("**Siscomex (Receita 7811):**")
                c_sis1, c_sis2, c_sis3, c_sis4 = st.columns(4)
                sis_agencia = c_sis1.text_input("Agência", value="3715")
                sis_banco = c_sis2.text_input("Banco", value="341")
                sis_cod = c_sis3.text_input("Cód. Receita", value="7811", disabled=True)
                sis_val = c_sis4.text_input("Valor Receita (7811)", value="000000000000000")

                st.divider()
                st.markdown("**Totais Locais (Descarga/Embarque):**")
                c_loc1, c_loc2 = st.columns(2)
                loc_desc_dolar = c_loc1.text_input("Descarga Total Dólares", value="000000000000000")
                loc_desc_reais = c_loc2.text_input("Descarga Total Reais", value="000000000000000")
                loc_emb_dolar = c_loc1.text_input("Embarque Total Dólares", value="000000000000000")
                loc_emb_reais = c_loc2.text_input("Embarque Total Reais", value="000000000000000")

            if st.button("Gerar XML (Layout 8686)", type="primary"):
                try:
                    p = st.session_state["parsed_duimp"]
                    records = st.session_state["merged_df"].to_dict("records")
                    
                    for i, item in enumerate(p.items):
                        if i < len(records):
                            item.update(records[i])
                    
                    # Dicionário com os dados manuais da tela
                    custom_data = {
                        "quantidadeVolume": qtd_volume,
                        "cargaPesoBruto": peso_bruto,
                        "cargaPesoLiquido": peso_liquido,
                        "cargaDataChegada": dt_chegada,
                        "dataDesembaraco": dt_desembaraco,
                        "dataRegistro": dt_registro,
                        "conhecimentoCargaEmbarqueData": dt_embarque,
                        
                        "siscomex_agencia": sis_agencia,
                        "siscomex_banco": sis_banco,
                        "siscomex_codigo": sis_cod,
                        "siscomex_valor": sis_val,
                        
                        "localDescargaTotalDolares": loc_desc_dolar,
                        "localDescargaTotalReais": loc_desc_reais,
                        "localEmbarqueTotalDolares": loc_emb_dolar,
                        "localEmbarqueTotalReais": loc_emb_reais
                    }

                    builder = XMLBuilder(p, custom_data=custom_data)
                    xml_bytes = builder.build()
                    
                    duimp_num = p.header.get("numeroDUIMP", "0000").replace("/", "-")
                    file_name = f"DUIMP_{duimp_num}_INTEGRADO.xml"
                    
                    st.download_button(
                        label="⬇️ Baixar XML",
                        data=xml_bytes,
                        file_name=file_name,
                        mime="text/xml"
                    )
                    st.success("XML Gerado com sucesso!")
                    
                except Exception as e:
                    st.error(f"Erro na geração do XML: {e}")
        else:
            st.warning("Realize a vinculação primeiro.")

if __name__ == "__main__":
    main()
