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
        # Configuração mais robusta para o ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"Erro ao iniciar o WebDriver: {str(e)}")
        st.stop()

def get_ufs(driver):
    try:
        driver.get("https://buscacepinter.correios.com.br/app/endereco/index.php")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        
        # Mudar para o frame correto
        driver.switch_to.frame("frame")
        
        # Clicar no link "Busca por CEP da Localidade"
        busca_por_cep = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Busca por CEP da Localidade"))
        )
        busca_por_cep.click()
        time.sleep(1)
        
        # Obter lista de UFs
        uf_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "uf"))
        )
        select = Select(uf_select)
        ufs = [option.get_attribute("value") for option in select.options if option.get_attribute("value")]
        return ufs
    except Exception as e:
        st.error(f"Erro ao obter UFs: {str(e)}")
        return []

def get_cidades_for_uf(driver, uf):
    try:
        driver.get("https://buscacepinter.correios.com.br/app/endereco/index.php")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        
        # Mudar para o frame correto
        driver.switch_to.frame("frame")
        
        # Clicar no link "Busca por CEP da Localidade"
        busca_por_cep = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Busca por CEP da Localidade"))
        )
        busca_por_cep.click()
        time.sleep(1)
        
        # Selecionar UF
        uf_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "uf"))
        )
        select_uf = Select(uf_select)
        select_uf.select_by_value(uf)
        time.sleep(1)
        
        # Obter lista de cidades
        cidade_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "localidade"))
        )
        select_cidade = Select(cidade_select)
        cidades = [option.get_attribute("value") for option in select_cidade.options if option.get_attribute("value")]
        return cidades
    except Exception as e:
        st.error(f"Erro ao obter cidades para UF {uf}: {str(e)}")
        return []

def get_faixas_cep(driver, uf, cidade):
    try:
        driver.get("https://buscacepinter.correios.com.br/app/endereco/index.php")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        
        # Mudar para o frame correto
        driver.switch_to.frame("frame")
        
        # Clicar no link "Busca por CEP da Localidade"
        busca_por_cep = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Busca por CEP da Localidade"))
        )
        busca_por_cep.click()
        time.sleep(1)
        
        # Selecionar UF e cidade
        uf_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "uf"))
        )
        select_uf = Select(uf_select)
        select_uf.select_by_value(uf)
        time.sleep(1)
        
        cidade_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "localidade"))
        )
        select_cidade = Select(cidade_select)
        select_cidade.select_by_value(cidade)
        time.sleep(1)
        
        # Clicar no botão de buscar
        buscar_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Buscar')]"))
        )
        buscar_btn.click()
        time.sleep(2)
        
        # Extrair dados da tabela
        tabela = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table[@id='resultado-DNEC']"))
        )
        linhas = tabela.find_elements(By.TAG_NAME, "tr")
        
        dados = []
        for linha in linhas[1:]:  # Pular cabeçalho
            colunas = linha.find_elements(By.TAG_NAME, "td")
            if len(colunas) >= 3:
                dados.append({
                    "Localidade": colunas[0].text,
                    "Faixa de CEP": colunas[1].text,
                    "Situação": colunas[2].text,
                    "UF": uf,
                    "Cidade": cidade
                })
        return dados
    except Exception as e:
        st.warning(f"Nenhuma faixa de CEP encontrada para {cidade}/{uf} ou erro ao processar: {str(e)}")
        return []

def main():
    driver = get_driver()
    
    st.sidebar.header("Configurações")
    uf_selecionada = st.sidebar.selectbox("Selecione uma UF para filtrar (ou todas)", ["Todas"] + get_ufs(driver))
    
    if st.sidebar.button("Iniciar Coleta de Dados"):
        with st.spinner("Coletando dados..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            ufs = get_ufs(driver) if uf_selecionada == "Todas" else [uf_selecionada]
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
                    all_data.extend(faixas)
            
            # Criar DataFrame
            if all_data:
                df = pd.DataFrame(all_data)
                
                # Reordenar colunas
                df = df[["UF", "Cidade", "Localidade", "Faixa de CEP", "Situação"]]
                
                # Mostrar dados
                st.success("Coleta de dados concluída!")
                st.dataframe(df)
                
                # Botão para download
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
