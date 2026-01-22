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
from typing import Dict, List, Tuple, Optional, Any
import tempfile
import os
from dataclasses import dataclass
from collections import defaultdict
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da página
st.set_page_config(
    page_title="Sistema Completo de Análise Häfele",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        color: #1E3A8A;
        font-weight: bold;
        margin-bottom: 1rem;
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
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
        border: 1px solid #E5E7EB;
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
</style>
""", unsafe_allow_html=True)

class HafelePDFParser:
    """Parser robusto para PDFs da Häfele"""
    
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
        """Processa todo o texto do PDF - versão melhorada"""
        
        # Dividir por páginas (se houver marcadores de página)
        pages = text.split('\x0c') if '\x0c' in text else [text]
        
        logger.info(f"Encontradas {len(pages)} páginas no texto")
        
        # Processar primeira página para informações gerais
        if pages:
            self.documento['cabecalho'] = self._extract_header_info(pages[0])
        
        # Processar todas as páginas para itens
        all_items = []
        for page_num, page_text in enumerate(pages, 1):
            logger.info(f"Extraindo itens da página {page_num}")
            items = self._find_all_items(page_text)
            all_items.extend(items)
        
        self.documento['itens'] = all_items
        
        # Calcular totais
        self._calculate_totals()
        
        logger.info(f"Total de {len(all_items)} itens processados")
    
    def _extract_header_info(self, text: str) -> Dict:
        """Extrai informações do cabeçalho da primeira página"""
        header = {}
        
        # Extrair número do processo
        processo_match = re.search(r'PROCESSO\s*[#]?(\d+)', text, re.IGNORECASE)
        if processo_match:
            header['processo'] = processo_match.group(1)
        
        # Extrair datas importantes
        data_match = re.search(r'Data de Cadastro\s*(\d{2}/\d{2}/\d{4})', text)
        if data_match:
            header['data_cadastro'] = data_match.group(1)
        
        # Extrair CNPJ
        cnpj_match = re.search(r'CNPJ\s*([\d\./]+)', text)
        if cnpj_match:
            header['cnpj'] = cnpj_match.group(1)
        
        # Extrair cotações
        euro_match = re.search(r'EURO.*?Cotacao\s*([\d\.,]+)', text, re.IGNORECASE)
        if euro_match:
            header['cotacao_euro'] = self._parse_valor(euro_match.group(1))
        
        dolar_match = re.search(r'DOLAR.*?Cotacao\s*([\d\.,]+)', text, re.IGNORECASE)
        if dolar_match:
            header['cotacao_dolar'] = self._parse_valor(dolar_match.group(1))
        
        # Extrair totais da primeira página
        cif_match = re.search(r'CIF \(R\$\)\s*([\d\.,]+)', text)
        if cif_match:
            header['cif_total'] = self._parse_valor(cif_match.group(1))
        
        # Extrair VMLE e VMLD
        vmle_match = re.search(r'VMLE \(R\$\)\s*([\d\.,]+)', text)
        if vmle_match:
            header['vmle_total'] = self._parse_valor(vmle_match.group(1))
        
        vmld_match = re.search(r'VMLD \(R\$\)\s*([\d\.,]+)', text)
        if vmld_match:
            header['vmld_total'] = self._parse_valor(vmld_match.group(1))
        
        # Extrair impostos totais
        ii_total_match = re.search(r'II\s+([\d\.,]+)', text)
        if ii_total_match:
            header['ii_total'] = self._parse_valor(ii_total_match.group(1))
        
        pis_total_match = re.search(r'PIS\s+([\d\.,]+)', text)
        if pis_total_match:
            header['pis_total'] = self._parse_valor(pis_total_match.group(1))
        
        cofins_total_match = re.search(r'COFINS\s+([\d\.,]+)', text)
        if cofins_total_match:
            header['cofins_total'] = self._parse_valor(cofins_total_match.group(1))
        
        return header
    
    def _find_all_items(self, text: str) -> List[Dict]:
        """Encontra todos os itens no texto - versão melhorada"""
        items = []
        
        # Padrão melhorado para encontrar itens
        # Procura por padrões como "1 X 8302.10.00 298 1 EXW"
        item_pattern = r'(?:^|\n)(\d+)\s+X\s+(\d{4}\.\d{2}\.\d{2})\s+(\d+)\s+(\d+)\s+(\w+)\s+([\w\-\s]+)'
        
        # Também procura por padrões alternativos (sem o "X")
        alt_pattern = r'(?:^|\n)(\d+)\s+(\d{4}\.\d{2}\.\d{2})\s+(\d+)\s+(\d+)\s+(\w+)\s+([\w\-\s]+)'
        
        # Usar ambos os padrões
        matches = list(re.finditer(item_pattern, text, re.IGNORECASE))
        if not matches:
            matches = list(re.finditer(alt_pattern, text, re.IGNORECASE))
        
        logger.info(f"Encontrados {len(matches)} padrões de itens")
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            item_text = text[start_pos:end_pos]
            
            # Extrair dados baseado no padrão encontrado
            if len(match.groups()) >= 6:
                # Padrão completo
                item_data = self._parse_item(
                    item_text, 
                    match.group(1),  # número do item
                    match.group(2),  # NCM
                    match.group(3),  # código do produto
                    match.group(4),  # versão
                    match.group(5),  # condição de venda
                    match.group(6).strip()  # fatura
                )
            else:
                # Padrão alternativo
                item_data = self._parse_item_simple(
                    item_text,
                    match.group(1),
                    match.group(2),
                    match.group(3)
                )
            
            if item_data:
                items.append(item_data)
        
        return items
    
    def _parse_item(self, text: str, item_num: str, ncm: str, codigo: str, 
                    versao: str = "", cond_venda: str = "", fatura: str = "") -> Optional[Dict]:
        """Parse de um item individual - versão melhorada"""
        try:
            item = {
                'numero_item': item_num,
                'ncm': ncm,
                'codigo_produto': codigo,
                'versao': versao,
                'nome_produto': '',
                'codigo_interno': '',
                'pais_origem': '',
                'aplicacao': '',
                'fatura': fatura,
                'condicao_venda': cond_venda,
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
            nome_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n(.*?)\n(?:DESCRICAO|CÓDIGO|FABRICANTE)', text, re.IGNORECASE | re.DOTALL)
            if nome_match:
                item['nome_produto'] = nome_match.group(1).replace('\n', ' ').strip()
            
            # Código Interno (Limpo)
            codigo_match = re.search(r'Código interno\s*([\d\.]+)', text, re.IGNORECASE)
            if codigo_match:
                item['codigo_interno'] = codigo_match.group(1).strip()
            else:
                # Tenta padrão alternativo
                codigo_alt_match = re.search(r'Código interno\s*(.*?)\s*(?=\n|FABRICANTE|Conhecido)', text, re.IGNORECASE | re.DOTALL)
                if codigo_alt_match:
                    raw_code = codigo_alt_match.group(1)
                    clean_code = raw_code.replace('(PARTNUMBER)', '').replace('Código interno', '').replace('\n', '')
                    item['codigo_interno'] = clean_code.strip()
            
            # Outros campos textuais
            pais_match = re.search(r'Pais Origem\s*([A-Z]{2})\s+', text, re.IGNORECASE)
            if pais_match:
                item['pais_origem'] = pais_match.group(1).strip()
            else:
                pais_alt_match = re.search(r'Pais Origem\s*(.*?)\s*(?=\n|CARACTERIZAÇÃO)', text, re.IGNORECASE)
                if pais_alt_match:
                    item['pais_origem'] = pais_alt_match.group(1).strip()
            
            app_match = re.search(r'Aplicação\s*(.*?)\s*(?=\n|Condição)', text, re.IGNORECASE)
            if app_match:
                item['aplicacao'] = app_match.group(1).strip()

            # --- SEÇÃO 2: VALORES E QUANTIDADES ---

            qtd_match = re.search(r'Qtde Unid\. Comercial\s+([\d\.,]+)', text)
            if qtd_match:
                item['quantidade'] = self._parse_valor(qtd_match.group(1))
            
            peso_match = re.search(r'Peso Líquido \(KG\)\s+([\d\.,]+)', text)
            if peso_match:
                item['peso_liquido'] = self._parse_valor(peso_match.group(1))
            
            valor_unit_match = re.search(r'Valor Unit Cond Venda\s+([\d\.,]+)', text)
            if valor_unit_match:
                item['valor_unitario'] = self._parse_valor(valor_unit_match.group(1))
            
            valor_total_match = re.search(r'Valor Tot\. Cond Venda\s+([\d\.,]+)', text)
            if valor_total_match:
                item['valor_total'] = self._parse_valor(valor_total_match.group(1))
            
            loc_adu_match = re.search(r'Local Aduaneiro \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE)
            if loc_adu_match:
                item['local_aduaneiro'] = self._parse_valor(loc_adu_match.group(1))
            else:
                # Tenta padrão alternativo
                loc_adu_alt_match = re.search(r'Local Aduaneiro.*?([\d\.,]+)', text, re.IGNORECASE)
                if loc_adu_alt_match:
                    item['local_aduaneiro'] = self._parse_valor(loc_adu_alt_match.group(1))

            frete_match = re.search(r'Frete Internac\. \(R\$\)\s+([\d\.,]+)', text)
            if frete_match:
                item['frete_internacional'] = self._parse_valor(frete_match.group(1))
            
            seguro_match = re.search(r'Seguro Internac\. \(R\$\)\s+([\d\.,]+)', text)
            if seguro_match:
                item['seguro_internacional'] = self._parse_valor(seguro_match.group(1))
            
            # --- SEÇÃO 3: IMPOSTOS, BASES E ALÍQUOTAS ---
            item = self._extract_taxes_directly(text, item)
            
            # Validar dados
            item = self._validate_item_data(item)
            
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
    
    def _parse_item_simple(self, text: str, item_num: str, ncm: str, codigo: str) -> Optional[Dict]:
        """Parse de um item simplificado (para padrões alternativos)"""
        return self._parse_item(text, item_num, ncm, codigo, "", "", "")
    
    def _extract_taxes_directly(self, text: str, item: Dict) -> Dict:
        """Extrai impostos, bases e alíquotas diretamente do texto - CORRIGIDO"""
        
        # Padrões específicos para o formato do PDF fornecido
        
        # Para II - Imposto de Importação
        ii_valor_match = re.search(r'II.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if ii_valor_match:
            item['ii_valor_devido'] = self._parse_valor(ii_valor_match.group(1))
        
        # Para IPI - Imposto sobre Produtos Industrializados
        ipi_valor_match = re.search(r'IPI.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if ipi_valor_match:
            item['ipi_valor_devido'] = self._parse_valor(ipi_valor_match.group(1))
        
        # Para PIS
        pis_valor_match = re.search(r'PIS.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if pis_valor_match:
            item['pis_valor_devido'] = self._parse_valor(pis_valor_match.group(1))
        
        # Para COFINS
        cofins_valor_match = re.search(r'COFINS.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if cofins_valor_match:
            item['cofins_valor_devido'] = self._parse_valor(cofins_valor_match.group(1))
        
        # Para Bases de Cálculo
        # II Base
        ii_base_match = re.search(r'II.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if ii_base_match:
            item['ii_base_calculo'] = self._parse_valor(ii_base_match.group(1))
        
        # IPI Base
        ipi_base_match = re.search(r'IPI.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if ipi_base_match:
            item['ipi_base_calculo'] = self._parse_valor(ipi_base_match.group(1))
        
        # PIS Base
        pis_base_match = re.search(r'PIS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if pis_base_match:
            item['pis_base_calculo'] = self._parse_valor(pis_base_match.group(1))
        
        # COFINS Base
        cofins_base_match = re.search(r'COFINS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if cofins_base_match:
            item['cofins_base_calculo'] = self._parse_valor(cofins_base_match.group(1))
        
        # Para Alíquotas
        # II Alíquota
        ii_aliquota_match = re.search(r'II.*?% Alíquota\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if ii_aliquota_match:
            item['ii_aliquota'] = self._parse_valor(ii_aliquota_match.group(1))
        
        # IPI Alíquota
        ipi_aliquota_match = re.search(r'IPI.*?% Alíquota\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if ipi_aliquota_match:
            item['ipi_aliquota'] = self._parse_valor(ipi_aliquota_match.group(1))
        
        # PIS Alíquota
        pis_aliquota_match = re.search(r'PIS.*?% Alíquota\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if pis_aliquota_match:
            item['pis_aliquota'] = self._parse_valor(pis_aliquota_match.group(1))
        
        # COFINS Alíquota
        cofins_aliquota_match = re.search(r'COFINS.*?% Alíquota\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
        if cofins_aliquota_match:
            item['cofins_aliquota'] = self._parse_valor(cofins_aliquota_match.group(1))
        
        # Se não encontrar pelo padrão completo, tenta padrões alternativos
        if item['ii_valor_devido'] == 0:
            # Tenta encontrar valores de impostos na seção de cálculos
            calc_match = re.search(r'CÁLCULOS DOS TRIBUTOS.*?II\s+([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
            if calc_match:
                item['ii_valor_devido'] = self._parse_valor(calc_match.group(1))
        
        if item['pis_valor_devido'] == 0:
            pis_calc_match = re.search(r'CÁLCULOS DOS TRIBUTOS.*?PIS\s+([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
            if pis_calc_match:
                item['pis_valor_devido'] = self._parse_valor(pis_calc_match.group(1))
        
        if item['cofins_valor_devido'] == 0:
            cofins_calc_match = re.search(r'CÁLCULOS DOS TRIBUTOS.*?COFINS\s+([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
            if cofins_calc_match:
                item['cofins_valor_devido'] = self._parse_valor(cofins_calc_match.group(1))
        
        return item
    
    def _validate_item_data(self, item: Dict) -> Dict:
        """Valida e ajusta os dados do item"""
        
        # Verifica se os impostos foram calculados corretamente
        if item['ii_valor_devido'] > 0:
            # Se temos base e alíquota, podemos validar
            if item['ii_base_calculo'] > 0 and item['ii_aliquota'] > 0:
                calculated_ii = item['ii_base_calculo'] * (item['ii_aliquota'] / 100)
                # Permite pequena diferença de arredondamento
                if abs(calculated_ii - item['ii_valor_devido']) > 0.1:
                    logger.warning(f"Diferença no cálculo do II para item {item['numero_item']}: Calculado={calculated_ii:.2f}, Encontrado={item['ii_valor_devido']:.2f}")
        
        # Garante que valores não sejam negativos
        for key in ['valor_total', 'peso_liquido', 'quantidade', 
                   'ii_valor_devido', 'ipi_valor_devido', 'pis_valor_devido', 'cofins_valor_devido']:
            if key in item and item[key] < 0:
                item[key] = 0
        
        # Se o código interno for muito longo, limita
        if 'codigo_interno' in item and len(item['codigo_interno']) > 50:
            item['codigo_interno'] = item['codigo_interno'][:50]
        
        return item
    
    def _calculate_totals(self):
        """Calcula totais do documento"""
        totais = {
            'valor_total_mercadoria': 0,
            'peso_total': 0,
            'quantidade_total': 0,
            'total_impostos': 0,
            'ii_total': 0,
            'ipi_total': 0,
            'pis_total': 0,
            'cofins_total': 0
        }
        
        for item in self.documento['itens']:
            totais['valor_total_mercadoria'] += item.get('valor_total', 0)
            totais['peso_total'] += item.get('peso_liquido', 0)
            totais['quantidade_total'] += item.get('quantidade', 0)
            totais['ii_total'] += item.get('ii_valor_devido', 0)
            totais['ipi_total'] += item.get('ipi_valor_devido', 0)
            totais['pis_total'] += item.get('pis_valor_devido', 0)
            totais['cofins_total'] += item.get('cofins_valor_devido', 0)
            totais['total_impostos'] += item.get('total_impostos', 0)
        
        self.documento['totais'] = totais
    
    def _parse_valor(self, valor_str: str) -> float:
        """Converte string de valor para float"""
        try:
            if not valor_str or valor_str.strip() == '':
                return 0.0
            
            # Remove possíveis espaços
            valor_str = valor_str.strip()
            
            # Verifica se tem vírgula como separador decimal
            if ',' in valor_str and '.' in valor_str:
                # Formato brasileiro: 1.234,56
                valor_str = valor_str.replace('.', '').replace(',', '.')
            elif ',' in valor_str:
                # Formato com vírgula decimal: 1234,56
                valor_str = valor_str.replace(',', '.')
            # Se só tem ponto, já está no formato correto
            
            return float(valor_str)
        except Exception as e:
            logger.warning(f"Erro ao converter valor '{valor_str}': {str(e)}")
            return 0.0

class FinancialAnalyzer:
    """Analisador financeiro"""
    
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
                'Versão': item.get('versao', ''),
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
    
    def get_summary_stats(self):
        """Retorna estatísticas resumidas"""
        if self.itens_df is None:
            self.prepare_dataframe()
        
        stats = {
            'total_itens': len(self.itens_df),
            'valor_total_mercadoria': self.itens_df['Valor Total (R$)'].sum(),
            'total_impostos': self.itens_df['Total Impostos (R$)'].sum(),
            'peso_total': self.itens_df['Peso (kg)'].sum(),
            'quantidade_total': self.itens_df['Quantidade'].sum(),
            'taxa_impostos_media': (self.itens_df['Total Impostos (R$)'].sum() / 
                                   self.itens_df['Valor Total (R$)'].sum() * 100 
                                   if self.itens_df['Valor Total (R$)'].sum() > 0 else 0)
        }
        
        return stats

def main():
    """Função principal"""
    
    st.markdown('<h1 class="main-header">🏭 Sistema de Análise de Extratos Häfele (PRO) - VERSÃO CORRIGIDA</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="section-card">
        <strong>✅ SISTEMA CORRIGIDO</strong><br>
        Agora com extração precisa de:
        <ul>
            <li>Códigos Internos (limpos)</li>
            <li>Local Aduaneiro</li>
            <li>Bases de Cálculo</li>
            <li>Alíquotas</li>
            <li>Valores de Impostos</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### 📁 Upload do Documento")
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo PDF",
            type=['pdf'],
            help="Documento PDF no formato padrão Häfele"
        )
        
        st.markdown("---")
        
        if uploaded_file:
            file_size = uploaded_file.size / (1024 * 1024)
            st.info(f"📄 Arquivo: {uploaded_file.name}")
            st.success(f"📊 Tamanho: {file_size:.2f} MB")
            
            st.markdown("### ⚙️ Opções")
            show_raw_data = st.checkbox("Mostrar dados brutos extraídos", value=False)
            show_debug = st.checkbox("Mostrar informações de debug", value=False)
    
    if uploaded_file is not None:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("📄 Analisando documento PDF...")
            progress_bar.progress(20)
            
            parser = HafelePDFParser()
            
            status_text.text("🔍 Extraindo informações do cabeçalho...")
            progress_bar.progress(40)
            
            documento = parser.parse_pdf(tmp_path)
            
            status_text.text("📊 Processando dados...")
            progress_bar.progress(70)
            
            analyser = FinancialAnalyzer(documento)
            df = analyser.prepare_dataframe()
            stats = analyser.get_summary_stats()
            
            progress_bar.progress(100)
            status_text.text("✅ Processamento concluído!")
            
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            # Exibir informações do cabeçalho
            if documento.get('cabecalho'):
                st.markdown('<h2 class="sub-header">📋 Informações do Processo</h2>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'processo' in documento['cabecalho']:
                        st.metric("Número do Processo", documento['cabecalho']['processo'])
                    if 'data_cadastro' in documento['cabecalho']:
                        st.metric("Data de Cadastro", documento['cabecalho']['data_cadastro'])
                
                with col2:
                    if 'cnpj' in documento['cabecalho']:
                        st.metric("CNPJ", documento['cabecalho']['cnpj'])
                    if 'cotacao_euro' in documento['cabecalho']:
                        st.metric("Cotação Euro", f"R$ {documento['cabecalho']['cotacao_euro']:.4f}")
                
                with col3:
                    if 'cotacao_dolar' in documento['cabecalho']:
                        st.metric("Cotação Dólar", f"R$ {documento['cabecalho']['cotacao_dolar']:.4f}")
                    if 'cif_total' in documento['cabecalho']:
                        st.metric("CIF Total", f"R$ {documento['cabecalho']['cif_total']:,.2f}")
            
            st.success(f"✅ **{len(documento['itens'])} itens** extraídos com sucesso!")
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">R$ {stats.get('valor_total_mercadoria', 0):,.2f}</div>
                    <div class="metric-label">Valor Mercadoria</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">R$ {stats.get('total_impostos', 0):,.2f}</div>
                    <div class="metric-label">Total Impostos</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">{stats.get('taxa_impostos_media', 0):.1f}%</div>
                    <div class="metric-label">Taxa de Impostos Média</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">{stats.get('total_itens', 0)}</div>
                    <div class="metric-label">Total de Itens</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Métricas de impostos detalhadas
            st.markdown('<h3 class="sub-header">💰 Detalhamento de Impostos</h3>', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_ii = sum(item.get('ii_valor_devido', 0) for item in documento['itens'])
                st.metric("Total II", f"R$ {total_ii:,.2f}")
            
            with col2:
                total_pis = sum(item.get('pis_valor_devido', 0) for item in documento['itens'])
                st.metric("Total PIS", f"R$ {total_pis:,.2f}")
            
            with col3:
                total_cofins = sum(item.get('cofins_valor_devido', 0) for item in documento['itens'])
                st.metric("Total COFINS", f"R$ {total_cofins:,.2f}")
            
            with col4:
                total_ipi = sum(item.get('ipi_valor_devido', 0) for item in documento['itens'])
                st.metric("Total IPI", f"R$ {total_ipi:,.2f}")
            
            st.markdown('<h2 class="sub-header">📦 Lista de Itens Detalhada</h2>', unsafe_allow_html=True)
            
            # Ordenação das colunas para visualização lógica
            cols_order = [
                'Item', 'Código Interno', 'Produto', 'NCM',
                'Quantidade', 'Peso (kg)', 
                'Valor Total (R$)', 'Local Aduaneiro (R$)', 
                'II Base (R$)', 'II Alíq. (%)', 'II (R$)',
                'IPI Base (R$)', 'IPI Alíq. (%)', 'IPI (R$)',
                'PIS Base (R$)', 'PIS Alíq. (%)', 'PIS (R$)',
                'COFINS Base (R$)', 'COFINS Alíq. (%)', 'COFINS (R$)',
                'Total Impostos (R$)', 'Valor c/ Impostos (R$)'
            ]
            
            display_cols = [c for c in cols_order if c in df.columns]
            remaining_cols = [c for c in df.columns if c not in display_cols]
            final_cols = display_cols + remaining_cols
            
            display_df = df[final_cols].copy()
            
            # Formatação de Moeda
            currency_cols = [col for col in display_df.columns if '(R$)' in col]
            for c in currency_cols:
                display_df[c] = display_df[c].apply(lambda x: f"R$ {x:,.2f}")
            
            # Formatação de Porcentagem
            pct_cols = [col for col in display_df.columns if '(%)' in col]
            for c in pct_cols:
                display_df[c] = display_df[c].apply(lambda x: f"{x:,.2f}%" if pd.notnull(x) else "0.00%")

            # Exibir dataframe
            st.dataframe(
                display_df,
                use_container_width=True,
                height=600
            )
            
            # Seção de debug (opcional)
            if show_debug and st.checkbox("Mostrar informações de parsing"):
                st.markdown('<h3 class="sub-header">🔧 Informações de Parsing</h3>', unsafe_allow_html=True)
                
                tab1, tab2, tab3 = st.tabs(["Dados Brutos", "Estrutura", "Logs"])
                
                with tab1:
                    st.json(documento.get('cabecalho', {}))
                
                with tab2:
                    st.write(f"Total de itens: {len(documento['itens'])}")
                    st.write(f"Colunas no DataFrame: {len(df.columns)}")
                    st.write("Colunas disponíveis:", list(df.columns))
                
                with tab3:
                    if documento['itens']:
                        sample_item = documento['itens'][0]
                        st.write("Exemplo do primeiro item parseado:")
                        st.json({k: v for k, v in sample_item.items() if v})
            
            st.markdown('<h2 class="sub-header">💾 Exportação de Dados</h2>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # CSV completo
                csv_data = df.to_csv(index=False, encoding='utf-8-sig', sep=';', decimal=',')
                st.download_button(
                    label="📥 Baixar CSV (Completo)",
                    data=csv_data,
                    file_name="itens_hafele_pro_completo.csv",
                    mime="text/csv",
                    help="Arquivo CSV com todos os dados extraídos"
                )
            
            with col2:
                # Excel
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Itens', index=False)
                    
                    # Adicionar resumo
                    summary_data = {
                        'Métrica': ['Total Itens', 'Valor Total Mercadoria', 'Total Impostos', 
                                   'Total II', 'Total PIS', 'Total COFINS', 'Total IPI',
                                   'Peso Total', 'Quantidade Total'],
                        'Valor': [stats['total_itens'], stats['valor_total_mercadoria'], 
                                 stats['total_impostos'], total_ii, total_pis, total_cofins, total_ipi,
                                 stats['peso_total'], stats['quantidade_total']]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Resumo', index=False)
                
                st.download_button(
                    label="📊 Baixar Excel",
                    data=output.getvalue(),
                    file_name="itens_hafele_pro_completo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Arquivo Excel com dados completos e resumo"
                )
            
            with col3:
                # JSON para análise
                json_data = json.dumps(documento, indent=2, default=str, ensure_ascii=False)
                st.download_button(
                    label="📄 Baixar JSON",
                    data=json_data,
                    file_name="dados_hafele_completos.json",
                    mime="application/json",
                    help="Dados completos em formato JSON para análise"
                )
        
        except Exception as e:
            st.error(f"❌ Erro no processamento: {str(e)}")
            st.error("Detalhes do erro:", str(e))
            import traceback
            st.code(traceback.format_exc())
    
    else:
        st.info("📁 Por favor, faça o upload de um arquivo PDF para começar a análise.")
        st.markdown("""
        <div class="section-card">
            <h4>📋 Como usar:</h4>
            <ol>
                <li>Clique em <strong>"Browse files"</strong> ou arraste um arquivo PDF</li>
                <li>Aguarde o processamento automático</li>
                <li>Visualize os dados extraídos na tabela</li>
                <li>Baixe os resultados nos formatos desejados</li>
            </ol>
            
            <h4>✅ Dados extraídos:</h4>
            <ul>
                <li>Códigos internos dos produtos</li>
                <li>Valores de mercadoria</li>
                <li>Bases de cálculo de impostos</li>
                <li>Alíquotas aplicadas</li>
                <li>Valores de impostos (II, IPI, PIS, COFINS)</li>
                <li>Informações de frete e seguro</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
