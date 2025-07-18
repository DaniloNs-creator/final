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
        if len(parts) > 1:
            record_type = parts[1]

            if record_type == 'I050':
                # I050: Account Code, Account Type (S/A), Account Level, Account Name
                # Example: |I050|01011900|01|S|1|100000000000000||Ativo|
                try:
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
                    elif account_code.startswith('5'):
                        main_group = 'Custos' # Assuming 5 is for costs if present

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
                # I355: Account Code, Value, Nature (D/C)
                # Example: |I355|4.1.02.02.0001||474,94|D|
                try:
                    account_code = parts[2] # Account code in I355 is in the 3rd field
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

    # Merge movements with account names
    df_merged = pd.merge(df_movements, df_accounts, on='Account_Code', how='left')

    # Calculate net balance for each account
    df_merged['Signed_Value'] = df_merged.apply(
        lambda row: row['Value'] if row['Nature'] == 'D' else -row['Value'], axis=1
    )

    account_balances = df_merged.groupby('Account_Code').agg(
        Total_Value=('Signed_Value', 'sum'),
        Account_Name=('Account_Name', 'first'),
        Main_Group=('Main_Group', 'first')
    ).reset_index()

    # Apply normal balance conventions for final balance
    # Assets, Expenses: Debit is positive
    # Liabilities, Equity, Revenue: Credit is positive (Debit is negative)
    def adjust_balance(row):
        if row['Main_Group'] in ['Ativo', 'Despesa']:
            return row['Total_Value']
        elif row['Main_Group'] in ['Passivo e PL', 'Receita', 'Custos']: # Assuming costs are credit in source, then flip
            return -row['Total_Value']
        return row['Total_Value'] # Default if group is not classified

    account_balances['Final_Balance'] = account_balances.apply(adjust_balance, axis=1)

    # Calculate main financial statements aggregates
    total_assets = account_balances[account_balances['Main_Group'] == 'Ativo']['Final_Balance'].sum()
    total_liabilities_equity = account_balances[account_balances['Main_Group'] == 'Passivo e PL']['Final_Balance'].sum()
    total_revenue = account_balances[account_balances['Main_Group'] == 'Receita']['Final_Balance'].sum()
    total_expenses = account_balances[account_balances['Main_Group'] == 'Despesa']['Final_Balance'].sum()
    total_costs = account_balances[account_balances['Main_Group'] == 'Custos']['Final_Balance'].sum()

    # Special handling for Equity: If 'Patrimônio Líquido' is a parent account in I050 and the I355 movements for its children are included in 'Passivo e PL' group
    # We need to ensure we isolate Equity from Liabilities for ratios.
    # From the file: Patrimônio Líquido is under main group '2' (Passivo).
    # Assuming '2.3' is Patrimônio Líquido's top-level code.
    equity_accounts = df_accounts[df_accounts['Account_Code'].str.startswith('2.3') & (df_accounts['Account_Type'] == 'S')]
    if not equity_accounts.empty:
        equity_parent_codes = equity_accounts['Account_Code'].tolist()
        # Find all analytical accounts that fall under these equity parent codes
        analytical_equity_accounts = df_accounts[
            (df_accounts['Account_Type'] == 'A') &
            df_accounts['Account_Code'].apply(lambda x: any(x.startswith(code) for code in equity_parent_codes))
        ]['Account_Code'].tolist()

        total_equity = account_balances[account_balances['Account_Code'].isin(analytical_equity_accounts)]['Final_Balance'].sum()
        total_liabilities = total_liabilities_equity - total_equity
    else:
        # Fallback if specific equity breakdown isn't clear, approximate total liabilities and equity together.
        total_equity = account_balances[account_balances['Account_Name'].str.contains('Patrimônio Líquido', case=False, na=False)]['Final_Balance'].sum()
        # Assuming other accounts under 'Passivo e PL' are Liabilities
        total_liabilities = total_liabilities_equity - total_equity if total_liabilities_equity > total_equity else 0


    # Net Income: Revenue - Costs - Expenses
    net_income = total_revenue - total_costs - total_expenses

    kpis['Total Assets'] = total_assets
    kpis['Total Liabilities'] = total_liabilities
    kpis['Total Equity'] = total_equity
    kpis['Total Revenue'] = total_revenue
    kpis['Total Expenses'] = total_expenses # Including costs here for simplicity, refine if needed
    kpis['Net Income (Profit/Loss)'] = net_income

    # Common Financial Ratios
    # Current Assets (assuming all 'Ativo Circulante' - 1.1)
    current_assets = account_balances[account_balances['Account_Code'].str.startswith('1.1')]['Final_Balance'].sum()
    # Current Liabilities (assuming all 'Passivo Circulante' - 2.1)
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
            df_merged['Signed_Value'] = df_merged.apply(
                lambda row: row['Value'] if row['Nature'] == 'D' else -row['Value'], axis=1
            )

            account_balances_detail = df_merged.groupby('Account_Code').agg(
                Account_Name=('Account_Name', 'first'),
                Main_Group=('Main_Group', 'first'),
                Balance=('Signed_Value', 'sum')
            ).reset_index()

            account_balances_detail['Final_Balance_Adjusted'] = account_balances_detail.apply(adjust_balance, axis=1)

            # Display only analytical accounts for detailed view
            analytical_balances = account_balances_detail[
                (account_balances_detail['Account_Code'].isin(df_accounts[df_accounts['Account_Type'] == 'A']['Account_Code']))
            ].copy()
            st.dataframe(analytical_balances[['Account_Code', 'Account_Name', 'Main_Group', 'Final_Balance_Adjusted']].sort_values(by='Account_Code'))

    else:
        st.warning("Não foi possível extrair dados válidos dos registros I050 ou I355 do arquivo. Por favor, verifique o formato.")

st.markdown("---")
st.info(
    "Este dashboard é uma ferramenta analítica e os resultados dependem da exatidão e completude dos dados "
    "presentes no arquivo ECD. A interpretação dos KPIs deve ser feita por um profissional qualificado. "
    "A estrutura da ECD pode variar e este parser foi desenvolvido com base no arquivo de exemplo fornecido. "
    [span_0](start_span)"[Fonte da estrutura ECD: ECD_18019528000178_01012025_31012025_162824.txt[span_0](end_span)]"
        )
