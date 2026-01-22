import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px

st.set_page_config(page_title="DUIMP Auditor - IPI Fix", page_icon="🔧", layout="wide")

# --- UTILITÁRIOS ---
def clean_currency(value_str):
    if not value_str: return 0.0
    try:
        # Pega o primeiro token numérico. Ex: "2.100,00"
        clean = re.sub(r'[^\d,]', '', str(value_str).split()[0])
        clean = clean.replace(',', '.')
        return float(clean)
    except:
        return 0.0

def clean_block_text(text):
    """
    Remove ruídos de quebra de página para 'costurar' o texto.
    Remove linhas como '--- PAGE 12 ---', datas isoladas, etc.
    """
    # Remove linhas de paginação comuns em logs de PDF
    text = re.sub(r'--- PAGE \d+ ---', '', text) 
    text = re.sub(r'ITENS DA DUIMP-\d+', '', text)
    # Remove excesso de quebras de linha para juntar o texto
    text = re.sub(r'\n+', '\n', text)
    return text

def extract_tax_details(block, tax_name):
    """
    Extrai Base, Alíquota e Valor com regex tolerante a quebras.
    """
    details = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}
    if not block: return details
    
    # Limpa o bloco para aproximar rótulos dos valores
    clean_block = clean_block_text(block)

    # 1. BASE DE CÁLCULO
    # Regex busca: "Base de Cálculo" ... (ignora texto intermediário) ... (Número)
    # O [^\n]* garante que peguemos o número mesmo que haja texto na mesma linha
    base_match = re.search(r"Base de Cálculo \(R\$\).*?([\d\.,]+)", clean_block, re.DOTALL)
    if base_match:
        details["Base"] = clean_currency(base_match.group(1))

    # 2. ALÍQUOTA (%)
    # Prioridade 1: "Alíquota" seguido de número (Ex: % Alíquota 9,6500)
    # Prioridade 2: "AD VALOREM" seguido de número (comum no IPI/II)
    rate_match = re.search(r"% Alíquota\s*([\d\.,]+)", clean_block, re.DOTALL)
    if not rate_match:
         # Tenta buscar logo após "AD VALOREM" se houver quebra de linha
         rate_match = re.search(r"AD VALOREM.*?([\d\.,]+)", clean_block, re.DOTALL)
    
    if rate_match:
        details["Rate"] = clean_currency(rate_match.group(1))

    # 3. VALOR A RECOLHER
    # Tenta "Valor A Recolher" primeiro, depois "Valor Devido" (comum no IPI)
    val_match = re.search(r"Valor A Recolher \(R\$\).*?([\d\.,]+)", clean_block, re.DOTALL)
    if not val_match:
        val_match = re.search(r"Valor Devido \(R\$\).*?([\d\.,]+)", clean_block, re.DOTALL)
    
    if val_match:
        details["Value"] = clean_currency(val_match.group(1))

    return details

# --- ENGINE CORE ---
def parse_duimp_fixed(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # Quebra por itens
    # A regex agora aceita espaços opcionais no separador
    raw_items = re.split(r"ITENS DA DUIMP\s*-\s*\d+", full_text)
    
    data = []
    
    if len(raw_items) > 1:
        for i, item_text in enumerate(raw_items[1:], start=1):
            try:
                # --- Identificadores ---
                pn = "N/A"
                pn_match = re.search(r"Código interno\s*([\d\.]+)", item_text)
                if pn_match: pn = pn_match.group(1)
                
                # --- Slicing dos Impostos (Com Logica de Fim de Arquivo) ---
                text_upper = item_text.upper()
                
                # Encontra posições
                # Adicionei variações com e sem \n para robustez
                idx_ii = text_upper.find("II\n") if text_upper.find("II\n") != -1 else text_upper.find(" II ")
                idx_ipi = text_upper.find("IPI\n") if text_upper.find("IPI\n") != -1 else text_upper.find(" IPI ")
                idx_pis = text_upper.find("PIS-") # PIS geralmente vem como PIS-IMPORTACAO
                if idx_pis == -1: idx_pis = text_upper.find("PIS\n")
                idx_cofins = text_upper.find("COFINS\n") if text_upper.find("COFINS\n") != -1 else text_upper.find(" COFINS ")
                
                # Define limites seguros (se não achar, usa o fim do texto)
                len_text = len(item_text)
                limit_ii = idx_ipi if idx_ipi != -1 else (idx_pis if idx_pis != -1 else len_text)
                limit_ipi = idx_pis if idx_pis != -1 else (idx_cofins if idx_cofins != -1 else len_text)
                limit_pis = idx_cofins if idx_cofins != -1 else len_text
                
                # Extração
                tax_info = {}
                
                # II
                if idx_ii != -1:
                    tax_info["II"] = extract_tax_details(item_text[idx_ii:limit_ii], "II")
                else: tax_info["II"] = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}
                
                # IPI (O foco do problema)
                if idx_ipi != -1:
                    # Pega um bloco generoso para garantir que pule a quebra de página
                    block_ipi = item_text[idx_ipi:limit_ipi]
                    tax_info["IPI"] = extract_tax_details(block_ipi, "IPI")
                else: tax_info["IPI"] = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}
                
                # PIS
                if idx_pis != -1:
                    tax_info["PIS"] = extract_tax_details(item_text[idx_pis:limit_pis], "PIS")
                else: tax_info["PIS"] = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}
                
                # COFINS
                if idx_cofins != -1:
                    tax_info["COFINS"] = extract_tax_details(item_text[idx_cofins:], "COFINS")
                else: tax_info["COFINS"] = {"Base": 0.0, "Rate": 0.0, "Value": 0.0}

                # --- Montagem ---
                row = {
                    "Item": i,
                    "Part Number": pn,
                    
                    # II
                    "II Base": tax_info["II"]["Base"],
                    "II Aliq": tax_info["II"]["Rate"],
                    "II Vlr": tax_info["II"]["Value"],
                    
                    # IPI
                    "IPI Base": tax_info["IPI"]["Base"],
                    "IPI Aliq": tax_info["IPI"]["Rate"],
                    "IPI Vlr": tax_info["IPI"]["Value"],
                    
                    # PIS
                    "PIS Base": tax_info["PIS"]["Base"],
                    "PIS Aliq": tax_info["PIS"]["Rate"],
                    "PIS Vlr": tax_info["PIS"]["Value"],
                    
                    # COFINS
                    "COFINS Base": tax_info["COFINS"]["Base"],
                    "COFINS Aliq": tax_info["COFINS"]["Rate"],
                    "COFINS Vlr": tax_info["COFINS"]["Value"],
                    
                    "Total Tributos": tax_info["II"]["Value"] + tax_info["IPI"]["Value"] + tax_info["PIS"]["Value"] + tax_info["COFINS"]["Value"]
                }
                data.append(row)

            except Exception as e:
                print(f"Erro no item {i}: {e}")
                continue

    return pd.DataFrame(data)

# --- FRONTEND ---
st.title("🕵️ Validador Fiscal DUIMP (Correção IPI)")
st.info("Algoritmo ajustado para ignorar quebras de página dentro dos blocos de impostos.")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    df = parse_duimp_fixed(uploaded_file)
    
    if not df.empty:
        # Tabela Focada em IPI e Impostos
        st.subheader("Auditoria de IPI e Tributos")
        
        # Formatação
        format_dict = {col: "R$ {:,.2f}" for col in df.columns if "Base" in col or "Vlr" in col or "Total" in col}
        format_dict.update({col: "{:.2f}%" for col in df.columns if "Aliq" in col})
        
        # Destaca colunas do IPI
        cols_ipi = ["Item", "Part Number", "IPI Base", "IPI Aliq", "IPI Vlr", "Total Tributos"]
        st.dataframe(df[cols_ipi].style.format(format_dict).background_gradient(subset=["IPI Vlr"], cmap="Reds"), use_container_width=True)
        
        with st.expander("Ver Tabela Completa (Todos Impostos)"):
            st.dataframe(df.style.format(format_dict), use_container_width=True)
            
        # Download
        csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        st.download_button("📥 Baixar Excel (Correção IPI)", csv, "duimp_ipi_fixed.csv", "text/csv")
    else:
        st.warning("Nenhum dado processado.")
