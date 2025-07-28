import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import StringIO
import re

# Configuração da página
st.set_page_config(page_title="Análise Contábil - ECD", layout="wide")
st.title("Análise de Demonstrações Contábeis via ECD")

# Funções para processar o arquivo ECD
def parse_ecd_file(uploaded_file):
    content = uploaded_file.getvalue().decode("utf-8")
    lines = content.split('\n')
    
    # Extrair dados do bloco I155 (Saldos das contas)
    i155_data = []
    for line in lines:
        if line.startswith('|I155|'):
            parts = line.split('|')
            if len(parts) >= 11:
                conta = parts[2].strip()
                saldo_anterior = float(parts[3].strip() or 0)
                natureza_saldo_anterior = parts[4].strip()
                debitos = float(parts[5].strip() or 0)
                creditos = float(parts[6].strip() or 0)
                saldo_final = float(parts[7].strip() or 0)
                natureza_saldo_final = parts[8].strip()
                
                i155_data.append({
                    'Conta': conta,
                    'Saldo Anterior': saldo_anterior if natureza_saldo_anterior == 'D' else -saldo_anterior,
                    'Débitos': debitos,
                    'Créditos': creditos,
                    'Saldo Final': saldo_final if natureza_saldo_final == 'D' else -saldo_final
                })
    
    df_i155 = pd.DataFrame(i155_data)
    
    # Extrair dados do bloco I050 (Plano de contas)
    i050_data = []
    for line in lines:
        if line.startswith('|I050|'):
            parts = line.split('|')
            if len(parts) >= 10:
                codigo = parts[5].strip()
                descricao = parts[9].strip()
                i050_data.append({'Código': codigo, 'Descrição': descricao})
    
    df_i050 = pd.DataFrame(i050_data).drop_duplicates()
    
    # Juntar os dados de saldos com as descrições das contas
    df_final = pd.merge(df_i155, df_i050, left_on='Conta', right_on='Código', how='left')
    df_final['Descrição'] = df_final['Descrição'].fillna(df_final['Conta'])
    
    return df_final

def classify_account(conta):
    """Classifica as contas com base no código para agrupamento"""
    if not conta or not isinstance(conta, str):
        return 'Outros'
    
    # Ativo
    if conta.startswith('1.1'):
        return 'Ativo Circulante'
    elif conta.startswith('1.2'):
        return 'Ativo Não Circulante'
    
    # Passivo
    elif conta.startswith('2.1'):
        return 'Passivo Circulante'
    elif conta.startswith('2.2'):
        return 'Passivo Não Circulante'
    elif conta.startswith('2.3'):
        return 'Patrimônio Líquido'
    
    # Receitas
    elif conta.startswith('3.'):
        return 'Receitas'
    
    # Despesas
    elif conta.startswith('4.'):
        return 'Despesas'
    
    # Custos
    elif conta.startswith('5.'):
        return 'Custos'
    
    else:
        return 'Outros'

def generate_balance_sheet(df):
    """Gera o Balanço Patrimonial"""
    df['Classificação'] = df['Conta'].apply(classify_account)
    
    # Agrupar por classificação
    grouped = df.groupby('Classificação')['Saldo Final'].sum().reset_index()
    
    # Separar Ativo e Passivo+PL
    ativo = grouped[grouped['Classificação'].isin(['Ativo Circulante', 'Ativo Não Circulante'])]
    passivo_pl = grouped[grouped['Classificação'].isin(['Passivo Circulante', 'Passivo Não Circulante', 'Patrimônio Líquido'])]
    
    return ativo, passivo_pl

def generate_income_statement(df):
    """Gera a Demonstração do Resultado do Exercício (DRE)"""
    df['Classificação'] = df['Conta'].apply(classify_account)
    
    # Filtra apenas contas de receitas, despesas e custos
    dre_df = df[df['Classificação'].isin(['Receitas', 'Despesas', 'Custos'])]
    
    # Agrupa por classificação
    dre_grouped = dre_df.groupby('Classificação')['Saldo Final'].sum().reset_index()
    
    # Calcula indicadores
    receita_total = dre_grouped[dre_grouped['Classificação'] == 'Receitas']['Saldo Final'].sum()
    custos_total = abs(dre_grouped[dre_grouped['Classificação'] == 'Custos']['Saldo Final'].sum())
    despesas_total = abs(dre_grouped[dre_grouped['Classificação'] == 'Despesas']['Saldo Final'].sum())
    
    lucro_bruto = receita_total - custos_total
    lucro_liquido = lucro_bruto - despesas_total
    
    return dre_grouped, receita_total, custos_total, despesas_total, lucro_bruto, lucro_liquido

def generate_trial_balance(df):
    """Gera o Balancete"""
    df['Classificação'] = df['Conta'].apply(classify_account)
    return df[['Conta', 'Descrição', 'Saldo Anterior', 'Débitos', 'Créditos', 'Saldo Final', 'Classificação']]

# Interface do usuário
uploaded_file = st.file_uploader("Importe o arquivo ECD (TXT)", type="txt")

if uploaded_file is not None:
    df = parse_ecd_file(uploaded_file)
    
    # Adicionar classificação das contas
    df['Classificação'] = df['Conta'].apply(classify_account)
    
    # Sidebar com filtros
    st.sidebar.header("Filtros")
    selected_class = st.sidebar.multiselect(
        "Classificação Contábil",
        options=df['Classificação'].unique(),
        default=df['Classificação'].unique()
    )
    
    # Aplicar filtros
    filtered_df = df[df['Classificação'].isin(selected_class)]
    
    # Layout principal
    tab1, tab2, tab3, tab4 = st.tabs(["Visão Geral", "Balanço Patrimonial", "DRE", "Balancete"])
    
    with tab1:
        st.header("Indicadores Financeiros")
        
        # Calcular KPIs
        ativo, passivo_pl = generate_balance_sheet(df)
        dre_grouped, receita_total, custos_total, despesas_total, lucro_bruto, lucro_liquido = generate_income_statement(df)
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Receita Total", f"R$ {receita_total:,.2f}")
        col2.metric("Lucro Bruto", f"R$ {lucro_bruto:,.2f}", f"{(lucro_bruto/receita_total*100 if receita_total != 0 else 0):.1f}%")
        col3.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}", f"{(lucro_liquido/receita_total*100 if receita_total != 0 else 0):.1f}%")
        
        # Calcular ROE (Return on Equity)
        pl = df[df['Classificação'] == 'Patrimônio Líquido']['Saldo Final'].sum()
        roe = (lucro_liquido / abs(pl)) * 100 if pl != 0 else 0
        col4.metric("ROE", f"{roe:.1f}%")
        
        # Gráficos
        st.subheader("Composição do Balanço")
        fig = px.pie(ativo, values='Saldo Final', names='Classificação', title='Ativo')
        st.plotly_chart(fig, use_container_width=True)
        
        fig = px.pie(passivo_pl, values='Saldo Final', names='Classificação', title='Passivo + Patrimônio Líquido')
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Margens")
        margem_bruta = (lucro_bruto / receita_total) * 100 if receita_total != 0 else 0
        margem_liquida = (lucro_liquido / receita_total) * 100 if receita_total != 0 else 0
        
        fig = px.bar(
            x=['Margem Bruta', 'Margem Líquida', 'ROE'],
            y=[margem_bruta, margem_liquida, roe],
            labels={'x': 'Indicador', 'y': 'Percentual (%)'},
            title='Indicadores de Rentabilidade'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("Balanço Patrimonial")
        
        ativo, passivo_pl = generate_balance_sheet(df)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Ativo")
            st.dataframe(
                ativo.assign(**{'Saldo Final': ativo['Saldo Final'].apply(lambda x: f"R$ {x:,.2f}")}),
                hide_index=True,
                use_container_width=True
            )
            
            fig = px.bar(
                ativo,
                x='Classificação',
                y='Saldo Final',
                title='Composição do Ativo'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Passivo + Patrimônio Líquido")
            st.dataframe(
                passivo_pl.assign(**{'Saldo Final': passivo_pl['Saldo Final'].apply(lambda x: f"R$ {x:,.2f}")}),
                hide_index=True,
                use_container_width=True
            )
            
            fig = px.bar(
                passivo_pl,
                x='Classificação',
                y='Saldo Final',
                title='Composição do Passivo + PL'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.header("Demonstração do Resultado do Exercício (DRE)")
        
        dre_grouped, receita_total, custos_total, despesas_total, lucro_bruto, lucro_liquido = generate_income_statement(df)
        
        # Criar DRE formatada
        dre_data = [
            {"Descrição": "Receita Operacional Bruta", "Valor": receita_total},
            {"Descrição": "(-) Custos", "Valor": -custos_total},
            {"Descrição": "= Lucro Bruto", "Valor": lucro_bruto},
            {"Descrição": "(-) Despesas Operacionais", "Valor": -despesas_total},
            {"Descrição": "= Lucro Líquido", "Valor": lucro_liquido}
        ]
        
        dre_df = pd.DataFrame(dre_data)
        dre_df['Valor'] = dre_df['Valor'].apply(lambda x: f"R$ {x:,.2f}")
        
        st.dataframe(
            dre_df,
            hide_index=True,
            use_container_width=True
        )
        
        # Gráfico da DRE
        fig = px.bar(
            dre_grouped,
            x='Classificação',
            y='Saldo Final',
            title='Composição do Resultado'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Margens
        st.subheader("Análise de Margens")
        
        margem_data = {
            "Margem": ["Margem Bruta", "Margem Líquida"],
            "Valor (%)": [
                (lucro_bruto / receita_total * 100) if receita_total != 0 else 0,
                (lucro_liquido / receita_total * 100) if receita_total != 0 else 0
            ]
        }
        
        fig = px.bar(
            pd.DataFrame(margem_data),
            x='Margem',
            y='Valor (%)',
            title='Margens (%)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("Balancete")
        
        balancete = generate_trial_balance(df)
        
        # Formatar valores monetários
        formatted_balancete = balancete.copy()
        for col in ['Saldo Anterior', 'Débitos', 'Créditos', 'Saldo Final']:
            formatted_balancete[col] = formatted_balancete[col].apply(lambda x: f"R$ {x:,.2f}")
        
        st.dataframe(
            formatted_balancete,
            hide_index=True,
            use_container_width=True
        )
        
        # Opção para download
        csv = balancete.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Balancete (CSV)",
            data=csv,
            file_name="balancete.csv",
            mime="text/csv"
        )
else:
    st.info("Por favor, importe um arquivo ECD no formato TXT para começar a análise.")
