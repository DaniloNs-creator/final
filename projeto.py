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
import io
from dataclasses import dataclass
from collections import defaultdict
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da página
st.set_page_config(
    page_title="Sistema Completo de Análise Häfele - APP2",
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
        text-align: center;
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
    .info-box {
        background-color: #F0F9FF;
        border-left: 4px solid #1E3A8A;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
    }
    .warning-box {
        background-color: #FEF3C7;
        border-left: 4px solid #D97706;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
    }
    .success-box {
        background-color: #D1FAE5;
        border-left: 4px solid #059669;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
    }
    .table-header {
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
        padding: 8px;
    }
    .tax-box {
        background-color: #FEFCE8;
        border: 1px solid #FBBF24;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


class HafelePDFParser:
    """Parser robusto para PDFs da Häfele (Layout APP2.pdf) - VERSÃO CORRIGIDA"""
    
    def __init__(self):
        self.documento = {
            'cabecalho': {},
            'itens': [],
            'totais': {},
            'carga': {},
            'transporte': {},
            'moedas': {},
            'impostos_totais': {}
        }
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        """Parse completo do PDF"""
        try:
            logger.info(f"Iniciando parsing do PDF: {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"PDF com {total_pages} páginas")
                
                # Extrair texto de todas as páginas
                all_text = ""
                for page_num, page in enumerate(pdf.pages, 1):
                    logger.info(f"Processando página {page_num}/{total_pages}")
                    text = page.extract_text()
                    if text:
                        # Adicionar marcador de página para facilitar debugging
                        all_text += f"\n=== PÁGINA {page_num} ===\n{text}\n"
            
            # Processar todo o texto
            self._process_full_text(all_text)
            
            logger.info(f"Parsing concluído. {len(self.documento['itens'])} itens processados.")
            return self.documento
            
        except Exception as e:
            logger.error(f"Erro no parsing: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _process_full_text(self, text: str):
        """Processa todo o texto do PDF"""
        try:
            # Extrair informações do cabeçalho
            self._extract_header_info(text)
            
            # Extrair informações de moedas
            self._extract_currency_info(text)
            
            # Extrair informações de carga
            self._extract_carga_info(text)
            
            # Extrair informações de transporte
            self._extract_transporte_info(text)
            
            # Extrair impostos totais da página 1
            self._extract_total_taxes(text)
            
            # Encontrar e processar todos os itens
            items = self._find_and_parse_items(text)
            self.documento['itens'] = items
            
            # Calcular totais
            self._calculate_totals()
            
            logger.info(f"Processamento completo: {len(items)} itens encontrados")
            
        except Exception as e:
            logger.error(f"Erro no processamento do texto: {str(e)}")
            raise
    
    def _extract_header_info(self, text: str):
        """Extrai informações do cabeçalho"""
        header_info = {}
        
        try:
            # Processo
            processo_match = re.search(r'PROCESSO\s*#(\d+)', text)
            if processo_match:
                header_info['processo'] = processo_match.group(1)
            
            # Importador
            importador_match = re.search(r'IMPORTADOR\s+(.+?)\s+CNPJ', text, re.DOTALL)
            if importador_match:
                header_info['importador'] = importador_match.group(1).replace('\n', ' ').strip()
            
            cnpj_match = re.search(r'CNPJ\s+([\d\.\/\-]+)', text)
            if cnpj_match:
                header_info['cnpj'] = cnpj_match.group(1)
            
            # Identificação
            ident_match = re.search(r'Identificacao\s+(.+?)\s+Data de Cadastro', text)
            if ident_match:
                header_info['identificacao'] = ident_match.group(1).strip()
            
            data_cad_match = re.search(r'Data de Cadastro\s+(\d{2}/\d{2}/\d{4})', text)
            if data_cad_match:
                header_info['data_cadastro'] = data_cad_match.group(1)
            
            # Responsável
            responsavel_match = re.search(r'Responsavel Legal\s+(.+?)(?:\n|$)', text)
            if responsavel_match:
                header_info['responsavel'] = responsavel_match.group(1).strip()
            
            self.documento['cabecalho'] = header_info
            logger.info(f"Cabeçalho extraído: {header_info}")
            
        except Exception as e:
            logger.error(f"Erro ao extrair cabeçalho: {str(e)}")
    
    def _extract_currency_info(self, text: str):
        """Extrai informações de moedas e cotações"""
        moedas_info = {}
        
        try:
            # Data das cotações
            data_match = re.search(r'MOEDAS/COTACOES - \((\d{2}/\d{2}/\d{4})\)', text)
            if data_match:
                moedas_info['data_cotacao'] = data_match.group(1)
            
            # Moeda negociada
            moeda_neg_match = re.search(r'Moeda Negociada\s+\d+\s+-\s+(.+?)\s+Cotacao\s+([\d,\.]+)', text)
            if moeda_neg_match:
                moedas_info['moeda_negociada'] = {
                    'nome': moeda_neg_match.group(1).strip(),
                    'cotacao': self._parse_valor(moeda_neg_match.group(2))
                }
            
            # Cotação do dólar
            dolar_match = re.search(r'Moeda Seguro\s+\d+\s+-\s+DOLAR DOS EUA.*?Cotacao\s+([\d,\.]+)', text, re.DOTALL)
            if dolar_match:
                moedas_info['dolar'] = {
                    'nome': 'DOLAR DOS EUA',
                    'cotacao': self._parse_valor(dolar_match.group(1))
                }
            
            self.documento['moedas'] = moedas_info
            logger.info(f"Moedas extraídas: {moedas_info}")
            
        except Exception as e:
            logger.error(f"Erro ao extrair moedas: {str(e)}")
    
    def _extract_carga_info(self, text: str):
        """Extrai informações da carga"""
        carga_info = {}
        
        try:
            # Via de transporte
            via_match = re.search(r'Via de Transporte\s+(.+?)\s+Num\.', text)
            if via_match:
                carga_info['via_transporte'] = via_match.group(1).strip()
            
            # Identificação
            ident_match = re.search(r'Num\. Identificacao\s+(\d+)', text)
            if ident_match:
                carga_info['identificacao_carga'] = ident_match.group(1)
            
            # Datas
            embarque_match = re.search(r'Data de Embarque\s+(\d{2}/\d{2}/\d{4})', text)
            if embarque_match:
                carga_info['data_embarque'] = embarque_match.group(1)
            
            chegada_match = re.search(r'Data de Chegada\s+(\d{2}/\d{2}/\d{4})', text)
            if chegada_match:
                carga_info['data_chegada'] = chegada_match.group(1)
            
            # Pesos
            peso_bruto_match = re.search(r'Peso Bruto\s+([\d\.,]+)', text)
            if peso_bruto_match:
                carga_info['peso_bruto'] = self._parse_valor(peso_bruto_match.group(1))
            
            peso_liquido_match = re.search(r'Peso Liquido\s+([\d\.,]+)', text)
            if peso_liquido_match:
                carga_info['peso_liquido'] = self._parse_valor(peso_liquido_match.group(1))
            
            # Países
            procedencia_match = re.search(r'Pais de Procedencia\s+(.+?)\s*\(', text)
            if procedencia_match:
                carga_info['pais_procedencia'] = procedencia_match.group(1).strip()
            
            # Unidades
            unidade_match = re.search(r'Unidade de Despacho\s+(.+?)\s+Recinto', text)
            if unidade_match:
                carga_info['unidade_despacho'] = unidade_match.group(1).strip()
            
            recinto_match = re.search(r'Recinto\s+(.+?)\s+Unid', text)
            if recinto_match:
                carga_info['recinto'] = recinto_match.group(1).strip()
            
            self.documento['carga'] = carga_info
            logger.info(f"Carga extraída: {carga_info}")
            
        except Exception as e:
            logger.error(f"Erro ao extrair carga: {str(e)}")
    
    def _extract_transporte_info(self, text: str):
        """Extrai informações de transporte"""
        transporte_info = {}
        
        try:
            # Conhecimento
            conhecimento_match = re.search(r'Tipo Conhecimento\s+(\d+)\s+-\s+(.+)', text)
            if conhecimento_match:
                transporte_info['tipo_conhecimento'] = {
                    'codigo': conhecimento_match.group(1),
                    'descricao': conhecimento_match.group(2).strip()
                }
            
            # Bandeira/Embarcação
            bandeira_match = re.search(r'Bandeira Embarcacao\s+(.+?)\s+Local', text)
            if bandeira_match:
                transporte_info['bandeira'] = bandeira_match.group(1).strip()
            
            # Local de embarque
            local_emb_match = re.search(r'Local Embarque\s+(.+)', text)
            if local_emb_match:
                transporte_info['local_embarque'] = local_emb_match.group(1).strip()
            
            # Frete
            frete_match = re.search(r'FRETE.*?Total \(Moeda\)\s+([\d\.,]+).*?Total \(R\$\)\s+([\d\.,]+)', text, re.DOTALL)
            if frete_match:
                transporte_info['frete'] = {
                    'valor_moeda': self._parse_valor(frete_match.group(1)),
                    'valor_real': self._parse_valor(frete_match.group(2))
                }
            
            # Seguro
            seguro_match = re.search(r'SEGURO.*?Total \(Moeda\)\s+([\d\.,]+).*?Total \(R\$\)\s+([\d\.,]+)', text, re.DOTALL)
            if seguro_match:
                transporte_info['seguro'] = {
                    'valor_moeda': self._parse_valor(seguro_match.group(1)),
                    'valor_real': self._parse_valor(seguro_match.group(2))
                }
            
            self.documento['transporte'] = transporte_info
            logger.info(f"Transporte extraído: {transporte_info}")
            
        except Exception as e:
            logger.error(f"Erro ao extrair transporte: {str(e)}")
    
    def _extract_total_taxes(self, text: str):
        """Extrai impostos totais da página 1"""
        impostos_totais = {}
        
        try:
            # Procurar seção de cálculos dos tributos
            calc_section = re.search(r'CÁLCULOS DOS TRIBUTOS.*?RECEITA', text, re.DOTALL)
            if calc_section:
                calc_text = calc_section.group(0)
                
                # Padrão para cada imposto
                patterns = {
                    'ii': r'II\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)',
                    'ipi': r'IPI\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)',
                    'pis': r'PIS\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)',
                    'cofins': r'COFINS\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)',
                    'taxa': r'TAXA DE UTILIZACAO\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)'
                }
                
                for imposto, pattern in patterns.items():
                    match = re.search(pattern, calc_text)
                    if match:
                        # O quinto valor é "A Recolher"
                        impostos_totais[imposto] = {
                            'calculado': self._parse_valor(match.group(1)),
                            'a_reduzir': self._parse_valor(match.group(2)),
                            'devido': self._parse_valor(match.group(3)),
                            'suspenso': self._parse_valor(match.group(4)),
                            'a_recolher': self._parse_valor(match.group(5))
                        }
            
            self.documento['impostos_totais'] = impostos_totais
            logger.info(f"Impostos totais extraídos: {impostos_totais}")
            
        except Exception as e:
            logger.error(f"Erro ao extrair impostos totais: {str(e)}")
    
    def _find_and_parse_items(self, text: str) -> List[Dict]:
        """Encontra e processa todos os itens no texto"""
        items = []
        
        try:
            # Padrão para encontrar itens (procura por "ITENS DA DUIMP")
            item_pattern = r'ITENS DA DUIMP - (\d{5}).*?(?=(?:ITENS DA DUIMP - \d{5}|\Z))'
            item_matches = re.finditer(item_pattern, text, re.DOTALL | re.IGNORECASE)
            
            for match in item_matches:
                item_text = match.group(0)
                item_num = match.group(1)
                
                logger.info(f"Processando item {item_num}")
                
                # Parsear o item
                item_data = self._parse_single_item(item_text, item_num)
                if item_data:
                    items.append(item_data)
            
            logger.info(f"Total de itens encontrados: {len(items)}")
            
        except Exception as e:
            logger.error(f"Erro ao encontrar itens: {str(e)}")
        
        return items
    
    def _parse_single_item(self, item_text: str, item_num: str) -> Optional[Dict]:
        """Parseia um único item"""
        try:
            item = {
                'numero_item': item_num,
                'ncm': '',
                'codigo_produto': '',
                'nome_produto': '',
                'descricao_produto': '',
                'codigo_interno': '',
                'pais_origem': '',
                'fabricante_conhecido': '',
                'caracterizacao_importacao': '',
                'exportador': '',
                'fabricante_produtor': '',
                'vinculacao': '',
                'aplicacao': '',
                'condicao_mercadoria': '',
                'quantidade_comercial': 0,
                'unidade_comercial': '',
                'peso_liquido_kg': 0,
                'moeda_negociada': '',
                'valor_unitario_cond_venda': 0,
                'valor_total_cond_venda': 0,
                'cfop': '',
                'descricao_complementar': '',
                'local_aduaneiro_real': 0,
                'frete_internacional_real': 0,
                'seguro_internacional_real': 0,
                
                # Impostos - INICIALIZADOS
                'ii_base_calculo': 0,
                'ii_aliquota': 0,
                'ii_valor_devido': 0,
                'ipi_base_calculo': 0,
                'ipi_aliquota': 0,
                'ipi_valor_devido': 0,
                'pis_base_calculo': 0,
                'pis_aliquota': 0,
                'pis_valor_devido': 0,
                'cofins_base_calculo': 0,
                'cofins_aliquota': 0,
                'cofins_valor_devido': 0,
                
                # ICMS
                'icms_regime': '',
                'icms_aliquota': 0,
                'icms_base_calculo': 0,
                'icms_valor_devido': 0,
                
                'total_impostos': 0,
                'valor_total_com_impostos': 0
            }
            
            # Extrair NCM e código do produto
            ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})\s+(\d{3})', item_text)
            if ncm_match:
                item['ncm'] = ncm_match.group(1)
                item['codigo_produto'] = ncm_match.group(2)
            
            # Nome do produto
            nome_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n*(.+?)(?:\nDESCRICAO|\nCÓDIGO|\Z)', 
                                  item_text, re.DOTALL | re.IGNORECASE)
            if nome_match:
                item['nome_produto'] = nome_match.group(1).replace('\n', ' ').strip()
            
            # Descrição do produto
            desc_match = re.search(r'DESCRICAO DO PRODUTO\s*\n*(.+?)(?:\nCÓDIGO INTERNO|\nFABRICANTE|\Z)', 
                                  item_text, re.DOTALL | re.IGNORECASE)
            if desc_match:
                item['descricao_produto'] = desc_match.group(1).replace('\n', ' ').strip()
            
            # Código interno
            codigo_match = re.search(r'Código interno\s*(\d+\.\d+\.\d+)', item_text)
            if codigo_match:
                item['codigo_interno'] = codigo_match.group(1)
            
            # Fabricante/Produtor
            fabricante_match = re.search(r'Conhecido\s+(SIM|NAO)', item_text, re.IGNORECASE)
            if fabricante_match:
                item['fabricante_conhecido'] = fabricante_match.group(1).upper()
            
            # País de origem
            pais_match = re.search(r'Pais Origem\s+(IT ITALIA|.+?)(?:\n|$)', item_text)
            if pais_match:
                item['pais_origem'] = pais_match.group(1).strip()
            
            # Caracterização da importação
            import_match = re.search(r'Importação\s+(.+?)(?:\n|$)', item_text)
            if import_match:
                item['caracterizacao_importacao'] = import_match.group(1).strip()
            
            # Extrair dados da mercadoria
            self._extract_item_mercadoria(item_text, item)
            
            # Extrair impostos do item
            self._extract_item_taxes(item_text, item)
            
            # Extrair ICMS
            self._extract_item_icms(item_text, item)
            
            # Calcular totais
            item['total_impostos'] = (
                item['ii_valor_devido'] + 
                item['ipi_valor_devido'] + 
                item['pis_valor_devido'] + 
                item['cofins_valor_devido']
            )
            
            item['valor_total_com_impostos'] = item['valor_total_cond_venda'] + item['total_impostos']
            
            logger.info(f"Item {item_num} processado:")
            logger.info(f"  Nome: {item['nome_produto'][:50]}...")
            logger.info(f"  Valor: R$ {item['valor_total_cond_venda']:.2f}")
            logger.info(f"  Impostos: II={item['ii_valor_devido']:.2f}, PIS={item['pis_valor_devido']:.2f}, COFINS={item['cofins_valor_devido']:.2f}")
            
            return item
            
        except Exception as e:
            logger.error(f"Erro ao parsear item {item_num}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_item_mercadoria(self, text: str, item: Dict):
        """Extrai dados da mercadoria do item"""
        try:
            # Aplicação
            app_match = re.search(r'Aplicação\s+(.+?)(?:\n|$)', text)
            if app_match:
                item['aplicacao'] = app_match.group(1).strip()
            
            # Quantidade comercial
            qtd_match = re.search(r'Qtde Unid\. Comercial\s+([\d\.,]+)', text)
            if qtd_match:
                item['quantidade_comercial'] = self._parse_valor(qtd_match.group(1))
            
            # Unidade comercial
            unid_match = re.search(r'Unidade Comercial\s+(.+?)(?:\n|$)', text)
            if unid_match:
                item['unidade_comercial'] = unid_match.group(1).strip()
            
            # Peso líquido
            peso_match = re.search(r'Peso Líquido \(KG\)\s+([\d\.,]+)', text)
            if peso_match:
                item['peso_liquido_kg'] = self._parse_valor(peso_match.group(1))
            
            # Valor unitário
            valor_unit_match = re.search(r'Valor Unit Cond Venda\s+([\d\.,]+)', text)
            if valor_unit_match:
                item['valor_unitario_cond_venda'] = self._parse_valor(valor_unit_match.group(1))
            
            # Valor total
            valor_total_match = re.search(r'Valor Tot\. Cond Venda\s+([\d\.,]+)', text)
            if valor_total_match:
                item['valor_total_cond_venda'] = self._parse_valor(valor_total_match.group(1))
            
            # CFOP
            cfop_match = re.search(r'CFOP\s+(\d+)\s+-\s+(.+?)(?:\n|$)', text)
            if cfop_match:
                item['cfop'] = f"{cfop_match.group(1)} - {cfop_match.group(2).strip()}"
            
            # Local aduaneiro
            local_adu_match = re.search(r'Local Aduaneiro \(R\$\)\s+([\d\.,]+)', text)
            if local_adu_match:
                item['local_aduaneiro_real'] = self._parse_valor(local_adu_match.group(1))
            
            # Frete internacional
            frete_match = re.search(r'Frete Internac\. \(R\$\)\s+([\d\.,]+)', text)
            if frete_match:
                item['frete_internacional_real'] = self._parse_valor(frete_match.group(1))
            
            # Seguro internacional
            seguro_match = re.search(r'Seguro Internac\. \(R\$\)\s+([\d\.,]+)', text)
            if seguro_match:
                item['seguro_internacional_real'] = self._parse_valor(seguro_match.group(1))
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados da mercadoria: {str(e)}")
    
    def _extract_item_taxes(self, text: str, item: Dict):
        """Extrai impostos do item - VERSÃO CORRIGIDA E ROBUSTA"""
        try:
            # Procurar por cada imposto individualmente
            tax_types = ['II', 'IPI', 'PIS', 'COFINS']
            
            for tax in tax_types:
                # Padrões robustos para cada imposto
                patterns = [
                    fr'{tax}.*?Base de Cálculo \(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor Devido \(R\$\)\s*([\d\.,]+)',
                    fr'{tax}.*?Base de Cálculo \(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+)',
                    fr'{tax}.*?Base de Cálculo \(R\$\)\s*([\d\.,]+).*?Valor Devido \(R\$\)\s*([\d\.,]+)',
                    fr'{tax}.*?% Alíquota\s*([\d\.,]+).*?Valor Devido \(R\$\)\s*([\d\.,]+)',
                    fr'{tax}.*?Valor Devido \(R\$\)\s*([\d\.,]+)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        
                        # Base de cálculo
                        if len(groups) >= 1 and 'Base' in pattern:
                            item[f'{tax.lower()}_base_calculo'] = self._parse_valor(groups[0])
                        
                        # Alíquota
                        if len(groups) >= 2:
                            # Verificar qual grupo é a alíquota
                            if 'Alíquota' in pattern:
                                # O grupo 1 é a base, grupo 2 é a alíquota
                                item[f'{tax.lower()}_aliquota'] = self._parse_valor(groups[1])
                            elif len(groups) == 2 and 'Valor' in pattern:
                                # Padrão simples: base e valor
                                item[f'{tax.lower()}_valor_devido'] = self._parse_valor(groups[1])
                        
                        # Valor devido
                        if len(groups) >= 3:
                            item[f'{tax.lower()}_valor_devido'] = self._parse_valor(groups[2])
                        elif len(groups) == 1 and 'Valor' in pattern and 'Base' not in pattern:
                            # Padrão que só tem o valor
                            item[f'{tax.lower()}_valor_devido'] = self._parse_valor(groups[0])
                        
                        # Se encontrou pelo menos um padrão, pode parar de procurar
                        break
            
            # Fallback: procurar valores específicos se não encontrou com os padrões anteriores
            if item['ii_valor_devido'] == 0:
                ii_valor_match = re.search(r'II.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.DOTALL | re.IGNORECASE)
                if ii_valor_match:
                    item['ii_valor_devido'] = self._parse_valor(ii_valor_match.group(1))
            
            if item['pis_valor_devido'] == 0:
                pis_valor_match = re.search(r'PIS.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.DOTALL | re.IGNORECASE)
                if pis_valor_match:
                    item['pis_valor_devido'] = self._parse_valor(pis_valor_match.group(1))
            
            if item['cofins_valor_devido'] == 0:
                cofins_valor_match = re.search(r'COFINS.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.DOTALL | re.IGNORECASE)
                if cofins_valor_match:
                    item['cofins_valor_devido'] = self._parse_valor(cofins_valor_match.group(1))
            
            # Log dos valores extraídos
            logger.debug(f"Impostos extraídos para item {item.get('numero_item', 'N/A')}:")
            logger.debug(f"  II: Base={item['ii_base_calculo']}, Alíq={item['ii_aliquota']}, Valor={item['ii_valor_devido']}")
            logger.debug(f"  PIS: Base={item['pis_base_calculo']}, Alíq={item['pis_aliquota']}, Valor={item['pis_valor_devido']}")
            logger.debug(f"  COFINS: Base={item['cofins_base_calculo']}, Alíq={item['cofins_aliquota']}, Valor={item['cofins_valor_devido']}")
            
        except Exception as e:
            logger.error(f"Erro ao extrair impostos do item: {str(e)}")
    
    def _extract_item_icms(self, text: str, item: Dict):
        """Extrai informações de ICMS do item"""
        try:
            # Procurar seção de ICMS
            icms_section = re.search(r'INFORMAÇÕES DO ICMS.*?(?=(?:ITENS DA DUIMP|\Z))', text, re.DOTALL | re.IGNORECASE)
            
            if icms_section:
                icms_text = icms_section.group(0)
                
                # Regime de tributação
                regime_match = re.search(r'Regime de Tributacao\s+(.+?)(?:\n|$)', icms_text)
                if regime_match:
                    item['icms_regime'] = regime_match.group(1).strip()
                
                # Alíquota
                aliquota_match = re.search(r'% Alíquota Ad Valorem\s+([\d\.,]+)', icms_text)
                if aliquota_match:
                    item['icms_aliquota'] = self._parse_valor(aliquota_match.group(1))
                
                # Base de cálculo
                base_match = re.search(r'Base de Cálculo\s+([\d\.,]+)', icms_text)
                if base_match:
                    item['icms_base_calculo'] = self._parse_valor(base_match.group(1))
                
                # Valor devido
                valor_match = re.search(r'Valor Devido\s+([\d\.,]+)', icms_text)
                if valor_match:
                    item['icms_valor_devido'] = self._parse_valor(valor_match.group(1))
            
        except Exception as e:
            logger.error(f"Erro ao extrair ICMS: {str(e)}")
    
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
            'cofins_total': 0,
            'valor_total_com_impostos': 0,
            'frete_total': 0,
            'seguro_total': 0
        }
        
        for item in self.documento['itens']:
            totais['valor_total_mercadoria'] += item.get('valor_total_cond_venda', 0)
            totais['peso_total'] += item.get('peso_liquido_kg', 0)
            totais['quantidade_total'] += item.get('quantidade_comercial', 0)
            totais['ii_total'] += item.get('ii_valor_devido', 0)
            totais['ipi_total'] += item.get('ipi_valor_devido', 0)
            totais['pis_total'] += item.get('pis_valor_devido', 0)
            totais['cofins_total'] += item.get('cofins_valor_devido', 0)
            totais['total_impostos'] += item.get('total_impostos', 0)
            totais['valor_total_com_impostos'] += item.get('valor_total_com_impostos', 0)
            totais['frete_total'] += item.get('frete_internacional_real', 0)
            totais['seguro_total'] += item.get('seguro_internacional_real', 0)
        
        self.documento['totais'] = totais
        
        logger.info(f"Totais calculados: {totais}")
    
    def _parse_valor(self, valor_str: str) -> float:
        """Converte string de valor para float"""
        try:
            if not valor_str or valor_str.strip() == '':
                return 0.0
            
            # Remover pontos de milhar e converter vírgula decimal para ponto
            valor_limpo = valor_str.replace('.', '').replace(',', '.')
            
            # Garantir que é um número válido
            valor_float = float(valor_limpo)
            
            # Arredondar para 2 casas decimais
            return round(valor_float, 2)
            
        except Exception as e:
            logger.warning(f"Erro ao converter valor '{valor_str}': {str(e)}")
            return 0.0


class FinancialAnalyzer:
    """Analisador financeiro para APP2"""
    
    def __init__(self, documento: Dict):
        self.documento = documento
        self.itens_df = None
        self.summary_df = None
        
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
                'Descrição': item.get('descricao_produto', ''),
                'País Origem': item.get('pais_origem', ''),
                'Aplicação': item.get('aplicacao', ''),
                'Fabricante Conhecido': item.get('fabricante_conhecido', ''),
                'CFOP': item.get('cfop', ''),
                'Quantidade': item.get('quantidade_comercial', 0),
                'Unidade': item.get('unidade_comercial', ''),
                'Peso (kg)': item.get('peso_liquido_kg', 0),
                'Valor Unit. (R$)': item.get('valor_unitario_cond_venda', 0),
                'Valor Total (R$)': item.get('valor_total_cond_venda', 0),
                'Local Aduaneiro (R$)': item.get('local_aduaneiro_real', 0),
                'Frete (R$)': item.get('frete_internacional_real', 0),
                'Seguro (R$)': item.get('seguro_internacional_real', 0),
                
                # Impostos - Bases
                'II Base (R$)': item.get('ii_base_calculo', 0),
                'IPI Base (R$)': item.get('ipi_base_calculo', 0),
                'PIS Base (R$)': item.get('pis_base_calculo', 0),
                'COFINS Base (R$)': item.get('cofins_base_calculo', 0),
                
                # Impostos - Alíquotas
                'II Alíq. (%)': item.get('ii_aliquota', 0),
                'IPI Alíq. (%)': item.get('ipi_aliquota', 0),
                'PIS Alíq. (%)': item.get('pis_aliquota', 0),
                'COFINS Alíq. (%)': item.get('cofins_aliquota', 0),
                
                # Impostos - Valores
                'II (R$)': item.get('ii_valor_devido', 0),
                'IPI (R$)': item.get('ipi_valor_devido', 0),
                'PIS (R$)': item.get('pis_valor_devido', 0),
                'COFINS (R$)': item.get('cofins_valor_devido', 0),
                
                # ICMS
                'ICMS Regime': item.get('icms_regime', ''),
                'ICMS Alíq. (%)': item.get('icms_aliquota', 0),
                'ICMS Base (R$)': item.get('icms_base_calculo', 0),
                'ICMS (R$)': item.get('icms_valor_devido', 0),
                
                'Total Impostos (R$)': item.get('total_impostos', 0),
                'Valor c/ Impostos (R$)': item.get('valor_total_com_impostos', 0)
            })
        
        self.itens_df = pd.DataFrame(itens_data)
        return self.itens_df
    
    def create_summary_dataframe(self):
        """Cria DataFrame com métricas resumidas"""
        totais = self.documento.get('totais', {})
        
        summary_data = {
            'Métrica': [
                'Valor Total Mercadoria',
                'Quantidade Total',
                'Peso Total (kg)',
                'Total Impostos',
                'II Total',
                'IPI Total',
                'PIS Total',
                'COFINS Total',
                'Frete Total',
                'Seguro Total',
                'Valor Total com Impostos'
            ],
            'Valor (R$)': [
                totais.get('valor_total_mercadoria', 0),
                totais.get('quantidade_total', 0),
                totais.get('peso_total', 0),
                totais.get('total_impostos', 0),
                totais.get('ii_total', 0),
                totais.get('ipi_total', 0),
                totais.get('pis_total', 0),
                totais.get('cofins_total', 0),
                totais.get('frete_total', 0),
                totais.get('seguro_total', 0),
                totais.get('valor_total_com_impostos', 0)
            ]
        }
        
        self.summary_df = pd.DataFrame(summary_data)
        return self.summary_df


def display_header_info(cabecalho: Dict):
    """Exibe informações do cabeçalho"""
    st.markdown('<h2 class="sub-header">📋 Informações do Processo</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="section-card">
            <div class="metric-value">{cabecalho.get('processo', 'N/A')}</div>
            <div class="metric-label">Processo</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="section-card">
            <div class="metric-value">{cabecalho.get('importador', 'N/A')[:20]}{'...' if len(cabecalho.get('importador', '')) > 20 else ''}</div>
            <div class="metric-label">Importador</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="section-card">
            <div class="metric-value">{cabecalho.get('cnpj', 'N/A')}</div>
            <div class="metric-label">CNPJ</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="section-card">
            <div class="metric-value">{cabecalho.get('responsavel', 'N/A')[:15]}{'...' if len(cabecalho.get('responsavel', '')) > 15 else ''}</div>
            <div class="metric-label">Responsável</div>
        </div>
        """, unsafe_allow_html=True)


def display_carga_info(carga: Dict):
    """Exibe informações da carga"""
    st.markdown('<h2 class="sub-header">📦 Informações da Carga</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info(f"**Via Transporte:** {carga.get('via_transporte', 'N/A')}")
    
    with col2:
        st.info(f"**Data Embarque:** {carga.get('data_embarque', 'N/A')}")
    
    with col3:
        st.info(f"**Data Chegada:** {carga.get('data_chegada', 'N/A')}")
    
    with col4:
        st.info(f"**Identificação:** {carga.get('identificacao_carga', 'N/A')}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info(f"**Peso Bruto:** {carga.get('peso_bruto', 0):,.2f} kg")
    
    with col2:
        st.info(f"**Peso Líquido:** {carga.get('peso_liquido', 0):,.2f} kg")
    
    with col3:
        st.info(f"**País Procedência:** {carga.get('pais_procedencia', 'N/A')}")
    
    with col4:
        st.info(f"**Unidade Despacho:** {carga.get('unidade_despacho', 'N/A')}")


def display_transporte_info(transporte: Dict):
    """Exibe informações de transporte"""
    st.markdown('<h2 class="sub-header">🚢 Informações de Transporte</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if transporte.get('tipo_conhecimento'):
            tipo = transporte['tipo_conhecimento']
            st.info(f"**Conhecimento:** {tipo.get('codigo', '')} - {tipo.get('descricao', '')}")
    
    with col2:
        st.info(f"**Bandeira:** {transporte.get('bandeira', 'N/A')}")
    
    with col3:
        st.info(f"**Local Embarque:** {transporte.get('local_embarque', 'N/A')}")
    
    with col4:
        if transporte.get('frete'):
            frete = transporte['frete']
            st.info(f"**Frete:** R$ {frete.get('valor_real', 0):,.2f}")
        
        if transporte.get('seguro'):
            seguro = transporte['seguro']
            st.info(f"**Seguro:** R$ {seguro.get('valor_real', 0):,.2f}")


def display_moedas_info(moedas: Dict):
    """Exibe informações de moedas"""
    st.markdown('<h2 class="sub-header">💰 Cotações de Moedas</h2>', unsafe_allow_html=True)
    
    if moedas.get('data_cotacao'):
        st.info(f"**Data das Cotações:** {moedas['data_cotacao']}")
    
    currency_data = []
    
    if 'moeda_negociada' in moedas:
        moeda = moedas['moeda_negociada']
        currency_data.append({
            'Moeda': moeda.get('nome', ''),
            'Código': '978',
            'Cotação': f"R$ {moeda.get('cotacao', 0):,.4f}"
        })
    
    if 'dolar' in moedas:
        dolar = moedas['dolar']
        currency_data.append({
            'Moeda': dolar.get('nome', ''),
            'Código': '220',
            'Cotação': f"R$ {dolar.get('cotacao', 0):,.4f}"
        })
    
    if currency_data:
        df_currency = pd.DataFrame(currency_data)
        st.dataframe(df_currency, use_container_width=True)


def display_impostos_totais(impostos_totais: Dict):
    """Exibe totais de impostos"""
    st.markdown('<h2 class="sub-header">🏛️ Impostos Totais do Documento</h2>', unsafe_allow_html=True)
    
    if not impostos_totais:
        st.warning("Nenhum imposto total encontrado")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    col_idx = 0
    
    impostos_mapping = {
        'ii': 'Imposto de Importação',
        'ipi': 'IPI',
        'pis': 'PIS',
        'cofins': 'COFINS',
        'taxa': 'Taxa de Utilização'
    }
    
    for imposto_key, imposto_nome in impostos_mapping.items():
        if imposto_key in impostos_totais:
            imposto_data = impostos_totais[imposto_key]
            valor = imposto_data.get('a_recolher', 0)
            
            if valor > 0:
                if col_idx < 4:
                    col = [col1, col2, col3, col4][col_idx]
                    with col:
                        st.markdown(f"""
                        <div class="section-card">
                            <div class="metric-value">R$ {valor:,.2f}</div>
                            <div class="metric-label">{imposto_nome}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    col_idx += 1


def display_tax_debug_info(documento: Dict):
    """Exibe informações de debug sobre impostos"""
    st.markdown('<h2 class="sub-header">🔍 Debug: Informações de Impostos</h2>', unsafe_allow_html=True)
    
    with st.expander("Ver detalhes de extração de impostos"):
        if documento['itens']:
            st.markdown("### Primeiro Item (Exemplo)")
            first_item = documento['itens'][0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Valores Extraídos:")
                st.json({
                    'II': {
                        'base': first_item.get('ii_base_calculo', 0),
                        'aliquota': first_item.get('ii_aliquota', 0),
                        'valor': first_item.get('ii_valor_devido', 0)
                    },
                    'PIS': {
                        'base': first_item.get('pis_base_calculo', 0),
                        'aliquota': first_item.get('pis_aliquota', 0),
                        'valor': first_item.get('pis_valor_devido', 0)
                    },
                    'COFINS': {
                        'base': first_item.get('cofins_base_calculo', 0),
                        'aliquota': first_item.get('cofins_aliquota', 0),
                        'valor': first_item.get('cofins_valor_devido', 0)
                    }
                })
            
            with col2:
                st.markdown("#### Cálculos:")
                st.metric("Total Impostos Item", f"R$ {first_item.get('total_impostos', 0):,.2f}")
                st.metric("Valor Mercadoria", f"R$ {first_item.get('valor_total_cond_venda', 0):,.2f}")
                st.metric("Valor c/ Impostos", f"R$ {first_item.get('valor_total_com_impostos', 0):,.2f}")


def main():
    """Função principal"""
    
    st.markdown('<h1 class="main-header">🏭 Sistema de Análise de Extratos Häfele - APP2</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>📄 Especificação:</strong> Este sistema foi ajustado especificamente para o layout do arquivo APP2.pdf.
        <br><strong>🔍 Funcionalidades:</strong> Extração completa de cabeçalho, carga, transporte, moedas, itens e impostos.
        <br><strong>⚠️ IMPORTANTE:</strong> Sistema otimizado para extração robusta de PIS, COFINS, II e outros impostos.
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### 📁 Upload do Documento APP2")
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo PDF (Formato APP2)",
            type=['pdf'],
            help="Documento PDF no formato padrão APP2.pdf da Häfele"
        )
        
        st.markdown("---")
        st.markdown("### ⚙️ Opções de Análise")
        
        show_tax_debug = st.checkbox("Mostrar debug de impostos", value=False)
        export_raw_data = st.checkbox("Exportar dados brutos", value=False)
        
        st.markdown("---")
        
        if uploaded_file:
            file_size = uploaded_file.size / (1024 * 1024)
            st.success(f"📄 Arquivo: {uploaded_file.name}")
            st.info(f"📊 Tamanho: {file_size:.2f} MB")
            st.info(f"📅 Processamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if uploaded_file is not None:
        try:
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Etapa 1: Análise do documento
            status_text.text("📄 Analisando documento PDF (Layout APP2)...")
            progress_bar.progress(20)
            
            parser = HafelePDFParser()
            documento = parser.parse_pdf(tmp_path)
            
            # Etapa 2: Processamento dos dados
            status_text.text("📊 Processando dados e calculando métricas...")
            progress_bar.progress(50)
            
            analyser = FinancialAnalyzer(documento)
            df = analyser.prepare_dataframe()
            summary_df = analyser.create_summary_dataframe()
            
            # Etapa 3: Cálculos finais
            status_text.text("🔢 Gerando visualizações...")
            progress_bar.progress(80)
            
            # Limpar arquivo temporário
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            progress_bar.progress(100)
            status_text.text("✅ Processamento concluído!")
            
            # Exibir informações gerais
            st.success(f"✅ **{len(documento['itens'])} itens** extraídos com sucesso do documento APP2!")
            
            # Métricas principais
            st.markdown('<h2 class="sub-header">📊 Métricas Principais</h2>', unsafe_allow_html=True)
            
            totais = documento.get('totais', {})
            
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
                    <div class="metric-value">R$ {totais.get('valor_total_com_impostos', 0):,.2f}</div>
                    <div class="metric-label">Valor c/ Impostos</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">{totais.get('quantidade_total', 0):,.0f}</div>
                    <div class="metric-label">Quantidade Total</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Abas para diferentes seções
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
                "📋 Cabeçalho", "📦 Carga", "🚢 Transporte", "💰 Moedas", "🏛️ Impostos", "📊 Itens", "📈 Análises"
            ])
            
            with tab1:
                if documento.get('cabecalho'):
                    display_header_info(documento['cabecalho'])
            
            with tab2:
                if documento.get('carga'):
                    display_carga_info(documento['carga'])
            
            with tab3:
                if documento.get('transporte'):
                    display_transporte_info(documento['transporte'])
            
            with tab4:
                if documento.get('moedas'):
                    display_moedas_info(documento['moedas'])
            
            with tab5:
                # Impostos totais
                if documento.get('impostos_totais'):
                    display_impostos_totais(documento['impostos_totais'])
                
                # Debug de impostos
                if show_tax_debug:
                    display_tax_debug_info(documento)
                
                # Resumo de impostos por item
                if not df.empty:
                    st.markdown("#### 📋 Resumo de Impostos por Item")
                    
                    # Filtrar colunas de impostos
                    tax_cols = ['Item', 'Produto', 'II (R$)', 'IPI (R$)', 'PIS (R$)', 'COFINS (R$)', 'Total Impostos (R$)']
                    available_cols = [col for col in tax_cols if col in df.columns]
                    
                    if available_cols:
                        tax_summary = df[available_cols].copy()
                        
                        # Formatar valores
                        for col in ['II (R$)', 'IPI (R$)', 'PIS (R$)', 'COFINS (R$)', 'Total Impostos (R$)']:
                            if col in tax_summary.columns:
                                tax_summary[col] = tax_summary[col].apply(lambda x: f"R$ {x:,.2f}")
                        
                        st.dataframe(tax_summary, use_container_width=True, height=300)
            
            with tab6:
                st.markdown('<h2 class="sub-header">📦 Lista de Itens Detalhada</h2>', unsafe_allow_html=True)
                
                # Configurar colunas para exibição
                if not df.empty:
                    # Ordenar colunas para melhor visualização
                    col_order = [
                        'Item', 'Código Interno', 'Produto', 'Descrição',
                        'Quantidade', 'Unidade', 'Peso (kg)',
                        'Valor Unit. (R$)', 'Valor Total (R$)',
                        'II Base (R$)', 'II Alíq. (%)', 'II (R$)',
                        'PIS Base (R$)', 'PIS Alíq. (%)', 'PIS (R$)',
                        'COFINS Base (R$)', 'COFINS Alíq. (%)', 'COFINS (R$)',
                        'Total Impostos (R$)', 'Valor c/ Impostos (R$)'
                    ]
                    
                    display_cols = [c for c in col_order if c in df.columns]
                    remaining_cols = [c for c in df.columns if c not in display_cols]
                    final_cols = display_cols + remaining_cols
                    
                    display_df = df[final_cols].copy()
                    
                    # Formatação de moeda
                    currency_cols = [col for col in display_df.columns if '(R$)' in col]
                    for col in currency_cols:
                        display_df[col] = display_df[col].apply(lambda x: f"R$ {x:,.2f}" if pd.notnull(x) else "")
                    
                    # Formatação de porcentagem
                    pct_cols = [col for col in display_df.columns if '(%)' in col]
                    for col in pct_cols:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}%" if pd.notnull(x) else "")
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        height=600
                    )
                else:
                    st.warning("Nenhum item encontrado no documento.")
            
            with tab7:
                st.markdown('<h2 class="sub-header">📈 Análises Financeiras</h2>', unsafe_allow_html=True)
                
                if not df.empty:
                    # Análise de impostos
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("##### 💰 Distribuição de Impostos")
                        
                        # Preparar dados para o gráfico
                        tax_distribution = {
                            'Imposto': ['II', 'PIS', 'COFINS'],
                            'Valor (R$)': [
                                totais.get('ii_total', 0),
                                totais.get('pis_total', 0),
                                totais.get('cofins_total', 0)
                            ]
                        }
                        
                        tax_df = pd.DataFrame(tax_distribution)
                        
                        fig1 = px.pie(
                            tax_df,
                            values='Valor (R$)',
                            names='Imposto',
                            title="Distribuição dos Impostos Totais",
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        fig1.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        st.markdown("##### 📊 Top 10 Produtos por Valor")
                        
                        # Preparar dados
                        top_products = df.copy()
                        top_products['Valor Total (R$)'] = top_products['Valor Total (R$)'].str.replace('R$ ', '').str.replace(',', '').astype(float)
                        top_products = top_products.nlargest(10, 'Valor Total (R$)')
                        
                        fig2 = px.bar(
                            top_products,
                            x='Produto',
                            y='Valor Total (R$)',
                            title="Top 10 Produtos por Valor",
                            color='Valor Total (R$)',
                            color_continuous_scale='Blues'
                        )
                        fig2.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    # Tabela de resumo
                    st.markdown("##### 📋 Resumo Financeiro")
                    
                    # Formatar o DataFrame de resumo
                    display_summary = summary_df.copy()
                    display_summary['Valor (R$)'] = display_summary['Valor (R$)'].apply(lambda x: f"R$ {x:,.2f}" if x >= 0 else f"-R$ {abs(x):,.2f}")
                    
                    st.dataframe(display_summary, use_container_width=True)
            
            # Exportação de dados
            st.markdown('<h2 class="sub-header">💾 Exportação de Dados</h2>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Exportar CSV completo
                csv_data = df.to_csv(index=False, encoding='utf-8-sig', sep=';')
                st.download_button(
                    label="📥 Baixar CSV (Completo)",
                    data=csv_data,
                    file_name="app2_hafele_completo.csv",
                    mime="text/csv",
                    help="Baixar todos os dados em formato CSV"
                )
            
            with col2:
                # Exportar Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Dados principais
                    df.to_excel(writer, sheet_name='Itens', index=False)
                    
                    # Resumo
                    summary_df.to_excel(writer, sheet_name='Resumo', index=False)
                    
                    # Totais
                    totais_df = pd.DataFrame([totais])
                    totais_df.to_excel(writer, sheet_name='Totais', index=False)
                
                st.download_button(
                    label="📊 Baixar Excel",
                    data=output.getvalue(),
                    file_name="app2_hafele_completo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Baixar todos os dados em formato Excel com múltiplas abas"
                )
            
            with col3:
                # Exportar JSON
                json_data = json.dumps(documento, default=str, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📋 Baixar JSON",
                    data=json_data,
                    file_name="app2_hafele_documento.json",
                    mime="application/json",
                    help="Baixar dados estruturados em formato JSON"
                )
            
            # Dados brutos (opcional)
            if export_raw_data:
                st.markdown('<h2 class="sub-header">🔍 Dados Brutos Extraídos</h2>', unsafe_allow_html=True)
                with st.expander("Visualizar estrutura completa dos dados"):
                    st.json(documento, expanded=False)
        
        except Exception as e:
            st.error(f"❌ Erro no processamento: {str(e)}")
            logger.error(f"Erro detalhado: {str(e)}", exc_info=True)
            
            # Mostrar mais detalhes do erro
            with st.expander("Detalhes do erro"):
                st.code(str(e))
    
    else:
        st.info("📁 Aguardando upload do arquivo PDF no formato APP2...")
        st.markdown("""
        <div class="warning-box">
            <strong>⚠️ Instruções:</strong>
            <ol>
                <li>Clique em <strong>"Browse files"</strong> no menu à esquerda</li>
                <li>Selecione um arquivo PDF no formato <strong>APP2.pdf</strong></li>
                <li>Aguarde o processamento automático (pode levar alguns segundos)</li>
                <li>Explore os dados nas diferentes abas</li>
                <li>Baixe os dados nos formatos desejados</li>
            </ol>
            <br>
            <strong>🎯 Destaques do Sistema:</strong>
            <ul>
                <li>Extração robusta de impostos (PIS, COFINS, II, IPI)</li>
                <li>Análise detalhada de cada item</li>
                <li>Visualizações gráficas interativas</li>
                <li>Exportação em múltiplos formatos</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
