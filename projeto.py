import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CSS para Estilização e Animação ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

    body {
        font-family: 'Roboto', sans-serif;
        background-color: #f0f2f6;
        color: #333;
    }
    .main {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        animation: fadeIn 1s ease-in-out;
    }
    .stApp {
        background-color: #f0f2f6;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease-in-out;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 700;
        border-bottom: 2px solid #4CAF50;
        padding-bottom: 5px;
        margin-bottom: 20px;
    }
    .stMarkdown p {
        font-size: 16px;
        line-height: 1.6;
    }
    .metric-card {
        background-color: #e8f5e9; /* Light green */
        border-left: 5px solid #4CAF50;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
    }
    .metric-card h3 {
        margin-top: 0;
        color: #2e7d32; /* Darker green */
        font-size: 1.1em;
        border-bottom: none;
    }
    .metric-card p {
        font-size: 1.8em;
        font-weight: bold;
        color: #333;
        margin-bottom: 0;
    }

    /* Animações */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stDataFrame {
        animation: slideIn 0.5s ease-out;
    }
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
</style>
""", unsafe_allow_html=True)

# --- Funções de Parsing da ECD (Ajuste conforme seu arquivo REAL) ---

def parse_ecd_file(uploaded_file):
    """
    Parses an uploaded ECD file to extract J100 and J155 records.
    Assumes pipe-separated values and a specific header structure.
    """
    j100_data = []
    j155_data = []
    content = uploaded_file.getvalue().decode("utf-8")

    # Split content by lines and process each line
    for line in content.splitlines():
        if line.startswith("|J100|"):
            parts = line.strip().split('|')
            # Example: |J100|COD_CTA|DESCR_CTA|VL_CTA_FINL|IND_DC|
            if len(parts) >= 6: # Ensure enough parts
                try:
                    j100_data.append({
                        'COD_CTA': parts[2],
                        'DESCR_CTA': parts[3],
                        'VL_CTA_FINL': float(parts[4]),
                        'IND_DC': parts[5]
                    })
                except ValueError:
                    st.warning(f"Linha J100 com erro de valor: {line}")
                    continue
        elif line.startswith("|J155|"):
            parts = line.strip().split('|')
            # Example: |J155|COD_CTA_RES|DESCR_CTA_RES|VL_CTA_RES|IND_VL|
            if len(parts) >= 6: # Ensure enough parts
                try:
                    j155_data.append({
                        'COD_CTA_RES': parts[2],
                        'DESCR_CTA_RES': parts[3],
                        'VL_CTA_RES': float(parts[4]),
                        'IND_VL': parts[5]
                    })
                except ValueError:
                    st.warning(f"Linha J155 com erro de valor: {line}")
                    continue
    return pd.DataFrame(j100_data), pd.DataFrame(j155_data)

# --- Funções de Cálculo de KPIs ---

def calculate_kpis(df_balanco, df_dre):
    kpis = {}

    # --- DRE Cálculos ---
    receita_bruta = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('3.01.01') & (df_dre['IND_VL'] == 'C')
    ]['VL_CTA_RES'].sum()

    deducoes_receita = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('3.01.02') & (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()

    custo_vendas = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('4.01.01') & (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()

    despesas_operacionais = df_dre[
        (df_dre['COD_CTA_RES'].str.startswith('5.01') | df_dre['COD_CTA_RES'].str.startswith('5.02')) & (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()

    receitas_financeiras = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('6.01') & (df_dre['IND_VL'] == 'C')
    ]['VL_CTA_RES'].sum()

    despesas_financeiras = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('6.02') & (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()
    
    impostos_lucro = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('9.01') & (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()

    # Receita Líquida
    receita_liquida = receita_bruta - deducoes_receita
    kpis['Receita Líquida'] = receita_liquida

    # Lucro Bruto
    lucro_bruto = receita_liquida - custo_vendas
    kpis['Lucro Bruto'] = lucro_bruto

    # Lucro Operacional (EBIT)
    lucro_operacional = lucro_bruto - despesas_operacionais
    kpis['Lucro Operacional (EBIT)'] = lucro_operacional

    # Resultado Antes dos Tributos e Participações (LAIR)
    lair = lucro_operacional + receitas_financeiras - despesas_financeiras
    kpis['Lucro Antes do IR e CSLL'] = lair

    # Lucro Líquido
    lucro_liquido = lair - impostos_lucro
    kpis['Lucro Líquido'] = lucro_liquido

    # --- Balanço Patrimonial Cálculos ---
    ativo_total = df_balanco[
        df_balanco['COD_CTA'].str.startswith('1') & (df_balanco['IND_DC'] == 'D')
    ]['VL_CTA_FINL'].sum()

    passivo_total = df_balanco[
        df_balanco['COD_CTA'].str.startswith('2') & (df_balanco['IND_DC'] == 'C')
    ]['VL_CTA_FINL'].sum()

    patrimonio_liquido = df_balanco[
        df_balanco['COD_CTA'].str.startswith('3') & (df_balanco['IND_DC'] == 'C')
    ]['VL_CTA_FINL'].sum()

    # --- KPIs Finais ---
    kpis['Margem Bruta'] = (lucro_bruto / receita_liquida) * 100 if receita_liquida != 0 else 0
    kpis['Margem Líquida'] = (lucro_liquido / receita_liquida) * 100 if receita_liquida != 0 else 0
    kpis['ROA (Retorno sobre Ativos)'] = (lucro_liquido / ativo_total) * 100 if ativo_total != 0 else 0
    kpis['ROE (Retorno sobre Patrimônio Líquido)'] = (lucro_liquido / patrimonio_liquido) * 100 if patrimonio_liquido != 0 else 0
    kpis['Giro do Ativo'] = (receita_liquida / ativo_total) if ativo_total != 0 else 0
    kpis['Liquidez Corrente'] = (
        df_balanco[df_balanco['COD_CTA'].str.startswith('1.01') & (df_balanco['IND_DC'] == 'D')]['VL_CTA_FINL'].sum() /
        df_balanco[df_balanco['COD_CTA'].str.startswith('2.01') & (df_balanco['IND_DC'] == 'C')]['VL_CTA_FINL'].sum()
    ) if df_balanco[df_balanco['COD_CTA'].str.startswith('2.01') & (df_balanco['IND_DC'] == 'C')]['VL_CTA_FINL'].sum() != 0 else 0

    return kpis

# --- Dashboard Streamlit ---
st.title("📊 Dashboard de Análise de KPIs Financeiros")

st.markdown("---")

st.sidebar.header("Upload do Arquivo ECD")
uploaded_file = st.sidebar.file_uploader("Arraste e solte ou clique para fazer upload do seu arquivo ECD (.txt)", type=["txt"])

if uploaded_file is not None:
    st.success("Arquivo carregado com sucesso!")
    
    # Processar o arquivo
    df_j100, df_j155 = parse_ecd_file(uploaded_file)

    if not df_j100.empty and not df_j155.empty:
        st.subheader("Dados Carregados")
        
        tab1, tab2 = st.tabs(["Balanço Patrimonial (J100)", "DRE (J155)"])
        with tab1:
            st.dataframe(df_j100, use_container_width=True)
        with tab2:
            st.dataframe(df_j155, use_container_width=True)

        st.markdown("---")
        st.subheader("Cálculo de KPIs Financeiros")
        
        # Calcular os KPIs
        kpis = calculate_kpis(df_j100, df_j155)
        
        # Exibir KPIs em cards
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f'<div class="metric-card"><h3>Lucro Bruto</h3><p>R$ {kpis["Lucro Bruto"]:,.2f}</p></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-card"><h3>Lucro Líquido</h3><p>R$ {kpis["Lucro Líquido"]:,.2f}</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><h3>Margem Bruta</h3><p>{kpis["Margem Bruta"]:,.2f}%</p></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-card"><h3>Margem Líquida</h3><p>{kpis["Margem Líquida"]:,.2f}%</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><h3>ROE</h3><p>{kpis["ROE (Retorno sobre Patrimônio Líquido)"]:,.2f}%</p></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-card"><h3>ROA</h3><p>{kpis["ROA (Retorno sobre Ativos)"]:,.2f}%</p></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Tabela completa de KPIs
        st.subheader("Todos os KPIs Calculados")
        kpis_df = pd.DataFrame(kpis.items(), columns=['KPI', 'Valor'])
        kpis_df['Valor Formatado'] = kpis_df.apply(
            lambda row: f"R$ {row['Valor']:,.2f}" if "R$" in str(row['KPI']) or "Lucro" in str(row['KPI']) or "Receita" in str(row['KPI']) else f"{row['Valor']:,.2f}%" if "%" in str(row['KPI']) or "Margem" in str(row['KPI']) or "ROA" in str(row['KPI']) or "ROE" in str(row['KPI']) else f"{row['Valor']:,.2f}", axis=1
        )
        st.dataframe(kpis_df[['KPI', 'Valor Formatado']], use_container_width=True)

        st.markdown("---")
        st.subheader("Visualização dos KPIs")

        # Gráfico de Margens
        fig_margens = go.Figure(data=[
            go.Bar(name='Margem Bruta', x=['Margens'], y=[kpis['Margem Bruta']], marker_color='#4CAF50'),
            go.Bar(name='Margem Líquida', x=['Margens'], y=[kpis['Margem Líquida']], marker_color='#2e7d32')
        ])
        fig_margens.update_layout(title='Margens de Lucro (%)', barmode='group', yaxis_title='Percentual (%)')
        st.plotly_chart(fig_margens, use_container_width=True)

        # Gráfico de Rentabilidade (ROE vs ROA)
        fig_rentabilidade = go.Figure(data=[
            go.Bar(name='ROE', x=['Rentabilidade'], y=[kpis['ROE (Retorno sobre Patrimônio Líquido)']], marker_color='#1E88E5'),
            go.Bar(name='ROA', x=['Rentabilidade'], y=[kpis['ROA (Retorno sobre Ativos)']], marker_color='#1565C0')
        ])
        fig_rentabilidade.update_layout(title='Retorno (%)', barmode='group', yaxis_title='Percentual (%)')
        st.plotly_chart(fig_rentabilidade, use_container_width=True)

    elif uploaded_file is not None:
        st.warning("Não foi possível extrair dados válidos dos blocos J100 e J155. Verifique o formato do arquivo.")

else:
    st.info("Aguardando o upload do arquivo ECD para iniciar a análise.")

st.markdown("---")
st.markdown("Desenvolvido com ❤️ por Seu Nome/Empresa")

