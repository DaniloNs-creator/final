import streamlit as st
import pdfplumber
import pandas as pd
import re

st.set_page_config(page_title="Auditoria DUIMP - Tributos", layout="wide")

def limpar_valor(valor_str):
    """Converte string '1.234,56' para float 1234.56"""
    if not valor_str: return 0.0
    return float(valor_str.replace('.', '').replace(',', '.'))

def extrair_tributos(pdf_file):
    dados_fiscais = []
    
    with pdfplumber.open(pdf_file) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    # Quebra o texto por itens da DUIMP
    blocos = re.split(r'ITENS DA DUIMP-\d+', texto_completo)
    
    # Ignora o primeiro bloco (cabeçalho geral)
    for i, bloco in enumerate(blocos[1:], start=1):
        item = {'Item': i}
        
        # 1. NCM
        ncm_match = re.search(r'NCM\s*\n\s*(\d{4}\.\d{2}\.\d{2})', bloco)
        if not ncm_match: # Tenta sem quebra de linha
            ncm_match = re.search(r'NCM\s*(\d{4}\.\d{2}\.\d{2})', bloco)
        item['NCM'] = ncm_match.group(1) if ncm_match else "N/A"

        # 2. VALOR ADUANEIRO (Base de Cálculo do II)
        # Procuramos a primeira "Base de Cálculo" que aparece logo após "II" ou "ALÍQUOTA TEC"
        # Regex captura o valor numérico associado à Base de Cálculo
        base_ii_match = re.search(r'Base de Cálculo \(R\$\)\s*\n\s*"([\d\.,]+)', bloco)
        item['Valor Aduaneiro (R$)'] = base_ii_match.group(1) if base_ii_match else "0,00"

        # 3. IMPOSTO DE IMPORTAÇÃO (II)
        # Geralmente associado à alíquota de 16% (neste caso) ou busca por "Valor A Recolher" no primeiro bloco tributário
        # Estratégia: Pegar o valor calculado próximo à alíquota do II (TEC)
        ii_match = re.search(r'Valor A Recolher \(R\$\)\s*\n\s*"([\d\.,]+)', bloco)
        item['II (R$)'] = ii_match.group(1) if ii_match else "0,00"

        # 4. PIS e COFINS (Busca por Alíquota para garantir precisão)
        # PIS geralmente é 2.10% e COFINS 9.65% na importação direta
        
        # PIS (Busca bloco com alíquota 2,1)
        pis_match = re.search(r'%\s*Alíquota\s*\n\s*"2,1000000".*?Valor A Recolher \(R\$\)\s*\n\s*"([\d\.,]+)', bloco, re.DOTALL)
        item['PIS (R$)'] = pis_match.group(1) if pis_match else "0,00"
        
        # COFINS (Busca bloco com alíquota 9,65)
        cofins_match = re.search(r'%\s*Alíquota\s*\n\s*"9,6500000".*?Valor A Recolher \(R\$\)\s*\n\s*"([\d\.,]+)', bloco, re.DOTALL)
        item['COFINS (R$)'] = cofins_match.group(1) if cofins_match else "0,00"
        
        # IPI (Geralmente zerado ou específico)
        # Se não achar alíquota específica, assume 0,00 ou busca campo IPI
        ipi_match = re.search(r'IPI.*?Valor A Recolher \(R\$\)\s*\n\s*"([\d\.,]+)', bloco, re.DOTALL)
        item['IPI (R$)'] = ipi_match.group(1) if ipi_match and "0,00" not in ipi_match.group(1) else "0,00"

        # Calcula Total Tributos Item
        total = limpar_valor(item['II (R$)']) + limpar_valor(item['PIS (R$)']) + \
                limpar_valor(item['COFINS (R$)']) + limpar_valor(item['IPI (R$)'])
        item['Total Tributos (R$)'] = f"{total:,.2f}".replace('.', 'v').replace(',', '.').replace('v', ',')

        dados_fiscais.append(item)

    return pd.DataFrame(dados_fiscais)

# --- Interface ---
st.title("⚖️ Extrator Fiscal DUIMP")
st.markdown("Extração exclusiva de **Valor Aduaneiro** e **Tributos (II, PIS, COFINS, IPI)**.")

arquivo = st.file_uploader("Upload DUIMP (PDF)", type="pdf")

if arquivo:
    df = extrair_tributos(arquivo)
    
    # Formatação para exibição (Totais)
    v_aduaneiro_total = sum([limpar_valor(x) for x in df['Valor Aduaneiro (R$)']])
    impostos_total = sum([limpar_valor(x) for x in df['Total Tributos (R$)']])
    
    c1, c2 = st.columns(2)
    c1.metric("Valor Aduaneiro Total", f"R$ {v_aduaneiro_total:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    c2.metric("Total Tributos Recuperados", f"R$ {impostos_total:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    
    st.dataframe(df, use_container_width=True)
    
    # Download
    csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
    st.download_button("Baixar CSV Fiscal", csv, "duimp_fiscal.csv", "text/csv")
