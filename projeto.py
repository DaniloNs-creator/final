import streamlit as st
import pdfplumber
import pandas as pd
import re

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Validador DUIMP - IPI Corrigido", page_icon="✅", layout="wide")

# --- FUNÇÕES DE LIMPEZA ---
def clean_currency(value_str):
    """Converte strings financeiras (ex: '3.318,72') para float."""
    if not value_str: return 0.0
    try:
        clean = re.sub(r'[^\d,]', '', str(value_str).split()[0])
        clean = clean.replace(',', '.')
        return float(clean)
    except:
        return 0.0

def clean_text_content(text):
    """Remove numeração de páginas para evitar quebras no meio das tabelas."""
    return re.sub(r'--- PAGE \d+ ---', '', text)

# --- EXTRAÇÃO DE DADOS ---
def extract_tax_data(item_text, tax_name):
    """
    Extrai Base, Alíquota e Valor de um imposto.
    Lógica Padrão: Funciona bem para II, PIS, COFINS.
    """
    # Encontra o bloco do imposto (do nome até o próximo nome ou fim)
    # Regex ajustada para pegar o bloco correto
    tax_map = {"II": "II", "IPI": "IPI", "PIS": "PIS", "COFINS": "COFINS"}
    
    # Índices aproximados (simples busca de texto)
    idx_start = item_text.find(f"\n{tax_name}\n")
    if idx_start == -1: idx_start = item_text.find(f" {tax_name} ")
    if idx_start == -1: return 0.0, 0.0, 0.0 # Não achou o imposto
    
    # Onde termina? No próximo imposto ou fim do texto
    indices = []
    for t in ["II", "IPI", "PIS", "COFINS"]:
        idx = item_text.find(f"\n{t}\n", idx_start + 5) # +5 para não achar a si mesmo
        if idx != -1: indices.append(idx)
        # Tenta achar sem quebra de linha também (cabeçalhos colados)
        idx2 = item_text.find(f" {t} ", idx_start + 5)
        if idx2 != -1: indices.append(idx2)
        
    idx_end = min(indices) if indices else len(item_text)
    
    block = item_text[idx_start:idx_end]
    
    # Extração de Valores
    base = 0.0
    rate = 0.0
    val = 0.0
    
    # Base
    m_base = re.search(r"Base de Cálculo \(R\$\)\s*([\d\.,]+)", block)
    if m_base: base = clean_currency(m_base.group(1))
    
    # Valor
    m_val = re.search(r"Valor A Recolher \(R\$\)\s*([\d\.,]+)", block)
    if not m_val: m_val = re.search(r"Valor Devido \(R\$\)\s*([\d\.,]+)", block)
    if m_val: val = clean_currency(m_val.group(1))
    
    # Alíquota
    m_rate = re.search(r"% Alíquota\s*([\d\.,]+)", block)
    if not m_rate: m_rate = re.search(r"AD VALOREM\s*([\d\.,]+)", block) # Às vezes o número vem logo depois
    if m_rate: rate = clean_currency(m_rate.group(1))
    
    return base, rate, val

def extract_ipi_safe(item_text):
    """
    Lógica BLINDADA para o IPI.
    Verifica se o Valor encontrado pertence à Base do IPI.
    """
    # 1. Achar a Base do IPI (geralmente a primeira coisa do bloco IPI)
    idx_ipi = item_text.find("IPI")
    if idx_ipi == -1: return 0.0, 0.0, 0.0
    
    # Pega um pedaço generoso de texto a partir do IPI
    ipi_chunk = item_text[idx_ipi:]
    
    # Base do IPI
    m_base = re.search(r"Base de Cálculo \(R\$\)\s*([\d\.,]+)", ipi_chunk)
    if not m_base: return 0.0, 0.0, 0.0
    ipi_base = clean_currency(m_base.group(1))
    
    # 2. Procurar Valor a Recolher
    # O problema: O texto pode pular para a tabela do PIS que tem outra base.
    # Vamos procurar "Valor A Recolher" e ver a "Base" que está IMEDIATAMENTE antes dele no texto visual
    
    # Regex que captura: Base ... (coisas) ... Valor
    # Limitamos o tamanho do "coisas" para garantir que estamos na mesma tabela
    pattern_validate = r"Base de Cálculo \(R\$\)\s*([\d\.,]+).*?Valor A Recolher \(R\$\)\s*([\d\.,]+)"
    
    matches = re.findall(pattern_validate, ipi_chunk, re.DOTALL)
    
    ipi_val = 0.0
    ipi_rate = 0.0
    
    # Varre as tabelas encontradas no chunk do IPI
    for base_found_str, val_found_str in matches:
        base_found = clean_currency(base_found_str)
        
        # O PULO DO GATO:
        # Se a base encontrada ao lado do valor for IGUAL à base do IPI, então é o valor do IPI.
        # Se for diferente (ex: Base IPI 3.800 mas Base encontrada 3.300), é o PIS invadindo!
        
        # Aceitamos uma margem de erro de R$ 1,00 para arredondamentos
        if abs(base_found - ipi_base) < 1.0:
            ipi_val = clean_currency(val_found_str)
            break # Achamos o valor correto!
            
    # Se loop terminar e não achar correspondência, ipi_val continua 0.0 (Correto!)
    
    # Tenta achar alíquota no mesmo bloco seguro
    if ipi_val > 0:
        m_rate = re.search(r"% Alíquota\s*([\d\.,]+)", ipi_chunk) # Simplificação
        if m_rate: ipi_rate = clean_currency(m_rate.group(1))
        
    return ipi_base, ipi_rate, ipi_val

# --- PROCESSAMENTO PRINCIPAL ---
def parse_duimp(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
            
    # Remove marcadores de página que quebram a leitura do IPI
    full_text = clean_text_content(full_text)
    
    # Separa itens
    items = re.split(r"ITENS DA DUIMP", full_text)
    
    data = []
    
    if len(items) > 1:
        for i, item_text in enumerate(items[1:], start=1):
            # Identificação
            pn_match = re.search(r"Código interno\s*([\d\.]+)", item_text)
            pn = pn_match.group(1) if pn_match else f"Item {i}"
            
            # --- LÓGICA MISTA ---
            
            # 1. II, PIS, COFINS -> Lógica Padrão (que você gostou)
            ii_base, ii_rate, ii_val = extract_tax_data(item_text, "II")
            pis_base, pis_rate, pis_val = extract_tax_data(item_text, "PIS")
            cof_base, cof_rate, cof_val = extract_tax_data(item_text, "COFINS")
            
            # 2. IPI -> Lógica Blindada (Valida Base)
            ipi_base, ipi_rate, ipi_val = extract_ipi_safe(item_text)
            
            # Monta linha
            row = {
                "Item": i,
                "Part Number": pn,
                
                "II Base": ii_base,
                "II Valor": ii_val,
                
                "IPI Base": ipi_base,
                "IPI Valor": ipi_val, # Agora virá zerado se a base não bater!
                
                "PIS Base": pis_base,
                "PIS Valor": pis_val,
                
                "COFINS Base": cof_base,
                "COFINS Valor": cof_val,
                
                "Total Tributos": ii_val + ipi_val + pis_val + cof_val
            }
            data.append(row)
            
    return pd.DataFrame(data)

# --- FRONTEND ---
st.title("Validador DUIMP (Restaurado + IPI Fix)")
st.warning("Lógica original restaurada para II, PIS e COFINS. IPI agora tem validação por Base de Cálculo.")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    df = parse_duimp(uploaded_file)
    
    if not df.empty:
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Total IPI", f"R$ {df['IPI Valor'].sum():,.2f}")
        c2.metric("Total Tributos", f"R$ {df['Total Tributos'].sum():,.2f}")
        c3.metric("Itens", len(df))
        
        st.divider()
        
        # Tabela Detalhada
        st.markdown("### Auditoria de Valores")
        st.dataframe(
            df.style.format("R$ {:,.2f}", subset=[c for c in df.columns if "Base" in c or "Valor" in c or "Total" in c]),
            use_container_width=True,
            height=600
        )
        
        # Download
        csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        st.download_button("📥 Baixar Excel", csv, "duimp_final.csv", "text/csv")
