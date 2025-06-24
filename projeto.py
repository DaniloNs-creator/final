import requests
from io import BytesIO, StringIO
from zipfile import ZipFile, BadZipFile
import streamlit as st
import os

# Título do aplicativo
st.title("📮 Baixador de Faixas de CEP do Brasil")

# Função para baixar o arquivo
def baixar_arquivo(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar o arquivo: {e}")
        return None

# Função para extrair o conteúdo do ZIP
def extrair_zip(conteudo_zip):
    try:
        with ZipFile(BytesIO(conteudo_zip)) as zip_file:
            arquivos = zip_file.namelist()
            if arquivos:
                with zip_file.open(arquivos[0]) as arquivo:
                    return arquivo.read().decode('latin1')
    except BadZipFile:
        st.error("O arquivo baixado não é um ZIP válido")
    except Exception as e:
        st.error(f"Erro ao extrair arquivo: {e}")
    return None

# URLs alternativas
URLS = [
    "https://dados.correios.com.br/public/localidades/faixa_cep_publico.zip",
    "http://dados.correios.com.br/public/localidades/faixa_cep_publico.zip",
    "https://ftp.correios.com.br/public/localidades/faixa_cep_publico.zip"
]

# Interface do usuário
st.markdown("""
Este aplicativo baixa a lista de faixas de CEP públicas disponibilizada pelos Correios.
""")

if st.button("Baixar dados de CEP"):
    with st.spinner("Buscando dados dos Correios..."):
        conteudo = None
        for url in URLS:
            conteudo = baixar_arquivo(url)
            if conteudo:
                break
        
        if conteudo:
            dados = extrair_zip(conteudo)
            if dados:
                st.success("Dados baixados e extraídos com sucesso!")
                st.download_button(
                    label="Baixar arquivo de CEPs",
                    data=dados,
                    file_name="faixa_cep.txt",
                    mime="text/plain"
                )
                
                # Mostrar primeiras linhas
                st.subheader("Prévia dos dados")
                st.text("\n".join(dados.split("\n")[:10]))
            else:
                st.error("Falha ao extrair os dados do arquivo ZIP")
        else:
            st.error("Não foi possível baixar o arquivo de nenhuma das fontes")
