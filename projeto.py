import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuração inicial da página
st.set_page_config(page_title="Dashboard ECD", page_icon="📊", layout="wide")

# Título do dashboard
st.title("📊 Análise de KPIs Contábeis e Financeiros - ECD")

# Simulação de dados (substitua por seus dados reais da ECD)
@st.cache_data
def load_data():
    # Dados do registro J100 (Plano de Contas)
    j100_data = {
        'COD_CONTA': ['1', '1.1', '1.1.1', '1.1.2', '2', '2.1', '2.1.1', '3', '3.1'],
        'DESCR_CONTA': ['ATIVO', 'ATIVO CIRCULANTE', 'CAIXA', 'BANCOS', 'PASSIVO', 'PASSIVO CIRCULANTE', 
                       'FORNECEDORES', 'PATRIMÔNIO LÍQUIDO', 'CAPITAL SOCIAL'],
        'NIVEL': [1, 2, 3, 3, 1, 2, 3, 1, 2],
        'TIPO_CONTA': ['S', 'S', 'A', 'A', 'S', 'S', 'A', 'S', 'A']
    }
    
    # Dados do registro J150 (Saldos Periódicos)
    j150_data = {
        'COD_CONTA': ['1.1.1', '1.1.2', '2.1.1', '3.1'] * 12,
        'DATA': [datetime(2023, m, 1).strftime('%Y-%m-%d') for m in range(1, 13) for _ in range(4)],
        'VALOR': [
            50000, 150000, 80000, 300000,  # Jan
            55000, 145000, 85000, 310000,  # Fev
            60000, 140000, 90000, 320000,  # Mar
            65000, 135000, 95000, 330000,  # Abr
            70000, 130000, 100000, 340000,  # Mai
            75000, 125000, 105000, 350000,  # Jun
            80000, 120000, 110000, 360000,  # Jul
            85000, 115000, 115000, 370000,  # Ago
            90000, 110000, 120000, 380000,  # Set
            95000, 105000, 125000, 390000,  # Out
            100000, 100000, 130000, 400000, # Nov
            105000, 95000, 135000, 410000   # Dez
        ],
        'TIPO_SALDO': ['D'] * 48
    }
    
    j100_df = pd.DataFrame(j100_data)
    j150_df = pd.DataFrame(j150_data)
    j150_df['DATA'] = pd.to_datetime(j150_df['DATA'])
    
    # Merge dos dados para ter as descrições das contas
    merged_df = pd.merge(j150_df, j100_df, on='COD_CONTA', how='left')
    
    return j100_df, j150_df, merged_df

j100_df, j150_df, merged_df = load_data()

# Sidebar com filtros
st.sidebar.header("Filtros")
start_date = st.sidebar.date_input("Data inicial", value=merged_df['DATA'].min())
end_date = st.sidebar.date_input("Data final", value=merged_df['DATA'].max())

contas_selecionadas = st.sidebar.multiselect(
    "Selecione as contas",
    options=merged_df['DESCR_CONTA'].unique(),
    default=merged_df['DESCR_CONTA'].unique()
)

# Aplicar filtros
filtered_df = merged_df[
    (merged_df['DATA'] >= pd.to_datetime(start_date)) & 
    (merged_df['DATA'] <= pd.to_datetime(end_date)) &
    (merged_df['DESCR_CONTA'].isin(contas_selecionadas))
]

# Layout principal
tab1, tab2, tab3 = st.tabs(["Visão Geral", "Análise por Conta", "Indicadores Financeiros"])

with tab1:
    st.header("Visão Geral das Contas")
    
    # KPIs principais
    col1, col2, col3 = st.columns(3)
    
    total_ativos = filtered_df[filtered_df['COD_CONTA'].str.startswith('1')]['VALOR'].sum()
    total_passivos = filtered_df[filtered_df['COD_CONTA'].str.startswith('2')]['VALOR'].sum()
    total_pl = filtered_df[filtered_df['COD_CONTA'].str.startswith('3')]['VALOR'].sum()
    
    col1.metric("Total Ativos", f"R$ {total_ativos:,.2f}")
    col2.metric("Total Passivos", f"R$ {total_passivos:,.2f}")
    col3.metric("Patrimônio Líquido", f"R$ {total_pl:,.2f}")
    
    # Gráfico de evolução dos saldos
    st.subheader("Evolução dos Saldos")
    
    fig = px.line(
        filtered_df,
        x='DATA',
        y='VALOR',
        color='DESCR_CONTA',
        title='Evolução dos Saldos por Conta',
        labels={'VALOR': 'Valor (R$)', 'DATA': 'Data'}
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Análise por Conta")
    
    # Selecionar conta para análise detalhada
    conta_selecionada = st.selectbox(
        "Selecione uma conta para análise detalhada",
        options=filtered_df['DESCR_CONTA'].unique()
    )
    
    conta_df = filtered_df[filtered_df['DESCR_CONTA'] == conta_selecionada]
    
    if not conta_df.empty:
        col1, col2 = st.columns(2)
        
        # Gráfico de linha para a conta selecionada
        with col1:
            st.subheader(f"Evolução da conta {conta_selecionada}")
            fig = px.line(
                conta_df,
                x='DATA',
                y='VALOR',
                title=f'Evolução de {conta_selecionada}',
                labels={'VALOR': 'Valor (R$)', 'DATA': 'Data'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Estatísticas da conta
        with col2:
            st.subheader("Estatísticas")
            variacao = ((conta_df['VALOR'].iloc[-1] - conta_df['VALOR'].iloc[0]) / conta_df['VALOR'].iloc[0]) * 100
            st.metric("Saldo Inicial", f"R$ {conta_df['VALOR'].iloc[0]:,.2f}")
            st.metric("Saldo Final", f"R$ {conta_df['VALOR'].iloc[-1]:,.2f}")
            st.metric("Variação (%)", f"{variacao:.2f}%")
            
            st.write("---")
            st.write("**Resumo estatístico:**")
            st.write(conta_df['VALOR'].describe().to_frame().T)
    else:
        st.warning("Nenhum dado disponível para a conta selecionada no período.")

with tab3:
    st.header("Indicadores Financeiros")
    
    # Calcular indicadores
    ativo_circulante = filtered_df[filtered_df['COD_CONTA'].isin(['1.1.1', '1.1.2'])]['VALOR'].sum()
    passivo_circulante = filtered_df[filtered_df['COD_CONTA'] == '2.1.1']['VALOR'].sum()
    liquidez_geral = ativo_circulante / passivo_circulante if passivo_circulante != 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Liquidez Geral", f"{liquidez_geral:.2f}")
    col2.metric("Endividamento", f"{(total_passivos / total_ativos * 100 if total_ativos != 0 else 0):.2f}%")
    col3.metric("Rentabilidade PL", f"{(total_pl / total_ativos * 100 if total_ativos != 0 else 0):.2f}%")
    
    # Gráfico de composição do ativo e passivo
    st.subheader("Composição do Balanço")
    
    composicao_df = filtered_df.groupby('COD_CONTA').agg({'VALOR': 'mean', 'DESCR_CONTA': 'first'}).reset_index()
    composicao_df = composicao_df[composicao_df['COD_CONTA'].str.len() == 3]  # Contas de nível 3
    
    fig = px.pie(
        composicao_df,
        values='VALOR',
        names='DESCR_CONTA',
        title='Composição Média das Contas'
    )
    st.plotly_chart(fig, use_container_width=True)

# Rodapé
st.sidebar.markdown("---")
st.sidebar.markdown("**Fonte:** Dados simulados baseados na ECD (Registros J100 e J150)")
st.sidebar.markdown("**Desenvolvido por:** [Seu Nome]")
