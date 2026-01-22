import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Analisador DUIMP - Data Intelligence",
    page_icon="📦",
    layout="wide"
)

# --- ESTILIZAÇÃO CSS (Senior Dev Touch) ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
    }
    .main-header {
        font-size: 2.5rem;
        color: #1E1E1E;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE UTILIDADE ---
def clean_currency(value_str):
    """Converte strings financeiras (PT-BR) para float."""
    if not value_str:
        return 0.0
    try:
        # Remove símbolos, troca ponto por nada e vírgula por ponto
        clean = value_str.replace('R$', '').replace('US$', '').replace('EUR', '').strip()
        clean = clean.replace('.', '').replace(',', '.')
        return float(clean)
    except:
        return 0.0

def extract_field(text, pattern, group_index=1):
    """Extração segura via Regex."""
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(group_index).strip()
    return "N/A"

# --- CORE LÓGICO DE EXTRAÇÃO (Data Scientist Engine) ---
def parse_duimp(pdf_file):
    """
    Lê o PDF e estrutura os dados em um DataFrame Pandas.
    Baseado no layout do documento APP2.pdf.
    """
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # 1. Dados Gerais do Processo
    processo = extract_field(full_text, r"PROCESSO\s*[:#]?\s*(\d+)")
    importador = extract_field(full_text, r"IMPORTADOR\s*[\"']?,\s*[\"']?([^\"\n]+)")
    
    # 2. Estratégia de Segmentação por Item
    # O padrão "ITENS DA DUIMP-" é o divisor claro no documento fornecido
    raw_items = re.split(r"ITENS DA DUIMP-\d+", full_text)
    
    parsed_items = []
    
    # Pulamos o índice 0 pois é o cabeçalho antes do primeiro item
    for i, item_text in enumerate(raw_items[1:], start=1):
        # Extração de Atributos Principais
        part_number = extract_field(item_text, r"Código interno\s*(\d+(\.\d+)*)")
        ncm = extract_field(item_text, r"NCM\s*(\d{4}\.\d{2}\.\d{2})")
        
        # Descrição (captura multilinha até a próxima keyword)
        descricao = extract_field(item_text, r"DENOMINACAO DO PRODUTO\s*(.*?)\s*DESCRICAO DO PRODUTO")
        desc_detalhada = extract_field(item_text, r"DESCRICAO DO PRODUTO\s*(.*?)\s*Conhecido")
        
        # Quantitativos
        qtd = extract_field(item_text, r"Qtde Unid. Comercial\s*([\d\.,]+)")
        peso_liq = extract_field(item_text, r"Peso Líquido \(KG\)\s*([\d\.,]+)")
        
        # Financeiro
        valor_uni_eur = extract_field(item_text, r"Valor Unit Cond Venda\s*([\d\.,]+)")
        valor_tot_eur = extract_field(item_text, r"Valor Tot. Cond Venda\s*([\d\.,]+)")
        valor_aduaneiro_brl = extract_field(item_text, r"Base de Cálculo \(R\$\)\s*([\d\.,]+)") # Captura da primeira ocorrência (geralmente base II)
        
        # Tributos (Busca específica por blocos de impostos)
        # Nota: A regex busca o padrão "Valor A Recolher" dentro do contexto do tributo
        
        # II (Imposto de Importação)
        ii_match = re.search(r"II.*?Valor A Recolher \(R\$\)\s*([\d\.,]+)", item_text, re.DOTALL)
        ii_value = clean_currency(ii_match.group(1)) if ii_match else 0.0
        
        # IPI
        ipi_match = re.search(r"IPI.*?Valor A Recolher \(R\$\)\s*([\d\.,]+)", item_text, re.DOTALL)
        ipi_value = clean_currency(ipi_match.group(1)) if ipi_match else 0.0
        
        # PIS
        pis_match = re.search(r"PIS.*?Valor A Recolher \(R\$\)\s*([\d\.,]+)", item_text, re.DOTALL)
        pis_value = clean_currency(pis_match.group(1)) if pis_match else 0.0
        
        # COFINS
        cofins_match = re.search(r"COFINS.*?Valor A Recolher \(R\$\)\s*([\d\.,]+)", item_text, re.DOTALL)
        cofins_value = clean_currency(cofins_match.group(1)) if cofins_match else 0.0

        # Montagem do Objeto
        parsed_items.append({
            "Item": i,
            "Part Number": part_number,
            "NCM": ncm,
            "Denominação": descricao.replace('\n', ' ').strip(),
            "Descrição Detalhada": desc_detalhada.replace('\n', ' ').strip()[:100] + "...", # Truncar para visualização
            "Qtd": clean_currency(qtd),
            "Peso Liq (Kg)": clean_currency(peso_liq),
            "Vlr Unit (EUR)": clean_currency(valor_uni_eur),
            "Vlr Total (EUR)": clean_currency(valor_tot_eur),
            "Vlr Aduaneiro (R$)": clean_currency(valor_aduaneiro_brl),
            "II (R$)": ii_value,
            "IPI (R$)": ipi_value,
            "PIS (R$)": pis_value,
            "COFINS (R$)": cofins_value,
            "Total Impostos (R$)": ii_value + ipi_value + pis_value + cofins_value
        })
        
    return pd.DataFrame(parsed_items), processo, importador

# --- INTERFACE DO USUÁRIO (Frontend) ---

st.title("📊 Extrator Inteligente de DUIMP")
st.markdown("**Role:** Data Scientist & Senior Dev | **Contexto:** Análise Tributária de Importação")
st.markdown("---")

uploaded_file = st.file_uploader("Faça o upload do PDF da DUIMP (Layout Padrão)", type="pdf")

if uploaded_file is not None:
    with st.spinner('Processando PDF com Regex e NLP...'):
        try:
            df, processo_num, importador_nome = parse_duimp(uploaded_file)
            
            # --- DASHBOARD HEADER ---
            st.success("Processamento concluído com sucesso!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Processo:** {processo_num}")
                st.markdown(f"**Importador:** {importador_nome}")
            with col2:
                total_aduaneiro = df["Vlr Aduaneiro (R$)"].sum()
                st.metric("Total Valor Aduaneiro", f"R$ {total_aduaneiro:,.2f}")
            with col3:
                total_impostos = df["Total Impostos (R$)"].sum()
                st.metric("Total Tributos Recolhidos", f"R$ {total_impostos:,.2f}", delta="Custo Fiscal")

            st.markdown("---")

            # --- VISUALIZAÇÃO DE DADOS (Charts) ---
            st.subheader("📈 Análise Visual")
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Composição dos Impostos
                impostos_cols = ["II (R$)", "IPI (R$)", "PIS (R$)", "COFINS (R$)"]
                impostos_total = df[impostos_cols].sum().reset_index()
                impostos_total.columns = ["Tributo", "Valor"]
                
                fig_pie = px.pie(impostos_total, values='Valor', names='Tributo', title='Breakdown de Impostos (Total do Processo)', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with chart_col2:
                # Custo por Item
                fig_bar = px.bar(df, x="Part Number", y=["Vlr Aduaneiro (R$)", "Total Impostos (R$)"], 
                                 title="Valor Aduaneiro vs. Carga Tributária por Item",
                                 barmode='group')
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- TABELA DETALHADA ---
            st.subheader("📋 Detalhamento por Item (Tabela Auditável)")
            
            # Formatação para exibição (Pandas Styler)
            st.dataframe(
                df.style.format({
                    "Vlr Unit (EUR)": "€ {:.2f}",
                    "Vlr Total (EUR)": "€ {:.2f}",
                    "Vlr Aduaneiro (R$)": "R$ {:.2f}",
                    "II (R$)": "R$ {:.2f}",
                    "IPI (R$)": "R$ {:.2f}",
                    "PIS (R$)": "R$ {:.2f}",
                    "COFINS (R$)": "R$ {:.2f}",
                    "Total Impostos (R$)": "R$ {:.2f}",
                    "Qtd": "{:.0f}",
                    "Peso Liq (Kg)": "{:.3f}"
                }),
                use_container_width=True,
                height=400
            )

            # --- EXPORTAÇÃO ---
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Dados em Excel (CSV)",
                data=csv,
                file_name=f'DUIMP_{processo_num}_extract.csv',
                mime='text/csv',
            )

        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
            st.warning("Certifique-se que o PDF segue exatamente o layout 'APP2' fornecido.")
            with st.expander("Ver detalhes técnicos do erro"):
                st.write(e)
else:
    st.info("Aguardando upload do arquivo PDF...")
