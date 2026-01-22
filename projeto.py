import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Leitor DUIMP Contextual", page_icon="🎯", layout="wide")

# --- FUNÇÕES DE TEXTO ---
def clean_currency(value_str):
    """Limpa e converte strings financeiras (ex: '3.318,7200000' -> 3318.72)."""
    if not value_str: return 0.0
    try:
        # Pega a parte numérica até o primeiro espaço (remove '00000' excessivos se necessário, mas float resolve)
        # O padrão brasileiro usa ponto para milhar e vírgula para decimal.
        # Mas no dump seu, '3.318,7200000'.
        clean = re.sub(r'[^\d,]', '', str(value_str).split()[0])
        clean = clean.replace(',', '.')
        return float(clean)
    except:
        return 0.0

def extract_block_value(block_text, label_pattern):
    """Busca um valor dentro de um bloco de texto específico."""
    # Procura pelo label (ex: "Valor A Recolher") seguido de um número
    # A regex busca o número que pode estar na mesma linha ou na próxima
    match = re.search(rf"{label_pattern}.*?([\d\.,]+)", block_text, re.DOTALL | re.IGNORECASE)
    if match:
        return clean_currency(match.group(1))
    return 0.0

# --- CORE LÓGICO: EXTRAÇÃO POR BLOCOS ---
def parse_duimp_contextual(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # Separa os itens
    raw_items = re.split(r"ITENS DA DUIMP\s*-\s*\d+", full_text)
    
    data = []
    
    if len(raw_items) > 1:
        for i, item_text in enumerate(raw_items[1:], start=1):
            
            # 1. Dados Básicos do Item
            pn = re.search(r"Código interno\s*([\d\.]+)", item_text)
            pn_val = pn.group(1) if pn else "N/A"
            
            desc = re.search(r"DESCRICAO DO PRODUTO\s*(.*?)\s*(?:Conhecido|Código interno)", item_text, re.DOTALL)
            desc_val = desc.group(1).replace('\n', ' ').strip() if desc else "N/A"

            # 2. Extração Contextual de Impostos
            # A estratégia é encontrar onde começa cada imposto e recortar o texto até o próximo
            
            # Normaliza o texto para facilitar a busca (tudo em uma linha só pode ajudar, mas regex DOTALL resolve)
            
            taxes_data = {
                "II": {"Base": 0.0, "Valor": 0.0},
                "IPI": {"Base": 0.0, "Valor": 0.0},
                "PIS": {"Base": 0.0, "Valor": 0.0},
                "COFINS": {"Base": 0.0, "Valor": 0.0}
            }

            # Define a ordem provável dos blocos para recortar
            # No seu PDF a ordem parece ser: II -> IPI -> PIS -> COFINS (ou variações, mas os labels existem)
            
            # Função auxiliar para extrair dados de um bloco nomeado
            def process_tax(tax_name):
                # Regex para pegar o bloco do imposto específico.
                # Começa com o NOME DO IMPOSTO (ex: "COFINS")
                # Termina quando encontra outro nome de imposto ou fim de seção
                # O Lookahead (?=...) garante que paramos antes do próximo título
                
                # Pattern mais solto: Pega do nome do imposto até 400 caracteres (suficiente para a tabela)
                # ou até o próximo label forte.
                pattern = rf"(?:\n|^){tax_name}\s.*?(?=(?:\n|^)(?:II|IPI|PIS|COFINS|INFORMAÇÕES|ITENS)|$)"
                
                block_match = re.search(pattern, item_text, re.DOTALL | re.IGNORECASE)
                
                if block_match:
                    block = block_match.group(0)
                    # Dentro deste bloco, buscamos os valores específicos
                    base = extract_block_value(block, r"Base de Cálculo \(R\$\)")
                    
                    # No seu dump, 'Valor A Recolher' aparece APÓS o label.
                    # As vezes o OCR joga o número antes ou depois dependendo da tabela.
                    # Vou usar uma regex que pega números próximos a "Valor A Recolher"
                    valor = extract_block_value(block, r"Valor A Recolher \(R\$\)")
                    
                    # Fallback: Se não achar "A Recolher", tenta "Valor Devido"
                    if valor == 0.0:
                        valor = extract_block_value(block, r"Valor Devido \(R\$\)")
                        
                    return base, valor
                return 0.0, 0.0

            # Processa cada um
            taxes_data["II"]["Base"], taxes_data["II"]["Valor"] = process_tax("II")
            taxes_data["IPI"]["Base"], taxes_data["IPI"]["Valor"] = process_tax("IPI")
            
            # PIS e COFINS as vezes compartilham cabeçalho "PIS-IMPORTAÇÃO e COFINS...", 
            # mas os blocos de valores são separados.
            # O dump mostra "PIS" isolado antes dos valores dele, e "COFINS" isolado antes dos dele.
            taxes_data["PIS"]["Base"], taxes_data["PIS"]["Valor"] = process_tax("PIS")
            taxes_data["COFINS"]["Base"], taxes_data["COFINS"]["Valor"] = process_tax("COFINS")

            # Monta a linha
            row = {
                "Item": i,
                "Part Number": pn_val,
                "Descrição": desc_val[:80] + "...",
                
                "Base II": taxes_data["II"]["Base"],
                "II Devido": taxes_data["II"]["Valor"],
                
                "Base IPI": taxes_data["IPI"]["Base"],
                "IPI Devido": taxes_data["IPI"]["Valor"],
                
                "Base PIS": taxes_data["PIS"]["Base"],
                "PIS Devido": taxes_data["PIS"]["Valor"],
                
                "Base COFINS": taxes_data["COFINS"]["Base"],
                "COFINS Devido": taxes_data["COFINS"]["Valor"],
                
                "Total Tributos": sum(t["Valor"] for t in taxes_data.values())
            }
            data.append(row)

    return pd.DataFrame(data)

# --- FRONTEND ---
st.title("🧩 DUIMP Analyzer - Extração Contextual")
st.info("Algoritmo atualizado: Recorta blocos de texto (II, PIS, COFINS) antes de ler os valores.")

uploaded_file = st.file_uploader("Upload DUIMP (PDF)", type="pdf")

if uploaded_file:
    with st.spinner("Analisando blocos de impostos..."):
        try:
            df = parse_duimp_contextual(uploaded_file)
            
            if df.empty:
                st.warning("Nenhum dado encontrado.")
            else:
                # Métricas Gerais
                col1, col2 = st.columns(2)
                col1.metric("Total Tributos (Extraído)", f"R$ {df['Total Tributos'].sum():,.2f}")
                col2.metric("Itens Processados", len(df))
                
                # Tabela Principal
                st.subheader("Detalhamento Fiscal por Item")
                st.dataframe(
                    df.style.format("{:.2f}", subset=[
                        "Base II", "II Devido", 
                        "Base IPI", "IPI Devido",
                        "Base PIS", "PIS Devido",
                        "Base COFINS", "COFINS Devido",
                        "Total Tributos"
                    ]),
                    use_container_width=True,
                    height=600
                )
                
                # Debug Visual (Opcional - ajuda a ver se a lógica está batendo)
                with st.expander("Verificar Lógica de um Item (Debug)"):
                    item_exemplo = df.iloc[0]
                    st.write(f"**Item 1 ({item_exemplo['Part Number']}) - COFINS:**")
                    st.write(f"Base: R$ {item_exemplo['Base COFINS']:,.2f}")
                    st.write(f"Devido: R$ {item_exemplo['COFINS Devido']:,.2f}")
                    st.caption("Se estes valores baterem com o PDF (Ex: Base ~922,67 e Valor ~89,04), a lógica está correta.")

        except Exception as e:
            st.error(f"Erro: {e}")
