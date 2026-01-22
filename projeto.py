import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# Configuração da Página
st.set_page_config(page_title="Extrator DUIMP - Fiscal", layout="wide")

def limpar_numero(valor_str):
    """Converte string '1.234,56' para float 1234.56"""
    if not valor_str:
        return 0.0
    # Remove pontos de milhar e troca vírgula por ponto
    limpo = valor_str.replace('.', '').replace(',', '.')
    try:
        return float(limpo)
    except ValueError:
        return 0.0

def extrair_dados_pdf(pdf_file):
    items_data = []
    
    with pdfplumber.open(pdf_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # 1. Extração de Cabeçalho (Dados Gerais)
    # Tenta encontrar o número do processo e importador
    processo_match = re.search(r'PROCESSO #\s*(\d+)', full_text)
    processo = processo_match.group(1) if processo_match else "N/A"
    
    importador_match = re.search(r'IMPORTADOR\s*\n\s*"(.*?)"', full_text, re.IGNORECASE)
    # Se não achar com as aspas (dependendo da formatação), tenta pegar a linha
    if not importador_match:
        importador_match = re.search(r'IMPORTADOR\s*\n\s*(.*)', full_text, re.IGNORECASE)
    importador = importador_match.group(1).strip() if importador_match else "HAFELE BRASIL" # Fallback baseado no padrão

    # 2. Separar os Itens
    # O padrão do PDF parece dividir itens por "ITENS DA DUIMP-XXXXX"
    # Usamos re.split para quebrar o texto em blocos, um para cada item
    blocos = re.split(r'ITENS DA DUIMP-\d+', full_text)
    
    # O primeiro bloco (índice 0) é o cabeçalho antes do item 1, ignoramos no loop de itens
    for i, bloco in enumerate(blocos[1:], start=1):
        item = {}
        item['Item'] = i
        item['Processo'] = processo
        item['Importador'] = importador
        
        # --- Extração de Campos Específicos com Regex ---
        
        # Código Interno (Part Number)
        # Procura padrão XXX.XX.XXX típico da Hafele
        codigo_match = re.search(r'Código interno\s*[\n\r]*(\d{3}\.\d{2}\.\d{3})', bloco)
        item['Código'] = codigo_match.group(1) if codigo_match else "N/A"
        
        # NCM
        ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', bloco) # Procura formato de NCM
        item['NCM'] = ncm_match.group(1) if ncm_match else "N/A"
        
        # Descrição (Pega o texto entre DENOMINACAO e DESCRICAO ou similar)
        desc_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n(.*?)\n', bloco)
        item['Descrição'] = desc_match.group(1).strip() if desc_match else "N/A"
        
        # Quantidade Comercial
        qtd_match = re.search(r'Qtde Unid\. Comercial\s*\n\s*"([\d,]+)', bloco)
        if not qtd_match: # Tenta outro padrão
             qtd_match = re.search(r'Qtde Unid\. Comercial\s*([\d,]+)', bloco)
        item['Qtd.'] = qtd_match.group(1) if qtd_match else "0"

        # Valor Total (Euro)
        vlr_eur_match = re.search(r'Valor Tot\. Cond Venda\s*\n\s*"([\d,]+)', bloco)
        item['Valor (EUR)'] = vlr_eur_match.group(1) if vlr_eur_match else "0,00"
        
        # --- Tributos (Lógica Heurística) ---
        # A DUIMP lista vários tributos. Vamos tentar pegar a Base de Cálculo do II (primeira que aparece)
        # e os valores a recolher.
        
        # Base de Cálculo (Geralmente a primeira base grande em R$ no bloco do item)
        base_calc_match = re.search(r'Base de Cálculo \(R\$\)\s*\n\s*"([\d\.,]+)', bloco)
        item['Base Calc. (R$)'] = base_calc_match.group(1) if base_calc_match else "0,00"
        
        # II (Imposto de Importação) - Valor a Recolher
        # Procuramos "II" seguido eventualmente de "Valor A Recolher"
        # Simplificação: Procurar padrões numéricos próximos às chaves de tributos
        
        # Esta parte é complexa em texto puro. Vou usar uma busca sequencial simples para o exemplo:
        vals = re.findall(r'Valor A Recolher \(R\$\)\s*\n\s*"([\d\.,]+)', bloco)
        
        # Assumindo a ordem padrão da DUIMP (II, IPI, PIS, COFINS) que aparece no texto
        item['II (R$)'] = vals[0] if len(vals) > 0 else "0,00"
        item['PIS (R$)'] = vals[1] if len(vals) > 1 else "0,00" # PIS costuma vir depois
        item['COFINS (R$)'] = vals[2] if len(vals) > 2 else "0,00"
        
        items_data.append(item)

    return pd.DataFrame(items_data)

# --- Interface Streamlit ---

st.title("📂 Extrator de DUIMP para DataFrame")
st.markdown("""
Esta ferramenta transforma o PDF padrão da DUIMP em uma tabela Excel.
**Ideal para conferência fiscal e importação no sistema.**
""")

uploaded_file = st.file_uploader("Arraste seu PDF aqui", type="pdf")

if uploaded_file is not None:
    with st.spinner('Lendo PDF e extraindo dados fiscais...'):
        try:
            # Processa o PDF
            df = extrair_dados_pdf(uploaded_file)
            
            # Exibe Métricas
            total_eur = sum([limpar_numero(x) for x in df['Valor (EUR)']])
            total_base = sum([limpar_numero(x) for x in df['Base Calc. (R$)']])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Itens", len(df))
            col2.metric("Valor Total (EUR)", f"€ {total_eur:,.2f}")
            col3.metric("Base de Cálculo Total", f"R$ {total_base:,.2f}")

            # Mostra Tabela
            st.subheader("Visualização dos Dados")
            st.dataframe(df, use_container_width=True)
            
            # Botão de Download
            csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            
            st.download_button(
                label="📥 Baixar Tabela em CSV (Excel)",
                data=csv,
                file_name=f"DUIMP_Extraida.csv",
                mime="text/csv",
            )
            
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
            st.warning("Verifique se o PDF não é uma imagem escaneada. O arquivo precisa ter texto selecionável.")

else:
    st.info("Aguardando upload do arquivo...")
