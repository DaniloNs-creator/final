import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="DUIMP Audit Pro", page_icon="⚖️", layout="wide")

# --- FUNÇÕES AUXILIARES ---
def clean_currency(value_str):
    """Converte '3.318,7200000' para float 3318.72"""
    if not value_str: return 0.0
    try:
        # Pega o primeiro token numérico
        clean = re.sub(r'[^\d,]', '', str(value_str).split()[0])
        clean = clean.replace(',', '.')
        return float(clean)
    except:
        return 0.0

def clean_text(text):
    """Remove quebras de linha e espaços extras"""
    if not text: return "N/A"
    return re.sub(r'\s+', ' ', text).strip()

def extract_within_block(block, start_pattern, end_pattern=None):
    """Extrai texto genérico entre dois marcadores"""
    try:
        if end_pattern:
            pattern = rf"{start_pattern}(.*?){end_pattern}"
        else:
            pattern = rf"{start_pattern}(.*)"
        
        match = re.search(pattern, block, re.DOTALL | re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
    except:
        pass
    return "N/A"

def extract_tax_details(block, tax_name):
    """
    Extrai o trio: Base de Cálculo, Alíquota (%) e Valor a Recolher (R$)
    dentro de um bloco de texto recortado.
    """
    details = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}
    
    if not block: return details

    # 1. Base de Cálculo
    # Busca "Base de Cálculo (R$)" seguido de números
    base_match = re.search(r"Base de Cálculo \(R\$\).*?([\d\.,]+)", block, re.DOTALL)
    if base_match:
        details["Base"] = clean_currency(base_match.group(1))

    # 2. Alíquota
    # Busca "% Alíquota" (ignora "Reduzida" ou "Específica" se vier antes)
    # O regex garante que pegamos a alíquota principal "Ad Valorem"
    rate_match = re.search(r"% Alíquota\s+([\d\.,]+)", block, re.DOTALL)
    if not rate_match:
         # Tenta padrão alternativo caso haja quebra de linha no meio
         rate_match = re.search(r"% Alíquota.*?([\d\.,]+)", block, re.DOTALL)
    
    if rate_match:
        details["Rate"] = clean_currency(rate_match.group(1))

    # 3. Valor a Recolher (ou Devido)
    val_match = re.search(r"Valor A Recolher \(R\$\).*?([\d\.,]+)", block, re.DOTALL)
    if not val_match:
        val_match = re.search(r"Valor Devido \(R\$\).*?([\d\.,]+)", block, re.DOTALL)
    
    if val_match:
        details["Value"] = clean_currency(val_match.group(1))

    return details

# --- ENGINE DE EXTRAÇÃO (Slicing + Detail Extraction) ---
def parse_duimp_complete(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # Quebra por itens
    raw_items = re.split(r"ITENS DA DUIMP", full_text)
    
    data = []
    
    if len(raw_items) > 1:
        for i, item_text in enumerate(raw_items[1:], start=1):
            try:
                # --- A. DADOS CADASTRAIS E LOGÍSTICOS ---
                pn_match = re.search(r"Código interno\s*([\d\.]+)", item_text)
                pn = pn_match.group(1) if pn_match else f"Item {i}"
                
                ncm_match = re.search(r"NCM\s*(\d{4}\.\d{2}\.\d{2})", item_text)
                ncm = ncm_match.group(1) if ncm_match else "N/A"

                desc = extract_within_block(item_text, "DESCRICAO DO PRODUTO", "Conhecido|Código interno")
                
                # Fabricante e Exportador (Busca texto entre chaves)
                fabricante = extract_within_block(item_text, "FABRICANTE/PRODUTOR", "Pais Origem|CARACTERIZAÇÃO")
                # Limpeza extra para fabricante (pega só a primeira linha relevante se tiver lixo)
                if "NAO" in fabricante: fabricante = fabricante.replace("NAO ", "") # Remove 'NAO' solto
                
                # Frete e Seguro Rateado
                frete_match = re.search(r"Frete Internac\. \(R\$\)\s*([\d\.,]+)", item_text)
                frete = clean_currency(frete_match.group(1)) if frete_match else 0.0
                
                seguro_match = re.search(r"Seguro Internac\. \(R\$\)\s*([\d\.,]+)", item_text)
                seguro = clean_currency(seguro_match.group(1)) if seguro_match else 0.0

                # Peso Líquido
                peso_match = re.search(r"Peso Líquido \(KG\)\s*([\d\.,]+)", item_text)
                peso = clean_currency(peso_match.group(1)) if peso_match else 0.0

                # --- B. FATIAMENTO DE IMPOSTOS (SLICING) ---
                text_upper = item_text.upper()
                
                # Marcos de corte (Headers)
                idx_ii = text_upper.find("\nII\n") 
                if idx_ii == -1: idx_ii = text_upper.find(" II ")
                
                idx_ipi = text_upper.find("\nIPI\n")
                if idx_ipi == -1: idx_ipi = text_upper.find(" IPI ")
                
                idx_pis = text_upper.find("PIS-IMPORTAÇÃO") 
                if idx_pis == -1: idx_pis = text_upper.find("\nPIS\n")
                
                idx_cofins = text_upper.find("\nCOFINS\n")
                if idx_cofins == -1: idx_cofins = text_upper.find(" COFINS ")
                
                idx_end = len(text_upper)

                # Extração Detalhada
                tax_info = {}
                
                # II
                if idx_ii != -1 and idx_ipi != -1:
                    tax_info["II"] = extract_tax_details(item_text[idx_ii:idx_ipi], "II")
                else: tax_info["II"] = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}

                # IPI
                if idx_ipi != -1 and idx_pis != -1:
                    tax_info["IPI"] = extract_tax_details(item_text[idx_ipi:idx_pis], "IPI")
                else: tax_info["IPI"] = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}

                # PIS
                if idx_pis != -1 and idx_cofins != -1:
                    tax_info["PIS"] = extract_tax_details(item_text[idx_pis:idx_cofins], "PIS")
                else: tax_info["PIS"] = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}

                # COFINS
                if idx_cofins != -1:
                    tax_info["COFINS"] = extract_tax_details(item_text[idx_cofins:idx_end], "COFINS")
                else: tax_info["COFINS"] = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}

                # --- C. MONTAGEM DA LINHA ---
                row = {
                    "Item": i,
                    "Part Number": pn,
                    "NCM": ncm,
                    "Descrição": desc[:50] + "...",
                    "Fabricante": fabricante[:30] + "...",
                    "Peso Liq (Kg)": peso,
                    "Frete (R$)": frete,
                    
                    # II
                    "II Base (R$)": tax_info["II"]["Base"],
                    "II Aliq (%)": tax_info["II"]["Rate"],
                    "II Vlr (R$)": tax_info["II"]["Value"],
                    
                    # IPI
                    "IPI Base (R$)": tax_info["IPI"]["Base"],
                    "IPI Aliq (%)": tax_info["IPI"]["Rate"],
                    "IPI Vlr (R$)": tax_info["IPI"]["Value"],
                    
                    # PIS
                    "PIS Base (R$)": tax_info["PIS"]["Base"],
                    "PIS Aliq (%)": tax_info["PIS"]["Rate"],
                    "PIS Vlr (R$)": tax_info["PIS"]["Value"],
                    
                    # COFINS
                    "COFINS Base (R$)": tax_info["COFINS"]["Base"],
                    "COFINS Aliq (%)": tax_info["COFINS"]["Rate"],
                    "COFINS Vlr (R$)": tax_info["COFINS"]["Value"],
                    
                    "Total Tributos": tax_info["II"]["Value"] + tax_info["IPI"]["Value"] + tax_info["PIS"]["Value"] + tax_info["COFINS"]["Value"]
                }
                data.append(row)

            except Exception as e:
                # Log de erro silencioso para não quebrar a UI
                print(f"Erro item {i}: {e}")
                continue

    return pd.DataFrame(data)

# --- INTERFACE VISUAL ---
st.title("📑 Auditoria DUIMP - Detalhamento Fiscal")
st.markdown("Visualize Bases de Cálculo, Alíquotas e Rateios Logísticos extraídos diretamente do PDF.")

uploaded_file = st.file_uploader("Carregar PDF da DUIMP", type="pdf")

if uploaded_file:
    with st.spinner("Processando Bases e Alíquotas..."):
        df = parse_duimp_complete(uploaded_file)
        
        if not df.empty:
            # 1. VISÃO MACRO
            st.success(f"Extração Concluída: {len(df)} itens identificados.")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Frete", f"R$ {df['Frete (R$)'].sum():,.2f}")
            c2.metric("Total II", f"R$ {df['II Vlr (R$)'].sum():,.2f}")
            c3.metric("Total PIS/COFINS", f"R$ {(df['PIS Vlr (R$)'].sum() + df['COFINS Vlr (R$)'].sum()):,.2f}")
            c4.metric("Carga Tributária Total", f"R$ {df['Total Tributos'].sum():,.2f}")
            
            st.divider()

            # 2. TABELA DETALHADA (TAB TABS)
            tab_fiscal, tab_logistica = st.tabs(["💰 Dados Fiscais (Bases & Alíquotas)", "📦 Dados Logísticos & Produto"])
            
            with tab_fiscal:
                st.markdown("### Memória de Cálculo dos Tributos")
                # Seleciona colunas fiscais para exibição limpa
                cols_fiscal = [
                    "Item", "Part Number", 
                    "II Base (R$)", "II Aliq (%)", "II Vlr (R$)",
                    "IPI Base (R$)", "IPI Aliq (%)", "IPI Vlr (R$)",
                    "PIS Base (R$)", "PIS Aliq (%)", "PIS Vlr (R$)",
                    "COFINS Base (R$)", "COFINS Aliq (%)", "COFINS Vlr (R$)"
                ]
                
                st.dataframe(
                    df[cols_fiscal].style.format({
                        "II Base (R$)": "{:,.2f}", "II Aliq (%)": "{:.2f}%", "II Vlr (R$)": "{:,.2f}",
                        "IPI Base (R$)": "{:,.2f}", "IPI Aliq (%)": "{:.2f}%", "IPI Vlr (R$)": "{:,.2f}",
                        "PIS Base (R$)": "{:,.2f}", "PIS Aliq (%)": "{:.2f}%", "PIS Vlr (R$)": "{:,.2f}",
                        "COFINS Base (R$)": "{:,.2f}", "COFINS Aliq (%)": "{:.2f}%", "COFINS Vlr (R$)": "{:,.2f}",
                    }),
                    use_container_width=True,
                    height=500
                )
            
            with tab_logistica:
                st.markdown("### Detalhes do Produto")
                cols_log = ["Item", "Part Number", "NCM", "Descrição", "Fabricante", "Peso Liq (Kg)", "Frete (R$)"]
                st.dataframe(df[cols_log], use_container_width=True)

            # 3. DOWNLOAD
            csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button("📥 Baixar Relatório Completo (Excel/CSV)", csv, "duimp_full.csv", "text/csv")

        else:
            st.error("Nenhum dado pôde ser extraído. Verifique o PDF.")
