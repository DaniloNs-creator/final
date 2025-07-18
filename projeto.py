import streamlit as st
import pandas as pd

# Funções auxiliares para cálculo dos KPIs
def calcular_kpis(df_i155):
    kpis = {}
    
    def parse_valor(valor):
        if pd.isna(valor):
            return 0.0
        if isinstance(valor, str):
            valor = valor.replace(',', '.')
            if valor.replace('.', '').isdigit():
                return float(valor)
            return 0.0
        return float(valor)
    
    try:
        # Encontrar contas relevantes nos registros I155
        ativo_total = df_i155[df_i155['COD_CTA'].str.startswith('1', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        passivo_total = df_i155[df_i155['COD_CTA'].str.startswith('2', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        patrimonio_liquido = df_i155[df_i155['COD_CTA'].str.startswith('2.3', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        
        receitas = df_i155[df_i155['COD_CTA'].str.startswith('3', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        despesas = df_i155[df_i155['COD_CTA'].str.startswith('4', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        custos = df_i155[df_i155['COD_CTA'].str.startswith('5', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        
        # Ajustar saldos conforme a natureza (Débito ou Crédito)
        def ajustar_saldo(row):
            valor = parse_valor(row['SALDO_FINAL'])
            if row['NATUREZA_FINAL'] == 'D':
                return valor
            return -valor
        
        # Recalcular totais considerando a natureza dos saldos
        ativo_total = df_i155[df_i155['COD_CTA'].str.startswith('1', na=False)].apply(ajustar_saldo, axis=1).sum()
        passivo_total = df_i155[df_i155['COD_CTA'].str.startswith('2', na=False)].apply(ajustar_saldo, axis=1).sum()
        patrimonio_liquido = df_i155[df_i155['COD_CTA'].str.startswith('2.3', na=False)].apply(ajustar_saldo, axis=1).sum()
        
        receitas = df_i155[df_i155['COD_CTA'].str.startswith('3', na=False)].apply(ajustar_saldo, axis=1).sum()
        despesas = abs(df_i155[df_i155['COD_CTA'].str.startswith('4', na=False)].apply(ajustar_saldo, axis=1).sum())
        custos = abs(df_i155[df_i155['COD_CTA'].str.startswith('5', na=False)].apply(ajustar_saldo, axis=1).sum())
        
        lucro_liquido = receitas - despesas - custos
        ebitda = lucro_liquido  # Simplificado
        
        ativo_circulante = df_i155[df_i155['COD_CTA'].str.startswith('1.1', na=False)].apply(ajustar_saldo, axis=1).sum()
        passivo_circulante = abs(df_i155[df_i155['COD_CTA'].str.startswith('2.1', na=False)].apply(ajustar_saldo, axis=1).sum())
        
        kpis['Lucro Líquido'] = lucro_liquido
        kpis['Margem de Lucro Líquido (%)'] = (lucro_liquido / receitas * 100) if receitas else 0
        kpis['EBITDA'] = ebitda
        kpis['Endividamento (%)'] = (passivo_total / ativo_total * 100) if ativo_total else 0
        kpis['Liquidez Corrente'] = (ativo_circulante / passivo_circulante) if passivo_circulante else 0
        kpis['ROE (%)'] = (lucro_liquido / patrimonio_liquido * 100) if patrimonio_liquido else 0
        
    except Exception as e:
        st.error(f"Erro ao calcular KPIs: {str(e)}")
        kpis = {
            'Lucro Líquido': 0,
            'Margem de Lucro Líquido (%)': 0,
            'EBITDA': 0,
            'Endividamento (%)': 0,
            'Liquidez Corrente': 0,
            'ROE (%)': 0
        }
    
    return kpis

# Interface Streamlit
st.title("📊 Análise de KPIs com base na ECD")

uploaded_file = st.file_uploader("Faça upload do arquivo ECD (.txt)", type=["txt"])

if uploaded_file:
    try:
        content = uploaded_file.read().decode('latin1')
        linhas = content.splitlines()

        registros_i155 = [l for l in linhas if l.startswith('|I155|')]
        
        def parse_registros(registros, colunas):
            dados = []
            for r in registros:
                campos = r.strip('|').split('|')[1:]
                if len(campos) >= len(colunas):
                    dados.append(campos[:len(colunas)])
                else:
                    dados.append(campos + [None]*(len(colunas)-len(campos)))
            return pd.DataFrame(dados, columns=colunas)
        
        df_i155 = parse_registros(registros_i155, [
            'REG', 'COD_CTA', 'VAZIO', 'VALOR_INICIAL', 'NATUREZA_INICIAL', 
            'DEBITOS', 'CREDITOS', 'SALDO_FINAL', 'NATUREZA_FINAL'
        ])
        
        # Converter apenas colunas numéricas
        for col in ['VALOR_INICIAL', 'DEBITOS', 'CREDITOS', 'SALDO_FINAL']:
            df_i155[col] = df_i155[col].apply(lambda x: float(x.replace(',', '.')) if isinstance(x, str) and x.replace(',', '').replace('.', '').isdigit() else 0.0)
        
        kpis = calcular_kpis(df_i155)
        
        st.subheader("📈 Indicadores Financeiros")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Lucro Líquido", f"R$ {kpis['Lucro Líquido']:,.2f}")
            st.metric("EBITDA", f"R$ {kpis['EBITDA']:,.2f}")
            st.metric("Liquidez Corrente", f"{kpis['Liquidez Corrente']:.2f}")
        
        with col2:
            st.metric("Margem Líquida", f"{kpis['Margem de Lucro Líquido (%)']:.2f}%")
            st.metric("Endividamento", f"{kpis['Endividamento (%)']:.2f}%")
            st.metric("ROE", f"{kpis['ROE (%)']:.2f}%")
        
        with st.expander("🔍 Visualizar dados brutos"):
            st.write("Registros I155 (Contas Contábeis)")
            st.dataframe(df_i155)
            
            st.write("Resumo por Tipo de Conta")
            df_resumo = df_i155.copy()
            df_resumo['Tipo'] = df_resumo['COD_CTA'].str.slice(0, 1).map({
                '1': 'Ativo',
                '2': 'Passivo',
                '3': 'Receitas',
                '4': 'Despesas',
                '5': 'Custos',
                '6': 'Contas de Compensação'
            })
            st.dataframe(df_resumo.groupby('Tipo')['SALDO_FINAL'].sum().reset_index())
            
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        st.error("Verifique se o arquivo está no formato correto da ECD.")
else:
    st.info("Por favor, envie um arquivo ECD no formato .txt para iniciar a análise.")
