import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO

# Configuração inicial
st.set_page_config(layout="wide", page_title="Análise ECD Contábil")

# Funções de processamento
def processar_ecd(arquivo):
    # Ler o arquivo
    content = arquivo.getvalue().decode("utf-8")
    linhas = content.split("\n")
    
    # Processar blocos
    plano_contas = []
    saldos = []
    
    for linha in linhas:
        if linha.startswith("|I050|"):
            partes = linha.split("|")
            if len(partes) >= 10:
                plano_contas.append({
                    'codigo': partes[3],
                    'nivel': partes[6],
                    'tipo': partes[7],
                    'descricao': partes[9],
                    'conta_pai': partes[8] if partes[8] else None
                })
        elif linha.startswith("|I155|"):
            partes = linha.split("|")
            if len(partes) >= 10:
                saldos.append({
                    'conta': partes[2],
                    'saldo_inicial': float(partes[3].replace(".", "").replace(",", ".")) if partes[3] else 0,
                    'natureza_saldo_inicial': partes[4],
                    'debitos': float(partes[5].replace(".", "").replace(",", ".")) if partes[5] else 0,
                    'creditos': float(partes[6].replace(".", "").replace(",", ".")) if partes[6] else 0,
                    'saldo_final': float(partes[7].replace(".", "").replace(",", ".")) if partes[7] else 0,
                    'natureza_saldo_final': partes[8]
                })
    
    # Criar DataFrames
    df_plano = pd.DataFrame(plano_contas)
    df_saldos = pd.DataFrame(saldos)
    
    # Juntar com o plano de contas para obter descrições
    df_final = pd.merge(df_saldos, df_plano, left_on='conta', right_on='codigo', how='left')
    
    # Ajustar saldo final conforme natureza
    df_final['saldo_final_ajustado'] = df_final.apply(
        lambda x: x['saldo_final'] if x['natureza_saldo_final'] == 'D' else -x['saldo_final'], axis=1)
    
    return df_final, df_plano

def gerar_balancete(df):
    # Filtrar contas relevantes e ordenar
    balancete = df[['codigo', 'descricao', 'nivel', 'saldo_final_ajustado']].copy()
    balancete = balancete.sort_values('codigo')
    return balancete

def gerar_balanco(df):
    # Separar Ativo e Passivo/PL
    ativo = df[df['codigo'].str.startswith('1')].copy()
    passivo = df[df['codigo'].str.startswith('2')].copy()
    pl = df[df['codigo'].str.startswith('2.3')].copy()
    
    # Agrupar por níveis superiores
    ativo_agrupado = ativo.groupby(ativo['codigo'].str[:4])['saldo_final_ajustado'].sum().reset_index()
    passivo_agrupado = passivo.groupby(passivo['codigo'].str[:4])['saldo_final_ajustado'].sum().reset_index()
    
    # Adicionar descrições
    ativo_agrupado = pd.merge(ativo_agrupado, df[['codigo', 'descricao']].drop_duplicates(), 
                             left_on='codigo', right_on='codigo', how='left')
    passivo_agrupado = pd.merge(passivo_agrupado, df[['codigo', 'descricao']].drop_duplicates(), 
                               left_on='codigo', right_on='codigo', how='left')
    
    return ativo_agrupado, passivo_agrupado

def gerar_dre(df):
    # Filtrar contas de receita e despesa
    receitas = df[df['codigo'].str.startswith('3')].copy()
    despesas = df[df['codigo'].str.startswith('4')].copy()
    custos = df[df['codigo'].str.startswith('5')].copy()
    
    # Agrupar por níveis superiores
    receitas_agrupadas = receitas.groupby(receitas['codigo'].str[:4])['saldo_final_ajustado'].sum().reset_index()
    despesas_agrupadas = despesas.groupby(despesas['codigo'].str[:4])['saldo_final_ajustado'].sum().reset_index()
    custos_agrupados = custos.groupby(custos['codigo'].str[:4])['saldo_final_ajustado'].sum().reset_index()
    
    # Adicionar descrições
    receitas_agrupadas = pd.merge(receitas_agrupadas, df[['codigo', 'descricao']].drop_duplicates(), 
                                 left_on='codigo', right_on='codigo', how='left')
    despesas_agrupadas = pd.merge(despesas_agrupadas, df[['codigo', 'descricao']].drop_duplicates(), 
                                 left_on='codigo', right_on='codigo', how='left')
    custos_agrupados = pd.merge(custos_agrupados, df[['codigo', 'descricao']].drop_duplicates(), 
                               left_on='codigo', right_on='codigo', how='left')
    
    return receitas_agrupadas, despesas_agrupadas, custos_agrupados

def calcular_kpis(df):
    # Encontrar contas relevantes
    receita_bruta = df[df['codigo'] == '3.1']['saldo_final_ajustado'].sum()
    deducoes = df[df['codigo'] == '3.2']['saldo_final_ajustado'].sum()
    custos = df[df['codigo'] == '5.1']['saldo_final_ajustado'].sum()
    despesas = df[df['codigo'].str.startswith('4')]['saldo_final_ajustado'].sum()
    lucro_liquido = df[df['codigo'] == '2.3.03.01.0002']['saldo_final_ajustado'].sum()
    ativo_total = df[df['codigo'].str.startswith('1')]['saldo_final_ajustado'].sum()
    patrimonio_liquido = df[df['codigo'].str.startswith('2.3')]['saldo_final_ajustado'].sum()
    
    # Calcular KPIs
    margem_bruta = (receita_bruta + deducoes - custos) / (receita_bruta + deducoes) * 100 if (receita_bruta + deducoes) != 0 else 0
    margem_liquida = lucro_liquido / (receita_bruta + deducoes) * 100 if (receita_bruta + deducoes) != 0 else 0
    roe = lucro_liquido / patrimonio_liquido * 100 if patrimonio_liquido != 0 else 0
    roa = lucro_liquido / ativo_total * 100 if ativo_total != 0 else 0
    
    return {
        'Receita Bruta': receita_bruta,
        'Deduções': deducoes,
        'Receita Líquida': receita_bruta + deducoes,
        'Custos': custos,
        'Lucro Bruto': receita_bruta + deducoes - custos,
        'Despesas': despesas,
        'Lucro Líquido': lucro_liquido,
        'Margem Bruta (%)': margem_bruta,
        'Margem Líquida (%)': margem_liquida,
        'ROE (%)': roe,
        'ROA (%)': roa,
        'Ativo Total': ativo_total,
        'Patrimônio Líquido': patrimonio_liquido
    }

# Interface Streamlit
st.title("Análise de Demonstrações Contábeis via ECD")

# Upload do arquivo
arquivo = st.file_uploader("Carregar arquivo ECD", type=["txt"])

if arquivo is not None:
    # Processar arquivo
    df, df_plano = processar_ecd(arquivo)
    
    # Calcular KPIs
    kpis = calcular_kpis(df)
    
    # Layout
    tab1, tab2, tab3, tab4 = st.tabs(["KPIs", "Balanço Patrimonial", "DRE", "Balancete"])
    
    with tab1:
        st.header("Indicadores Financeiros")
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Lucro Líquido", f"R$ {kpis['Lucro Líquido']:,.2f}")
        col2.metric("Margem Líquida", f"{kpis['Margem Líquida (%)']:.2f}%")
        col3.metric("ROE", f"{kpis['ROE (%)']:.2f}%")
        col4.metric("ROA", f"{kpis['ROA (%)']:.2f}%")
        
        # Gráficos
        st.subheader("Análise de Rentabilidade")
        fig = px.bar(
            x=['Margem Bruta', 'Margem Líquida', 'ROE', 'ROA'],
            y=[kpis['Margem Bruta (%)'], kpis['Margem Líquida (%)'], kpis['ROE (%)'], kpis['ROA (%)']],
            labels={'x': 'Indicador', 'y': 'Percentual (%)'},
            title='Indicadores de Rentabilidade'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela de KPIs
        st.subheader("Resumo Financeiro")
        kpis_df = pd.DataFrame.from_dict(kpis, orient='index', columns=['Valor'])
        st.dataframe(kpis_df.style.format("{:,.2f}"), use_container_width=True)
    
    with tab2:
        st.header("Balanço Patrimonial")
        
        # Gerar balanço
        ativo, passivo = gerar_balanco(df)
        
        # Layout em colunas
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Ativo")
            st.dataframe(ativo[['descricao', 'saldo_final_ajustado']]
                        .rename(columns={'descricao': 'Conta', 'saldo_final_ajustado': 'Valor'})
                        .style.format({"Valor": "R$ {:,.2f}"}), 
                        use_container_width=True)
            
            # Gráfico do Ativo
            fig = px.pie(ativo, names='descricao', values='saldo_final_ajustado', 
                         title='Composição do Ativo')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Passivo e Patrimônio Líquido")
            st.dataframe(passivo[['descricao', 'saldo_final_ajustado']]
                        .rename(columns={'descricao': 'Conta', 'saldo_final_ajustado': 'Valor'})
                        .style.format({"Valor": "R$ {:,.2f}"}), 
                        use_container_width=True)
            
            # Gráfico do Passivo
            fig = px.pie(passivo, names='descricao', values='saldo_final_ajustado', 
                         title='Composição do Passivo e PL')
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.header("Demonstração do Resultado do Exercício (DRE)")
        
        # Gerar DRE
        receitas, despesas, custos = gerar_dre(df)
        
        # Formatar DRE completa
        dre_data = [
            {"Item": "Receita Bruta", "Valor": kpis['Receita Bruta']},
            {"Item": "(-) Deduções", "Valor": kpis['Deduções']},
            {"Item": "Receita Líquida", "Valor": kpis['Receita Líquida']},
            {"Item": "(-) Custos", "Valor": kpis['Custos']},
            {"Item": "Lucro Bruto", "Valor": kpis['Lucro Bruto']},
            {"Item": "(-) Despesas Operacionais", "Valor": despesas[despesas['codigo'].str.startswith('4.1')]['saldo_final_ajustado'].sum()},
            {"Item": "(-) Despesas Financeiras", "Valor": despesas[despesas['codigo'].str.startswith('4.2')]['saldo_final_ajustado'].sum()},
            {"Item": "Resultado Antes IR/CSLL", "Valor": kpis['Lucro Bruto'] - despesas['saldo_final_ajustado'].sum()},
            {"Item": "(-) Provisão para IR/CSLL", "Valor": despesas[despesas['codigo'].str.startswith('4.4')]['saldo_final_ajustado'].sum()},
            {"Item": "Lucro Líquido", "Valor": kpis['Lucro Líquido']}
        ]
        
        dre_df = pd.DataFrame(dre_data)
        st.dataframe(dre_df.style.format({"Valor": "R$ {:,.2f}"}), use_container_width=True)
        
        # Gráfico da DRE
        fig = px.bar(dre_df, x='Item', y='Valor', title='Evolução da DRE')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("Balancete Contábil")
        
        # Gerar balancete
        balancete = gerar_balancete(df)
        
        # Mostrar tabela
        st.dataframe(balancete[['codigo', 'descricao', 'saldo_final_ajustado']]
                    .rename(columns={'codigo': 'Conta', 'descricao': 'Descrição', 'saldo_final_ajustado': 'Saldo'})
                    .style.format({"Saldo": "R$ {:,.2f}"}), 
                    use_container_width=True, height=600)
        
        # Opção de download
        csv = balancete.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Baixar Balancete (CSV)",
            csv,
            "balancete.csv",
            "text/csv",
            key='download-balancete'
        )

else:
    st.info("Por favor, carregue um arquivo ECD no formato TXT para iniciar a análise.")
