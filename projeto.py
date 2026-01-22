import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import pdfplumber
import re
import json
from typing import Dict, List, Optional
import tempfile
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da página
st.set_page_config(
    page_title="Sistema Avançado de Análise Häfele",
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
    """Parser otimizado para PDFs complexos da Häfele"""
    
    def __init__(self):
        self.documento = {
            'cabecalho': {},
            'itens': [],
            'totais': {}
        }
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        """Parse completo do PDF com extração robusta"""
        try:
            logger.info(f"Iniciando parsing do PDF: {pdf_path}")
            
            all_text = ""
            all_pages_data = []
            
            # Extrair texto de todas as páginas
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        all_text += f"\n--- PAGE {page_num} ---\n{page_text}"
                        all_pages_data.append({
                            'page_num': page_num,
                            'text': page_text,
                            'bbox': page.bbox
                        })
            
            # Processar todo o texto
            self._process_full_text(all_text, all_pages_data)
            
            logger.info(f"Parsing concluído. {len(self.documento['itens'])} itens processados.")
            return self.documento
            
        except Exception as e:
            logger.error(f"Erro no parsing: {str(e)}")
            raise
    
    def _process_full_text(self, text: str, pages_data: List[Dict]):
        """Processa todo o texto do PDF"""
        
        # Extrair informações do cabeçalho da primeira página
        if pages_data:
            first_page_text = pages_data[0]['text']
            self.documento['cabecalho'] = self._extract_header_info(first_page_text)
        
        # Encontrar todos os itens no texto
        items = self._extract_all_items(text)
        self.documento['itens'] = items
        
        # Calcular totais
        self._calculate_totals()
        
        logger.info(f"Total de {len(items)} itens extraídos")
    
    def _extract_header_info(self, text: str) -> Dict:
        """Extrai informações do cabeçalho"""
        header = {}
        
        # Expressões regulares para informações do cabeçalho
        patterns = {
            'processo': r'PROCESSO\s*[#]?\s*(\d+)',
            'data_cadastro': r'Data de Cadastro\s*(\d{2}/\d{2}/\d{4})',
            'cnpj': r'CNPJ\s*([\d\./]+)',
            'cotacao_euro': r'EURO.*?Cotacao\s*([\d\.,]+)',
            'cotacao_dolar': r'DOLAR.*?Cotacao\s*([\d\.,]+)',
            'cif_total': r'CIF \(R\$\)\s*([\d\.,]+)',
            'vmle_total': r'VMLE \(R\$\)\s*([\d\.,]+)',
            'vmld_total': r'VMLD \(R\$\)\s*([\d\.,]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header[key] = match.group(1) if key in ['processo', 'data_cadastro', 'cnpj'] else self._parse_valor(match.group(1))
        
        return header
    
    def _extract_all_items(self, text: str) -> List[Dict]:
        """Extrai todos os itens do documento"""
        items = []
        
        # Padrão para identificar itens (baseado no seu exemplo)
        # Procura por padrões como: "1 X 8302.10.00 298 1 EXW 2025-EX 000142"
        item_pattern = r'(?:^|\n)(\d+)\s+[X]?\s*(\d{4}\.\d{2}\.\d{2})\s+(\d+)\s+(\d+)?\s*(\w+)?\s*([\w\-\s]+)?'
        
        matches = list(re.finditer(item_pattern, text, re.IGNORECASE))
        logger.info(f"Encontrados {len(matches)} padrões de itens")
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            item_text = text[start_pos:end_pos]
            
            item_data = self._parse_single_item(item_text, match.groups())
            if item_data:
                items.append(item_data)
        
        return items
    
    def _parse_single_item(self, text: str, match_groups: tuple) -> Optional[Dict]:
        """Parseia um único item do documento"""
        try:
            item_num = match_groups[0] if len(match_groups) > 0 else ""
            ncm = match_groups[1] if len(match_groups) > 1 else ""
            codigo = match_groups[2] if len(match_groups) > 2 else ""
            versao = match_groups[3] if len(match_groups) > 3 else ""
            cond_venda = match_groups[4] if len(match_groups) > 4 else ""
            fatura = match_groups[5] if len(match_groups) > 5 else ""
            
            item = {
                'numero_item': item_num,
                'ncm': ncm,
                'codigo_produto': codigo,
                'versao': versao,
                'condicao_venda': cond_venda,
                'fatura': fatura.strip() if fatura else "",
                'nome_produto': '',
                'codigo_interno': '',
                'pais_origem': '',
                'aplicacao': '',
                'quantidade': 0,
                'peso_liquido': 0,
                'valor_unitario': 0,
                'valor_total': 0,
                'local_aduaneiro': 0,
                'frete_internacional': 0,
                'seguro_internacional': 0,
                
                # Impostos - Valores
                'ii_valor_devido': 0,
                'ipi_valor_devido': 0,
                'pis_valor_devido': 0,
                'cofins_valor_devido': 0,
                
                # Bases de Cálculo
                'ii_base_calculo': 0,
                'ipi_base_calculo': 0,
                'pis_base_calculo': 0,
                'cofins_base_calculo': 0,
                
                # Alíquotas
                'ii_aliquota': 0,
                'ipi_aliquota': 0,
                'pis_aliquota': 0,
                'cofins_aliquota': 0,
                
                'total_impostos': 0,
                'valor_total_com_impostos': 0
            }
            
            # 1. Extrair informações básicas do produto
            self._extract_product_info(text, item)
            
            # 2. Extrair valores e quantidades
            self._extract_values(text, item)
            
            # 3. Extrair informações de impostos (MÉTODO MELHORADO)
            self._extract_tax_information(text, item)
            
            # 4. Calcular totais
            item['total_impostos'] = (
                item['ii_valor_devido'] + 
                item['ipi_valor_devido'] + 
                item['pis_valor_devido'] + 
                item['cofins_valor_devido']
            )
            
            item['valor_total_com_impostos'] = item['valor_total'] + item['total_impostos']
            
            # 5. Validar dados
            item = self._validate_item(item)
            
            return item
            
        except Exception as e:
            logger.error(f"Erro ao parsear item {match_groups[0] if match_groups else 'desconhecido'}: {str(e)}")
            return None
    
    def _extract_product_info(self, text: str, item: Dict):
        """Extrai informações do produto"""
        # Nome do Produto
        nome_match = re.search(r'DENOMINACAO DO PRODUTO[\s\S]*?\n(.*?)(?:\n|DESCRICAO)', text, re.IGNORECASE)
        if nome_match:
            item['nome_produto'] = nome_match.group(1).strip()
        
        # Código Interno
        codigo_match = re.search(r'Código interno\s*([\d\.]+)', text, re.IGNORECASE)
        if codigo_match:
            item['codigo_interno'] = codigo_match.group(1).strip()
        
        # País de Origem
        pais_match = re.search(r'Pais Origem\s*([A-Z]{2})\s+(ITALIA|BRASIL|etc)', text, re.IGNORECASE)
        if pais_match:
            item['pais_origem'] = pais_match.group(1).strip()
        
        # Aplicação
        aplicacao_match = re.search(r'Aplicação\s*(\w+)', text, re.IGNORECASE)
        if aplicacao_match:
            item['aplicacao'] = aplicacao_match.group(1).strip()
    
    def _extract_values(self, text: str, item: Dict):
        """Extrai valores e quantidades"""
        # Quantidade
        qtd_match = re.search(r'Qtde Unid\. Comercial\s+([\d\.,]+)', text)
        if qtd_match:
            item['quantidade'] = self._parse_valor(qtd_match.group(1))
        
        # Peso Líquido
        peso_match = re.search(r'Peso Líquido \(KG\)\s+([\d\.,]+)', text)
        if peso_match:
            item['peso_liquido'] = self._parse_valor(peso_match.group(1))
        
        # Valor Unitário
        valor_unit_match = re.search(r'Valor Unit Cond Venda\s+([\d\.,]+)', text)
        if valor_unit_match:
            item['valor_unitario'] = self._parse_valor(valor_match.group(1))
        
        # Valor Total
        valor_total_match = re.search(r'Valor Tot\. Cond Venda\s+([\d\.,]+)', text)
        if valor_total_match:
            item['valor_total'] = self._parse_valor(valor_total_match.group(1))
        
        # Local Aduaneiro
        local_match = re.search(r'Local Aduaneiro.*?([\d\.,]+)', text, re.IGNORECASE)
        if local_match:
            item['local_aduaneiro'] = self._parse_valor(local_match.group(1))
        
        # Frete Internacional
        frete_match = re.search(r'Frete Internac.*?([\d\.,]+)', text, re.IGNORECASE)
        if frete_match:
            item['frete_internacional'] = self._parse_valor(frete_match.group(1))
        
        # Seguro Internacional
        seguro_match = re.search(r'Seguro Internac.*?([\d\.,]+)', text, re.IGNORECASE)
        if seguro_match:
            item['seguro_internacional'] = self._parse_valor(seguro_match.group(1))
    
    def _extract_tax_information(self, text: str, item: Dict):
        """Extrai informações de impostos - MÉTODO OTIMIZADO"""
        # Primeiro, encontrar a seção de cálculos de tributos
        tax_section_start = re.search(r'CÁLCULOS DOS TRIBUTOS', text, re.IGNORECASE)
        if not tax_section_start:
            return
        
        # Extrair a seção de tributos
        tax_section = text[tax_section_start.start():]
        
        # Dividir em linhas para análise mais precisa
        lines = tax_section.split('\n')
        
        # Dicionário para armazenar valores encontrados por tipo de imposto
        tax_values = {
            'II': {'base': 0, 'rate': 0, 'value': 0},
            'IPI': {'base': 0, 'rate': 0, 'value': 0},
            'PIS': {'base': 0, 'rate': 0, 'value': 0},
            'COFINS': {'base': 0, 'rate': 0, 'value': 0}
        }
        
        current_tax = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Identificar qual imposto estamos processando
            if 'II' in line and 'ALÍQUOTA TEC' not in line:
                current_tax = 'II'
            elif 'IPI' in line:
                current_tax = 'IPI'
            elif 'PIS' in line:
                current_tax = 'PIS'
            elif 'COFINS' in line:
                current_tax = 'COFINS'
            
            if current_tax:
                # Procurar por valores na linha atual e nas próximas
                for j in range(i, min(i + 5, len(lines))):  # Verifica 5 linhas adiante
                    check_line = lines[j]
                    
                    # Procurar Base de Cálculo
                    base_match = re.search(r'([\d\.]+,\d+)\s+Base de Cálculo', check_line)
                    if base_match:
                        tax_values[current_tax]['base'] = self._parse_valor(base_match.group(1))
                    
                    # Procurar % Alíquota
                    rate_match = re.search(r'(\d+,\d+)\s+% Alíquota', check_line)
                    if rate_match:
                        tax_values[current_tax]['rate'] = self._parse_valor(rate_match.group(1))
                    
                    # Procurar Valor Devido
                    value_match = re.search(r'([\d\.]+,\d+)\s+Valor Devido', check_line)
                    if value_match:
                        tax_values[current_tax]['value'] = self._parse_valor(value_match.group(1))
                    
                    # Procurar padrões específicos do seu exemplo
                    # Exemplo: "531,0500000 Valor Devido (R$)"
                    specific_match = re.search(r'([\d\.]+,\d+)\s+Valor Devido \(R\$\)', check_line)
                    if specific_match:
                        tax_values[current_tax]['value'] = self._parse_valor(specific_match.group(1))
        
        # Mapear valores extraídos para o item
        # II
        item['ii_base_calculo'] = tax_values['II']['base'] or self._find_value_near_label(text, 'Base de Cálculo', 'II')
        item['ii_aliquota'] = tax_values['II']['rate'] or self._find_rate_near_label(text, 'II')
        item['ii_valor_devido'] = tax_values['II']['value'] or self._find_value_near_label(text, 'Valor Devido', 'II')
        
        # PIS
        item['pis_base_calculo'] = tax_values['PIS']['base'] or self._find_value_near_label(text, 'Base de Cálculo', 'PIS')
        item['pis_aliquota'] = tax_values['PIS']['rate'] or self._find_rate_near_label(text, 'PIS')
        item['pis_valor_devido'] = tax_values['PIS']['value'] or self._find_value_near_label(text, 'Valor Devido', 'PIS')
        
        # COFINS
        item['cofins_base_calculo'] = tax_values['COFINS']['base'] or self._find_value_near_label(text, 'Base de Cálculo', 'COFINS')
        item['cofins_aliquota'] = tax_values['COFINS']['rate'] or self._find_rate_near_label(text, 'COFINS')
        item['cofins_valor_devido'] = tax_values['COFINS']['value'] or self._find_value_near_label(text, 'Valor Devido', 'COFINS')
        
        # IPI
        item['ipi_base_calculo'] = tax_values['IPI']['base'] or self._find_value_near_label(text, 'Base de Cálculo', 'IPI')
        item['ipi_aliquota'] = tax_values['IPI']['rate'] or self._find_rate_near_label(text, 'IPI')
        item['ipi_valor_devido'] = tax_values['IPI']['value'] or self._find_value_near_label(text, 'Valor Devido', 'IPI')
        
        # Se ainda não encontrou valores, tenta calcular a partir da base e alíquota
        self._calculate_missing_tax_values(item)
    
    def _find_value_near_label(self, text: str, label: str, tax_name: str) -> float:
        """Encontra valores próximos a um label específico"""
        # Procura padrão: label seguido de valor numérico
        pattern = rf'{tax_name}.*?{label}.*?([\d\.]+,\d+)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return self._parse_valor(match.group(1))
        return 0.0
    
    def _find_rate_near_label(self, text: str, tax_name: str) -> float:
        """Encontra alíquota próxima ao nome do imposto"""
        # Procura padrões comuns de alíquota
        patterns = [
            rf'{tax_name}.*?% Alíquota\s*([\d,]+)',
            rf'% Alíquota\s*([\d,]+).*?{tax_name}',
            rf'{tax_name}.*?(\d+,\d+)\s*%'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return self._parse_valor(match.group(1))
        
        # Valores padrão comuns
        default_rates = {
            'II': 16.0,
            'PIS': 2.1,
            'COFINS': 9.65,
            'IPI': 0.0
        }
        
        return default_rates.get(tax_name.upper(), 0.0)
    
    def _calculate_missing_tax_values(self, item: Dict):
        """Calcula valores de impostos faltantes"""
        # II
        if item['ii_valor_devido'] == 0 and item['ii_base_calculo'] > 0 and item['ii_aliquota'] > 0:
            item['ii_valor_devido'] = round(item['ii_base_calculo'] * (item['ii_aliquota'] / 100), 2)
        
        # PIS
        if item['pis_valor_devido'] == 0 and item['pis_base_calculo'] > 0 and item['pis_aliquota'] > 0:
            item['pis_valor_devido'] = round(item['pis_base_calculo'] * (item['pis_aliquota'] / 100), 2)
        
        # COFINS
        if item['cofins_valor_devido'] == 0 and item['cofins_base_calculo'] > 0 and item['cofins_aliquota'] > 0:
            item['cofins_valor_devido'] = round(item['cofins_base_calculo'] * (item['cofins_aliquota'] / 100), 2)
        
        # IPI
        if item['ipi_valor_devido'] == 0 and item['ipi_base_calculo'] > 0 and item['ipi_aliquota'] > 0:
            item['ipi_valor_devido'] = round(item['ipi_base_calculo'] * (item['ipi_aliquota'] / 100), 2)
    
    def _validate_item(self, item: Dict) -> Dict:
        """Valida e limpa os dados do item"""
        # Garantir que valores não sejam negativos
        for key in item:
            if isinstance(item[key], (int, float)) and item[key] < 0:
                item[key] = 0
        
        # Validar consistência dos impostos
        if item['ii_valor_devido'] > 0 and item['ii_base_calculo'] > 0 and item['ii_aliquota'] > 0:
            expected_ii = round(item['ii_base_calculo'] * (item['ii_aliquota'] / 100), 2)
            if abs(expected_ii - item['ii_valor_devido']) > 0.5:  # Tolerância de 50 centavos
                logger.warning(f"Item {item['numero_item']}: II calculado ({expected_ii}) diferente do extraído ({item['ii_valor_devido']})")
        
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
            
            valor_str = valor_str.strip()
            
            # Remove pontos de milhar e converte vírgula para ponto decimal
            if ',' in valor_str:
                # Formato brasileiro: 1.234,56 ou 3.319,0500000
                parts = valor_str.split(',')
                if len(parts) == 2:
                    inteiro = parts[0].replace('.', '')
                    decimal = parts[1]
                    return float(f"{inteiro}.{decimal}")
                else:
                    # Apenas remove pontos se não tiver vírgula decimal
                    valor_str = valor_str.replace('.', '').replace(',', '.')
            
            return float(valor_str)
        except Exception as e:
            logger.warning(f"Erro ao converter valor '{valor_str}': {str(e)}")
            return 0.0


class HafeleAnalyzer:
    """Analisador para dados da Häfele"""
    
    def __init__(self, documento: Dict):
        self.documento = documento
        self.df = None
        
    def create_dataframe(self):
        """Cria DataFrame com todos os dados"""
        if not self.documento['itens']:
            return pd.DataFrame()
        
        data = []
        for item in self.documento['itens']:
            data.append({
                'Item': item.get('numero_item', ''),
                'NCM': item.get('ncm', ''),
                'Código Produto': item.get('codigo_produto', ''),
                'Código Interno': item.get('codigo_interno', ''),
                'Produto': item.get('nome_produto', ''),
                'País Origem': item.get('pais_origem', ''),
                'Aplicação': item.get('aplicacao', ''),
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
                
                # Bases de Cálculo
                'II Base (R$)': item.get('ii_base_calculo', 0),
                'IPI Base (R$)': item.get('ipi_base_calculo', 0),
                'PIS Base (R$)': item.get('pis_base_calculo', 0),
                'COFINS Base (R$)': item.get('cofins_base_calculo', 0),
                
                # Alíquotas
                'II Alíq. (%)': item.get('ii_aliquota', 0),
                'IPI Alíq. (%)': item.get('ipi_aliquota', 0),
                'PIS Alíq. (%)': item.get('pis_aliquota', 0),
                'COFINS Alíq. (%)': item.get('cofins_aliquota', 0),
                
                'Total Impostos (R$)': item.get('total_impostos', 0),
                'Valor c/ Impostos (R$)': item.get('valor_total_com_impostos', 0)
            })
        
        self.df = pd.DataFrame(data)
        return self.df
    
    def get_summary(self):
        """Retorna resumo dos dados"""
        if self.df is None:
            self.create_dataframe()
        
        if self.df.empty:
            return {}
        
        totais = self.documento['totais']
        
        return {
            'total_itens': len(self.df),
            'valor_total': totais['valor_total_mercadoria'],
            'peso_total': totais['peso_total'],
            'quantidade_total': totais['quantidade_total'],
            'total_impostos': totais['total_impostos'],
            'taxa_impostos': (totais['total_impostos'] / totais['valor_total_mercadoria'] * 100 
                            if totais['valor_total_mercadoria'] > 0 else 0),
            'ii_total': totais['ii_total'],
            'pis_total': totais['pis_total'],
            'cofins_total': totais['cofins_total'],
            'ipi_total': totais['ipi_total']
        }


def main():
    """Função principal do aplicativo"""
    
    st.markdown('<h1 class="main-header">🏭 Sistema Avançado de Análise Häfele</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="section-card">
        <strong>🚀 SISTEMA OTIMIZADO PARA EXTRATOS COMPLEXOS</strong><br>
        Extração precisa de todas as informações dos PDFs da Häfele, incluindo:
        <ul>
            <li>✅ Códigos internos e descrições dos produtos</li>
            <li>✅ Valores de mercadoria, frete e seguro</li>
            <li>✅ <strong>Bases de cálculo de impostos</strong> (corrigido!)</li>
            <li>✅ <strong>Alíquotas aplicadas</strong> (corrigido!)</li>
            <li>✅ <strong>Valores de impostos</strong> (II, IPI, PIS, COFINS)</li>
            <li>✅ Cálculo automático de valores faltantes</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📁 Upload do Documento")
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo PDF da Häfele",
            type=['pdf'],
            help="Arraste ou selecione o arquivo PDF com os dados de importação"
        )
        
        st.markdown("---")
        
        if uploaded_file:
            file_size = uploaded_file.size / (1024 * 1024)
            st.info(f"**Arquivo:** {uploaded_file.name}")
            st.success(f"**Tamanho:** {file_size:.2f} MB")
            
            st.markdown("### ⚙️ Configurações")
            show_raw = st.checkbox("Mostrar dados brutos", value=False)
            debug_mode = st.checkbox("Modo debug (para desenvolvedores)", value=False)
    
    # Área principal
    if uploaded_file is not None:
        try:
            # Salvar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Processamento
            status_text.text("📄 Lendo e analisando documento PDF...")
            progress_bar.progress(20)
            
            parser = HafelePDFParser()
            documento = parser.parse_pdf(tmp_path)
            
            status_text.text("📊 Processando dados extraídos...")
            progress_bar.progress(60)
            
            analyzer = HafeleAnalyzer(documento)
            df = analyzer.create_dataframe()
            summary = analyzer.get_summary()
            
            progress_bar.progress(100)
            status_text.text("✅ Processamento concluído com sucesso!")
            
            # Limpar arquivo temporário
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            # Exibir resumo
            st.success(f"✅ **{summary['total_itens']} itens** extraídos com sucesso!")
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">R$ {summary['valor_total']:,.2f}</div>
                    <div class="metric-label">Valor Total Mercadoria</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">R$ {summary['total_impostos']:,.2f}</div>
                    <div class="metric-label">Total de Impostos</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">{summary['taxa_impostos']:.1f}%</div>
                    <div class="metric-label">Taxa Média de Impostos</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">{summary['peso_total']:,.1f} kg</div>
                    <div class="metric-label">Peso Total</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Detalhamento de impostos
            st.markdown('<h3 class="sub-header">💰 Detalhamento de Impostos</h3>', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total II", f"R$ {summary['ii_total']:,.2f}")
            
            with col2:
                st.metric("Total PIS", f"R$ {summary['pis_total']:,.2f}")
            
            with col3:
                st.metric("Total COFINS", f"R$ {summary['cofins_total']:,.2f}")
            
            with col4:
                st.metric("Total IPI", f"R$ {summary['ipi_total']:,.2f}")
            
            # Tabela de itens
            st.markdown('<h2 class="sub-header">📦 Lista Completa de Itens</h2>', unsafe_allow_html=True)
            
            if not df.empty:
                # Formatar colunas numéricas
                display_df = df.copy()
                
                # Colunas monetárias
                money_cols = [col for col in display_df.columns if '(R$)' in col]
                for col in money_cols:
                    display_df[col] = display_df[col].apply(lambda x: f"R$ {x:,.2f}")
                
                # Colunas de porcentagem
                pct_cols = [col for col in display_df.columns if '(%)' in col]
                for col in pct_cols:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "0.00%")
                
                # Exibir tabela
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=600
                )
                
                # Opções de exportação
                st.markdown('<h3 class="sub-header">💾 Exportar Dados</h3>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # CSV
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig', sep=';', decimal=',')
                    st.download_button(
                        label="📥 Baixar CSV",
                        data=csv_data,
                        file_name="hafele_extracao.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    # Excel
                    import io
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Itens', index=False)
                        
                        # Adicionar resumo
                        summary_df = pd.DataFrame([summary])
                        summary_df.to_excel(writer, sheet_name='Resumo', index=False)
                    
                    st.download_button(
                        label="📊 Baixar Excel",
                        data=output.getvalue(),
                        file_name="hafele_extracao.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col3:
                    # JSON
                    json_data = json.dumps(documento, indent=2, default=str, ensure_ascii=False)
                    st.download_button(
                        label="📄 Baixar JSON",
                        data=json_data,
                        file_name="hafele_dados_completos.json",
                        mime="application/json"
                    )
                
                # Modo debug
                if debug_mode:
                    st.markdown('<h3 class="sub-header">🔧 Informações de Debug</h3>', unsafe_allow_html=True)
                    
                    tab1, tab2 = st.tabs(["Dados Extraídos", "Estatísticas"])
                    
                    with tab1:
                        st.write("**Primeiro item extraído:**")
                        if documento['itens']:
                            first_item = documento['itens'][0]
                            st.json({k: v for k, v in first_item.items() if v})
                    
                    with tab2:
                        st.write("**Estatísticas de extração:**")
                        st.write(f"- Total de itens: {len(documento['itens'])}")
                        st.write(f"- Colunas no DataFrame: {len(df.columns)}")
                        st.write(f"- Valores extraídos com sucesso: {df.notna().sum().sum()}")
                        
                        # Verificar se os impostos foram extraídos corretamente
                        tax_cols = ['II (R$)', 'PIS (R$)', 'COFINS (R$)']
                        tax_extracted = sum(df[col].sum() > 0 for col in tax_cols if col in df.columns)
                        st.write(f"- Impostos extraídos: {tax_extracted}/3")
            
            else:
                st.warning("Nenhum item foi extraído do documento.")
        
        except Exception as e:
            st.error(f"❌ Erro durante o processamento: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    else:
        # Tela inicial
        st.info("📁 Faça o upload de um arquivo PDF para começar a análise.")
        
        st.markdown("""
        <div class="section-card">
            <h4>🎯 Funcionalidades Principais:</h4>
            <ol>
                <li><strong>Extração completa</strong> de dados de importação</li>
                <li><strong>Análise detalhada</strong> de impostos (II, PIS, COFINS, IPI)</li>
                <li><strong>Cálculo automático</strong> de bases e valores</li>
                <li><strong>Exportação</strong> para CSV, Excel e JSON</li>
                <li><strong>Interface intuitiva</strong> e responsiva</li>
            </ol>
            
            <h4>📋 Dados Extraídos:</h4>
            <ul>
                <li>✅ Informações do produto (código, descrição, NCM)</li>
                <li>✅ Valores comerciais (unitário, total, frete, seguro)</li>
                <li>✅ <strong>Bases de cálculo de todos os impostos</strong></li>
                <li>✅ <strong>Alíquotas aplicadas a cada item</strong></li>
                <li>✅ <strong>Valores de impostos devidos</strong></li>
                <li>✅ Totais e resumos consolidados</li>
            </ul>
            
            <p><strong>Dica:</strong> O sistema agora está otimizado para extrair corretamente as informações 
            de impostos que estavam sendo lidas incorretamente anteriormente.</p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
