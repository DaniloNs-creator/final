import streamlit as st
import pandas as pd
import io
import plotly.express as px

# Função para processar o arquivo ECD
def processar_ecd(arquivo):
    # Lê o arquivo como texto
    conteudo = arquivo.read().decode('utf-8')
    linhas = conteudo.split('\n')
    
    # Filtra apenas as linhas I155 (saldos das contas)
    linhas_i155 = [linha for linha in linhas if linha.startswith('|I155|')]
    
    dados = []
    for linha in linhas_i155:
        partes = linha.split('|')
        if len(partes) >= 10:
            conta = partes[2]
            saldo_final_valor = partes[8]
            natureza_saldo = partes[9]
            
            # Converte o saldo para float, tratando valores vazios
            try:
                saldo_final = float(saldo_final_valor.replace(',', '.')) if saldo_final_valor else 0.0
            except:
                saldo_final = 0.0
                
            # Ajusta o sinal conforme a natureza do saldo
            if natureza_saldo == 'D':
                saldo_final = -saldo_final
                
            dados.append({
                'Conta': conta,
                'Descricao': obter_descricao_conta(conta, linhas),
                'Saldo': saldo_final
            })
    
    df = pd.DataFrame(dados)
    return df

# Função auxiliar para obter descrição das contas do bloco I050
def obter_descricao_conta(codigo, linhas):
    for linha in linhas:
        if linha.startswith('|I050|') and codigo in linha:
            partes = linha.split('|')
            if len(partes) >= 11:
                return partes[10]
    return codigo

# Função para calcular KPIs
def calcular_kpis(df):
    kpis = {}
    
    # Ativo Total
    ativo_total = df[df['Conta'].str.startswith('1.')]['Saldo'].sum()
    
    # Passivo Total
    passivo_total = df[df['Conta'].str.startswith('2.')]['Saldo'].sum()
    
    # Patrimônio Líquido
    pl = df[df['Conta'].str.startswith('2.3')]['Saldo'].sum()
    
    # Receita Líquida
    receita_bruta = df[df['Conta'].str.startswith('3.1')]['Saldo'].sum()
    deducoes = abs(df[df['Conta'].str.startswith('3.2')]['Saldo'].sum())
    receita_liquida = receita_bruta - deducoes
    
    # Custo das Mercadorias Vendidas
    cmv = abs(df[df['Conta'].str.startswith('5.1')]['Saldo'].sum())
    
    # Lucro Bruto
    lucro_bruto = receita_liquida - cmv
    
    # Despesas Operacionais
    despesas_operacionais = abs(df[df['Conta'].str.startswith('4.1')]['Saldo'].sum())
    
    # Despesas Financeiras
    despesas_financeiras = abs(df[df['Conta'].str.startswith('4.2')]['Saldo'].sum())
    
    # Outras Receitas/Despesas
    outras_receitas_despesas = df[df['Conta'].str.startswith('4.3')]['Saldo'].sum()
    
    # Lucro Operacional
    lucro_operacional = lucro_bruto - despesas_operacionais
    
    # Lucro Líquido antes do IR/CSLL
    lucro_antes_ir = lucro_operacional - despesas_financeiras + outras_receitas_despesas
    
    # Provisão para IR/CSLL
    provisao_ir = abs(df[df['Conta'].str.startswith('4.4')]['Saldo'].sum())
    
    # Lucro Líquido
    lucro_liquido = lucro_antes_ir - provisao_ir
    
    # Margem Bruta
    margem_bruta = (lucro_bruto / receita_liquida) * 100 if receita_liquida != 0 else 0
    
    # Margem Operacional
    margem_operacional = (lucro_operacional / receita_liquida) * 100 if receita_liquida != 0 else 0
    
    # Margem Líquida
    margem_liquida = (lucro_liquido / receita_liquida) * 100 if receita_liquida != 0 else 0
    
    # ROE (Return on Equity)
    roe = (lucro_liquido / pl) * 100 if pl != 0 else 0
    
    # ROA (Return on Assets)
    roa = (lucro_liquido / ativo_total) * 100 if ativo_total != 0 else 0
    
    # Liquidez Corrente
    ativo_circulante = df[df['Conta'].str.startswith('1.1')]['Saldo'].sum()
    passivo_circulante = df[df['Conta'].str.startswith('2.1')]['Saldo'].sum()
    liquidez_corrente = ativo_circulante / passivo_circulante if passivo_circulante != 0 else 0
    
    # Endividamento Geral
    endividamento_geral = passivo_total / (passivo_total + pl) * 100 if (passivo_total + pl) != 0 else 0
    
    # Compilando os KPIs
    kpis = {
        'Receita Líquida': receita_liquida,
        'Lucro Bruto': lucro_bruto,
        'Lucro Operacional': lucro_operacional,
        'Lucro Líquido': lucro_liquido,
        'Margem Bruta (%)': margem_bruta,
        'Margem Operacional (%)': margem_operacional,
        'Margem Líquida (%)': margem_liquida,
        'ROE (%)': roe,
        'ROA (%)': roa,
        'Ativo Total': ativo_total,
        'Passivo Total': passivo_total,
        'Patrimônio Líquido': pl,
        'Liquidez Corrente': liquidez_corrente,
        'Endividamento Geral (%)': endividamento_geral
    }
    
    return kpis

# Configuração da página Streamlit
st.set_page_config(page_title="Análise de KPIs Contábeis", layout="wide")

st.title("📊 Análise de KPIs de Demonstrações Contábeis")
st.markdown("""
Esta aplicação analisa os principais indicadores financeiros a partir de um arquivo ECD (Escrituração Contábil Digital).
""")

# Upload do arquivo
arquivo = st.file_uploader("Carregue o arquivo ECD (formato TXT)", type=['txt'])

if arquivo is not None:
    try:
        # Processa o arquivo ECD
        df_contas = processar_ecd(arquivo)
        kpis = calcular_kpis(df_contas)
        
        # Exibe os dados brutos
        st.subheader("Dados das Contas Contábeis")
        st.dataframe(df_contas)
        
        # KPIs principais
        st.subheader("Principais KPIs Financeiros")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Receita Líquida", f"R$ {kpis['Receita Líquida']:,.2f}")
            st.metric("Lucro Bruto", f"R$ {kpis['Lucro Bruto']:,.2f}")
            st.metric("Lucro Operacional", f"R$ {kpis['Lucro Operacional']:,.2f}")
            
        with col2:
            st.metric("Lucro Líquido", f"R$ {kpis['Lucro Líquido']:,.2f}")
            st.metric("Margem Bruta", f"{kpis['Margem Bruta (%)']:.2f}%")
            st.metric("Margem Operacional", f"{kpis['Margem Operacional (%)']:.2f}%")
            
        with col3:
            st.metric("Margem Líquida", f"{kpis['Margem Líquida (%)']:.2f}%")
            st.metric("ROE", f"{kpis['ROE (%)']:.2f}%")
            st.metric("ROA", f"{kpis['ROA (%)']:.2f}%")
        
        # Gráfico de margens
        st.subheader("Análise de Margens")
        margens = {
            'Margem': ['Bruta', 'Operacional', 'Líquida'],
            'Valor (%)': [kpis['Margem Bruta (%)'], kpis['Margem Operacional (%)'], kpis['Margem Líquida (%)']]
        }
        df_margens = pd.DataFrame(margens)
        fig = px.bar(df_margens, x='Margem', y='Valor (%)', text='Valor (%)',
                     title="Comparativo de Margens (%)", color='Margem')
        fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        # Estrutura do Balanço
        st.subheader("Estrutura do Balanço Patrimonial")
        balanco = {
            'Item': ['Ativo Total', 'Passivo Total', 'Patrimônio Líquido'],
            'Valor (R$)': [kpis['Ativo Total'], kpis['Passivo Total'], kpis['Patrimônio Líquido']]
        }
        df_balanco = pd.DataFrame(balanco)
        fig2 = px.pie(df_balanco, names='Item', values='Valor (R$)', 
                      title="Composição do Balanço Patrimonial")
        st.plotly_chart(fig2, use_container_width=True)
        
        # Indicadores de Liquidez e Endividamento
        st.subheader("Indicadores Financeiros")
        col4, col5 = st.columns(2)
        
        with col4:
            st.metric("Liquidez Corrente", f"{kpis['Liquidez Corrente']:.2f}")
            
        with col5:
            st.metric("Endividamento Geral", f"{kpis['Endividamento Geral (%)']:.2f}%")
        
        # Tabela com todos os KPIs
        st.subheader("Resumo dos Indicadores")
        df_kpis = pd.DataFrame(list(kpis.items()), columns=['Indicador', 'Valor'])
        st.dataframe(df_kpis.style.format({
            'Valor': lambda x: f"R$ {x:,.2f}" if isinstance(x, (int, float)) and abs(x) > 1000 else f"{x:.2f}%"
        }))
        
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
else:
    st.info("Por favor, carregue um arquivo ECD para análise.")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido para análise de arquivos ECD - Escrituração Contábil Digital")
