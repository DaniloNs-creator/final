import streamlit as st
import pdfplumber
import re
import pandas as pd

def extrair_dados_duimp(pdf_file):
    dados_itens = []
    
    with pdfplumber.open(pdf_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # 1. Separar o texto por Itens (A DUIMP separa itens por "ITENS DA DUIMP-")
    # O padrão parece ser "ITENS DA DUIMP-00001", "ITENS DA DUIMP-00002", etc.
    itens_raw = re.split(r'ITENS DA DUIMP-\d+', full_text)
    
    # O primeiro elemento geralmente é o cabeçalho geral, então pulamos se não tiver dados de item
    for i, texto_item in enumerate(itens_raw[1:], start=1):
        item_data = {'Item': i}
        
        # --- EXTRAÇÃO DE VALORES LOGÍSTICOS (VMLD, Frete, Seguro) ---
        # Regex procura: "Texto Chave" seguido de espaço e números (com pontos e vírgulas)
        
        # VMLD (Local Aduaneiro)
        vmld_match = re.search(r'Local Aduaneiro \(R\$\)\s*([\d\.]+,\d+)', texto_item)
        item_data['VMLD (R$)'] = vmld_match.group(1) if vmld_match else "0,00"
        
        # Frete Internacional
        frete_match = re.search(r'Frete Internac\. \(R\$\)\s*([\d\.]+,\d+)', texto_item)
        item_data['Frete (R$)'] = frete_match.group(1) if frete_match else "0,00"
        
        # Seguro Internacional
        seguro_match = re.search(r'Seguro Internac\. \(R\$\)\s*([\d\.]+,\d+)', texto_item)
        item_data['Seguro (R$)'] = seguro_match.group(1) if seguro_match else "0,00"

        # --- EXTRAÇÃO DOS TRIBUTOS (II, IPI, PIS, COFINS) ---
        # A lógica aqui é achar o bloco do imposto e pegar o "Valor Devido" ou "A Recolher" logo abaixo
        
        # Função auxiliar para pegar imposto dentro do texto do item
        def pegar_imposto(nome_imposto, texto):
            # Procura a palavra do imposto (ex: "II") e tenta achar "Valor Devido (R$)" ou valores numéricos próximos
            # Ajuste fino: Na DUIMP, o valor costuma vir após "Valor Devido (R$)" ou em tabelas quebradas.
            # Vamos tentar capturar o bloco específico.
            
            # Pega um pedaço de texto após a menção do imposto (limite de 500 caracteres para não pegar o próximo)
            bloco_imposto = re.search(fr'{nome_imposto}.*?(Valor Devido \(R\$\)|Valor A Recolher \(R\$\))[\s\n]*([\d\.]+,\d+)', texto, re.DOTALL)
            if bloco_imposto:
                return bloco_imposto.group(2)
            return "0,00"

        # Aplicando para cada tributo
        # Nota: O texto do PDF extraído muitas vezes quebra linhas, o regex com DOTALL ajuda.
        
        # II (Imposto de Importação) - Geralmente aparece no início da seção de tributos
        item_data['II (R$)'] = pegar_imposto(r'CALCULOS DOS TRIBUTOS - MERCADORIA\s+II', texto_item)
        
        # IPI
        item_data['IPI (R$)'] = pegar_imposto(r'IPI\s+Cobertura', texto_item) # Reforço de contexto
        if item_data['IPI (R$)'] == "0,00": # Tentativa secundária se o layout mudar
             item_data['IPI (R$)'] = pegar_imposto(r'IPI', texto_item)

        # PIS
        item_data['PIS (R$)'] = pegar_imposto(r'PIS\s+.*?COFINS', texto_item) # PIS geralmente vem antes de COFINS
        
        # COFINS
        item_data['COFINS (R$)'] = pegar_imposto(r'COFINS', texto_item)

        dados_itens.append(item_data)

    return pd.DataFrame(dados_itens)

# --- INTERFACE STREAMLIT ---
st.title("Extrator de Custos DUIMP")

uploaded_file = st.file_uploader("Suba o PDF da DUIMP", type="pdf")

if uploaded_file:
    df_resultado = extrair_dados_duimp(uploaded_file)
    
    st.subheader("Valores Extraídos por Item")
    st.dataframe(df_resultado)
    
    # Opção de baixar em Excel para você conferir
    # st.download_button(...)
