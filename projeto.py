# -*- coding: utf-8 -*-
"""
ANALISADOR ESPECÍFICO DE TRIBUTOS POR ITEM
Extrai bases de cálculo e valores devidos de cada tributo em cada item
"""

import streamlit as st
import PyPDF2
import pandas as pd
import re
import io
from typing import Dict, List, Any
import plotly.graph_objects as go
import plotly.express as px

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

st.set_page_config(
    page_title="Analisador Detalhado de Tributos",
    page_icon="💰",
    layout="wide"
)

# ============================================================================
# CSS
# ============================================================================

st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 800;
    }
    
    .tax-table {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #E5E7EB;
    }
    
    .tax-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.8rem;
        border-radius: 8px;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .item-card {
        background: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# EXTRATOR ESPECÍFICO PARA TRIBUTOS
# ============================================================================

class TributosExtractor:
    """Extrator específico para bases de cálculo e valores devidos dos tributos"""
    
    def __init__(self, pdf_text: str):
        self.pdf_text = pdf_text
        self.items_data = []
    
    def extract_all_items_taxes(self):
        """Extrai todos os itens com seus tributos detalhados"""
        # Encontrar todos os itens
        item_matches = list(re.finditer(r'ITENS DA DUIMP - (\d{5})', self.pdf_text))
        
        for i, match in enumerate(item_matches):
            item_num = match.group(1)
            start_pos = match.start()
            
            # Determinar fim do item
            if i + 1 < len(item_matches):
                end_pos = item_matches[i + 1].start()
            else:
                end_pos = len(self.pdf_text)
            
            item_text = self.pdf_text[start_pos:end_pos]
            
            # Extrair dados do item
            item_data = self._extract_item_data(item_text, item_num)
            self.items_data.append(item_data)
        
        return self.items_data
    
    def _extract_item_data(self, item_text: str, item_num: str) -> Dict[str, Any]:
        """Extrai dados de um item específico"""
        item_data = {
            'item_numero': item_num,
            'descricao': '',
            'ncm': '',
            'codigo_interno': '',
            'tributos': {}
        }
        
        # Extrair descrição
        desc_match = re.search(r'DENOMINACAO DO PRODUTO\s+(.+?)\s+DESCRICAO', item_text, re.DOTALL)
        if desc_match:
            item_data['descricao'] = desc_match.group(1).strip()
        
        # Extrair NCM
        ncm_match = re.search(r'NCM\s*(\d{4}\.\d{2}\.\d{2})', item_text)
        if ncm_match:
            item_data['ncm'] = ncm_match.group(1)
        
        # Extrair código interno
        cod_match = re.search(r'Código interno\s+(\d+\.\d+\.\d+)', item_text)
        if cod_match:
            item_data['codigo_interno'] = cod_match.group(1)
        
        # Extrair tributos INDIVIDUAIS com base de cálculo
        item_data['tributos']['II'] = self._extract_specific_tax(item_text, 'II')
        item_data['tributos']['PIS'] = self._extract_specific_tax(item_text, 'PIS')
        item_data['tributos']['COFINS'] = self._extract_specific_tax(item_text, 'COFINS')
        
        # Extrair valor aduaneiro
        aduaneiro_match = re.search(r'Local Aduaneiro \(R\$\)\s+([\d.,]+)', item_text)
        if aduaneiro_match:
            item_data['valor_aduaneiro'] = float(aduaneiro_match.group(1).replace('.', '').replace(',', '.'))
        
        # Extrair valor no embarque
        embarque_match = re.search(r'Local Embarque \(R\$\)\s+([\d.,]+)', item_text)
        if embarque_match:
            item_data['valor_embarque'] = float(embarque_match.group(1).replace('.', '').replace(',', '.'))
        
        return item_data
    
    def _extract_specific_tax(self, item_text: str, tax_name: str) -> Dict[str, Any]:
        """Extrai dados específicos de um tributo"""
        tax_data = {
            'base_calculo': 0,
            'valor_devido': 0,
            'aliquota': 0,
            'valor_calculado': 0,
            'valor_recolher': 0
        }
        
        # Padrão específico para cada tributo
        patterns = {
            'II': r'(?:II|I\.I\.).*?Base de Cálculo \(R\$\)\s+([\d.,]+).*?Valor Devido \(R\$\)\s+([\d.,]+)',
            'PIS': r'PIS.*?Base de Cálculo \(R\$\)\s+([\d.,]+).*?Valor Devido \(R\$\)\s+([\d.,]+)',
            'COFINS': r'COFINS.*?Base de Cálculo \(R\$\)\s+([\d.,]+).*?Valor Devido \(R\$\)\s+([\d.,]+)'
        }
        
        if tax_name in patterns:
            match = re.search(patterns[tax_name], item_text, re.DOTALL | re.IGNORECASE)
            if match:
                base_calculo = float(match.group(1).replace('.', '').replace(',', '.'))
                valor_devido = float(match.group(2).replace('.', '').replace(',', '.'))
                
                tax_data['base_calculo'] = base_calculo
                tax_data['valor_devido'] = valor_devido
                tax_data['aliquota'] = (valor_devido / base_calculo * 100) if base_calculo > 0 else 0
        
        # Tentar extrair valor calculado também
        calc_pattern = rf'{tax_name}.*?Valor Calculado \(R\$\)\s+([\d.,]+)'
        calc_match = re.search(calc_pattern, item_text, re.DOTALL | re.IGNORECASE)
        if calc_match:
            tax_data['valor_calculado'] = float(calc_match.group(1).replace('.', '').replace(',', '.'))
        
        # Tentar extrair valor a recolher
        recolher_pattern = rf'{tax_name}.*?Valor A Recolher \(R\$\)\s+([\d.,]+)'
        recolher_match = re.search(recolher_pattern, item_text, re.DOTALL | re.IGNORECASE)
        if recolher_match:
            tax_data['valor_recolher'] = float(recolher_match.group(1).replace('.', '').replace(',', '.'))
        
        return tax_data

# ============================================================================
# VISUALIZADOR DE TRIBUTOS
# ============================================================================

class TributosVisualizer:
    """Visualizador especializado em mostrar tributos por item"""
    
    @staticmethod
    def display_item_taxes_table(item_data: Dict[str, Any]):
        """Exibe tabela detalhada dos tributos de um item"""
        tributos = item_data.get('tributos', {})
        
        # Criar DataFrame para a tabela
        tax_rows = []
        for tax_name, tax_info in tributos.items():
            if tax_info['base_calculo'] > 0:
                tax_rows.append({
                    'Tributo': tax_name,
                    'Base de Cálculo (R$)': f"R$ {tax_info['base_calculo']:,.2f}",
                    'Valor Devido (R$)': f"R$ {tax_info['valor_devido']:,.2f}",
                    'Alíquota Efetiva': f"{tax_info['aliquota']:.2f}%",
                    'Valor Calculado (R$)': f"R$ {tax_info['valor_calculado']:,.2f}" if tax_info['valor_calculado'] > 0 else "N/A",
                    'Valor a Recolher (R$)': f"R$ {tax_info['valor_recolher']:,.2f}" if tax_info['valor_recolher'] > 0 else "N/A"
                })
        
        if tax_rows:
            df = pd.DataFrame(tax_rows)
            
            # Estilizar a tabela
            st.markdown(f"""
            <div class="tax-table">
                <div class="tax-header">
                    📊 Item {item_data['item_numero']} - {item_data['descricao'][:50]}...
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Mostrar informações básicas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("NCM", item_data.get('ncm', 'N/A'))
            with col2:
                st.metric("Código", item_data.get('codigo_interno', 'N/A'))
            with col3:
                if 'valor_aduaneiro' in item_data:
                    st.metric("Valor Aduaneiro", f"R$ {item_data['valor_aduaneiro']:,.2f}")
            
            # Mostrar tabela de tributos
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tributo": st.column_config.TextColumn(width="small"),
                    "Base de Cálculo (R$)": st.column_config.TextColumn(width="medium"),
                    "Valor Devido (R$)": st.column_config.TextColumn(width="medium"),
                    "Alíquota Efetiva": st.column_config.TextColumn(width="medium"),
                    "Valor Calculado (R$)": st.column_config.TextColumn(width="medium"),
                    "Valor a Recolher (R$)": st.column_config.TextColumn(width="medium")
                }
            )
            
            # Calcular totais
            total_base = sum(tax['base_calculo'] for tax in tributos.values())
            total_devido = sum(tax['valor_devido'] for tax in tributos.values())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Base", f"R$ {total_base:,.2f}")
            with col2:
                st.metric("Total Devido", f"R$ {total_devido:,.2f}")
            with col3:
                aliquota_media = (total_devido / total_base * 100) if total_base > 0 else 0
                st.metric("Alíquota Média", f"{aliquota_media:.2f}%")
            
            st.markdown("---")
    
    @staticmethod
    def create_tax_comparison_chart(items_data: List[Dict[str, Any]]):
        """Cria gráfico comparativo de tributos entre itens"""
        # Preparar dados para o gráfico
        chart_data = []
        
        for item in items_data:
            item_num = item['item_numero']
            tributos = item['tributos']
            
            for tax_name, tax_info in tributos.items():
                if tax_info['base_calculo'] > 0:
                    chart_data.append({
                        'Item': f"Item {item_num}",
                        'Tributo': tax_name,
                        'Base Cálculo': tax_info['base_calculo'],
                        'Valor Devido': tax_info['valor_devido'],
                        'Alíquota': tax_info['aliquota']
                    })
        
        if not chart_data:
            return
        
        df = pd.DataFrame(chart_data)
        
        # Gráfico 1: Valores devidos por item
        fig1 = px.bar(
            df,
            x='Item',
            y='Valor Devido',
            color='Tributo',
            title='💰 Valor Devido por Item e Tributo',
            barmode='group',
            text='Valor Devido',
            hover_data=['Base Cálculo', 'Alíquota']
        )
        fig1.update_traces(texttemplate='R$%{text:,.0f}', textposition='outside')
        fig1.update_layout(height=500)
        
        # Gráfico 2: Bases de cálculo
        fig2 = px.bar(
            df,
            x='Item',
            y='Base Cálculo',
            color='Tributo',
            title='📊 Base de Cálculo por Item',
            barmode='group',
            text='Base Cálculo',
            hover_data=['Valor Devido', 'Alíquota']
        )
        fig2.update_traces(texttemplate='R$%{text:,.0f}', textposition='outside')
        fig2.update_layout(height=500)
        
        # Gráfico 3: Alíquotas
        fig3 = px.bar(
            df,
            x='Item',
            y='Alíquota',
            color='Tributo',
            title='📈 Alíquota Efetiva por Item (%)',
            barmode='group',
            text='Alíquota',
            hover_data=['Base Cálculo', 'Valor Devido']
        )
        fig3.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig3.update_layout(height=500)
        
        # Mostrar gráficos
        st.plotly_chart(fig1, use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            st.plotly_chart(fig3, use_container_width=True)
    
    @staticmethod
    def create_summary_table(items_data: List[Dict[str, Any]]):
        """Cria tabela resumo de todos os itens"""
        summary_rows = []
        
        for item in items_data:
            item_num = item['item_numero']
            tributos = item['tributos']
            
            # Calcular totais para o item
            total_base = sum(tax['base_calculo'] for tax in tributos.values())
            total_devido = sum(tax['valor_devido'] for tax in tributos.values())
            
            # Detalhes por tributo
            ii = tributos.get('II', {})
            pis = tributos.get('PIS', {})
            cofins = tributos.get('COFINS', {})
            
            summary_rows.append({
                'Item': item_num,
                'Descrição': item['descricao'][:30] + ('...' if len(item['descricao']) > 30 else ''),
                'NCM': item.get('ncm', ''),
                'Valor Aduan.': f"R$ {item.get('valor_aduaneiro', 0):,.2f}",
                'II Base': f"R$ {ii.get('base_calculo', 0):,.2f}",
                'II Devido': f"R$ {ii.get('valor_devido', 0):,.2f}",
                'PIS Base': f"R$ {pis.get('base_calculo', 0):,.2f}",
                'PIS Devido': f"R$ {pis.get('valor_devido', 0):,.2f}",
                'COFINS Base': f"R$ {cofins.get('base_calculo', 0):,.2f}",
                'COFINS Devido': f"R$ {cofins.get('valor_devido', 0):,.2f}",
                'Total Base': f"R$ {total_base:,.2f}",
                'Total Devido': f"R$ {total_devido:,.2f}"
            })
        
        if summary_rows:
            df = pd.DataFrame(summary_rows)
            
            st.markdown("### 📋 Resumo Geral por Item")
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Calcular totais gerais
            total_geral_base = sum(float(row['Total Base'].replace('R$ ', '').replace('.', '').replace(',', '.')) 
                                  for row in summary_rows)
            total_geral_devido = sum(float(row['Total Devido'].replace('R$ ', '').replace('.', '').replace(',', '.')) 
                                    for row in summary_rows)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Itens", len(items_data))
            with col2:
                st.metric("Total Base Cálculo", f"R$ {total_geral_base:,.2f}")
            with col3:
                st.metric("Total Devido", f"R$ {total_geral_devido:,.2f}")

# ============================================================================
# APLICAÇÃO PRINCIPAL
# ============================================================================

def main():
    """Aplicação principal"""
    
    st.markdown('<h1 class="main-title">💰 ANALISADOR DETALHADO DE TRIBUTOS POR ITEM</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; color: #6B7280; margin-bottom: 2rem;">
        Extrai <strong>bases de cálculo</strong> e <strong>valores devidos</strong> de cada tributo por item
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3710/3710277.png", width=80)
        st.markdown("### 📤 Upload do PDF")
        
        uploaded_file = st.file_uploader(
            "Carregue o documento de importação",
            type=['pdf'],
            help="Documento deve estar no formato padrão"
        )
        
        st.markdown("---")
        st.markdown("### ⚙️ Opções")
        
        show_charts = st.checkbox("Mostrar gráficos comparativos", value=True)
        show_raw = st.checkbox("Mostrar dados extraídos", value=False)
        
        st.markdown("---")
        st.markdown("""
        **Tributos extraídos:**
        - ✅ II (Imposto de Importação)
        - ✅ PIS (Programa de Integração Social)
        - ✅ COFINS (Contribuição para Financiamento da Seguridade Social)
        
        **Por cada item:**
        - Base de Cálculo
        - Valor Devido
        - Alíquota Efetiva
        - Valores Calculados
        """)
    
    # Processar arquivo
    if uploaded_file is not None:
        try:
            # Extrair texto do PDF
            with st.spinner("📄 Lendo documento..."):
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text()
            
            # Extrair dados dos tributos
            with st.spinner("🔍 Extraindo bases de cálculo e valores..."):
                extractor = TributosExtractor(pdf_text)
                items_data = extractor.extract_all_items_taxes()
            
            # Mostrar resultados
            if items_data:
                st.success(f"✅ {len(items_data)} itens processados com sucesso!")
                
                # Criar abas
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📊 Detalhes por Item", 
                    "📈 Comparativo", 
                    "📋 Resumo", 
                    "💾 Exportar"
                ])
                
                with tab1:
                    st.markdown("### 📋 TRIBUTOS DETALHADOS POR ITEM")
                    
                    for item_data in items_data:
                        TributosVisualizer.display_item_taxes_table(item_data)
                
                with tab2:
                    if show_charts:
                        st.markdown("### 📈 COMPARAÇÃO ENTRE ITENS")
                        TributosVisualizer.create_tax_comparison_chart(items_data)
                    else:
                        st.info("Ative 'Mostrar gráficos comparativos' na sidebar para ver os gráficos.")
                
                with tab3:
                    st.markdown("### 📋 RESUMO GERAL")
                    TributosVisualizer.create_summary_table(items_data)
                
                with tab4:
                    st.markdown("### 💾 EXPORTAR DADOS")
                    
                    # Preparar dados para exportação
                    export_data = []
                    for item in items_data:
                        for tax_name, tax_info in item['tributos'].items():
                            if tax_info['base_calculo'] > 0:
                                export_data.append({
                                    'Item': item['item_numero'],
                                    'Descrição': item['descricao'],
                                    'NCM': item.get('ncm', ''),
                                    'Tributo': tax_name,
                                    'Base_Calculo': tax_info['base_calculo'],
                                    'Valor_Devido': tax_info['valor_devido'],
                                    'Aliquota': tax_info['aliquota'],
                                    'Valor_Calculado': tax_info['valor_calculado'],
                                    'Valor_Recolher': tax_info['valor_recolher']
                                })
                    
                    if export_data:
                        df_export = pd.DataFrame(export_data)
                        
                        # Botão para download CSV
                        csv = df_export.to_csv(index=False, sep=';', decimal=',')
                        st.download_button(
                            label="📥 Baixar CSV (Excel)",
                            data=csv,
                            file_name=f"tributos_detalhados.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        # Botão para download Excel
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_export.to_excel(writer, sheet_name='Tributos', index=False)
                            
                            # Adicionar resumo
                            summary = []
                            for item in items_data:
                                summary.append({
                                    'Item': item['item_numero'],
                                    'Descrição': item['descricao'],
                                    'Total_Base': sum(tax['base_calculo'] for tax in item['tributos'].values()),
                                    'Total_Devido': sum(tax['valor_devido'] for tax in item['tributos'].values())
                                })
                            
                            if summary:
                                df_summary = pd.DataFrame(summary)
                                df_summary.to_excel(writer, sheet_name='Resumo', index=False)
                        
                        output.seek(0)
                        
                        st.download_button(
                            label="📥 Baixar Excel Completo",
                            data=output,
                            file_name=f"tributos_completo.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                
                # Mostrar dados extraídos se solicitado
                if show_raw and items_data:
                    with st.expander("🔍 Ver Dados Extraídos (Brutos)"):
                        for i, item in enumerate(items_data):
                            st.markdown(f"**Item {item['item_numero']}:**")
                            st.json(item)
                            st.markdown("---")
            
            else:
                st.warning("⚠️ Nenhum item encontrado no documento.")
                
        except Exception as e:
            st.error(f"❌ Erro ao processar documento: {str(e)}")
    
    else:
        # Tela inicial
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.info("👆 **Faça upload de um documento PDF para começar a análise.**")
            
            st.markdown("""
            <div style="background: #F0F9FF; padding: 2rem; border-radius: 10px; margin-top: 2rem;">
                <h4>📋 Exemplo do que será extraído:</h4>
                <p><strong>Para cada item (ex: Item 00001):</strong></p>
                <ul>
                    <li><strong>II:</strong> Base: R$ 3.318,72 | Devido: R$ 531,00 | Alíquota: 16%</li>
                    <li><strong>PIS:</strong> Base: R$ 3.318,72 | Devido: R$ 69,69 | Alíquota: 2,1%</li>
                    <li><strong>COFINS:</strong> Base: R$ 3.318,72 | Devido: R$ 320,26 | Alíquota: 9,65%</li>
                </ul>
                <p><em>E assim para cada um dos 5 itens do seu documento.</em></p>
            </div>
            """, unsafe_allow_html=True)
            
            # Exemplo de como os dados são extraídos
            st.markdown("---")
            st.markdown("### 🎯 Exemplo de Extração do Seu Documento")
            
            # Criar exemplo com os dados que você mostrou
            example_data = {
                'item_numero': '00005',
                'descricao': 'ALOJAMENTO PARA DOBRADICA DE EMBUTIR EM ACO',
                'ncm': '8302.10.00',
                'tributos': {
                    'COFINS': {
                        'base_calculo': 922.67,
                        'valor_devido': 89.04,
                        'aliquota': 9.65,
                        'valor_calculado': 89.04,
                        'valor_recolher': 89.04
                    }
                }
            }
            
            st.markdown(f"""
            <div class="item-card">
                <h4>Item {example_data['item_numero']} - {example_data['descricao']}</h4>
                <p><strong>NCM:</strong> {example_data['ncm']}</p>
                <p><strong>COFINS:</strong></p>
                <ul>
                    <li><strong>Base de Cálculo:</strong> R$ {example_data['tributos']['COFINS']['base_calculo']:,.2f}</li>
                    <li><strong>Valor Devido:</strong> R$ {example_data['tributos']['COFINS']['valor_devido']:,.2f}</li>
                    <li><strong>Alíquota:</strong> {example_data['tributos']['COFINS']['aliquota']:.2f}%</li>
                    <li><strong>Valor Calculado:</strong> R$ {example_data['tributos']['COFINS']['valor_calculado']:,.2f}</li>
                    <li><strong>Valor a Recolher:</strong> R$ {example_data['tributos']['COFINS']['valor_recolher']:,.2f}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    main()
