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
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service

# Configuração do Streamlit
st.set_page_config(page_title="Scraper de Faixas de CEP", page_icon="📮", layout="wide")

# Título do aplicativo
st.title("📮 Scraper de Faixas de CEP dos Correios")
st.markdown("""
Este aplicativo coleta todas as faixas de CEP de todas as cidades de todas as UFs do site dos Correios.
""")

# Configuração do Selenium para funcionar no Streamlit Cloud
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
        service = Service(executable_path="/usr/bin/chromedriver")
    else:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
    
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except WebDriverException as e:
        st.error(f"Erro ao iniciar o WebDriver: {str(e)}")
        st.stop()

def scrape_uf(uf, driver):
    """Raspa todas as cidades e faixas de CEP para uma UF específica."""
    url = "https://buscacepinter.correios.com.br/app/faixa_cep_uf_localidade/index.php"
    
    try:
        driver.get(url)
        
        # Seleciona a UF
        select_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "uf"))
        )
        select_uf = Select(select_element)
        select_uf.select_by_value(uf)
        
        # Clica no botão de buscar
        buscar_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Buscar')]"))
        )
        buscar_button.click()
        
        # Aguarda a tabela carregar
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tabela"))
        )
        
        # Processa a tabela de resultados
        table = driver.find_element(By.CSS_SELECTOR, "table.tabela")
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        data = []
        for row in rows[1:]:  # Pula o cabeçalho
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
    # Lista de UFs brasileiras
    ufs = [
        "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", 
        "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", 
        "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"
    ]
    
    # Interface do usuário
    st.sidebar.header("Configurações")
    selected_ufs = st.sidebar.multiselect("Selecione as UFs", ufs, default=ufs)
    
    if st.sidebar.button("Coletar Dados"):
        if not selected_ufs:
            st.warning("Por favor, selecione pelo menos uma UF.")
            return
        
        with st.spinner("Iniciando o navegador virtual..."):
            try:
                driver = get_driver()
            except Exception as e:
                st.error(f"Falha ao iniciar o navegador: {str(e)}")
                return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        all_data = []
        
        try:
            for i, uf in enumerate(selected_ufs):
                status_text.text(f"Processando {uf} ({i+1}/{len(selected_ufs)})")
                progress_bar.progress((i + 1) / len(selected_ufs))
                
                df_uf = scrape_uf(uf, driver)
                if df_uf is not None and not df_uf.empty:
                    all_data.append(df_uf)
                
                time.sleep(2)  # Delay para evitar bloqueio
            
            if all_data:
                final_df = pd.concat(all_data, ignore_index=True)
                st.success(f"Coleta concluída! Total de registros: {len(final_df)}")
                
                st.dataframe(final_df.head())
                
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
            st.info("Navegador encerrado.")

if __name__ == "__main__":
    # Verifica se está rodando no Streamlit Cloud
    os.environ['IS_STREAMLIT_CLOUD'] = 'true' if 'HOSTNAME' in os.environ and 'streamlit' in os.environ['HOSTNAME'] else 'false'
    main()
