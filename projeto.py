import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Análise de KPIs Contábeis - ECD",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título do dashboard
st.title("📊 Dashboard de Análise de KPIs Contábeis e Financeiros - ECD")
st.markdown("Análise dos principais indicadores com base nos registros J100 e J150 da Escrituração Contábil Digital")

# Dados de exemplo (substituir pela leitura real da ECD)
@st.cache_data
def carregar_dados():
    # Simulando dados da ECD - Registros J100 e J150
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    anos = [2022, 2023]
    
    dados = []
    for ano in anos:
        for mes in meses:
            receita_bruta = np.random.uniform(50000, 200000)
            custos = receita_bruta * np.random.uniform(0.4, 0.7)
            despesas_operacionais = receita_bruta * np.random.uniform(0.1, 0.3)
            despesas_financeiras = receita_bruta * np.random.uniform(0.01, 0.05)
            impostos = receita_bruta * np.random.uniform(0.1, 0.2)
            patrimonio_liquido = np.random.uniform(300000, 500000)
            
            dados.append({
                'Ano': ano,
                'Mês': mes,
                'Receita Bruta': receita_bruta,
                'Custos': custos,
                'Despesas Operacionais': despesas_operacionais,
                'Despesas Financeiras': despesas_financeiras,
                'Impostos': impostos,
                'Patrimônio Líquido': patrimonio_liquido
            })
    
    df = pd.DataFrame(dados)
    
    # Calculando KPIs
    df['Lucro Bruto'] = df['Receita Bruta'] - df['Custos']
    df['Lucro Operacional'] = df['Lucro Bruto'] - df['Despesas Operacionais']
    df['Lucro Antes IR'] = df['Lucro Operacional'] - df['Despesas Financeiras']
    df['Lucro Líquido'] = df['Lucro Antes IR'] - df['Impostos']
    df['Margem Bruta'] = df['Lucro Bruto'] / df['Receita Bruta']
    df['Margem Operacional'] = df['Lucro Operacional'] / df['Receita Bruta']
    df['Margem Líquida'] = df['Lucro Líquido'] / df['Receita Bruta']
    df['ROE'] = df['Lucro Líquido'] / df['Patrimônio Líquido']
    
    return df

df = carregar_dados()

# Sidebar - Filtros
st.sidebar.header("Filtros")
ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=df['Ano'].unique())
meses_selecionados = st.sidebar.multiselect(
    "Selecione os meses", 
    options=df['Mês'].unique(), 
    default=df['Mês'].unique()
)

# Filtrando dados
dados_filtrados = df[(df['Ano'] == ano_selecionado) & (df['Mês'].isin(meses_selecionados))]

# Layout principal
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Visão Geral", 
    "💰 Lucratividade", 
    "📊 Rentabilidade", 
    "🧮 ECD - Registros J100/J150"
])

with tab1:
    st.header("Visão Geral dos Principais KPIs")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Receita Bruta Média", f"R$ {dados_filtrados['Receita Bruta'].mean():,.2f}")
    with col2:
        st.metric("Lucro Líquido Médio", f"R$ {dados_filtrados['Lucro Líquido'].mean():,.2f}")
    with col3:
        st.metric("Margem Líquida Média", f"{dados_filtrados['Margem Líquida'].mean()*100:.2f}%")
    with col4:
        st.metric("ROE Médio", f"{dados_filtrados['ROE'].mean()*100:.2f}%")
    
    # Gráfico de evolução da receita e lucro
    fig = px.line(
        dados_filtrados, 
        x='Mês', 
        y=['Receita Bruta', 'Lucro Líquido'],
        title='Evolução da Receita Bruta e Lucro Líquido',
        labels={'value': 'Valor (R$)', 'variable': 'Conta'},
        color_discrete_map={'Receita Bruta': '#1f77b4', 'Lucro Líquido': '#ff7f0e'}
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Indicadores de Lucratividade")
    
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            dados_filtrados,
            x='Mês',
            y=['Lucro Bruto', 'Lucro Operacional', 'Lucro Líquido'],
            title='Composição do Lucro',
            labels={'value': 'Valor (R$)', 'variable': 'Tipo de Lucro'},
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.line(
            dados_filtrados,
            x='Mês',
            y=['Margem Bruta', 'Margem Operacional', 'Margem Líquida'],
            title='Evolução das Margens',
            labels={'value': 'Percentual (%)', 'variable': 'Tipo de Margem'},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Análise de composição
    st.subheader("Análise de Composição")
    mes_analise = st.selectbox("Selecione o mês para análise detalhada", options=dados_filtrados['Mês'].unique())
    
    dados_mes = dados_filtrados[dados_filtrados['Mês'] == mes_analise].iloc[0]
    
    composicao = pd.DataFrame({
        'Item': ['Receita Bruta', 'Custos', 'Despesas Operacionais', 'Despesas Financeiras', 'Impostos'],
        'Valor': [
            dados_mes['Receita Bruta'],
            -dados_mes['Custos'],
            -dados_mes['Despesas Operacionais'],
            -dados_mes['Despesas Financeiras'],
            -dados_mes['Impostos']
        ],
        'Tipo': ['Receita', 'Custo', 'Despesa', 'Despesa', 'Imposto']
    })
    
    fig = px.treemap(
        composicao,
        path=['Tipo', 'Item'],
        values='Valor',
        title=f'Composição do Resultado - {mes_analise}'
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("Indicadores de Rentabilidade")
    
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            dados_filtrados,
            x='Mês',
            y='ROE',
            title='Retorno sobre Patrimônio Líquido (ROE)',
            labels={'ROE': 'ROE (%)'},
            text=[f"{x*100:.1f}%" for x in dados_filtrados['ROE']]
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.scatter(
            dados_filtrados,
            x='Receita Bruta',
            y='Lucro Líquido',
            size='Patrimônio Líquido',
            color='Mês',
            title='Relação entre Receita, Lucro e Patrimônio',
            labels={'Receita Bruta': 'Receita Bruta (R$)', 'Lucro Líquido': 'Lucro Líquido (R$)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Análise de rentabilidade
    st.subheader("Análise Comparativa")
    
    fig = px.parallel_coordinates(
        dados_filtrados,
        dimensions=['Margem Bruta', 'Margem Operacional', 'Margem Líquida', 'ROE'],
        color='ROE',
        labels={
            'Margem Bruta': 'Margem Bruta',
            'Margem Operacional': 'Margem Operacional',
            'Margem Líquida': 'Margem Líquida',
            'ROE': 'ROE'
        },
        title='Comparação entre Diferentes Indicadores de Rentabilidade'
    )
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("Análise dos Registros J100 e J150 da ECD")
    st.markdown("""
    ### Estrutura dos Registros J100 e J150
    - **J100**: Balancete Diário - Contas de Resultado
    - **J150**: Demonstração do Resultado do Exercício (DRE)
    """)
    
    # Simulação de dados da ECD
    st.subheader("Dados Simulados dos Registros J100 (Balancete Diário)")
    
    contas_j100 = pd.DataFrame({
        'Conta': [
            '3 - Receitas', '3.1 - Receita Bruta', '3.2 - Deduções',
            '4 - Custos', '4.1 - Custo dos Produtos Vendidos',
            '5 - Despesas', '5.1 - Despesas Operacionais', '5.2 - Despesas Financeiras',
            '6 - Impostos', '6.1 - IRPJ', '6.2 - CSLL'
        ],
        'Débito': [0, 0, 0, 
                  dados_mes['Custos'], dados_mes['Custos'],
                  dados_mes['Despesas Operacionais'] + dados_mes['Despesas Financeiras'],
                  dados_mes['Despesas Operacionais'], dados_mes['Despesas Financeiras'],
                  dados_mes['Impostos'], dados_mes['Impostos']*0.6, dados_mes['Impostos']*0.4],
        'Crédito': [dados_mes['Receita Bruta'], dados_mes['Receita Bruta'], 0,
                   0, 0,
                   0, 0, 0,
                   0, 0, 0],
        'Saldo': [dados_mes['Receita Bruta'], dados_mes['Receita Bruta'], 0,
                 -dados_mes['Custos'], -dados_mes['Custos'],
                 -(dados_mes['Despesas Operacionais'] + dados_mes['Despesas Financeiras']),
                 -dados_mes['Despesas Operacionais'], -dados_mes['Despesas Financeiras'],
                 -dados_mes['Impostos'], -dados_mes['Impostos']*0.6, -dados_mes['Impostos']*0.4]
    })
    
    st.dataframe(contas_j100.style.format({
        'Débito': 'R$ {:.2f}',
        'Crédito': 'R$ {:.2f}',
        'Saldo': 'R$ {:.2f}'
    }), use_container_width=True)
    
    st.subheader("Dados Simulados dos Registros J150 (DRE)")
    
    dre = pd.DataFrame({
        'Descrição': [
            'Receita Bruta de Vendas',
            '(-) Deduções',
            '(=) Receita Líquida',
            '(-) Custo dos Produtos Vendidos',
            '(=) Lucro Bruto',
            '(-) Despesas Operacionais',
            '(=) Lucro Operacional',
            '(-) Despesas Financeiras',
            '(=) Lucro Antes do IR',
            '(-) Provisão para IR e CSLL',
            '(=) Lucro Líquido'
        ],
        'Valor': [
            dados_mes['Receita Bruta'],
            0,
            dados_mes['Receita Bruta'],
            dados_mes['Custos'],
            dados_mes['Lucro Bruto'],
            dados_mes['Despesas Operacionais'],
            dados_mes['Lucro Operacional'],
            dados_mes['Despesas Financeiras'],
            dados_mes['Lucro Antes IR'],
            dados_mes['Impostos'],
            dados_mes['Lucro Líquido']
        ]
    })
    
    st.dataframe(dre.style.format({'Valor': 'R$ {:.2f}'}), use_container_width=True)

# Rodapé
st.markdown("---")
st.markdown("**Dashboard desenvolvido para análise dos principais KPIs contábeis e financeiros com base na ECD**")
st.markdown(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
