# -*- coding: utf-8 -*-
"""
ANALISADOR INTELIGENTE DE DOCUMENTOS DE IMPORTAÇÃO
Streamlit App - Versão Completa
Integração: Cientista de Dados + Desenvolvedor Sênior
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
from typing import Dict, List, Any, Optional

# ============================================================================
# 1. MÓDULO DO CIENTISTA DE DADOS (EXTRATOR DE DADOS)
# ============================================================================

class PDFDataScientist:
    """
    Módulo avançado de extração e análise de dados de PDFs de importação.
    Utiliza técnicas de processamento de linguagem natural e regex avançado.
    """
    
    def __init__(self, pdf_text: str):
        self.pdf_text = pdf_text
        self.raw_data = {}
        self.processed_data = {}
        self.analytics = {}
        
    def _clean_text(self, text: str) -> str:
        """Limpa e normaliza o texto"""
        text = re.sub(r'\s+', ' ', text)  # Remove múltiplos espaços
        text = re.sub(r'\n+', ' ', text)  # Remove múltiplas quebras
        return text.strip()
    
    def extract_structured_data(self) -> Dict[str, Any]:
        """Extrai dados estruturados usando múltiplas estratégias"""
        
        # Estratégia 1: Regex para informações gerais
        patterns = {
            'processo': (r'PROCESSO\s*#\s*(\d+)', 'Número do processo'),
            'duimp': (r'Numero\s+(\d{2}BR\d+)', 'Número da DUIMP'),
            'importador': (r'IMPORTADOR\s+(.+?)\s+CNPJ', 'Nome do importador'),
            'cnpj': (r'CNPJ\s+(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', 'CNPJ'),
            'data_registro': (r'Data Registro\s+(\d{2}/\d{2}/\d{4})', 'Data de registro'),
            'cotacao_euro': (r'Moeda Negociada.*?Cotacao\s+([\d,]+)', 'Cotação do Euro'),
            'cotacao_dolar': (r'Moeda Seguro.*?Cotacao\s+([\d,]+)', 'Cotação do Dólar'),
            'cif_reais': (r'CIF\s*\(R\$\)\s*([\d.,]+)', 'Valor CIF em reais'),
            'cif_usd': (r'CIF\s*\(\$\)\s*([\d.,]+)', 'Valor CIF em dólar'),
            'pais_origem': (r'Pais de Procedencia\s+(.+?)\s*\(', 'País de origem'),
            'porto': (r'PORTO DE\s+(.+?)[\s\n]', 'Porto de destino'),
            'data_embarque': (r'Data de Embarque\s+(\d{2}/\d{2}/\d{4})', 'Data de embarque'),
            'data_chegada': (r'Data de Chegada\s+(\d{2}/\d{2}/\d{4})', 'Data de chegada'),
            'peso_bruto': (r'Peso Bruto\s+([\d.,]+)', 'Peso bruto (kg)'),
            'peso_liquido': (r'Peso Liquido\s+([\d.,]+)', 'Peso líquido (kg)'),
        }
        
        extracted = {}
        for key, (pattern, description) in patterns.items():
            match = re.search(pattern, self.pdf_text, re.IGNORECASE)
            if match:
                extracted[key] = {
                    'valor': match.group(1),
                    'descricao': description
                }
        
        self.raw_data['geral'] = extracted
        
        # Estratégia 2: Extração de itens usando delimitadores conhecidos
        self._extract_items_data()
        
        # Estratégia 3: Extração de tributos
        self._extract_taxes_data()
        
        # Estratégia 4: Extração de documentos
        self._extract_documents_data()
        
        return self.raw_data
    
    def _extract_items_data(self):
        """Extrai dados dos itens da importação"""
        items_section = re.search(r'ITENS DA DUIMP.*?(?=INFORMACOES COMPLEMENTARES|\Z)', 
                                 self.pdf_text, re.DOTALL | re.IGNORECASE)
        
        if not items_section:
            return
        
        items_text = items_section.group(0)
        
        # Padrão para encontrar cada item
        item_patterns = [
            # Padrão 1: Com header de tabela
            (r'ITENS DA DUIMP - (\d{5}).*?DENOMINACAO DO PRODUTO\s+(.+?)\s+DESCRICAO DO PRODUTO\s+(.+?)\s+CÓDIGO INTERNO.*?(\d+\.\d+\.\d+)', 
             ['item_num', 'denominacao', 'descricao', 'codigo']),
            
            # Padrão 2: Com NCM
            (r'NCM\s*(\d{4}\.\d{2}\.\d{2}).*?Valor Unit Cond Venda\s*([\d.,]+).*?Valor Tot\. Cond Venda\s*([\d.,]+)', 
             ['ncm', 'valor_unit', 'valor_total']),
            
            # Padrão 3: Com quantidades
            (r'Qtde Unid\. Comercial\s*([\d.,]+).*?Unidade Comercial\s*(.+?)\s', 
             ['quantidade', 'unidade']),
        ]
        
        items = []
        current_item = {}
        
        lines = items_text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Detectar início de novo item
            if 'ITENS DA DUIMP -' in line:
                if current_item:
                    items.append(current_item)
                current_item = {}
                match = re.search(r'ITENS DA DUIMP - (\d{5})', line)
                if match:
                    current_item['item'] = match.group(1)
            
            # Extrair NCM
            elif 'NCM' in line and len(line.replace('NCM', '').strip()) >= 8:
                ncm = re.search(r'(\d{4}\.\d{2}\.\d{2})', line)
                if ncm:
                    current_item['ncm'] = ncm.group(1)
            
            # Extrair descrição
            elif 'DENOMINACAO DO PRODUTO' in line and i + 1 < len(lines):
                current_item['denominacao'] = lines[i + 1].strip()
            
            # Extrair código interno
            elif 'Código interno' in line:
                codigo = re.search(r'(\d+\.\d+\.\d+)', line)
                if codigo:
                    current_item['codigo_interno'] = codigo.group(1)
            
            # Extrair valores
            elif 'Valor Tot. Cond Venda' in line:
                valor = re.search(r'([\d.,]+)', line)
                if valor:
                    current_item['valor_total'] = float(valor.group(1).replace('.', '').replace(',', '.'))
            
            # Extrair quantidade
            elif 'Qtde Unid. Comercial' in line:
                qtd = re.search(r'([\d.,]+)', line)
                if qtd:
                    current_item['quantidade'] = float(qtd.group(1).replace('.', '').replace(',', '.'))
        
        if current_item:
            items.append(current_item)
        
        # Extrair tributos para cada item
        for item in items:
            item['tributos'] = self._extract_item_taxes(item.get('item', ''))
        
        self.raw_data['itens'] = items
    
    def _extract_item_taxes(self, item_num: str) -> Dict[str, float]:
        """Extrai tributos específicos para um item"""
        taxes = {}
        
        # Padrões de busca para tributos
        tax_patterns = {
            'II': (r'II[\s\S]*?Valor Devido \(R\$\)\s*([\d.,]+)', 'Imposto de Importação'),
            'PIS': (r'PIS[\s\S]*?Valor Devido \(R\$\)\s*([\d.,]+)', 'PIS Importação'),
            'COFINS': (r'COFINS[\s\S]*?Valor Devido \(R\$\)\s*([\d.,]+)', 'COFINS Importação'),
            'ICMS': (r'ICMS[\s\S]*?Valor Devido\s*([\d.,]+)', 'ICMS'),
        }
        
        # Buscar na área do item específico
        item_section = re.search(
            f'ITENS DA DUIMP - {item_num}.*?(?=ITENS DA DUIMP -|\Z)',
            self.pdf_text,
            re.DOTALL | re.IGNORECASE
        )
        
        if item_section:
            section_text = item_section.group(0)
            for tax_name, (pattern, desc) in tax_patterns.items():
                match = re.search(pattern, section_text)
                if match:
                    try:
                        value = float(match.group(1).replace('.', '').replace(',', '.'))
                        taxes[tax_name] = value
                    except:
                        taxes[tax_name] = 0.0
        
        return taxes
    
    def _extract_taxes_data(self):
        """Extrai dados de tributação"""
        taxes_section = re.search(
            r'CÁLCULOS DOS TRIBUTOS.*?(?=DADOS DA CARGA|VALORES TOTAIS)',
            self.pdf_text,
            re.DOTALL | re.IGNORECASE
        )
        
        taxes = {}
        if taxes_section:
            text = taxes_section.group(0)
            
            # Valores totais
            total_patterns = {
                'ii_total': r'II\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)',
                'pis_total': r'PIS\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)',
                'cofins_total': r'COFINS\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)',
                'taxa_siscomex': r'TAXA DE UTILIZACAO\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)',
            }
            
            for key, pattern in total_patterns.items():
                match = re.search(pattern, text)
                if match:
                    try:
                        taxes[key] = float(match.group(1).replace('.', '').replace(',', '.'))
                    except:
                        taxes[key] = 0.0
        
        self.raw_data['tributacao'] = taxes
    
    def _extract_documents_data(self):
        """Extrai dados dos documentos"""
        docs = {}
        
        # Conhecimento de embarque
        ce_match = re.search(r'CONHECIMENTO DE EMBARQUE.*?NUMERO[:]?\s*(\d+)', 
                           self.pdf_text, re.IGNORECASE)
        if ce_match:
            docs['conhecimento_embarque'] = ce_match.group(1)
        
        # Fatura comercial
        fatura_match = re.search(r'FATURA COMERCIAL.*?NUMERO\s*(.+?)\s', 
                               self.pdf_text, re.IGNORECASE)
        if fatura_match:
            docs['fatura_comercial'] = fatura_match.group(1)
        
        # Valor da fatura
        valor_match = re.search(r'VALOR US\$\s*([\d.,]+)', self.pdf_text)
        if valor_match:
            docs['valor_fatura_usd'] = valor_match.group(1)
        
        self.raw_data['documentos'] = docs
    
    def perform_analytics(self) -> Dict[str, Any]:
        """Realiza análises avançadas nos dados extraídos"""
        analytics = {}
        
        if 'itens' in self.raw_data:
            items = self.raw_data['itens']
            
            # Métricas básicas
            analytics['total_itens'] = len(items)
            analytics['total_valor_eur'] = sum(item.get('valor_total', 0) for item in items)
            analytics['total_quantidade'] = sum(item.get('quantidade', 0) for item in items)
            
            # Análise de tributos
            total_taxes = sum(
                sum(item.get('tributos', {}).values())
                for item in items
            )
            analytics['total_tributos'] = total_taxes
            
            if analytics['total_valor_eur'] > 0:
                analytics['taxa_tributaria_media'] = (
                    total_taxes / (analytics['total_valor_eur'] * 6.3085)
                ) * 100
            else:
                analytics['taxa_tributaria_media'] = 0
            
            # Distribuição por NCM
            ncm_dist = {}
            for item in items:
                ncm = item.get('ncm', 'Desconhecido')
                if ncm not in ncm_dist:
                    ncm_dist[ncm] = 0
                ncm_dist[ncm] += item.get('valor_total', 0)
            analytics['distribuicao_ncm'] = ncm_dist
            
            # Item mais caro
            if items:
                item_mais_caro = max(items, key=lambda x: x.get('valor_total', 0))
                analytics['item_mais_caro'] = {
                    'item': item_mais_caro.get('item'),
                    'valor': item_mais_caro.get('valor_total', 0),
                    'descricao': item_mais_caro.get('denominacao', '')
                }
        
        if 'tributacao' in self.raw_data:
            taxes = self.raw_data['tributacao']
            analytics['resumo_tributacao'] = {
                'total': sum(taxes.values()),
                'detalhado': taxes
            }
        
        self.analytics = analytics
        return analytics
    
    def generate_insights(self) -> List[str]:
        """Gera insights baseados nos dados extraídos"""
        insights = []
        
        if not self.analytics:
            self.perform_analytics()
        
        # Insight 1: Taxa tributária
        taxa = self.analytics.get('taxa_tributaria_media', 0)
        if taxa > 30:
            insights.append(f"⚠️ **Alta carga tributária**: {taxa:.1f}% do valor total")
        elif taxa < 15:
            insights.append(f"✅ **Carga tributária moderada**: {taxa:.1f}% do valor total")
        
        # Insight 2: Distribuição de valor
        if 'itens' in self.raw_data:
            items = self.raw_data['itens']
            if len(items) > 1:
                valores = [item.get('valor_total', 0) for item in items]
                variancia = np.var(valores)
                if variancia > 10000:
                    insights.append("📊 **Alta variância de valores** entre os itens")
                else:
                    insights.append("📊 **Valores distribuídos uniformemente** entre os itens")
        
        # Insight 3: Prazo de entrega
        if 'geral' in self.raw_data:
            geral = self.raw_data['geral']
            if 'data_embarque' in geral and 'data_chegada' in geral:
                try:
                    emb = datetime.strptime(geral['data_embarque']['valor'], '%d/%m/%Y')
                    cheg = datetime.strptime(geral['data_chegada']['valor'], '%d/%m/%Y')
                    dias = (cheg - emb).days
                    if dias > 60:
                        insights.append(f"⏳ **Prazo longo de transporte**: {dias} dias")
                    else:
                        insights.append(f"🚢 **Prazo normal de transporte**: {dias} dias")
                except:
                    pass
        
        return insights

# ============================================================================
# 2. MÓDULO DO DESENVOLVEDOR SÊNIOR (VISUALIZAÇÃO E UI)
# ============================================================================

class SeniorDeveloperUI:
    """
    Módulo de interface do usuário e visualização de dados.
    Responsável por criar uma experiência rica e interativa.
    """
    
    @staticmethod
    def setup_page_config():
        """Configura a página do Streamlit"""
        st.set_page_config(
            page_title="AI Import Analyzer",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    @staticmethod
    def apply_custom_css():
        """Aplica CSS customizado para melhorar a UI"""
        st.markdown("""
        <style>
            /* Estilos gerais */
            .main-title {
                font-size: 2.8rem;
                background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-align: center;
                margin-bottom: 1.5rem;
                font-weight: 800;
            }
            
            .sub-title {
                font-size: 1.8rem;
                color: #374151;
                border-bottom: 3px solid #3B82F6;
                padding-bottom: 0.5rem;
                margin-top: 2rem;
                margin-bottom: 1.5rem;
                font-weight: 600;
            }
            
            .card {
                background-color: white;
                border-radius: 10px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border: 1px solid #E5E7EB;
            }
            
            .metric-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 10px;
                padding: 1.5rem;
                text-align: center;
            }
            
            .insight-card {
                background-color: #F0F9FF;
                border-left: 5px solid #3B82F6;
                padding: 1rem;
                margin-bottom: 1rem;
                border-radius: 5px;
            }
            
            .warning-card {
                background-color: #FEF3C7;
                border-left: 5px solid #F59E0B;
                padding: 1rem;
                margin-bottom: 1rem;
                border-radius: 5px;
            }
            
            .success-card {
                background-color: #D1FAE5;
                border-left: 5px solid #10B981;
                padding: 1rem;
                margin-bottom: 1rem;
                border-radius: 5px;
            }
            
            /* Botões */
            .stButton > button {
                width: 100%;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.3s ease;
            }
            
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }
            
            /* Tabelas */
            .dataframe {
                border-radius: 8px;
                overflow: hidden;
            }
            
            /* Sidebar */
            .css-1d391kg {
                background-color: #F9FAFB;
            }
            
            /* Animações */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .fade-in {
                animation: fadeIn 0.5s ease-out;
            }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_header():
        """Cria o cabeçalho da aplicação"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<h1 class="main-title fade-in">📊 ANALISADOR INTELIGENTE DE IMPORTAÇÃO</h1>', 
                       unsafe_allow_html=True)
            st.markdown("""
            <div style="text-align: center; color: #6B7280; margin-bottom: 2rem;">
                <strong>CIENTISTA DE DADOS + DESENVOLVEDOR SÊNIOR INTEGRADOS</strong><br>
                Análise automática de documentos de importação
            </div>
            """, unsafe_allow_html=True)
    
    @staticmethod
    def create_sidebar() -> Dict[str, Any]:
        """Cria a sidebar com controles"""
        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/3710/3710277.png", 
                    width=100, use_container_width=True)
            
            st.markdown("### 🎯 Controles")
            
            # Upload de arquivo
            uploaded_file = st.file_uploader(
                "📤 Carregar PDF de Importação",
                type=['pdf'],
                help="Selecione o documento no formato padrão"
            )
            
            st.markdown("---")
            st.markdown("### 📊 Opções de Visualização")
            
            show_analytics = st.checkbox("Mostrar Análises Avançadas", value=True)
            show_charts = st.checkbox("Mostrar Gráficos Interativos", value=True)
            show_raw_data = st.checkbox("Mostrar Dados Brutos", value=False)
            
            st.markdown("---")
            st.markdown("### ⚙️ Configurações")
            
            currency = st.selectbox(
                "Moeda de Referência",
                ["BRL (Real)", "USD (Dólar)", "EUR (Euro)"]
            )
            
            tax_display = st.selectbox(
                "Formato de Tributos",
                ["Valores Absolutos", "Percentual", "Ambos"]
            )
            
            return {
                'uploaded_file': uploaded_file,
                'show_analytics': show_analytics,
                'show_charts': show_charts,
                'show_raw_data': show_raw_data,
                'currency': currency,
                'tax_display': tax_display
            }
    
    @staticmethod
    def create_visualizations(data: Dict[str, Any]) -> None:
        """Cria visualizações interativas dos dados"""
        
        if 'itens' not in data or not data['itens']:
            return
        
        items = data['itens']
        
        # Gráfico 1: Valor dos itens
        df_items = pd.DataFrame([
            {
                'Item': f"Item {item.get('item', 'N/A')}",
                'Valor (€)': item.get('valor_total', 0),
                'Valor (R$)': item.get('valor_total', 0) * 6.3085,
                'NCM': item.get('ncm', 'N/A'),
                'Quantidade': item.get('quantidade', 0)
            }
            for item in items
        ])
        
        if not df_items.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = px.bar(
                    df_items,
                    x='Item',
                    y='Valor (€)',
                    title='📈 Valor dos Itens (EUR)',
                    color='NCM',
                    text='Valor (€)',
                    hover_data=['Quantidade']
                )
                fig1.update_traces(texttemplate='€%{text:,.0f}', textposition='outside')
                fig1.update_layout(showlegend=True, height=400)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = px.pie(
                    df_items,
                    values='Valor (R$)',
                    names='Item',
                    title='🥧 Distribuição por Item',
                    hole=0.4
                )
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
            
            # Gráfico 3: Tributos por item
            st.markdown("---")
            st.markdown('<h3 class="sub-title">💰 Análise Tributária por Item</h3>', 
                       unsafe_allow_html=True)
            
            tax_data = []
            for item in items:
                item_num = item.get('item', 'N/A')
                tributos = item.get('tributos', {})
                for tax_name, tax_value in tributos.items():
                    tax_data.append({
                        'Item': f"Item {item_num}",
                        'Tributo': tax_name,
                        'Valor (R$)': tax_value
                    })
            
            if tax_data:
                df_tax = pd.DataFrame(tax_data)
                fig3 = px.bar(
                    df_tax,
                    x='Item',
                    y='Valor (R$)',
                    color='Tributo',
                    title='📊 Distribuição de Tributos',
                    barmode='group',
                    text='Valor (R$)'
                )
                fig3.update_traces(texttemplate='R$%{text:,.0f}')
                fig3.update_layout(height=500)
                st.plotly_chart(fig3, use_container_width=True)
    
    @staticmethod
    def display_general_info(data: Dict[str, Any]) -> None:
        """Exibe informações gerais do processo"""
        st.markdown('<h3 class="sub-title">📋 RESUMO DO PROCESSO</h3>', 
                   unsafe_allow_html=True)
        
        if 'geral' not in data:
            st.warning("Nenhuma informação geral encontrada.")
            return
        
        geral = data['geral']
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3>📄 Processo</h3>
                <h2>{}</h2>
            </div>
            """.format(geral.get('processo', {}).get('valor', 'N/A')), 
            unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <h3>🏢 Importador</h3>
                <h4>HAFELE BRASIL</h4>
                <p>{}</p>
            </div>
            """.format(geral.get('cnpj', {}).get('valor', 'N/A')), 
            unsafe_allow_html=True)
        
        with col3:
            cif_valor = geral.get('cif_reais', {}).get('valor', '0,00')
            st.markdown(f"""
            <div class="metric-card">
                <h3>💰 Valor CIF</h3>
                <h2>R$ {cif_valor}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            if 'itens' in data:
                total_itens = len(data['itens'])
                st.markdown(f"""
                <div class="metric-card">
                    <h3>📦 Total Itens</h3>
                    <h2>{total_itens}</h2>
                </div>
                """, unsafe_allow_html=True)
        
        # Informações detalhadas
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📋 Detalhes do Processo")
        
        info_cols = st.columns(4)
        
        with info_cols[0]:
            st.metric("DUIMP", geral.get('duimp', {}).get('valor', 'N/A'))
            st.metric("Data Registro", geral.get('data_registro', {}).get('valor', 'N/A'))
        
        with info_cols[1]:
            st.metric("País de Origem", geral.get('pais_origem', {}).get('valor', 'N/A'))
            st.metric("Porto", geral.get('porto', {}).get('valor', 'N/A'))
        
        with info_cols[2]:
            st.metric("Data Embarque", geral.get('data_embarque', {}).get('valor', 'N/A'))
            st.metric("Data Chegada", geral.get('data_chegada', {}).get('valor', 'N/A'))
        
        with info_cols[3]:
            peso_bruto = geral.get('peso_bruto', {}).get('valor', '0,00')
            peso_liquido = geral.get('peso_liquido', {}).get('valor', '0,00')
            st.metric("Peso Bruto", f"{peso_bruto} kg")
            st.metric("Peso Líquido", f"{peso_liquido} kg")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def display_items_table(data: Dict[str, Any]) -> None:
        """Exibe tabela detalhada dos itens"""
        st.markdown('<h3 class="sub-title">📦 ITENS DA IMPORTACAO</h3>', 
                   unsafe_allow_html=True)
        
        if 'itens' not in data or not data['itens']:
            st.warning("Nenhum item encontrado no documento.")
            return
        
        items = data['itens']
        
        # Preparar dados para a tabela
        table_data = []
        for item in items:
            valor_eur = item.get('valor_total', 0)
            valor_brl = valor_eur * 6.3085
            tributos = item.get('tributos', {})
            
            table_data.append({
                'Item': item.get('item', 'N/A'),
                'Código': item.get('codigo_interno', 'N/A'),
                'NCM': item.get('ncm', 'N/A'),
                'Descrição': item.get('denominacao', 'N/A')[:50] + 
                            ("..." if len(item.get('denominacao', '')) > 50 else ""),
                'Qtd': f"{item.get('quantidade', 0):.0f}",
                'Unidade': 'PEÇAS',
                'Valor €': f"€ {valor_eur:,.2f}",
                'Valor R$': f"R$ {valor_brl:,.2f}",
                'II (R$)': f"R$ {tributos.get('II', 0):,.2f}",
                'PIS (R$)': f"R$ {tributos.get('PIS', 0):,.2f}",
                'COFINS (R$)': f"R$ {tributos.get('COFINS', 0):,.2f}",
                'Total Trib. (R$)': f"R$ {sum(tributos.values()):,.2f}"
            })
        
        df = pd.DataFrame(table_data)
        
        # Exibir tabela com formatação
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Descrição": st.column_config.TextColumn(width="medium"),
                "Valor €": st.column_config.NumberColumn(format="€ %.2f"),
                "Valor R$": st.column_config.NumberColumn(format="R$ %.2f"),
                "II (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "PIS (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "COFINS (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Total Trib. (R$)": st.column_config.NumberColumn(format="R$ %.2f")
            }
        )
        
        # Estatísticas rápidas
        total_valor_eur = sum(item.get('valor_total', 0) for item in items)
        total_valor_brl = total_valor_eur * 6.3085
        total_tributos = sum(sum(item.get('tributos', {}).values()) for item in items)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Valor Total (EUR)", f"€ {total_valor_eur:,.2f}")
        with col2:
            st.metric("Valor Total (BRL)", f"R$ {total_valor_brl:,.2f}")
        with col3:
            st.metric("Total Tributos", f"R$ {total_tributos:,.2f}")
    
    @staticmethod
    def display_taxes_summary(data: Dict[str, Any]) -> None:
        """Exibe resumo da tributação"""
        st.markdown('<h3 class="sub-title">💰 RESUMO TRIBUTÁRIO</h3>', 
                   unsafe_allow_html=True)
        
        if 'tributacao' not in data:
            st.warning("Nenhuma informação de tributação encontrada.")
            return
        
        taxes = data['tributacao']
        
        # Cartões de métricas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🛃 Imposto de Importação</h3>
                <h2>R$ {taxes.get('ii_total', 0):,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🏛️ PIS Importação</h3>
                <h2>R$ {taxes.get('pis_total', 0):,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🏛️ COFINS Importação</h3>
                <h2>R$ {taxes.get('cofins_total', 0):,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📋 Taxa Siscomex</h3>
                <h2>R$ {taxes.get('taxa_siscomex', 0):,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # Gráfico de pizza
        total_tax = sum(taxes.values())
        if total_tax > 0:
            labels = ['II', 'PIS', 'COFINS', 'Taxa Siscomex']
            values = [
                taxes.get('ii_total', 0),
                taxes.get('pis
