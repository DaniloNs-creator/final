import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# Configuração da Página para modo "Wide" (melhor para visualizar DataFrames grandes)
st.set_page_config(page_title="Extrator DUIMP Pro", layout="wide", page_icon="📄")

def clean_currency(value_str):
    """
    Converte strings de moeda brasileira (1.000,00) para float (1000.00).
    Retorna 0.0 se falhar.
    """
    if not value_str:
        return 0.0
    try:
        # Remove pontos de milhar e troca vírgula por ponto
        clean_str = value_str.replace('.', '').replace(',', '.')
        return float(clean_str)
    except ValueError:
        return 0.0

def extract_data_from_pdf(uploaded_file):
    """
    Lê o PDF e retorna um dicionário com dados da Capa e um DataFrame com os Itens.
    """
    full_text = ""
    
    # 1. Leitura do PDF
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            # Extraímos o texto mantendo o layout visual aproximado
            text = page.extract_text()
            if text:
                full_text += "\n" + text

    # 2. Limpeza básica (remover cabeçalhos/rodapés repetitivos se necessário)
    # Ex: remover "--- PAGE X ---" para não quebrar lógica
    full_text = re.sub(r'--- PAGE \d+ ---', '', full_text)

    # 3. Extração dos Dados da CAPA (Regex)
    # Procuramos padrões específicos que aparecem no início do arquivo
    capa_data = {}
    
    # Ex: Busca "PROCESSO #28523"
    match_proc = re.search(r'PROCESSO #(\d+)', full_text)
    capa_data['Processo Interno'] = match_proc.group(1) if match_proc else "N/A"

    # Ex: Busca "IMPORTADOR" e pega a linha de baixo ou lado
    # Ajuste o regex conforme a variabilidade do layout
    match_imp = re.search(r'IMPORTADOR\s*[\r\n]+([^\r\n]+)', full_text)
    capa_data['Importador'] = match_imp.group(1).strip() if match_imp else "N/A"
    
    match_duimp = re.search(r'Numero\s*[\r\n]+(\d{2}BR\d+)', full_text)
    capa_data['Número DUIMP'] = match_duimp.group(1) if match_duimp else "N/A"

    # 4. Extração dos ITENS (Loop Principal)
    # O padrão chave é "ITENS DA DUIMP - X"
    # Vamos dividir o texto inteiro usando esse marcador
    # O split vai gerar uma lista onde cada elemento é um bloco de texto de um item
    blocks = re.split(r'ITENS DA DUIMP\s*-\s*\d+', full_text)
    
    # O primeiro bloco (blocks[0]) é a capa, o resto são os itens
    items_list = []
    
    # Iteramos a partir do segundo bloco (índice 1)
    # Nota: Precisamos recuperar o número do item que foi "comido" pelo split se for importante,
    # ou geramos um sequencial.
    
    for i, block in enumerate(blocks[1:], start=1):
        item_dict = {}
        item_dict['Item #'] = i
        
        # Extração de Campos Específicos dentro do bloco do item
        
        # NCM (Ex: NCM 3926.30.00)
        m_ncm = re.search(r'NCM\s+(\d{4}\.\d{2}\.\d{2})', block)
        item_dict['NCM'] = m_ncm.group(1) if m_ncm else ""
        
        # Descrição (Pegamos um trecho, pois pode ser grande)
        # Tentativa de pegar texto logo após "Denominação" ou similar
        # Aqui simplificamos pegando linhas próximas ao NCM
        
        # Valor Aduaneiro (Base para impostos)
        # Procura "Valor Aduaneiro" seguido de um número
        m_vlr = re.search(r'Valor Aduaneiro\s+([\d\.]+,\d{2})', block)
        vlr_aduaneiro = m_vlr.group(1) if m_vlr else "0,00"
        item_dict['Vlr Aduaneiro'] = clean_currency(vlr_aduaneiro)
        
        # Imposto de Importação (II) - Valor Devido
        # Procura por "II" ... "Valor Devido" ... número
        # Regex flexível para pegar a linha do imposto
        # Ajuste conforme layout real: as vezes o valor está na mesma linha ou abaixo
        # Supondo padrão: II <espaços> Base <espaços> Alíquota <espaços> Valor
        m_ii = re.search(r'II.*?([\d\.]+,\d{2})\s*Valor Devido', block, re.DOTALL)
        # Se o layout for tabular, o valor pode estar no final da linha que começa com II
        if not m_ii:
             # Tenta pegar o último número da linha que contém "II" e "%"
             m_ii = re.search(r'II\s+.*?(\d{1,3}(?:\.\d{3})*,\d{2})[^\n]*$', block, re.MULTILINE)
        
        item_dict['II Devido'] = clean_currency(m_ii.group(1)) if m_ii else 0.0

        # PIS e COFINS (Lógica similar)
        m_pis = re.search(r'PIS\s+.*?(\d{1,3}(?:\.\d{3})*,\d{2})[^\n]*$', block, re.MULTILINE)
        item_dict['PIS Devido'] = clean_currency(m_pis.group(1)) if m_pis else 0.0
        
        m_cofins = re.search(r'COFINS\s+.*?(\d{1,3}(?:\.\d{3})*,\d{2})[^\n]*$', block, re.MULTILINE)
        item_dict['COFINS Devido'] = clean_currency(m_cofins.group(1)) if m_cofins else 0.0
        
        items_list.append(item_dict)

    df_items = pd.DataFrame(items_list)
    return capa_data, df_items

# --- INTERFACE GRÁFICA (FRONTEND) ---

st.title("📊 Extrator de DUIMPs - Análise Fiscal")
st.markdown("""
<style>
    .big-font { font-size:18px !important; }
</style>
<div class='big-font'>
    Ferramenta profissional para extração de dados do PDF padrão de Desembaraço Aduaneiro.
    Faça upload do arquivo para visualizar o Resumo e o Detalhamento por Item.
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Arraste seu PDF aqui (Layout Padrão)", type="pdf")

if uploaded_file is not None:
    with st.spinner('Lendo e processando o PDF...'):
        try:
            # Processamento
            header_info, df_resultado = extract_data_from_pdf(uploaded_file)
            
            # --- SEÇÃO 1: CABEÇALHO ---
            st.divider()
            st.subheader("📁 Dados do Processo (Capa)")
            
            # Layout em Colunas para ficar bonito (Card-like metrics)
            col1, col2, col3 = st.columns(3)
            col1.metric("Processo Interno", header_info.get('Processo Interno', '-'))
            col2.metric("Número DUIMP", header_info.get('Número DUIMP', '-'))
            col3.metric("Importador", header_info.get('Importador', '-')[:20] + "...") # Trunca se for longo

            # --- SEÇÃO 2: TABELA DE ITENS ---
            st.divider()
            st.subheader(f"📦 Detalhamento dos Itens ({len(df_resultado)} encontrados)")
            
            # Formatação do DataFrame para exibição (R$)
            st.dataframe(
                df_resultado,
                column_config={
                    "Vlr Aduaneiro": st.column_config.NumberColumn("Vlr Aduaneiro (R$)", format="R$ %.2f"),
                    "II Devido": st.column_config.NumberColumn("II (R$)", format="R$ %.2f"),
                    "PIS Devido": st.column_config.NumberColumn("PIS (R$)", format="R$ %.2f"),
                    "COFINS Devido": st.column_config.NumberColumn("COFINS (R$)", format="R$ %.2f"),
                },
                use_container_width=True,
                hide_index=True
            )

            # --- SEÇÃO 3: DOWNLOAD ---
            st.divider()
            col_d1, col_d2 = st.columns([1, 4])
            
            # Botão para baixar CSV
            csv = df_resultado.to_csv(index=False, sep=';', decimal=',')
            col_d1.download_button(
                label="💾 Baixar Excel/CSV",
                data=csv,
                file_name=f"duimp_{header_info.get('Processo Interno')}.csv",
                mime='text/csv',
            )
            
            # Análise Rápida (Totalizadores)
            total_aduaneiro = df_resultado['Vlr Aduaneiro'].sum()
            total_impostos = df_resultado['II Devido'].sum() + df_resultado['PIS Devido'].sum() + df_resultado['COFINS Devido'].sum()
            
            st.info(f"💰 **Total Aduaneiro Processado:** R$ {total_aduaneiro:,.2f} | **Total Impostos (Estimado):** R$ {total_impostos:,.2f}")

        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
            st.warning("Verifique se o PDF segue o layout padrão esperado.")

else:
    st.info("Aguardando upload do arquivo...")

# Rodapé profissional
st.markdown("---")
st.caption("Desenvolvido para automação fiscal via Python & Streamlit.")
