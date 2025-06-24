import streamlit as st
import pandas as pd
import requests
from io import BytesIO, StringIO
from zipfile import ZipFile, BadZipFile
import urllib3

# Configurações iniciais
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="Faixas de CEP Brasil", layout="wide")

# URLs alternativas (HTTP)
URLS = {
    'TXT': 'http://dados.correios.com.br/public/localidades/faixa_cep_publico.txt',
    'ZIP': 'http://dados.correios.com.br/public/localidades/faixa_cep_publico.zip'
}

# Função para baixar dados
def download_data(url):
    try:
        response = requests.get(url, stream=True, verify=False, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Falha ao baixar arquivo: {str(e)}")
        return None

# Função para processar conteúdo
def process_content(content, is_zip=False):
    try:
        if is_zip:
            with ZipFile(BytesIO(content)) as zip_file:
                for file in zip_file.namelist():
                    if file.lower().endswith('.txt'):
                        with zip_file.open(file) as f:
                            content = f.read()
                            break
                else:
                    st.error("Arquivo TXT não encontrado no ZIP")
                    return None
        
        # Tentar decodificar
        try:
            text = content.decode('latin1')
        except UnicodeDecodeError:
            text = content.decode('utf-8', errors='replace')
        
        # Processar DataFrame
        df = pd.read_csv(
            StringIO(text),
            sep=';',
            header=None,
            names=['UF', 'Localidade', 'Faixa_Inicio', 'Faixa_Fim', 'Situacao'],
            dtype=str
        )
        
        # Limpeza dos dados
        df = df.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)
        df = df.dropna(how='all')
        
        return df
    
    except Exception as e:
        st.error(f"Erro no processamento: {str(e)}")
        return None

# Interface principal
def main():
    st.title("📊 Faixas de CEP do Brasil")
    st.markdown("""
    Aplicativo para download dos dados públicos de faixas de CEP disponibilizados pelos Correios.
    """)
    
    # Seleção de fonte
    fonte = st.radio(
        "Selecione a fonte dos dados:",
        ('Arquivo TXT', 'Arquivo ZIP'),
        horizontal=True
    )
    
    # Botão de download
    if st.button("🔽 Baixar Dados", type="primary"):
        with st.spinner("Obtendo dados dos Correios..."):
            url = URLS['ZIP'] if fonte == 'Arquivo ZIP' else URLS['TXT']
            content = download_data(url)
            
            if content:
                df = process_content(content, fonte == 'Arquivo ZIP')
                
                if df is not None:
                    st.session_state.df = df
                    st.success("Dados carregados com sucesso!")
                    st.dataframe(df.head())

    # Seção de filtros e exportação
    if 'df' in st.session_state:
        st.divider()
        st.subheader("🔍 Filtrar Dados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            uf = st.selectbox(
                "Selecione a UF:",
                ['TODAS'] + sorted(st.session_state.df['UF'].unique().tolist())
            )
        
        with col2:
            if uf != 'TODAS':
                cidades = sorted(st.session_state.df[st.session_state.df['UF'] == uf]['Localidade'].unique())
                cidade = st.selectbox("Selecione a cidade:", ['TODAS'] + cidades)
            else:
                cidade = 'TODAS'
        
        # Aplicar filtros
        filtered_df = st.session_state.df.copy()
        if uf != 'TODAS':
            filtered_df = filtered_df[filtered_df['UF'] == uf]
        if cidade != 'TODAS':
            filtered_df = filtered_df[filtered_df['Localidade'] == cidade]
        
        st.dataframe(filtered_df)
        
        # Exportação
        st.divider()
        st.subheader("📤 Exportar Dados")
        
        export_format = st.radio(
            "Formato de exportação:",
            ['CSV', 'Excel', 'JSON'],
            horizontal=True
        )
        
        export_name = f"faixas_cep_{uf if uf != 'TODAS' else 'BR'}{f'_{cidade}' if cidade != 'TODAS' else ''}"
        
        if export_format == 'CSV':
            csv = filtered_df.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                "⬇️ Baixar CSV",
                csv,
                f"{export_name}.csv",
                "text/csv"
            )
        elif export_format == 'Excel':
            excel = BytesIO()
            filtered_df.to_excel(excel, index=False, engine='openpyxl')
            st.download_button(
                "⬇️ Baixar Excel",
                excel.getvalue(),
                f"{export_name}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            json = filtered_df.to_json(orient='records', force_ascii=False)
            st.download_button(
                "⬇️ Baixar JSON",
                json,
                f"{export_name}.json",
                "application/json"
            )

if __name__ == "__main__":
    main()
