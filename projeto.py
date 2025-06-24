import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from webdriver_manager.chrome import ChromeDriverManager

# Configuração do Streamlit
st.title("Coletor de Faixas de CEP dos Correios")
st.write("Este aplicativo coleta todas as faixas de CEP de todas as cidades brasileiras diretamente do site dos Correios.")

# Configuração do Selenium
@st.cache_resource
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver

def get_ufs(driver):
    driver.get("https://buscacepinter.correios.com.br/app/endereco/index.php")
    time.sleep(2)
    
    # Mudar para o frame correto
    driver.switch_to.frame("frame")
    
    # Clicar no link "Busca por CEP da Localidade"
    busca_por_cep = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.LINK_TEXT, "Busca por CEP da Localidade"))
    )
    busca_por_cep.click()
    time.sleep(2)
    
    # Obter lista de UFs
    uf_select = Select(driver.find_element(By.NAME, "uf"))
    ufs = [option.get_attribute("value") for option in uf_select.options if option.get_attribute("value")]
    return ufs

def get_cidades_for_uf(driver, uf):
    driver.get("https://buscacepinter.correios.com.br/app/endereco/index.php")
    time.sleep(2)
    
    # Mudar para o frame correto
    driver.switch_to.frame("frame")
    
    # Clicar no link "Busca por CEP da Localidade"
    busca_por_cep = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.LINK_TEXT, "Busca por CEP da Localidade"))
    )
    busca_por_cep.click()
    time.sleep(2)
    
    # Selecionar UF
    uf_select = Select(driver.find_element(By.NAME, "uf"))
    uf_select.select_by_value(uf)
    time.sleep(2)
    
    # Obter lista de cidades
    cidade_select = Select(driver.find_element(By.NAME, "localidade"))
    cidades = [option.get_attribute("value") for option in cidade_select.options if option.get_attribute("value")]
    return cidades

def get_faixas_cep(driver, uf, cidade):
    driver.get("https://buscacepinter.correios.com.br/app/endereco/index.php")
    time.sleep(2)
    
    # Mudar para o frame correto
    driver.switch_to.frame("frame")
    
    # Clicar no link "Busca por CEP da Localidade"
    busca_por_cep = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.LINK_TEXT, "Busca por CEP da Localidade"))
    )
    busca_por_cep.click()
    time.sleep(2)
    
    # Selecionar UF e cidade
    uf_select = Select(driver.find_element(By.NAME, "uf"))
    uf_select.select_by_value(uf)
    time.sleep(2)
    
    cidade_select = Select(driver.find_element(By.NAME, "localidade"))
    cidade_select.select_by_value(cidade)
    time.sleep(2)
    
    # Clicar no botão de buscar
    buscar_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Buscar')]")
    buscar_btn.click()
    time.sleep(3)
    
    # Extrair dados da tabela
    try:
        tabela = driver.find_element(By.XPATH, "//table[@id='resultado-DNEC']")
        linhas = tabela.find_elements(By.TAG_NAME, "tr")
        
        dados = []
        for linha in linhas[1:]:  # Pular cabeçalho
            colunas = linha.find_elements(By.TAG_NAME, "td")
            if len(colunas) >= 3:
                dados.append({
                    "Localidade": colunas[0].text,
                    "Faixa de CEP": colunas[1].text,
                    "Situação": colunas[2].text
                })
        return dados
    except:
        return []

def main():
    driver = get_driver()
    
    if st.button("Iniciar Coleta de Dados"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        ufs = get_ufs(driver)
        all_data = []
        
        total_ufs = len(ufs)
        for i, uf in enumerate(ufs):
            status_text.text(f"Processando UF: {uf} ({i+1}/{total_ufs})")
            progress_bar.progress((i) / (total_ufs * 2))
            
            cidades = get_cidades_for_uf(driver, uf)
            total_cidades = len(cidades)
            
            for j, cidade in enumerate(cidades):
                status_text.text(f"Processando: {uf} - {cidade} ({j+1}/{total_cidades})")
                progress_bar.progress((i + (j+1)/total_cidades) / (total_ufs * 2))
                
                faixas = get_faixas_cep(driver, uf, cidade)
                for faixa in faixas:
                    faixa["UF"] = uf
                    faixa["Cidade"] = cidade
                    all_data.append(faixa)
        
        # Criar DataFrame
        df = pd.DataFrame(all_data)
        
        # Reordenar colunas
        df = df[["UF", "Cidade", "Localidade", "Faixa de CEP", "Situação"]]
        
        # Mostrar dados
        st.dataframe(df)
        
        # Botão para download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Baixar dados como CSV",
            data=csv,
            file_name='faixas_cep_brasil.csv',
            mime='text/csv'
        )
        
        st.success("Coleta de dados concluída!")

if __name__ == "__main__":
    main()
