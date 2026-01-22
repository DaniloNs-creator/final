import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="DUIMP Analytics Pro",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILIZAÇÃO CSS (Tema Corporativo) ---
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .css-1d391kg { padding-top: 1rem; }
    h1, h2, h3 { color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

# --- UTILITÁRIOS ---
def clean_currency(value_str):
    """
    Converte strings de moeda (ex: '3.318,72') para float (3318.72).
    Robusto contra None, strings vazias e formatações estranhas.
    """
    if not value_str or not isinstance(value_str, str):
        return 0.0
    try:
        # Remove símbolos de moeda e espaços
        clean = re.sub(r'[^\d,]', '', value_str.split()[0]) # Pega apenas a parte numérica se houver texto
        # Troca vírgula decimal por ponto
        clean = clean.replace(',', '.')
        return float(clean)
    except (ValueError, IndexError):
        return 0.0

def extract_field(text, pattern, group_index=1, default="N/A"):
    """
    Extração segura via Regex com valor padrão (fallback).
    """
    if not text:
        return default
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if match:
        return match.group(group_index).strip()
    return default

# --- ENGINE DE EXTRAÇÃO (Lógica Core) ---
def parse_duimp(pdf_file):
    """
    Lê o PDF da DUIMP e estrutura os dados item a item.
    Otimizado para o layout 'APP2.pdf'.
    """
    full_text = ""
    # Abre o PDF e extrai texto concatenado
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    # 1. Metadados do Processo
    processo = extract_field(full_text, r"PROCESSO\s*[:#]?\s*(\d+)")
    importador = extract_field(full_text, r"IMPORTADOR\s*[\"']?,\s*[\"']?([^\"\n]+)")
    
    # 2. Segmentação por Item (Anchor: "ITENS DA DUIMP-XXXXX")
    # Usa re.split com flag de ignore case e espaços flexíveis
    raw_items = re.split(r"ITENS DA DUIMP\s*-\s*\d+", full_text, flags=re.IGNORECASE)
    
    parsed_items = []
    
    # Ignora o índice 0 (cabeçalho geral)
    if len(raw_items) > 1:
        for i, item_text in enumerate(raw_items[1:], start=1):
            
            # --- EXTRAÇÃO DE ATRIBUTOS ---
            
            # Identificação
            part_number = extract_field(item_text, r"Código interno\s*([\d\.]+)")
            ncm = extract_field(item_text, r"NCM\s*(\d{4}\.\d{2}\.\d{2})")
            
            # Descrição (Tenta capturar o bloco entre DENOMINACAO e DESCRICAO ou Conhecido)
            descricao = extract_field(item_text, r"DENOMINACAO DO PRODUTO\s*(.*?)\s*DESCRICAO DO PRODUTO", default="")
            if not descricao:
                descricao = extract_field(item_text, r"DENOMINACAO DO PRODUTO\s*(.*?)\s*Conhecido")
            
            # Quantitativos
            qtd = extract_field(item_text, r"Qtde Unid. Comercial\s*([\d\.,]+)")
            peso_liq = extract_field(item_text, r"Peso Líquido \(KG\)\s*([\d\.,]+)")
            
            # Valores Comerciais
            vlr_unit_eur = extract_field(item_text, r"Valor Unit Cond Venda\s*([\d\.,]+)")
            vlr_total_eur = extract_field(item_text, r"Valor Tot. Cond Venda\s*([\d\.,]+)")
            
            # Valor Aduaneiro (Base para impostos) - Ponto crítico
            # Estratégia Dupla: Procura "Local Aduaneiro" (mais preciso no texto) ou "Base de Cálculo" (tabela)
            vlr_aduaneiro = extract_field(item_text, r"Local Aduaneiro\s*\(R\$\)\s*([\d\.,]+)")
            if vlr_aduaneiro == "N/A":
                vlr_aduaneiro = extract_field(item_text, r"Base de Cálculo\s*\(R\$\)\s*([\d\.,]+)")

            # --- IMPOSTOS (Regex busca valor 'A Recolher' dentro do contexto) ---
            
            # II
            ii_val = 0.0
            if "II" in item_text:
                match_ii = re.search(r"II.*?Valor A Recolher \(R\$\)\s*([\d\.,]+)", item_text, re.DOTALL)
                if match_ii: ii_val = clean_currency(match_ii.group(1))

            # IPI
            ipi_val = 0.0
            if "IPI" in item_text:
                match_ipi = re.search(r"IPI.*?Valor A Recolher \(R\$\)\s*([\d\.,]+)", item_text, re.DOTALL)
                if match_ipi: ipi_val = clean_currency(match_ipi.group(1))
            
            # PIS
            pis_val = 0.0
            match_pis = re.search(r"PIS.*?Valor A Recolher \(R\$\)\s*([\d\.,]+)", item_text, re.DOTALL)
            if match_pis: pis_val = clean_currency(match_pis.group(1))
            
            # COFINS
            cofins_val = 0.0
            match_cofins = re.search(r"COFINS.*?Valor A Recolher \(R\$\)\s*([\d\.,]+)", item_text, re.DOTALL)
            if match_cofins: cofins_val = clean_currency(match_cofins.group(1))

            # Montagem do Dicionário
            parsed_items.append({
                "Item": i,
                "Part Number": part_number,
                "NCM": ncm,
                "Descrição": descricao.replace('\n', ' ').strip()[:80], # Limita tamanho
                "Qtd": clean_currency(qtd),
                "Peso Liq (Kg)": clean_currency(peso_liq),
                "Vlr Unit (EUR)": clean_currency(vlr_unit_eur),
                "Vlr Aduaneiro (R$)": clean_currency(vlr_aduaneiro),
                "II (R$)": ii_val,
                "IPI (R$)": ipi_val,
                "PIS (R$)": pis_val,
                "COFINS (R$)": cofins_val,
                "Total Impostos (R$)": ii_val + ipi_val + pis_val + cofins_val
            })

    # Criação do DataFrame
    df = pd.DataFrame(parsed_items)
    
    # Validação de Estrutura (Evita KeyError se o PDF for lido mas nenhum item for achado)
    required_cols = ["Item", "Part Number", "NCM", "Vlr Aduaneiro (R$)", "Total Impostos (R$)"]
    if df.empty:
        return pd.DataFrame(columns=required_cols), processo, importador
        
    return df, processo, importador

# --- FRONTEND (STREAMLIT) ---

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3069/3069172.png", width=80)
    st.header("Importação de DUIMP")
    st.info("Faça o upload do arquivo PDF padrão do Siscomex/DUIMP para gerar o dashboard analítico.")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    st.markdown("---")
    st.caption("v2.1.0 - Layout Padrão APP2")

# Main Content
if not uploaded_file:
    st.title("📊 DUIMP Analytics Dashboard")
    st.markdown("""
    Bem-vindo ao sistema de análise tributária inteligente.
    
    **Funcionalidades:**
    * Extração automática de itens e NCMs.
    * Cálculo consolidado de impostos (II, IPI, PIS, COFINS).
    * Auditoria de Valores Aduaneiros.
    * Exportação para Excel/CSV.
    
    👈 *Comece fazendo o upload do arquivo na barra lateral.*
    """)
    
else:
    with st.spinner("Processando Inteligência de Dados..."):
        try:
            # EXECUÇÃO DA EXTRAÇÃO
            df_result, proc_num, imp_nome = parse_duimp(uploaded_file)
            
            if df_result.empty:
                st.error("❌ Não foi possível identificar itens no documento.")
                st.warning("Verifique se o PDF é um arquivo de texto pesquisável (não imagem escaneada).")
            else:
                # HEADER
                st.success(f"Arquivo processado com sucesso! {len(df_result)} itens identificados.")
                
                # KPIs (Key Performance Indicators)
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                total_aduaneiro = df_result["Vlr Aduaneiro (R$)"].sum()
                total_impostos = df_result["Total Impostos (R$)"].sum()
                total_peso = df_result["Peso Liq (Kg)"].sum()
                tax_rate = (total_impostos / total_aduaneiro * 100) if total_aduaneiro > 0 else 0
                
                kpi1.metric("Processo", proc_num or "N/A")
                kpi2.metric("Valor Aduaneiro Total", f"R$ {total_aduaneiro:,.2f}")
                kpi3.metric("Total Tributos", f"R$ {total_impostos:,.2f}")
                kpi4.metric("Taxa Efetiva (Tax Rate)", f"{tax_rate:.1f}%")

                st.markdown("---")

                # GRÁFICOS (DATA SCIENCE VIEW)
                tab1, tab2 = st.tabs(["📈 Visão Analítica", "📋 Dados Detalhados"])

                with tab1:
                    col_g1, col_g2 = st.columns(2)
                    
                    with col_g1:
                        # Breakdown de Impostos (Donut Chart)
                        taxes = df_result[["II (R$)", "IPI (R$)", "PIS (R$)", "COFINS (R$)"]].sum().reset_index()
                        taxes.columns = ["Tributo", "Valor"]
                        fig_pie = px.pie(taxes, values="Valor", names="Tributo", hole=0.5, 
                                         title="Distribuição da Carga Tributária",
                                         color_discrete_sequence=px.colors.sequential.RdBu)
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    with col_g2:
                        # Top Itens por Custo (Bar Chart)
                        top_items = df_result.nlargest(10, "Total Impostos (R$)")
                        fig_bar = px.bar(top_items, x="Part Number", y=["Vlr Aduaneiro (R$)", "Total Impostos (R$)"],
                                         title="Top Itens por Custo (Aduaneiro vs Imposto)",
                                         barmode="group",
                                         color_discrete_sequence=["#3498db", "#e74c3c"])
                        st.plotly_chart(fig_bar, use_container_width=True)

                with tab2:
                    # TABELA INTERATIVA
                    st.markdown("### Detalhamento Item a Item")
                    
                    # Formatação para exibição
                    st.dataframe(
                        df_result.style.format({
                            "Vlr Unit (EUR)": "€ {:.2f}",
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
                        height=500
                    )
                    
                    # DOWNLOAD
                    csv = df_result.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Relatório CSV",
                        data=csv,
                        file_name=f"DUIMP_{proc_num}_Relatorio.csv",
                        mime="text/csv"
                    )

        except Exception as e:
            st.error(f"Erro crítico no processamento: {str(e)}")
            st.code(str(e)) # Exibe o stack trace para o desenvolvedor
