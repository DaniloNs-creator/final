import streamlit as st
import pdfplumber
import pandas as pd
import re

st.set_page_config(page_title="Auditoria DUIMP - Tributos", layout="wide")

def limpar_valor(valor_str):
    """Converte string '1.234,56' para float 1234.56. Retorna 0.0 se vazio/nulo."""
    if not valor_str or not isinstance(valor_str, str): 
        return 0.0
    # Remove qualquer coisa que não seja dígito, vírgula ou ponto (ex: espaços)
    valor_limpo = re.sub(r'[^\d,\.]', '', valor_str)
    try:
        return float(valor_limpo.replace('.', '').replace(',', '.'))
    except ValueError:
        return 0.0

def extrair_tributos(pdf_file):
    dados_fiscais = []
    
    with pdfplumber.open(pdf_file) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            # layout=True ajuda a manter a estrutura visual da tabela
            texto_completo += page.extract_text(layout=True) + "\n"

    # Regex ajustado: \s+ significa "um ou mais espaços/quebras de linha"
    # Isso previne erros se o PDF quebrar "DUIMP" para a linha de baixo
    blocos = re.split(r'ITENS\s+DA\s+DUIMP\s*[-\s]*\d+', texto_completo, flags=re.IGNORECASE)
    
    # Ignora o primeiro bloco (cabeçalho geral antes do item 1)
    for i, bloco in enumerate(blocos[1:], start=1):
        item = {'Item': i}
        
        # 1. NCM
        ncm_match = re.search(r'NCM\s*[:\n]?\s*(\d{4}\.\d{2}\.\d{2})', bloco)
        item['NCM'] = ncm_match.group(1) if ncm_match else "N/A"

        # 2. VALOR ADUANEIRO (Base de Cálculo do II)
        # Procuramos o padrão numérico logo após "Base de Cálculo"
        base_ii_match = re.search(r'Base de Cálculo \(R\$\)\s*\n*\s*([\d\.,]+)', bloco)
        item['Valor Aduaneiro (R$)'] = base_ii_match.group(1) if base_ii_match else "0,00"

        # 3. IMPOSTO DE IMPORTAÇÃO (II) - Valor A Recolher
        # Busca "Valor A Recolher" associado ao contexto de alíquota (geralmente 16% ou próximo ao inicio)
        # Simplificação: Pega o primeiro "Valor A Recolher" que aparece no bloco, que na ordem da DUIMP costuma ser II
        recolher_matches = re.findall(r'Valor A Recolher \(R\$\)\s*\n*\s*([\d\.,]+)', bloco)
        
        # Lógica posicional baseada no padrão do PDF (II -> PIS -> COFINS)
        # Se houver menos matches que o esperado, preenche com 0,00
        item['II (R$)'] = recolher_matches[0] if len(recolher_matches) > 0 else "0,00"
        
        # Tenta achar PIS/COFINS por alíquota para ser mais preciso, senão vai pela ordem
        pis_match = re.search(r'%\s*Alíquota\s*[\n\r]*.*2,10.*[\n\r]*.*?Valor A Recolher \(R\$\)\s*\n*\s*([\d\.,]+)', bloco, re.DOTALL)
        item['PIS (R$)'] = pis_match.group(1) if pis_match else (recolher_matches[1] if len(recolher_matches) > 1 else "0,00")
        
        cofins_match = re.search(r'%\s*Alíquota\s*[\n\r]*.*9,65.*[\n\r]*.*?Valor A Recolher \(R\$\)\s*\n*\s*([\d\.,]+)', bloco, re.DOTALL)
        item['COFINS (R$)'] = cofins_match.group(1) if cofins_match else (recolher_matches[2] if len(recolher_matches) > 2 else "0,00")
        
        item['IPI (R$)'] = "0,00" # Assume zero se não achar lógica específica

        # Calcula Total
        total = limpar_valor(item['II (R$)']) + limpar_valor(item['PIS (R$)']) + \
                limpar_valor(item['COFINS (R$)']) + limpar_valor(item['IPI (R$)'])
        item['Total Tributos (R$)'] = f"{total:,.2f}".replace('.', 'v').replace(',', '.').replace('v', ',')

        dados_fiscais.append(item)

    # CORREÇÃO PRINCIPAL: Definir colunas explicitamente
    cols = ['Item', 'NCM', 'Valor Aduaneiro (R$)', 'II (R$)', 'PIS (R$)', 'COFINS (R$)', 'IPI (R$)', 'Total Tributos (R$)']
    return pd.DataFrame(dados_fiscais, columns=cols)

# --- Interface ---
st.title("⚖️ Extrator Fiscal DUIMP")
st.markdown("Extração exclusiva de **Valor Aduaneiro** e **Tributos**.")

arquivo = st.file_uploader("Upload DUIMP (PDF)", type="pdf")

if arquivo:
    with st.spinner("Processando documento..."):
        df = extrair_tributos(arquivo)
        
        # VERIFICAÇÃO DE SEGURANÇA
        if not df.empty and df['NCM'].iloc[0] != "N/A": 
            # Cálculos
            v_aduaneiro_total = sum([limpar_valor(x) for x in df['Valor Aduaneiro (R$)']])
            impostos_total = sum([limpar_valor(x) for x in df['Total Tributos (R$)']])
            
            c1, c2 = st.columns(2)
            c1.metric("Valor Aduaneiro Total", f"R$ {v_aduaneiro_total:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
            c2.metric("Total Tributos a Recolher", f"R$ {impostos_total:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
            
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button("Baixar CSV Fiscal", csv, "duimp_fiscal.csv", "text/csv")
        
        else:
            st.warning("⚠️ Não foi possível identificar os itens automaticamente.")
            st.info("Dica: Verifique se o PDF é um arquivo de texto selecionável (não escaneado) ou se o layout mudou.")
            # Debug: Mostra o que foi lido para ajudar a entender o erro
            with st.expander("Ver texto extraído (Debug)"):
                with pdfplumber.open(arquivo) as pdf:
                    st.text(pdf.pages[0].extract_text()[:1000])
