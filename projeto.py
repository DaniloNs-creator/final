import pandas as pd
import streamlit as st
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from streamlit_extras.metric_cards import style_metric_cards
import time

# Configuração inicial da página
st.set_page_config(
    page_title="Análise de KPIs Contábeis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado com animações
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
        
        * {
            font-family: 'Montserrat', sans-serif;
        }
        
        .main {
            background-color: #f8f9fa;
        }
        
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
        }
        
        .header {
            font-size: 2.5em;
            font-weight: 700;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 0.5em;
            animation: fadeIn 1.5s ease-in-out;
        }
        
        .subheader {
            font-size: 1.2em;
            color: #7f8c8d;
            text-align: center;
            margin-bottom: 2em;
            animation: slideIn 1s ease-in-out;
        }
        
        .card {
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            padding: 20px;
            background-color: white;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            animation: fadeInUp 0.8s ease-out;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }
        
        .kpi-title {
            font-size: 1em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        
        .kpi-value {
            font-size: 1.8em;
            font-weight: 700;
            color: #2c3e50;
        }
        
        .positive {
            color: #27ae60;
        }
        
        .negative {
            color: #e74c3c;
        }
        
        .neutral {
            color: #3498db;
        }
        
        .upload-section {
            background-color: white;
            border-radius: 10px;
            padding: 2em;
            margin-bottom: 2em;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            animation: fadeIn 1s ease-in-out;
        }
        
        .tabs {
            margin-bottom: 1em;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes slideIn {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes fadeInUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .stProgress > div > div > div > div {
            background-image: linear-gradient(to right, #3498db, #2ecc71);
        }
        
        .stButton>button {
            background-color: #3498db;
            color: white;
            border-radius: 8px;
            padding: 0.5em 1.5em;
            font-weight: 600;
            border: none;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            background-color: #2980b9;
            transform: scale(1.05);
        }
        
        .stSelectbox>div>div>select {
            border-radius: 8px;
            padding: 0.5em;
        }
        
        .stDataFrame {
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)

load_css()

# Header
st.markdown('<p class="header">Dashboard de Análise de KPIs Contábeis</p>', unsafe_allow_html=True)
st.markdown('<p class="subheader">Análise completa de demonstrações financeiras baseada na ECD (Layouts J100 e J155)</p>', unsafe_allow_html=True)

# Upload de arquivos
with st.container():
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("Carregar Arquivos da ECD")
    
    uploaded_files = st.file_uploader(
        "Selecione os arquivos J100 (Balanço Patrimonial) e J155 (DRE) da ECD",
        type=['txt', 'csv'],
        accept_multiple_files=True
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

# Placeholder para progresso
progress_bar = st.progress(0)
status_text = st.empty()

# Processamento dos arquivos
if uploaded_files:
    # Simular processamento com barra de progresso
    for i in range(100):
        time.sleep(0.02)
        progress_bar.progress(i + 1)
    
    status_text.success("Arquivos processados com sucesso!")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()
    
    # Dados de exemplo (substituir pelo processamento real dos arquivos)
    # Estrutura do J100 - Balanço Patrimonial
    j100_data = {
        'COD_AGR': ['J100', 'J100', 'J100', 'J100', 'J100', 'J100', 'J100', 'J100'],
        'COD_CTA': ['1', '1.01', '1.01.01', '2', '2.01', '2.01.01', '3', '3.01'],
        'DESC_CTA': ['ATIVO', 'ATIVO CIRCULANTE', 'CAIXA E EQUIVALENTES', 'PASSIVO', 'PASSIVO CIRCULANTE', 
                    'FORNECEDORES', 'PATRIMÔNIO LÍQUIDO', 'CAPITAL SOCIAL'],
        'VAL_CTA': [1000000, 600000, 150000, 700000, 400000, 200000, 300000, 300000],
        'IND_CTA': ['S', 'S', 'A', 'S', 'S', 'A', 'S', 'A']
    }
    
    # Estrutura do J155 - DRE
    j155_data = {
        'COD_AGR': ['J155', 'J155', 'J155', 'J155', 'J155', 'J155', 'J155', 'J155'],
        'COD_CTA': ['3', '3.01', '3.02', '3.03', '4', '4.01', '4.02', '4.03'],
        'DESC_CTA': ['RECEITAS', 'RECEITA BRUTA', 'DEDUÇÕES', 'RECEITA LÍQUIDA', 'CUSTOS E DESPESAS', 
                    'CUSTO MERCADORIAS VENDIDAS', 'DESPESAS OPERACIONAIS', 'DESPESAS FINANCEIRAS'],
        'VAL_CTA': [500000, 600000, 100000, 500000, 350000, 200000, 100000, 50000],
        'IND_CTA': ['S', 'A', 'A', 'A', 'S', 'A', 'A', 'A']
    }
    
    df_j100 = pd.DataFrame(j100_data)
    df_j155 = pd.DataFrame(j155_data)
    
    # Extrair valores para cálculos
    try:
        # Balanço Patrimonial
        ativo_total = df_j100[df_j100['COD_CTA'] == '1']['VAL_CTA'].values[0]
        passivo_total = df_j100[df_j100['COD_CTA'] == '2']['VAL_CTA'].values[0]
        patrimonio_liquido = df_j100[df_j100['COD_CTA'] == '3']['VAL_CTA'].values[0]
        
        # DRE
        receita_liquida = df_j155[df_j155['COD_CTA'] == '3.03']['VAL_CTA'].values[0]
        lucro_bruto = receita_liquida - df_j155[df_j155['COD_CTA'] == '4.01']['VAL_CTA'].values[0]
        custo_mercadorias_vendidas = df_j155[df_j155['COD_CTA'] == '4.01']['VAL_CTA'].values[0]
        despesas_operacionais = df_j155[df_j155['COD_CTA'] == '4.02']['VAL_CTA'].values[0]
        despesas_financeiras = df_j155[df_j155['COD_CTA'] == '4.03']['VAL_CTA'].values[0]
        lucro_operacional = lucro_bruto - despesas_operacionais
        lucro_liquido = lucro_operacional - despesas_financeiras
        
        # Cálculo dos KPIs
        margem_bruta = (lucro_bruto / receita_liquida) * 100
        margem_operacional = (lucro_operacional / receita_liquida) * 100
        margem_liquida = (lucro_liquido / receita_liquida) * 100
        roe = (lucro_liquido / patrimonio_liquido) * 100
        roa = (lucro_liquido / ativo_total) * 100
        ebitda = lucro_operacional  # Simplificado (sem depreciação/amortização)
        margem_ebitda = (ebitda / receita_liquida) * 100
        endividamento = (passivo_total / ativo_total) * 100
        liquidez_corrente = df_j100[df_j100['COD_CTA'] == '1.01']['VAL_CTA'].values[0] / df_j100[df_j100['COD_CTA'] == '2.01']['VAL_CTA'].values[0]
        
        # Exibição dos KPIs
        st.markdown("---")
        st.subheader("Indicadores Financeiros")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="Receita Líquida", value=f"R$ {receita_liquida:,.2f}")
            st.metric(label="Margem Bruta", value=f"{margem_bruta:.2f}%", delta=f"{margem_bruta - 20:.2f}% vs setor")
        
        with col2:
            st.metric(label="Lucro Líquido", value=f"R$ {lucro_liquido:,.2f}")
            st.metric(label="Margem Líquida", value=f"{margem_liquida:.2f}%", delta=f"{margem_liquida - 8:.2f}% vs setor")
        
        with col3:
            st.metric(label="ROE", value=f"{roe:.2f}%", delta=f"{roe - 15:.2f}% vs setor")
            st.metric(label="ROA", value=f"{roa:.2f}%", delta=f"{roa - 10:.2f}% vs setor")
        
        with col4:
            st.metric(label="EBITDA", value=f"R$ {ebitda:,.2f}")
            st.metric(label="Margem EBITDA", value=f"{margem_ebitda:.2f}%", delta=f"{margem_ebitda - 12:.2f}% vs setor")
        
        style_metric_cards()
        
        # Gráficos
        st.markdown("---")
        st.subheader("Visualizações")
        
        tab1, tab2, tab3 = st.tabs(["Margens", "Rentabilidade", "Estrutura"])
        
        with tab1:
            fig_margens = go.Figure()
            fig_margens.add_trace(go.Indicator(
                mode="number+gauge",
                value=margem_bruta,
                domain={'x': [0.25, 1], 'y': [0.7, 0.9]},
                title={'text': "Margem Bruta (%)"},
                gauge={
                    'shape': "bullet",
                    'axis': {'range': [None, 50]},
                    'threshold': {
                        'line': {'color': "black", 'width': 2},
                        'thickness': 0.75,
                        'value': 20},
                    'steps': [
                        {'range': [0, 20], 'color': "lightgray"},
                        {'range': [20, 50], 'color': "gray"}]}))
            
            fig_margens.add_trace(go.Indicator(
                mode="number+gauge",
                value=margem_liquida,
                domain={'x': [0.25, 1], 'y': [0.4, 0.6]},
                title={'text': "Margem Líquida (%)"},
                gauge={
                    'shape': "bullet",
                    'axis': {'range': [None, 30]},
                    'threshold': {
                        'line': {'color': "black", 'width': 2},
                        'thickness': 0.75,
                        'value': 8},
                    'steps': [
                        {'range': [0, 8], 'color': "lightgray"},
                        {'range': [8, 30], 'color': "gray"}]}))
            
            fig_margens.add_trace(go.Indicator(
                mode="number+gauge",
                value=margem_ebitda,
                domain={'x': [0.25, 1], 'y': [0.1, 0.3]},
                title={'text': "Margem EBITDA (%)"},
                gauge={
                    'shape': "bullet",
                    'axis': {'range': [None, 30]},
                    'threshold': {
                        'line': {'color': "black", 'width': 2},
                        'thickness': 0.75,
                        'value': 12},
                    'steps': [
                        {'range': [0, 12], 'color': "lightgray"},
                        {'range': [12, 30], 'color': "gray"}]}))
            
            fig_margens.update_layout(height=400, margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})
            st.plotly_chart(fig_margens, use_container_width=True)
        
        with tab2:
            fig_rentabilidade = px.bar(
                x=['ROE', 'ROA'],
                y=[roe, roa],
                labels={'x': 'Indicador', 'y': 'Percentual (%)'},
                title='Retorno sobre Patrimônio e Ativos',
                color=['ROE', 'ROA'],
                color_discrete_sequence=['#3498db', '#2ecc71']
            )
            fig_rentabilidade.update_layout(showlegend=False)
            st.plotly_chart(fig_rentabilidade, use_container_width=True)
        
        with tab3:
            fig_estrutura = go.Figure()
            fig_estrutura.add_trace(go.Indicator(
                mode="number+gauge",
                value=endividamento,
                domain={'x': [0.25, 1], 'y': [0.7, 0.9]},
                title={'text': "Endividamento (%)"},
                gauge={
                    'shape': "bullet",
                    'axis': {'range': [None, 100]},
                    'threshold': {
                        'line': {'color': "black", 'width': 2},
                        'thickness': 0.75,
                        'value': 60},
                    'steps': [
                        {'range': [0, 60], 'color': "lightgray"},
                        {'range': [60, 100], 'color': "gray"}]}))
            
            fig_estrutura.add_trace(go.Indicator(
                mode="number+gauge",
                value=liquidez_corrente,
                domain={'x': [0.25, 1], 'y': [0.4, 0.6]},
                title={'text': "Liquidez Corrente"},
                gauge={
                    'shape': "bullet",
                    'axis': {'range': [None, 2]},
                    'threshold': {
                        'line': {'color': "black", 'width': 2},
                        'thickness': 0.75,
                        'value': 1},
                    'steps': [
                        {'range': [0, 1], 'color': "lightgray"},
                        {'range': [1, 2], 'color': "gray"}]}))
            
            fig_estrutura.update_layout(height=400, margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})
            st.plotly_chart(fig_estrutura, use_container_width=True)
        
        # Análise detalhada
        st.markdown("---")
        st.subheader("Análise Detalhada")
        
        col_analise1, col_analise2 = st.columns(2)
        
        with col_analise1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**Balanço Patrimonial**")
            st.dataframe(df_j100[['COD_CTA', 'DESC_CTA', 'VAL_CTA']].style.format({'VAL_CTA': 'R$ {:.2f}'}))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_analise2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**Demonstração de Resultados**")
            st.dataframe(df_j155[['COD_CTA', 'DESC_CTA', 'VAL_CTA']].style.format({'VAL_CTA': 'R$ {:.2f}'}))
            st.markdown('</div>', unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"Erro ao processar os arquivos: {str(e)}")
        st.warning("Verifique se os arquivos estão no formato correto da ECD (Layouts J100 e J155)")

else:
    st.info("Por favor, faça o upload dos arquivos J100 e J155 da ECD para começar a análise.")
