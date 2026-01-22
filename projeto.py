import streamlit as st
import pdfplumber
import pandas as pd
import re

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Leitor DUIMP - IPI Fix", page_icon="🎯", layout="wide")

# --- FUNÇÕES DE LIMPEZA ---
def clean_currency(value_str):
    """Converte '3.849,7200000' para float 3849.72"""
    if not value_str: return 0.0
    try:
        # Pega apenas números e vírgula/ponto iniciais
        clean = re.sub(r'[^\d,]', '', str(value_str).split()[0])
        clean = clean.replace(',', '.')
        return float(clean)
    except:
        return 0.0

def clean_text_stream(text):
    """Remove cabeçalhos de página e une o texto para análise contínua"""
    # Remove marcadores de página comuns
    text = re.sub(r'--- PAGE \d+ ---', '', text)
    text = re.sub(r'ITENS DA DUIMP\s*-\s*\d+', ' ||ITEM_SEP|| ', text, flags=re.IGNORECASE)
    # Normaliza quebras de linha
    return text.replace('\n', ' ')

def extract_tax_by_base_barrier(item_text, tax_name):
    """
    Técnica de Barreira: Busca o valor do imposto apenas dentro do escopo
    da sua própria Base de Cálculo até a próxima Base de Cálculo.
    Isso impede que o IPI 'roube' o valor do PIS.
    """
    # 1. Encontrar a Base de Cálculo do Imposto Específico
    # Procura algo como "IPI ... Base de Cálculo (R$) 3.849,72"
    # O regex procura o nome do imposto, segue texto, acha "Base", pega o número.
    
    # Pattern: TaxName ... (text) ... Base de Cálculo (R$) (Value)
    start_pattern = rf"{tax_name}.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)"
    base_match = re.search(start_pattern, item_text, re.IGNORECASE)
    
    if not base_match:
        return 0.0, 0.0, 0.0 # Base, Rate, Value
        
    base_val_str = base_match.group(1)
    base_val = clean_currency(base_val_str)
    
    # Posição onde termina a Base do IPI
    start_search_idx = base_match.end()
    
    # 2. Definir a Barreira (Onde começa a próxima Base de Cálculo?)
    # Procuramos a próxima ocorrência de "Base de Cálculo" a partir daqui
    next_base_match = re.search(r"Base de Cálculo \(R\$\)", item_text[start_search_idx:])
    
    if next_base_match:
        # O limite é onde começa a próxima base
        end_search_idx = start_search_idx + next_base_match.start()
        # O bloco seguro é apenas entre a Base Atual e a Próxima Base
        safe_block = item_text[start_search_idx:end_search_idx]
    else:
        # Se não tiver próxima base, vai até o fim do item
        safe_block = item_text[start_search_idx:]
        
    # 3. Extrair Valores Seguros dentro do Bloco
    # Alíquota
    rate = 0.0
    rate_match = re.search(r"% Alíquota\s*([\d\.,]+)", safe_block)
    if not rate_match: # Tenta padrão alternativo
         rate_match = re.search(r"AD VALOREM.*?([\d\.,]+)", safe_block)
    if rate_match: rate = clean_currency(rate_match.group(1))
    
    # Valor a Recolher
    value = 0.0
    val_match = re.search(r"Valor A Recolher \(R\$\)\s*([\d\.,]+)", safe_block)
    if not val_match:
        val_match = re.search(r"Valor Devido \(R\$\)\s*([\d\.,]+)", safe_block)
        
    if val_match:
        value = clean_currency(val_match.group(1))
        
    return base_val, rate, value

# --- ENGINE PRINCIPAL ---
def parse_duimp_advanced(pdf_file):
    # 1. Leitura Linear Completa (Costura as páginas)
    full_text_pages = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text_pages.append(page.extract_text())
    
    full_text = "\n".join(full_text_pages)
    
    # Limpeza para remover cabeçalhos de página que quebram tabelas
    clean_content = clean_text_stream(full_text)
    
    # 2. Separação por Itens
    items_raw = clean_content.split('||ITEM_SEP||')
    
    data = []
    
    # Pula o primeiro bloco (cabeçalho geral)
    if len(items_raw) > 1:
        for i, item_text in enumerate(items_raw[1:], start=1):
            try:
                # --- Identificação ---
                pn_match = re.search(r"Código interno\s*([\d\.]+)", item_text)
                pn = pn_match.group(1) if pn_match else f"Item {i}"
                
                # --- Extração Cirúrgica por Barreiras ---
                # A ordem de extração não importa mais, pois cada um busca sua própria Base
                
                # II
                ii_base, ii_rate, ii_val = extract_tax_by_base_barrier(item_text, "II")
                
                # IPI (Agora protegido pela lógica de barreira)
                # Ele vai procurar "IPI ... Base" e parar antes de "Base" do PIS
                ipi_base, ipi_rate, ipi_val = extract_tax_by_base_barrier(item_text, "IPI")
                
                # PIS
                pis_base, pis_rate, pis_val = extract_tax_by_base_barrier(item_text, "PIS")
                
                # COFINS
                cofins_base, cofins_rate, cofins_val = extract_tax_by_base_barrier(item_text, "COFINS")

                # --- Montagem ---
                row = {
                    "Item": i,
                    "Part Number": pn,
                    
                    # IPI (O foco do problema)
                    "IPI Base": ipi_base,
                    "IPI Alíquota": ipi_rate,
                    "IPI Valor": ipi_val,
                    
                    # Outros
                    "II Valor": ii_val,
                    "PIS Valor": pis_val,
                    "COFINS Valor": cofins_val,
                    "Total Tributos": ii_val + ipi_val + pis_val + cofins_val
                }
                data.append(row)
                
            except Exception as e:
                print(f"Erro item {i}: {e}")
                
    return pd.DataFrame(data)

# --- FRONTEND ---
st.title("🛡️ Validador Fiscal - Solução Definitiva IPI")
st.info("Algoritmo de 'Barreira de Base de Cálculo' aplicado. Impede que o IPI leia valores do PIS mesmo com quebras de página.")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    df = parse_duimp_advanced(uploaded_file)
    
    if not df.empty:
        # Métricas de Validação
        c1, c2, c3 = st.columns(3)
        c1.metric("Total IPI (Extraído)", f"R$ {df['IPI Valor'].sum():,.2f}")
        c2.metric("Total PIS (Extraído)", f"R$ {df['PIS Valor'].sum():,.2f}")
        c3.metric("Total Geral", f"R$ {df['Total Tributos'].sum():,.2f}")
        
        st.divider()
        
        st.subheader("Auditoria Item a Item")
        # Formatação
        fmt = "{:,.2f}"
        st.dataframe(
            df.style.format({
                "IPI Base": "R$ {:,.2f}", 
                "IPI Alíquota": "{:.2f}%", 
                "IPI Valor": "R$ {:,.2f}",
                "II Valor": "R$ {:,.2f}",
                "PIS Valor": "R$ {:,.2f}",
                "COFINS Valor": "R$ {:,.2f}",
                "Total Tributos": "R$ {:,.2f}"
            }), 
            use_container_width=True,
            height=500
        )
        
        # Download
        csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha Corrigida", csv, "duimp_final_ipi_ok.csv", "text/csv")
        
    else:
        st.warning("Arquivo processado mas nenhum dado foi encontrado. Verifique se o PDF contém texto.")
