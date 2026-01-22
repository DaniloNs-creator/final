import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pdfplumber
import re
import json
import tempfile
import os
import io
import sys
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
import logging
from enum import Enum
import traceback
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

# Configuração avançada de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('hafele_parser.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuração da página Streamlit
st.set_page_config(
    page_title="Sistema Avançado de Análise Häfele - APP2",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS avançados
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        color: #1E3A8A;
        font-weight: bold;
        margin-bottom: 1rem;
        text-align: center;
        background: linear-gradient(90deg, #1E3A8A, #2563EB);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #2563EB;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 3px solid #E5E7EB;
        padding-bottom: 0.5rem;
        font-weight: 600;
    }
    .section-card {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
        border: 1px solid #E5E7EB;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .section-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: bold;
        color: #1E3A8A;
        line-height: 1;
    }
    .metric-label {
        font-size: 1rem;
        color: #6B7280;
        margin-top: 0.5rem;
        font-weight: 500;
    }
    .info-box {
        background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%);
        border-left: 4px solid #1E3A8A;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 10px;
    }
    .warning-box {
        background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
        border-left: 4px solid #D97706;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 10px;
    }
    .success-box {
        background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%);
        border-left: 4px solid #059669;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 10px;
    }
    .error-box {
        background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%);
        border-left: 4px solid #DC2626;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 10px;
    }
    .tax-highlight {
        background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
        border: 2px solid #D97706;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #1E3A8A, #2563EB);
    }
    .stButton > button {
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.3);
    }
    .dataframe {
        font-size: 0.9rem;
    }
    .debug-panel {
        background: #1E293B;
        color: #E2E8F0;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


class TaxType(Enum):
    """Enum para tipos de impostos"""
    II = "Imposto de Importação"
    IPI = "IPI"
    PIS = "PIS"
    COFINS = "COFINS"
    ICMS = "ICMS"
    TAXA = "Taxa de Utilização"


@dataclass
class TaxInfo:
    """Estrutura de dados para informações de impostos"""
    tipo: TaxType
    base_calculo: float = 0.0
    aliquota: float = 0.0
    valor_devido: float = 0.0
    valor_suspenso: float = 0.0
    valor_recolher: float = 0.0
    cobertura_cambial: str = ""
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            'tipo': self.tipo.value,
            'base_calculo': self.base_calculo,
            'aliquota': self.aliquota,
            'valor_devido': self.valor_devido,
            'valor_suspenso': self.valor_suspenso,
            'valor_recolher': self.valor_recolher,
            'cobertura_cambial': self.cobertura_cambial
        }


@dataclass
class ItemInfo:
    """Estrutura de dados para informações do item"""
    numero_item: str
    ncm: str
    codigo_produto: str
    codigo_interno: str
    nome_produto: str
    descricao_produto: str
    quantidade: float
    unidade: str
    peso_liquido: float
    valor_unitario: float
    valor_total: float
    pais_origem: str
    cfop: str
    aplicacao: str
    local_aduaneiro: float = 0.0
    frete_internacional: float = 0.0
    seguro_internacional: float = 0.0
    impostos: Dict[TaxType, TaxInfo] = field(default_factory=dict)
    
    def add_tax(self, tax_info: TaxInfo):
        """Adiciona informação de imposto ao item"""
        self.impostos[tax_info.tipo] = tax_info
    
    def get_total_impostos(self) -> float:
        """Calcula total de impostos"""
        return sum(tax.valor_devido for tax in self.impostos.values())
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        base_dict = {
            'numero_item': self.numero_item,
            'ncm': self.ncm,
            'codigo_produto': self.codigo_produto,
            'codigo_interno': self.codigo_interno,
            'nome_produto': self.nome_produto,
            'descricao_produto': self.descricao_produto,
            'quantidade': self.quantidade,
            'unidade': self.unidade,
            'peso_liquido': self.peso_liquido,
            'valor_unitario': self.valor_unitario,
            'valor_total': self.valor_total,
            'pais_origem': self.pais_origem,
            'cfop': self.cfop,
            'aplicacao': self.aplicacao,
            'local_aduaneiro': self.local_aduaneiro,
            'frete_internacional': self.frete_internacional,
            'seguro_internacional': self.seguro_internacional,
            'total_impostos': self.get_total_impostos(),
            'valor_total_com_impostos': self.valor_total + self.get_total_impostos()
        }
        
        # Adicionar impostos individualmente
        for tax_type, tax_info in self.impostos.items():
            prefix = tax_type.name.lower()
            base_dict.update({
                f'{prefix}_base_calculo': tax_info.base_calculo,
                f'{prefix}_aliquota': tax_info.aliquota,
                f'{prefix}_valor_devido': tax_info.valor_devido,
                f'{prefix}_valor_suspenso': tax_info.valor_suspenso,
                f'{prefix}_valor_recolher': tax_info.valor_recolher
            })
        
        return base_dict


class PDFTextExtractor:
    """Extrator avançado de texto de PDFs"""
    
    def __init__(self):
        self.text_cache = {}
    
    def extract_text(self, pdf_path: str) -> str:
        """Extrai texto do PDF com múltiplas estratégias"""
        if pdf_path in self.text_cache:
            return self.text_cache[pdf_path]
        
        try:
            text = self._extract_with_pdfplumber(pdf_path)
            self.text_cache[pdf_path] = text
            return text
        except Exception as e:
            logger.error(f"Erro ao extrair texto: {e}")
            raise
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extrai texto usando pdfplumber com configurações otimizadas"""
        all_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extrair texto com configurações otimizadas
                text = page.extract_text(
                    x_tolerance=1,
                    y_tolerance=1,
                    keep_blank_chars=False,
                    use_text_flow=True
                )
                
                if text:
                    # Adicionar marcador de página para debug
                    all_text.append(f"\n=== PÁGINA {page_num:02d} ===\n")
                    all_text.append(text)
                
                # Tentar extrair tabelas se o texto estiver vazio
                if not text or len(text.strip()) < 100:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                if row:
                                    row_text = ' | '.join([str(cell).strip() for cell in row if cell])
                                    if row_text:
                                        all_text.append(row_text + "\n")
        
        return ''.join(all_text)


class TaxParser:
    """Parser especializado para impostos"""
    
    # Padrões de regex otimizados para cada tipo de imposto
    TAX_PATTERNS = {
        TaxType.II: [
            # Padrão 1: Formato completo
            r'(?:##\s+)?II.*?Base de Cálculo \(R\$\)\s*[:\s]*([\d\.,]+).*?% Alíquota\s*[:\s]*([\d\.,]+).*?Valor Devido \(R\$\)\s*[:\s]*([\d\.,]+)',
            # Padrão 2: Formato simplificado
            r'II.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            # Padrão 3: Apenas valor
            r'Imposto de Importacao.*?([\d\.,]+)',
        ],
        TaxType.PIS: [
            # Padrão 1: Formato completo
            r'(?:##\s+)?PIS.*?Base de Cálculo \(R\$\)\s*[:\s]*([\d\.,]+).*?% Alíquota\s*[:\s]*([\d\.,]+).*?Valor Devido \(R\$\)\s*[:\s]*([\d\.,]+)',
            # Padrão 2: Formato simplificado
            r'PIS.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            # Padrão 3: No bloco de cálculo
            r'PIS\s+[\d\.,]+\s+[\d\.,]+\s+([\d\.,]+)',
        ],
        TaxType.COFINS: [
            # Padrão 1: Formato completo
            r'(?:##\s+)?COFINS.*?Base de Cálculo \(R\$\)\s*[:\s]*([\d\.,]+).*?% Alíquota\s*[:\s]*([\d\.,]+).*?Valor Devido \(R\$\)\s*[:\s]*([\d\.,]+)',
            # Padrão 2: Formato simplificado
            r'COFINS.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            # Padrão 3: No bloco de cálculo
            r'COFINS\s+[\d\.,]+\s+[\d\.,]+\s+([\d\.,]+)',
        ],
        TaxType.IPI: [
            # Padrão 1: Formato completo
            r'(?:##\s+)?IPI.*?Base de Cálculo \(R\$\)\s*[:\s]*([\d\.,]+).*?% Alíquota\s*[:\s]*([\d\.,]+).*?Valor Devido \(R\$\)\s*[:\s]*([\d\.,]+)',
            # Padrão 2: Formato simplificado
            r'IPI.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
        ],
        TaxType.ICMS: [
            r'ICMS.*?Base de Cálculo\s*[:\s]*([\d\.,]+).*?% Alíquota Ad Valorem\s*[:\s]*([\d\.,]+).*?Valor Devido\s*[:\s]*([\d\.,]+)',
            r'Regime de Tributacao\s+(.+?)(?:\n|$)',
        ]
    }
    
    @staticmethod
    def parse_valor(valor_str: str) -> float:
        """Converte string de valor para float de forma robusta"""
        if not valor_str or valor_str.strip() == '':
            return 0.0
        
        try:
            # Remover caracteres não numéricos exceto ponto e vírgula
            valor_limpo = re.sub(r'[^\d,\.]', '', valor_str)
            
            # Se não tem vírgula, assumir que é inteiro
            if ',' not in valor_limpo and '.' in valor_limpo:
                # Tem ponto mas não vírgula - pode ser decimal com ponto
                if valor_limpo.count('.') > 1:
                    # Múltiplos pontos - remover todos e dividir por 100
                    valor_limpo = valor_limpo.replace('.', '')
                    return float(valor_limpo) / 100
                else:
                    # Apenas um ponto - tratar como decimal
                    return float(valor_limpo)
            else:
                # Tem vírgula - tratar como decimal brasileiro
                valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
                return float(valor_limpo)
                
        except Exception as e:
            logger.warning(f"Erro ao converter valor '{valor_str}': {e}")
            return 0.0
    
    def parse_tax_from_text(self, text: str, tax_type: TaxType) -> Optional[TaxInfo]:
        """Extrai informações de imposto do texto"""
        tax_info = TaxInfo(tipo=tax_type)
        
        patterns = self.TAX_PATTERNS.get(tax_type, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Diferentes padrões têm diferentes números de grupos
                if len(groups) >= 3:
                    # Padrão completo: base, aliquota, valor
                    tax_info.base_calculo = self.parse_valor(groups[0])
                    tax_info.aliquota = self.parse_valor(groups[1])
                    tax_info.valor_devido = self.parse_valor(groups[2])
                elif len(groups) == 2 and tax_type == TaxType.ICMS:
                    # ICMS pode ter apenas base e aliquota
                    tax_info.base_calculo = self.parse_valor(groups[0])
                    tax_info.aliquota = self.parse_valor(groups[1])
                elif len(groups) == 1:
                    # Padrão simplificado: apenas valor
                    tax_info.valor_devido = self.parse_valor(groups[0])
                
                # Se encontrou algum valor, retorna
                if tax_info.base_calculo > 0 or tax_info.aliquota > 0 or tax_info.valor_devido > 0:
                    return tax_info
        
        return None
    
    def parse_all_taxes_from_item(self, item_text: str) -> Dict[TaxType, TaxInfo]:
        """Extrai todos os impostos de um item"""
        taxes = {}
        
        for tax_type in [TaxType.II, TaxType.PIS, TaxType.COFINS, TaxType.IPI, TaxType.ICMS]:
            tax_info = self.parse_tax_from_text(item_text, tax_type)
            if tax_info:
                taxes[tax_type] = tax_info
        
        return taxes


class APP2Parser:
    """Parser principal para documentos APP2.pdf da Häfele"""
    
    def __init__(self):
        self.text_extractor = PDFTextExtractor()
        self.tax_parser = TaxParser()
        self.document_data = {
            'cabecalho': {},
            'itens': [],
            'totais': {},
            'carga': {},
            'transporte': {},
            'moedas': {},
            'impostos_totais': {}
        }
    
    def parse_document(self, pdf_path: str) -> Dict:
        """Parseia o documento completo"""
        try:
            logger.info("Iniciando parse do documento APP2")
            
            # Extrair texto do PDF
            text = self.text_extractor.extract_text(pdf_path)
            
            # Parsear diferentes seções
            self._parse_header(text)
            self._parse_carga(text)
            self._parse_transporte(text)
            self._parse_moedas(text)
            self._parse_total_taxes(text)
            
            # Parsear itens
            items = self._parse_items(text)
            self.document_data['itens'] = items
            
            # Calcular totais
            self._calculate_totals()
            
            logger.info(f"Parse concluído: {len(items)} itens processados")
            return self.document_data
            
        except Exception as e:
            logger.error(f"Erro no parse do documento: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _parse_header(self, text: str):
        """Parseia o cabeçalho do documento"""
        header = {}
        
        try:
            # Processo
            processo_match = re.search(r'PROCESSO\s*#(\d+)', text)
            if processo_match:
                header['processo'] = processo_match.group(1)
            
            # Importador
            importador_match = re.search(r'IMPORTADOR\s+(.+?)\s+CNPJ', text, re.DOTALL)
            if importador_match:
                header['importador'] = importador_match.group(1).replace('\n', ' ').strip()
            
            # CNPJ
            cnpj_match = re.search(r'CNPJ\s+([\d\.\/\-]+)', text)
            if cnpj_match:
                header['cnpj'] = cnpj_match.group(1)
            
            # Data de cadastro
            data_match = re.search(r'Data de Cadastro\s+(\d{2}/\d{2}/\d{4})', text)
            if data_match:
                header['data_cadastro'] = data_match.group(1)
            
            # Responsável
            resp_match = re.search(r'Responsavel Legal\s+(.+?)(?:\n|$)', text)
            if resp_match:
                header['responsavel'] = resp_match.group(1).strip()
            
            self.document_data['cabecalho'] = header
            logger.info(f"Cabeçalho parseado: {header}")
            
        except Exception as e:
            logger.error(f"Erro ao parsear cabeçalho: {e}")
    
    def _parse_carga(self, text: str):
        """Parseia informações da carga"""
        carga = {}
        
        try:
            # Via de transporte
            via_match = re.search(r'Via de Transporte\s+(.+?)\s+Num\.', text)
            if via_match:
                carga['via_transporte'] = via_match.group(1).strip()
            
            # Identificação
            ident_match = re.search(r'Num\. Identificacao\s+(\d+)', text)
            if ident_match:
                carga['identificacao_carga'] = ident_match.group(1)
            
            # Datas
            embarque_match = re.search(r'Data de Embarque\s+(\d{2}/\d{2}/\d{4})', text)
            if embarque_match:
                carga['data_embarque'] = embarque_match.group(1)
            
            chegada_match = re.search(r'Data de Chegada\s+(\d{2}/\d{2}/\d{4})', text)
            if chegada_match:
                carga['data_chegada'] = chegada_match.group(1)
            
            # Pesos
            peso_bruto_match = re.search(r'Peso Bruto\s+([\d\.,]+)', text)
            if peso_bruto_match:
                carga['peso_bruto'] = self.tax_parser.parse_valor(peso_bruto_match.group(1))
            
            peso_liquido_match = re.search(r'Peso Liquido\s+([\d\.,]+)', text)
            if peso_liquido_match:
                carga['peso_liquido'] = self.tax_parser.parse_valor(peso_liquido_match.group(1))
            
            self.document_data['carga'] = carga
            logger.info(f"Carga parseada: {carga}")
            
        except Exception as e:
            logger.error(f"Erro ao parsear carga: {e}")
    
    def _parse_transporte(self, text: str):
        """Parseia informações de transporte"""
        transporte = {}
        
        try:
            # Conhecimento
            conhecimento_match = re.search(r'Tipo Conhecimento\s+(\d+)\s+-\s+(.+)', text)
            if conhecimento_match:
                transporte['tipo_conhecimento'] = {
                    'codigo': conhecimento_match.group(1),
                    'descricao': conhecimento_match.group(2).strip()
                }
            
            # Frete
            frete_match = re.search(r'FRETE.*?Total \(Moeda\)\s+([\d\.,]+).*?Total \(R\$\)\s+([\d\.,]+)', text, re.DOTALL)
            if frete_match:
                transporte['frete'] = {
                    'valor_moeda': self.tax_parser.parse_valor(frete_match.group(1)),
                    'valor_real': self.tax_parser.parse_valor(frete_match.group(2))
                }
            
            # Seguro
            seguro_match = re.search(r'SEGURO.*?Total \(Moeda\)\s+([\d\.,]+).*?Total \(R\$\)\s+([\d\.,]+)', text, re.DOTALL)
            if seguro_match:
                transporte['seguro'] = {
                    'valor_moeda': self.tax_parser.parse_valor(seguro_match.group(1)),
                    'valor_real': self.tax_parser.parse_valor(seguro_match.group(2))
                }
            
            self.document_data['transporte'] = transporte
            logger.info(f"Transporte parseado: {transporte}")
            
        except Exception as e:
            logger.error(f"Erro ao parsear transporte: {e}")
    
    def _parse_moedas(self, text: str):
        """Parseia informações de moedas"""
        moedas = {}
        
        try:
            # Moeda negociada
            moeda_match = re.search(r'Moeda Negociada\s+\d+\s+-\s+(.+?)\s+Cotacao\s+([\d\.,]+)', text)
            if moeda_match:
                moedas['moeda_negociada'] = {
                    'nome': moeda_match.group(1).strip(),
                    'cotacao': self.tax_parser.parse_valor(moeda_match.group(2))
                }
            
            # Data da cotação
            data_match = re.search(r'MOEDAS/COTACOES - \((\d{2}/\d{2}/\d{4})\)', text)
            if data_match:
                moedas['data_cotacao'] = data_match.group(1)
            
            self.document_data['moedas'] = moedas
            logger.info(f"Moedas parseadas: {moedas}")
            
        except Exception as e:
            logger.error(f"Erro ao parsear moedas: {e}")
    
    def _parse_total_taxes(self, text: str):
        """Parseia impostos totais da primeira página"""
        impostos = {}
        
        try:
            # Seção de cálculos de tributos
            calc_section = re.search(r'CÁLCULOS DOS TRIBUTOS.*?RECEITA', text, re.DOTALL)
            
            if calc_section:
                calc_text = calc_section.group(0)
                
                # Procurar por cada linha de imposto
                lines = calc_text.split('\n')
                for line in lines:
                    if 'II' in line and len(line.split()) >= 6:
                        parts = line.split()
                        if len(parts) >= 6:
                            impostos['ii'] = {
                                'calculado': self.tax_parser.parse_valor(parts[1]),
                                'a_recolher': self.tax_parser.parse_valor(parts[5])
                            }
                    
                    elif 'PIS' in line and len(line.split()) >= 6:
                        parts = line.split()
                        if len(parts) >= 6:
                            impostos['pis'] = {
                                'calculado': self.tax_parser.parse_valor(parts[1]),
                                'a_recolher': self.tax_parser.parse_valor(parts[5])
                            }
                    
                    elif 'COFINS' in line and len(line.split()) >= 6:
                        parts = line.split()
                        if len(parts) >= 6:
                            impostos['cofins'] = {
                                'calculado': self.tax_parser.parse_valor(parts[1]),
                                'a_recolher': self.tax_parser.parse_valor(parts[5])
                            }
            
            self.document_data['impostos_totais'] = impostos
            logger.info(f"Impostos totais parseados: {impostos}")
            
        except Exception as e:
            logger.error(f"Erro ao parsear impostos totais: {e}")
    
    def _parse_items(self, text: str) -> List[Dict]:
        """Parseia todos os itens do documento"""
        items = []
        
        try:
            # Encontrar seções de itens
            # Primeiro tentar pelo padrão "ITENS DA DUIMP"
            item_sections = re.findall(r'ITENS DA DUIMP - (\d{5}).*?(?=(?:ITENS DA DUIMP - \d{5}|$))', text, re.DOTALL)
            
            if not item_sections:
                # Tentar outro padrão se o primeiro não funcionar
                item_sections = re.findall(r'Item\s+(\d+).*?(?=(?:Item\s+\d+|$))', text, re.DOTALL)
            
            for i, section_text in enumerate(item_sections, 1):
                try:
                    if isinstance(section_text, tuple):
                        item_num = section_text[0]
                        item_text = section_text[0] + section_text[1] if len(section_text) > 1 else section_text[0]
                    else:
                        item_num = f"{i:05d}"
                        item_text = section_text
                    
                    # Parsear o item individual
                    item_data = self._parse_single_item(item_text, item_num)
                    if item_data:
                        items.append(item_data.to_dict())
                        
                except Exception as e:
                    logger.error(f"Erro ao parsear item {i}: {e}")
                    continue
            
            logger.info(f"Parseados {len(items)} itens")
            
        except Exception as e:
            logger.error(f"Erro ao parsear itens: {e}")
        
        return items
    
    def _parse_single_item(self, text: str, item_num: str) -> Optional[ItemInfo]:
        """Parseia um único item"""
        try:
            # Extrair informações básicas
            ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', text)
            ncm = ncm_match.group(1) if ncm_match else ""
            
            codigo_produto_match = re.search(r'NCM.*?(\d{3})', text)
            codigo_produto = codigo_produto_match.group(1) if codigo_produto_match else ""
            
            # Nome do produto
            nome_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n*(.+?)(?:\nDESCRICAO|\nCÓDIGO|\Z)', text, re.DOTALL | re.IGNORECASE)
            nome_produto = nome_match.group(1).replace('\n', ' ').strip() if nome_match else ""
            
            # Descrição
            desc_match = re.search(r'DESCRICAO DO PRODUTO\s*\n*(.+?)(?:\nCÓDIGO INTERNO|\nFABRICANTE|\Z)', text, re.DOTALL | re.IGNORECASE)
            descricao = desc_match.group(1).replace('\n', ' ').strip() if desc_match else ""
            
            # Código interno
            codigo_match = re.search(r'Código interno\s*(\d+\.\d+\.\d+)', text)
            codigo_interno = codigo_match.group(1) if codigo_match else ""
            
            # Quantidade
            qtd_match = re.search(r'Qtde Unid\. Comercial\s+([\d\.,]+)', text)
            quantidade = self.tax_parser.parse_valor(qtd_match.group(1)) if qtd_match else 0.0
            
            # Unidade
            unid_match = re.search(r'Unidade Comercial\s+(.+?)(?:\n|$)', text)
            unidade = unid_match.group(1).strip() if unid_match else ""
            
            # Peso
            peso_match = re.search(r'Peso Líquido \(KG\)\s+([\d\.,]+)', text)
            peso = self.tax_parser.parse_valor(peso_match.group(1)) if peso_match else 0.0
            
            # Valor unitário
            valor_unit_match = re.search(r'Valor Unit Cond Venda\s+([\d\.,]+)', text)
            valor_unitario = self.tax_parser.parse_valor(valor_unit_match.group(1)) if valor_unit_match else 0.0
            
            # Valor total
            valor_total_match = re.search(r'Valor Tot\. Cond Venda\s+([\d\.,]+)', text)
            valor_total = self.tax_parser.parse_valor(valor_total_match.group(1)) if valor_total_match else 0.0
            
            # País de origem
            pais_match = re.search(r'Pais Origem\s+(.+?)(?:\n|$)', text)
            pais = pais_match.group(1).strip() if pais_match else ""
            
            # CFOP
            cfop_match = re.search(r'CFOP\s+(\d+)\s+-\s+(.+?)(?:\n|$)', text)
            cfop = f"{cfop_match.group(1)} - {cfop_match.group(2).strip()}" if cfop_match else ""
            
            # Aplicação
            app_match = re.search(r'Aplicação\s+(.+?)(?:\n|$)', text)
            aplicacao = app_match.group(1).strip() if app_match else ""
            
            # Local aduaneiro
            local_match = re.search(r'Local Aduaneiro \(R\$\)\s+([\d\.,]+)', text)
            local_aduaneiro = self.tax_parser.parse_valor(local_match.group(1)) if local_match else 0.0
            
            # Criar objeto ItemInfo
            item = ItemInfo(
                numero_item=item_num,
                ncm=ncm,
                codigo_produto=codigo_produto,
                codigo_interno=codigo_interno,
                nome_produto=nome_produto,
                descricao_produto=descricao,
                quantidade=quantidade,
                unidade=unidade,
                peso_liquido=peso,
                valor_unitario=valor_unitario,
                valor_total=valor_total,
                pais_origem=pais,
                cfop=cfop,
                aplicacao=aplicacao,
                local_aduaneiro=local_aduaneiro
            )
            
            # Extrair impostos
            taxes = self.tax_parser.parse_all_taxes_from_item(text)
            for tax_type, tax_info in taxes.items():
                item.add_tax(tax_info)
            
            # Log do item parseado
            logger.debug(f"Item {item_num} parseado: {item.nome_produto[:50]}...")
            logger.debug(f"  Valor: R$ {item.valor_total:.2f}, Impostos: R$ {item.get_total_impostos():.2f}")
            
            return item
            
        except Exception as e:
            logger.error(f"Erro ao parsear item {item_num}: {e}")
            return None
    
    def _calculate_totals(self):
        """Calcula totais do documento"""
        totais = defaultdict(float)
        
        for item in self.document_data['itens']:
            totais['valor_total_mercadoria'] += item.get('valor_total', 0)
            totais['quantidade_total'] += item.get('quantidade', 0)
            totais['peso_total'] += item.get('peso_liquido', 0)
            totais['total_impostos'] += item.get('total_impostos', 0)
            totais['ii_total'] += item.get('ii_valor_devido', 0)
            totais['pis_total'] += item.get('pis_valor_devido', 0)
            totais['cofins_total'] += item.get('cofins_valor_devido', 0)
        
        self.document_data['totais'] = dict(totais)


class FinancialAnalyzer:
    """Analisador financeiro avançado"""
    
    def __init__(self, document_data: Dict):
        self.document_data = document_data
        self.items_df = None
        self.summary_df = None
        
    def prepare_dataframes(self):
        """Prepara todos os DataFrames para análise"""
        # DataFrame de itens
        items_data = []
        
        for item in self.document_data['itens']:
            items_data.append(item)
        
        self.items_df = pd.DataFrame(items_data)
        
        # DataFrame de resumo
        totais = self.document_data.get('totais', {})
        impostos_totais = self.document_data.get('impostos_totais', {})
        
        summary_data = [
            {'Métrica': 'Valor Total Mercadoria', 'Valor (R$)': totais.get('valor_total_mercadoria', 0)},
            {'Métrica': 'Quantidade Total', 'Valor': totais.get('quantidade_total', 0), 'Unidade': 'un'},
            {'Métrica': 'Peso Total', 'Valor (kg)': totais.get('peso_total', 0)},
            {'Métrica': 'Total Impostos', 'Valor (R$)': totais.get('total_impostos', 0)},
            {'Métrica': 'II Total', 'Valor (R$)': totais.get('ii_total', 0)},
            {'Métrica': 'PIS Total', 'Valor (R$)': totais.get('pis_total', 0)},
            {'Métrica': 'COFINS Total', 'Valor (R$)': totais.get('cofins_total', 0)},
        ]
        
        # Adicionar impostos totais da primeira página
        if 'ii' in impostos_totais:
            summary_data.append({'Métrica': 'II Total (Pág 1)', 'Valor (R$)': impostos_totais['ii'].get('a_recolher', 0)})
        
        if 'pis' in impostos_totais:
            summary_data.append({'Métrica': 'PIS Total (Pág 1)', 'Valor (R$)': impostos_totais['pis'].get('a_recolher', 0)})
        
        if 'cofins' in impostos_totais:
            summary_data.append({'Métrica': 'COFINS Total (Pág 1)', 'Valor (R$)': impostos_totais['cofins'].get('a_recolher', 0)})
        
        self.summary_df = pd.DataFrame(summary_data)
        
        return self.items_df, self.summary_df


class APP2Dashboard:
    """Dashboard principal do sistema"""
    
    def __init__(self):
        self.parser = APP2Parser()
        self.analyzer = None
        
    def run(self):
        """Executa o dashboard"""
        st.markdown('<h1 class="main-header">🏭 Sistema Avançado de Análise Häfele - APP2</h1>', unsafe_allow_html=True)
        
        # Sidebar
        with st.sidebar:
            self._render_sidebar()
        
        # Main content
        uploaded_file = st.session_state.get('uploaded_file', None)
        
        if uploaded_file:
            self._process_file(uploaded_file)
        else:
            self._render_welcome()
    
    def _render_sidebar(self):
        """Renderiza a sidebar"""
        st.markdown("### 📁 Upload do Documento")
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo APP2.pdf",
            type=['pdf'],
            key='file_uploader',
            help="Documento PDF no formato APP2.pdf da Häfele"
        )
        
        if uploaded_file:
            st.session_state['uploaded_file'] = uploaded_file
        
        st.markdown("---")
        st.markdown("### ⚙️ Configurações")
        
        st.session_state['show_debug'] = st.checkbox("Modo Debug", value=False)
        st.session_state['show_raw_text'] = st.checkbox("Mostrar texto extraído", value=False)
        
        st.markdown("---")
        st.markdown("### 📊 Análises")
        
        st.session_state['tax_analysis'] = st.checkbox("Análise Detalhada de Impostos", value=True)
        st.session_state['financial_analysis'] = st.checkbox("Análise Financeira", value=True)
        
        st.markdown("---")
        
        if 'uploaded_file' in st.session_state:
            file = st.session_state['uploaded_file']
            st.success(f"✅ **{file.name}**")
            st.info(f"📦 Tamanho: {file.size / 1024:.1f} KB")
            
            if st.button("🔄 Processar Novamente"):
                st.session_state.pop('processed_data', None)
                st.rerun()
    
    def _render_welcome(self):
        """Renderiza a tela de boas-vindas"""
        st.markdown("""
        <div class="info-box">
            <h3>🎯 Sistema de Análise de Extratos APP2.pdf</h3>
            <p>Este sistema foi desenvolvido especificamente para processar documentos <strong>APP2.pdf</strong> da Häfele.</p>
            
            <h4>🚀 Funcionalidades Principais:</h4>
            <ul>
                <li><strong>Extração Robusta de Impostos</strong>: II, PIS, COFINS, IPI, ICMS</li>
                <li><strong>Parse Inteligente</strong>: Múltiplas estratégias de fallback</li>
                <li><strong>Análise Financeira</strong>: Gráficos e métricas detalhadas</li>
                <li><strong>Exportação Completa</strong>: CSV, Excel, JSON</li>
                <li><strong>Debug Avançado</strong>: Logs detalhados e visualização do parse</li>
            </ul>
            
            <h4>📋 Como Usar:</h4>
            <ol>
                <li>Carregue um arquivo <strong>APP2.pdf</strong> no menu à esquerda</li>
                <li>Aguarde o processamento automático</li>
                <li>Explore os dados nas diferentes abas</li>
                <li>Exporte os resultados nos formatos desejados</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # Exemplo de estrutura
        with st.expander("📚 Exemplo de Estrutura APP2.pdf"):
            st.markdown("""
            ### Estrutura Típica do Documento:
            
            **Página 1:**
            - Cabeçalho (Processo, Importador, CNPJ)
            - Moedas e Cotações
            - Cálculos dos Tributos (Totais)
            - Resumo da Carga
            
            **Páginas 2+:**
            - Itens da DUIMP (001, 002, etc.)
            - Para cada item:
              * Nome e Descrição do Produto
              * Códigos (NCM, Interno)
              * Valores (Unitário, Total)
              * **Cálculos dos Tributos por Item**
              * Informações de ICMS
            """)
    
    def _process_file(self, uploaded_file):
        """Processa o arquivo carregado"""
        if 'processed_data' in st.session_state and not st.button("🔄 Reprocessar"):
            document_data = st.session_state['processed_data']
        else:
            with st.spinner("🔍 Analisando documento APP2..."):
                # Criar arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    # Parsear documento
                    document_data = self.parser.parse_document(tmp_path)
                    st.session_state['processed_data'] = document_data
                    
                    # Preparar analisador
                    self.analyzer = FinancialAnalyzer(document_data)
                    items_df, summary_df = self.analyzer.prepare_dataframes()
                    st.session_state['items_df'] = items_df
                    st.session_state['summary_df'] = summary_df
                    
                finally:
                    # Limpar arquivo temporário
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
        
        # Renderizar resultados
        self._render_results()
    
    def _render_results(self):
        """Renderiza os resultados do processamento"""
        document_data = st.session_state.get('processed_data', {})
        items_df = st.session_state.get('items_df', pd.DataFrame())
        summary_df = st.session_state.get('summary_df', pd.DataFrame())
        
        # Header com métricas rápidas
        self._render_quick_metrics(document_data)
        
        # Tabs principais
        tabs = st.tabs([
            "📋 Visão Geral", 
            "📦 Itens", 
            "💰 Impostos", 
            "📈 Análises",
            "🔧 Debug"
        ])
        
        with tabs[0]:
            self._render_overview_tab(document_data)
        
        with tabs[1]:
            self._render_items_tab(items_df)
        
        with tabs[2]:
            self._render_taxes_tab(document_data, items_df)
        
        with tabs[3]:
            self._render_analysis_tab(items_df, summary_df)
        
        with tabs[4]:
            self._render_debug_tab(document_data)
        
        # Exportação
        self._render_export_section(items_df, summary_df, document_data)
    
    def _render_quick_metrics(self, document_data: Dict):
        """Renderiza métricas rápidas no topo"""
        totais = document_data.get('totais', {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="section-card">
                <div class="metric-value">R$ {totais.get('valor_total_mercadoria', 0):,.2f}</div>
                <div class="metric-label">Valor Mercadoria</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="section-card">
                <div class="metric-value">R$ {totais.get('total_impostos', 0):,.2f}</div>
                <div class="metric-label">Total Impostos</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="section-card">
                <div class="metric-value">{len(document_data.get('itens', []))}</div>
                <div class="metric-label">Itens</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            pis_total = totais.get('pis_total', 0)
            cofins_total = totais.get('cofins_total', 0)
            total_pis_cofins = pis_total + cofins_total
            
            st.markdown(f"""
            <div class="section-card">
                <div class="metric-value">R$ {total_pis_cofins:,.2f}</div>
                <div class="metric-label">PIS + COFINS</div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_overview_tab(self, document_data: Dict):
        """Renderiza a aba de visão geral"""
        # Cabeçalho
        col1, col2 = st.columns(2)
        
        with col1:
            if document_data.get('cabecalho'):
                st.markdown("### 📋 Informações do Processo")
                cabecalho = document_data['cabecalho']
                
                for key, value in cabecalho.items():
                    if value:
                        st.info(f"**{key.replace('_', ' ').title()}:** {value}")
        
        with col2:
            if document_data.get('carga'):
                st.markdown("### 📦 Informações da Carga")
                carga = document_data['carga']
                
                if carga.get('data_embarque'):
                    st.info(f"**Data Embarque:** {carga['data_embarque']}")
                if carga.get('data_chegada'):
                    st.info(f"**Data Chegada:** {carga['data_chegada']}")
                if carga.get('peso_liquido'):
                    st.info(f"**Peso Líquido:** {carga['peso_liquido']:,.2f} kg")
        
        # Resumo de impostos
        st.markdown("### 🏛️ Resumo de Impostos")
        
        if document_data.get('impostos_totais'):
            impostos = document_data['impostos_totais']
            
            cols = st.columns(len(impostos))
            
            for idx, (imposto_key, imposto_data) in enumerate(impostos.items()):
                if idx < len(cols):
                    with cols[idx]:
                        valor = imposto_data.get('a_recolher', 0)
                        nome = imposto_key.upper()
                        
                        st.markdown(f"""
                        <div class="tax-highlight">
                            <div style="font-size: 1.2rem; font-weight: bold; color: #1E3A8A;">{nome}</div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: #2563EB; margin-top: 0.5rem;">R$ {valor:,.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
    
    def _render_items_tab(self, items_df: pd.DataFrame):
        """Renderiza a aba de itens"""
        if items_df.empty:
            st.warning("Nenhum item encontrado no documento.")
            return
        
        st.markdown(f"### 📦 Itens Encontrados: {len(items_df)}")
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            if 'Código Interno' in items_df.columns:
                codigos = items_df['Código Interno'].unique()
                selected_codigos = st.multiselect(
                    "Filtrar por Código Interno",
                    options=codigos,
                    default=[]
                )
        
        with col2:
            if 'Produto' in items_df.columns:
                search_term = st.text_input("Buscar por nome do produto")
        
        # Aplicar filtros
        filtered_df = items_df.copy()
        
        if selected_codigos:
            filtered_df = filtered_df[filtered_df['Código Interno'].isin(selected_codigos)]
        
        if search_term:
            filtered_df = filtered_df[filtered_df['Produto'].str.contains(search_term, case=False, na=False)]
        
        # Selecionar colunas para exibição
        default_cols = [
            'Item', 'Código Interno', 'Produto', 'Quantidade', 'Unidade',
            'Valor Total (R$)', 'II (R$)', 'PIS (R$)', 'COFINS (R$)', 'Total Impostos (R$)'
        ]
        
        available_cols = [col for col in default_cols if col in filtered_df.columns]
        other_cols = [col for col in filtered_df.columns if col not in available_cols]
        
        selected_cols = st.multiselect(
            "Selecionar colunas para exibição",
            options=available_cols + other_cols,
            default=available_cols
        )
        
        if selected_cols:
            display_df = filtered_df[selected_cols].copy()
            
            # Formatar colunas numéricas
            numeric_cols = display_df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if '(R$)' in col:
                    display_df[col] = display_df[col].apply(lambda x: f"R$ {x:,.2f}")
                elif '(%)' in col:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(display_df, use_container_width=True, height=500)
        
        # Estatísticas rápidas
        if not filtered_df.empty:
            st.markdown("#### 📊 Estatísticas dos Itens Filtrados")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_valor = filtered_df['Valor Total (R$)'].sum() if 'Valor Total (R$)' in filtered_df.columns else 0
                st.metric("Valor Total", f"R$ {total_valor:,.2f}")
            
            with col2:
                total_quantidade = filtered_df['Quantidade'].sum() if 'Quantidade' in filtered_df.columns else 0
                st.metric("Quantidade Total", f"{total_quantidade:,.0f}")
            
            with col3:
                if 'Total Impostos (R$)' in filtered_df.columns:
                    total_impostos = filtered_df['Total Impostos (R$)'].sum()
                    st.metric("Impostos Total", f"R$ {total_impostos:,.2f}")
            
            with col4:
                if 'PIS (R$)' in filtered_df.columns:
                    total_pis = filtered_df['PIS (R$)'].sum()
                    st.metric("PIS Total", f"R$ {total_pis:,.2f}")
    
    def _render_taxes_tab(self, document_data: Dict, items_df: pd.DataFrame):
        """Renderiza a aba de impostos"""
        st.markdown("### 💰 Análise Detalhada de Impostos")
        
        if items_df.empty:
            st.warning("Nenhum dado disponível para análise.")
            return
        
        # Gráfico de distribuição de impostos
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Distribuição por Tipo de Imposto")
            
            # Calcular totais por tipo de imposto
            tax_totals = {}
            
            for tax_col in ['II (R$)', 'PIS (R$)', 'COFINS (R$)', 'IPI (R$)']:
                if tax_col in items_df.columns:
                    tax_totals[tax_col.replace(' (R$)', '')] = items_df[tax_col].sum()
            
            if tax_totals:
                fig = px.pie(
                    values=list(tax_totals.values()),
                    names=list(tax_totals.keys()),
                    title="Distribuição dos Impostos",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 📈 Impostos por Item")
            
            # Top 10 itens por valor de impostos
            if 'Total Impostos (R$)' in items_df.columns and 'Produto' in items_df.columns:
                top_items = items_df.nlargest(10, 'Total Impostos (R$)')[['Produto', 'Total Impostos (R$)']]
                
                fig = px.bar(
                    top_items,
                    x='Produto',
                    y='Total Impostos (R$)',
                    title="Top 10 Itens por Valor de Impostos",
                    color='Total Impostos (R$)',
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
        
        # Tabela detalhada de impostos
        st.markdown("#### 📋 Detalhamento por Item")
        
        tax_cols = [col for col in items_df.columns if any(tax in col for tax in ['II', 'PIS', 'COFINS', 'IPI', 'ICMS'])]
        if tax_cols:
            tax_detail_df = items_df[['Item', 'Produto'] + tax_cols].copy()
            
            # Formatar valores
            for col in tax_cols:
                if '(R$)' in col:
                    tax_detail_df[col] = tax_detail_df[col].apply(lambda x: f"R$ {x:,.2f}")
                elif '(%)' in col:
                    tax_detail_df[col] = tax_detail_df[col].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(tax_detail_df, use_container_width=True, height=400)
        
        # Análise de alíquotas
        st.markdown("#### 📐 Análise de Alíquotas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'II Alíq. (%)' in items_df.columns:
                avg_ii = items_df['II Alíq. (%)'].mean()
                st.metric("Alíquota Média II", f"{avg_ii:.2f}%")
        
        with col2:
            if 'PIS Alíq. (%)' in items_df.columns:
                avg_pis = items_df['PIS Alíq. (%)'].mean()
                st.metric("Alíquota Média PIS", f"{avg_pis:.2f}%")
    
    def _render_analysis_tab(self, items_df: pd.DataFrame, summary_df: pd.DataFrame):
        """Renderiza a aba de análises"""
        st.markdown("### 📈 Análises Financeiras Avançadas")
        
        if items_df.empty:
            st.warning("Nenhum dado disponível para análise.")
            return
        
        # Análise de valor vs impostos
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💰 Valor vs Impostos")
            
            if 'Valor Total (R$)' in items_df.columns and 'Total Impostos (R$)' in items_df.columns:
                fig = px.scatter(
                    items_df,
                    x='Valor Total (R$)',
                    y='Total Impostos (R$)',
                    size='Quantidade',
                    color='Produto',
                    title="Relação: Valor do Item vs Impostos",
                    hover_data=['Item', 'Código Interno']
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 📊 Eficiência Tributária")
            
            if 'Valor Total (R$)' in items_df.columns and 'Total Impostos (R$)' in items_df.columns:
                items_df['% Impostos'] = (items_df['Total Impostos (R$)'] / items_df['Valor Total (R$)']) * 100
                
                fig = px.bar(
                    items_df.nlargest(10, '% Impostos'),
                    x='Produto',
                    y='% Impostos',
                    title="Top 10 Itens por % de Impostos",
                    color='% Impostos',
                    color_continuous_scale='RdYlGn_r'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
        
        # Resumo estatístico
        st.markdown("#### 📋 Resumo Estatístico")
        
        if not summary_df.empty:
            st.dataframe(summary_df, use_container_width=True)
        
        # Análise de tendências
        st.markdown("#### 📈 Tendências por Item")
        
        numeric_cols = items_df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            selected_col = st.selectbox(
                "Selecione a métrica para análise",
                options=numeric_cols.tolist()
            )
            
            if selected_col:
                fig = px.histogram(
                    items_df,
                    x=selected_col,
                    title=f"Distribuição de {selected_col}",
                    nbins=20
                )
                st.plotly_chart(fig, use_container_width=True)
    
    def _render_debug_tab(self, document_data: Dict):
        """Renderiza a aba de debug"""
        st.markdown("### 🔧 Painel de Debug")
        
        if st.session_state.get('show_debug', False):
            # Informações do parse
            with st.expander("📊 Estatísticas do Parse"):
                stats = {
                    'Total Itens': len(document_data.get('itens', [])),
                    'Cabeçalho Extraído': bool(document_data.get('cabecalho')),
                    'Carga Extraída': bool(document_data.get('carga')),
                    'Impostos Totais Extraídos': bool(document_data.get('impostos_totais')),
                    'Moedas Extraídas': bool(document_data.get('moedas'))
                }
                
                for key, value in stats.items():
                    st.write(f"**{key}:** {value}")
            
            # Logs
            with st.expander("📝 Logs do Sistema"):
                try:
                    with open('hafele_parser.log', 'r') as f:
                        logs = f.readlines()[-100:]  # Últimas 100 linhas
                    
                    st.text_area("Logs", ''.join(logs), height=300)
                except:
                    st.warning("Arquivo de log não encontrado.")
            
            # Dados brutos
            with st.expander("📄 Dados Brutos Extraídos"):
                st.json(document_data, expanded=False)
    
    def _render_export_section(self, items_df: pd.DataFrame, summary_df: pd.DataFrame, document_data: Dict):
        """Renderiza seção de exportação"""
        st.markdown("---")
        st.markdown('<h2 class="sub-header">💾 Exportação de Dados</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV completo
            if not items_df.empty:
                csv_data = items_df.to_csv(index=False, encoding='utf-8-sig', sep=';')
                st.download_button(
                    label="📥 Baixar CSV (Itens)",
                    data=csv_data,
                    file_name="app2_itens_completo.csv",
                    mime="text/csv",
                    help="Exportar todos os itens em formato CSV"
                )
        
        with col2:
            # Excel com múltiplas abas
            if not items_df.empty:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    items_df.to_excel(writer, sheet_name='Itens', index=False)
                    
                    if not summary_df.empty:
                        summary_df.to_excel(writer, sheet_name='Resumo', index=False)
                    
                    # Adicionar outras abas se disponíveis
                    if document_data.get('cabecalho'):
                        pd.DataFrame([document_data['cabecalho']]).to_excel(
                            writer, sheet_name='Cabeçalho', index=False
                        )
                
                st.download_button(
                    label="📊 Baixar Excel",
                    data=output.getvalue(),
                    file_name="app2_analise_completa.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Exportar dados em Excel com múltiplas abas"
                )
        
        with col3:
            # JSON estruturado
            json_data = json.dumps(document_data, default=str, indent=2, ensure_ascii=False)
            st.download_button(
                label="📋 Baixar JSON",
                data=json_data,
                file_name="app2_documento_completo.json",
                mime="application/json",
                help="Exportar dados completos em formato JSON estruturado"
            )


def main():
    """Função principal"""
    try:
        # Inicializar e executar o dashboard
        dashboard = APP2Dashboard()
        dashboard.run()
        
    except Exception as e:
        st.error(f"❌ Erro crítico no sistema: {str(e)}")
        
        # Mostrar detalhes do erro em modo debug
        if st.session_state.get('show_debug', False):
            with st.expander("🔍 Detalhes do Erro"):
                st.code(traceback.format_exc())
        
        # Botão para recarregar
        if st.button("🔄 Recarregar Aplicação"):
            st.rerun()


if __name__ == "__main__":
    main()
