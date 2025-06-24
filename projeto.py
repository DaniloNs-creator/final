import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from zipfile import ZipFile
import os

# Título do aplicativo
st.title("📦 Baixador de Faixas de CEP do Brasil")
st.markdown("""
Este aplicativo permite baixar todas as faixas de CEP das cidades brasileiras.
Os dados são obtidos diretamente dos arquivos públicos dos Correios.
""")

# Função para baixar e processar os dados
def download_cep_data():
    # URL do arquivo público dos Correios (exemplo - pode precisar ser atualizado)
    url = "http://www.buscacep.correios.com.br/sistemas/buscacep/arquivos/faixa_cep_publico.zip"
    
    try:
        # Baixar o arquivo ZIP
        response = requests.get(url)
        response.raise_for_status()
        
        # Extrair o conteúdo do ZIP
        with ZipFile(BytesIO(response.content)) as zip_file:
            # Listar arquivos no ZIP
            file_list = zip_file.namelist()
            
            # Procurar pelo arquivo de dados (pode variar)
            data_file = None
            for file in file_list:
                if file.lower().endswith('.txt') or file.lower().endswith('.csv'):
                    data_file = file
                    break
            
            if data_file:
                # Ler o arquivo de dados
                with zip_file.open(data_file) as f:
                    # Tentar detectar o encoding e o delimitador
                    try:
                        df = pd.read_csv(f, encoding='latin1', sep=';', header=None)
                    except:
                        f.seek(0)
                        df = pd.read_csv(f, encoding='utf-8', sep='\t', header=None)
                
                # Processar os dados (ajustar conforme o formato real do arquivo)
                # Esta parte precisa ser adaptada ao formato real dos dados
                df.columns = ['UF', 'Cidade', 'Faixa_Inicio', 'Faixa_Fim', 'Situacao']
                return df
            else:
                st.error("Arquivo de dados não encontrado no ZIP.")
                return None
                
    except Exception as e:
        st.error(f"Erro ao baixar os dados: {str(e)}")
        return None

# Função para filtrar dados por UF
def filter_by_uf(df, uf):
    return df[df['UF'] == uf]

# Função para filtrar dados por cidade
def filter_by_city(df, cidade):
    return df[df['Cidade'].str.contains(cidade, case=False)]

# Interface do aplicativo
if st.button("Baixar Todos os Dados de CEP"):
    with st.spinner("Baixando e processando dados dos Correios..."):
        cep_data = download_cep_data()
        
        if cep_data is not None:
            st.session_state.cep_data = cep_data
            st.success("Dados carregados com sucesso!")
            
            # Mostrar pré-visualização
            st.subheader("Pré-visualização dos Dados")
            st.dataframe(cep_data.head())

# Filtros (se os dados estiverem carregados)
if 'cep_data' in st.session_state:
    st.sidebar.header("Filtros")
    
    # Filtrar por UF
    ufs = sorted(st.session_state.cep_data['UF'].unique())
    selected_uf = st.sidebar.selectbox("Selecione uma UF", ['Todas'] + ufs)
    
    if selected_uf != 'Todas':
        filtered_data = filter_by_uf(st.session_state.cep_data, selected_uf)
        
        # Filtrar por cidade
        cidades = sorted(filtered_data['Cidade'].unique())
        selected_cidade = st.sidebar.selectbox("Selecione uma cidade", ['Todas'] + cidades)
        
        if selected_cidade != 'Todas':
            filtered_data = filter_by_city(filtered_data, selected_cidade)
    else:
        filtered_data = st.session_state.cep_data
    
    # Mostrar dados filtrados
    st.subheader("Dados Filtrados")
    st.dataframe(filtered_data)
    
    # Opção para download
    st.subheader("Download dos Dados")
    
    # Formato do arquivo
    file_format = st.radio("Formato do arquivo", ['CSV', 'Excel'])
    
    if st.button("Baixar Dados Filtrados"):
        if file_format == 'CSV':
            csv = filtered_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Baixar CSV",
                data=csv,
                file_name='faixas_cep.csv',
                mime='text/csv'
            )
        else:
            excel = BytesIO()
            filtered_data.to_excel(excel, index=False, engine='openpyxl')
            excel.seek(0)
            st.download_button(
                label="Baixar Excel",
                data=excel,
                file_name='faixas_cep.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

# Notas importantes
st.markdown("""
### Notas:
1. Este aplicativo baixa dados diretamente do site dos Correiros.
2. O formato dos dados pode mudar, então o aplicativo pode precisar de ajustes.
3. Para uso mais atualizado, verifique sempre a fonte oficial dos Correios.
""")
