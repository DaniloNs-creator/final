import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="DUIMP Analyzer Debug", page_icon="🛠️", layout="wide")

# --- UTILITÁRIOS ---
def clean_currency(value_str):
    if not value_str: return 0.0
    try:
        # Pega o primeiro token numérico, limpa tudo que não é dígito ou vírgula
        # Ex: "3.318,7200000" -> "3318,7200000" -> 3318.72
        clean = re.sub(r'[^\d,]', '', str(value_str).split()[0])
        clean = clean.replace(',', '.')
        return float(clean)
    except:
        return 0.0

def find_tax_value(text_block, tax_name):
    """
    Busca valores dentro de um bloco de texto já recortado.
    Prioridade: 'Valor A Recolher' -> 'Valor Devido' -> 'Valor Calculado'
    """
    # Regex flexível que aceita quebras de linha entre o rótulo e o valor
    patterns = [
        r"Valor A Recolher.*?([\d\.,]+)",
        r"Valor Devido.*?([\d\.,]+)",
        r"Valor Calculado.*?([\d\.,]+)"
    ]
    
    for pat in patterns:
        match = re.search(pat, text_block, re.IGNORECASE | re.DOTALL)
        if match:
            return clean_currency(match.group(1))
    return 0.0

# --- ENGINE DE EXTRAÇÃO (Slicing Strategy) ---
def parse_duimp_debug(pdf_file):
    status_log = [] # Lista para guardar logs de execução
    
    status_log.append("📂 Abrindo arquivo PDF...")
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for i, page in enumerate(pdf.pages):
            full_text += page.extract_text() + "\n"
    
    status_log.append(f"📄 Texto extraído: {len(full_text)} caracteres.")

    # 1. Divisão por Itens
    # Regex simples para quebrar nos cabeçalhos de itens
    raw_items = re.split(r"ITENS DA DUIMP", full_text)
    
    status_log.append(f"✂️ Segmentos encontrados: {len(raw_items)} (incluindo cabeçalho).")
    
    data = []
    
    # Processa do índice 1 em diante (o 0 é o cabeçalho do processo)
    if len(raw_items) > 1:
        for i, item_text in enumerate(raw_items[1:], start=1):
            try:
                # --- Identificação Básica ---
                pn_match = re.search(r"Código interno\s*([\d\.]+)", item_text)
                pn = pn_match.group(1) if pn_match else f"Item {i}"
                
                # --- Estratégia de Fatiamento (Slicing) para Impostos ---
                # A ordem no PDF é fixa: II -> IPI -> PIS -> COFINS
                # Vamos achar os índices onde cada seção começa
                
                # Normaliza para letras maiúsculas para facilitar busca
                text_upper = item_text.upper()
                
                # Busca as posições (índices) dos cabeçalhos
                # Nota: Adicionamos um caractere de "fim" virtual
                idx_ii = text_upper.find("\nII\n") 
                if idx_ii == -1: idx_ii = text_upper.find(" II ") # Tenta sem quebra de linha
                
                idx_ipi = text_upper.find("\nIPI\n")
                if idx_ipi == -1: idx_ipi = text_upper.find(" IPI ")
                
                idx_pis = text_upper.find("PIS-IMPORTAÇÃO") # Cabeçalho comum do PIS
                if idx_pis == -1: idx_pis = text_upper.find("\nPIS\n")
                
                idx_cofins = text_upper.find("\nCOFINS\n")
                if idx_cofins == -1: idx_cofins = text_upper.find(" COFINS ")
                
                # Define o final do texto (para o último imposto)
                idx_end = len(text_upper)
                
                # Valores padrão
                val_ii = val_ipi = val_pis = val_cofins = 0.0
                
                # Recorta e extrai II (Se achou o cabeçalho II e o próximo IPI)
                if idx_ii != -1 and idx_ipi != -1:
                    block_ii = item_text[idx_ii:idx_ipi]
                    val_ii = find_tax_value(block_ii, "II")
                
                # Recorta e extrai IPI
                if idx_ipi != -1 and idx_pis != -1:
                    block_ipi = item_text[idx_ipi:idx_pis]
                    val_ipi = find_tax_value(block_ipi, "IPI")
                
                # Recorta e extrai PIS
                if idx_pis != -1 and idx_cofins != -1:
                    block_pis = item_text[idx_pis:idx_cofins]
                    val_pis = find_tax_value(block_pis, "PIS")
                
                # Recorta e extrai COFINS (do COFINS até o fim do item)
                if idx_cofins != -1:
                    block_cofins = item_text[idx_cofins:idx_end]
                    val_cofins = find_tax_value(block_cofins, "COFINS")

                # Valor Aduaneiro (Base)
                base_match = re.search(r"Local Aduaneiro.*?([\d\.,]+)", item_text)
                base_val = clean_currency(base_match.group(1)) if base_match else 0.0

                data.append({
                    "Item": i,
                    "Part Number": pn,
                    "Base Aduaneira": base_val,
                    "II": val_ii,
                    "IPI": val_ipi,
                    "PIS": val_pis,
                    "COFINS": val_cofins,
                    "Total Impostos": val_ii + val_ipi + val_pis + val_cofins
                })
            except Exception as e:
                status_log.append(f"⚠️ Erro ao processar item {i}: {str(e)}")
                continue

    return pd.DataFrame(data), status_log

# --- FRONTEND ---
st.title("🛠️ Analisador DUIMP (Modo Seguro)")
st.info("Este modo exibe logs de execução para evitar tela branca.")

uploaded_file = st.file_uploader("Carregar PDF", type="pdf")

if uploaded_file:
    # Mostra logs em tempo real
    placeholder = st.empty()
    
    try:
        df, logs = parse_duimp_debug(uploaded_file)
        
        # Exibe os logs técnicos (Debugging)
        with st.expander("📝 Ver Logs de Extração (Técnico)"):
            for log in logs:
                st.text(log)
                
        if df.empty:
            st.error("❌ O processamento terminou mas nenhum dado foi tabularizado.")
            st.warning("Verifique se o PDF contém texto selecionável (não é imagem).")
        else:
            st.success(f"✅ Sucesso! {len(df)} itens processados.")
            
            # --- DASHBOARD ---
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Base Aduaneira", f"R$ {df['Base Aduaneira'].sum():,.2f}")
            col2.metric("Total Impostos", f"R$ {df['Total Impostos'].sum():,.2f}")
            col3.metric("Taxa Efetiva", f"{(df['Total Impostos'].sum()/df['Base Aduaneira'].sum()*100):.1f}%")
            
            st.markdown("---")
            
            # Gráfico Rápido
            chart_data = df[["Part Number", "Total Impostos"]].head(10)
            fig = px.bar(chart_data, x="Part Number", y="Total Impostos", title="Top Custos por Item")
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela
            st.dataframe(df.style.format("R$ {:.2f}", subset=["Base Aduaneira", "II", "IPI", "PIS", "COFINS", "Total Impostos"]), use_container_width=True)
            
    except Exception as e:
        st.error("💥 Erro Crítico no App:")
        st.code(str(e))
