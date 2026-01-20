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
        """Processa todo o texto do PDF"""
        # Encontrar todos os itens
        items = self._find_all_items(text)
        self.documento['itens'] = items
        
        # Calcular totais
        self._calculate_totals()
    
    def _find_all_items(self, text: str) -> List[Dict]:
        """Encontra todos os itens no texto com proteção contra erros de índice"""
        items = []
        
        # Padrão para encontrar início de itens
        item_pattern = r'(?:^|\n)(\d+)\s+(\d{4}\.\d{2}\.\d{2})\s+(\d+)\s'
        matches = list(re.finditer(item_pattern, text))
        
        logger.info(f"Encontrados {len(matches)} padrões de itens")
        
        # Lógica Blindada de Iteração
        for i, match in enumerate(matches):
            try:
                start_pos = match.start()
                
                # Definição segura do fim do bloco
                if i + 1 < len(matches):
                    end_pos = matches[i + 1].start()
                else:
                    end_pos = len(text)
                
                # Verifica se os índices são válidos
                if start_pos >= len(text) or end_pos > len(text):
                    continue

                item_text = text[start_pos:end_pos]
                
                # Extrai grupos do match atual
                item_num = match.group(1)
                ncm = match.group(2)
                codigo = match.group(3)
                
                item_data = self._parse_item(item_text, item_num, ncm, codigo)
                
                if item_data:
                    items.append(item_data)
                    
            except Exception as e:
                # Se der erro em um item específico, loga e continua para o próximo
                # Isso evita que o erro "list index out of range" pare o script inteiro
                logger.warning(f"Erro ao processar item index {i}: {str(e)}")
                continue
        
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
                
                # Campos Base de Cálculo
                'ii_base_calculo': 0,
                'ipi_base_calculo': 0,
                'pis_base_calculo': 0,
                'cofins_base_calculo': 0,
                
                # Campos Alíquotas
                'ii_aliquota': 0,
                'ipi_aliquota': 0,
                'pis_aliquota': 0,
                'cofins_aliquota': 0,
                
                'total_impostos': 0,
                'valor_total_com_impostos': 0
            }
            
            # --- SEÇÃO 1: TEXTOS E CÓDIGOS ---
            nome_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n(.*?)\n(?:DESCRICAO|MARCA)', text, re.IGNORECASE | re.DOTALL)
            if nome_match:
                item['nome_produto'] = nome_match.group(1).replace('\n', ' ').strip()
            
            codigo_match = re.search(r'Código interno\s*(.*?)\s*(?=FABRICANTE|Conhecido|Pais)', text, re.IGNORECASE | re.DOTALL)
            if codigo_match:
                raw_code = codigo_match.group(1)
                clean_code = raw_code.replace('(PARTNUMBER)', '').replace('Código interno', '').replace('\n', '')
                item['codigo_interno'] = clean_code.strip()
            
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
        
        # Mapeamento Completo
        patterns = {
            # Valores
            'ii_valor_devido': r'II.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            'ipi_valor_devido': r'IPI.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            'pis_valor_devido': r'PIS.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            'cofins_valor_devido': r'COFINS.*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            
            # Bases
            'ii_base_calculo': r'II.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
            'ipi_base_calculo': r'IPI.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
            'pis_base_calculo': r'PIS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
            'cofins_base_calculo': r'COFINS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)',
            
            # Alíquotas
            'ii_aliquota': r'II.*?% Alíquota\s*([\d\.,]+)',
            'ipi_aliquota': r'IPI.*?% Alíquota\s*([\d\.,]+)',
            'pis_aliquota': r'PIS.*?% Alíquota\s*([\d\.,]+)',
            'cofins_aliquota': r'COFINS.*?% Alíquota\s*([\d\.,]+)'
        }
        
        for key, pattern in patterns.items():
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
    """Analisador financeiro"""
    
    def __init__(self, documento: Dict):
        self.documento = documento
        self.itens_df = None
        
    def prepare_dataframe(self):
        """Prepara DataFrame para análise"""
        itens_data = []
        
        for item in self.documento['itens']:
            
            # --- REGRA DA TAG XML (10.000.000) ---
            # 1. Valor Total
            valor_total_float = item.get('valor_total', 0)
            xml_total_value = int(valor_total_float * 10000000)

            # 2. Valor Unitário (Aplicado conforme solicitado)
            valor_unit_float = item.get('valor_unitario', 0)
            xml_unit_value = int(valor_unit_float * 10000000)
            
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
                
                # Valores Principais e Tags XML
                'Valor Unit. (R$)': valor_unit_float,
                'XML <valorUnitarioCondicaoVenda>': str(xml_unit_value),
                
                'Valor Total (R$)': valor_total_float,
                'XML <valorTotalCondicaoVenda>': str(xml_total_value),
                
                'Local Aduaneiro (R$)': item.get('local_aduaneiro', 0),
                
                'Frete (R$)': item.get('frete_internacional', 0),
                'Seguro (R$)': item.get('seguro_internacional', 0),
                
                # Impostos - Valores
                'II (R$)': item.get('ii_valor_devido', 0),
                'IPI (R$)': item.get('ipi_valor_devido', 0),
                'PIS (R$)': item.get('pis_valor_devido', 0),
                'COFINS (R$)': item.get('cofins_valor_devido', 0),
                
                # Bases e Alíquotas
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

def main():
    """Função principal"""
    
    st.markdown('<h1 class="main-header">🏭 Sistema de Análise de Extratos Häfele (PRO)</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="section-card">
        <strong>🔍 Extração Profissional</strong><br>
        Sistema com regra de XML (Tags Unitário e Total), Bases de Cálculo e Alíquotas.
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
    
    if uploaded_file is not None:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("📄 Analisando documento PDF...")
            progress_bar.progress(30)
            
            parser = HafelePDFParser()
            documento = parser.parse_pdf(tmp_path)
            
            status_text.text("📊 Processando dados...")
            progress_bar.progress(60)
            
            analyser = FinancialAnalyzer(documento)
            df = analyser.prepare_dataframe()
            
            progress_bar.progress(100)
            status_text.text("✅ Processamento concluído!")
            
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            totais = documento['totais']
            st.success(f"✅ **{len(documento['itens'])} itens** extraídos com sucesso!")
            
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
                    <div class="metric-value">R$ {totais.get('pis_total', 0):,.2f}</div>
                    <div class="metric-label">Total PIS</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">R$ {totais.get('cofins_total', 0):,.2f}</div>
                    <div class="metric-label">Total COFINS</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('<h2 class="sub-header">📦 Lista de Itens Detalhada</h2>', unsafe_allow_html=True)
            
            cols_order = [
                'Item', 'Código Interno', 'Produto', 'NCM',
                'Valor Unit. (R$)', 'XML <valorUnitarioCondicaoVenda>',
                'Valor Total (R$)', 'XML <valorTotalCondicaoVenda>', 
                'II Base (R$)', 'II Alíq. (%)',
                'IPI Base (R$)', 'IPI Alíq. (%)',
                'PIS Base (R$)', 'PIS Alíq. (%)',
                'COFINS Base (R$)', 'COFINS Alíq. (%)'
            ]
            
            display_cols = [c for c in cols_order if c in df.columns]
            remaining_cols = [c for c in df.columns if c not in display_cols]
            final_cols = display_cols + remaining_cols
            
            display_df = df[final_cols].copy()
            
            # Formatação
            currency_cols = [col for col in display_df.columns if '(R$)' in col]
            for c in currency_cols:
                display_df[c] = display_df[c].apply(lambda x: f"R$ {x:,.2f}")
            
            pct_cols = [col for col in display_df.columns if '(%)' in col]
            for c in pct_cols:
                display_df[c] = display_df[c].apply(lambda x: f"{x:,.2f}%")
            
            xml_cols = ['XML <valorTotalCondicaoVenda>', 'XML <valorUnitarioCondicaoVenda>']
            for c in xml_cols:
                if c in display_df.columns:
                    display_df[c] = display_df[c].astype(str)

            st.dataframe(
                display_df,
                use_container_width=True,
                height=600
            )
            
            st.markdown('<h2 class="sub-header">💾 Exportação</h2>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = df.to_csv(index=False, encoding='utf-8-sig', sep=';')
                st.download_button(
                    label="📥 Baixar CSV (Completo)",
                    data=csv_data,
                    file_name="itens_hafele_xml_ready.csv",
                    mime="text/csv"
                )
            
            with col2:
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Itens', index=False)
                
                st.download_button(
                    label="📊 Baixar Excel",
                    data=output.getvalue(),
                    file_name="itens_hafele_xml_ready.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        except Exception as e:
            st.error(f"❌ Erro no processamento: {str(e)}")
    
    else:
        st.info("Aguardando upload do PDF...")

if __name__ == "__main__":
    main()
