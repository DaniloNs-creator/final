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

    def adjust_final_balance(row):
        # Assets, Expenses, Costs: Debit balance is positive
        if row['Main_Group'] in ['Ativo', 'Despesa', 'Custos']:
            return row['Total_Value']
        # Liabilities, Equity, Revenue: Credit balance is positive (so Debit value means negative)
        elif row['Main_Group'] in ['Passivo e PL', 'Receita']:
            return -row['Total_Value']
        return row['Total_Value'] # Default for other groups

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
    # Need to identify Net Sales Revenue and Cost of Goods Sold (CPV/CMV)
    # Assuming 'Receita' is mostly Net Sales Revenue.
    # Assuming 'Custos' (e.g., accounts starting with 5) are CPV/CMV.
    gross_profit = total_revenue - total_costs
    kpis['Gross Profit (Lucro Bruto)'] = gross_profit

    # 2. Lucro Antes do IR e CSLL (LAIR/LAL) - Lucro Operacional + Receitas/Despesas Não Operacionais
    # For simplicity, we'll take Net Income before taxes directly if possible.
    # Otherwise, Operating Income (Lucro Operacional)
    # We'll calculate a simplified Operating Income first
    operating_income = gross_profit - total_expenses
    kpis['Operating Income (Lucro Operacional)'] = operating_income

    # 3. Lucro Líquido
    # This assumes `net_income` calculated earlier is after all expenses including financial and taxes
    # If taxes are in a specific account (e.g., 4.x.y.z for IR/CSLL), we could refine.
    # For now, it's total_revenue - total_costs - total_expenses
    net_income = total_revenue - total_costs - total_expenses
    kpis['Net Income (Lucro Líquido)'] = net_income

    # 4. Margem de Contribuição
    # This is tricky without explicit variable/fixed cost separation.
    # We'll need to make assumptions. If 'Custos' (group 5) are mainly variable costs and some 'Despesas' (group 4)
    # are variable (e.g., comissões, fretes sobre vendas).
    # For simplicity, let's assume total_costs + a portion of total_expenses are variable.
    # This is a strong assumption and needs actual COA mapping for accuracy.
    # If we don't have clear variable cost identification, we'll skip or use a placeholder
    # For now, we'll try to infer based on typical COA structures for variable costs.
    # Example: If your COA classifies some 4.x accounts as 'Despesas Variáveis'
    # For the provided file, there's no clear 'variable' distinction.
    # So, for contribution margin, we'll assume 'Custos' are variable costs.
    # And we need 'Receita Líquida'. Total Revenue from our parsing is likely Gross Revenue.
    # Let's assume there are no significant sales deductions/returns to simplify to Total Revenue as Net Sales.
    variable_costs_and_expenses = total_costs # Simplified: assuming all costs are variable, ignoring variable expenses
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
    # This is very hard to calculate accurately from just I050/I355 without specific accounts for Depr/Amort and Interest.
    # A common approximation: EBITDA = Lucro Operacional + Depreciação + Amortização.
    # Since we can't identify Depreciação/Amortização directly from the COA snippet, we'll make a strong assumption.
    # If there are no clear D&A accounts, we might approximate using only operating income, or skip.
    # Let's assume for now we cannot precisely calculate D&A from the given structure.
    # We will provide an approximation based on operating income. If specific D&A accounts exist (e.g., under Despesas),
    # they would need to be identified.
    # For now, let's mark it as 'Not Fully Calculable' or assume zero D&A if not explicitly found.
    # If 'Depreciação' or 'Amortização' are account names under expenses, we could try to sum them.
    # This requires looking for keywords in `df_accounts['Account_Name']`.
    depreciation_amortization = account_balances[
        account_balances['Account_Name'].str.contains('depreciação|amortização', case=False, na=False)
    ]['Final_Balance'].sum()

    # EBITDA = Lucro Operacional + Depreciação + Amortização
    ebitda = operating_income + depreciation_amortization
    kpis['EBITDA'] = ebitda
    kpis['EBITDA Margin'] = (ebitda / total_revenue) if total_revenue != 0 else 0


    # --- Existing KPIs ---
    kpis['Total Assets'] = total_assets
    kpis['Total Liabilities'] = total_liabilities
    kpis['Total Equity'] = total_equity
    kpis['Total Revenue'] = total_revenue
    kpis['Total Expenses (Operational & Admin)'] = total_expenses # Clarify which expenses
    kpis['Total Costs (CPV/CMV)'] = total_costs # Clarify which costs

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
                st.metric(label="Ativo Circulante", value=f"R$ {kpis['Total Assets']:.2f}") # Assuming Total Assets for simplicity, refine if needed
            with liq_col2:
                st.metric(label="Passivo Circulante", value=f"R$ {kpis['Total Liabilities']:.2f}") # Assuming Total Liabilities for simplicity, refine if needed
                st.metric(label="Índice de Liquidez Corrente", value=f"{kpis['Current Ratio (Current Assets / Current Liabilities)']:.2f}")


            st.markdown("---")
            st.write("### Detalhes dos Balanços por Conta (Contas Analíticas)")
            df_detailed_balances = pd.merge(df_movements, df_accounts, on='Account_Code', how='left')

            df_detailed_balances['Signed_Value'] = df_detailed_balances.apply(
                lambda row: row['Value'] if row['Nature'] == 'D' else -row['Value'], axis=1
            )

            account_balances_for_display = df_detailed_balances.groupby('Account_Code').agg(
                Account_Name=('Account_Name', 'first'),
                Main_Group=('Main_Group', 'first'),
                Balance=('Signed_Value', 'sum')
            ).reset_index()

            account_balances_for_display['Final_Balance_Adjusted'] = account_balances_for_display.apply(adjust_final_balance, axis=1)

            analytical_account_codes = df_accounts[df_accounts['Account_Type'] == 'A']['Account_Code'].tolist()
            analytical_balances_display = account_balances_for_display[
                account_balances_for_display['Account_Code'].isin(analytical_account_codes)
            ].copy()

            st.dataframe(analytical_balances_display[['Account_Code', 'Account_Name', 'Main_Group', 'Final_Balance_Adjusted']].sort_values(by='Account_Code'))

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
