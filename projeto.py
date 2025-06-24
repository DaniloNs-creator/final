import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import os
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType

# Configuração do Streamlit
st.set_page_config(page_title="Coletor de Faixas de CEP", layout="wide")
st.title("Coletor de Faixas de CEP dos Correios")
st.write("Este aplicativo coleta todas as faixas de CEP de todas as cidades brasileiras diretamente do site dos Correios.")

# Configuração do Selenium
@st.cache_resource
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    
    try:
        # Configuração alternativa para o ChromeDriver
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"Erro ao iniciar o WebDriver: {str(e)}")
        st.error("Tentando método alternativo...")
        
        try:
            # Tentativa alternativa com versão fixa do ChromeDriver
            service = Service(ChromeDriverManager(version="114.0.5735.90").install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e2:
            st.error(f"Erro no método alternativo: {str(e2)}")
            st.stop()

def get_ufs(driver):
    try:
        driver.get("https://buscacepinter.correios.com.br/app/endereco/index.php")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        
        driver.switch_to.frame("frame")
        
        busca_por_cep = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Busca por CEP da Localidade"))
        )
        busca_por_cep.click()
        time.sleep(1.5)
        
        uf_select = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "uf"))
        )
        select = Select(uf_select)
        ufs = [option.get_attribute("value") for option in select.options if option.get_attribute("value")]
        return ufs
    except Exception as e:
        st.error(f"Erro ao obter UFs: {str(e)}")
        return []

# [Restante das funções get_cidades_for_uf e get_faixas_cep permanecem iguais à versão anterior]

def main():
    if 'driver' not in st.session_state:
        st.session_state.driver = get_driver()
    
    driver = st.session_state.driver
    
    st.sidebar.header("Configurações")
    ufs_disponiveis = get_ufs(driver)
    
    if not ufs_disponiveis:
        st.error("Não foi possível obter a lista de UFs. Verifique sua conexão.")
        return
    
    uf_selecionada = st.sidebar.selectbox("Selecione uma UF para filtrar (ou todas)", ["Todas"] + ufs_disponiveis)
    
    if st.sidebar.button("Iniciar Coleta de Dados"):
        with st.spinner("Coletando dados..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            ufs = ufs_disponiveis if uf_selecionada == "Todas" else [uf_selecionada]
            all_data = []
            
            total_ufs = len(ufs)
            for i, uf in enumerate(ufs):
                status_text.text(f"Processando UF: {uf} ({i+1}/{total_ufs})")
                progress_bar.progress((i) / (total_ufs * 2))
                
                cidades = get_cidades_for_uf(driver, uf)
                if not cidades:
                    st.warning(f"Nenhuma cidade encontrada para UF {uf}")
                    continue
                
                total_cidades = len(cidades)
                
                for j, cidade in enumerate(cidades):
                    status_text.text(f"Processando: {uf} - {cidade} ({j+1}/{total_cidades})")
                    progress_bar.progress((i + (j+1)/total_cidades) / (total_ufs * 2))
                    
                    faixas = get_faixas_cep(driver, uf, cidade)
                    all_data.extend(faixas)
            
            if all_data:
                df = pd.DataFrame(all_data)
                df = df[["UF", "Cidade", "Localidade", "Faixa de CEP", "Situação"]]
                
                st.success(f"Coleta concluída! {len(df)} registros encontrados.")
                st.dataframe(df)
                
                csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig')
                st.download_button(
                    label="Baixar dados como CSV",
                    data=csv,
                    file_name='faixas_cep_brasil.csv',
                    mime='text/csv'
                )
            else:
                st.warning("Nenhum dado foi coletado. Verifique sua conexão ou tente novamente.")

if __name__ == "__main__":
    main()
