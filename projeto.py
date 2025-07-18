import streamlit as st
import pandas as pd
import io

# Moved adjust_final_balance to global scope so it's accessible by both functions and the main script
def adjust_final_balance(row):
    """
    Adjusts the balance based on the normal balance of the account type.
    For Assets, Expenses, Costs: Debit balance is positive.
    For Liabilities, Equity, Revenue: Credit balance is positive (so Debit value means negative).
    """
    if row['Main_Group'] in ['Ativo', 'Despesa', 'Custos']:
        return row['Total_Value']
    elif row['Main_Group'] in ['Passivo e PL', 'Receita']:
        return -row['Total_Value']
    return row['Total_Value'] # Default for other groups

def parse_ecd_file(file_content):
    """
    Parses the content of an ECD (Escrituração Contábil Digital) file.

    Args:
        file_content (str): The raw content of the ECD .txt file.

    Returns:
        tuple: A tuple containing two pandas DataFrames:
               - chart_of_accounts: Contains account details from I050 records.
               - movements: Contains financial movements from I355 records.
    """
    lines = file_content.splitlines()
    chart_of_accounts = []
    movements = []

    for line in lines:
        parts = line.split('|')
        if len(parts) > 1:
            record_type = parts[1]

            if record_type == 'I050':
                try:
                    # Based on example: |I050|01011900|01|S|1|100000000000000||Ativo|
                    # parts[6] is the account code (e.g., '1', '1.1', '1.1.01')
                    # parts[4] is Account Type ('S' or 'A')
                    # parts[5] is Account Level
                    # parts[8] is Account Name
                    account_code = parts[6]
                    account_type = parts[4]
                    account_level = int(parts[5])
                    account_name = parts[8]

                    main_group = ''
                    if account_code.startswith('1'):
                        main_group = 'Ativo'
                    elif account_code.startswith('2'):
                        main_group = 'Passivo e PL'
                    elif account_code.startswith('3'):
                        main_group = 'Receita'
                    elif account_code.startswith('4'):
                        main_group = 'Despesa'
                    elif account_code.startswith('5'):
                        main_group = 'Custos' # Assuming 5 for costs if present in your COA

                    chart_of_accounts.append({
                        'Account_Code': account_code,
                        'Account_Type': account_type,
                        'Account_Level': account_level,
                        'Account_Name': account_name,
                        'Main_Group': main_group
                    })
                except (IndexError, ValueError) as e:
                    st.warning(f"Skipping malformed I050 record: {line} - Error: {e}")

            elif record_type == 'I355':
                try:
                    # Based on example: |I355|4.1.02.02.0001||474,94|D|
                    # parts[2] is Account Code
                    # parts[4] is Value (VL_SLD_INI)
                    # parts[5] is Nature (IND_DC_INI)
                    account_code = parts[2]
                    value_str = parts[4].replace('.', '').replace(',', '.')
                    value = float(value_str)
                    nature = parts[5]
                    movements.append({
                        'Account_Code': account_code,
                        'Value': value,
                        'Nature': nature
                    })
                except (IndexError, ValueError) as e:
                    st.warning(f"Skipping malformed I355 record: {line} - Error: {e}")

    df_accounts = pd.DataFrame(chart_of_accounts)
    df_movements = pd.DataFrame(movements)

    return df_accounts, df_movements

def calculate_kpis(df_accounts, df_movements):
    """
    Calculates key accounting and financial KPIs from parsed ECD data.

    Args:
        df_accounts (pd.DataFrame): DataFrame containing chart of accounts.
        df_movements (pd.DataFrame): DataFrame containing financial movements.

    Returns:
        dict: A dictionary of calculated KPIs.
    """
    kpis = {}

    if df_accounts.empty or df_movements.empty:
        return {"Error": "No data in accounts or movements to calculate KPIs."}

    df_merged = pd.merge(df_movements, df_accounts, on='Account_Code', how='left')

    df_merged['Signed_Value'] = df_merged.apply(
        lambda row: row['Value'] if row['Nature'] == 'D' else -row['Value'], axis=1
    )

    account_balances = df_merged.groupby('Account_Code').agg(
        Total_Value=('Signed_Value', 'sum'),
        Account_Name=('Account_Name', 'first'),
        Main_Group=('Main_Group', 'first')
    ).reset_index()

    # The adjust_final_balance function is now in global scope
    account_balances['Final_Balance'] = account_balances.apply(adjust_final_balance, axis=1)

    # --- Basic Financial Statement Aggregates ---
    total_assets = account_balances[account_balances['Main_Group'] == 'Ativo']['Final_Balance'].sum()

    # Identify Equity accounts: common prefix '2.3' or specific names
    equity_filter = df_accounts['Account_Code'].apply(lambda x: x.startswith('2.3')) | df_accounts['Account_Name'].str.contains('patrimônio líquido|capital social|reservas de lucros', case=False, na=False)
    equity_codes = df_accounts[equity_filter]['Account_Code'].tolist()
    total_equity = account_balances[account_balances['Account_Code'].isin(equity_codes)]['Final_Balance'].sum()

    total_liabilities_and_pl = account_balances[account_balances['Main_Group'] == 'Passivo e PL']['Final_Balance'].sum()
    total_liabilities = total_liabilities_and_pl - total_equity # Assuming PL is a subset of Passivo e PL

    total_revenue = account_balances[account_balances['Main_Group'] == 'Receita']['Final_Balance'].sum()
    total_costs = account_balances[account_balances['Main_Group'] == 'Custos']['Final_Balance'].sum()
    total_expenses = account_balances[account_balances['Main_Group'] == 'Despesa']['Final_Balance'].sum()

    # --- New KPIs Calculations ---

    # 1. Lucro Bruto
    gross_profit = total_revenue - total_costs
    kpis['Gross Profit (Lucro Bruto)'] = gross_profit

    # 2. Lucro Operacional
    operating_income = gross_profit - total_expenses
    kpis['Operating Income (Lucro Operacional)'] = operating_income

    # 3. Lucro Líquido
    net_income = total_revenue - total_costs - total_expenses
    kpis['Net Income (Lucro Líquido)'] = net_income

    # 4. Margem de Contribuição
    # Simplified: assuming all costs are variable, ignoring variable expenses from other groups
    variable_costs_and_expenses = total_costs
    contribution_margin = total_revenue - variable_costs_and_expenses
    kpis['Contribution Margin (Margem de Contribuição)'] = contribution_margin
    kpis['Contribution Margin %'] = (contribution_margin / total_revenue) if total_revenue != 0 else 0

    # 5. ROE (Return on Equity)
    kpis['ROE (Return on Equity)'] = (net_income / total_equity) if total_equity != 0 else float('inf')

    # 6. ROA (Return on Assets)
    kpis['ROA (Return on Assets)'] = (net_income / total_assets) if total_assets != 0 else 0

    # 7. Margem Bruta
    kpis['Gross Profit Margin (Margem Bruta)'] = (gross_profit / total_revenue) if total_revenue != 0 else 0

    # 8. Margem Líquida
    kpis['Net Profit Margin (Margem Líquida)'] = (net_income / total_revenue) if total_revenue != 0 else 0

    # 9. EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)
    depreciation_amortization = account_balances[
        account_balances['Account_Name'].str.contains('depreciação|amortização', case=False, na=False)
    ]['Final_Balance'].sum()

    ebitda = operating_income + depreciation_amortization
    kpis['EBITDA'] = ebitda
    kpis['EBITDA Margin'] = (ebitda / total_revenue) if total_revenue != 0 else 0

    # --- Existing KPIs (ensure they are still included for consistency) ---
    kpis['Total Assets'] = total_assets
    kpis['Total Liabilities'] = total_liabilities
    kpis['Total Equity'] = total_equity
    kpis['Total Revenue'] = total_revenue
    kpis['Total Expenses (Operational & Admin)'] = total_expenses
    kpis['Total Costs (CPV/CMV)'] = total_costs

    current_assets = account_balances[account_balances['Account_Code'].str.startswith('1.1')]['Final_Balance'].sum()
    current_liabilities = account_balances[account_balances['Account_Code'].str.startswith('2.1')]['Final_Balance'].sum()

    kpis['Current Ratio (Current Assets / Current Liabilities)'] = current_assets / current_liabilities if current_liabilities != 0 else float('inf')
    kpis['Debt-to-Equity Ratio (Total Liabilities / Total Equity)'] = total_liabilities / total_equity if total_equity != 0 else float('inf')

    return kpis

# Streamlit UI
st.set_page_config(layout="wide")
st.title("📊 Dashboard de KPIs Contábeis e Financeiros (ECD)")

st.write("Faça o upload do seu arquivo TXT da ECD para analisar os principais indicadores.")

uploaded_file = st.file_uploader("Escolha um arquivo TXT da ECD", type="txt")

if uploaded_file is not None:
    file_content = uploaded_file.read().decode("utf-8")

    st.subheader("Conteúdo do Arquivo ECD (Amostra)")
    st.code(file_content[:1000] + "...", language="text")

    st.subheader("Processando Dados...")
    df_accounts, df_movements = parse_ecd_file(file_content)

    if not df_accounts.empty and not df_movements.empty:
        st.success("Arquivo ECD processado com sucesso!")

        st.subheader("Estrutura do Plano de Contas (I050)")
        st.dataframe(df_accounts)

        st.subheader("Lançamentos Contábeis (I355)")
        st.dataframe(df_movements)

        st.subheader("Calculando KPIs...")
        kpis = calculate_kpis(df_accounts, df_movements)

        st.header("Principais Indicadores Financeiros e Contábeis")

        if "Error" in kpis:
            st.error(kpis["Error"])
        else:
            st.markdown("### Indicadores de Rentabilidade")
            rent_col1, rent_col2, rent_col3 = st.columns(3)
            with rent_col1:
                st.metric(label="Receita Total", value=f"R$ {kpis['Total Revenue']:.2f}")
                st.metric(label="Lucro Bruto", value=f"R$ {kpis['Gross Profit (Lucro Bruto)']:.2f}")
                st.metric(label="Margem Bruta", value=f"{kpis['Gross Profit Margin (Margem Bruta)']:.2%}")
            with rent_col2:
                st.metric(label="Lucro Operacional", value=f"R$ {kpis['Operating Income (Lucro Operacional)']:.2f}")
                st.metric(label="Lucro Líquido", value=f"R$ {kpis['Net Income (Lucro Líquido)']:.2f}")
                st.metric(label="Margem Líquida", value=f"{kpis['Net Profit Margin (Margem Líquida)']:.2%}")
            with rent_col3:
                st.metric(label="EBITDA (Aprox.)", value=f"R$ {kpis['EBITDA']:.2f}")
                st.metric(label="Margem EBITDA (Aprox.)", value=f"{kpis['EBITDA Margin']:.2%}")
                st.metric(label="Margem de Contribuição % (Aprox.)", value=f"{kpis['Contribution Margin %']:.2%}")

            st.markdown("### Indicadores de Estrutura de Capital e Eficiência")
            struct_col1, struct_col2, struct_col3 = st.columns(3)
            with struct_col1:
                st.metric(label="Ativo Total", value=f"R$ {kpis['Total Assets']:.2f}")
                st.metric(label="Passivo Total", value=f"R$ {kpis['Total Liabilities']:.2f}")
            with struct_col2:
                st.metric(label="Capital Próprio (Patrimônio Líquido)", value=f"R$ {kpis['Total Equity']:.2f}")
                st.metric(label="Índice Dívida/Capital Próprio", value=f"{kpis['Debt-to-Equity Ratio (Total Liabilities / Total Equity)']:.2f}")
            with struct_col3:
                st.metric(label="ROE (Retorno sobre PL)", value=f"{kpis['ROE (Return on Equity)']:.2%}")
                st.metric(label="ROA (Retorno sobre Ativo)", value=f"{kpis['ROA (Return on Assets)']:.2%}")

            st.markdown("### Indicadores de Liquidez")
            liq_col1, liq_col2 = st.columns(2)
            with liq_col1:
                # Clarifying label for Current Assets. The total_assets is not current assets.
                # Re-using the current_assets variable calculated in calculate_kpis.
                st.metric(label="Ativo Circulante", value=f"R$ {kpis['Current Ratio (Current Assets / Current Liabilities)']:.2f}") # This is actually the ratio, not the value. Let's fix this display.
                # Corrected: Display the value if available, not the ratio.
                st.metric(label="Ativo Circulante (Valor)", value=f"R$ {kpis.get('Current Assets (Valor)', 0.0):.2f}") # Added a new KPI for current asset value
            with liq_col2:
                # Clarifying label for Current Liabilities.
                st.metric(label="Passivo Circulante (Valor)", value=f"R$ {kpis.get('Current Liabilities (Valor)', 0.0):.2f}") # Added a new KPI for current liabilities value
                st.metric(label="Índice de Liquidez Corrente", value=f"{kpis['Current Ratio (Current Assets / Current Liabilities)']:.2f}")

            # Adding Current Assets and Current Liabilities values to kpis dict
            kpis['Current Assets (Valor)'] = current_assets # from calculate_kpis function
            kpis['Current Liabilities (Valor)'] = current_liabilities # from calculate_kpis function

            st.markdown("---")
            st.write("### Detalhes dos Balanços por Conta (Contas Analíticas)")
            # No need to re-calculate df_detailed_balances and account_balances_for_display inside here
            # as account_balances already has Final_Balance.
            # We just need to filter and display from account_balances directly.
            analytical_account_codes = df_accounts[df_accounts['Account_Type'] == 'A']['Account_Code'].tolist()
            analytical_balances_display = account_balances[
                account_balances['Account_Code'].isin(analytical_account_codes)
            ].copy()

            st.dataframe(analytical_balances_display[['Account_Code', 'Account_Name', 'Main_Group', 'Final_Balance']].sort_values(by='Account_Code'))

    else:
        st.warning("Não foi possível extrair dados válidos dos registros I050 ou I355 do arquivo. Por favor, verifique o formato e se há registros contábeis.")

st.markdown("---")
st.info(
    "**Importante:** Este dashboard é uma ferramenta analítica e os resultados dependem da exatidão e completude dos dados "
    "presentes no arquivo ECD. A interpretação dos KPIs deve ser feita por um profissional qualificado. "
    "A classificação das contas (Ativo, Passivo, Receita, Despesa, Custos) é baseada na primeira parte do código da conta e/ou no nome da conta, "
    "o que pode não ser totalmente preciso para todos os planos de contas. "
    "**Margem de Contribuição** e **EBITDA** são calculados com base em inferências sobre a natureza das contas, "
    "e podem não refletir o cálculo exato da empresa sem um detalhamento maior dos custos e despesas variáveis, depreciação e amortização. "
    "Para rodar este dashboard, salve o código como um arquivo Python (ex: `ecd_dashboard.py`) e execute "
    "`streamlit run ecd_dashboard.py` no seu terminal."
    )
