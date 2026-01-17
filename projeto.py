import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Extrator DUIMP Master",
    layout="wide",
    page_icon="🚢",
    initial_sidebar_state="expanded"
)

# --- FUNÇÕES UTILITÁRIAS (ENGINEERING) ---

def clean_currency(value_str):
    """Converte '1.000,00' para float 1000.00. Retorna 0.0 se falhar."""
    if not value_str: return 0.0
    try:
        # Remove caracteres indesejados que não sejam números, ponto ou vírgula
        clean = re.sub(r'[^\d,.]', '', str(value_str))
        # Remove ponto de milhar e troca vírgula decimal
        return float(clean.replace('.', '').replace(',', '.'))
    except:
        return 0.0

def extract_field(pattern, text, type='text'):
    """Função genérica segura para extração via Regex."""
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        val = match.group(1).strip()
        if type == 'currency':
            return clean_currency(val)
        return val
    return 0.0 if type == 'currency' else ""

def process_pdf(uploaded_file):
    all_text = ""
    
    # 1. LEITURA COMPLETA (GLOBAL CONTEXT)
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            # Extração física mantendo fluxo visual
            page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if page_text:
                all_text += "\n" + page_text

    # 2. LIMPEZA DE CABEÇALHOS DE PÁGINA (RUÍDO)
    # Remove "--- PAGE X ---" e cabeçalhos repetidos que quebram tabelas
    all_text = re.sub(r'--- PAGE \d+ ---', '', all_text)
    
    # 3. EXTRAÇÃO DE DADOS MESTRE (CAPA)
    # Estes dados são únicos por arquivo
    master_data = {
        "Processo": extract_field(r'PROCESSO\s*#?\s*(\d+)', all_text),
        "Importador": extract_field(r'IMPORTADOR\s*[\r\n]+([^\r\n]+)', all_text),
        "CNPJ": extract_field(r'CNPJ\s*[\r\n]+([\d\./-]+)', all_text),
        "Número DUIMP": extract_field(r'Numero\s*[\r\n]+(\d{2}BR\d+)', all_text),
        "Data Registro": extract_field(r'Data Registro\s*[\r\n]+(\d{2}/\d{2}/\d{4})', all_text),
        "Via Transporte": extract_field(r'Via de Transporte\s*[\r\n]+([^\r\n]+)', all_text),
        "Peso Bruto Total": extract_field(r'Peso Bruto\s*[\r\n]+([\d\.,]+)', all_text, 'currency'),
        "Peso Líquido Total": extract_field(r'Liquido\s*[\r\n]+([\d\.,]+)', all_text, 'currency'),
        "Total VMLE": extract_field(r'VALOR DA MERCADORIA NO LOCAL DE EMBARQUE \(VMLE\)\s*[\r\n]+([\d\.,]+)', all_text, 'currency'),
    }

    # 4. LOOP DE ITENS (CORE LOGIC)
    # Dividimos o texto inteiro onde aparece "ITENS DA DUIMP - X"
    # O regex (?=...) é um lookahead para não consumir o texto do próximo item
    item_blocks = re.split(r'ITENS DA DUIMP\s*-\s*\d+', all_text)
    
    parsed_items = []
    
    # O primeiro bloco (índice 0) é o cabeçalho geral, pulamos.
    # Usamos enumerate start=1 para o número do item
    for idx, block in enumerate(item_blocks[1:], start=1):
        item = {}
        
        # --- IDENTIFICAÇÃO DO PRODUTO ---
        item['Item #'] = idx
        item['NCM'] = extract_field(r'NCM\s*[\r\n]+([\d\.]+)', block)
        item['Código Produto'] = extract_field(r'Codigo Produto\s*[\r\n]+(\d+)', block)
        
        # Descrição: Pega tudo entre "DENOMINACAO DO PRODUTO" e "CODIGO INTERNO"
        desc_raw = extract_field(r'DENOMINACAO DO PRODUTO(.*?)CÓDIGO INTERNO', block)
        item['Descrição'] = desc_raw.replace('\n', ' ').strip()[:200] # Limita a 200 chars
        
        item['Partnumber'] = extract_field(r'Código interno\s*[\r\n]+([^\r\n]+)', block)
        item['Fabricante'] = extract_field(r'FABRICANTE/PRODUTOR\s*[\r\n]+([^\r\n]+)', block)
        item['País Origem'] = extract_field(r'Pais Origem\s*[\r\n]+([^\r\n]+)', block)
        item['Exportador'] = extract_field(r'EXPORTADOR ESTRANGEIRO\s*[\r\n]+([^\r\n]+)', block)

        # --- DADOS QUANTITATIVOS ---
        # Busca "Qtde Unid. Comercial" seguido de número
        item['Qtd Comercial'] = extract_field(r'Qtde Unid\. Comercial\s*[\r\n]+([\d\.,]+)', block, 'currency')
        item['Unid Comercial'] = extract_field(r'Unidade Comercial\s*[\r\n]+([A-Z]+)', block)
        item['Peso Líquido'] = extract_field(r'Peso Líquido \(KG\)\s*[\r\n]+([\d\.,]+)', block, 'currency')
        
        # --- VALORES E LOGÍSTICA ---
        item['INCOTERM'] = extract_field(r'Condição de Venda\s*[\r\n]+([A-Z]+)', block)
        item['Vlr Unitário'] = extract_field(r'Valor Unit Cond Venda\s*[\r\n]+([\d\.,]+)', block, 'currency')
        item['VMLE (Item)'] = extract_field(r'VIr Cond Venda \(R\$\)\s*[\r\n]+([\d\.,]+)', block, 'currency')
        item['Frete Rateado'] = extract_field(r'Frete Internac\. \(R\$\)\s*[\r\n]+([\d\.,]+)', block, 'currency')
        item['Seguro Rateado'] = extract_field(r'Seguro Internac\. \(R\$\)\s*[\r\n]+([\d\.,]+)', block, 'currency')
        item['Vlr Aduaneiro'] = extract_field(r'Local Aduaneiro \(R\$\)\s*[\r\n]+([\d\.,]+)', block, 'currency')

        # --- TRIBUTOS (REGEX ESPECÍFICO PARA CADA IMPOSTO NO BLOCO) ---
        # A lógica aqui é encontrar o sub-bloco do imposto e pegar o valor "A Recolher" ou "Devido"
        
        # II (Imposto Importação)
        # Procura texto entre "II" e "IPI" (ou fim do bloco se for o último)
        ii_block_match = re.search(r'II(.*?)IPI', block, re.DOTALL)
        ii_text = ii_block_match.group(1) if ii_block_match else block
        item['II Base'] = extract_field(r'Base de Cálculo \(R\$\)\s*[\r\n]+([\d\.,]+)', ii_text, 'currency')
        item['II Alíquota'] = extract_field(r'% Alíquota\s*[\r\n]+([\d\.,]+)', ii_text, 'currency')
        item['II Valor'] = extract_field(r'Valor A Recolher \(R\$\)\s*[\r\n]+([\d\.,]+)', ii_text, 'currency')
        if item['II Valor'] == 0: # Tenta "Valor Devido" se "A Recolher" for zero
             item['II Valor'] = extract_field(r'Valor Devido \(R\$\)\s*[\r\n]+([\d\.,]+)', ii_text, 'currency')

        # IPI
        ipi_block_match = re.search(r'IPI(.*?)PIS', block, re.DOTALL)
        ipi_text = ipi_block_match.group(1) if ipi_block_match else ""
        item['IPI Base'] = extract_field(r'Base de Cálculo \(R\$\)\s*[\r\n]+([\d\.,]+)', ipi_text, 'currency')
        item['IPI Alíquota'] = extract_field(r'% Alíquota\s*[\r\n]+([\d\.,]+)', ipi_text, 'currency')
        item['IPI Valor'] = extract_field(r'Valor A Recolher \(R\$\)\s*[\r\n]+([\d\.,]+)', ipi_text, 'currency')

        # PIS
        pis_block_match = re.search(r'PIS(.*?)COFINS', block, re.DOTALL)
        pis_text = pis_block_match.group(1) if pis_block_match else ""
        item['PIS Valor'] = extract_field(r'Valor A Recolher \(R\$\)\s*[\r\n]+([\d\.,]+)', pis_text, 'currency')

        # COFINS
        cofins_block_match = re.search(r'COFINS(.*?)ICMS', block, re.DOTALL)
        cofins_text = cofins_block_match.group(1) if cofins_block_match else ""
        item['COFINS Valor'] = extract_field(r'Valor A Recolher \(R\$\)\s*[\r\n]+([\d\.,]+)', cofins_text, 'currency')

        # ICMS (Geralmente no final do bloco do item)
        item['ICMS Regime'] = extract_field(r'Regime de Tributacao\s*([^\r\n]+)', block)

        parsed_items.append(item)

    return master_data, pd.DataFrame(parsed_items)

# --- INTERFACE VISUAL (FRONTEND) ---

st.title("📊 Extrator DUIMP Pro (Análise Fiscal)")
st.markdown("Filtre, analise e exporte dados de Conferência Aduaneira.")

uploaded_file = st.file_uploader("Upload do PDF da DUIMP", type="pdf")

if uploaded_file:
    with st.spinner("Processando Inteligência Fiscal..."):
        try:
            # PROCESSAMENTO
            header, df = process_pdf(uploaded_file)
            
            # --- DASHBOARD KPI ---
            st.subheader("1. Visão Geral do Processo")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Importador", header.get("Importador")[:15]+"...")
            kpi2.metric("Processo", header.get("Processo"))
            kpi3.metric("DUIMP", header.get("Número DUIMP"))
            kpi4.metric("Itens", len(df))

            kpi5, kpi6, kpi7, kpi8 = st.columns(4)
            total_aduana = df['Vlr Aduaneiro'].sum()
            total_tributos = df['II Valor'].sum() + df['IPI Valor'].sum() + df['PIS Valor'].sum() + df['COFINS Valor'].sum()
            
            kpi5.metric("Valor Aduaneiro Total", f"R$ {total_aduana:,.2f}")
            kpi6.metric("Total Tributos Federais", f"R$ {total_tributos:,.2f}")
            kpi7.metric("Peso Líquido Total", f"{df['Peso Líquido'].sum():,.2f} kg")
            kpi8.metric("Via", header.get("Via Transporte"))

            # --- TABELA DETALHADA ---
            st.divider()
            st.subheader("2. Detalhamento por Item (Auditoria)")
            
            # Filtros laterais
            with st.sidebar:
                st.header("Filtros")
                selected_ncm = st.multiselect("Filtrar NCM", df['NCM'].unique())
                if selected_ncm:
                    df_view = df[df['NCM'].isin(selected_ncm)]
                else:
                    df_view = df

            st.dataframe(
                df_view,
                use_container_width=True,
                column_config={
                    "Item #": st.column_config.NumberColumn("Item", width="small"),
                    "Descrição": st.column_config.TextColumn("Descrição Produto", width="large"),
                    "Vlr Aduaneiro": st.column_config.NumberColumn("Vlr Aduaneiro", format="R$ %.2f"),
                    "II Valor": st.column_config.NumberColumn("II", format="R$ %.2f"),
                    "IPI Valor": st.column_config.NumberColumn("IPI", format="R$ %.2f"),
                    "PIS Valor": st.column_config.NumberColumn("PIS", format="R$ %.2f"),
                    "COFINS Valor": st.column_config.NumberColumn("COFINS", format="R$ %.2f"),
                }
            )

            # --- EXPORTAÇÃO ---
            st.divider()
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("3. Exportação")
                # Converter para CSV com ; e vírgula decimal (Excel PT-BR)
                csv = df.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')
                st.download_button(
                    label="💾 Baixar Relatório Completo (CSV)",
                    data=csv,
                    file_name=f"DUIMP_{header.get('Processo')}.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Erro Crítico: {str(e)}")
            st.warning("Dica: Verifique se o PDF não é uma imagem escaneada.")
