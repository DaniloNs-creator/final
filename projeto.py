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

# Título do aplicativo
st.title("📮 Scraper de Faixas de CEP dos Correios")
st.markdown("""
Este aplicativo coleta todas as faixas de CEP de todas as cidades de todas as UFs do site dos Correios.
""")

# Configuração do Selenium
@st.cache_resource
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    
    # Configuração para funcionar tanto localmente quanto no Streamlit Sharing
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def scrape_uf(uf, driver):
    """Raspa todas as cidades e faixas de CEP para uma UF específica."""
    url = "https://buscacepinter.correios.com.br/app/faixa_cep_uf_localidade/index.php"
    driver.get(url)
    
    try:
        # Seleciona a UF
        select_uf = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "uf"))
        )
        select_uf = Select(select_uf)
        select_uf.select_by_value(uf)
        
        # Clica no botão de buscar
        buscar_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Buscar')]"))
        )
        buscar_button.click()
        
        # Aguarda a tabela carregar
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tabela"))
        
        # Processa a tabela de resultados
        table = driver.find_element(By.CSS_SELECTOR, "table.tabela")
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        data = []
        for row in rows[1:]:  # Pula o cabeçalho
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 3:
                localidade = cols[0].text.strip()
                faixa_cep = cols[1].text.strip()
                situacao = cols[2].text.strip()
                data.append({
                    "UF": uf,
                    "Localidade": localidade,
                    "Faixa de CEP": faixa_cep,
                    "Situação": situacao
                })
        
        return pd.DataFrame(data)
        
    except NoSuchElementException as e:
        st.error(f"Elemento não encontrado para UF {uf}: {str(e)}")
        return None
    except TimeoutException:
        st.warning(f"Tempo de espera excedido para UF {uf}. A página pode não ter carregado corretamente.")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao processar UF {uf}: {str(e)}")
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
        
        with st.spinner("Coletando dados. Por favor, aguarde..."):
            driver = get_driver()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_data = []
            total_ufs = len(selected_ufs)
            
            for i, uf in enumerate(selected_ufs):
                status_text.text(f"Processando UF: {uf} ({i+1}/{total_ufs})")
                progress_bar.progress((i + 1) / total_ufs)
                
                df_uf = scrape_uf(uf, driver)
                if df_uf is not None and not df_uf.empty:
                    all_data.append(df_uf)
                
                # Pequena pausa para evitar sobrecarregar o servidor
                time.sleep(2)
            
            driver.quit()
            
            if all_data:
                final_df = pd.concat(all_data, ignore_index=True)
                st.success(f"Coleta concluída! Total de registros: {len(final_df)}")
                
                # Mostra os dados
                st.dataframe(final_df)
                
                # Cria um botão para download
                csv = final_df.to_csv(index=False, encoding="utf-8-sig", sep=";")
                st.download_button(
                    label="📥 Baixar dados como CSV",
                    data=csv,
                    file_name="faixas_cep_correios.csv",
                    mime="text/csv"
                )
            else:
                st.error("Nenhum dado foi coletado. Verifique os logs para mais informações.")
    
    st.sidebar.markdown("""
    ### Como usar:
    1. Selecione as UFs desejadas
    2. Clique em "Coletar Dados"
    3. Aguarde o processamento
    4. Baixe os dados em CSV
    
    **Observação:** A coleta pode demorar vários minutos para todas as UFs.
    """)

if __name__ == "__main__":
    main()
