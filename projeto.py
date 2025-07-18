import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações da Página ---
st.set_page_config(layout="wide", page_title="Dashboard Contábil-Financeiro da ECD")

# --- Função para Carregar e Processar Dados (ECD) ---
@st.cache_data # Cache para evitar recarregar dados a cada interação
def load_and_process_ecd_data(uploaded_file):
    if uploaded_file is not None:
        # Aqui você precisará de uma lógica robusta para parsear o arquivo da ECD.
        # A ECD é um arquivo texto com um layout bem específico.
        # Para J100 (Balanço Patrimonial) e J150 (Demonstração de Resultado):
        # - Você pode ler o arquivo linha a linha.
        # - Identificar as linhas que começam com '|J100|' ou '|J150|'.
        # - Extrair as informações relevantes (código da conta, descrição, valor).
        # Este é o passo mais complexo e pode exigir bibliotecas específicas para parsing de arquivos de texto grandes
        # ou, se a ECD já estiver em um formato mais acessível (CSV/Excel) por uma exportação prévia, usar pd.read_csv/excel.

        # Exemplo simplificado (você precisará adaptar isso MUITO para a ECD real):
        # Supondo que você tenha um parser que gera DataFrames para J100 e J150
        try:
            # Placeholder para o parsing real da ECD
            # Em um cenário real, você teria uma função como:
            # df_j100, df_j150 = parse_ecd_file(uploaded_file)
            
            # Para demonstração, criarei DataFrames mock
            data_j100 = {
                'Conta': ['Ativo Total', 'Passivo Total', 'Patrimônio Líquido', 'Caixa e Equivalentes', 'Contas a Receber'],
                'Valor_2024': [1000000, 500000, 500000, 200000, 300000],
                'Valor_2023': [900000, 450000, 450000, 180000, 280000]
            }
            df_j100 = pd.DataFrame(data_j100)

            data_j150 = {
                'Conta': ['Receita Bruta de Vendas', 'Custo dos Produtos Vendidos', 'Lucro Bruto', 'Despesas Operacionais', 'Lucro Antes do IR/CSLL', 'Imposto de Renda e CSLL', 'Lucro Líquido'],
                'Valor_2024': [1500000, 600000, 900000, 300000, 600000, 180000, 420000],
                'Valor_2023': [1300000, 550000, 750000, 250000, 500000, 150000, 350000]
            }
            df_j150 = pd.DataFrame(data_j150)

            return df_j100, df_j150
        except Exception as e:
            st.error(f"Erro ao processar o arquivo da ECD: {e}")
            return pd.DataFrame(), pd.DataFrame() # Retorna DataFrames vazios em caso de erro
    return pd.DataFrame(), pd.DataFrame()


# --- Título do Dashboard ---
st.title("📊 Dashboard Contábil-Financeiro da ECD")
st.markdown("Analise os principais KPIs contábeis e financeiros com base nos registros J100 (Balanço Patrimonial) e J150 (Demonstração de Resultado) da ECD.")

# --- Upload do Arquivo da ECD ---
st.sidebar.header("Upload da ECD")
uploaded_file = st.sidebar.file_uploader("Carregue seu arquivo TXT da ECD", type=["txt"])

df_j100, df_j150 = load_and_process_ecd_data(uploaded_file)

if not df_j100.empty and not df_j150.empty:
    st.success("Dados da ECD carregados e processados com sucesso!")

    # --- Análise e Cálculo de KPIs ---
    st.sidebar.header("Configurações da Análise")
    ano_analise = st.sidebar.selectbox("Selecione o Ano para Análise", options=['2024', '2023'], index=0)

    st.header(f"Resultados para o Ano: {ano_analise}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Balanço Patrimonial (J100)")
        st.dataframe(df_j100[['Conta', f'Valor_{ano_analise}']].set_index('Conta'))

    with col2:
        st.subheader("Demonstração de Resultado (J150)")
        st.dataframe(df_j150[['Conta', f'Valor_{ano_analise}']].set_index('Conta'))
    
    st.markdown("---")

    st.header("Principais KPIs Contábeis e Financeiros")

    # Função para buscar valor de um DataFrame
    def get_value(df, account_name, year_col):
        try:
            return df[df['Conta'] == account_name][year_col].iloc[0]
        except IndexError:
            return 0 # Ou NaN, dependendo de como você quer tratar a ausência

    # Obtenção dos valores para o ano selecionado
    receita_bruta = get_value(df_j150, 'Receita Bruta de Vendas', f'Valor_{ano_analise}')
    custo_produtos_vendidos = get_value(df_j150, 'Custo dos Produtos Vendidos', f'Valor_{ano_analise}')
    lucro_bruto = get_value(df_j150, 'Lucro Bruto', f'Valor_{ano_analise}')
    lucro_liquido = get_value(df_j150, 'Lucro Líquido', f'Valor_{ano_analise}')
    patrimonio_liquido = get_value(df_j100, 'Patrimônio Líquido', f'Valor_{ano_analise}')
    ativo_total = get_value(df_j100, 'Ativo Total', f'Valor_{ano_analise}')

    # Cálculo dos KPIs
    margem_bruta = (lucro_bruto / receita_bruta) * 100 if receita_bruta != 0 else 0
    margem_liquida = (lucro_liquido / receita_bruta) * 100 if receita_bruta != 0 else 0
    roe = (lucro_liquido / patrimonio_liquido) * 100 if patrimonio_liquido != 0 else 0
    giro_ativo = (receita_bruta / ativo_total) if ativo_total != 0 else 0
    endividamento_total = (get_value(df_j100, 'Passivo Total', f'Valor_{ano_analise}') / ativo_total) * 100 if ativo_total != 0 else 0
    
    # Criando um DataFrame para exibir os KPIs
    kpis_data = {
        'KPI': ['Lucro Bruto', 'Lucro Líquido', 'Margem Bruta (%)', 'Margem Líquida (%)', 'ROE (%)', 'Giro do Ativo (Vezes)', 'Endividamento Total (%)'],
        'Valor': [lucro_bruto, lucro_liquido, margem_bruta, margem_liquida, roe, giro_ativo, endividamento_total]
    }
    df_kpis = pd.DataFrame(kpis_data)
    
    st.subheader("Visão Geral dos KPIs")
    st.dataframe(df_kpis.set_index('KPI'))

    # --- Visualizações Gráficas ---
    st.markdown("---")
    st.header("Visualizações Gráficas")

    # Gráfico de evolução de Lucro Bruto e Lucro Líquido (se houver mais anos)
    if len(df_j150.columns) > 2: # Se tiver mais de um ano para comparar
        df_lucros = df_j150[df_j150['Conta'].isin(['Lucro Bruto', 'Lucro Líquido'])]
        df_lucros_melted = df_lucros.melt(id_vars=['Conta'], var_name='Ano', value_name='Valor')
        df_lucros_melted['Ano'] = df_lucros_melted['Ano'].str.replace('Valor_', '')

        fig_lucros = px.line(df_lucros_melted, x='Ano', y='Valor', color='Conta', 
                             title='Evolução do Lucro Bruto e Lucro Líquido',
                             labels={'Valor': 'Valor (R$)', 'Ano': 'Ano'})
        fig_lucros.update_traces(mode='lines+markers')
        st.plotly_chart(fig_lucros, use_container_width=True)

    # Gráfico de pizza para composição do Ativo ou Passivo
    st.subheader("Composição do Balanço Patrimonial")
    tipo_bp = st.selectbox("Selecione o tipo de Balanço Patrimonial para visualizar", options=['Ativo', 'Passivo e PL'])

    if tipo_bp == 'Ativo':
        # Adapte isso para pegar as contas de ativo específicas do seu parsing da ECD
        df_ativo = df_j100[df_j100['Conta'].isin(['Caixa e Equivalentes', 'Contas a Receber'])] # Exemplo
        if not df_ativo.empty:
            fig_ativo = px.pie(df_ativo, values=f'Valor_{ano_analise}', names='Conta', 
                               title=f'Composição do Ativo ({ano_analise})')
            st.plotly_chart(fig_ativo, use_container_width=True)
        else:
            st.info("Dados de Ativo não disponíveis para visualização detalhada.")
    else:
        # Adapte para contas de passivo e PL
        df_passivo_pl = df_j100[df_j100['Conta'].isin(['Passivo Total', 'Patrimônio Líquido'])] # Exemplo
        if not df_passivo_pl.empty:
            fig_passivo = px.pie(df_passivo_pl, values=f'Valor_{ano_analise}', names='Conta', 
                                 title=f'Composição do Passivo e Patrimônio Líquido ({ano_analise})')
            st.plotly_chart(fig_passivo, use_container_width=True)
        else:
            st.info("Dados de Passivo e Patrimônio Líquido não disponíveis para visualização detalhada.")

else:
    st.info("Por favor, carregue um arquivo da ECD para iniciar a análise.")

st.markdown("---")
st.markdown("Desenvolvido para análise de KPIs contábeis e financeiros com base na ECD.")

