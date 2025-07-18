import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CSS para Estilização e Animação ---
# Importante: Este bloco de CSS deve estar impecável.
# Verifique se não há aspas triplas dentro dele que não sejam de fechamento
# e se não há barras invertidas (\) no final de linhas que não estejam escapadas (\\).
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
""", unsafe_allow_html=True) # <<< Esta é a linha onde o """ deve fechar.

# --- Funções de Parsing da ECD (Ajuste conforme seu arquivo REAL) ---

def parse_ecd_file(uploaded_file):
    """
    Parses an uploaded ECD file to extract J100 and J155 records.
    Assumes pipe-separated values and a specific header structure.
    Includes robust error handling for UnicodeDecodeError and parsing errors.
    """
    j100_data = []
    j155_data = []
    content = None

    # Tenta decodificar o arquivo com diferentes codificações
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            # st.sidebar.info(f"Tentando decodificar com {encoding}...") # Debugging
            content = uploaded_file.getvalue().decode(encoding)
            st.sidebar.success(f"Arquivo decodificado com sucesso usando {encoding}!")
            break # Se decodificar, sai do loop
        except UnicodeDecodeError:
            # st.sidebar.warning(f"Falha na decodificação com {encoding}. Tentando a próxima...") # Debugging
            continue # Tenta a próxima codificação
        except Exception as e:
            st.sidebar.error(f"Ocorreu um erro inesperado ao tentar decodificar com {encoding}: {e}")
            return pd.DataFrame(), pd.DataFrame() # Retorna vazios em caso de erro grave

    if content is None:
        st.error("Não foi possível decodificar o arquivo com as codificações testadas (UTF-8, Latin-1, CP1252). Por favor, verifique a codificação do seu arquivo ECD.")
        return pd.DataFrame(), pd.DataFrame() # Retorna DataFrames vazios se nenhuma codificação funcionar

    # Processar o conteúdo decodificado
    for line in content.splitlines():
        # Remove caracteres de quebra de linha e espaços extras, e garante que a linha não esteja vazia
        line = line.strip() 
        if not line:
            continue # Pula linhas vazias

        if line.startswith("|J100|"):
            parts = line.split('|')
            # Exemplo de formato: |J100|COD_CTA|DESCR_CTA|VL_CTA_FINL|IND_DC|
            # Índice 0 é vazio antes do primeiro |, Índice 1 é "J100".
            # Então, os dados úteis começam do Índice 2
            if len(parts) >= 6: # Garante que há partes suficientes para evitar IndexError
                try:
                    j100_data.append({
                        'COD_CTA': parts[2],
                        'DESCR_CTA': parts[3],
                        'VL_CTA_FINL': float(parts[4].replace(',', '.')), # Trata vírgula como separador decimal
                        'IND_DC': parts[5]
                    })
                except ValueError:
                    st.warning(f"Linha J100 com erro de valor numérico. Pulando linha: {line}")
                    continue
                except IndexError:
                    st.warning(f"Linha J100 com formato inesperado (menos colunas que o esperado). Pulando linha: {line}")
                    continue
        elif line.startswith("|J155|"):
            parts = line.split('|')
            # Exemplo de formato: |J155|COD_CTA_RES|DESCR_CTA_RES|VL_CTA_RES|IND_VL|
            if len(parts) >= 6: # Garante que há partes suficientes
                try:
                    j155_data.append({
                        'COD_CTA_RES': parts[2],
                        'DESCR_CTA_RES': parts[3],
                        'VL_CTA_RES': float(parts[4].replace(',', '.')), # Trata vírgula como separador decimal
                        'IND_VL': parts[5]
                    })
                except ValueError:
                    st.warning(f"Linha J155 com erro de valor numérico. Pulando linha: {line}")
                    continue
                except IndexError:
                    st.warning(f"Linha J155 com formato inesperado (menos colunas que o esperado). Pulando linha: {line}")
                    continue
    
    return pd.DataFrame(j100_data), pd.DataFrame(j155_data)

# --- Funções de Cálculo de KPIs ---

def calculate_kpis(df_balanco, df_dre):
    kpis = {}

    # --- DRE Cálculos ---
    # É fundamental que os códigos de conta abaixo correspondam EXATAMENTE aos do seu arquivo ECD.
    # Ajuste os prefixos ('3.01.01', etc.) conforme necessário para o seu plano de contas.

    # Receita Bruta de Vendas (Contas iniciadas com 3.01.01 e indicador 'C' - Crédito)
    receita_bruta = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('3.01.01') & (df_dre['IND_VL'] == 'C')
    ]['VL_CTA_RES'].sum()

    # Deduções da Receita Bruta (Contas iniciadas com 3.01.02 e indicador 'D' - Débito)
    deducoes_receita = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('3.01.02') & (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()

    # Custo dos Produtos/Serviços Vendidos (Contas iniciadas com 4.01.01 e indicador 'D')
    custo_vendas = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('4.01.01') & (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()

    # Despesas Operacionais (ex: Despesas com Vendas, Administrativas, outras operacionais)
    # Ajuste os prefixos de acordo com as suas contas reais para despesas operacionais.
    despesas_operacionais = df_dre[
        (df_dre['COD_CTA_RES'].str.startswith('5.01') | # Ex: Despesas com Vendas
         df_dre['COD_CTA_RES'].str.startswith('5.02') | # Ex: Despesas Administrativas
         df_dre['COD_CTA_RES'].str.startswith('5.03')) & # Outras Despesas Operacionais, se houver
        (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()

    # Receitas Financeiras (Contas iniciadas com 6.01 e indicador 'C')
    receitas_financeiras = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('6.01') & (df_dre['IND_VL'] == 'C')
    ]['VL_CTA_RES'].sum()

    # Despesas Financeiras (Contas iniciadas com 6.02 e indicador 'D')
    despesas_financeiras = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('6.02') & (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()
    
    # Impostos sobre o Lucro (IRPJ e CSLL - Contas iniciadas com 9.01 e indicador 'D')
    impostos_lucro = df_dre[
        df_dre['COD_CTA_RES'].str.startswith('9.01') & (df_dre['IND_VL'] == 'D')
    ]['VL_CTA_RES'].sum()

    # Receita Líquida
    receita_liquida = receita_bruta - deducoes_receita
    kpis['Receita Líquida'] = receita_liquida

    # Lucro Bruto
    lucro_bruto = receita_liquida - custo_vendas
    kpis['Lucro Bruto'] = lucro_bruto

    # Margem de Contribuição (Exemplo Simplificado - Adapte se tiver mais detalhes de custos variáveis)
    # Aqui estamos assumindo Custo dos Produtos Vendidos como o principal Custo Variável.
    # Em uma análise real, você precisaria identificar todas as despesas variáveis.
    custos_variaveis = custo_vendas # + Outros custos variáveis se existirem (ex: comissões de vendas)
    margem_contribuicao = receita_liquida - custos_variaveis
    kpis['Margem de Contribuição'] = margem_contribuicao
    kpis['% Margem de Contribuição'] = (margem_contribuicao / receita_liquida) * 100 if receita_liquida != 0 else 0


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
    # Ativo Total (Contas iniciadas com 1 e indicador 'D')
    ativo_total = df_balanco[
        df_balanco['COD_CTA'].str.startswith('1') & (df_balanco['IND_DC'] == 'D')
    ]['VL_CTA_FINL'].sum()

    # Passivo Total (Contas iniciadas com 2 e indicador 'C')
    passivo_total = df_balanco[
        df_balanco['COD_CTA'].str.startswith('2') & (df_balanco['IND_DC'] == 'C')
    ]['VL_CTA_FINL'].sum()

    # Patrimônio Líquido (Contas iniciadas com 3 e indicador 'C')
    patrimonio_liquido = df_balanco[
        df_balanco['COD_CTA'].str.startswith('3') & (df_balanco['IND_DC'] == 'C')
    ]['VL_CTA_FINL'].sum()
    
    # Ativo Circulante (Contas iniciadas com 1.01 e indicador 'D')
    ativo_circulante = df_balanco[
        df_balanco['COD_CTA'].str.startswith('1.01') & (df_balanco['IND_DC'] == 'D')
    ]['VL_CTA_FINL'].sum()

    # Passivo Circulante (Contas iniciadas com 2.01 e indicador 'C')
    passivo_circulante = df_balanco[
        df_balanco['COD_CTA'].str.startswith('2.01') & (df_balanco['IND_DC'] == 'C')
    ]['VL_CTA_FINL'].sum()

    # --- KPIs Finais ---
    kpis['Margem Bruta'] = (lucro_bruto / receita_liquida) * 100 if receita_liquida != 0 else 0
    kpis['Margem Líquida'] = (lucro_liquido / receita_liquida) * 100 if receita_liquida != 0 else 0
    kpis['ROA (Retorno sobre Ativos)'] = (lucro_liquido / ativo_total) * 100 if ativo_total != 0 else 0
    kpis['ROE (Retorno sobre Patrimônio Líquido)'] = (lucro_liquido / patrimonio_liquido) * 100 if patrimonio_liquido != 0 else 0
    kpis['Giro do Ativo'] = (receita_liquida / ativo_total) if ativo_total != 0 else 0
    
    # Liquidez Corrente = Ativo Circulante / Passivo Circulante
    kpis['Liquidez Corrente'] = (ativo_circulante / passivo_circulante) if passivo_circulante != 0 else 0

    return kpis

# --- Dashboard Streamlit ---
# Configurações da página (deve ser no início do script, antes de qualquer st.write/st.sidebar)
st.set_page_config(layout="wide", page_title="Dashboard de KPIs Financeiros", page_icon="📊")

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
        
        # Tabs para visualizar os DataFrames brutos
        tab1, tab2 = st.tabs(["Balanço Patrimonial (J100)", "DRE (J155)"])
        with tab1:
            st.dataframe(df_j100, use_container_width=True)
        with tab2:
            st.dataframe(df_j155, use_container_width=True)

        st.markdown("---")
        st.subheader("Cálculo de KPIs Financeiros")
        
        # Calcular os KPIs
        kpis = calculate_kpis(df_j100, df_j155)
        
        # Função auxiliar para exibir os cards de métricas
        def display_metric_card(col, title, value, is_percentage=False):
            with col:
                if is_percentage:
                    st.markdown(f'<div class="metric-card"><h3>{title}</h3><p>{value:,.2f}%</p></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="metric-card"><h3>{title}</h3><p>R$ {value:,.2f}</p></div>', unsafe_allow_html=True)

        # Exibir KPIs em cards
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        
        # Linha 1 de KPIs
        col1, col2, col3, col4 = st.columns(4)
        display_metric_card(col1, "Lucro Bruto", kpis["Lucro Bruto"])
        display_metric_card(col2, "Margem Bruta", kpis["Margem Bruta"], is_percentage=True)
        display_metric_card(col3, "Lucro Líquido", kpis["Lucro Líquido"])
        display_metric_card(col4, "Margem Líquida", kpis["Margem Líquida"], is_percentage=True)
        
        # Linha 2 de KPIs
        col5, col6, col7, col8 = st.columns(4)
        display_metric_card(col5, "ROE", kpis["ROE (Retorno sobre Patrimônio Líquido)"], is_percentage=True)
        display_metric_card(col6, "ROA", kpis["ROA (Retorno sobre Ativos)"], is_percentage=True)
        display_metric_card(col7, "Margem Contribuição", kpis["% Margem de Contribuição"], is_percentage=True)
        display_metric_card(col8, "Liquidez Corrente", kpis["Liquidez Corrente"])

        st.markdown('</div>', unsafe_allow_html=True) # Fechamento do container de métricas

        # Tabela completa de KPIs
        st.subheader("Todos os KPIs Calculados")
        kpis_df = pd.DataFrame(kpis.items(), columns=['KPI', 'Valor'])
        
        # Formatação dos valores na tabela
        def format_kpi_value(row):
            if "Margem" in row['KPI'] or "ROE" in row['KPI'] or "ROA" in row['KPI'] or "Percentual" in row['KPI']:
                return f"{row['Valor']:,.2f}%"
            elif "Lucro" in row['KPI'] or "Receita" in row['KPI'] or "Contribuição" in row['KPI']: # Incluindo Margem de Contribuição aqui
                return f"R$ {row['Valor']:,.2f}"
            else: # Para outros KPIs numéricos (Giro, Liquidez Corrente)
                return f"{row['Valor']:,.2f}"

        kpis_df['Valor Formatado'] = kpis_df.apply(format_kpi_value, axis=1)
        st.dataframe(kpis_df[['KPI', 'Valor Formatado']], use_container_width=True)

        st.markdown("---")
        st.subheader("Visualização dos KPIs")

        # Gráfico de Margens
        fig_margens = go.Figure(data=[
            go.Bar(name='Margem Bruta', x=['Margens'], y=[kpis['Margem Bruta']], marker_color='#4CAF50'),
            go.Bar(name='Margem Líquida', x=['Margens'], y=[kpis['Margem Líquida']], marker_color='#2e7d32'),
            go.Bar(name='Margem Contribuição', x=['Margens'], y=[kpis['% Margem de Contribuição']], marker_color='#8BC34A') # Nova barra
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
        st.warning("Não foi possível extrair dados válidos dos blocos J100 e J155. Verifique o formato do arquivo e os códigos das contas. (Se o arquivo foi carregado mas não exibiu dados, pode ser um problema no formato das linhas dos blocos J100/J155).")

else:
    st.info("Aguardando o upload do arquivo ECD para iniciar a análise. Por favor, certifique-se de que o arquivo esteja no formato de texto (.txt) e siga o layout da ECD para os blocos J100 e J155.")

st.markdown("---")
st.markdown("Desenvolvido com ❤️ por Seu Nome/Empresa")

