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

# Configuração simplificada do Selenium
@st.cache_resource
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    
    # Configuração para Streamlit Cloud
    if 'HOSTNAME' in os.environ and 'streamlit' in os.environ['HOSTNAME']:
        chrome_options.binary_location = "/usr/bin/google-chrome"
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"Erro ao iniciar o navegador: {str(e)}")
        st.stop()

def scrape_uf(uf, driver):
    try:
        driver.get("https://buscacepinter.correios.com.br/app/faixa_cep_uf_localidade/index.php")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "uf"))
        )
        Select(driver.find_element(By.NAME, "uf")).select_by_value(uf)
        
        driver.find_element(By.XPATH, "//button[contains(text(), 'Buscar')]").click()
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tabela"))
        )
        
        data = []
        table = driver.find_element(By.CSS_SELECTOR, "table.tabela")
        for row in table.find_elements(By.TAG_NAME, "tr")[1:]:
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
        st.warning(f"Erro na UF {uf}: {str(e)}")
        return None

def main():
    ufs = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", 
           "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", 
           "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
    
    selected_ufs = st.sidebar.multiselect("Selecione as UFs", ufs, default=["SP", "RJ"])
    
    if st.sidebar.button("Coletar Dados") and selected_ufs:
        with st.spinner("Coletando dados..."):
            driver = get_driver()
            try:
                all_data = []
                for i, uf in enumerate(selected_ufs):
                    st.write(f"Processando {uf} ({i+1}/{len(selected_ufs)})")
                    df = scrape_uf(uf, driver)
                    if df is not None:
                        all_data.append(df)
                    time.sleep(1)
                
                if all_data:
                    final_df = pd.concat(all_data)
                    st.success(f"Dados coletados! {len(final_df)} registros.")
                    st.dataframe(final_df)
                    
                    csv = final_df.to_csv(index=False, sep=";")
                    st.download_button(
                        "Baixar CSV",
                        csv,
                        "faixas_cep.csv",
                        "text/csv"
                    )
                else:
                    st.error("Nenhum dado foi coletado.")
            finally:
                driver.quit()

if __name__ == "__main__":
    main()
