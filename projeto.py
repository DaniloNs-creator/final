import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

# Configuração inicial da página
st.set_page_config(page_title="Análise ECD", page_icon="📊", layout="wide")
st.title("📊 Dashboard de Análise Contábil e Financeira - ECD")

# Funções para processar o arquivo ECD
def parse_ecd_file(uploaded_file):
    """Processa o arquivo ECD e extrai os dados relevantes"""
    content = uploaded_file.read().decode('utf-8')
    lines = content.split('\n')
    
    # Extrair informações da empresa
    empresa_info = {}
    for line in lines:
        if line.startswith('|0000|'):
            parts = line.split('|')
            empresa_info['Nome'] = parts[4]
            empresa_info['CNPJ'] = parts[5]
            empresa_info['UF'] = parts[6]
            empresa_info['Período'] = f"{parts[3]} a {parts[4]}"
            break
    
    # Extrair contas contábeis (registros I050)
    contas = []
    for line in lines:
        if line.startswith('|I050|'):
            parts = line.split('|')
            contas.append({
                'Data': parts[2],
                'Código': parts[6],
                'Descrição': parts[8],
                'Tipo': parts[4],
                'Nível': int(parts[5]),
                'ContaPai': parts[7] if parts[7] else None
            })
    
    # Extrair saldos (registros I155)
    saldos = []
    for line in lines:
        if line.startswith('|I155|'):
            parts = line.split('|')
            saldos.append({
                'Conta': parts[2],
                'SaldoAnterior': float(parts[4].replace(',', '.')) if parts[4] else 0,
                'Débito': float(parts[5].replace(',', '.')) if parts[5] else 0,
                'Crédito': float(parts[6].replace(',', '.')) if parts[6] else 0,
                'SaldoAtual': float(parts[7].replace(',', '.')) if parts[7] else 0,
                'Natureza': parts[8]
            })
    
    # Extrair lançamentos (registros I200 e I250)
    lancamentos = []
    current_lancamento = None
    for line in lines:
        if line.startswith('|I200|'):
            parts = line.split('|')
            current_lancamento = {
                'Número': parts[2],
                'Data': parts[3],
                'Valor': float(parts[4].replace(',', '.')) if parts[4] else 0,
                'Tipo': parts[5],
                'Histórico': parts[7] if len(parts) > 7 else ''
            }
        elif line.startswith('|I250|') and current_lancamento:
            parts = line.split('|')
            lancamentos.append({
                **current_lancamento,
                'Conta': parts[2],
                'ValorConta': float(parts[4].replace(',', '.')) if parts[4] else 0,
                'NaturezaConta': parts[5],
                'Complemento': parts[7] if len(parts) > 7 else ''
            })
    
    return {
        'empresa': empresa_info,
        'contas': pd.DataFrame(contas),
        'saldos': pd.DataFrame(saldos),
        'lancamentos': pd.DataFrame(lancamentos)
    }

def get_conta_descricao(codigo, contas_df):
    """Obtém a descrição de uma conta com base no código"""
    conta = contas_df[contas_df['Código'] == codigo]
    return conta['Descrição'].values[0] if not conta.empty else codigo

def analyze_balances(contas_df, saldos_df):
    """Analisa os saldos das contas"""
    # Juntar contas com saldos
    df = pd.merge(saldos_df, contas_df, left_on='Conta', right_on='Código', how='left')
    
    # Classificar contas por grupo (ativo, passivo, etc.)
    df['Grupo'] = df['Código'].apply(lambda x: x.split('.')[0] if x and '.' in x else '0')
    df['Grupo'] = df['Grupo'].replace({
        '1': 'Ativo',
        '2': 'Passivo',
        '3': 'Receita',
        '4': 'Despesa',
        '5': 'Custo',
        '6': 'Compensação'
    })
    
    # Calcular totais por grupo
    group_totals = df.groupby('Grupo')['SaldoAtual'].sum().reset_index()
    
    return df, group_totals

def analyze_cash_flow(lancamentos_df, contas_df):
    """Analisa o fluxo de caixa"""
    # Filtrar apenas contas de caixa e equivalentes
    cash_accounts = ['1.1.01.02', '1.1.01.03']  # Bancos e aplicações financeiras
    
    # Obter todas as contas filhas dessas contas principais
    all_cash_accounts = []
    for codigo in cash_accounts:
        all_cash_accounts.extend(contas_df[contas_df['Código'].str.startswith(codigo)]['Código'].tolist())
    
    # Filtrar lançamentos nessas contas
    cash_flow = lancamentos_df[lancamentos_df['Conta'].isin(all_cash_accounts)].copy()
    
    # Classificar como entrada ou saída
    cash_flow['TipoMovimento'] = cash_flow.apply(
        lambda x: 'Entrada' if x['NaturezaConta'] == 'C' else 'Saída', axis=1)
    
    # Agrupar por dia e tipo
    cash_flow_daily = cash_flow.groupby(['Data', 'TipoMovimento'])['ValorConta'].sum().reset_index()
    cash_flow_daily['Data'] = pd.to_datetime(cash_flow_daily['Data'], format='%d%m%Y')
    
    return cash_flow, cash_flow_daily

# Interface do usuário
uploaded_file = st.file_uploader("Carregar arquivo ECD (TXT)", type="txt")

if uploaded_file is not None:
    try:
        data = parse_ecd_file(uploaded_file)
        
        # Mostrar informações da empresa
        st.subheader("Informações da Empresa")
        col1, col2, col3 = st.columns(3)
        col1.metric("Nome", data['empresa'].get('Nome', 'Não informado'))
        col2.metric("CNPJ", data['empresa'].get('CNPJ', 'Não informado'))
        col3.metric("UF", data['empresa'].get('UF', 'Não informado'))
        
        # Análise de saldos
        st.subheader("Análise de Saldos Contábeis")
        saldos_analisados, group_totals = analyze_balances(data['contas'], data['saldos'])
        
        # Gráfico de saldos por grupo
        fig = px.bar(group_totals, x='Grupo', y='SaldoAtual', 
                     title='Saldos por Grupo Contábil',
                     color='Grupo')
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela com principais contas
        st.write("Principais Contas:")
        principais_contas = saldos_analisados.sort_values('SaldoAtual', key=abs, ascending=False).head(10)
        st.dataframe(principais_contas[['Descrição', 'SaldoAnterior', 'SaldoAtual', 'Natureza']])
        
        # Análise de fluxo de caixa
        st.subheader("Análise de Fluxo de Caixa")
        cash_flow, cash_flow_daily = analyze_cash_flow(data['lancamentos'], data['contas'])
        
        if not cash_flow_daily.empty:
            # Gráfico de fluxo de caixa diário
            fig = px.line(cash_flow_daily, x='Data', y='ValorConta', 
                          color='TipoMovimento',
                          title='Fluxo de Caixa Diário')
            st.plotly_chart(fig, use_container_width=True)
            
            # KPIs de fluxo de caixa
            total_entradas = cash_flow_daily[cash_flow_daily['TipoMovimento'] == 'Entrada']['ValorConta'].sum()
            total_saidas = cash_flow_daily[cash_flow_daily['TipoMovimento'] == 'Saída']['ValorConta'].sum()
            saldo_final = total_entradas - total_saidas
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Entradas", f"R$ {total_entradas:,.2f}")
            col2.metric("Total de Saídas", f"R$ {total_saidas:,.2f}")
            col3.metric("Saldo Final", f"R$ {saldo_final:,.2f}", 
                        delta_color="inverse" if saldo_final < 0 else "normal")
        else:
            st.warning("Não foram encontrados dados de fluxo de caixa.")
        
        # Análise de receitas e despesas
        st.subheader("Análise de Receitas e Despesas")
        receitas_despesas = saldos_analisados[
            saldos_analisados['Grupo'].isin(['Receita', 'Despesa', 'Custo'])
        ].copy()
        
        if not receitas_despesas.empty:
            # Agrupar por tipo
            rd_grouped = receitas_despesas.groupby('Grupo')['SaldoAtual'].sum().reset_index()
            
            # Gráfico de receitas vs despesas
            fig = px.bar(rd_grouped, x='Grupo', y='SaldoAtual',
                         title='Receitas vs Despesas',
                         color='Grupo')
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela com maiores receitas e despesas
            st.write("Maiores Contas de Receita e Despesa:")
            top_rd = receitas_despesas.sort_values('SaldoAtual', key=abs, ascending=False).head(10)
            st.dataframe(top_rd[['Descrição', 'SaldoAtual', 'Natureza']])
        else:
            st.warning("Não foram encontrados dados de receitas e despesas.")
        
        # Análise de lançamentos
        st.subheader("Análise de Lançamentos Contábeis")
        if not data['lancamentos'].empty:
            # Contagem de lançamentos por dia
            lancamentos_diarios = data['lancamentos'].groupby('Data').size().reset_index(name='Quantidade')
            lancamentos_diarios['Data'] = pd.to_datetime(lancamentos_diarios['Data'], format='%d%m%Y')
            
            fig = px.line(lancamentos_diarios, x='Data', y='Quantidade',
                          title='Quantidade de Lançamentos por Dia')
            st.plotly_chart(fig, use_container_width=True)
            
            # Maiores lançamentos
            st.write("Maiores Lançamentos:")
            maiores_lancamentos = data['lancamentos'].sort_values('ValorConta', ascending=False).head(10)
            st.dataframe(maiores_lancamentos[['Data', 'Conta', 'ValorConta', 'NaturezaConta', 'Complemento']])
        else:
            st.warning("Não foram encontrados dados de lançamentos.")
            
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
else:
    st.info("Por favor, carregue um arquivo ECD no formato TXT para análise.")
