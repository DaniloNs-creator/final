import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np

# Configuração da página
st.set_page_config(page_title="Análise Financeira Avançada", page_icon="📈", layout="wide")
st.title("📈 Dashboard de Análise Financeira Avançada")

# Funções de tratamento de dados
def parse_br_number(number_str):
    """Converte números no formato brasileiro para float"""
    if not number_str or str(number_str).strip() in ('', 'D', 'C'):
        return 0.0
    try:
        cleaned = str(number_str).replace('.', '').replace(',', '.').replace(' ', '')
        return float(cleaned)
    except ValueError:
        return 0.0

def process_ecd_file(content):
    """Processa o conteúdo do arquivo ECD"""
    lines = content.split('\n')
    
    # Extrair informações da empresa
    empresa_info = {}
    for line in lines:
        if line.startswith('|0000|'):
            parts = line.split('|')
            empresa_info = {
                'Nome': parts[4] if len(parts) > 4 else '',
                'CNPJ': parts[5] if len(parts) > 5 else '',
                'UF': parts[6] if len(parts) > 6 else '',
                'Data Início': parts[3] if len(parts) > 3 else '',
                'Data Fim': parts[4] if len(parts) > 4 else ''
            }
            break
    
    # Extrair contas e saldos
    contas = []
    saldos = []
    for line in lines:
        if line.startswith('|I050|'):
            parts = line.split('|')
            if len(parts) >= 9:
                contas.append({
                    'Código': parts[6],
                    'Descrição': parts[8],
                    'Nível': int(parts[5]) if parts[5].isdigit() else 0,
                    'ContaPai': parts[7] if len(parts) > 7 else None
                })
        elif line.startswith('|I155|'):
            parts = line.split('|')
            if len(parts) >= 9:
                saldos.append({
                    'Conta': parts[2],
                    'Saldo': parse_br_number(parts[7]),
                    'Natureza': parts[8]
                })
    
    return {
        'empresa': empresa_info,
        'contas': pd.DataFrame(contas),
        'saldos': pd.DataFrame(saldos)
    }

# Funções de cálculo de KPIs
def calculate_kpis(contas_df, saldos_df):
    """Calcula todos os KPIs financeiros"""
    # Criar dicionário de saldos por conta
    saldos_dict = {}
    for _, row in saldos_df.iterrows():
        valor = row['Saldo'] if row['Natureza'] == 'D' else -row['Saldo']
        saldos_dict[row['Conta']] = valor
    
    # Função auxiliar para obter saldo
    def get_saldo(codigo):
        return saldos_dict.get(codigo, 0)
    
    # 1. Dados do Balanço Patrimonial
    ativo_total = sum(v for k, v in saldos_dict.items() if k.startswith('1.'))
    passivo_total = sum(v for k, v in saldos_dict.items() if k.startswith('2.'))
    patrimonio_liquido = get_saldo('2.3')  # Conta do patrimônio líquido
    
    # Ativo Circulante e Não Circulante
    ativo_circulante = sum(v for k, v in saldos_dict.items() if k.startswith('1.1.'))
    ativo_nao_circulante = sum(v for k, v in saldos_dict.items() if k.startswith('1.2.'))
    
    # Passivo Circulante e Não Circulante
    passivo_circulante = sum(v for k, v in saldos_dict.items() if k.startswith('2.1.'))
    passivo_nao_circulante = sum(v for k, v in saldos_dict.items() if k.startswith('2.2.'))
    
    # 2. Dados da DRE
    receita_bruta = get_saldo('3.1')
    deducoes = abs(get_saldo('3.2'))
    receita_liquida = receita_bruta - deducoes
    custo_vendas = abs(get_saldo('5.1'))
    lucro_bruto = receita_liquida - custo_vendas
    
    despesas_operacionais = abs(sum(
        v for k, v in saldos_dict.items() 
        if k.startswith('4.1.') or k.startswith('4.3.')
    ))
    
    despesas_financeiras = abs(get_saldo('4.2'))
    receitas_financeiras = get_saldo('3.3')
    resultado_financeiro = receitas_financeiras - despesas_financeiras
    
    lucro_operacional = lucro_bruto - despesas_operacionais + resultado_financeiro
    impostos = abs(get_saldo('4.4'))
    lucro_liquido = lucro_operacional - impostos
    
    # 3. Cálculo dos KPIs
    kpis = {
        # Balanço Patrimonial
        'Ativo Total': ativo_total,
        'Passivo Total': passivo_total,
        'Patrimônio Líquido': patrimonio_liquido,
        'Ativo Circulante': ativo_circulante,
        'Ativo Não Circulante': ativo_nao_circulante,
        'Passivo Circulante': passivo_circulante,
        'Passivo Não Circulante': passivo_nao_circulante,
        
        # Demonstração de Resultados
        'Receita Bruta': receita_bruta,
        'Deduções': deducoes,
        'Receita Líquida': receita_liquida,
        'Custo das Vendas': custo_vendas,
        'Lucro Bruto': lucro_bruto,
        'Margem Bruta': (lucro_bruto / receita_liquida) * 100 if receita_liquida != 0 else 0,
        'Despesas Operacionais': despesas_operacionais,
        'Resultado Financeiro': resultado_financeiro,
        'Lucro Operacional': lucro_operacional,
        'Impostos': impostos,
        'Lucro Líquido': lucro_liquido,
        'Margem Líquida': (lucro_liquido / receita_liquida) * 100 if receita_liquida != 0 else 0,
        
        # Indicadores de Rentabilidade
        'ROE': (lucro_liquido / patrimonio_liquido) * 100 if patrimonio_liquido != 0 else 0,
        'ROA': (lucro_liquido / ativo_total) * 100 if ativo_total != 0 else 0,
        
        # Indicadores de Liquidez
        'Liquidez Corrente': ativo_circulante / passivo_circulante if passivo_circulante != 0 else 0,
        'Liquidez Seca': (ativo_circulante - get_saldo('1.1.03')) / passivo_circulante if passivo_circulante != 0 else 0,
        'Liquidez Geral': (ativo_circulante + ativo_nao_circulante) / (passivo_circulante + passivo_nao_circulante) 
                          if (passivo_circulante + passivo_nao_circulante) != 0 else 0,
        
        # Indicadores de Endividamento
        'Endividamento Geral': (passivo_total / ativo_total) * 100 if ativo_total != 0 else 0,
        'Composição do Endividamento': (passivo_circulante / passivo_total) * 100 if passivo_total != 0 else 0,
        'Garantia de Capital Próprio': patrimonio_liquido / passivo_total if passivo_total != 0 else 0,
        
        # Indicadores de Eficiência
        'Giro do Ativo': receita_liquida / ativo_total if ativo_total != 0 else 0
    }
    
    return kpis

# Interface do usuário
def main():
    uploaded_file = st.file_uploader("Carregar arquivo ECD (TXT)", type="txt")
    
    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode('utf-8')
            data = process_ecd_file(content)
            kpis = calculate_kpis(data['contas'], data['saldos'])
            
            # Mostrar informações da empresa
            st.subheader("Informações da Empresa")
            col1, col2, col3 = st.columns(3)
            col1.metric("Nome", data['empresa'].get('Nome', 'Não informado'))
            col2.metric("CNPJ", data['empresa'].get('CNPJ', 'Não informado'))
            col3.metric("UF", data['empresa'].get('UF', 'Não informado'))
            
            # Seção de Demonstração de Resultados
            st.subheader("🔄 Demonstração de Resultados")
            cols = st.columns(4)
            cols[0].metric("Receita Bruta", f"R$ {kpis['Receita Bruta']:,.2f}")
            cols[1].metric("Deduções", f"R$ {kpis['Deduções']:,.2f}", delta=f"-{kpis['Deduções']:,.2f}")
            cols[2].metric("Receita Líquida", f"R$ {kpis['Receita Líquida']:,.2f}")
            cols[3].metric("Custo das Vendas", f"R$ {kpis['Custo das Vendas']:,.2f}", delta_color="inverse")
            
            cols = st.columns(3)
            cols[0].metric("Lucro Bruto", f"R$ {kpis['Lucro Bruto']:,.2f}", 
                          delta=f"{kpis['Margem Bruta']:.2f}%")
            cols[1].metric("Despesas Operacionais", f"R$ {kpis['Despesas Operacionais']:,.2f}", delta_color="inverse")
            cols[2].metric("Resultado Financeiro", f"R$ {kpis['Resultado Financeiro']:,.2f}")
            
            cols = st.columns(3)
            cols[0].metric("Lucro Operacional", f"R$ {kpis['Lucro Operacional']:,.2f}")
            cols[1].metric("Impostos", f"R$ {kpis['Impostos']:,.2f}", delta_color="inverse")
            cols[2].metric("Lucro Líquido", f"R$ {kpis['Lucro Líquido']:,.2f}", 
                          delta=f"{kpis['Margem Líquida']:.2f}%")
            
            # Gráfico de margens
            fig = px.bar(
                x=['Margem Bruta', 'Margem Operacional', 'Margem Líquida'],
                y=[
                    kpis['Margem Bruta'], 
                    (kpis['Lucro Operacional']/kpis['Receita Líquida'])*100 if kpis['Receita Líquida'] != 0 else 0, 
                    kpis['Margem Líquida']
                ],
                title="Margens (%)",
                labels={'x': 'Tipo de Margem', 'y': 'Percentual (%)'},
                color=['Margem Bruta', 'Margem Operacional', 'Margem Líquida']
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Seção de Balanço Patrimonial
            st.subheader("🏦 Balanço Patrimonial")
            cols = st.columns(3)
            cols[0].metric("Ativo Total", f"R$ {kpis['Ativo Total']:,.2f}")
            cols[1].metric("Passivo Total", f"R$ {kpis['Passivo Total']:,.2f}")
            cols[2].metric("Patrimônio Líquido", f"R$ {kpis['Patrimônio Líquido']:,.2f}")
            
            # Gráfico de composição do ativo e passivo
            fig = px.pie(
                names=['Ativo Circulante', 'Ativo Não Circulante'],
                values=[kpis['Ativo Circulante'], kpis['Ativo Não Circulante']],
                title='Composição do Ativo',
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
            
            fig = px.pie(
                names=['Passivo Circulante', 'Passivo Não Circulante', 'Patrimônio Líquido'],
                values=[kpis['Passivo Circulante'], kpis['Passivo Não Circulante'], kpis['Patrimônio Líquido']],
                title='Composição do Passivo',
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Seção de Indicadores de Rentabilidade
            st.subheader("📈 Indicadores de Rentabilidade")
            cols = st.columns(3)
            cols[0].metric("ROE (Return on Equity)", f"{kpis['ROE']:.2f}%")
            cols[1].metric("ROA (Return on Assets)", f"{kpis['ROA']:.2f}%")
            cols[2].metric("Giro do Ativo", f"{kpis['Giro do Ativo']:.2f}x")
            
            # Seção de Indicadores de Liquidez
            st.subheader("💧 Indicadores de Liquidez")
            cols = st.columns(3)
            cols[0].metric("Liquidez Corrente", f"{kpis['Liquidez Corrente']:.2f}x",
                          help="Ativo Circulante / Passivo Circulante")
            cols[1].metric("Liquidez Seca", f"{kpis['Liquidez Seca']:.2f}x",
                          help="(Ativo Circulante - Estoques) / Passivo Circulante")
            cols[2].metric("Liquidez Geral", f"{kpis['Liquidez Geral']:.2f}x",
                          help="(Ativo Circulante + Não Circulante) / (Passivo Circulante + Não Circulante)")
            
            # Seção de Indicadores de Endividamento
            st.subheader("🏦 Indicadores de Endividamento")
            cols = st.columns(3)
            cols[0].metric("Endividamento Geral", f"{kpis['Endividamento Geral']:.2f}%",
                          help="(Passivo Total / Ativo Total) x 100")
            cols[1].metric("Composição do Endividamento", f"{kpis['Composição do Endividamento']:.2f}%",
                          help="(Passivo Circulante / Passivo Total) x 100")
            cols[2].metric("Garantia de Capital Próprio", f"{kpis['Garantia de Capital Próprio']:.2f}x",
                          help="Patrimônio Líquido / Passivo Total")
            
            # Tabela resumo de todos os KPIs
            st.subheader("📊 Resumo de Todos os KPIs")
            kpi_df = pd.DataFrame.from_dict(kpis, orient='index', columns=['Valor'])
            st.dataframe(kpi_df.style.format({'Valor': '{:,.2f}'}))
            
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
    else:
        st.info("Por favor, carregue um arquivo ECD no formato TXT para análise.")

if __name__ == "__main__":
    main()
