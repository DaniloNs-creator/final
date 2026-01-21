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
st.set_page_config(page_title="Sistema Unificado 2026 (Pro)", layout="wide")

# Estilos CSS (Mistura dos dois apps para consistência)
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1E3A8A; font-weight: bold; margin-bottom: 1rem; }
    .sub-header { font-size: 1.5rem; color: #2563EB; margin-top: 1.5rem; border-bottom: 2px solid #E5E7EB; }
    .section-card { background: #FFFFFF; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1rem; border: 1px solid #E5E7EB; }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #1E3A8A; }
    .metric-label { font-size: 0.9rem; color: #6B7280; }
    .success-box { background-color: #d1fae5; color: #065f46; padding: 10px; border-radius: 5px; margin: 10px 0; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Configurar logging (Do seu código original)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# PARTE 1: CÓDIGO ORIGINAL DO APP 2 (HÄFELE) - INTACTO
# ==============================================================================

class HafelePDFParser:
    """Parser robusto para PDFs da Häfele (SEU CÓDIGO ORIGINAL)"""
    
    def __init__(self):
        self.documento = {
            'cabecalho': {},
            'itens': [],
            'totais': {}
        }
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        """Parse completo do PDF"""
        try:
            logger.info(f"Iniciando parsing do PDF: {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"PDF com {total_pages} páginas")
                
                all_text = ""
                for page_num, page in enumerate(pdf.pages, 1):
                    logger.info(f"Processando página {page_num}/{total_pages}")
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"
            
            # Processar todo o texto
            self._process_full_text(all_text)
            
            logger.info(f"Parsing concluído. {len(self.documento['itens'])} itens processados.")
            return self.documento
            
        except Exception as e:
            logger.error(f"Erro no parsing: {str(e)}")
            raise
    
    def _process_full_text(self, text: str):
        """Processa todo o texto do PDF"""
        # Encontrar todos os itens
        items = self._find_all_items(text)
        self.documento['itens'] = items
        
        # Calcular totais
        self._calculate_totals()
    
    def _find_all_items(self, text: str) -> List[Dict]:
        """Encontra todos os itens no texto"""
        items = []
        
        # Padrão para encontrar início de itens (SEU REGEX ORIGINAL)
        item_pattern = r'(?:^|\n)(\d+)\s+(\d{4}\.\d{2}\.\d{2})\s+(\d+)\s'
        matches = list(re.finditer(item_pattern, text))
        
        logger.info(f"Encontrados {len(matches)} padrões de itens")
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            item_text = text[start_pos:end_pos]
            item_data = self._parse_item(item_text, match.group(1), match.group(2), match.group(3))
            
            if item_data:
                items.append(item_data)
        
        return items
    
    def _parse_item(self, text: str, item_num: str, ncm: str, codigo: str) -> Optional[Dict]:
        """Parse de um item individual"""
        try:
            item = {
                'numero_item': item_num,
                'ncm': ncm,
                'codigo_produto': codigo,
                'nome_produto': '',
                'codigo_interno': '',
                'pais_origem': '',
                'aplicacao': '',
                'fatura': '',
                'condicao_venda': '',
                'quantidade': 0,
                'peso_liquido': 0,
                'valor_unitario': 0,
                'valor_total': 0,
                'local_aduaneiro': 0,
                'frete_internacional': 0,
                'seguro_internacional': 0,
                
                # Campos de Impostos (Valores)
                'ii_valor_devido': 0,
                'ipi_valor_devido': 0,
                'pis_valor_devido': 0,
                'cofins_valor_devido': 0,
                
                # NOVOS CAMPOS: Base de Cálculo
                'ii_base_calculo': 0,
                'ipi_base_calculo': 0,
                'pis_base_calculo': 0,
                'cofins_base_calculo': 0,
                
                # NOVOS CAMPOS: Alíquotas
                'ii_aliquota': 0,
                'ipi_aliquota': 0,
                'pis_aliquota': 0,
                'cofins_aliquota': 0,
                
                'total_impostos': 0,
                'valor_total_com_impostos': 0
            }
            
            # --- SEÇÃO 1: TEXTOS E CÓDIGOS ---

            # Nome do Produto
            nome_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n(.*?)\n(?:DESCRICAO|MARCA)', text, re.IGNORECASE | re.DOTALL)
            if nome_match:
                item['nome_produto'] = nome_match.group(1).replace('\n', ' ').strip()
            
            # Código Interno (Limpo)
            codigo_match = re.search(r'Código interno\s*(.*?)\s*(?=FABRICANTE|Conhecido|Pais)', text, re.IGNORECASE | re.DOTALL)
            if codigo_match:
                raw_code = codigo_match.group(1)
                clean_code = raw_code.replace('(PARTNUMBER)', '').replace('Código interno', '').replace('\n', '')
                item['codigo_interno'] = clean_code.strip()
            
            # Outros campos textuais
            pais_match = re.search(r'Pais Origem\s*(.*?)\s*(?=CARACTERIZAÇÃO|\n)', text, re.IGNORECASE)
            if pais_match: item['pais_origem'] = pais_match.group(1).strip()

            fatura_match = re.search(r'Fatura/Invoice\s*([0-9]+)', text, re.IGNORECASE)
            if fatura_match: item['fatura'] = fatura_match.group(1).strip()
            
            app_match = re.search(r'Aplicação\s*(.*?)\s*(?=Condição|\n)', text, re.IGNORECASE)
            if app_match: item['aplicacao'] = app_match.group(1).strip()

            cond_venda_match = re.search(r'Cond\. Venda\s*(.*?)\s*(?=Fatura)', text, re.IGNORECASE)
            if cond_venda_match: item['condicao_venda'] = cond_venda_match.group(1).strip()

            # --- SEÇÃO 2: VALORES E QUANTIDADES ---

            qtd_match = re.search(r'Qtde Unid\. Comercial\s+([\d\.,]+)', text)
            if qtd_match: item['quantidade'] = self._parse_valor(qtd_match.group(1))
            
            peso_match = re.search(r'Peso Líquido \(KG\)\s+([\d\.,]+)', text)
            if peso_match: item['peso_liquido'] = self._parse_valor(peso_match.group(1))
            
            valor_unit_match = re.search(r'Valor Unit Cond Venda\s+([\d\.,]+)', text)
            if valor_unit_match: item['valor_unitario'] = self._parse_valor(valor_unit_match.group(1))
            
            valor_total_match = re.search(r'Valor Tot\. Cond Venda\s+([\d\.,]+)', text)
            if valor_total_match: item['valor_total'] = self._parse_valor(valor_total_match.group(1))
            
            loc_adu_match = re.search(r'Local Aduaneiro \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE)
            if loc_adu_match: item['local_aduaneiro'] = self._parse_valor(loc_adu_match.group(1))

            frete_match = re.search(r'Frete Internac\. \(R\$\)\s+([\d\.,]+)', text)
            if frete_match: item['frete_internacional'] = self._parse_valor(frete_match.group(1))
            
            seguro_match = re.search(r'Seguro Internac\. \(R\$\)\s+([\d\.,]+)', text)
            if seguro_match: item['seguro_internacional'] = self._parse_valor(seguro_match.group(1))
            
            # --- SEÇÃO 3: IMPOSTOS, BASES E ALÍQUOTAS ---
            item = self._extract_taxes_directly(text, item)
            
            # Calcular totais
            item['total_impostos'] = (
                item['ii_valor_devido'] + 
                item['ipi_valor_devido'] + 
                item['pis_valor_devido'] + 
                item['cofins_valor_devido']
            )
            
            item['valor_total_com_impostos'] = item['valor_total'] + item['total_impostos']
            
            return item
            
        except Exception as e:
            logger.error(f"Erro ao parsear item {item_num}: {str(e)}")
            return None
    
    def _extract_taxes_directly(self, text: str, item: Dict) -> Dict:
        """Extrai impostos, bases e alíquotas diretamente do texto"""
        
        # Mapeamento para Valore Devido
        tax_values = {
            'ii_valor_devido': r'II.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            'ipi_valor_devido': r'IPI.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            'pis_valor_devido': r'PIS.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            'cofins_valor_devido': r'COFINS.*?Valor Devido \(R\$\)\s*([\d\.,]+)'
        }
        
        # Mapeamento para Base de Cálculo (Procura 'Base de Cálculo (R$)' logo após o nome do imposto)
        base_values = {
            'ii_base_calculo': r'II.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
            'ipi_base_calculo': r'IPI.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
            'pis_base_calculo': r'PIS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
            'cofins_base_calculo': r'COFINS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)'
        }

        # Mapeamento para Alíquotas (Procura '% Alíquota' logo após o nome do imposto)
        rate_values = {
            'ii_aliquota': r'II.*?% Alíquota\s*([\d\.,]+)',
            'ipi_aliquota': r'IPI.*?% Alíquota\s*([\d\.,]+)',
            'pis_aliquota': r'PIS.*?% Alíquota\s*([\d\.,]+)',
            'cofins_aliquota': r'COFINS.*?% Alíquota\s*([\d\.,]+)'
        }
        
        # Executa as buscas
        all_patterns = {**tax_values, **base_values, **rate_values}
        
        for key, pattern in all_patterns.items():
            # re.DOTALL permite que o .*? atravesse linhas para encontrar o valor correspondente ao bloco
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                item[key] = self._parse_valor(match.group(1))
        
        return item
    
    def _calculate_totals(self):
        """Calcula totais do documento"""
        totais = {
            'valor_total_mercadoria': 0,
            'peso_total': 0,
            'quantidade_total': 0,
            'total_impostos': 0,
            'pis_total': 0,
            'cofins_total': 0
        }
        
        for item in self.documento['itens']:
            totais['valor_total_mercadoria'] += item.get('valor_total', 0)
            totais['peso_total'] += item.get('peso_liquido', 0)
            totais['quantidade_total'] += item.get('quantidade', 0)
            totais['pis_total'] += item.get('pis_valor_devido', 0)
            totais['cofins_total'] += item.get('cofins_valor_devido', 0)
            totais['total_impostos'] += item.get('total_impostos', 0)
        
        self.documento['totais'] = totais
    
    def _parse_valor(self, valor_str: str) -> float:
        """Converte string de valor para float"""
        try:
            if not valor_str or valor_str.strip() == '':
                return 0.0
            valor_limpo = valor_str.replace('.', '').replace(',', '.')
            return float(valor_limpo)
        except:
            return 0.0

class FinancialAnalyzer:
    """Analisador financeiro (SEU CÓDIGO ORIGINAL)"""
    
    def __init__(self, documento: Dict):
        self.documento = documento
        self.itens_df = None
        
    def prepare_dataframe(self):
        """Prepara DataFrame para análise"""
        itens_data = []
        
        for item in self.documento['itens']:
            itens_data.append({
                'Item': item.get('numero_item', ''),
                'NCM': item.get('ncm', ''),
                'Código Produto': item.get('codigo_produto', ''),
                'Código Interno': item.get('codigo_interno', ''),
                'Produto': item.get('nome_produto', ''),
                'Aplicação': item.get('aplicacao', ''),
                'País Origem': item.get('pais_origem', ''),
                'Fatura': item.get('fatura', ''),
                'Cond. Venda': item.get('condicao_venda', ''),
                'Quantidade': item.get('quantidade', 0),
                'Peso (kg)': item.get('peso_liquido', 0),
                'Valor Unit. (R$)': item.get('valor_unitario', 0),
                'Valor Total (R$)': item.get('valor_total', 0),
                'Local Aduaneiro (R$)': item.get('local_aduaneiro', 0),
                'Frete (R$)': item.get('frete_internacional', 0),
                'Seguro (R$)': item.get('seguro_internacional', 0),
                
                # Impostos - Valores
                'II (R$)': item.get('ii_valor_devido', 0),
                'IPI (R$)': item.get('ipi_valor_devido', 0),
                'PIS (R$)': item.get('pis_valor_devido', 0),
                'COFINS (R$)': item.get('cofins_valor_devido', 0),
                
                # NOVAS COLUNAS - Bases e Alíquotas
                'II Base (R$)': item.get('ii_base_calculo', 0),
                'II Alíq. (%)': item.get('ii_aliquota', 0),
                'IPI Base (R$)': item.get('ipi_base_calculo', 0),
                'IPI Alíq. (%)': item.get('ipi_aliquota', 0),
                'PIS Base (R$)': item.get('pis_base_calculo', 0),
                'PIS Alíq. (%)': item.get('pis_aliquota', 0),
                'COFINS Base (R$)': item.get('cofins_base_calculo', 0),
                'COFINS Alíq. (%)': item.get('cofins_aliquota', 0),
                
                'Total Impostos (R$)': item.get('total_impostos', 0),
                'Valor c/ Impostos (R$)': item.get('valor_total_com_impostos', 0)
            })
        
        self.itens_df = pd.DataFrame(itens_data)
        return self.itens_df

# ==============================================================================
# PARTE 2: APP 1 - PARSERS E XML BUILDER (MANTIDOS E INTEGRADOS)
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

class DuimpPDFParser:
    """Parser do App 1 (Mantido original)"""
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
        
        # --- HEADER XML EXATO ---
        xml_content = etree.tostring(self.root, pretty_print=True, encoding="UTF-8", xml_declaration=False)
        header = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        return header + xml_content

# ==============================================================================
# MAIN APP - INTEGRAÇÃO FINAL
# ==============================================================================

def main():
    st.markdown('<div class="main-header">Sistema Integrado DUIMP 2026 (Versão Final Restaurada)</div>', unsafe_allow_html=True)

    # Estado da Sessão
    if "parsed_duimp" not in st.session_state: st.session_state["parsed_duimp"] = None
    if "parsed_hafele" not in st.session_state: st.session_state["parsed_hafele"] = None
    if "merged_df" not in st.session_state: st.session_state["merged_df"] = None

    # Abas
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
            st.info("Passo 2: Carregue o Relatório Häfele")
            file_hafele = st.file_uploader("Arquivo Häfele (.pdf)", type="pdf", key="u2")
            st.markdown('</div>', unsafe_allow_html=True)

        # Processamento DUIMP (APP 1)
        if file_duimp:
            if st.session_state["parsed_duimp"] is None or file_duimp.name != getattr(st.session_state.get("last_duimp"), "name", ""):
                try:
                    p = DuimpPDFParser(file_duimp.read())
                    p.preprocess()
                    p.extract_header()
                    p.extract_items()
                    st.session_state["parsed_duimp"] = p
                    st.session_state["last_duimp"] = file_duimp
                    
                    # DataFrame Base
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

        # Processamento Häfele (APP 2 - CÓDIGO ORIGINAL)
        if file_hafele and st.session_state["parsed_hafele"] is None:
            # pdfplumber exige path, então usamos tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(file_hafele.getvalue())
                tmp_path = tmp.name
            try:
                parser_h = HafelePDFParser()
                doc_h = parser_h.parse_pdf(tmp_path)
                st.session_state["parsed_hafele"] = doc_h
                
                qtd_itens = len(doc_h['itens'])
                if qtd_itens > 0:
                    st.markdown(f'<div class="success-box">✅ Häfele Lido com Sucesso! {qtd_itens} itens encontrados.</div>', unsafe_allow_html=True)
                else:
                    st.warning("Nenhum item encontrado no PDF Häfele.")
                    
            except Exception as e:
                st.error(f"Erro ao ler Häfele: {e}")
            finally:
                if os.path.exists(tmp_path): os.unlink(tmp_path)

        st.divider()

        # Botão de Vinculação
        if st.button("🔗 VINCULAR DADOS (Cruzamento Automático)", type="primary", use_container_width=True):
            if st.session_state["merged_df"] is not None and st.session_state["parsed_hafele"] is not None:
                try:
                    df_dest = st.session_state["merged_df"].copy()
                    
                    # Mapear itens do Häfele pelo numero_item (INT)
                    src_map = {}
                    for item in st.session_state["parsed_hafele"]['itens']:
                        try:
                            # Tenta converter para int para garantir match
                            idx = int(item['numero_item'])
                            src_map[idx] = item
                        except: pass
                    
                    count = 0
                    for idx, row in df_dest.iterrows():
                        try:
                            # DUIMP também deve ser int
                            item_num = int(row['numeroAdicao'])
                            if item_num in src_map:
                                src = src_map[item_num]
                                
                                # Preenchimento dos campos mapeados
                                df_dest.at[idx, 'NUMBER'] = src.get('codigo_interno', '')
                                df_dest.at[idx, 'Frete (R$)'] = src.get('frete_internacional', 0.0)
                                df_dest.at[idx, 'Seguro (R$)'] = src.get('seguro_internacional', 0.0)
                                df_dest.at[idx, 'Aduaneiro (R$)'] = src.get('local_aduaneiro', 0.0)
                                
                                # Impostos (Valores, Bases e Alíquotas)
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
                        except:
                            continue
                    
                    st.session_state["merged_df"] = df_dest
                    st.success(f"Sucesso! {count} itens foram vinculados e preenchidos.")
                    
                except Exception as e:
                    st.error(f"Erro na vinculação: {e}")
            else:
                st.warning("Carregue os dois arquivos antes de vincular.")

    with tab2:
        st.subheader("Conferência e Edição")
        if st.session_state["merged_df"] is not None:
            # Configuração das colunas para melhor visualização
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
            st.session_state["merged_df"] = edited_df
        else:
            st.info("Nenhum dado para exibir.")

    with tab3:
        st.subheader("Gerar XML Final")
        if st.session_state["merged_df"] is not None:
            if st.button("Gerar XML (Layout 8686)", type="primary"):
                try:
                    p = st.session_state["parsed_duimp"]
                    # Converter dataframe editado para lista de dicionários
                    records = st.session_state["merged_df"].to_dict("records")
                    
                    # Atualizar os itens originais do parser com os novos dados
                    for i, item in enumerate(p.items):
                        if i < len(records):
                            item.update(records[i])
                    
                    # Construir XML
                    builder = XMLBuilder(p)
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
