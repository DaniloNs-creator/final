import streamlit as st
import pandas as pd

# Funções auxiliares para cálculo dos KPIs
def calcular_kpis(df_i155, df_j100, df_j150):
    kpis = {}

    def parse_valor(valor):
        try:
            return float(valor.replace(',', '.'))
        except:
            return 0.0

    lucro_liquido = df_j150[df_j150['DESCRICAO_CONTA'].str.contains('lucro', case=False, na=False)]['VALOR'].map(parse_valor).sum()
    receita_total = df_j150[df_j150['DESCRICAO_CONTA'].str.contains('receita', case=False, na=False)]['VALOR'].map(parse_valor).sum()
    despesas_total = df_j150[df_j150['DESCRICAO_CONTA'].str.contains('despesa', case=False, na=False)]['VALOR'].map(parse_valor).sum()
    ebitda = lucro_liquido + df_j150[df_j150['DESCRICAO_CONTA'].str.contains('deprecia', case=False, na=False)]['VALOR'].map(parse_valor).sum()

    ativo_total = df_j100[df_j100['DESCRICAO_CONTA'].str.contains('ativo total', case=False, na=False)]['VALOR'].map(parse_valor).sum()
    passivo_total = df_j100[df_j100['DESCRICAO_CONTA'].str.contains('passivo total', case=False, na=False)]['VALOR'].map(parse_valor).sum()
    ativo_circulante = df_j100[df_j100['DESCRICAO_CONTA'].str.contains('ativo circulante', case=False, na=False)]['VALOR'].map(parse_valor).sum()
    passivo_circulante = df_j100[df_j100['DESCRICAO_CONTA'].str.contains('passivo circulante', case=False, na=False)]['VALOR'].map(parse_valor).sum()
    patrimonio_liquido = df_j100[df_j100['DESCRICAO_CONTA'].str.contains('patrimônio líquido', case=False, na=False)]['VALOR'].map(parse_valor).sum()

    kpis['Lucro Líquido'] = lucro_liquido
    kpis['Margem de Lucro Líquido (%)'] = (lucro_liquido / receita_total * 100) if receita_total else 0
    kpis['EBITDA'] = ebitda
    kpis['Endividamento (%)'] = (passivo_total / ativo_total * 100) if ativo_total else 0
    kpis['Liquidez Corrente'] = (ativo_circulante / passivo_circulante) if passivo_circulante else 0
    kpis['ROE (%)'] = (lucro_liquido / patrimonio_liquido * 100) if patrimonio_liquido else 0

    return kpis

# Interface Streamlit
st.title("📊 Análise de KPIs com base na ECD")

uploaded_file = st.file_uploader("Faça upload do arquivo ECD (.txt)", type=["txt"])

if uploaded_file:
    content = uploaded_file.read().decode('latin1')
    linhas = content.splitlines()

    registros_i155 = [l for l in linhas if l.startswith('|I155|')]
    registros_j100 = [l for l in linhas if l.startswith('|J100|')]
    registros_j150 = [l for l in linhas if l.startswith('|J150|')]
    registros_j210 = [l for l in linhas if l.startswith('|J210|')]

    def parse_registros(registros, colunas):
        dados = [r.strip('|').split('|')[1:] for r in registros]
        return pd.DataFrame(dados, columns=colunas)

    df_i155 = parse_registros(registros_i155, ['REG', 'DT_BAL', 'COD_CTA', 'NOME_CTA', 'VALOR'])
    df_j100 = parse_registros(registros_j100, ['REG', 'DT_BAL', 'COD_AGL', 'NIVEL', 'COD_CTA', 'DESCRICAO_CONTA', 'VALOR'])
    df_j150 = parse_registros(registros_j150, ['REG', 'DT_DEM', 'COD_AGL', 'NIVEL', 'COD_CTA', 'DESCRICAO_CONTA', 'VALOR'])
    df_j210 = parse_registros(registros_j210, ['REG', 'DT_DEM', 'COD_AGL', 'NIVEL', 'COD_CTA', 'DESCRICAO_CONTA', 'VALOR'])

    kpis = calcular_kpis(df_i155, df_j100, df_j150)

    st.subheader("📈 Indicadores Financeiros")
    for kpi, valor in kpis.items():
        st.metric(label=kpi, value=f"{valor:,.2f}")

    with st.expander("🔍 Visualizar dados brutos"):
        st.write("Registros I155")
        st.dataframe(df_i155)
        st.write("Registros J100")
        st.dataframe(df_j100)
        st.write("Registros J150")
        st.dataframe(df_j150)
        st.write("Registros J210")
        st.dataframe(df_j210)
else:
    st.info("Por favor, envie um arquivo ECD no formato .txt para iniciar a análise.")
