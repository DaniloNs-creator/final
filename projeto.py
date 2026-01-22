import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Analisador de Documentos de Importação - Detalhado",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS customizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #374151;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E5E7EB;
    }
    .info-box {
        background-color: #F3F4F6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3B82F6;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 0.5rem;
    }
    .data-table {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .item-detail-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

class ImportationPDFParser:
    """Classe para analisar e extrair dados de PDFs de importação com detalhamento por item."""
    
    def __init__(self):
        self.data = {
            'processo_info': {},
            'resumo': {},
            'tributos_totais': {},
            'carga': {},
            'transporte': {},
            'itens_detalhados': [],  # Agora com mais detalhes
            'documentos': [],
            'valores': {},
            'cotacoes': {},
            'impostos_por_item': []
        }
    
    def extract_text_from_pdf(self, pdf_file):
        """Extrai texto de um arquivo PDF."""
        try:
            all_text = ""
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        # Adiciona número da página para referência
                        all_text += f"=== PÁGINA {page_num} ===\n{page_text}\n\n"
            return all_text
        except Exception as e:
            st.error(f"Erro ao ler PDF: {str(e)}")
            return ""
    
    def parse_processo_info(self, text):
        """Extrai informações do processo."""
        patterns = {
            'processo': r'PROCESSO\s*#(\d+)',
            'importador': r'IMPORTADOR\s*(.+?)\n',
            'cnpj': r'CNPJ\s*([\d\.\/\-]+)',
            'data_registro': r'Data Registro\s*(\d{2}/\d{2}/\d{4})',
            'responsavel': r'Responsavel Legal\s*(.+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                self.data['processo_info'][key] = match.group(1).strip()
    
    def parse_resumo(self, text):
        """Extrai informações do resumo."""
        # Valores CIF
        cif_pattern = r'CIF\s*\(US\$\)\s*([\d\.,]+)\s*CIF\s*\(R\$\)\s*([\d\.,]+)'
        cif_match = re.search(cif_pattern, text)
        if cif_match:
            self.data['resumo']['cif_usd'] = cif_match.group(1)
            self.data['resumo']['cif_brl'] = cif_match.group(2)
        
        # VMLE e VMLD
        vmle_pattern = r'VMLE\s*\(US\$\)\s*([\d\.,]+)\s*VMLE\s*\(R\$\)\s*([\d\.,]+)'
        vmle_match = re.search(vmle_pattern, text)
        if vmle_match:
            self.data['resumo']['vmle_usd'] = vmle_match.group(1)
            self.data['resumo']['vmle_brl'] = vmle_match.group(2)
        
        vml_pattern = r'VMLD\s*\(US\$\)\s*([\d\.,]+)\s*VMLD\s*\(R\$\)\s*([\d\.,]+)'
        vml_match = re.search(vml_pattern, text)
        if vml_match:
            self.data['resumo']['vmld_usd'] = vml_match.group(1)
            self.data['resumo']['vmld_brl'] = vml_match.group(2)
    
    def parse_tributos_totais(self, text):
        """Extrai informações de tributos totais."""
        impostos_patterns = {
            'ii_total': r'II\s*([\d\.,]+)',
            'pis_total': r'PIS\s*([\d\.,]+)',
            'cofins_total': r'COFINS\s*([\d\.,]+)',
            'taxa_siscomex': r'TAXA DE UTILIZACAO\s*([\d\.,]+)'
        }
        
        for imposto, pattern in impostos_patterns.items():
            match = re.search(pattern, text)
            if match:
                self.data['tributos_totais'][imposto] = self._clean_number(match.group(1))
    
    def parse_carga(self, text):
        """Extrai informações da carga."""
        carga_patterns = {
            'via_transporte': r'Via de Transporte\s*(.+?)\s+Num',
            'num_identificacao': r'Num\. Identificacao\s*(\d+)',
            'data_embarque': r'Data de Embarque\s*(\d{2}/\d{2}/\d{4})',
            'data_chegada': r'Data de Chegada\s*(\d{2}/\d{2}/\d{4})',
            'peso_bruto': r'Peso Bruto\s*([\d\.,]+)',
            'peso_liquido': r'Peso Liquido\s*([\d\.,]+)',
            'pais_procedencia': r'Pais de Procedencia\s*(.+)',
            'porto': r'Unidade de Despacho\s*(.+)'
        }
        
        for key, pattern in carga_patterns.items():
            match = re.search(pattern, text)
            if match:
                self.data['carga'][key] = match.group(1).strip()
    
    def parse_itens_detalhados(self, text):
        """Extrai informações detalhadas dos itens da importação."""
        # Primeiro, encontrar todos os itens com seus códigos
        item_sections = re.split(r'Item\s*\d+', text)
        
        # Padrão para identificar itens (ex: "1X8302.10.00 298")
        item_pattern = r'(\d+)X(\d{4}\.\d{2}\.\d{2})\s*(\d{3})'
        item_matches = list(re.finditer(item_pattern, text))
        
        for i, match in enumerate(item_matches):
            item_num = match.group(1)
            ncm = match.group(2)
            codigo = match.group(3)
            
            # Encontrar a seção deste item
            start_pos = match.start()
            if i < len(item_matches) - 1:
                end_pos = item_matches[i + 1].start()
                item_text = text[start_pos:end_pos]
            else:
                item_text = text[start_pos:]
            
            # Extrair informações detalhadas do item
            item_data = self._extract_item_details(item_text, item_num, ncm, codigo)
            if item_data:
                self.data['itens_detalhados'].append(item_data)
    
    def _extract_item_details(self, item_text, item_num, ncm, codigo):
        """Extrai detalhes específicos de um item."""
        item_data = {
            'item_num': item_num,
            'ncm': ncm,
            'codigo': codigo,
            'descricao': 'N/A',
            'partnumber': 'N/A',
            'valor_cond_venda_moeda': 0,
            'valor_cond_venda_brl': 0,
            'valor_local_embarque_brl': 0,
            'valor_local_aduanetro_brl': 0,
            'frete_internacional_brl': 0,
            'seguro_internacional_brl': 0,
            'ii_valor': 0,
            'ipi_valor': 0,
            'pis_valor': 0,
            'cofins_valor': 0,
            'base_calculo_ii': 0,
            'aliquota_ii': 0
        }
        
        # Descrição do produto
        desc_pattern = r'DENOMINACAO DO PRODUTO\s*(.+?)\n'
        desc_match = re.search(desc_pattern, item_text)
        if desc_match:
            item_data['descricao'] = desc_match.group(1).strip()
        
        # Part Number
        part_pattern = r'Código interno\s*([\d\.]+)'
        part_match = re.search(part_pattern, item_text)
        if part_match:
            item_data['partnumber'] = part_match.group(1)
        
        # Valores da mercadoria
        # Valor condição de venda
        vcv_pattern = r'Vlr Cond Venda \(Moeda[\s]*([\d\.,]+)'
        vcv_match = re.search(vcv_pattern, item_text)
        if vcv_match:
            item_data['valor_cond_venda_moeda'] = self._clean_number(vcv_match.group(1))
        
        vcv_brl_pattern = r'Vlr Cond Venda \(R\$\)([\d\.,]+)'
        vcv_brl_match = re.search(vcv_brl_pattern, item_text)
        if vcv_brl_match:
            item_data['valor_cond_venda_brl'] = self._clean_number(vcv_brl_match.group(1))
        
        # Local de embarque (R$)
        vle_pattern = r'Local Embarque \(R\$\)([\d\.,]+)'
        vle_match = re.search(vle_pattern, item_text)
        if vle_match:
            item_data['valor_local_embarque_brl'] = self._clean_number(vle_match.group(1))
        
        # Local aduaneiro (R$) - IMPORTANTE!
        vla_pattern = r'Local Aduaneiro \(R\$\)([\d\.,]+)'
        vla_match = re.search(vla_pattern, item_text)
        if vla_match:
            item_data['valor_local_aduanetro_brl'] = self._clean_number(vla_match.group(1))
        else:
            # Tentar padrão alternativo
            alt_pattern = r'Local Aduaneiro\s*\(R\$\)\s*([\d\.,]+)'
            alt_match = re.search(alt_pattern, item_text)
            if alt_match:
                item_data['valor_local_aduanetro_brl'] = self._clean_number(alt_match.group(1))
        
        # Frete internacional (R$)
        frete_pattern = r'Frete Internac\. \(R\$\)([\d\.,]+)'
        frete_match = re.search(frete_pattern, item_text)
        if frete_match:
            item_data['frete_internacional_brl'] = self._clean_number(frete_match.group(1))
        
        # Seguro internacional (R$)
        seguro_pattern = r'Seguro Internac\. \(R\$\)([\d\.,]+)'
        seguro_match = re.search(seguro_pattern, item_text)
        if seguro_match:
            item_data['seguro_internacional_brl'] = self._clean_number(seguro_match.group(1))
        
        # Impostos do item
        # II (Imposto de Importação)
        ii_pattern = r'II.*?Valor Devido \(R\$\)([\d\.,]+)'
        ii_match = re.search(ii_pattern, item_text)
        if ii_match:
            item_data['ii_valor'] = self._clean_number(ii_match.group(1))
        
        # PIS
        pis_pattern = r'PIS.*?Valor Devido \(R\$\)([\d\.,]+)'
        pis_match = re.search(pis_pattern, item_text)
        if pis_match:
            item_data['pis_valor'] = self._clean_number(pis_match.group(1))
        
        # COFINS
        cofins_pattern = r'COFINS.*?Valor Devido \(R\$\)([\d\.,]+)'
        cofins_match = re.search(cofins_pattern, item_text)
        if cofins_match:
            item_data['cofins_valor'] = self._clean_number(cofins_match.group(1))
        
        # Base de cálculo do II
        bc_ii_pattern = r'Base de Cálculo \(R\$\)([\d\.,]+)'
        bc_ii_match = re.search(bc_ii_pattern, item_text)
        if bc_ii_match:
            item_data['base_calculo_ii'] = self._clean_number(bc_ii_match.group(1))
        
        # Alíquota do II
        aliq_ii_pattern = r'% Alíquota\s*([\d\.,]+)'
        aliq_ii_match = re.search(aliq_ii_pattern, item_text)
        if aliq_ii_match:
            item_data['aliquota_ii'] = self._clean_number(aliq_ii_match.group(1))
        
        # Quantidades
        qtd_pattern = r'Qtde Unid\. Comercial\s*([\d\.,]+)'
        qtd_match = re.search(qtd_pattern, item_text)
        if qtd_match:
            item_data['quantidade'] = self._clean_number(qtd_match.group(1))
        
        # Valor unitário
        vu_pattern = r'Valor Unit Cond Venda\s*([\d\.,]+)'
        vu_match = re.search(vu_pattern, item_text)
        if vu_match:
            item_data['valor_unitario'] = self._clean_number(vu_match.group(1))
        
        return item_data
    
    def parse_documentos(self, text):
        """Extrai informações dos documentos."""
        doc_patterns = [
            r'CONHECIMENTO DE EMBARQUE.*?NUMERO[:]?\s*(\d+)',
            r'FATURA COMERCIAL.*?NUMERO[:]?\s*(.+?)\s+VALOR',
            r'ROMANEIO DE CARGA.*?DESCRICAO[:]?\s*(.+)'
        ]
        
        for pattern in doc_patterns:
            match = re.search(pattern, text)
            if match:
                self.data['documentos'].append(match.group(1).strip())
    
    def parse_moedas_cotacoes(self, text):
        """Extrai informações de moedas e cotações."""
        # Cotações
        euro_pattern = r'Moeda Negociada.*?EURO.*?Cotacao\s*([\d\.,]+)'
        euro_match = re.search(euro_pattern, text)
        if euro_match:
            self.data['cotacoes']['euro'] = self._clean_number(euro_match.group(1))
        
        dolar_pattern = r'Moeda Seguro.*?DOLAR.*?Cotacao\s*([\d\.,]+)'
        dolar_match = re.search(dolar_pattern, text)
        if dolar_match:
            self.data['cotacoes']['dolar'] = self._clean_number(dolar_match.group(1))
        
        # Valores de frete e seguro totais
        frete_total_pattern = r'FRETE.*?Total \(R\$\)([\d\.,]+)'
        frete_total_match = re.search(frete_total_pattern, text)
        if frete_total_match:
            self.data['valores']['frete_total_brl'] = self._clean_number(frete_total_match.group(1))
        
        seguro_total_pattern = r'SEGURO.*?Total \(R\$\)([\d\.,]+)'
        seguro_total_match = re.search(seguro_total_pattern, text)
        if seguro_total_match:
            self.data['valores']['seguro_total_brl'] = self._clean_number(seguro_total_match.group(1))
    
    def _clean_number(self, num_str):
        """Converte string numérica para float."""
        if not num_str:
            return 0.0
        try:
            # Remove pontos de milhar, substitui vírgula decimal por ponto
            cleaned = num_str.replace('.', '').replace(',', '.')
            return float(cleaned)
        except:
            return 0.0
    
    def parse_all(self, pdf_file):
        """Executa todas as etapas de parsing."""
        text = self.extract_text_from_pdf(pdf_file)
        
        if not text:
            return False
        
        # Executar todos os métodos de parsing
        self.parse_processo_info(text)
        self.parse_resumo(text)
        self.parse_tributos_totais(text)
        self.parse_carga(text)
        self.parse_itens_detalhados(text)  # Novo método detalhado
        self.parse_documentos(text)
        self.parse_moedas_cotacoes(text)
        
        # Calcular totais e médias
        self._calculate_totals()
        
        return True
    
    def _calculate_totals(self):
        """Calcula totais a partir dos itens detalhados."""
        if not self.data['itens_detalhados']:
            return
        
        # Calcular somatórios
        total_ii = sum(item.get('ii_valor', 0) for item in self.data['itens_detalhados'])
        total_pis = sum(item.get('pis_valor', 0) for item in self.data['itens_detalhados'])
        total_cofins = sum(item.get('cofins_valor', 0) for item in self.data['itens_detalhados'])
        total_vla = sum(item.get('valor_local_aduanetro_brl', 0) for item in self.data['itens_detalhados'])
        total_frete = sum(item.get('frete_internacional_brl', 0) for item in self.data['itens_detalhados'])
        total_seguro = sum(item.get('seguro_internacional_brl', 0) for item in self.data['itens_detalhados'])
        
        self.data['tributos_totais']['ii_total_itens'] = total_ii
        self.data['tributos_totais']['pis_total_itens'] = total_pis
        self.data['tributos_totais']['cofins_total_itens'] = total_cofins
        self.data['valores']['total_local_aduanetro'] = total_vla
        self.data['valores']['total_frete_itens'] = total_frete
        self.data['valores']['total_seguro_itens'] = total_seguro

def create_dashboard(data):
    """Cria o dashboard com os dados extraídos."""
    
    # Cabeçalho
    st.markdown('<h1 class="main-header">📊 Analisador de Importação - Detalhamento por Item</h1>', unsafe_allow_html=True)
    
    # Barra lateral
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=100)
        st.markdown("### 📋 Informações do Processo")
        
        if 'processo_info' in data and data['processo_info']:
            st.info(f"**Processo:** {data['processo_info'].get('processo', 'N/A')}")
            st.info(f"**Importador:** {data['processo_info'].get('importador', 'N/A')}")
            st.info(f"**CNPJ:** {data['processo_info'].get('cnpj', 'N/A')}")
        
        st.markdown("---")
        st.markdown("### ⚙️ Configurações")
        
        # Filtros
        view_options = st.multiselect(
            "Seções para exibir",
            ["Resumo Financeiro", "Tributos Totais", "Detalhamento por Item", 
             "Análise de Custos por Item", "Carga", "Documentos", "Visualizações"],
            default=["Resumo Financeiro", "Detalhamento por Item", "Análise de Custos por Item"]
        )
        
        st.markdown("---")
        if data.get('cotacoes'):
            st.markdown("### 💱 Cotações")
            st.write(f"**EUR/BRL:** {data['cotacoes'].get('euro', 'N/A'):.4f}")
            st.write(f"**USD/BRL:** {data['cotacoes'].get('dolar', 'N/A'):.4f}")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if 'resumo' in data and 'cif_brl' in data['resumo']:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; opacity: 0.9;">CIF Total (R$)</div>
                <div style="font-size: 1.5rem; font-weight: bold;">R$ {data['resumo'].get('cif_brl', '0')}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        if 'valores' in data and 'total_local_aduanetro' in data['valores']:
            total_vla = data['valores'].get('total_local_aduanetro', 0)
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);">
                <div style="font-size: 0.9rem; opacity: 0.9;">Total Local Aduaneiro</div>
                <div style="font-size: 1.5rem; font-weight: bold;">R$ {total_vla:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        if 'tributos_totais' in data and 'ii_total_itens' in data['tributos_totais']:
            total_ii = data['tributos_totais'].get('ii_total_itens', 0)
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; opacity: 0.9;">II Total (Itens)</div>
                <div style="font-size: 1.5rem; font-weight: bold;">R$ {total_ii:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        if 'carga' in data and 'data_chegada' in data['carga']:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);">
                <div style="font-size: 0.9rem; opacity: 0.9;">Previsão de Chegada</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{data['carga'].get('data_chegada', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Seção: Resumo Financeiro
    if "Resumo Financeiro" in view_options and data.get('resumo'):
        st.markdown('<h2 class="sub-header">💰 Resumo Financeiro Geral</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="data-table">', unsafe_allow_html=True)
            st.markdown("### Valores em Dólar (USD)")
            
            resumo_data = []
            if 'cif_usd' in data['resumo']:
                resumo_data.append(['CIF', f"US$ {data['resumo']['cif_usd']}"])
            if 'vmle_usd' in data['resumo']:
                resumo_data.append(['VMLE (Local Embarque)', f"US$ {data['resumo']['vmle_usd']}"])
            if 'vmld_usd' in data['resumo']:
                resumo_data.append(['VMLD (Local Destino)', f"US$ {data['resumo']['vmld_usd']}"])
            
            df_usd = pd.DataFrame(resumo_data, columns=['Descrição', 'Valor (USD)'])
            st.dataframe(df_usd, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="data-table">', unsafe_allow_html=True)
            st.markdown("### Valores em Real (BRL)")
            
            resumo_data_brl = []
            if 'cif_brl' in data['resumo']:
                resumo_data_brl.append(['CIF', f"R$ {data['resumo']['cif_brl']}"])
            if 'vmle_brl' in data['resumo']:
                resumo_data_brl.append(['VMLE (Local Embarque)', f"R$ {data['resumo']['vmle_brl']}"])
            if 'vmld_brl' in data['resumo']:
                resumo_data_brl.append(['VMLD (Local Destino)', f"R$ {data['resumo']['vmld_brl']}"])
            
            if 'valores' in data:
                if 'frete_total_brl' in data['valores']:
                    resumo_data_brl.append(['Frete Total', f"R$ {data['valores']['frete_total_brl']:,.2f}"])
                if 'seguro_total_brl' in data['valores']:
                    resumo_data_brl.append(['Seguro Total', f"R$ {data['valores']['seguro_total_brl']:,.2f}"])
            
            df_brl = pd.DataFrame(resumo_data_brl, columns=['Descrição', 'Valor (BRL)'])
            st.dataframe(df_brl, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção: Tributos Totais
    if "Tributos Totais" in view_options and data.get('tributos_totais'):
        st.markdown('<h2 class="sub-header">🏛️ Tributos Totais do Processo</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div class="data-table">', unsafe_allow_html=True)
            st.markdown("### Detalhamento de Tributos")
            
            tributos_data = []
            
            # Tributos dos itens (calculados)
            if 'ii_total_itens' in data['tributos_totais']:
                tributos_data.append(['Imposto de Importação (II)', f"R$ {data['tributos_totais']['ii_total_itens']:,.2f}", "SOMA ITENS"])
            if 'pis_total_itens' in data['tributos_totais']:
                tributos_data.append(['PIS Importação', f"R$ {data['tributos_totais']['pis_total_itens']:,.2f}", "SOMA ITENS"])
            if 'cofins_total_itens' in data['tributos_totais']:
                tributos_data.append(['COFINS Importação', f"R$ {data['tributos_totais']['cofins_total_itens']:,.2f}", "SOMA ITENS"])
            
            # Outros tributos
            if 'taxa_siscomex' in data['tributos_totais']:
                tributos_data.append(['Taxa Siscomex', f"R$ {data['tributos_totais']['taxa_siscomex']:,.2f}", "DOCUMENTO"])
            
            df_tributos = pd.DataFrame(tributos_data, columns=['Tributo', 'Valor (R$)', 'Fonte'])
            
            # Calcular total
            if not df_tributos.empty:
                total_tributos = sum(float(v.replace('R$ ', '').replace('.', '').replace(',', '.')) 
                                   for v in df_tributos['Valor (R$)'])
                total_row = pd.DataFrame([['TOTAL', f"R$ {total_tributos:,.2f}", '']], 
                                        columns=['Tributo', 'Valor (R$)', 'Fonte'])
                df_tributos = pd.concat([df_tributos, total_row], ignore_index=True)
            
            st.dataframe(df_tributos, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            # Gráfico de pizza dos tributos
            if len(tributos_data) > 0:
                valores = []
                nomes = []
                for item in tributos_data:
                    try:
                        if item[0] != 'TOTAL':
                            valor = float(item[1].replace('R$ ', '').replace('.', '').replace(',', '.'))
                            valores.append(valor)
                            nomes.append(item[0])
                    except:
                        continue
                
                if valores:
                    fig = px.pie(
                        values=valores,
                        names=nomes,
                        title="Distribuição dos Tributos",
                        hole=0.4,
                        color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
    
    # Seção: DETALHAMENTO POR ITEM (PRINCIPAL)
    if "Detalhamento por Item" in view_options and data.get('itens_detalhados'):
        st.markdown('<h2 class="sub-header">📋 Detalhamento Completo por Item</h2>', unsafe_allow_html=True)
        
        # Criar DataFrame com todos os dados dos itens
        itens_df = pd.DataFrame(data['itens_detalhados'])
        
        if not itens_df.empty:
            # Renomear colunas para melhor apresentação
            col_mapping = {
                'item_num': 'Item',
                'ncm': 'NCM',
                'codigo': 'Código',
                'partnumber': 'Part Number',
                'descricao': 'Descrição',
                'valor_cond_venda_brl': 'Valor Cond. Venda (R$)',
                'valor_local_embarque_brl': 'Local Embarque (R$)',
                'valor_local_aduanetro_brl': 'Local Aduaneiro (R$)',
                'frete_internacional_brl': 'Frete Item (R$)',
                'seguro_internacional_brl': 'Seguro Item (R$)',
                'ii_valor': 'II (R$)',
                'pis_valor': 'PIS (R$)',
                'cofins_valor': 'COFINS (R$)',
                'base_calculo_ii': 'Base Cálc. II (R$)',
                'aliquota_ii': 'Alíq. II (%)',
                'quantidade': 'Quantidade',
                'valor_unitario': 'Valor Unit. (EUR)'
            }
            
            # Selecionar e renomear colunas disponíveis
            available_cols = {}
            for db_col, display_name in col_mapping.items():
                if db_col in itens_df.columns:
                    available_cols[db_col] = display_name
            
            # Ordem preferencial das colunas
            preferred_order = ['Item', 'NCM', 'Part Number', 'Descrição', 'Quantidade', 
                             'Valor Unit. (EUR)', 'Valor Cond. Venda (R$)', 
                             'Local Embarque (R$)', 'Local Aduaneiro (R$)',
                             'Frete Item (R$)', 'Seguro Item (R$)',
                             'Base Cálc. II (R$)', 'Alíq. II (%)',
                             'II (R$)', 'PIS (R$)', 'COFINS (R$)']
            
            # Reordenar colunas
            display_cols = []
            for col in preferred_order:
                # Encontrar a chave correspondente no mapping
                for db_col, disp_name in col_mapping.items():
                    if disp_name == col and db_col in itens_df.columns:
                        display_cols.append(db_col)
                        break
            
            # Formatar valores numéricos
            formatted_df = itens_df[display_cols].copy()
            for col in formatted_df.columns:
                if col in ['valor_local_aduanetro_brl', 'frete_internacional_brl', 
                          'seguro_internacional_brl', 'ii_valor', 'pis_valor', 
                          'cofins_valor', 'base_calculo_ii', 'valor_cond_venda_brl',
                          'valor_local_embarque_brl']:
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"R$ {x:,.2f}" if pd.notnull(x) else "R$ 0,00")
                elif col == 'aliquota_ii':
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "0%")
                elif col == 'valor_unitario':
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"€ {x:,.4f}" if pd.notnull(x) else "€ 0,0000")
                elif col == 'quantidade':
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "0")
            
            # Renomear colunas para display
            formatted_df = formatted_df.rename(columns=col_mapping)
            
            # Mostrar tabela
            st.markdown('<div class="data-table">', unsafe_allow_html=True)
            st.markdown("### 📊 Tabela Detalhada por Item")
            
            # Adicionar filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_ncm = st.multiselect(
                    "Filtrar por NCM",
                    options=formatted_df['NCM'].unique(),
                    default=formatted_df['NCM'].unique()
                )
            
            with col2:
                min_valor = st.number_input("Valor mínimo (R$)", 
                                          value=0.0, 
                                          step=100.0)
            
            with col3:
                show_totals = st.checkbox("Mostrar totais por coluna", value=True)
            
            # Aplicar filtros
            filtered_df = formatted_df.copy()
            if filter_ncm:
                filtered_df = filtered_df[filtered_df['NCM'].isin(filter_ncm)]
            
            # Mostrar tabela filtrada
            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Mostrar totais se solicitado
            if show_totals and not filtered_df.empty:
                st.markdown("---")
                st.markdown("### 📈 Totais dos Itens Filtrados")
                
                # Calcular totais
                totals = {
                    'Total Local Aduaneiro (R$)': itens_df.loc[itens_df['ncm'].isin(filter_ncm) if filter_ncm else itens_df.index, 
                                                              'valor_local_aduanetro_brl'].sum(),
                    'Total Frete (R$)': itens_df.loc[itens_df['ncm'].isin(filter_ncm) if filter_ncm else itens_df.index, 
                                                    'frete_internacional_brl'].sum(),
                    'Total Seguro (R$)': itens_df.loc[itens_df['ncm'].isin(filter_ncm) if filter_ncm else itens_df.index, 
                                                     'seguro_internacional_brl'].sum(),
                    'Total II (R$)': itens_df.loc[itens_df['ncm'].isin(filter_ncm) if filter_ncm else itens_df.index, 
                                                 'ii_valor'].sum(),
                    'Total PIS (R$)': itens_df.loc[itens_df['ncm'].isin(filter_ncm) if filter_ncm else itens_df.index, 
                                                  'pis_valor'].sum(),
                    'Total COFINS (R$)': itens_df.loc[itens_df['ncm'].isin(filter_ncm) if filter_ncm else itens_df.index, 
                                                     'cofins_valor'].sum()
                }
                
                # Mostrar totais em colunas
                cols = st.columns(3)
                for i, (key, value) in enumerate(totals.items()):
                    with cols[i % 3]:
                        st.metric(key, f"R$ {value:,.2f}")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção: Análise de Custos por Item
    if "Análise de Custos por Item" in view_options and data.get('itens_detalhados'):
        st.markdown('<h2 class="sub-header">📈 Análise de Custos e Composição por Item</h2>', unsafe_allow_html=True)
        
        itens_df = pd.DataFrame(data['itens_detalhados'])
        
        if not itens_df.empty:
            # Criar abas para diferentes análises
            tab1, tab2, tab3 = st.tabs(["📊 Distribuição de Valores", "🧮 Composição de Custos", "📋 Comparativo entre Itens"])
            
            with tab1:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gráfico de barras: Local Aduaneiro por item
                    fig1 = px.bar(
                        itens_df,
                        x='item_num',
                        y='valor_local_aduanetro_brl',
                        title="Valor Local Aduaneiro por Item (R$)",
                        labels={'item_num': 'Item', 'valor_local_aduanetro_brl': 'Valor Local Aduaneiro (R$)'},
                        color='valor_local_aduanetro_brl',
                        color_continuous_scale='viridis',
                        text_auto='.2f'
                    )
                    fig1.update_layout(height=400)
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Gráfico de barras: Impostos por item
                    fig2 = go.Figure(data=[
                        go.Bar(name='II', x=itens_df['item_num'], y=itens_df['ii_valor']),
                        go.Bar(name='PIS', x=itens_df['item_num'], y=itens_df['pis_valor']),
                        go.Bar(name='COFINS', x=itens_df['item_num'], y=itens_df['cofins_valor'])
                    ])
                    fig2.update_layout(
                        title="Impostos por Item (R$)",
                        barmode='group',
                        height=400,
                        xaxis_title="Item",
                        yaxis_title="Valor (R$)"
                    )
                    st.plotly_chart(fig2, use_container_width=True)
            
            with tab2:
                st.markdown("### 🧮 Composição de Custos por Item")
                
                for _, item in itens_df.iterrows():
                    with st.expander(f"Item {item['item_num']} - {item.get('descricao', 'N/A')}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Valores básicos
                            st.markdown("**Valores Base:**")
                            st.write(f"Valor Condição Venda: R$ {item.get('valor_cond_venda_brl', 0):,.2f}")
                            st.write(f"Local Embarque: R$ {item.get('valor_local_embarque_brl', 0):,.2f}")
                            st.write(f"Local Aduaneiro: **R$ {item.get('valor_local_aduanetro_brl', 0):,.2f}**")
                        
                        with col2:
                            # Custos adicionais
                            st.markdown("**Custos Adicionais:**")
                            st.write(f"Frete: R$ {item.get('frete_internacional_brl', 0):,.2f}")
                            st.write(f"Seguro: R$ {item.get('seguro_internacional_brl', 0):,.2f}")
                            st.write(f"Base Cálculo II: R$ {item.get('base_calculo_ii', 0):,.2f}")
                        
                        # Impostos
                        st.markdown("**Impostos:**")
                        imp_cols = st.columns(3)
                        with imp_cols[0]:
                            st.metric("II", f"R$ {item.get('ii_valor', 0):,.2f}", 
                                    f"{item.get('aliquota_ii', 0):.2f}%")
                        with imp_cols[1]:
                            st.metric("PIS", f"R$ {item.get('pis_valor', 0):,.2f}")
                        with imp_cols[2]:
                            st.metric("COFINS", f"R$ {item.get('cofins_valor', 0):,.2f}")
                        
                        # Custo total aproximado
                        custo_total = (item.get('valor_local_aduanetro_brl', 0) + 
                                      item.get('ii_valor', 0) + 
                                      item.get('pis_valor', 0) + 
                                      item.get('cofins_valor', 0))
                        
                        st.markdown(f"**Custo Total Aproximado (Item):** R$ {custo_total:,.2f}")
            
            with tab3:
                st.markdown("### 📋 Comparativo entre Itens")
                
                # Selecionar métricas para comparar
                metrics = st.multiselect(
                    "Selecione as métricas para comparar:",
                    options=['valor_local_aduanetro_brl', 'frete_internacional_brl', 
                            'seguro_internacional_brl', 'ii_valor', 'pis_valor', 'cofins_valor'],
                    default=['valor_local_aduanetro_brl', 'ii_valor'],
                    format_func=lambda x: {
                        'valor_local_aduanetro_brl': 'Local Aduaneiro',
                        'frete_internacional_brl': 'Frete',
                        'seguro_internacional_brl': 'Seguro',
                        'ii_valor': 'II',
                        'pis_valor': 'PIS',
                        'cofins_valor': 'COFINS'
                    }.get(x, x)
                )
                
                if metrics:
                    # Criar gráfico comparativo
                    fig = go.Figure()
                    
                    for metric in metrics:
                        fig.add_trace(go.Bar(
                            name={
                                'valor_local_aduanetro_brl': 'Local Aduaneiro',
                                'frete_internacional_brl': 'Frete',
                                'seguro_internacional_brl': 'Seguro',
                                'ii_valor': 'II',
                                'pis_valor': 'PIS',
                                'cofins_valor': 'COFINS'
                            }.get(metric, metric),
                            x=itens_df['item_num'],
                            y=itens_df[metric],
                            text=itens_df[metric].apply(lambda x: f"R$ {x:,.2f}"),
                            textposition='auto'
                        ))
                    
                    fig.update_layout(
                        title="Comparativo de Métricas entre Itens",
                        barmode='group',
                        height=500,
                        xaxis_title="Item",
                        yaxis_title="Valor (R$)",
                        legend_title="Métrica"
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    # Seção: Carga
    if "Carga" in view_options and data.get('carga'):
        st.markdown('<h2 class="sub-header">🚢 Informações da Carga</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown("### 📦 Dados Físicos")
            st.write(f"**Peso Bruto:** {data['carga'].get('peso_bruto', 'N/A')} kg")
            st.write(f"**Peso Líquido:** {data['carga'].get('peso_liquido', 'N/A')} kg")
            st.write(f"**País de Procedência:** {data['carga'].get('pais_procedencia', 'N/A')}")
            st.write(f"**Identificação:** {data['carga'].get('num_identificacao', 'N/A')}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown("### 📅 Datas e Transporte")
            st.write(f"**Data de Embarque:** {data['carga'].get('data_embarque', 'N/A')}")
            st.write(f"**Data de Chegada:** {data['carga'].get('data_chegada', 'N/A')}")
            st.write(f"**Via de Transporte:** {data['carga'].get('via_transporte', 'N/A')}")
            st.write(f"**Porto:** {data['carga'].get('porto', 'N/A')}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção: Documentos
    if "Documentos" in view_options and data.get('documentos'):
        st.markdown('<h2 class="sub-header">📄 Documentos do Processo</h2>', unsafe_allow_html=True)
        
        if data['documentos']:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            for i, doc in enumerate(data['documentos'], 1):
                st.write(f"**Documento {i}:** {doc}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção: Visualizações
    if "Visualizações" in view_options and data.get('itens_detalhados'):
        st.markdown('<h2 class="sub-header">📊 Visualizações Analíticas Avançadas</h2>', unsafe_allow_html=True)
        
        itens_df = pd.DataFrame(data['itens_detalhados'])
        
        # Gráfico de dispersão: Valor Local Aduaneiro vs Impostos
        fig = px.scatter(
            itens_df,
            x='valor_local_aduanetro_brl',
            y='ii_valor',
            size='pis_valor',
            color='ncm',
            hover_name='descricao',
            hover_data=['partnumber', 'frete_internacional_brl', 'seguro_internacional_brl'],
            title="Relação: Local Aduaneiro vs Impostos por Item",
            labels={
                'valor_local_aduanetro_brl': 'Local Aduaneiro (R$)',
                'ii_valor': 'Imposto de Importação (R$)',
                'ncm': 'NCM'
            }
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    # Botão para download dos dados
    if st.button("📥 Exportar Dados Detalhados para Excel", use_container_width=True, type="primary"):
        # Criar arquivo Excel com múltiplas abas
        with pd.ExcelWriter('dados_importacao_detalhado.xlsx', engine='openpyxl') as writer:
            # Aba 1: Itens detalhados
            if data.get('itens_detalhados'):
                itens_df = pd.DataFrame(data['itens_detalhados'])
                itens_df.to_excel(writer, sheet_name='Itens_Detalhados', index=False)
            
            # Aba 2: Resumo financeiro
            resumo_data = []
            if data.get('resumo'):
                for key, value in data['resumo'].items():
                    resumo_data.append([key, value])
            if data.get('valores'):
                for key, value in data['valores'].items():
                    resumo_data.append([key, value])
            
            if resumo_data:
                pd.DataFrame(resumo_data, columns=['Descrição', 'Valor']).to_excel(
                    writer, sheet_name='Resumo_Financeiro', index=False)
            
            # Aba 3: Tributos
            tributos_data = []
            if data.get('tributos_totais'):
                for key, value in data['tributos_totais'].items():
                    tributos_data.append([key, value])
            
            if tributos_data:
                pd.DataFrame(tributos_data, columns=['Tributo', 'Valor']).to_excel(
                    writer, sheet_name='Tributos', index=False)
            
            # Aba 4: Carga
            carga_data = []
            if data.get('carga'):
                for key, value in data['carga'].items():
                    carga_data.append([key, value])
            
            if carga_data:
                pd.DataFrame(carga_data, columns=['Item', 'Valor']).to_excel(
                    writer, sheet_name='Carga', index=False)
        
        # Botão de download
        with open('dados_importacao_detalhado.xlsx', 'rb') as f:
            st.download_button(
                label="⬇️ Baixar Arquivo Excel Completo",
                data=f,
                file_name="dados_importacao_detalhado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

def main():
    """Função principal do aplicativo."""
    
    st.title("📄 Analisador de Documentos de Importação - Detalhado")
    st.markdown("""
    ### 🎯 **Recursos Principais:**
    - ✅ **Detalhamento completo por item**
    - ✅ **Valor Local Aduaneiro por item**
    - ✅ **Impostos (II, PIS, COFINS) por item**
    - ✅ **Frete e Seguro por item**
    - ✅ **Análises comparativas e gráficos**
    - ✅ **Exportação para Excel com todos os dados**
    
    Carregue um arquivo PDF para visualizar os dados estruturados e análises detalhadas.
    """)
    
    # Upload do arquivo
    uploaded_file = st.file_uploader(
        "Escolha um arquivo PDF de importação",
        type="pdf",
        help="Faça upload de um documento de importação no formato PDF"
    )
    
    if uploaded_file is not None:
        # Inicializar parser
        parser = ImportationPDFParser()
        
        # Mostrar indicador de progresso
        with st.spinner("🔍 Processando documento e extraindo dados detalhados..."):
            success = parser.parse_all(uploaded_file)
        
        if success:
            # Mostrar dados no dashboard
            create_dashboard(parser.data)
            
            # Mostrar estatísticas de extração
            with st.expander("📊 Estatísticas da Extração"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Itens Extraídos", len(parser.data.get('itens_detalhados', [])))
                
                with col2:
                    total_vla = sum(item.get('valor_local_aduanetro_brl', 0) 
                                  for item in parser.data.get('itens_detalhados', []))
                    st.metric("Total Local Aduaneiro", f"R$ {total_vla:,.2f}")
                
                with col3:
                    total_impostos = sum(item.get('ii_valor', 0) + item.get('pis_valor', 0) + item.get('cofins_valor', 0)
                                       for item in parser.data.get('itens_detalhados', []))
                    st.metric("Total Impostos Itens", f"R$ {total_impostos:,.2f}")
            
            # Mostrar dados brutos em expansor
            with st.expander("🔍 Visualizar Dados Brutos Extraídos"):
                st.json(parser.data, expanded=False)
        else:
            st.error("❌ Não foi possível processar o documento. Verifique se o PDF contém texto legível.")
    else:
        # Tela inicial com instruções
        st.info("👆 **Por favor, faça upload de um arquivo PDF para começar.**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📋 **Dados Extraídos por Item:**
            
            **💰 Valores:**
            - Valor Local Aduaneiro (R$)
            - Valor Condição de Venda (R$)
            - Valor Local Embarque (R$)
            - Frete por item (R$)
            - Seguro por item (R$)
            
            **🏛️ Impostos por Item:**
            - Imposto de Importação (II)
            - PIS Importação
            - COFINS Importação
            - Base de cálculo e alíquotas
            
            **📦 Informações do Item:**
            - NCM
            - Part Number
            - Descrição detalhada
            - Quantidade
            - Valor unitário
            """)
        
        with col2:
            st.markdown("""
            ### 📊 **Análises Disponíveis:**
            
            **📈 Visualizações:**
            - Distribuição de valores por item
            - Composição de custos detalhada
            - Comparativo entre itens
            - Relações entre variáveis
            
            **📋 Relatórios:**
            - Tabelas interativas filtradas
            - Totais e médias automáticas
            - Exportação completa para Excel
            
            **🎯 Funcionalidades:**
            - Filtros por NCM e valor
            - Cálculos automáticos de totais
            - Detalhamento individual por item
            - Análise de custos unitários
            """)

if __name__ == "__main__":
    main()
