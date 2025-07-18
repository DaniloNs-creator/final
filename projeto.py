import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

# Configuração inicial da página
st.set_page_config(page_title="Análise ECD", page_icon="📊", layout="wide")
st.title("📊 Dashboard de Análise Contábil e Financeira - ECD")

# Função para converter valores numéricos do formato brasileiro
def parse_br_number(number_str):
    if not number_str or number_str.strip() == '':
        return 0.0
    try:
        # Remove pontos de milhar e substitui vírgula decimal por ponto
        cleaned = number_str.replace('.', '').replace(',', '.')
        return float(cleaned)
    except ValueError:
        return 0.0

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
            if len(parts) >= 8:
                empresa_info['Nome'] = parts[4]
                empresa_info['CNPJ'] = parts[5]
                empresa_info['UF'] = parts[6]
                empresa_info['Data Início'] = parts[3]
                empresa_info['Data Fim'] = parts[4]
                empresa_info['Período'] = f"{parts[3]} a {parts[4]}"
            break
    
    # Extrair contas contábeis (registros I050)
    contas = []
    for line in lines:
        if line.startswith('|I050|'):
            parts = line.split('|')
            if len(parts) >= 9:
                contas.append({
                    'Data': parts[2],
                    'Código': parts[6],
                    'Descrição': parts[8],
                    'Tipo': parts[4],
                    'Nível': int(parts[5]) if parts[5].isdigit() else 0,
                    'ContaPai': parts[7] if parts[7] else None
                })
    
    # Extrair saldos (registros I155) com tratamento robusto de valores
    saldos = []
    for line in lines:
        if line.startswith('|I155|'):
            parts = line.split('|')
            if len(parts) >= 9:
                saldo_anterior = parse_br_number(parts[4])
                debito = parse_br_number(parts[5])
                credito = parse_br_number(parts[6])
                saldo_atual = parse_br_number(parts[7])
                
                saldos.append({
                    'Conta': parts[2],
                    'SaldoAnterior': saldo_anterior,
                    'Débito': debito,
                    'Crédito': credito,
                    'SaldoAtual': saldo_atual,
                    'Natureza': parts[8] if len(parts) > 8 else 'C'
                })
    
    # Extrair lançamentos (registros I200 e I250) com tratamento robusto de valores
    lancamentos = []
    current_lancamento = None
    for line in lines:
        if line.startswith('|I200|'):
            parts = line.split('|')
            if len(parts) >= 6:
                current_lancamento = {
                    'Número': parts[2],
                    'Data': parts[3],
                    'Valor': parse_br_number(parts[4]),
                    'Tipo': parts[5],
                    'Histórico': parts[7] if len(parts) > 7 else ''
                }
        elif line.startswith('|I250|') and current_lancamento:
            parts = line.split('|')
            if len(parts) >= 8:
                lancamentos.append({
                    **current_lancamento,
                    'Conta': parts[2],
                    'ValorConta': parse_br_number(parts[4]),
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
    if not codigo or pd.isna(codigo):
        return "Sem descrição"
    conta = contas_df[contas_df['Código'] == codigo]
    return conta['Descrição'].values[0] if not conta.empty else codigo

def analyze_balances(contas_df, saldos_df):
    """Analisa os saldos das contas"""
    if contas_df.empty or saldos_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
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
    
    # Calcular saldo considerando a natureza (Débito/Crédito)
    df['SaldoFinal'] = df.apply(
        lambda x: x['SaldoAtual'] if x['Natureza'] == 'D' else -x['SaldoAtual'], 
        axis=1
    )
    
    # Calcular totais por grupo
    group_totals = df.groupby('Grupo')['SaldoFinal'].sum().reset_index()
    
    return df, group_totals

def analyze_cash_flow(lancamentos_df, contas_df):
    """Analisa o fluxo de caixa"""
    if lancamentos_df.empty or contas_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Filtrar apenas contas de caixa e equivalentes
    cash_accounts = ['1.1.01.02', '1.1.01.03']  # Bancos e aplicações financeiras
    
    # Obter todas as contas filhas dessas contas principais
    all_cash_accounts = []
    for codigo in cash_accounts:
        all_cash_accounts.extend(contas_df[contas_df['Código'].str.startswith(codigo, na=False)]['Código'].tolist())
    
    # Filtrar lançamentos nessas contas
    cash_flow = lancamentos_df[lancamentos_df['Conta'].isin(all_cash_accounts)].copy()
    
    if cash_flow.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Classificar como entrada ou saída
    cash_flow['TipoMovimento'] = cash_flow.apply(
        lambda x: 'Entrada' if x['NaturezaConta'] == 'C' else 'Saída', axis=1)
    
    # Converter data para formato datetime
    cash_flow['Data'] = pd.to_datetime(cash_flow['Data'], format='%d%m%Y', errors='coerce')
    cash_flow = cash_flow.dropna(subset=['Data'])
    
    # Agrupar por dia e tipo
    cash_flow_daily = cash_flow.groupby(['Data', 'TipoMovimento'])['ValorConta'].sum().reset_index()
    
    return cash_flow, cash_flow_daily

def analyze_revenues_expenses(saldos_analisados):
    """Analisa receitas e despesas"""
    if saldos_analisados.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    receitas_despesas = saldos_analisados[
        saldos_analisados['Grupo'].isin(['Receita', 'Despesa', 'Custo'])
    ].copy()
    
    if receitas_despesas.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Calcular saldo final considerando a natureza
    receitas_despesas['SaldoFinal'] = receitas_despesas.apply(
        lambda x: x['SaldoAtual'] if x['Natureza'] == 'D' else -x['SaldoAtual'], 
        axis=1
    )
    
    # Agrupar por tipo
    rd_grouped = receitas_despesas.groupby('Grupo')['SaldoFinal'].sum().reset_index()
    
    return receitas_despesas, rd_grouped

# Interface do usuário
uploaded_file = st.file_uploader("Carregar arquivo ECD (TXT)", type="txt")

if uploaded_file is not None:
    try:
        with st.spinner('Processando arquivo...'):
            data = parse_ecd_file(uploaded_file)
        
        # Mostrar informações da empresa
        st.subheader("Informações da Empresa")
        if data['empresa']:
            col1, col2, col3 = st.columns(3)
            col1.metric("Nome", data['empresa'].get('Nome', 'Não informado'))
            col2.metric("CNPJ", data['empresa'].get('CNPJ', 'Não informado'))
            col3.metric("Período", data['empresa'].get('Período', 'Não informado'))
        else:
            st.warning("Não foram encontradas informações da empresa no arquivo.")
        
        # Análise de saldos
        st.subheader("Análise de Saldos Contábeis")
        saldos_analisados, group_totals = analyze_balances(data['contas'], data['saldos'])
        
        if not group_totals.empty:
            # Gráfico de saldos por grupo
            fig = px.bar(group_totals, x='Grupo', y='SaldoFinal', 
                         title='Saldos por Grupo Contábil',
                         color='Grupo',
                         labels={'SaldoFinal': 'Saldo (R$)', 'Grupo': 'Grupo Contábil'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela com principais contas
            st.write("Principais Contas:")
            principais_contas = saldos_analisados.sort_values('SaldoFinal', key=abs, ascending=False).head(10)
            principais_contas['SaldoFinal'] = principais_contas['SaldoFinal'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(principais_contas[['Descrição', 'SaldoFinal', 'Natureza']])
        else:
            st.warning("Não foram encontrados dados de saldos contábeis.")
        
        # Análise de fluxo de caixa
        st.subheader("Análise de Fluxo de Caixa")
        cash_flow, cash_flow_daily = analyze_cash_flow(data['lancamentos'], data['contas'])
        
        if not cash_flow_daily.empty:
            # Gráfico de fluxo de caixa diário
            fig = px.line(cash_flow_daily, x='Data', y='ValorConta', 
                          color='TipoMovimento',
                          title='Fluxo de Caixa Diário',
                          labels={'ValorConta': 'Valor (R$)', 'Data': 'Data'})
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
        receitas_despesas, rd_grouped = analyze_revenues_expenses(saldos_analisados)
        
        if not rd_grouped.empty:
            # Gráfico de receitas vs despesas
            fig = px.bar(rd_grouped, x='Grupo', y='SaldoFinal',
                         title='Receitas vs Despesas',
                         color='Grupo',
                         labels={'SaldoFinal': 'Valor (R$)', 'Grupo': 'Tipo'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela com maiores receitas e despesas
            st.write("Maiores Contas de Receita e Despesa:")
            top_rd = receitas_despesas.sort_values('SaldoFinal', key=abs, ascending=False).head(10)
            top_rd['SaldoFinal'] = top_rd['SaldoFinal'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(top_rd[['Descrição', 'SaldoFinal', 'Natureza']])
        else:
            st.warning("Não foram encontrados dados de receitas e despesas.")
        
        # Análise de lançamentos
        st.subheader("Análise de Lançamentos Contábeis")
        if not data['lancamentos'].empty:
            # Contagem de lançamentos por dia
            lancamentos_diarios = data['lancamentos'].copy()
            lancamentos_diarios['Data'] = pd.to_datetime(lancamentos_diarios['Data'], format='%d%m%Y', errors='coerce')
            lancamentos_diarios = lancamentos_diarios.dropna(subset=['Data'])
            
            if not lancamentos_diarios.empty:
                lancamentos_count = lancamentos_diarios.groupby('Data').size().reset_index(name='Quantidade')
                
                fig = px.line(lancamentos_count, x='Data', y='Quantidade',
                              title='Quantidade de Lançamentos por Dia',
                              labels={'Quantidade': 'Nº de Lançamentos', 'Data': 'Data'})
                st.plotly_chart(fig, use_container_width=True)
                
                # Maiores lançamentos
                st.write("Maiores Lançamentos:")
                maiores_lancamentos = data['lancamentos'].sort_values('ValorConta', ascending=False).head(10)
                maiores_lancamentos['ValorConta'] = maiores_lancamentos['ValorConta'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(maiores_lancamentos[['Data', 'Conta', 'ValorConta', 'NaturezaConta', 'Complemento']])
            else:
                st.warning("Não foi possível processar as datas dos lançamentos.")
        else:
            st.warning("Não foram encontrados dados de lançamentos.")
            
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        st.error("Por favor, verifique se o arquivo está no formato ECD correto.")
else:
    st.info("Por favor, carregue um arquivo ECD no formato TXT para análise.")
