import streamlit as st
import pandas as pd
import io

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
        if len(parts) > 1: # Ensure the line is not empty after splitting
            record_type = parts[1]

            if record_type == 'I050':
                # I050: 0|I050|1|2|3|4|5|6|7|8|9|10
                # Example: |I050|01011900|01|S|1|100000000000000||Ativo|
                try:
                    # Adjusting indices based on the provided example and split behavior
                    # The first element after split will be an empty string if line starts with '|'
                    # So, if line is |REC_TYPE|FIELD1|FIELD2|, then parts will be ['', 'REC_TYPE', 'FIELD1', 'FIELD2']
                    # This means REC_TYPE is parts[1], FIELD1 is parts[2], etc.
                    # Looking at the example: |I050|01011900|01|S|1|100000000000000||Ativo|
                    # parts[1] = 'I050'
                    # parts[4] = 'S' (Account Type)
                    # parts[5] = '1' (Account Level)
                    # parts[6] = '100000000000000' (Account Code) - This seems to be the COD_NAT
                    # The actual account code appears to be parts[7] (empty string in example, or actual code in another I050 line)
                    # Let's re-evaluate based on a common ECD structure
                    # Standard I050: |REG|DT_ALT|COD_NAT|IND_CTA|NIVEL|COD_CTA|COD_CTA_SUP|CTA_INI|DT_ALT_CTA_INI|DSC_CTA|
                    # So for |I050|01011900|01|S|1|100000000000000||Ativo|
                    # parts[1] is 'I050'
                    # parts[2] is DT_ALT '01011900'
                    # parts[3] is COD_NAT '01'
                    # parts[4] is IND_CTA 'S'
                    # parts[5] is NIVEL '1'
                    # parts[6] is COD_CTA '100000000000000' (This is the parent account code from the snippet. Let's use it as 'Account_Code')
                    # parts[7] is COD_CTA_SUP (empty in this case, but can be a parent account code for lower levels)
                    # parts[8] is DSC_CTA 'Ativo' (Account Name)

                    # Based on the snippet `|I050|01011900|01|S|1|100000000000000||Ativo|`
                    # And `|I050|01011900|01|S|2|1.1|100000000000000|ATIVO CIRCULANTE|`
                    # It seems `parts[6]` is the account code (e.g., '1' or '1.1')
                    # and `parts[8]` is the description (e.g., 'Ativo', 'ATIVO CIRCULANTE')
                    account_code = parts[6]
                    account_type = parts[4] # 'S' for Synthetical, 'A' for Analytical
                    account_level = int(parts[5])
                    account_name = parts[8]

                    # Determine main account group based on the first digit of the code
                    main_group = ''
                    if account_code.startswith('1'):
                        main_group = 'Ativo'
                    elif account_code.startswith('2'):
                        main_group = 'Passivo e PL'
                    elif account_code.startswith('3'):
                        main_group = 'Receita'
                    elif account_code.startswith('4'):
                        main_group = 'Despesa'
                    elif account_code.startswith('5'): # Example: Custos de Produtos Vendidos
                        main_group = 'Custos'
                    elif account_code.startswith('8'): # Example: Contas de Resultado - if applicable
                        main_group = 'Contas de Resultado'

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
                # I355: |REG|COD_CTA|COD_CCUSTO|VL_SLD_INI|IND_DC_INI|VL_DEB|VL_CRED|
                # Example: |I355|4.1.02.02.0001||474,94|D|
                try:
                    # parts[1] = 'I355'
                    # parts[2] = COD_CTA '4.1.02.02.0001' (Account Code)
                    # parts[3] = COD_CCUSTO (empty in example)
                    # parts[4] = VL_SLD_INI '474,94' (Value)
                    # parts[5] = IND_DC_INI 'D' (Nature)
                    account_code = parts[2]
                    value_str = parts[4].replace('.', '').replace(',', '.') # Handle Brazilian decimal format
                    value = float(value_str)
                    nature = parts[5] # 'D' for Debit, 'C' for Credit
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

    # Merge movements with account names and main groups
    df_merged = pd.merge(df_movements, df_accounts, on='Account_Code', how='left')

    # Calculate net balance for each account
    # Debit increases Asset/Expense, decreases Liability/Equity/Revenue
    # Credit increases Liability/Equity/Revenue, decreases Asset/Expense
    df_merged['Signed_Value'] = df_merged.apply(
        lambda row: row['Value'] if row['Nature'] == 'D' else -row['Value'], axis=1
    )

    account_balances = df_merged.groupby('Account_Code').agg(
        Total_Value=('Signed_Value', 'sum'),
        Account_Name=('Account_Name', 'first'),
        Main_Group=('Main_Group', 'first')
    ).reset_index()

    # Adjusting balance based on the normal balance of the account type
    # For Assets and Expenses, a debit balance is positive.
    # For Liabilities, Equity, and Revenue, a credit balance is positive (meaning a debit balance is negative).
    def adjust_final_balance(row):
        if row['Main_Group'] == 'Ativo' or row['Main_Group'] == 'Despesa' or row['Main_Group'] == 'Custos':
            # For these groups, Debit is positive. If Total_Value is result of (Debits - Credits), it's correct.
            return row['Total_Value']
        elif row['Main_Group'] == 'Passivo e PL' or row['Main_Group'] == 'Receita':
            # For these groups, Credit is positive. If Total_Value is result of (Debits - Credits), we need to invert.
            return -row['Total_Value']
        return row['Total_Value'] # Default for other groups

    account_balances['Final_Balance'] = account_balances.apply(adjust_final_balance, axis=1)

    # Calculate main financial statements aggregates
    total_assets = account_balances[account_balances['Main_Group'] == 'Ativo']['Final_Balance'].sum()

    # Identify Equity accounts more robustly if possible, or assume based on common structures like 'Patrimônio Líquido'
    # From the example, 'Patrimônio Líquido' is under '2' (Passivo e PL).
    # Assuming '2.3' is a common start for Equity accounts if detailed
    equity_filter = df_accounts['Account_Code'].apply(lambda x: x.startswith('2.3')) | df_accounts['Account_Name'].str.contains('patrimônio líquido', case=False, na=False)
    equity_codes = df_accounts[equity_filter]['Account_Code'].tolist()

    total_equity = account_balances[account_balances['Account_Code'].isin(equity_codes)]['Final_Balance'].sum()
    
    # Total Liabilities can be calculated by subtracting Equity from 'Passivo e PL' group
    total_liabilities_and_pl = account_balances[account_balances['Main_Group'] == 'Passivo e PL']['Final_Balance'].sum()
    total_liabilities = total_liabilities_and_pl - total_equity # This assumes PL is a subset of Passivo e PL

    total_revenue = account_balances[account_balances['Main_Group'] == 'Receita']['Final_Balance'].sum()
    total_expenses = account_balances[account_balances['Main_Group'] == 'Despesa']['Final_Balance'].sum()
    total_costs = account_balances[account_balances['Main_Group'] == 'Custos']['Final_Balance'].sum()

    # Net Income: Revenue - Costs - Expenses
    net_income = total_revenue - total_costs - total_expenses

    kpis['Total Assets'] = total_assets
    kpis['Total Liabilities'] = total_liabilities
    kpis['Total Equity'] = total_equity
    kpis['Total Revenue'] = total_revenue
    kpis['Total Expenses'] = total_expenses
    kpis['Net Income (Profit/Loss)'] = net_income

    # Common Financial Ratios
    current_assets = account_balances[account_balances['Account_Code'].str.startswith('1.1')]['Final_Balance'].sum()
    current_liabilities = account_balances[account_balances['Account_Code'].str.startswith('2.1')]['Final_Balance'].sum()

    kpis['Current Ratio (Current Assets / Current Liabilities)'] = current_assets / current_liabilities if current_liabilities != 0 else float('inf')
    kpis['Debt-to-Equity Ratio (Total Liabilities / Total Equity)'] = total_liabilities / total_equity if total_equity != 0 else float('inf')
    kpis['Net Profit Margin (Net Income / Total Revenue)'] = (net_income / total_revenue) if total_revenue != 0 else 0

    return kpis

# Streamlit UI
st.set_page_config(layout="wide")
st.title("📊 Dashboard de KPIs Contábeis e Financeiros (ECD)")

st.write("Faça o upload do seu arquivo TXT da ECD para analisar os principais indicadores.")

uploaded_file = st.file_uploader("Escolha um arquivo TXT da ECD", type="txt")

if uploaded_file is not None:
    # Read the file content
    file_content = uploaded_file.read().decode("utf-8")

    st.subheader("Conteúdo do Arquivo ECD (Amostra)")
    st.code(file_content[:1000] + "...", language="text") # Show first 1000 characters

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

        st.subheader("Principais KPIs Contábeis e Financeiros")
        if "Error" in kpis:
            st.error(kpis["Error"])
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Ativo Total", value=f"R$ {kpis['Total Assets']:.2f}")
                st.metric(label="Receita Total", value=f"R$ {kpis['Total Revenue']:.2f}")
                st.metric(label="Margem de Lucro Líquida", value=f"{kpis['Net Profit Margin (Net Income / Total Revenue)']:.2%}")
            with col2:
                st.metric(label="Passivo Total", value=f"R$ {kpis['Total Liabilities']:.2f}")
                st.metric(label="Despesa Total", value=f"R$ {kpis['Total Expenses']:.2f}")
                st.metric(label="Capital Próprio (Patrimônio Líquido)", value=f"R$ {kpis['Total Equity']:.2f}")
            with col3:
                st.metric(label="Lucro/Prejuízo Líquido", value=f"R$ {kpis['Net Income (Profit/Loss)']:.2f}")
                st.metric(label="Índice de Liquidez Corrente", value=f"{kpis['Current Ratio (Current Assets / Current Liabilities)']:.2f}")
                st.metric(label="Índice Dívida/Capital Próprio", value=f"{kpis['Debt-to-Equity Ratio (Total Liabilities / Total Equity)']:.2f}")

            st.markdown("---")
            st.write("### Detalhes dos Balanços por Conta")
            # Re-calculate account balances to display them in a table
            # Re-merge to ensure all original account info is present for filtering/display
            df_detailed_balances = pd.merge(df_movements, df_accounts, on='Account_Code', how='left')

            df_detailed_balances['Signed_Value'] = df_detailed_balances.apply(
                lambda row: row['Value'] if row['Nature'] == 'D' else -row['Value'], axis=1
            )

            # Group by account to get final balance for each account
            account_balances_for_display = df_detailed_balances.groupby('Account_Code').agg(
                Account_Name=('Account_Name', 'first'),
                Main_Group=('Main_Group', 'first'),
                Balance=('Signed_Value', 'sum')
            ).reset_index()

            # Apply the normal balance adjustment for display
            account_balances_for_display['Final_Balance_Adjusted'] = account_balances_for_display.apply(adjust_final_balance, axis=1)

            # Filter to show only analytical accounts for detailed view, or all if desired
            analytical_account_codes = df_accounts[df_accounts['Account_Type'] == 'A']['Account_Code'].tolist()
            analytical_balances_display = account_balances_for_display[
                account_balances_for_display['Account_Code'].isin(analytical_account_codes)
            ].copy()

            st.dataframe(analytical_balances_display[['Account_Code', 'Account_Name', 'Main_Group', 'Final_Balance_Adjusted']].sort_values(by='Account_Code'))

    else:
        st.warning("Não foi possível extrair dados válidos dos registros I050 ou I355 do arquivo. Por favor, verifique o formato.")

st.markdown("---")
st.info(
    "Este dashboard é uma ferramenta analítica e os resultados dependem da exatidão e completude dos dados "
    "presentes no arquivo ECD. A interpretação dos KPIs deve ser feita por um profissional qualificado. "
    "A estrutura da ECD pode variar e este parser foi desenvolvido com base no arquivo de exemplo fornecido. "
    "Para rodar este dashboard, salve o código como um arquivo Python (ex: `ecd_dashboard.py`) e execute "
    "`streamlit run ecd_dashboard.py` no seu terminal."
)
