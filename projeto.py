import os
import time
import pandas as pd
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Configuração do Streamlit
st.set_page_config(page_title="Scraper de Faixas de CEP", page_icon="📮", layout="wide")

st.title("📮 Scraper de Faixas de CEP dos Correios")
st.markdown("""
Este aplicativo coleta faixas de CEP de todas as cidades das UFs selecionadas.
""")

# Configuração otimizada para o Streamlit Cloud
@st.cache_resource
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    
    # Configurações específicas para o Streamlit Cloud
    if os.environ.get('IS_STREAMLIT_CLOUD'):
        chrome_options.binary_location = "/usr/bin/google-chrome"
        driver = webdriver.Chrome(
            executable_path="/usr/bin/chromedriver",
            options=chrome_options
        )
    else:
        # Configuração para ambiente local
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

def scrape_uf(uf, driver):
    try:
        driver.get("https://buscacepinter.correios.com.br/app/faixa_cep_uf_localidade/index.php")
        
        # Seleciona a UF
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "uf"))
        )
        Select(driver.find_element(By.NAME, "uf")).select_by_value(uf)
        
        # Clica no botão buscar
        driver.find_element(By.XPATH, "//button[contains(text(), 'Buscar')]").click()
        
        # Aguarda a tabela carregar
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tabela"))
        )
        
        # Processa os dados da tabela
        data = []
        table = driver.find_element(By.CSS_SELECTOR, "table.tabela")
        for row in table.find_elements(By.TAG_NAME, "tr")[1:]:  # Pula o cabeçalho
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 3:
                data.append({
                    "UF": uf,
                    "Localidade": cols[0].text.strip(),
                    "Faixa de CEP": cols[1].text.strip(),
                    "Situação": cols[2].text.strip()
                })
        
        return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Erro ao processar UF {uf}: {str(e)}")
        return None

def main():
    # Lista completa de UFs
    ufs = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", 
           "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", 
           "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
    
    # Interface do usuário
    selected_ufs = st.sidebar.multiselect("Selecione as UFs", ufs, default=["SP", "RJ"])
    
    if st.sidebar.button("Coletar Dados") and selected_ufs:
        with st.spinner("Iniciando o navegador..."):
            try:
                driver = get_driver()
            except Exception as e:
                st.error(f"Falha ao iniciar o navegador: {str(e)}")
                return
        
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            all_data = []
            
            for i, uf in enumerate(selected_ufs):
                status_text.text(f"Processando {uf} ({i+1}/{len(selected_ufs)})")
                progress_bar.progress((i + 1) / len(selected_ufs))
                
                df = scrape_uf(uf, driver)
                if df is not None:
                    all_data.append(df)
                
                time.sleep(2)  # Intervalo entre requisições
            
            if all_data:
                final_df = pd.concat(all_data, ignore_index=True)
                st.success(f"Coleta concluída! Total de registros: {len(final_df)}")
                
                # Mostra uma prévia dos dados
                st.dataframe(final_df.head())
                
                # Botão de download
                csv = final_df.to_csv(index=False, sep=";", encoding="utf-8-sig")
                st.download_button(
                    "⬇️ Baixar CSV completo",
                    csv,
                    "faixas_cep_correios.csv",
                    "text/csv",
                    key="download-csv"
                )
            else:
                st.error("Nenhum dado válido foi coletado.")
                
        finally:
            driver.quit()
            st.info("Processo finalizado.")

if __name__ == "__main__":
    # Configura variável de ambiente para detectar se está no Streamlit Cloud
    os.environ['IS_STREAMLIT_CLOUD'] = 'true' if 'HOSTNAME' in os.environ and 'streamlit' in os.environ['HOSTNAME'] else 'false'
    main()
