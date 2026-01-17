import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Raio-X DUIMP: Análise Completa",
    layout="wide",
    page_icon="🕵️‍♂️",
    initial_sidebar_state="collapsed"
)

# --- CSS CUSTOMIZADO PARA ESTILO "FISCAL" ---
st.markdown("""
    <style>
    .metric-card {background-color: #f0f2f6; border-radius: 10px; padding: 15px; margin: 5px;}
    .tax-alert {color: #d63031; font-weight: bold;}
    .fiscal-header {font-size: 20px; font-weight: bold; color: #0984e3; border-bottom: 2px solid #0984e3; padding-bottom: 5px; margin-top: 20px;}
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE ENGENHARIA DE DADOS ---

def clean_decimal(value_str):
    """Converte padrão brasileiro 1.000,00 para float 1000.00 de forma robusta."""
    if not value_str: return 0.0
    try:
        # Remove tudo que não é dígito ou vírgula/ponto
        clean = re.sub(r'[^\d,.-]', '', str(value_str))
        # Se tiver ponto como milhar e vírgula como decimal
        if ',' in clean and '.' in clean:
            clean = clean.replace('.', '').replace(',', '.')
        elif ',' in clean:
             clean = clean.replace(',', '.')
        return float(clean)
    except:
        return 0.0

def extract_regex(pattern, text, default="-"):
    """Busca segura com Regex retornando padrão se falhar."""
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip().replace('\n', ' ')
    return default

def parse_full_pdf(uploaded_file):
    """
    Motor de Extração Principal.
    Lê o PDF inteiro como um fluxo de texto contínuo para evitar quebras de página.
    """
    full_text = ""
    
    # 1. Leitura do PDF
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            # density=True ajuda a manter o layout visual
            text = page.extract_text(x_tolerance=1, y_tolerance=1) 
            if text:
                full_text += f"\n{text}"
    
    # 2. Pré-processamento (Limpeza de Artefatos)
    # Remove rodapés/cabeçalhos de página que quebram tabelas (ex: "--- PAGE 10 ---")
    clean_text = re.sub(r'--- PAGE \d+ ---', '', full_text)
    
    # 3. Extração da CAPA (Dados Gerais)
    # Procuramos padrões globais no início do arquivo
    metadata = {
        "processo_interno": extract_regex(r'PROCESSO\s*#?\s*([\w\d]+)', clean_text),
        "importador": extract_regex(r'IMPORTADOR\s*[\r\n]+([^\r\n]+)', clean_text),
        "cnpj": extract_regex(r'CNPJ\s*[\r\n]+([\d\./-]+)', clean_text),
        "duimp_numero": extract_regex(r'Numero\s*[\r\n]+(\d{2}BR\d+)', clean_text),
        "duimp_versao": extract_regex(r'Versao\s*[\r\n]+(\d+)', clean_text),
        "data_registro": extract_regex(r'Data Registro\s*[\r\n]+(\d{2}/\d{2}/\d{4})', clean_text),
        "canal": extract_regex(r'Canal\s*[\r\n]+([^\r\n]*)', clean_text),
        "tipo_declaracao": extract_regex(r'Tipo\s*[\r\n]+([^\r\n]+)', clean_text),
        "cotacao_dolar": clean_decimal(extract_regex(r'COTACAO DO DOLAR.*?([\d,]+)', clean_text, "0")),
        "cotacao_euro": clean_decimal(extract_regex(r'COTACAO DA MOEDA NEGOCIADA.*?([\d,]+)', clean_text, "0")),
        "peso_bruto_total": clean_decimal(extract_regex(r'PESO BRUTO KG\s*[\r\n]+([\d\.,]+)', clean_text)),
        "peso_liquido_total": clean_decimal(extract_regex(r'PESO LIQUIDO KG\s*[\r\n]+([\d\.,]+)', clean_text)),
        "via_transporte": extract_regex(r'VIA DE TRANSPORTE\s*[\r\n]+([^\r\n]+)', clean_text),
        "local_desembaraco": extract_regex(r'UNIDADE DE DESPACHO\s*[\r\n]+([^\r\n]+)', clean_text)
    }

    # 4. Extração dos ITENS (Deep Dive)
    # A estratégia é dividir o texto pelos blocos "ITENS DA DUIMP - X"
    # O regex (?=...) garante que não cortaremos o cabeçalho do próximo item
    item_blocks = re.split(r'(?=ITENS DA DUIMP\s*-\s*\d+)', clean_text)
    
    items_data = []
    
    # Ignora o primeiro bloco (índice 0) pois é o cabeçalho geral antes do primeiro item
    for block in item_blocks:
        if "ITENS DA DUIMP" not in block:
            continue
            
        item = {}
        
        # Identificadores
        item['Item'] = extract_regex(r'ITENS DA DUIMP\s*-\s*(\d+)', block)
        item['Adição'] = extract_regex(r'Adição\s*(\d+)', block) # Se houver conceito de adição
        item['NCM'] = extract_regex(r'NCM\s+([\d\.]+)', block)
        item['Código Produto'] = extract_regex(r'Codigo Produto\s+(\d+)', block)
        item['Partnumber'] = extract_regex(r'CÓDIGO INTERNO\s*[\r\n]+([^\r\n]+)', block)
        
        # Descrição (Tentativa de pegar o bloco de texto maior)
        desc = extract_regex(r'DENOMINACAO DO PRODUTO(.*?)(?:CÓDIGO INTERNO|FABRICANTE)', block)
        item['Descrição'] = desc[:300].strip() + "..." if len(desc) > 300 else desc.strip()
        
        # Atores
        item['Fabricante'] = extract_regex(r'FABRICANTE/PRODUTOR\s*[\r\n]+([^\r\n]+)', block)
        item['Exportador'] = extract_regex(r'EXPORTADOR ESTRANGEIRO\s*[\r\n]+([^\r\n]+)', block)
        item['País Origem'] = extract_regex(r'Pais Origem\s*[\r\n]+([^\r\n]+)', block)
        
        # Quantitativos
        item['Qtd Comercial'] = clean_decimal(extract_regex(r'Qtde Unid\. Comercial\s*[\r\n]+([\d\.,]+)', block))
        item['Unid Comercial'] = extract_regex(r'Unidade Comercial\s*[\r\n]+([A-Z]+)', block)
        item['Qtd Estatística'] = clean_decimal(extract_regex(r'Qtde Unid\. Estatistica\s*[\r\n]+([\d\.,]+)', block))
        item['Peso Líquido'] = clean_decimal(extract_regex(r'Peso Líquido \(KG\)\s*[\r\n]+([\d\.,]+)', block))
        
        # Valores Monetários
        item['INCOTERM'] = extract_regex(r'Condição de Venda\s*[\r\n]+([A-Z]+)', block)
        item['Vlr Unitário'] = clean_decimal(extract_regex(r'Valor Unit Cond Venda\s*[\r\n]+([\d\.,]+)', block))
        item['Vlr Aduaneiro'] = clean_decimal(extract_regex(r'Local Aduaneiro \(R\$\)\s*[\r\n]+([\d\.,]+)', block))
        item['Frete Rateado'] = clean_decimal(extract_regex(r'Frete Internac\. \(R\$\)\s*[\r\n]+([\d\.,]+)', block))
        item['Seguro Rateado'] = clean_decimal(extract_regex(r'Seguro Internac\. \(R\$\)\s*[\r\n]+([\d\.,]+)', block))

        # --- TRIBUTAÇÃO DETALHADA (Here be dragons) ---
        # A lógica é buscar a seção específica de cada imposto para evitar falsos positivos
        
        # II (Imposto de Importação)
        ii_chunk = extract_regex(r'(II\s.*?)(?:IPI|PIS|COFINS)', block)
        item['II Base'] = clean_decimal(extract_regex(r'Base de Cálculo \(R\$\)\s*([\d\.,]+)', ii_chunk))
        item['II Alíquota'] = clean_decimal(extract_regex(r'% Alíquota\s*([\d\.,]+)', ii_chunk))
        item['II Devido'] = clean_decimal(extract_regex(r'(?:Valor A Recolher|Valor Devido) \(R\$\)\s*([\d\.,]+)', ii_chunk))
        item['II Regime'] = extract_regex(r'Regime de Tributacao\s*([^\r\n]+)', ii_chunk)

        # IPI
        ipi_chunk = extract_regex(r'(IPI\s.*?)(?:PIS|COFINS|ICMS)', block)
        item['IPI Base'] = clean_decimal(extract_regex(r'Base de Cálculo \(R\$\)\s*([\d\.,]+)', ipi_chunk))
        item['IPI Alíquota'] = clean_decimal(extract_regex(r'% Alíquota\s*([\d\.,]+)', ipi_chunk))
        item['IPI Devido'] = clean_decimal(extract_regex(r'(?:Valor A Recolher|Valor Devido) \(R\$\)\s*([\d\.,]+)', ipi_chunk))

        # PIS
        pis_chunk = extract_regex(r'(PIS\s.*?)(?:COFINS|ICMS)', block)
        item['PIS Devido'] = clean_decimal(extract_regex(r'(?:Valor A Recolher|Valor Devido) \(R\$\)\s*([\d\.,]+)', pis_chunk))
        
        # COFINS
        cofins_chunk = extract_regex(r'(COFINS\s.*?)(?:ICMS|TOTAL)', block)
        item['COFINS Devido'] = clean_decimal(extract_regex(r'(?:Valor A Recolher|Valor Devido) \(R\$\)\s*([\d\.,]+)', cofins_chunk))

        # ICMS (Geralmente no final)
        icms_chunk = extract_regex(r'(ICMS\s.*?)(?:ITENS DA DUIMP|$)', block)
        item['ICMS Base'] = clean_decimal(extract_regex(r'Base de Cálculo \(R\$\)\s*([\d\.,]+)', icms_chunk))
        item['ICMS Alíquota'] = clean_decimal(extract_regex(r'% Alíquota\s*([\d\.,]+)', icms_chunk))
        item['ICMS Devido'] = clean_decimal(extract_regex(r'Valor A Recolher.*?([\d\.,]+)', icms_chunk))
        
        items_data.append(item)

    return metadata, pd.DataFrame(items_data), clean_text

# --- LAYOUT DO APLICATIVO ---

st.title("📑 DUIMP ANALYZER PRO v2.0")
st.markdown("**Ferramenta de Auditoria e Extração de Dados Aduaneiros**")

uploaded_file = st.file_uploader("Arraste o PDF da DUIMP aqui", type='pdf')

if uploaded_file:
    with st.spinner("Decodificando estrutura do PDF..."):
        meta, df, raw_text = parse_full_pdf(uploaded_file)
        
        # === 1. CAPA DO PROCESSO ===
        st.markdown('<div class="fiscal-header">1. Dados do Processo (Capa)</div>', unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.info(f"**Importador:**\n{meta['importador']}")
        c2.info(f"**DUIMP:**\n{meta['duimp_numero']}")
        c3.info(f"**Processo:**\n{meta['processo_interno']}")
        c4.info(f"**Data:**\n{meta['data_registro']}")

        with st.expander("🔍 Ver Detalhes Logísticos e Cambiais"):
            lc1, lc2, lc3, lc4 = st.columns(4)
            lc1.metric("Peso Bruto", f"{meta['peso_bruto_total']:,.2f} kg")
            lc2.metric("Peso Líquido", f"{meta['peso_liquido_total']:,.2f} kg")
            lc3.metric("Cotação USD", f"R$ {meta['cotacao_dolar']:,.4f}")
            lc4.metric("Cotação EUR", f"R$ {meta['cotacao_euro']:,.4f}")
            st.text(f"Via: {meta['via_transporte']} | Local: {meta['local_desembaraco']}")

        # === 2. KPI FINANCEIRO ===
        st.markdown('<div class="fiscal-header">2. Resumo Tributário (Simulação)</div>', unsafe_allow_html=True)
        
        if not df.empty:
            tot_aduana = df['Vlr Aduaneiro'].sum()
            tot_ii = df['II Devido'].sum()
            tot_ipi = df['IPI Devido'].sum()
            tot_pis = df['PIS Devido'].sum()
            tot_cofins = df['COFINS Devido'].sum()
            
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Total Aduaneiro", f"R$ {tot_aduana:,.2f}", delta="Base Cálculo")
            k2.metric("Total II", f"R$ {tot_ii:,.2f}", delta_color="inverse")
            k3.metric("Total IPI", f"R$ {tot_ipi:,.2f}", delta_color="inverse")
            k4.metric("Total PIS/COFINS", f"R$ {tot_pis + tot_cofins:,.2f}", delta_color="inverse")
            k5.metric("Total Tributos", f"R$ {tot_ii+tot_ipi+tot_pis+tot_cofins:,.2f}", delta_color="inverse")

        # === 3. TABELA DE ITENS (O CORAÇÃO DO SISTEMA) ===
        st.markdown('<div class="fiscal-header">3. Detalhamento dos Itens</div>', unsafe_allow_html=True)
        
        # Filtros Inteligentes
        cols_filter = st.columns([1,1,2])
        with cols_filter[0]:
            filtro_ncm = st.multiselect("Filtrar por NCM:", options=df['NCM'].unique())
        with cols_filter[1]:
            filtro_fab = st.multiselect("Filtrar por Fabricante:", options=df['Fabricante'].unique())
            
        df_show = df.copy()
        if filtro_ncm:
            df_show = df_show[df_show['NCM'].isin(filtro_ncm)]
        if filtro_fab:
            df_show = df_show[df_show['Fabricante'].isin(filtro_fab)]
            
        st.dataframe(
            df_show,
            use_container_width=True,
            column_config={
                "Vlr Aduaneiro": st.column_config.NumberColumn(format="R$ %.2f"),
                "II Devido": st.column_config.NumberColumn(format="R$ %.2f"),
                "IPI Devido": st.column_config.NumberColumn(format="R$ %.2f"),
                "PIS Devido": st.column_config.NumberColumn(format="R$ %.2f"),
                "COFINS Devido": st.column_config.NumberColumn(format="R$ %.2f"),
                "Descrição": st.column_config.TextColumn(width="medium"),
            }
        )
        
        # === 4. EXPORTAÇÃO E DEBUG ===
        st.divider()
        c_down, c_debug = st.columns([1,1])
        
        with c_down:
            st.subheader("📥 Exportar Dados")
            csv = df.to_csv(sep=';', decimal=',', index=False).encode('utf-8-sig')
            st.download_button(
                "Baixar Planilha Completa (Excel/CSV)",
                data=csv,
                file_name=f"DUIMP_FULL_{meta['processo_interno']}.csv",
                mime="text/csv",
                type="primary"
            )

        with c_debug:
            st.subheader("🛠️ Área do Desenvolvedor")
            with st.expander("Ver Texto Bruto do PDF (Debug)"):
                st.text_area("Conteúdo extraído pelo Python:", raw_text, height=300)
                st.caption("Use este texto para ajustar as Expressões Regulares (Regex) se o layout mudar.")

else:
    st.info("👆 Faça o upload do PDF padrão da DUIMP para começar a análise.")
