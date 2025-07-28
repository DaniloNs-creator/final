import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO
import re

# Configuração inicial
st.set_page_config(layout="wide", page_title="Análise ECD Contábil")

# Funções auxiliares
def parse_float(value):
    """Converte string para float, tratando formatos numéricos brasileiros"""
    if not value or value.strip() == "":
        return 0.0
    try:
        # Remove pontos de milhar e substitui vírgula decimal por ponto
        cleaned = value.replace(".", "").replace(",", ".")
        return float(cleaned)
    except ValueError:
        return 0.0

def processar_ecd(arquivo):
    """Processa o arquivo ECD e retorna DataFrames com os dados"""
    try:
        # Ler o arquivo
        content = arquivo.getvalue().decode("utf-8")
        linhas = content.split("\n")
        
        plano_contas = []
        saldos = []
        
        for linha in linhas:
            if not linha.startswith("|"):
                continue
                
            partes = [p.strip() for p in linha.split("|") if p.strip() != ""]
            
            if linha.startswith("|I050|") and len(partes) >= 6:
                try:
                    plano_contas.append({
                        'codigo': partes[2] if len(partes) > 2 else "",
                        'nivel': partes[5] if len(partes) > 5 else "",
                        'tipo': partes[6] if len(partes) > 6 else "",
                        'descricao': partes[9] if len(partes) > 9 else "",
                        'conta_pai': partes[8] if len(partes) > 8 else None
                    })
                except IndexError:
                    continue
                    
            elif linha.startswith("|I155|") and len(partes) >= 8:
                try:
                    saldos.append({
                        'conta': partes[2] if len(partes) > 2 else "",
                        'saldo_inicial': parse_float(partes[3]) if len(partes) > 3 else 0,
                        'natureza_saldo_inicial': partes[4] if len(partes) > 4 else "",
                        'debitos': parse_float(partes[5]) if len(partes) > 5 else 0,
                        'creditos': parse_float(partes[6]) if len(partes) > 6 else 0,
                        'saldo_final': parse_float(partes[7]) if len(partes) > 7 else 0,
                        'natureza_saldo_final': partes[8] if len(partes) > 8 else ""
                    })
                except IndexError:
                    continue
        
        # Criar DataFrames
        df_plano = pd.DataFrame(plano_contas)
        df_saldos = pd.DataFrame(saldos)
        
        # Juntar com o plano de contas para obter descrições
        if not df_saldos.empty and not df_plano.empty:
            df_final = pd.merge(df_saldos, df_plano, left_on='conta', right_on='codigo', how='left')
            
            # Ajustar saldo final conforme natureza
            df_final['saldo_final_ajustado'] = df_final.apply(
                lambda x: x['saldo_final'] if x['natureza_saldo_final'] == 'D' else -x['saldo_final'], axis=1)
            
            return df_final, df_plano
        else:
            st.error("Não foi possível processar o arquivo ECD. Verifique o formato.")
            return pd.DataFrame(), pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

def gerar_balancete(df):
    """Gera o balancete contábil"""
    if df.empty:
        return pd.DataFrame()
        
    balancete = df[['codigo', 'descricao', 'nivel', 'saldo_final_ajustado']].copy()
    balancete = balancete.sort_values('codigo')
    return balancete

def gerar_balanco(df):
    """Separa Ativo e Passivo/PL"""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    ativo = df[df['codigo'].str.startswith('1', na=False)].copy()
    passivo = df[df['codigo'].str.startswith('2', na=False)].copy()
    
    # Agrupar por níveis superiores
    ativo['grupo'] = ativo['codigo'].str[:4]
    passivo['grupo'] = passivo['codigo'].str[:4]
    
    ativo_agrupado = ativo.groupby('grupo', as_index=False).agg({
        'saldo_final_ajustado': 'sum',
        'descricao': 'first'
    })
    
    passivo_agrupado = passivo.groupby('grupo', as_index=False).agg({
        'saldo_final_ajustado': 'sum',
        'descricao': 'first'
    })
    
    return ativo_agrupado, passivo_agrupado

def gerar_dre(df):
    """Gera a Demonstração do Resultado"""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    receitas = df[df['codigo'].str.startswith('3', na=False)].copy()
    despesas = df[df['codigo'].str.startswith('4', na=False)].copy()
    custos = df[df['codigo'].str.startswith('5', na=False)].copy()
    
    # Agrupar por níveis superiores
    receitas['grupo'] = receitas['codigo'].str[:4]
    despesas['grupo'] = despesas['codigo'].str[:4]
    custos['grupo'] = custos['codigo'].str[:4]
    
    receitas_agrupadas = receitas.groupby('grupo', as_index=False).agg({
        'saldo_final_ajustado': 'sum',
        'descricao': 'first'
    })
    
    despesas_agrupadas = despesas.groupby('grupo', as_index=False).agg({
        'saldo_final_ajustado': 'sum',
        'descricao': 'first'
    })
    
    custos_agrupados = custos.groupby('grupo', as_index=False).agg({
        'saldo_final_ajustado': 'sum',
        'descricao': 'first'
    })
    
    return receitas_agrupadas, despesas_agrupadas, custos_agrupados

def calcular_kpis(df):
    """Calcula os principais indicadores financeiros"""
    if df.empty:
        return {}
    
    try:
        receita_bruta = df[df['codigo'] == '3.1']['saldo_final_ajustado'].sum()
        deducoes = abs(df[df['codigo'] == '3.2']['saldo_final_ajustado'].sum())
        custos = abs(df[df['codigo'] == '5.1']['saldo_final_ajustado'].sum())
        despesas = abs(df[df['codigo'].str.startswith('4', na=False)]['saldo_final_ajustado'].sum())
        
        # Lucro líquido pode estar em 2.3.03.01.0001 ou 2.3.03.01.0002
        lucro_liquido = df[df['codigo'].str.startswith('2.3.03.01', na=False)]['saldo_final_ajustado'].sum()
        
        ativo_total = df[df['codigo'].str.startswith('1', na=False)]['saldo_final_ajustado'].sum()
        patrimonio_liquido = df[df['codigo'].str.startswith('2.3', na=False)]['saldo_final_ajustado'].sum()
        
        # Cálculos com tratamento para divisão por zero
        receita_liquida = receita_bruta - deducoes
        margem_bruta = (receita_liquida - custos) / receita_liquida * 100 if receita_liquida != 0 else 0
        margem_liquida = lucro_liquido / receita_liquida * 100 if receita_liquida != 0 else 0
        roe = lucro_liquido / patrimonio_liquido * 100 if patrimonio_liquido != 0 else 0
        roa = lucro_liquido / ativo_total * 100 if ativo_total != 0 else 0
        
        return {
            'Receita Bruta': receita_bruta,
            'Deduções': deducoes,
            'Receita Líquida': receita_liquida,
            'Custos': custos,
            'Lucro Bruto': receita_liquida - custos,
            'Despesas': despesas,
            'Lucro Líquido': lucro_liquido,
            'Margem Bruta (%)': margem_bruta,
            'Margem Líquida (%)': margem_liquida,
            'ROE (%)': roe,
            'ROA (%)': roa,
            'Ativo Total': ativo_total,
            'Patrimônio Líquido': patrimonio_liquido
        }
    except Exception as e:
        st.error(f"Erro ao calcular KPIs: {str(e)}")
        return {}

# Interface Streamlit
st.title("📊 Análise de Demonstrações Contábeis via ECD")

# Upload do arquivo
with st.expander("🔽 Upload do Arquivo ECD", expanded=True):
    arquivo = st.file_uploader("Carregar arquivo ECD (TXT)", type=["txt"], help="Selecione o arquivo ECD no formato TXT")
    if arquivo:
        st.success("Arquivo carregado com sucesso!")

if arquivo is not None:
    # Processar arquivo
    with st.spinner("Processando arquivo ECD..."):
        df, df_plano = processar_ecd(arquivo)
    
    if not df.empty:
        # Calcular KPIs
        kpis = calcular_kpis(df)
        
        # Layout
        tab1, tab2, tab3, tab4 = st.tabs(["📈 KPIs", "🏦 Balanço", "📋 DRE", "🧾 Balancete"])
        
        with tab1:
            st.header("📊 Indicadores Financeiros")
            
            if kpis:
                # Métricas principais
                cols = st.columns(4)
                cols[0].metric("💰 Lucro Líquido", f"R$ {kpis['Lucro Líquido']:,.2f}", 
                             help="Resultado final do exercício")
                cols[1].metric("📈 Margem Líquida", f"{kpis['Margem Líquida (%)']:.2f}%", 
                             help="Lucro líquido / Receita líquida")
                cols[2].metric("📊 ROE", f"{kpis['ROE (%)']:.2f}%", 
                             help="Retorno sobre Patrimônio Líquido")
                cols[3].metric("🏛️ ROA", f"{kpis['ROA (%)']:.2f}%", 
                             help="Retorno sobre Ativos")
                
                # Gráficos
                st.subheader("📈 Análise de Rentabilidade")
                fig = px.bar(
                    x=['Margem Bruta', 'Margem Líquida', 'ROE', 'ROA'],
                    y=[kpis['Margem Bruta (%)'], kpis['Margem Líquida (%)'], kpis['ROE (%)'], kpis['ROA (%)']],
                    labels={'x': 'Indicador', 'y': 'Percentual (%)'},
                    title='Indicadores de Rentabilidade',
                    color=['Margem Bruta', 'Margem Líquida', 'ROE', 'ROA']
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela de KPIs
                st.subheader("📋 Resumo Financeiro")
                kpis_df = pd.DataFrame.from_dict(kpis, orient='index', columns=['Valor'])
                st.dataframe(
                    kpis_df.style.format({"Valor": "R$ {:,.2f}" if not isinstance(kpis_df['Valor'].iloc[0], str) else "{}"}),
                    use_container_width=True
                )
            else:
                st.warning("Não foi possível calcular os indicadores financeiros.")
        
        with tab2:
            st.header("🏦 Balanço Patrimonial")
            
            ativo, passivo = gerar_balanco(df)
            
            if not ativo.empty and not passivo.empty:
                # Layout em colunas
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🟢 Ativo")
                    st.dataframe(
                        ativo[['descricao', 'saldo_final_ajustado']]
                        .rename(columns={'descricao': 'Conta', 'saldo_final_ajustado': 'Valor'})
                        .style.format({"Valor": "R$ {:,.2f}"}), 
                        use_container_width=True,
                        height=400
                    )
                    
                    # Gráfico do Ativo
                    fig = px.pie(
                        ativo, 
                        names='descricao', 
                        values='saldo_final_ajustado', 
                        title='Composição do Ativo',
                        hole=0.3
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.subheader("🔴 Passivo e Patrimônio Líquido")
                    st.dataframe(
                        passivo[['descricao', 'saldo_final_ajustado']]
                        .rename(columns={'descricao': 'Conta', 'saldo_final_ajustado': 'Valor'})
                        .style.format({"Valor": "R$ {:,.2f}"}), 
                        use_container_width=True,
                        height=400
                    )
                    
                    # Gráfico do Passivo
                    fig = px.pie(
                        passivo, 
                        names='descricao', 
                        values='saldo_final_ajustado', 
                        title='Composição do Passivo e PL',
                        hole=0.3
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Dados insuficientes para gerar o Balanço Patrimonial.")
        
        with tab3:
            st.header("📋 Demonstração do Resultado do Exercício (DRE)")
            
            receitas, despesas, custos = gerar_dre(df)
            
            if not receitas.empty and not despesas.empty and not custos.empty:
                # Formatar DRE completa
                receita_bruta = receitas[receitas['grupo'] == '3.1']['saldo_final_ajustado'].sum()
                deducoes = abs(receitas[receitas['grupo'] == '3.2']['saldo_final_ajustado'].sum())
                custo_total = abs(custos['saldo_final_ajustado'].sum())
                despesas_oper = abs(despesas[despesas['grupo'].str.startswith('4.1')]['saldo_final_ajustado'].sum())
                despesas_fin = abs(despesas[despesas['grupo'].str.startswith('4.2')]['saldo_final_ajustado'].sum())
                provisoes = abs(despesas[despesas['grupo'].str.startswith('4.4')]['saldo_final_ajustado'].sum())
                
                dre_data = [
                    {"Item": "Receita Bruta", "Valor": receita_bruta},
                    {"Item": "(-) Deduções", "Valor": -deducoes},
                    {"Item": "Receita Líquida", "Valor": receita_bruta - deducoes},
                    {"Item": "(-) Custos", "Valor": -custo_total},
                    {"Item": "Lucro Bruto", "Valor": receita_bruta - deducoes - custo_total},
                    {"Item": "(-) Despesas Operacionais", "Valor": -despesas_oper},
                    {"Item": "(-) Despesas Financeiras", "Valor": -despesas_fin},
                    {"Item": "Resultado Antes IR/CSLL", "Valor": receita_bruta - deducoes - custo_total - despesas_oper - despesas_fin},
                    {"Item": "(-) Provisão para IR/CSLL", "Valor": -provisoes},
                    {"Item": "Lucro Líquido", "Valor": receita_bruta - deducoes - custo_total - despesas_oper - despesas_fin - provisoes}
                ]
                
                dre_df = pd.DataFrame(dre_data)
                st.dataframe(
                    dre_df.style.format({"Valor": "R$ {:,.2f}"}), 
                    use_container_width=True,
                    hide_index=True
                )
                
                # Gráfico da DRE
                fig = px.bar(
                    dre_df, 
                    x='Item', 
                    y='Valor', 
                    title='Evolução da DRE',
                    color='Item',
                    text='Valor'
                )
                fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Dados insuficientes para gerar a DRE.")
        
        with tab4:
            st.header("🧾 Balancete Contábil")
            
            balancete = gerar_balancete(df)
            
            if not balancete.empty:
                # Mostrar tabela
                st.dataframe(
                    balancete[['codigo', 'descricao', 'saldo_final_ajustado']]
                    .rename(columns={'codigo': 'Conta', 'descricao': 'Descrição', 'saldo_final_ajustado': 'Saldo'})
                    .style.format({"Saldo": "R$ {:,.2f}"}), 
                    use_container_width=True, 
                    height=600
                )
                
                # Opção de download
                csv = balancete.to_csv(index=False, sep=";", decimal=",", encoding='utf-8-sig')
                st.download_button(
                    "⬇️ Baixar Balancete (CSV)",
                    csv,
                    "balancete.csv",
                    "text/csv",
                    key='download-balancete'
                )
            else:
                st.warning("Não foi possível gerar o balancete contábil.")
    else:
        st.error("O arquivo ECD não contém dados válidos para análise.")

else:
    st.info("ℹ️ Por favor, carregue um arquivo ECD no formato TXT para iniciar a análise.")
    st.markdown("""
    ### Como usar:
    1. Clique em "Browse files" ou arraste um arquivo ECD (TXT) para a área acima
    2. Aguarde o processamento do arquivo
    3. Navegue pelas abas para visualizar as análises
                
    ### Formato esperado:
    - Arquivo texto no formato ECD (Escrituração Contábil Digital)
    - Deve conter os blocos I050 (Plano de Contas) e I155 (Saldos)
    """)
