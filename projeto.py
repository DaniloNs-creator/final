import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Configuração inicial da página
st.set_page_config(page_title="Análise de ECD", layout="wide")
st.title("Análise de Demonstrações Contábeis - ECD")

# Função auxiliar para conversão segura de valores
def safe_float_converter(value):
    try:
        # Remove pontos de milhar e substitui vírgula decimal por ponto
        cleaned = value.replace('.', '').replace(',', '.').strip()
        return float(cleaned) if cleaned else 0.0
    except:
        return 0.0

# Função para processar o arquivo ECD
def processar_ecd(uploaded_file):
    try:
        # Ler o arquivo
        content = uploaded_file.read().decode('utf-8')
        
        # Extrair apenas as linhas I155
        i155_lines = [line for line in content.split('\n') if line.startswith('|I155|')]
        
        # Criar DataFrame
        data = []
        for line in i155_lines:
            parts = line.split('|')
            if len(parts) >= 9:
                # Converter valores numéricos com tratamento seguro
                saldo_inicial = safe_float_converter(parts[3])
                debitos = safe_float_converter(parts[5])
                creditos = safe_float_converter(parts[6])
                saldo_final = safe_float_converter(parts[7])
                
                data.append({
                    'Conta': parts[2],
                    'Data': parts[1],
                    'Saldo_Inicial': saldo_inicial,
                    'Natureza_Saldo_Inicial': parts[4],
                    'Debitos': debitos,
                    'Creditos': creditos,
                    'Saldo_Final': saldo_final,
                    'Natureza_Saldo_Final': parts[8]
                })
        
        df = pd.DataFrame(data)
        
        # Ajustar saldos conforme natureza
        df['Saldo_Final_Ajustado'] = np.where(
            df['Natureza_Saldo_Final'] == 'D',
            df['Saldo_Final'],
            -df['Saldo_Final']
        )
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
        return pd.DataFrame()

# Função para classificar as contas
def classificar_conta(conta):
    if not isinstance(conta, str):
        return 'Outras'
    
    if conta.startswith('1.') or conta.startswith('1'):
        return 'Ativo'
    elif conta.startswith('2.') or conta.startswith('2'):
        return 'Passivo/Patrimônio Líquido'
    elif conta.startswith('3.') or conta.startswith('3'):
        return 'Receita'
    elif conta.startswith('4.') or conta.startswith('4'):
        return 'Despesa'
    elif conta.startswith('5.') or conta.startswith('5'):
        return 'Custo'
    elif conta.startswith('6.') or conta.startswith('6'):
        return 'Contas de Compensação'
    else:
        return 'Outras'

# Função para gerar o Balancete
def gerar_balancete(df):
    if df.empty:
        return pd.DataFrame()
    
    balancete = df.copy()
    balancete['Classificacao'] = balancete['Conta'].apply(classificar_conta)
    balancete = balancete[['Classificacao', 'Conta', 'Saldo_Final_Ajustado']]
    balancete = balancete.sort_values(by=['Classificacao', 'Conta'])
    return balancete

# Função para gerar o Balanço Patrimonial
def gerar_balanco(df):
    if df.empty:
        return pd.DataFrame()
    
    # Filtrar contas do Ativo
    ativo = df[df['Conta'].str.startswith(('1.', '1'), na=False)].copy()
    ativo['Classificacao'] = ativo['Conta'].apply(
        lambda x: 'Ativo Circulante' if str(x).startswith(('1.1', '1.1.')) else 'Ativo Não Circulante')
    ativo = ativo.groupby('Classificacao')['Saldo_Final_Ajustado'].sum().reset_index()
    
    # Filtrar contas do Passivo e PL
    passivo_pl = df[df['Conta'].str.startswith(('2.', '2'), na=False)].copy()
    passivo_pl['Classificacao'] = passivo_pl['Conta'].apply(lambda x: 
        'Passivo Circulante' if str(x).startswith(('2.1', '2.1.')) 
        else 'Passivo Não Circulante' if str(x).startswith(('2.2', '2.2.')) 
        else 'Patrimônio Líquido')
    passivo_pl = passivo_pl.groupby('Classificacao')['Saldo_Final_Ajustado'].sum().reset_index()
    
    # Calcular Totais
    total_ativo = ativo['Saldo_Final_Ajustado'].sum()
    total_passivo_pl = passivo_pl['Saldo_Final_Ajustado'].sum()
    
    # Criar DataFrame consolidado
    balanco = pd.concat([
        pd.DataFrame({'Classificacao': ['ATIVO'], 'Saldo_Final_Ajustado': [total_ativo]}),
        ativo,
        pd.DataFrame({'Classificacao': ['PASSIVO + PL'], 'Saldo_Final_Ajustado': [total_passivo_pl]}),
        passivo_pl
    ])
    
    return balanco

# Função para gerar a DRE
def gerar_dre(df):
    if df.empty:
        return pd.DataFrame()
    
    # Receitas
    receitas = df[df['Conta'].str.startswith(('3.', '3'), na=False)]['Saldo_Final_Ajustado'].sum()
    
    # Custos
    custos = df[df['Conta'].str.startswith(('5.', '5'), na=False)]['Saldo_Final_Ajustado'].sum()
    
    # Despesas
    despesas = df[df['Conta'].str.startswith(('4.', '4'), na=False)]['Saldo_Final_Ajustado'].sum()
    
    # Lucro Bruto
    lucro_bruto = receitas + custos  # Custos são negativos
    
    # Lucro Operacional
    lucro_operacional = lucro_bruto + despesas  # Despesas são negativas
    
    # Lucro Líquido (assumindo que não há outros resultados)
    lucro_liquido = lucro_operacional
    
    # Criar DataFrame da DRE
    dre = pd.DataFrame({
        'Descricao': [
            'Receita Operacional Bruta',
            '(-) Custos',
            '= Lucro Bruto',
            '(-) Despesas Operacionais',
            '= Lucro Operacional',
            '= Lucro Líquido'
        ],
        'Valor': [
            receitas,
            custos,
            lucro_bruto,
            despesas,
            lucro_operacional,
            lucro_liquido
        ]
    })
    
    return dre

# Função para calcular KPIs
def calcular_kpis(df, dre):
    if df.empty or dre.empty:
        return pd.DataFrame()
    
    try:
        # Lucro Líquido
        lucro_liquido = dre[dre['Descricao'] == '= Lucro Líquido']['Valor'].values[0]
        
        # Receita Líquida
        receita_liquida = dre[dre['Descricao'] == 'Receita Operacional Bruta']['Valor'].values[0]
        
        # Margem Líquida
        margem_liquida = (lucro_liquido / receita_liquida) * 100 if receita_liquida != 0 else 0
        
        # Margem Bruta
        lucro_bruto = dre[dre['Descricao'] == '= Lucro Bruto']['Valor'].values[0]
        margem_bruta = (lucro_bruto / receita_liquida) * 100 if receita_liquida != 0 else 0
        
        # ROE (Return on Equity)
        pl = df[df['Conta'].str.startswith(('2.3', '2.3.'), na=False)]['Saldo_Final_Ajustado'].sum()
        roe = (lucro_liquido / abs(pl)) * 100 if pl != 0 else 0
        
        # Liquidez Corrente
        ativo_circulante = df[df['Conta'].str.startswith(('1.1', '1.1.'), na=False)]['Saldo_Final_Ajustado'].sum()
        passivo_circulante = df[df['Conta'].str.startswith(('2.1', '2.1.'), na=False)]['Saldo_Final_Ajustado'].sum()
        liquidez_corrente = ativo_circulante / abs(passivo_circulante) if passivo_circulante != 0 else 0
        
        # Endividamento
        passivo_total = df[df['Conta'].str.startswith(('2.', '2'), na=False)]['Saldo_Final_Ajustado'].sum()
        ativo_total = df[df['Conta'].str.startswith(('1.', '1'), na=False)]['Saldo_Final_Ajustado'].sum()
        endividamento = (abs(passivo_total) / ativo_total) * 100 if ativo_total != 0 else 0
        
        kpis = {
            'Lucro Líquido': lucro_liquido,
            'Margem Líquida (%)': margem_liquida,
            'Margem Bruta (%)': margem_bruta,
            'ROE (%)': roe,
            'Liquidez Corrente': liquidez_corrente,
            'Endividamento (%)': endividamento
        }
        
        return pd.DataFrame.from_dict(kpis, orient='index', columns=['Valor'])
    except Exception as e:
        st.error(f"Erro ao calcular KPIs: {str(e)}")
        return pd.DataFrame()

# Interface do usuário
uploaded_file = st.file_uploader("Carregar arquivo ECD", type=['txt'])

if uploaded_file is not None:
    # Processar arquivo
    df = processar_ecd(uploaded_file)
    
    if not df.empty:
        # Mostrar dados brutos
        with st.expander("Visualizar dados brutos"):
            st.dataframe(df)
        
        # Calcular demonstrações
        balancete = gerar_balancete(df)
        balanco = gerar_balanco(df)
        dre = gerar_dre(df)
        kpis = calcular_kpis(df, dre)
        
        # Layout em abas
        tab1, tab2, tab3, tab4 = st.tabs(["Balancete", "Balanço Patrimonial", "DRE", "KPIs"])
        
        with tab1:
            st.subheader("Balancete")
            if not balancete.empty:
                st.dataframe(balancete)
                
                # Gráfico do balancete
                fig = px.treemap(balancete, path=['Classificacao', 'Conta'], values='Saldo_Final_Ajustado',
                                color='Saldo_Final_Ajustado', color_continuous_scale='RdBu',
                                title='Distribuição de Saldos por Conta')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Não foi possível gerar o balancete.")
        
        with tab2:
            st.subheader("Balanço Patrimonial")
            if not balanco.empty:
                st.dataframe(balanco)
                
                # Gráfico do balanço
                fig = px.bar(balanco, x='Classificacao', y='Saldo_Final_Ajustado', 
                            text='Saldo_Final_Ajustado', title='Balanço Patrimonial')
                fig.update_traces(texttemplate='%{text:,.2f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Não foi possível gerar o balanço patrimonial.")
        
        with tab3:
            st.subheader("Demonstração do Resultado do Exercício (DRE)")
            if not dre.empty:
                st.dataframe(dre)
                
                # Gráfico da DRE
                fig = px.bar(dre, x='Descricao', y='Valor', text='Valor', title='Demonstração do Resultado do Exercício')
                fig.update_traces(texttemplate='%{text:,.2f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Não foi possível gerar a DRE.")
        
        with tab4:
            st.subheader("Indicadores Financeiros (KPIs)")
            if not kpis.empty:
                st.dataframe(kpis.style.format({'Valor': '{:,.2f}'}))
                
                # Gráfico de KPIs
                fig = px.bar(kpis.reset_index(), x='index', y='Valor', text='Valor', 
                            title='Indicadores Financeiros')
                fig.update_traces(texttemplate='%{text:,.2f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
                
                # Explicação dos KPIs
                with st.expander("Explicação dos KPIs"):
                    st.markdown("""
                    - **Lucro Líquido**: Resultado final após todas as receitas, custos e despesas
                    - **Margem Líquida (%)**: Lucro Líquido / Receita Líquida
                    - **Margem Bruta (%)**: Lucro Bruto / Receita Líquida
                    - **ROE (%)** (Return on Equity): Retorno sobre o Patrimônio Líquido
                    - **Liquidez Corrente**: Ativo Circulante / Passivo Circulante
                    - **Endividamento (%)**: (Passivo Total / Ativo Total) * 100
                    """)
            else:
                st.warning("Não foi possível calcular os KPIs.")
    else:
        st.error("O arquivo foi carregado, mas não contém dados válidos para análise.")

else:
    st.info("Por favor, carregue um arquivo ECD no formato TXT para iniciar a análise.")
