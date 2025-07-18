import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import io

# Configuração da página
st.set_page_config(
    page_title="Análise de ECD - Registro J155",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título do dashboard
st.title("📊 Análise de KPIs Contábeis - ECD (Registro J155)")
st.markdown("Carregue o arquivo TXT da Escrituração Contábil Digital para análise do registro J155")

# Function to parse the ECD with focus on J155
def parse_ecd_j155(file_content):
    """Processa o arquivo ECD e extrai os registros J155"""
    lines = file_content.split('\n')
    registros_j155 = []

    for line in lines:
        if not line.strip():
            continue

        # Verifica se é registro J155 (posições 1-4)
        if line.startswith('|I355|'): # Changed from J155 to I355 based on your provided file snippet
            # Remove os pipes e separa os campos
            campos = [campo.strip() for campo in line.split('|')[1:-1]]

            # Adjusted indexing for I355 based on your provided snippet
            # The snippet looks like: |I355|COD_CTA_REF||VALOR|IND_VALOR|
            # So, COD_CTA_REF is campos[1], VALOR is campos[3], IND_VALOR is campos[4]
            if len(campos) >= 5:  # Check for minimum required fields for I355
                registro = {
                    'TIPO_REG': campos[0],
                    'COD_CTA_REF': campos[1],
                    # DT_INI, DT_FIN, COD_VER, COD_FIN, NOME, CNPJ, UF, IE, COD_MUN, IM, IND_SIT_ESP are not directly in I355 line based on your snippet
                    # Setting them to None or empty for now, as they are not present in the I355 lines you provided.
                    # If these are derived from other records (like 0000, I030), you would need to parse those records first.
                    'DT_INI': None,
                    'DT_FIN': None,
                    'COD_VER': None,
                    'COD_FIN': None,
                    'NOME': None,
                    'CNPJ': None,
                    'UF': None,
                    'IE': None,
                    'COD_MUN': None,
                    'IM': None,
                    'IND_SIT_ESP': None,
                    'DESCRICAO': '', # Description is not directly in I355, would need I050 for this
                    'VALOR': float(campos[3].replace(',', '.')) if campos[3] else 0.0,
                    'IND_VALOR': campos[4]
                }
                registros_j155.append(registro)
    return pd.DataFrame(registros_j155)


def processar_kpis_j155(df_j155):
    """Processa os registros J155 (or I355 in this case) para calcular os KPIs"""
    # Group values by reference account code, considering 'D' as positive and 'C' as negative for DRE
    df_j155['VALOR_AJUSTADO'] = df_j155.apply(
        lambda row: row['VALOR'] if row['IND_VALOR'] == 'D' else -row['VALOR'],
        axis=1
    )
    df_agrupado = df_j155.groupby('COD_CTA_REF')['VALOR_AJUSTADO'].sum().reset_index()

    # Mapping of codes to DRE accounts (adjust as per your chart of accounts)
    # Based on your snippet, I see codes like 4.1.02.02.0001, 4.1.02.05.0001, etc.
    # It seems '4' might represent a major group, possibly 'CUSTOS' based on the original code.
    # Let's refine the mapping based on typical DRE structure and your example codes.
    dre_mapping = {
        '3': 'RECEITA_BRUTA', # Assuming codes starting with '3' are revenues
        '4': 'CUSTOS',        # Assuming codes starting with '4' are costs
        '5': 'DESPESAS_OPERACIONAIS', # Assuming codes starting with '5' are operating expenses
        '6': 'IMPOSTOS',      # Assuming codes starting with '6' are taxes
        # Example for Patrimonio Liquido - if it were in the J155/I355 with a specific code, like 2.01.04
        '2.01.04': 'PATRIMONIO_LIQUIDO'
    }

    kpis = {
        'PERIODO': "N/A", # Will be set if DT_INI/DT_FIN are parsed
        'RECEITA_BRUTA': 0.0,
        'DEDUCOES': 0.0,
        'CUSTOS': 0.0,
        'DESPESAS_OPERACIONAIS': 0.0,
        'IMPOSTOS': 0.0,
        'PATRIMONIO_LIQUIDO': 0.0
    }

    # Populate KPIs based on the mapping
    for _, row in df_agrupado.iterrows():
        found = False
        for codigo_prefixo, conta_kpi in dre_mapping.items():
            if row['COD_CTA_REF'].startswith(codigo_prefixo):
                kpis[conta_kpi] += row['VALOR_AJUSTADO']
                found = True
                break # Match found, move to next row

    # Calculate derived KPIs
    kpis['RECEITA_LIQUIDA'] = kpis['RECEITA_BRUTA'] - kpis['DEDUCOES'] # Deducoes would need to be identified from specific account codes
    kpis['LUCRO_BRUTO'] = kpis['RECEITA_LIQUIDA'] - kpis['CUSTOS']
    kpis['LUCRO_OPERACIONAL'] = kpis['LUCRO_BRUTO'] - kpis['DESPESAS_OPERACIONAIS']
    kpis['LUCRO_ANTES_IR'] = kpis['LUCRO_OPERACIONAL']  # Simplified
    kpis['LUCRO_LIQUIDO'] = kpis['LUCRO_ANTES_IR'] - kpis['IMPOSTOS']

    kpis['MARGEM_BRUTA'] = kpis['LUCRO_BRUTO'] / kpis['RECEITA_LIQUIDA'] if kpis['RECEITA_LIQUIDA'] != 0 else 0
    kpis['MARGEM_OPERACIONAL'] = kpis['LUCRO_OPERACIONAL'] / kpis['RECEITA_LIQUIDA'] if kpis['RECEITA_LIQUIDA'] != 0 else 0
    kpis['MARGEM_LIQUIDA'] = kpis['LUCRO_LIQUIDO'] / kpis['RECEITA_LIQUIDA'] if kpis['RECEITA_LIQUIDA'] != 0 else 0
    kpis['ROE'] = kpis['LUCRO_LIQUIDO'] / kpis['PATRIMONIO_LIQUIDO'] if kpis['PATRIMONIO_LIQUIDO'] != 0 else 0

    return kpis

# Sample content from your provided file snippet for demonstration
# In a real Streamlit app, this would come from `uploaded_file.getvalue().decode("latin-1")`
sample_file_content = """|0000|LECD|01012025|31012025|GL BRANDS IMPORTACAO, EXPORTACAO E COMERCIO LTDA|18019528000178|SC|257018760|4209102|||0|0|0||0|0||N|N|0|0||
|0001|0|
|0007|SC||
|0990|4|
|I001|0|
|I010|G|9.00|
|I030|TERMO DE ABERTURA|7|LIVRO DIARIO|2901|GL BRANDS IMPORTACAO, EXPORTACAO E COMERCIO LTDA||18019528000178|31122024||São Paulo|31122024|
|I050|01011900|01|S|1|100000000000000||Ativo|
|I050|01011900|01|S|2|1.1|100000000000000|ATIVO CIRCULANTE|
|I050|01011900|01|S|3|1.1.01|1.1|DISPONÍVEL|
|I355|4.1.02.02.0001||474,94|D|
|I355|4.1.02.02.0005||118,90|D|
|I355|4.1.02.03.0009||166,70|D|
|I355|4.1.02.03.0011||26571,81|D|
|I355|4.1.02.04.0004||13198,61|D|
|I355|4.1.02.05.0001||8974,36|D|
|I355|4.1.02.05.0003||3422,39|D|
|I355|4.1.02.05.0004||6684,82|D|
|I355|4.1.02.05.0007||5000,00|D|
|I355|4.1.02.05.0008||249,90|D|
|I355|4.1.02.06.0003||625,10|D|
|I355|4.1.02.07.0002||164"""

# This part simulates the file upload for demonstration
file_content = sample_file_content

try:
    # Process the ECD file - focus on I355 (as it appears in your snippet)
    df_i355 = parse_ecd_j155(file_content)

    if len(df_i355) == 0:
        st.error("Nenhum registro I355 encontrado no arquivo! (Esperava J155, mas seu snippet mostra I355)")
    else:
        # Process KPIs
        kpis = processar_kpis_j155(df_i355)

        # Extract company info from 0000 record if present
        company_name = "Não Encontrado"
        cnpj = "Não Encontrado"
        period_start = "N/A"
        period_end = "N/A"

        for line in file_content.split('\n'):
            if line.startswith('|0000|'):
                parts = line.split('|')
                if len(parts) > 7:
                    company_name = parts[5]
                    cnpj = parts[6]
                    period_start_str = parts[2]
                    period_end_str = parts[3]
                    try:
                        period_start = datetime.strptime(period_start_str, '%d%m%Y').strftime('%d/%m/%Y')
                        period_end = datetime.strptime(period_end_str, '%d%m%Y').strftime('%d/%m/%Y')
                    except ValueError:
                        pass # Keep as N/A if parsing fails
                break

        kpis['PERIODO'] = f"{period_start} a {period_end}"

        # Display company info
        st.subheader("Informações da Empresa")
        col1, col2, col3 = st.columns(3)
        col1.metric("Nome", company_name)
        col2.metric("CNPJ", cnpj)
        col3.metric("Período", kpis['PERIODO'])

        # Main metrics
        st.subheader("Principais KPIs - Demonstração do Resultado")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Receita Líquida", f"R$ {kpis['RECEITA_LIQUIDA']:,.2f}")
        col2.metric("Lucro Líquido", f"R$ {kpis['LUCRO_LIQUIDO']:,.2f}")
        col3.metric("Margem Líquida", f"{kpis['MARGEM_LIQUIDA']*100:.2f}%")
        col4.metric("ROE", f"{kpis['ROE']*100:.2f}%")

        # Tabs for detailed analysis
        tab1, tab2, tab3 = st.tabs(["📊 DRE Completa", "📈 Análise de Rentabilidade", "🧮 Registros I355"])

        with tab1:
            st.header("Demonstração do Resultado do Exercício")

            # Create DataFrame for DRE
            dre_data = [
                {"Descrição": "Receita Bruta", "Valor": kpis['RECEITA_BRUTA'], "Tipo": "Receita"},
                {"Descrição": "(-) Deduções", "Valor": -kpis['DEDUCOES'], "Tipo": "Dedução"},
                {"Descrição": "(=) Receita Líquida", "Valor": kpis['RECEITA_LIQUIDA'], "Tipo": "Receita"},
                {"Descrição": "(-) Custos", "Valor": -kpis['CUSTOS'], "Tipo": "Custo"},
                {"Descrição": "(=) Lucro Bruto", "Valor": kpis['LUCRO_BRUTO'], "Tipo": "Resultado"},
                {"Descrição": "(-) Despesas Operacionais", "Valor": -kpis['DESPESAS_OPERACIONAIS'], "Tipo": "Despesa"},
                {"Descrição": "(=) Lucro Operacional", "Valor": kpis['LUCRO_OPERACIONAL'], "Tipo": "Resultado"},
                {"Descrição": "(-) Impostos", "Valor": -kpis['IMPOSTOS'], "Tipo": "Imposto"},
                {"Descrição": "(=) Lucro Líquido", "Valor": kpis['LUCRO_LIQUIDO'], "Tipo": "Resultado"}
            ]
            df_dre = pd.DataFrame(dre_data)

            # Bar chart of DRE
            fig = px.bar(
                df_dre,
                x='Descrição',
                y='Valor',
                color='Tipo',
                text=[f"R$ {x:,.2f}" for x in df_dre['Valor']],
                title="Demonstração do Resultado do Exercício",
                labels={'Valor': 'Valor (R$)', 'Descrição': 'Conta'}
            )
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

            # Table with values
            st.dataframe(
                df_dre[['Descrição', 'Valor']].style.format({
                    'Valor': 'R$ {:.2f}'
                }),
                use_container_width=True
            )

        with tab2:
            st.header("Análise de Rentabilidade")

            col1, col2 = st.columns(2)

            with col1:
                # Margins chart
                margens_data = {
                    'Margem': ['Margem Bruta', 'Margem Operacional', 'Margem Líquida'],
                    'Percentual': [
                        kpis['MARGEM_BRUTA'] * 100,
                        kpis['MARGEM_OPERACIONAL'] * 100,
                        kpis['MARGEM_LIQUIDA'] * 100
                    ]
                }
                df_margens = pd.DataFrame(margens_data)

                fig = px.bar(
                    df_margens,
                    x='Margem',
                    y='Percentual',
                    text=[f"{x:.1f}%" for x in df_margens['Percentual']],
                    title="Análise de Margens",
                    labels={'Percentual': 'Percentual (%)', 'Margem': 'Tipo de Margem'}
                )
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # ROE indicator
                fig = px.bar(
                    x=['ROE'],
                    y=[kpis['ROE'] * 100],
                    text=[f"{kpis['ROE'] * 100:.1f}%"],
                    title="Retorno sobre o Patrimônio Líquido (ROE)",
                    labels={'x': '', 'y': 'Percentual (%)'}
                )
                fig.update_traces(marker_color='green')
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            # Composition analysis
            st.subheader("Composição do Resultado")
            composicao = pd.DataFrame({
                'Item': ['Receita Líquida', 'Custos', 'Despesas Operacionais', 'Impostos'],
                'Valor': [
                    kpis['RECEITA_LIQUIDA'],
                    -kpis['CUSTOS'],
                    -kpis['DESPESAS_OPERACIONAIS'],
                    -kpis['IMPOSTOS']
                ]
            })

            fig = px.pie(
                composicao,
                names='Item',
                values='Valor',
                title='Composição do Resultado',
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.header("Registros I355 da ECD") # Changed from J155 to I355

            # Filters for records
            st.subheader("Filtros de Consulta")
            col1, col2 = st.columns(2)

            with col1:
                codigo_conta = st.text_input("Filtrar por código de conta (início):")

            with col2:
                descricao_conta = st.text_input("Filtrar por descrição:")

            # Apply filters
            df_filtrado = df_i355.copy()
            if codigo_conta:
                df_filtrado = df_filtrado[df_filtrado['COD_CTA_REF'].str.startswith(codigo_conta)]
            if descricao_conta:
                # Note: 'DESCRICAO' is empty in parse_ecd_j155 for I355 records.
                # If you want to filter by description, you'd need to parse I050 records first to get account descriptions.
                st.warning("Filtrar por descrição não funcionará, pois a descrição não é extraída diretamente do registro I355. Considere o registro I050 para descrições de contas.")
                df_filtrado = df_filtrado[df_filtrado['DESCRICAO'].str.contains(descricao_conta, case=False)]

            # Show filtered records
            st.dataframe(
                df_filtrado[['COD_CTA_REF', 'DESCRICAO', 'VALOR', 'IND_VALOR']].style.format({
                    'VALOR': 'R$ {:.2f}'
                }),
                use_container_width=True,
                height=400
            )

            # Show official layout of I355 record (adapted from J155)
            st.subheader("Layout Oficial do Registro I355 (Adaptado)")
            st.markdown("""
            O registro I355 é um registro de saldo de contas analíticas ou agregadas,
            muitas vezes relacionado a um plano de contas referencial ou interno.
            O layout exato pode variar ligeiramente com as versões da ECD, mas tipicamente contém:

            | Ordem | Campo | Tipo | Descrição |
            |-------|-------|------|-----------|
            | 1 | REG | C | Tipo do registro (I355) |
            | 2 | COD_CTA_REF | C | Código da conta de referência |
            | 3 | CCE | C | Código da conta contábil |
            | 4 | VL_CTA | N | Valor da conta |
            | 5 | IND_VL | C | Indicador da natureza do valor (D - Débito / C - Crédito) |
            """)
            st.markdown("""
            **Observação:** O layout original fornecido para J155 é mais complexo e inclui
            informações como período, CNPJ, etc. Para o I355, como visto em seu snippet,
            as informações são mais concisas e focadas no código da conta e valor.
            Para um dashboard completo de DRE, normalmente se combinam informações de I355 (ou J155)
            com o plano de contas referencial (I050) e dados da empresa (0000).
            """)

except Exception as e:
    st.error(f"Erro ao processar o arquivo: {str(e)}")

# Footer
st.markdown("---")
st.markdown("**Dashboard para análise de ECD (Registro I355) - v1.0**") # Changed from J155 to I355
st.markdown(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

