# -*- coding: utf-8 -*-
"""
ANALISADOR COMPLETO DE DOCUMENTOS DE IMPORTAÇÃO
Streamlit App - Versão 2.0
Extrai TODOS os dados do PDF padrão incluindo bases de cálculo e tributos detalhados
"""

import streamlit as st
import PyPDF2
import pandas as pd
import numpy as np
import re
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io
import base64
from typing import Dict, List, Any, Optional, Tuple

# ============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Analisador de Importação HAFELE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS CUSTOMIZADO
# ============================================================================

st.markdown("""
<style>
    /* Títulos principais */
    .main-title {
        font-size: 2.8rem;
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 800;
        padding: 1rem;
    }
    
    .sub-title {
        font-size: 1.8rem;
        color: #1E40AF;
        border-bottom: 3px solid #3B82F6;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
        margin-bottom: 1.5rem;
        font-weight: 700;
    }
    
    .section-title {
        font-size: 1.4rem;
        color: #374151;
        background-color: #F3F4F6;
        padding: 0.8rem;
        border-radius: 8px;
        margin-top: 1.5rem;
        font-weight: 600;
    }
    
    /* Cards e containers */
    .info-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #E5E7EB;
    }
    
    .tax-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        margin: 0.5rem;
    }
    
    .metric-card {
        background: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .warning-box {
        background-color: #FEF3C7;
        border-left: 5px solid #F59E0B;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    
    .success-box {
        background-color: #D1FAE5;
        border-left: 5px solid #10B981;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    
    /* Tabelas */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #E5E7EB;
    }
    
    /* Botões */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    
    .badge-primary {
        background-color: #DBEAFE;
        color: #1E40AF;
    }
    
    .badge-success {
        background-color: #D1FAE5;
        color: #065F46;
    }
    
    .badge-warning {
        background-color: #FEF3C7;
        color: #92400E;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# MÓDULO DE EXTRAÇÃO DE DADOS DO PDF (CIENTISTA DE DADOS)
# ============================================================================

class PDFDataExtractor:
    """Classe especializada em extrair dados do layout padrão de importação"""
    
    def __init__(self, pdf_text: str):
        self.pdf_text = pdf_text
        self.data = {
            'informacoes_gerais': {},
            'moedas_cotacoes': {},
            'valores_totais': {},
            'tributos_totais': {},
            'dados_carga': {},
            'transportes': {},
            'documentos': {},
            'itens': [],
            'resumo_geral': {}
        }
    
    def extract_all_data(self) -> Dict[str, Any]:
        """Extrai todos os dados do PDF"""
        try:
            self._extract_informacoes_gerais()
            self._extract_moedas_cotacoes()
            self._extract_valores_totais()
            self._extract_tributos_totais()
            self._extract_dados_carga()
            self._extract_transportes()
            self._extract_documentos()
            self._extract_itens_detalhados()
            self._calcular_resumo_geral()
            return self.data
        except Exception as e:
            st.error(f"Erro na extração de dados: {str(e)}")
            return self.data
    
    def _extract_informacoes_gerais(self):
        """Extrai informações gerais do processo"""
        patterns = {
            'processo': r'PROCESSO #(\d+)',
            'importador': r'IMPORTADOR\s+(.+?)\n',
            'cnpj': r'CNPJ\s+(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
            'identificacao': r'Identificacao\s+(.+?)\s',
            'data_cadastro': r'Data de Cadastro\s+(\d{2}/\d{2}/\d{4})',
            'duimp': r'Numero\s+(\d{2}BR\d+)',
            'versao': r'Versao\s+(\d+)',
            'data_registro': r'Data Registro\s+(\d{2}/\d{2}/\d{4})',
            'tipo': r'Tipo\s+(CONSUMO|OUTROS)',
            'operacao': r'Operacao\s+(PROPRIA|OUTROS)',
            'responsavel': r'Responsavel Legal\s+(.+?)\n',
            'ref_importador': r'Ref\. Importador\s+(.+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, self.pdf_text)
            if match:
                self.data['informacoes_gerais'][key] = match.group(1).strip()
    
    def _extract_moedas_cotacoes(self):
        """Extrai moedas e cotações"""
        # Moeda negociada
        moeda_match = re.search(r'Moeda Negociada\s+(\d+)\s+-\s+(.+?)\s+Cotacao\s+([\d,]+)', self.pdf_text)
        if moeda_match:
            self.data['moedas_cotacoes']['moeda_negociada'] = {
                'codigo': moeda_match.group(1),
                'nome': moeda_match.group(2),
                'cotacao': float(moeda_match.group(3).replace(',', '.'))
            }
        
        # Moeda frete
        frete_match = re.search(r'Moeda Frete\s+(\d+)\s+-\s+(.+?)\s+Cotacao\s+([\d,]+)', self.pdf_text)
        if frete_match:
            self.data['moedas_cotacoes']['moeda_frete'] = {
                'codigo': frete_match.group(1),
                'nome': frete_match.group(2),
                'cotacao': float(frete_match.group(3).replace(',', '.'))
            }
        
        # Moeda seguro
        seguro_match = re.search(r'Moeda Seguro\s+(\d+)\s+-\s+(.+?)\s+Cotacao\s+([\d,]+)', self.pdf_text)
        if seguro_match:
            self.data['moedas_cotacoes']['moeda_seguro'] = {
                'codigo': seguro_match.group(1),
                'nome': seguro_match.group(2),
                'cotacao': float(seguro_match.group(3).replace(',', '.'))
            }
    
    def _extract_valores_totais(self):
        """Extrai valores totais CIF, VMLE, VMLD"""
        # CIF
        cif_match = re.search(r'CIF\s*\(US\$\)\s*([\d.,]+)\s+CIF\s*\(R\$\)\s*([\d.,]+)', self.pdf_text)
        if cif_match:
            self.data['valores_totais']['cif_usd'] = float(cif_match.group(1).replace('.', '').replace(',', '.'))
            self.data['valores_totais']['cif_brl'] = float(cif_match.group(2).replace('.', '').replace(',', '.'))
        
        # VMLE
        vmle_match = re.search(r'VMLE\s*\(US\$\)\s*([\d.,]+)\s+VMLE\s*\(R\$\)\s*([\d.,]+)', self.pdf_text)
        if vmle_match:
            self.data['valores_totais']['vmle_usd'] = float(vmle_match.group(1).replace('.', '').replace(',', '.'))
            self.data['valores_totais']['vmle_brl'] = float(vmle_match.group(2).replace('.', '').replace(',', '.'))
        
        # VMLD
        vmld_match = re.search(r'VMLD\s*\(US\$\)\s*([\d.,]+)\s+VMLD\s*\(R\$\)\s*([\d.,]+)', self.pdf_text)
        if vmld_match:
            self.data['valores_totais']['vmld_usd'] = float(vmld_match.group(1).replace('.', '').replace(',', '.'))
            self.data['valores_totais']['vmld_brl'] = float(vmld_match.group(2).replace('.', '').replace(',', '.'))
    
    def _extract_tributos_totais(self):
        """Extrai tributos totais da tabela"""
        # Padrão para II
        ii_match = re.search(r'II\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', self.pdf_text)
        if ii_match:
            self.data['tributos_totais']['II'] = {
                'calculado': float(ii_match.group(1).replace('.', '').replace(',', '.')),
                'a_reduzir': float(ii_match.group(2).replace('.', '').replace(',', '.')),
                'devido': float(ii_match.group(3).replace('.', '').replace(',', '.')),
                'suspenso': float(ii_match.group(4).replace('.', '').replace(',', '.')),
                'a_recolher': float(ii_match.group(5).replace('.', '').replace(',', '.'))
            }
        
        # Padrão para PIS
        pis_match = re.search(r'PIS\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', self.pdf_text)
        if pis_match:
            self.data['tributos_totais']['PIS'] = {
                'calculado': float(pis_match.group(1).replace('.', '').replace(',', '.')),
                'a_reduzir': float(pis_match.group(2).replace('.', '').replace(',', '.')),
                'devido': float(pis_match.group(3).replace('.', '').replace(',', '.')),
                'suspenso': float(pis_match.group(4).replace('.', '').replace(',', '.')),
                'a_recolher': float(pis_match.group(5).replace('.', '').replace(',', '.'))
            }
        
        # Padrão para COFINS
        cofins_match = re.search(r'COFINS\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', self.pdf_text)
        if cofins_match:
            self.data['tributos_totais']['COFINS'] = {
                'calculado': float(cofins_match.group(1).replace('.', '').replace(',', '.')),
                'a_reduzir': float(cofins_match.group(2).replace('.', '').replace(',', '.')),
                'devido': float(cofins_match.group(3).replace('.', '').replace(',', '.')),
                'suspenso': float(cofins_match.group(4).replace('.', '').replace(',', '.')),
                'a_recolher': float(cofins_match.group(5).replace('.', '').replace(',', '.'))
            }
        
        # Taxa de utilização
        taxa_match = re.search(r'TAXA DE UTILIZACAO\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', self.pdf_text)
        if taxa_match:
            self.data['tributos_totais']['TAXA_UTILIZACAO'] = {
                'calculado': float(taxa_match.group(1).replace('.', '').replace(',', '.')),
                'a_reduzir': float(taxa_match.group(2).replace('.', '').replace(',', '.')),
                'devido': float(taxa_match.group(3).replace('.', '').replace(',', '.')),
                'suspenso': float(taxa_match.group(4).replace('.', '').replace(',', '.')),
                'a_recolher': float(taxa_match.group(5).replace('.', '').replace(',', '.'))
            }
    
    def _extract_dados_carga(self):
        """Extrai dados da carga"""
        patterns = {
            'via_transporte': r'Via de Transporte\s+(.+?)\n',
            'num_identificacao': r'Num\. Identificacao\s+(\d+)',
            'data_embarque': r'Data de Embarque\s+(\d{2}/\d{2}/\d{4})',
            'data_chegada': r'Data de Chegada\s+(\d{2}/\d{2}/\d{4})',
            'peso_bruto': r'Peso Bruto\s+([\d.,]+)',
            'peso_liquido': r'Peso Liquido\s+([\d.,]+)',
            'pais_procedencia': r'Pais de Procedencia\s+(.+?)\s*\n',
            'unidade_despacho': r'Unidade de Despacho\s+(.+?)\n',
            'recinto': r'Recinto\s+(.+?)\n',
            'unid_entrada': r'Unid Entrada/Descarga\s+(.+?)\n',
            'unid_destino': r'Unid Destino Final\s+(.+?)\n'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, self.pdf_text)
            if match:
                value = match.group(1).strip()
                # Converter para float se for número
                if key in ['peso_bruto', 'peso_liquido']:
                    value = float(value.replace(',', '.'))
                self.data['dados_carga'][key] = value
    
    def _extract_transportes(self):
        """Extrai informações de transporte"""
        # Tipo conhecimento
        tipo_match = re.search(r'Tipo Conhecimento\s+(.+?)\n', self.pdf_text)
        if tipo_match:
            self.data['transportes']['tipo_conhecimento'] = tipo_match.group(1).strip()
        
        # Bandeira embarcação
        bandeira_match = re.search(r'Bandeira Embarcacao\s+(.+?)\n', self.pdf_text)
        if bandeira_match:
            self.data['transportes']['bandeira_embarcacao'] = bandeira_match.group(1).strip()
        
        # Local embarque
        local_match = re.search(r'Local Embarque\s+(.+?)\n', self.pdf_text)
        if local_match:
            self.data['transportes']['local_embarque'] = local_match.group(1).strip()
        
        # Seguro
        seguro_match = re.search(r'SEGURO.*?Total \(Moeda\)\s+([\d.,]+).*?Total \(R\$\)\s+([\d.,]+)', self.pdf_text, re.DOTALL)
        if seguro_match:
            self.data['transportes']['seguro'] = {
                'valor_moeda': float(seguro_match.group(1).replace(',', '.')),
                'valor_brl': float(seguro_match.group(2).replace('.', '').replace(',', '.'))
            }
        
        # Frete
        frete_match = re.search(r'FRETE.*?Total \(Moeda\)\s+([\d.,]+).*?Total \(R\$\)\s+([\d.,]+)', self.pdf_text, re.DOTALL)
        if frete_match:
            self.data['transportes']['frete'] = {
                'valor_moeda': float(frete_match.group(1).replace(',', '.')),
                'valor_brl': float(frete_match.group(2).replace('.', '').replace(',', '.'))
            }
    
    def _extract_documentos(self):
        """Extrai documentos"""
        # Conhecimento de embarque
        ce_match = re.search(r'CONHECIMENTO DE EMBARQUE.*?NUMERO\s*(\d+)', self.pdf_text, re.IGNORECASE)
        if ce_match:
            self.data['documentos']['conhecimento_embarque'] = ce_match.group(1)
        
        # Fatura comercial
        fatura_match = re.search(r'FATURA COMERCIAL.*?NUMERO\s*(.+?)\s+VALOR', self.pdf_text, re.IGNORECASE)
        if fatura_match:
            self.data['documentos']['fatura_comercial'] = fatura_match.group(1).strip()
        
        # Valor fatura
        valor_match = re.search(r'VALOR US\$\s*([\d.,]+)', self.pdf_text)
        if valor_match:
            self.data['documentos']['valor_fatura_usd'] = float(valor_match.group(1).replace(',', '.'))
    
    def _extract_itens_detalhados(self):
        """Extrai dados detalhados de cada item - MELHORADO para capturar bases de cálculo"""
        # Encontrar todas as ocorrências de itens
        item_sections = re.finditer(r'ITENS DA DUIMP - (\d{5})', self.pdf_text)
        
        for match in item_sections:
            item_start = match.start()
            item_num = match.group(1)
            
            # Encontrar fim da seção do item (próximo item ou fim)
            next_item = re.search(r'ITENS DA DUIMP - \d{5}', self.pdf_text[item_start + 1:])
            if next_item:
                item_end = item_start + next_item.start()
            else:
                item_end = len(self.pdf_text)
            
            item_text = self.pdf_text[item_start:item_end]
            
            # Extrair dados básicos do item
            item_data = self._extract_dados_basicos_item(item_text, item_num)
            
            # Extrair tributos detalhados do item (incluindo bases de cálculo)
            tributos_item = self._extract_tributos_item(item_text)
            item_data['tributos_detalhados'] = tributos_item
            
            self.data['itens'].append(item_data)
    
    def _extract_dados_basicos_item(self, item_text: str, item_num: str) -> Dict[str, Any]:
        """Extrai dados básicos de um item"""
        item_data = {
            'item_numero': item_num,
            'tributos': {}
        }
        
        # NCM
        ncm_match = re.search(r'NCM\s*(\d{4}\.\d{2}\.\d{2})', item_text)
        if ncm_match:
            item_data['ncm'] = ncm_match.group(1)
        
        # Código do produto
        codigo_match = re.search(r'Codigo Produto\s*(\d+)', item_text)
        if codigo_match:
            item_data['codigo_produto'] = codigo_match.group(1)
        
        # Denominação
        denom_match = re.search(r'DENOMINACAO DO PRODUTO\s+(.+?)\s+DESCRICAO', item_text, re.DOTALL)
        if denom_match:
            item_data['denominacao'] = denom_match.group(1).strip()
        
        # Descrição
        desc_match = re.search(r'DESCRICAO DO PRODUTO\s+(.+?)\s+CÓDIGO INTERNO', item_text, re.DOTALL)
        if desc_match:
            item_data['descricao'] = desc_match.group(1).strip()
        
        # Código interno
        cod_int_match = re.search(r'Código interno\s+(\d+\.\d+\.\d+)', item_text)
        if cod_int_match:
            item_data['codigo_interno'] = cod_int_match.group(1)
        
        # Condição de venda
        cond_match = re.search(r'Cond\. Venda\s+(EXW|FOB|CIF|etc)', item_text)
        if cond_match:
            item_data['condicao_venda'] = cond_match.group(1)
        
        # Quantidade comercial
        qtd_match = re.search(r'Qtde Unid\. Comercial\s+([\d.,]+)', item_text)
        if qtd_match:
            item_data['quantidade_comercial'] = float(qtd_match.group(1).replace(',', '.'))
        
        # Unidade comercial
        unid_match = re.search(r'Unidade Comercial\s+(.+?)\s', item_text)
        if unid_match:
            item_data['unidade_comercial'] = unid_match.group(1).strip()
        
        # Peso líquido
        peso_match = re.search(r'Peso Líquido \(KG\)\s+([\d.,]+)', item_text)
        if peso_match:
            item_data['peso_liquido_kg'] = float(peso_match.group(1).replace(',', '.'))
        
        # Moeda negociada
        moeda_match = re.search(r'Moeda Negociada\s+(.+?)\s', item_text)
        if moeda_match:
            item_data['moeda_negociada'] = moeda_match.group(1).strip()
        
        # Valor unitário
        valor_unit_match = re.search(r'Valor Unit Cond Venda\s+([\d.,]+)', item_text)
        if valor_unit_match:
            item_data['valor_unitario'] = float(valor_unit_match.group(1).replace(',', '.'))
        
        # Valor total
        valor_total_match = re.search(r'Valor Tot\. Cond Venda\s+([\d.,]+)', item_text)
        if valor_total_match:
            item_data['valor_total'] = float(valor_total_match.group(1).replace(',', '.'))
        
        # CFOP
        cfop_match = re.search(r'CFOP\s+(\d+)\s+-\s+(.+)', item_text)
        if cfop_match:
            item_data['cfop'] = {
                'codigo': cfop_match.group(1),
                'descricao': cfop_match.group(2).strip()
            }
        
        return item_data
    
    def _extract_tributos_item(self, item_text: str) -> Dict[str, Any]:
        """Extrai tributos detalhados de um item, incluindo bases de cálculo"""
        tributos = {}
        
        # Padrão para extrair cada tributo com sua base de cálculo
        # Buscar por cada tipo de tributo
        tributo_patterns = {
            'II': r'II.*?Base de Cálculo \(R\$\)\s+([\d.,]+).*?Valor Devido \(R\$\)\s+([\d.,]+)',
            'IPI': r'IPI.*?Base de Cálculo \(R\$\)\s+([\d.,]+).*?Valor Devido \(R\$\)\s+([\d.,]+)',
            'PIS': r'PIS.*?Base de Cálculo \(R\$\)\s+([\d.,]+).*?Valor Devido \(R\$\)\s+([\d.,]+)',
            'COFINS': r'COFINS.*?Base de Cálculo \(R\$\)\s+([\d.,]+).*?Valor Devido \(R\$\)\s+([\d.,]+)'
        }
        
        for tributo, pattern in tributo_patterns.items():
            match = re.search(pattern, item_text, re.DOTALL | re.IGNORECASE)
            if match:
                base_calculo = float(match.group(1).replace('.', '').replace(',', '.'))
                valor_devido = float(match.group(2).replace('.', '').replace(',', '.'))
                
                tributos[tributo] = {
                    'base_calculo': base_calculo,
                    'valor_devido': valor_devido,
                    'aliquota': (valor_devido / base_calculo * 100) if base_calculo > 0 else 0
                }
        
        # Extrair também do resumo geral se disponível
        resumo_pattern = r'Local Aduaneiro \(R\$\)\s+([\d.,]+)'
        resumo_match = re.search(resumo_pattern, item_text)
        if resumo_match:
            tributos['valor_aduaneiro'] = float(resumo_match.group(1).replace('.', '').replace(',', '.'))
        
        return tributos
    
    def _calcular_resumo_geral(self):
        """Calcula resumo geral dos dados"""
        # Total de itens
        self.data['resumo_geral']['total_itens'] = len(self.data['itens'])
        
        # Soma de valores
        total_valor = sum(item.get('valor_total', 0) for item in self.data['itens'])
        self.data['resumo_geral']['valor_total_itens_eur'] = total_valor
        
        # Converter para BRL usando cotação
        cotacao = self.data['moedas_cotacoes'].get('moeda_negociada', {}).get('cotacao', 6.3085)
        self.data['resumo_geral']['valor_total_itens_brl'] = total_valor * cotacao
        
        # Total de tributos
        total_tributos = 0
        for item in self.data['itens']:
            tributos = item.get('tributos_detalhados', {})
            for tributo in ['II', 'PIS', 'COFINS']:
                if tributo in tributos:
                    total_tributos += tributos[tributo].get('valor_devido', 0)
        
        self.data['resumo_geral']['total_tributos'] = total_tributos

# ============================================================================
# MÓDULO DE VISUALIZAÇÃO E UI (DESENVOLVEDOR SÊNIOR)
# ============================================================================

class DataVisualizer:
    """Classe para criar visualizações e interface do usuário"""
    
    @staticmethod
    def create_header():
        """Cria cabeçalho da aplicação"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<h1 class="main-title">📊 ANALISADOR DE IMPORTAÇÃO HAFELE</h1>', unsafe_allow_html=True)
            st.markdown("""
            <div style="text-align: center; color: #6B7280; margin-bottom: 2rem;">
                <strong>Extração completa de dados de documentos de importação</strong><br>
                Processamento automático de PDFs no layout padrão
            </div>
            """, unsafe_allow_html=True)
    
    @staticmethod
    def create_sidebar() -> Dict[str, Any]:
        """Cria sidebar com controles"""
        with st.sidebar:
            # Logo
            st.image("https://cdn-icons-png.flaticon.com/512/3710/3710277.png", width=100)
            
            st.markdown("### 📤 Upload do Documento")
            uploaded_file = st.file_uploader(
                "Carregar PDF de Importação",
                type=['pdf'],
                help="Selecione o documento no formato padrão"
            )
            
            st.markdown("---")
            st.markdown("### ⚙️ Configurações")
            
            # Opções de exibição
            exibir_tributos_detalhados = st.checkbox("Exibir Tributos Detalhados", value=True)
            exibir_graficos = st.checkbox("Exibir Gráficos", value=True)
            exibir_dados_brutos = st.checkbox("Exibir Dados Brutos", value=False)
            
            st.markdown("---")
            st.markdown("### 💾 Exportação")
            
            formato_export = st.selectbox(
                "Formato de Exportação",
                ["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"]
            )
            
            return {
                'uploaded_file': uploaded_file,
                'exibir_tributos_detalhados': exibir_tributos_detalhados,
                'exibir_graficos': exibir_graficos,
                'exibir_dados_brutos': exibir_dados_brutos,
                'formato_export': formato_export
            }
    
    @staticmethod
    def extract_text_from_pdf(uploaded_file) -> str:
        """Extrai texto do PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            st.error(f"Erro ao ler PDF: {str(e)}")
            return ""
    
    @staticmethod
    def display_general_info(data: Dict[str, Any]):
        """Exibe informações gerais"""
        st.markdown('<h3 class="sub-title">📋 INFORMAÇÕES GERAIS DO PROCESSO</h3>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Processo",
                data['informacoes_gerais'].get('processo', 'N/A'),
                "Importação"
            )
            
            st.metric(
                "DUIMP",
                data['informacoes_gerais'].get('duimp', 'N/A')
            )
        
        with col2:
            st.metric(
                "Importador",
                "HAFELE BRASIL",
                data['informacoes_gerais'].get('cnpj', 'N/A')
            )
            
            st.metric(
                "Responsável",
                data['informacoes_gerais'].get('responsavel', 'N/A')
            )
        
        with col3:
            st.metric(
                "Data Registro",
                data['informacoes_gerais'].get('data_registro', 'N/A')
            )
            
            st.metric(
                "Tipo",
                data['informacoes_gerais'].get('tipo', 'N/A')
            )
        
        with col4:
            cif_brl = data['valores_totais'].get('cif_brl', 0)
            st.metric(
                "Valor CIF (R$)",
                f"R$ {cif_brl:,.2f}",
                delta="Valor total da operação"
            )
    
    @staticmethod
    def display_moedas_cotacoes(data: Dict[str, Any]):
        """Exibe moedas e cotações"""
        st.markdown('<h3 class="sub-title">💱 MOEDAS E COTAÇÕES</h3>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        moedas = data.get('moedas_cotacoes', {})
        
        with col1:
            if 'moeda_negociada' in moedas:
                st.markdown("""
                <div class="metric-card">
                    <h4>💰 Moeda Negociada</h4>
                    <p><strong>{nome}</strong> (Código: {codigo})</p>
                    <h3>R$ {cotacao:,.4f}</h3>
                </div>
                """.format(**moedas['moeda_negociada']), unsafe_allow_html=True)
        
        with col2:
            if 'moeda_frete' in moedas:
                st.markdown("""
                <div class="metric-card">
                    <h4>🚚 Moeda do Frete</h4>
                    <p><strong>{nome}</strong> (Código: {codigo})</p>
                    <h3>R$ {cotacao:,.4f}</h3>
                </div>
                """.format(**moedas['moeda_frete']), unsafe_allow_html=True)
        
        with col3:
            if 'moeda_seguro' in moedas:
                st.markdown("""
                <div class="metric-card">
                    <h4>🛡️ Moeda do Seguro</h4>
                    <p><strong>{nome}</strong> (Código: {codigo})</p>
                    <h3>R$ {cotacao:,.4f}</h3>
                </div>
                """.format(**moedas['moeda_seguro']), unsafe_allow_html=True)
    
    @staticmethod
    def display_valores_totais(data: Dict[str, Any]):
        """Exibe valores totais"""
        st.markdown('<h3 class="sub-title">💰 VALORES TOTAIS</h3>', unsafe_allow_html=True)
        
        valores = data.get('valores_totais', {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "VMLE (R$)",
                f"R$ {valores.get('vmle_brl', 0):,.2f}",
                f"US$ {valores.get('vmle_usd', 0):,.2f}"
            )
        
        with col2:
            st.metric(
                "VMLD (R$)",
                f"R$ {valores.get('vmld_brl', 0):,.2f}",
                f"US$ {valores.get('vmld_usd', 0):,.2f}"
            )
        
        with col3:
            st.metric(
                "CIF (R$)",
                f"R$ {valores.get('cif_brl', 0):,.2f}",
                f"US$ {valores.get('cif_usd', 0):,.2f}"
            )
    
    @staticmethod
    def display_tributos_totais(data: Dict[str, Any]):
        """Exibe tributos totais"""
        st.markdown('<h3 class="sub-title">🏛️ TRIBUTOS TOTAIS</h3>', unsafe_allow_html=True)
        
        tributos = data.get('tributos_totais', {})
        
        if not tributos:
            st.warning("Nenhuma informação de tributos encontrada.")
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'II' in tributos:
                st.markdown(f"""
                <div class="tax-card">
                    <h4>🛃 II</h4>
                    <h3>R$ {tributos['II']['a_recolher']:,.2f}</h3>
                    <p>Devido: R$ {tributos['II']['devido']:,.2f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if 'PIS' in tributos:
                st.markdown(f"""
                <div class="tax-card">
                    <h4>🏛️ PIS</h4>
                    <h3>R$ {tributos['PIS']['a_recolher']:,.2f}</h3>
                    <p>Devido: R$ {tributos['PIS']['devido']:,.2f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            if 'COFINS' in tributos:
                st.markdown(f"""
                <div class="tax-card">
                    <h4>🏛️ COFINS</h4>
                    <h3>R$ {tributos['COFINS']['a_recolher']:,.2f}</h3>
                    <p>Devido: R$ {tributos['COFINS']['devido']:,.2f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col4:
            if 'TAXA_UTILIZACAO' in tributos:
                st.markdown(f"""
                <div class="tax-card">
                    <h4>📋 Taxa Siscomex</h4>
                    <h3>R$ {tributos['TAXA_UTILIZACAO']['a_recolher']:,.2f}</h3>
                    <p>Devido: R$ {tributos['TAXA_UTILIZACAO']['devido']:,.2f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Total geral
        total = sum(t['a_recolher'] for t in tributos.values())
        st.metric(
            "TOTAL DE TRIBUTOS A RECOLHER",
            f"R$ {total:,.2f}",
            delta="Soma de todos os impostos"
        )
    
    @staticmethod
    def display_dados_carga(data: Dict[str, Any]):
        """Exibe dados da carga"""
        st.markdown('<h3 class="sub-title">🚚 DADOS DA CARGA</h3>', unsafe_allow_html=True)
        
        carga = data.get('dados_carga', {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown("#### 📦 Informações de Transporte")
            st.write(f"**Via:** {carga.get('via_transporte', 'N/A')}")
            st.write(f"**Nº Identificação:** {carga.get('num_identificacao', 'N/A')}")
            st.write(f"**Local Embarque:** {data.get('transportes', {}).get('local_embarque', 'N/A')}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown("#### 📅 Datas")
            st.write(f"**Data Embarque:** {carga.get('data_embarque', 'N/A')}")
            st.write(f"**Data Chegada:** {carga.get('data_chegada', 'N/A')}")
            
            # Calcular prazo
            if 'data_embarque' in carga and 'data_chegada' in carga:
                try:
                    emb = datetime.strptime(carga['data_embarque'], '%d/%m/%Y')
                    cheg = datetime.strptime(carga['data_chegada'], '%d/%m/%Y')
                    dias = (cheg - emb).days
                    st.write(f"**Prazo Transporte:** {dias} dias")
                except:
                    pass
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown("#### ⚖️ Pesos e Medidas")
            st.write(f"**Peso Bruto:** {carga.get('peso_bruto', 0):.3f} kg")
            st.write(f"**Peso Líquido:** {carga.get('peso_liquido', 0):.3f} kg")
            st.write(f"**País Origem:** {carga.get('pais_procedencia', 'N/A')}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def display_itens_detalhados(data: Dict[str, Any], exibir_tributos_detalhados: bool = True):
        """Exibe itens detalhados com tributos"""
        st.markdown('<h3 class="sub-title">📦 ITENS DA IMPORTACAO</h3>', unsafe_allow_html=True)
        
        itens = data.get('itens', [])
        
        if not itens:
            st.warning("Nenhum item encontrado no documento.")
            return
        
        # Criar DataFrame para exibição
        items_data = []
        for item in itens:
            # Dados básicos
            item_dict = {
                'Item': item.get('item_numero', ''),
                'NCM': item.get('ncm', ''),
                'Código': item.get('codigo_interno', ''),
                'Descrição': (item.get('denominacao', '')[:50] + '...' 
                            if len(item.get('denominacao', '')) > 50 
                            else item.get('denominacao', '')),
                'Qtd': f"{item.get('quantidade_comercial', 0):.0f}",
                'Unid': item.get('unidade_comercial', ''),
                'Valor Unit (€)': f"€ {item.get('valor_unitario', 0):,.2f}",
                'Valor Total (€)': f"€ {item.get('valor_total', 0):,.2f}",
                'Peso (kg)': f"{item.get('peso_liquido_kg', 0):,.3f}"
            }
            
            # Adicionar tributos se solicitado
            if exibir_tributos_detalhados:
                tributos = item.get('tributos_detalhados', {})
                
                for tributo in ['II', 'PIS', 'COFINS']:
                    if tributo in tributos:
                        item_dict[f'{tributo} Base'] = f"R$ {tributos[tributo]['base_calculo']:,.2f}"
                        item_dict[f'{tributo} Devido'] = f"R$ {tributos[tributo]['valor_devido']:,.2f}"
                        item_dict[f'{tributo} %'] = f"{tributos[tributo]['aliquota']:.2f}%"
            
            items_data.append(item_dict)
        
        df = pd.DataFrame(items_data)
        
        # Exibir tabela
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Descrição": st.column_config.TextColumn(width="medium"),
                "Valor Unit (€)": st.column_config.NumberColumn(format="€ %.2f"),
                "Valor Total (€)": st.column_config.NumberColumn(format="€ %.2f")
            }
        )
        
        # Estatísticas rápidas
        st.markdown('<div class="section-title">📊 Estatísticas dos Itens</div>', unsafe_allow_html=True)
        
        total_itens = len(itens)
        total_valor_eur = sum(item.get('valor_total', 0) for item in itens)
        total_peso = sum(item.get('peso_liquido_kg', 0) for item in itens)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Itens", total_itens)
        with col2:
            st.metric("Valor Total (€)", f"€ {total_valor_eur:,.2f}")
        with col3:
            st.metric("Peso Total", f"{total_peso:,.3f} kg")
    
    @staticmethod
    def create_tax_visualizations(data: Dict[str, Any]):
        """Cria visualizações dos tributos"""
        itens = data.get('itens', [])
        
        if not itens:
            return
        
        st.markdown('<div class="section-title">📈 Visualizações dos Tributos</div>', unsafe_allow_html=True)
        
        # Preparar dados para gráficos
        tax_data = []
        for item in itens:
            item_num = item.get('item_numero', '')
            tributos = item.get('tributos_detalhados', {})
            
            for tributo_name, tributo_info in tributos.items():
                if isinstance(tributo_info, dict):
                    tax_data.append({
                        'Item': f"Item {item_num}",
                        'Tributo': tributo_name,
                        'Base Calculo (R$)': tributo_info.get('base_calculo', 0),
                        'Valor Devido (R$)': tributo_info.get('valor_devido', 0),
                        'Alíquota (%)': tributo_info.get('aliquota', 0)
                    })
        
        if not tax_data:
            return
        
        df_tax = pd.DataFrame(tax_data)
        
        # Gráfico 1: Valor devido por tributo
        col1, col2 = st.columns(2)
        
        with col1:
            if not df_tax.empty:
                fig1 = px.bar(
                    df_tax,
                    x='Item',
                    y='Valor Devido (R$)',
                    color='Tributo',
                    title='💰 Valor Devido por Item e Tributo',
                    barmode='group',
                    text='Valor Devido (R$)'
                )
                fig1.update_traces(texttemplate='R$%{text:,.0f}', textposition='outside')
                fig1.update_layout(height=400)
                st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Agrupar por tributo
            if not df_tax.empty:
                tax_summary = df_tax.groupby('Tributo')['Valor Devido (R$)'].sum().reset_index()
                fig2 = px.pie(
                    tax_summary,
                    values='Valor Devido (R$)',
                    names='Tributo',
                    title='🥧 Distribuição dos Tributos',
                    hole=0.4
                )
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
    
    @staticmethod
    def display_documentos(data: Dict[str, Any]):
        """Exibe documentos"""
        st.markdown('<h3 class="sub-title">📄 DOCUMENTOS</h3>', unsafe_allow_html=True)
        
        docs = data.get('documentos', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown("#### 📋 Documentos Instruídos")
            st.write(f"**Conhecimento:** {docs.get('conhecimento_embarque', 'N/A')}")
            st.write(f"**Fatura:** {docs.get('fatura_comercial', 'N/A')}")
            st.write(f"**Valor Fatura:** US$ {docs.get('valor_fatura_usd', 0):,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown("#### 🚢 Transporte")
            transportes = data.get('transportes', {})
            st.write(f"**Tipo Conhecimento:** {transportes.get('tipo_conhecimento', 'N/A')}")
            st.write(f"**Bandeira:** {transportes.get('bandeira_embarcacao', 'N/A')}")
            
            if 'frete' in transportes:
                st.write(f"**Frete:** R$ {transportes['frete']['valor_brl']:,.2f}")
            if 'seguro' in transportes:
                st.write(f"**Seguro:** R$ {transportes['seguro']['valor_brl']:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def create_export_button(data: Dict[str, Any], formato: str):
        """Cria botão para exportar dados"""
        if not data:
            return
        
        if formato == "Excel (.xlsx)":
            # Preparar dados para Excel
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Sheet 1: Itens
                items_data = []
                for item in data.get('itens', []):
                    items_data.append({
                        'Item': item.get('item_numero', ''),
                        'NCM': item.get('ncm', ''),
                        'Código Interno': item.get('codigo_interno', ''),
                        'Descrição': item.get('denominacao', ''),
                        'Quantidade': item.get('quantidade_comercial', 0),
                        'Unidade': item.get('unidade_comercial', ''),
                        'Valor Unitário (€)': item.get('valor_unitario', 0),
                        'Valor Total (€)': item.get('valor_total', 0),
                        'Valor Total (R$)': item.get('valor_total', 0) * 6.3085,
                        'Peso (kg)': item.get('peso_liquido_kg', 0)
                    })
                
                if items_data:
                    df_items = pd.DataFrame(items_data)
                    df_items.to_excel(writer, sheet_name='Itens', index=False)
                
                # Sheet 2: Tributos
                tax_data = []
                for item in data.get('itens', []):
                    tributos = item.get('tributos_detalhados', {})
                    for tax_name, tax_info in tributos.items():
                        if isinstance(tax_info, dict):
                            tax_data.append({
                                'Item': item.get('item_numero', ''),
                                'Tributo': tax_name,
                                'Base Calculo (R$)': tax_info.get('base_calculo', 0),
                                'Valor Devido (R$)': tax_info.get('valor_devido', 0),
                                'Alíquota (%)': tax_info.get('aliquota', 0)
                            })
                
                if tax_data:
                    df_tax = pd.DataFrame(tax_data)
                    df_tax.to_excel(writer, sheet_name='Tributos', index=False)
                
                # Sheet 3: Resumo
                summary_data = [{
                    'Processo': data['informacoes_gerais'].get('processo', ''),
                    'DUIMP': data['informacoes_gerais'].get('duimp', ''),
                    'Data Registro': data['informacoes_gerais'].get('data_registro', ''),
                    'Total Itens': len(data.get('itens', [])),
                    'Valor Total (€)': sum(item.get('valor_total', 0) for item in data.get('itens', [])),
                    'Valor Total (R$)': sum(item.get('valor_total', 0) for item in data.get('itens', [])) * 6.3085,
                    'Total Tributos (R$)': data['resumo_geral'].get('total_tributos', 0)
                }]
                
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Resumo', index=False)
            
            output.seek(0)
            
            st.download_button(
                label="📥 Baixar Excel Completo",
                data=output,
                file_name=f"importacao_{data['informacoes_gerais'].get('processo', '')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# ============================================================================
# APLICAÇÃO PRINCIPAL
# ============================================================================

def main():
    """Função principal da aplicação"""
    
    # Inicializar visualizador
    visualizer = DataVisualizer()
    
    # Criar cabeçalho
    visualizer.create_header()
    
    # Criar sidebar e obter configurações
    config = visualizer.create_sidebar()
    
    # Verificar se há arquivo carregado
    if config['uploaded_file'] is not None:
        try:
            # Extrair texto do PDF
            with st.spinner("📄 Processando documento..."):
                pdf_text = visualizer.extract_text_from_pdf(config['uploaded_file'])
            
            if pdf_text:
                # Processar dados
                with st.spinner("🔍 Extraindo dados..."):
                    extractor = PDFDataExtractor(pdf_text)
                    data = extractor.extract_all_data()
                
                # Exibir mensagem de sucesso
                st.success(f"✅ Documento processado com sucesso! {len(data.get('itens', []))} itens encontrados.")
                
                # Criar abas para organização
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📋 Resumo", 
                    "💰 Tributos", 
                    "📦 Itens", 
                    "🚚 Logística", 
                    "💾 Exportar"
                ])
                
                with tab1:
                    # Resumo Geral
                    visualizer.display_general_info(data)
                    visualizer.display_moedas_cotacoes(data)
                    visualizer.display_valores_totais(data)
                    visualizer.display_dados_carga(data)
                
                with tab2:
                    # Tributos
                    visualizer.display_tributos_totais(data)
                    if config['exibir_graficos']:
                        visualizer.create_tax_visualizations(data)
                
                with tab3:
                    # Itens
                    visualizer.display_itens_detalhados(data, config['exibir_tributos_detalhados'])
                
                with tab4:
                    # Logística
                    visualizer.display_documentos(data)
                
                with tab5:
                    # Exportação
                    st.markdown('<h3 class="sub-title">💾 EXPORTAR DADOS</h3>', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        visualizer.create_export_button(data, config['formato_export'])
                    
                    with col2:
                        # Mostrar dados brutos se solicitado
                        if config['exibir_dados_brutos']:
                            with st.expander("📊 Ver Dados Brutos Extraídos"):
                                st.json(data)
        except Exception as e:
            st.error(f"❌ Erro ao processar documento: {str(e)}")
    else:
        # Tela inicial
        st.info("👆 **Por favor, faça upload de um documento PDF no formato padrão.**")
        
        col1, col2, col3 = st.columns(3)
        
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <h3>📋 Informações que serão extraídas:</h3>
                <p>✅ Dados do processo e importador</p>
                <p>✅ Moedas e cotações</p>
                <p>✅ Valores totais (CIF, VMLE, VMLD)</p>
                <p>✅ Tributos detalhados (II, PIS, COFINS)</p>
                <p>✅ Itens com NCM, valores e tributos</p>
                <p>✅ Documentos e informações logísticas</p>
                <p>✅ Bases de cálculo de cada tributo</p>
            </div>
            """, unsafe_allow_html=True)

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    main()
