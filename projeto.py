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
    page_title="Analisador de Documentos de Importação",
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
</style>
""", unsafe_allow_html=True)

class ImportationPDFParser:
    """Classe para analisar e extrair dados de PDFs de importação."""
    
    def __init__(self):
        self.data = {
            'processo_info': {},
            'resumo': {},
            'tributos': {},
            'carga': {},
            'transporte': {},
            'itens': [],
            'documentos': [],
            'valores': {},
            'impostos_detalhados': []
        }
    
    def extract_text_from_pdf(self, pdf_file):
        """Extrai texto de um arquivo PDF."""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                all_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        all_text += page_text + "\n\n"
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
        
        # VMLE
        vmle_pattern = r'VMLE\s*\(US\$\)\s*([\d\.,]+)\s*VMLE\s*\(R\$\)\s*([\d\.,]+)'
        vmle_match = re.search(vmle_pattern, text)
        if vmle_match:
            self.data['resumo']['vmle_usd'] = vmle_match.group(1)
            self.data['resumo']['vmle_brl'] = vmle_match.group(2)
    
    def parse_tributos(self, text):
        """Extrai informações de tributos."""
        # Valores totais dos impostos
        impostos_patterns = {
            'ii': r'II\s*([\d\.,]+)',
            'pis': r'PIS\s*([\d\.,]+)',
            'cofins': r'COFINS\s*([\d\.,]+)',
            'taxa_siscomex': r'TAXA DE UTILIZACAO\s*([\d\.,]+)'
        }
        
        for imposto, pattern in impostos_patterns.items():
            match = re.search(pattern, text)
            if match:
                self.data['tributos'][imposto] = match.group(1)
    
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
    
    def parse_itens(self, text):
        """Extrai informações dos itens da importação."""
        # Padrão para encontrar itens
        item_pattern = r'Item\s*\d+\s*X\s*(\d{4}\.\d{2}\.\d{2})\s*(\d+).*?Valor Unit Cond Venda\s*([\d\.,]+)'
        items = re.findall(item_pattern, text, re.DOTALL)
        
        for i, item in enumerate(items, 1):
            ncm, codigo, valor_unit = item
            # Encontrar descrição do produto
            desc_pattern = f"{ncm}.*?DENOMINACAO DO PRODUTO\s*(.+?)\n"
            desc_match = re.search(desc_pattern, text, re.DOTALL)
            
            item_data = {
                'item': i,
                'ncm': ncm,
                'codigo': codigo,
                'valor_unit': valor_unit,
                'descricao': desc_match.group(1).strip() if desc_match else 'N/A'
            }
            self.data['itens'].append(item_data)
    
    def parse_documentos(self, text):
        """Extrai informações dos documentos."""
        # Documentos instrutivos
        doc_patterns = [
            r'CONHECIMENTO DE EMBARQUE.*?NUMERO[:]?\s*(\d+)',
            r'FATURA COMERCIAL.*?NUMERO[:]?\s*(.+?)\s+VALOR',
            r'ROMANEIO DE CARGA.*?DESCRICAO[:]?\s*(.+)'
        ]
        
        for pattern in doc_patterns:
            match = re.search(pattern, text)
            if match:
                self.data['documentos'].append(match.group(1).strip())
    
    def parse_moedas(self, text):
        """Extrai informações de moedas e cotações."""
        moeda_pattern = r'Moeda Negociada\s*(\d+)\s*-\s*(\w+)\s*Cotacao\s*([\d\.,]+)'
        moedas = re.findall(moeda_pattern, text)
        
        for moeda in moedas:
            codigo, nome, cotacao = moeda
            self.data['valores'][f'cotacao_{nome.lower()}'] = cotacao
    
    def parse_all(self, pdf_file):
        """Executa todas as etapas de parsing."""
        text = self.extract_text_from_pdf(pdf_file)
        
        if not text:
            return False
        
        # Executar todos os métodos de parsing
        self.parse_processo_info(text)
        self.parse_resumo(text)
        self.parse_tributos(text)
        self.parse_carga(text)
        self.parse_itens(text)
        self.parse_documentos(text)
        self.parse_moedas(text)
        
        return True

def create_dashboard(data):
    """Cria o dashboard com os dados extraídos."""
    
    # Cabeçalho
    st.markdown('<h1 class="main-header">📊 Analisador de Documentos de Importação</h1>', unsafe_allow_html=True)
    
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
            ["Resumo Financeiro", "Tributos", "Carga", "Itens", "Documentos", "Visualizações"],
            default=["Resumo Financeiro", "Tributos", "Itens"]
        )
    
    # Layout principal
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
        if 'tributos' in data and 'ii' in data['tributos']:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; opacity: 0.9;">Imposto de Importação</div>
                <div style="font-size: 1.5rem; font-weight: bold;">R$ {data['tributos'].get('ii', '0')}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        if 'tributos' in data and 'pis' in data['tributos']:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; opacity: 0.9;">PIS Importação</div>
                <div style="font-size: 1.5rem; font-weight: bold;">R$ {data['tributos'].get('pis', '0')}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        if 'carga' in data and 'data_chegada' in data['carga']:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; opacity: 0.9;">Previsão de Chegada</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{data['carga'].get('data_chegada', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Seção: Resumo Financeiro
    if "Resumo Financeiro" in view_options and data.get('resumo'):
        st.markdown('<h2 class="sub-header">💰 Resumo Financeiro</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="data-table">', unsafe_allow_html=True)
            st.markdown("### Valores em Dólar (USD)")
            df_usd = pd.DataFrame({
                'Descrição': ['CIF', 'VMLE (Local de Embarque)'],
                'Valor (USD)': [
                    data['resumo'].get('cif_usd', '0'),
                    data['resumo'].get('vmle_usd', '0')
                ]
            })
            st.dataframe(df_usd, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="data-table">', unsafe_allow_html=True)
            st.markdown("### Valores em Real (BRL)")
            df_brl = pd.DataFrame({
                'Descrição': ['CIF', 'VMLE (Local de Embarque)'],
                'Valor (BRL)': [
                    data['resumo'].get('cif_brl', '0'),
                    data['resumo'].get('vmle_brl', '0')
                ]
            })
            st.dataframe(df_brl, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção: Tributos
    if "Tributos" in view_options and data.get('tributos'):
        st.markdown('<h2 class="sub-header">🏛️ Tributos e Impostos</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div class="data-table">', unsafe_allow_html=True)
            st.markdown("### Detalhamento de Tributos")
            
            tributos_data = []
            for tributo, valor in data['tributos'].items():
                nome = {
                    'ii': 'Imposto de Importação',
                    'pis': 'PIS Importação',
                    'cofins': 'COFINS Importação',
                    'taxa_siscomex': 'Taxa Siscomex'
                }.get(tributo, tributo.upper())
                
                tributos_data.append({'Tributo': nome, 'Valor (R$)': f"R$ {valor}"})
            
            df_tributos = pd.DataFrame(tributos_data)
            st.dataframe(df_tributos, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            # Gráfico de pizza dos tributos
            if len(tributos_data) > 0:
                valores = []
                nomes = []
                for item in tributos_data:
                    try:
                        valor = float(item['Valor (R$)'].replace('R$ ', '').replace('.', '').replace(',', '.'))
                        valores.append(valor)
                        nomes.append(item['Tributo'])
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
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown("### 📅 Datas e Transporte")
            st.write(f"**Data de Embarque:** {data['carga'].get('data_embarque', 'N/A')}")
            st.write(f"**Data de Chegada:** {data['carga'].get('data_chegada', 'N/A')}")
            st.write(f"**Via de Transporte:** {data['carga'].get('via_transporte', 'N/A')}")
            st.write(f"**Porto:** {data['carga'].get('porto', 'N/A')}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção: Itens
    if "Itens" in view_options and data.get('itens'):
        st.markdown('<h2 class="sub-header">📋 Itens da Importação</h2>', unsafe_allow_html=True)
        
        if data['itens']:
            df_itens = pd.DataFrame(data['itens'])
            
            # Melhorar a exibição
            df_display = df_itens.copy()
            df_display['Valor Unitário (EUR)'] = df_display['valor_unit']
            
            st.markdown('<div class="data-table">', unsafe_allow_html=True)
            st.dataframe(
                df_display[['item', 'ncm', 'codigo', 'descricao', 'Valor Unitário (EUR)']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'item': st.column_config.NumberColumn('Item', width='small'),
                    'ncm': st.column_config.TextColumn('NCM', width='medium'),
                    'codigo': st.column_config.TextColumn('Código', width='medium'),
                    'descricao': st.column_config.TextColumn('Descrição', width='large'),
                    'Valor Unitário (EUR)': st.column_config.NumberColumn('Valor Unit. (EUR)', format="%.4f")
                }
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Estatísticas dos itens
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Itens", len(df_itens))
            with col2:
                if 'valor_unit' in df_itens.columns:
                    try:
                        valores = pd.to_numeric(df_itens['valor_unit'].str.replace(',', '.'), errors='coerce')
                        st.metric("Valor Médio Unitário", f"€ {valores.mean():.2f}")
                    except:
                        pass
            with col3:
                st.metric("NCMs Diferentes", df_itens['ncm'].nunique())
    
    # Seção: Documentos
    if "Documentos" in view_options and data.get('documentos'):
        st.markdown('<h2 class="sub-header">📄 Documentos do Processo</h2>', unsafe_allow_html=True)
        
        if data['documentos']:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            for i, doc in enumerate(data['documentos'], 1):
                st.write(f"**Documento {i}:** {doc}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção: Visualizações
    if "Visualizações" in view_options:
        st.markdown('<h2 class="sub-header">📈 Visualizações Analíticas</h2>', unsafe_allow_html=True)
        
        # Exemplo de visualização adicional
        if data.get('itens'):
            df_itens = pd.DataFrame(data['itens'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de barras dos itens por NCM
                if 'ncm' in df_itens.columns and 'valor_unit' in df_itens.columns:
                    try:
                        df_itens['valor_unit_numeric'] = pd.to_numeric(
                            df_itens['valor_unit'].str.replace(',', '.'), 
                            errors='coerce'
                        )
                        
                        ncm_summary = df_itens.groupby('ncm')['valor_unit_numeric'].mean().reset_index()
                        
                        fig = px.bar(
                            ncm_summary,
                            x='ncm',
                            y='valor_unit_numeric',
                            title="Valor Médio por NCM",
                            labels={'valor_unit_numeric': 'Valor Médio (EUR)', 'ncm': 'NCM'},
                            color='valor_unit_numeric',
                            color_continuous_scale='viridis'
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    except:
                        st.info("Não foi possível gerar o gráfico de valores por NCM.")
            
            with col2:
                # Distribuição dos itens
                if 'descricao' in df_itens.columns:
                    item_counts = df_itens['descricao'].value_counts().head(10)
                    
                    fig = px.bar(
                        x=item_counts.values,
                        y=item_counts.index,
                        orientation='h',
                        title="Top 10 Itens por Quantidade",
                        labels={'x': 'Quantidade', 'y': 'Descrição'},
                        color=item_counts.values,
                        color_continuous_scale='blues'
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
    
    # Botão para download dos dados
    if st.button("📥 Exportar Dados para Excel", use_container_width=True):
        # Criar arquivo Excel com múltiplas abas
        with pd.ExcelWriter('dados_importacao.xlsx', engine='openpyxl') as writer:
            if data.get('itens'):
                pd.DataFrame(data['itens']).to_excel(writer, sheet_name='Itens', index=False)
            
            if data.get('tributos'):
                tributos_df = pd.DataFrame([data['tributos']])
                tributos_df.to_excel(writer, sheet_name='Tributos', index=False)
            
            if data.get('resumo'):
                resumo_df = pd.DataFrame([data['resumo']])
                resumo_df.to_excel(writer, sheet_name='Resumo', index=False)
        
        with open('dados_importacao.xlsx', 'rb') as f:
            st.download_button(
                label="Baixar Arquivo Excel",
                data=f,
                file_name="dados_importacao.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def main():
    """Função principal do aplicativo."""
    
    st.title("📄 Analisador de Documentos de Importação")
    st.markdown("""
    Esta aplicação extrai e analisa automaticamente informações de documentos de importação em PDF.
    Carregue um arquivo PDF para visualizar os dados estruturados e análises.
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
        with st.spinner("Processando documento..."):
            success = parser.parse_all(uploaded_file)
        
        if success:
            # Mostrar dados no dashboard
            create_dashboard(parser.data)
            
            # Mostrar dados brutos em expansor
            with st.expander("📋 Visualizar Dados Brutos Extraídos"):
                st.json(parser.data)
        else:
            st.error("Não foi possível processar o documento. Verifique se o PDF contém texto legível.")
    else:
        # Tela inicial com instruções
        st.info("👆 **Por favor, faça upload de um arquivo PDF para começar.**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📋 O que este app faz:
            
            1. **Extrai dados automaticamente** de PDFs de importação
            2. **Estrutura informações** em categorias lógicas
            3. **Calcula métricas** financeiras e operacionais
            4. **Gera visualizações** interativas
            5. **Exporta dados** para Excel
            
            ### 🎯 Funcionalidades:
            - Análise de tributos e impostos
            - Monitoramento de prazos
            - Detalhamento de itens
            - Controle documental
            """)
        
        with col2:
            st.markdown("""
            ### 📊 Dados Extraídos:
            
            **📈 Financeiro:**
            - Valores CIF (USD/BRL)
            - VMLE/VMLD
            - Tributos (II, PIS, COFINS)
            
            **🚢 Logística:**
            - Datas de embarque/chegada
            - Pesos (bruto/líquido)
            - Informações de transporte
            
            **📦 Itens:**
            - Códigos NCM
            - Descrições
            - Valores unitários
            
            **📄 Documentos:**
            - Conhecimento de embarque
            - Faturas comerciais
            - Documentos complementares
            """)

if __name__ == "__main__":
    main()
