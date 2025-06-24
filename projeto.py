import streamlit as st
import pandas as pd
import requests
from io import BytesIO, StringIO
from zipfile import ZipFile, BadZipFile
import magic  # Para detecção do tipo de arquivo

# Título do aplicativo
st.title("📦 Baixador de Faixas de CEP do Brasil - Versão Atualizada")
st.markdown("""
Este aplicativo permite baixar todas as faixas de CEP das cidades brasileiras.
Os dados são obtidos diretamente dos arquivos públicos dos Correios.
""")

# URLs dos arquivos (atualizadas)
URLS = {
    'TXT': 'https://ftp.correios.com.br/localidades/faixa_cep_publico.txt',
    'ZIP': 'https://ftp.correios.com.br/localidades/faixa_cep_publico.zip'
}

# Função para detectar o tipo de arquivo
def get_file_type(content):
    mime = magic.Magic(mime=True)
    file_type = mime.from_buffer(content)
    return file_type

# Função para baixar e processar dados
def download_cep_data(url):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        content = response.content
        
        # Verificar se é um arquivo ZIP
        if url.endswith('.zip'):
            try:
                with ZipFile(BytesIO(content)) as zip_file:
                    # Procurar pelo arquivo TXT dentro do ZIP
                    for file in zip_file.namelist():
                        if file.lower().endswith('.txt'):
                            with zip_file.open(file) as f:
                                file_content = f.read()
                                break
                    else:
                        st.error("Nenhum arquivo TXT encontrado no ZIP.")
                        return None
            except BadZipFile:
                st.error("O arquivo baixado não é um ZIP válido. Tentando processar como TXT...")
                file_content = content
        else:
            file_content = content
        
        # Tentar diferentes encodings
        try:
            text_content = file_content.decode('latin1')
        except UnicodeDecodeError:
            try:
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                st.error("Não foi possível decodificar o arquivo. Encoding desconhecido.")
                return None
        
        # Processar o conteúdo do arquivo
        try:
            # Tentar ler com pandas
            df = pd.read_csv(
                StringIO(text_content),
                sep=';',
                header=None,
                dtype=str,
                names=['UF', 'Localidade', 'Faixa_Inicio', 'Faixa_Fim', 'Situacao'],
                na_values=[''],
                keep_default_na=False
            )
            
            # Limpeza básica dos dados
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            
            return df
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar o arquivo: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        return None

# Interface principal
st.sidebar.header("Configurações")
file_source = st.sidebar.radio(
    "Fonte dos dados:",
    ('Arquivo TXT', 'Arquivo ZIP'),
    help="Selecione se deseja baixar diretamente o TXT ou o arquivo ZIP"
)

if st.button("Baixar Dados de CEP"):
    with st.spinner("Baixando e processando dados..."):
        url = URLS['ZIP'] if file_source == 'Arquivo ZIP' else URLS['TXT']
        cep_data = download_cep_data(url)
        
        if cep_data is not None:
            st.session_state.cep_data = cep_data
            st.success("Dados carregados com sucesso!")
            
            # Mostrar pré-visualização
            st.subheader("Pré-visualização dos Dados")
            st.dataframe(cep_data.head())

# Se os dados foram carregados
if 'cep_data' in st.session_state:
    st.sidebar.header("Filtros")
    
    # Filtrar por UF
    ufs = sorted(st.session_state.cep_data['UF'].unique())
    selected_uf = st.sidebar.selectbox("Selecione uma UF", ['Todas'] + ufs)
    
    if selected_uf != 'Todas':
        filtered_data = st.session_state.cep_data[st.session_state.cep_data['UF'] == selected_uf]
        
        # Filtrar por cidade
        cidades = sorted(filtered_data['Localidade'].unique())
        selected_cidade = st.sidebar.selectbox("Selecione uma cidade", ['Todas'] + cidades)
        
        if selected_cidade != 'Todas':
            filtered_data = filtered_data[filtered_data['Localidade'] == selected_cidade]
    else:
        filtered_data = st.session_state.cep_data
    
    # Mostrar dados filtrados
    st.subheader("Dados Filtrados")
    st.dataframe(filtered_data)
    
    # Opção para download
    st.subheader("Download dos Dados")
    output_format = st.radio("Formato de saída:", ['CSV', 'Excel', 'TXT'])
    
    if st.button("Gerar Arquivo para Download"):
        if output_format == 'CSV':
            csv = filtered_data.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                label="Baixar CSV",
                data=csv,
                file_name='faixas_cep.csv',
                mime='text/csv'
            )
        elif output_format == 'Excel':
            excel = BytesIO()
            filtered_data.to_excel(excel, index=False, engine='openpyxl')
            excel.seek(0)
            st.download_button(
                label="Baixar Excel",
                data=excel,
                file_name='faixas_cep.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:  # TXT
            txt = filtered_data.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                label="Baixar TXT",
                data=txt,
                file_name='faixas_cep.txt',
                mime='text/plain'
            )

# Instruções de instalação
st.markdown("""
### Caso encontre erros:

1. Instale a biblioteca magic-file:
