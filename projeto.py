import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Leitor DUIMP Definitivo", page_icon="🚀", layout="wide")

# --- FUNÇÕES DE LIMPEZA E EXTRAÇÃO ---
def clean_currency(value_str):
    """Converte strings como '3.318,72' ou '531,0000000' para float."""
    if not value_str: return 0.0
    try:
        # Pega apenas a parte numérica, remove pontos de milhar e troca vírgula decimal
        clean = re.sub(r'[^\d,]', '', str(value_str))
        clean = clean.replace(',', '.')
        return float(clean)
    except:
        return 0.0

def extract_field_regex(text, pattern, default="N/A"):
    """Busca segura com Regex."""
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return default

def extract_tax_value(item_text, tax_name):
    """
    Busca o 'Valor A Recolher' especificamente dentro do bloco do imposto (II, IPI, etc).
    Usa Regex Non-Greedy (.*?) para parar no primeiro valor encontrado após o nome do imposto.
    """
    # Padrão: Nome do Imposto ... (texto qualquer) ... Valor A Recolher (R$) ... (VALOR)
    pattern = rf"{tax_name}.*?Valor A Recolher \(R\$\)\s*([\d\.,]+)"
    val_str = extract_field_regex(item_text, pattern, default="0,00")
    return clean_currency(val_str)

# --- CORE LÓGICO ---
def parse_duimp_advanced(pdf_file):
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # Debug: Se quiser ver o texto lido no terminal
    # print(full_text)

    # 1. Estratégia de Divisão: "ITENS DA DUIMP"
    # O texto bruto mostra "ITENS DA DUIMP - 00001", "ITENS DA DUIMP-00002" (com e sem espaço)
    raw_items = re.split(r"ITENS DA DUIMP\s*-\s*\d+", full_text)

    data = []
    
    # Ignoramos o índice 0 (cabeçalho do processo)
    if len(raw_items) > 1:
        for i, item_text in enumerate(raw_items[1:], start=1):
            
            # --- EXTRAÇÃO BASEADA NO SEU DUMP DE TEXTO ---
            
            # Part Number: No texto aparece "Código interno\n342.79.301"
            pn = extract_field_regex(item_text, r"Código interno\s*([\d\.]+)")
            
            # NCM: Aparece "NCM\n8302.10.00" ou próximo
            ncm = extract_field_regex(item_text, r"NCM\s*.*?(\d{4}\.\d{2}\.\d{2})")
            
            # Valor Aduaneiro: No texto aparece explicitamente "Local Aduaneiro (R$) 3.318,72"
            vlr_aduaneiro_str = extract_field_regex(item_text, r"Local Aduaneiro \(R\$\)\s*([\d\.,]+)")
            
            # Descrição: Captura o texto entre "DESCRICAO DO PRODUTO" e "Conhecido" ou "Código interno"
            desc = extract_field_regex(item_text, r"DESCRICAO DO PRODUTO\s*(.*?)\s*(?:Conhecido|Código interno|CÓDIGO INTERNO)")
            
            # Quantidade: "Qtde Unid. Comercial\n100,00000"
            qtd_str = extract_field_regex(item_text, r"Qtde Unid. Comercial\s*([\d\.,]+)")

            # --- IMPOSTOS (Lógica Refinada) ---
            ii = extract_tax_value(item_text, "II")
            ipi = extract_tax_value(item_text, "IPI")
            pis = extract_tax_value(item_text, "PIS")
            cofins = extract_tax_value(item_text, "COFINS")

            # Monta Objeto
            data.append({
                "Item": i,
                "Part Number": pn,
                "NCM": ncm,
                "Descrição": desc.replace('\n', ' ')[:100], # Limpa quebras de linha
                "Qtd": clean_currency(qtd_str),
                "Valor Aduaneiro (R$)": clean_currency(vlr_aduaneiro_str),
                "II (R$)": ii,
                "IPI (R$)": ipi,
                "PIS (R$)": pis,
                "COFINS (R$)": cofins,
                "Total Impostos (R$)": ii + ipi + pis + cofins
            })

    return pd.DataFrame(data)

# --- FRONTEND STREAMLIT ---
st.title("📊 Extrator DUIMP - Layout APP2")
st.markdown("**Status:** Algoritmo ajustado para o padrão exato do texto fornecido.")

uploaded_file = st.file_uploader("Arraste o PDF aqui", type="pdf")

if uploaded_file:
    with st.spinner("Decodificando PDF..."):
        try:
            df = parse_duimp_advanced(uploaded_file)
            
            if df.empty:
                st.error("O PDF foi lido, mas a Regex não 'casou' com os itens. Verifique se é o arquivo correto.")
            else:
                # 1. KPIs
                st.markdown("### Resumo do Processo")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Itens", len(df))
                col2.metric("Total Aduaneiro", f"R$ {df['Valor Aduaneiro (R$)'].sum():,.2f}")
                col3.metric("Total Tributos", f"R$ {df['Total Impostos (R$)'].sum():,.2f}")
                
                # 2. Gráficos
                st.markdown("---")
                c1, c2 = st.columns(2)
                
                with c1:
                    # Gráfico de Impostos
                    taxes = df[["II (R$)", "IPI (R$)", "PIS (R$)", "COFINS (R$)"]].sum().reset_index()
                    taxes.columns = ["Imposto", "Valor"]
                    fig = px.pie(taxes, values="Valor", names="Imposto", title="Distribuição Tributária")
                    st.plotly_chart(fig, use_container_width=True)
                
                with c2:
                    # Top Itens por Custo
                    fig2 = px.bar(df.head(10), x="Part Number", y="Total Impostos (R$)", title="Top Itens por Custo de Imposto")
                    st.plotly_chart(fig2, use_container_width=True)

                # 3. Tabela de Dados
                st.markdown("### Detalhamento por Item")
                st.dataframe(
                    df.style.format({
                        "Valor Aduaneiro (R$)": "R$ {:.2f}",
                        "II (R$)": "R$ {:.2f}",
                        "IPI (R$)": "R$ {:.2f}",
                        "PIS (R$)": "R$ {:.2f}",
                        "COFINS (R$)": "R$ {:.2f}",
                        "Total Impostos (R$)": "R$ {:.2f}",
                        "Qtd": "{:.0f}"
                    }),
                    use_container_width=True,
                    height=500
                )
                
                # Download
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Tabela em Excel (CSV)", csv, "duimp_extraida.csv", "text/csv")

        except Exception as e:
            st.error(f"Erro Crítico: {e}")
