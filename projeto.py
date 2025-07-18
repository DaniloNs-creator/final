import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import io

# Configuração da página
st.set_page_config(
    page_title="Análise de ECD - Registro I155",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título do dashboard
st.title("📊 Análise de KPIs Contábeis - ECD (Registro I155)")
st.markdown("Carregue o arquivo TXT da Escrituração Contábil Digital para análise do registro I155")

# Função para processar a ECD com foco no registro I155
def parse_ecd_i155(file_content):
    """Processa o arquivo ECD e extrai os registros I155"""
    lines = file_content.split('\n')
    registros_i155 = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # Verifica se é registro I155 (posições 1-4)
        if line.startswith('|I155|'):
            # Remove os pipes e separa os campos
            campos = [campo.strip() for campo in line.split('|')[1:-1]]
            
            if len(campos) >= 9:  # Verifica se tem todos os campos obrigatórios
                registro = {
                    'TIPO_REG': campos[0],
                    'COD_CTA': campos[1],       # Código da conta contábil
                    'COD_CCUS': campos[2] if len(campos) > 2 else '',  # Centro de custo
                    'VL_SLD_INI': float(campos[3].replace(',', '.')) if campos[3] else 0.0,  # Saldo inicial
                    'IND_VL_SLD_INI': campos[4],  # Natureza do saldo inicial (D/C)
                    'VL_DEB': float(campos[5].replace(',', '.')) if campos[5] else 0.0,  # Valor débito
                    'VL_CRED': float(campos[6].replace(',', '.')) if campos[6] else 0.0,  # Valor crédito
                    'VL_SLD_FIN': float(campos[7].replace(',', '.')) if campos[7] else 0.0,  # Saldo final
                    'IND_VL_SLD_FIN': campos[8]   # Natureza do saldo final (D/C)
                }
                registros_i155.append(registro)
    
    return pd.DataFrame(registros_i155)

def processar_kpis_i155(df_i155):
    """Processa os registros I155 para calcular os KPIs"""
    # Agrupa valores por código de conta contábil
    df_agrupado = df_i155.groupby('COD_CTA').agg({
        'VL_DEB': 'sum',
        'VL_CRED': 'sum'
    }).reset_index()
    
    # Mapeamento de códigos para contas da DRE (ajuste conforme plano de contas do arquivo)
    dre_mapping = {
        '3': 'RECEITA_BRUTA',          # Receitas
        '3.1': 'RECEITA_BRUTA',        # Receitas de Vendas
        '3.2': 'DEDUCOES',             # Deduções
        '3.3': 'OUTRAS_RECEITAS',      # Outras Receitas
        '4': 'DESPESAS',               # Despesas
        '4.1': 'DESPESAS_OPERACIONAIS',# Despesas Operacionais
        '4.2': 'DESPESAS_FINANCEIRAS', # Despesas Financeiras
        '4.3': 'OUTRAS_DESPESAS',      # Outras Despesas
        '4.4': 'PROVISAO_IR',          # Provisão para IRPJ/CSLL
        '5': 'CUSTOS',                 # Custos
        '5.1': 'CUSTOS_OPERACIONAIS',  # Custos Operacionais
        '2.3': 'PATRIMONIO_LIQUIDO'    # Patrimônio Líquido
    }
    
    # Inicializa dicionário de KPIs
    kpis = {
        'RECEITA_BRUTA': 0.0,
        'DEDUCOES': 0.0,
        'OUTRAS_RECEITAS': 0.0,
        'CUSTOS': 0.0,
        'DESPESAS_OPERACIONAIS': 0.0,
        'DESPESAS_FINANCEIRAS': 0.0,
        'OUTRAS_DESPESAS': 0.0,
        'PROVISAO_IR': 0.0,
        'PATRIMONIO_LIQUIDO': 0.0
    }
    
    # Popula os KPIs com base no mapeamento
    for _, row in df_agrupado.iterrows():
        for codigo, conta in dre_mapping.items():
            if row['COD_CTA'].startswith(codigo):
                # Para receitas, consideramos os créditos
                if codigo in ['3', '3.1', '3.3']:
                    kpis[conta] += row['VL_CRED']
                # Para despesas e custos, consideramos os débitos
                elif codigo in ['4', '4.1', '4.2', '4.3', '4.4', '5', '5.1']:
                    kpis[conta] += row['VL_DEB']
                # Para PL, consideramos o saldo final (ajustar conforme natureza)
                elif codigo == '2.3':
                    if row['IND_VL_SLD_FIN'] == 'C':
                        kpis[conta] += row['VL_SLD_FIN']
                    else:
                        kpis[conta] -= row['VL_SLD_FIN']
    
    # Calcula KPIs derivados
    kpis['RECEITA_LIQUIDA'] = kpis['RECEITA_BRUTA'] - kpis['DEDUCOES'] + kpis['OUTRAS_RECEITAS']
    kpis['LUCRO_BRUTO'] = kpis['RECEITA_LIQUIDA'] - kpis['CUSTOS']
    kpis['LUCRO_OPERACIONAL'] = kpis['LUCRO_BRUTO'] - kpis['DESPESAS_OPERACIONAIS']
    kpis['LUCRO_ANTES_IR'] = kpis['LUCRO_OPERACIONAL'] - kpis['DESPESAS_FINANCEIRAS'] - kpis['OUTRAS_DESPESAS']
    kpis['LUCRO_LIQUIDO'] = kpis['LUCRO_ANTES_IR'] - kpis['PROVISAO_IR']
    
    # Cálculo de margens
    kpis['MARGEM_BRUTA'] = kpis['LUCRO_BRUTO'] / kpis['RECEITA_LIQUIDA'] if kpis['RECEITA_LIQUIDA'] != 0 else 0
    kpis['MARGEM_OPERACIONAL'] = kpis['LUCRO_OPERACIONAL'] / kpis['RECEITA_LIQUIDA'] if kpis['RECEITA_LIQUIDA'] != 0 else 0
    kpis['MARGEM_LIQUIDA'] = kpis['LUCRO_LIQUIDO'] / kpis['RECEITA_LIQUIDA'] if kpis['RECEITA_LIQUIDA'] != 0 else 0
    kpis['ROE'] = kpis['LUCRO_LIQUIDO'] / kpis['PATRIMONIO_LIQUIDO'] if kpis['PATRIMONIO_LIQUIDO'] != 0 else 0
    
    return kpis

# Upload do arquivo ECD
uploaded_file = st.file_uploader("Carregue o arquivo TXT da ECD (com registro I155)", type=['txt'])

if uploaded_file is not None:
    try:
        # Lê o arquivo
        stringio = io.StringIO(uploaded_file.getvalue().decode("latin-1"))
        file_content = stringio.read()
        
        # Processa o arquivo ECD - foco no I155
        df_i155 = parse_ecd_i155(file_content)
        
        if len(df_i155) == 0:
            st.error("Nenhum registro I155 encontrado no arquivo!")
        else:
            # Extrai informações do cabeçalho (registro I030)
            lines = file_content.split('\n')
            for line in lines:
                if line.startswith('|I030|'):
                    campos = [campo.strip() for campo in line.split('|')[1:-1]]
                    nome_empresa = campos[8]
                    cnpj = campos[9]
                    periodo = f"{campos[2]} a {campos[3]}"
                    break
            
            # Processa KPIs
            kpis = processar_kpis_i155(df_i155)
            
            # Exibe informações da empresa
            st.subheader("Informações da Empresa")
            col1, col2, col3 = st.columns(3)
            col1.metric("Nome", nome_empresa)
            col2.metric("CNPJ", cnpj)
            col3.metric("Período", periodo)
            
            # Métricas principais
            st.subheader("Principais KPIs - Demonstração do Resultado")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Receita Líquida", f"R$ {kpis['RECEITA_LIQUIDA']:,.2f}")
            col2.metric("Lucro Líquido", f"R$ {kpis['LUCRO_LIQUIDO']:,.2f}")
            col3.metric("Margem Líquida", f"{kpis['MARGEM_LIQUIDA']*100:.2f}%")
            col4.metric("ROE", f"{kpis['ROE']*100:.2f}%")
            
            # Abas para análise detalhada
            tab1, tab2, tab3 = st.tabs(["📊 DRE Completa", "📈 Análise de Rentabilidade", "🧮 Registros I155"])
            
            with tab1:
                st.header("Demonstração do Resultado do Exercício")
                
                # Cria dataframe para DRE
                dre_data = [
                    {"Descrição": "Receita Bruta", "Valor": kpis['RECEITA_BRUTA'], "Tipo": "Receita"},
                    {"Descrição": "(-) Deduções", "Valor": -kpis['DEDUCOES'], "Tipo": "Dedução"},
                    {"Descrição": "(+) Outras Receitas", "Valor": kpis['OUTRAS_RECEITAS'], "Tipo": "Receita"},
                    {"Descrição": "(=) Receita Líquida", "Valor": kpis['RECEITA_LIQUIDA'], "Tipo": "Receita"},
                    {"Descrição": "(-) Custos", "Valor": -kpis['CUSTOS'], "Tipo": "Custo"},
                    {"Descrição": "(=) Lucro Bruto", "Valor": kpis['LUCRO_BRUTO'], "Tipo": "Resultado"},
                    {"Descrição": "(-) Despesas Operacionais", "Valor": -kpis['DESPESAS_OPERACIONAIS'], "Tipo": "Despesa"},
                    {"Descrição": "(=) Lucro Operacional", "Valor": kpis['LUCRO_OPERACIONAL'], "Tipo": "Resultado"},
                    {"Descrição": "(-) Despesas Financeiras", "Valor": -kpis['DESPESAS_FINANCEIRAS'], "Tipo": "Despesa"},
                    {"Descrição": "(-) Outras Despesas", "Valor": -kpis['OUTRAS_DESPESAS'], "Tipo": "Despesa"},
                    {"Descrição": "(=) Lucro Antes do IR", "Valor": kpis['LUCRO_ANTES_IR'], "Tipo": "Resultado"},
                    {"Descrição": "(-) Provisão para IR", "Valor": -kpis['PROVISAO_IR'], "Tipo": "Imposto"},
                    {"Descrição": "(=) Lucro Líquido", "Valor": kpis['LUCRO_LIQUIDO'], "Tipo": "Resultado"}
                ]
                df_dre = pd.DataFrame(dre_data)
                
                # Gráfico de barras da DRE
                fig = px.bar(
                    df_dre,
                    x='Descrição',
                    y='Valor',
                    color='Tipo',
                    text=[f"R$ {x:,.2f}" for x in df_dre['Valor']],
                    title="Demonstração do Resultado do Exercício",
                    labels={'Valor': 'Valor (R$)', 'Descrição': 'Conta'}
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela com valores
                st.dataframe(
                    df_dre[['Descrição', 'Valor']].style.format({
                        'Valor': 'R$ {:.2f}'
                    }),
                    use_container_width=True,
                    height=600
                )
            
            with tab2:
                st.header("Análise de Rentabilidade")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gráfico de margens
                    margens_data = {
                        'Margem': ['Margem Bruta', 'Margem Operacional', 'Margem Líquida'],
                        'Percentual': [
                            kpis['MARGEM_BRUTA'] * 100,
                            kpis['MARGEM_OPERACIONAL'] * 100,
                            kpis['MARGEM_LIQUIDA'] * 100
                        ]
                    }
                    df_margens = pd.DataFrame(margens_data)
                    
                    fig = px.bar(
                        df_margens,
                        x='Margem',
                        y='Percentual',
                        text=[f"{x:.1f}%" for x in df_margens['Percentual']],
                        title="Análise de Margens",
                        labels={'Percentual': 'Percentual (%)', 'Margem': 'Tipo de Margem'}
                    )
                    fig.update_traces(textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Indicador ROE
                    fig = px.bar(
                        x=['ROE'],
                        y=[kpis['ROE'] * 100],
                        text=[f"{kpis['ROE'] * 100:.1f}%"],
                        title="Retorno sobre o Patrimônio Líquido (ROE)",
                        labels={'x': '', 'y': 'Percentual (%)'}
                    )
                    fig.update_traces(marker_color='green')
                    fig.update_traces(textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)
                
                # Análise de composição
                st.subheader("Composição do Resultado")
                composicao = pd.DataFrame({
                    'Item': ['Receita Líquida', 'Custos', 'Despesas Operacionais', 'Despesas Financeiras', 'Outras Despesas', 'Provisão IR'],
                    'Valor': [
                        kpis['RECEITA_LIQUIDA'],
                        -kpis['CUSTOS'],
                        -kpis['DESPESAS_OPERACIONAIS'],
                        -kpis['DESPESAS_FINANCEIRAS'],
                        -kpis['OUTRAS_DESPESAS'],
                        -kpis['PROVISAO_IR']
                    ]
                })
                
                fig = px.pie(
                    composicao,
                    names='Item',
                    values='Valor',
                    title='Composição do Resultado',
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                st.header("Registros I155 da ECD")
                
                # Filtros para os registros
                st.subheader("Filtros de Consulta")
                col1, col2 = st.columns(2)
                
                with col1:
                    codigo_conta = st.text_input("Filtrar por código de conta (início):")
                
                with col2:
                    natureza = st.selectbox("Filtrar por natureza:", ['Todos', 'Débito', 'Crédito'])
                
                # Aplica filtros
                df_filtrado = df_i155.copy()
                if codigo_conta:
                    df_filtrado = df_filtrado[df_filtrado['COD_CTA'].str.startswith(codigo_conta)]
                if natureza != 'Todos':
                    if natureza == 'Débito':
                        df_filtrado = df_filtrado[df_filtrado['VL_DEB'] > 0]
                    else:
                        df_filtrado = df_filtrado[df_filtrado['VL_CRED'] > 0]
                
                # Mostra registros filtrados
                st.dataframe(
                    df_filtrado[['COD_CTA', 'VL_SLD_INI', 'IND_VL_SLD_INI', 'VL_DEB', 'VL_CRED', 'VL_SLD_FIN', 'IND_VL_SLD_FIN']].style.format({
                        'VL_SLD_INI': 'R$ {:.2f}',
                        'VL_DEB': 'R$ {:.2f}',
                        'VL_CRED': 'R$ {:.2f}',
                        'VL_SLD_FIN': 'R$ {:.2f}'
                    }),
                    use_container_width=True,
                    height=600
                )
                
                # Mostra layout oficial do registro I155
                st.subheader("Layout Oficial do Registro I155")
                st.markdown("""
                | Ordem | Campo | Tipo | Tamanho | Descrição |
                |-------|-------|------|---------|-----------|
                | 1 | TIPO_REG | C | 4 | Tipo do registro (I155) |
                | 2 | COD_CTA | C | 255 | Código da conta contábil |
                | 3 | COD_CCUS | C | 255 | Código do centro de custos |
                | 4 | VL_SLD_INI | N | 20 | Valor do saldo inicial |
                | 5 | IND_VL_SLD_INI | C | 1 | Indicador da natureza do saldo inicial (D - Débito / C - Crédito) |
                | 6 | VL_DEB | N | 20 | Valor total dos débitos no período |
                | 7 | VL_CRED | N | 20 | Valor total dos créditos no período |
                | 8 | VL_SLD_FIN | N | 20 | Valor do saldo final |
                | 9 | IND_VL_SLD_FIN | C | 1 | Indicador da natureza do saldo final (D - Débito / C - Crédito) |
                """)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")

else:
    st.info("Por favor, carregue o arquivo TXT da ECD para iniciar a análise")
    st.markdown("""
    ### Instruções:
    1. Clique no botão "Browse files" ou arraste o arquivo TXT da ECD para a área acima
    2. O sistema processará automaticamente os registros I155
    3. Os principais KPIs serão calculados e exibidos
    
    ### Sobre o Registro I155:
    O registro I155 da ECD contém informações detalhadas sobre as contas contábeis
    e seus movimentos, sendo fundamental para a construção da Demonstração do Resultado.
    
    Este dashboard analisa especificamente:
    - Receitas (códigos iniciados com 3)
    - Custos (códigos iniciados com 5)
    - Despesas (códigos iniciados com 4)
    - Resultados
    - Patrimônio Líquido (códigos iniciados com 2.3)
    """)

# Rodapé
st.markdown("---")
st.markdown("**Dashboard para análise de ECD (Registro I155) - v1.0**")
st.markdown(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
