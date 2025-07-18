import streamlit as st
import pandas as pd

# Funções auxiliares para cálculo dos KPIs
def calcular_kpis(df_i155):
    kpis = {}
    
    def parse_valor(valor):
        if isinstance(valor, str):
            return float(valor.replace(',', '.')) if valor.replace(',', '').replace('.', '').isdigit() else 0.0
        return float(valor) if pd.notna(valor) else 0.0
    
    # Calculando KPIs baseados nos registros I155 (contas contábeis)
    try:
        # Encontrar contas relevantes nos registros I155
        ativo_total = df_i155[df_i155['COD_CTA'].str.startswith('1', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        passivo_total = df_i155[df_i155['COD_CTA'].str.startswith('2', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        patrimonio_liquido = df_i155[df_i155['COD_CTA'].str.startswith('2.3', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        
        receitas = df_i155[df_i155['COD_CTA'].str.startswith('3', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        despesas = df_i155[df_i155['COD_CTA'].str.startswith('4', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        custos = df_i155[df_i155['COD_CTA'].str.startswith('5', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        
        lucro_liquido = receitas - despesas - custos
        ebitda = lucro_liquido  # Simplificado - seria necessário ajustar para adicionar depreciação/amortização
        
        ativo_circulante = df_i155[df_i155['COD_CTA'].str.startswith('1.1', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        passivo_circulante = df_i155[df_i155['COD_CTA'].str.startswith('2.1', na=False)]['SALDO_FINAL'].apply(parse_valor).sum()
        
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

        # Filtrar registros
        registros_i155 = [l for l in linhas if l.startswith('|I155|')]
        
        # Função para parsear registros com tratamento robusto
        def parse_registros(registros, colunas):
            dados = []
            for r in registros:
                campos = r.strip('|').split('|')[1:]  # Remove os | iniciais/finais e divide
                # Garante que temos dados suficientes para as colunas
                if len(campos) >= len(colunas):
                    dados.append(campos[:len(colunas)])
                else:
                    # Preenche com None se faltarem campos
                    dados.append(campos + [None]*(len(colunas)-len(campos)))
            return pd.DataFrame(dados, columns=colunas)
        
        # Parsear registros I155 (que têm 9 campos)
        df_i155 = parse_registros(registros_i155, [
            'REG', 'COD_CTA', 'VAZIO', 'VALOR_INICIAL', 'NATUREZA_INICIAL', 
            'DEBITOS', 'CREDITOS', 'SALDO_FINAL', 'NATUREZA_FINAL'
        ])
        
        # Converter valores numéricos
        for col in ['VALOR_INICIAL', 'DEBITOS', 'CREDITOS', 'SALDO_FINAL']:
            df_i155[col] = df_i155[col].str.replace(',', '.').astype(float)
        
        # Calcular KPIs apenas com I155 (já que J100/J150 não estão presentes no arquivo)
        kpis = calcular_kpis(df_i155)
        
        # Exibir KPIs
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
        
        # Visualização dos dados
        with st.expander("🔍 Visualizar dados brutos"):
            st.write("Registros I155 (Contas Contábeis)")
            st.dataframe(df_i155)
            
            st.write("Resumo por Tipo de Conta")
            df_resumo = df_i155.groupby(df_i155['COD_CTA'].str.slice(0, 1))['SALDO_FINAL'].sum().reset_index()
            df_resumo['Tipo'] = df_resumo['COD_CTA'].map({
                '1': 'Ativo',
                '2': 'Passivo',
                '3': 'Receitas',
                '4': 'Despesas',
                '5': 'Custos',
                '6': 'Contas de Compensação'
            })
            st.dataframe(df_resumo)
            
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
else:
    st.info("Por favor, envie um arquivo ECD no formato .txt para iniciar a análise.")
