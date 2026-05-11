import streamlit as st
import os
import sys
import zipfile
import tempfile
import shutil
import threading
import time
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="MasterSAF", page_icon="⚡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;500;700&display=swap');
#MainMenu {visibility:hidden;} footer {visibility:hidden;} header {visibility:hidden;}
html,body,[data-testid="stAppViewContainer"]{background:#0a0c10!important;color:#d4dbe8!important;font-family:'DM Sans',sans-serif!important;}
[data-testid="stSidebar"]{background:#0e1117!important;border-right:1px solid #1e2535!important;}
[data-testid="stSidebar"] *{color:#c4ccd8!important;}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input{background:#070910!important;border:1px solid #1e2535!important;border-radius:6px!important;color:#d4dbe8!important;font-family:'Space Mono',monospace!important;font-size:0.82rem!important;}
[data-testid="stSidebar"] label{font-family:'Space Mono',monospace!important;font-size:0.72rem!important;letter-spacing:0.1em!important;text-transform:uppercase!important;color:#4a5568!important;}
[data-testid="stSidebar"] .stButton button{background:linear-gradient(135deg,#00e5a0,#0070f3)!important;color:#020408!important;font-family:'Space Mono',monospace!important;font-weight:700!important;border:none!important;border-radius:6px!important;padding:0.75rem 1.5rem!important;width:100%!important;}
.stDownloadButton button{background:linear-gradient(135deg,#00e5a0,#0070f3)!important;color:#020408!important;font-family:'Space Mono',monospace!important;font-weight:700!important;font-size:1rem!important;border-radius:8px!important;padding:0.9rem 2rem!important;width:100%!important;border:none!important;}
[data-testid="stAlert"]{background:#0e1117!important;border-radius:8px!important;border-left:3px solid!important;font-family:'Space Mono',monospace!important;font-size:0.8rem!important;}
[data-testid="stProgress"] > div > div{background:linear-gradient(90deg,#00e5a0,#0070f3)!important;border-radius:4px!important;}
[data-testid="stProgress"] > div{background:#1e2535!important;border-radius:4px!important;height:6px!important;}
.hero{padding:2rem 0 1.5rem;border-bottom:1px solid #1e2535;margin-bottom:1.5rem;}
.hero-tag{font-family:'Space Mono',monospace;font-size:0.7rem;letter-spacing:0.2em;color:#00e5a0;text-transform:uppercase;margin-bottom:0.4rem;}
.hero-title{font-family:'Space Mono',monospace;font-size:2rem;font-weight:700;color:#eef2ff;margin:0;}
.hero-title span{color:#00e5a0;}
.hero-sub{font-size:0.9rem;color:#6b7a99;margin-top:0.4rem;}
.sidebar-logo{font-family:'Space Mono',monospace;font-size:0.95rem;font-weight:700;color:#eef2ff;padding:1rem 0 1.4rem;border-bottom:1px solid #1e2535;margin-bottom:1rem;}
.sidebar-logo span{color:#00e5a0;}
.slabel{font-family:'Space Mono',monospace;font-size:0.62rem;letter-spacing:0.2em;color:#4a5568;text-transform:uppercase;margin-bottom:0.6rem;margin-top:1.4rem;border-bottom:1px solid #1e2535;padding-bottom:0.3rem;}
.stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:0.8rem;margin:1rem 0;}
.stat-card{background:#0e1117;border:1px solid #1e2535;border-radius:8px;padding:1rem 1.2rem;position:relative;overflow:hidden;}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#00e5a0,#0070f3);}
.stat-label{font-family:'Space Mono',monospace;font-size:0.6rem;letter-spacing:0.15em;color:#4a5568;text-transform:uppercase;margin-bottom:0.3rem;}
.stat-value{font-family:'Space Mono',monospace;font-size:1.5rem;font-weight:700;color:#eef2ff;}
.green{color:#00e5a0!important;} .blue{color:#0070f3!important;}
.log-box{background:#070910;border:1px solid #1e2535;border-radius:8px;padding:1rem;font-family:'Space Mono',monospace;font-size:0.7rem;color:#00e5a0;max-height:300px;overflow-y:auto;line-height:1.8;white-space:pre-wrap;word-break:break-all;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ESTADO
# ==============================================================================
for k,v in {"running":False,"done":False,"error_msg":"","page_atual":0,
             "page_total":0,"status_msg":"","stage":"idle",
             "xml_count":0,"excel_bytes":None,"logs":[]}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==============================================================================
# HERO
# ==============================================================================
st.markdown("""
<div class="hero">
  <div class="hero-tag">⚡ Automação Fiscal</div>
  <h1 class="hero-title">Master<span>SAF</span> → Excel</h1>
  <p class="hero-sub">Baixa CT-es, extrai XMLs dos ZIPs e gera planilha Excel — automaticamente</p>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown('<div class="sidebar-logo">MASTER<span>SAF</span> //</div>', unsafe_allow_html=True)
    st.markdown('<div class="slabel">Credenciais</div>', unsafe_allow_html=True)
    usuario   = st.text_input("Usuário", placeholder="login@empresa.com.br", disabled=st.session_state.running)
    senha     = st.text_input("Senha", type="password", placeholder="••••••••", disabled=st.session_state.running)
    st.markdown('<div class="slabel">Período</div>', unsafe_allow_html=True)
    data_ini  = st.text_input("Data Inicial", value="08/05/2026", disabled=st.session_state.running)
    data_fin  = st.text_input("Data Final",   value="08/05/2026", disabled=st.session_state.running)
    st.markdown('<div class="slabel">Parâmetros</div>', unsafe_allow_html=True)
    qtd_loops = st.number_input("Qtd. Páginas", min_value=1, max_value=1000, value=5, disabled=st.session_state.running)
    st.markdown("<br>", unsafe_allow_html=True)
    if not st.session_state.running:
        iniciar = st.button("⚡ Iniciar Automação")
    else:
        st.button("⏳ Processando...", disabled=True)
        iniciar = False

# ==============================================================================
# CTeProcessor — RÉPLICA EXATA DO TKINTER
# Única diferença: export_to_excel salva em BytesIO em vez de arquivo
# ==============================================================================
CTE_NAMESPACES = {'cte': 'http://www.portalfiscal.inf.br/cte'}

class CTeProcessor:
    def __init__(self):
        self.processed_data = []

    def extract_nfe_number_from_key(self, chave_acesso):
        if not chave_acesso or len(chave_acesso) != 44:
            return None
        try:
            return chave_acesso[25:34]
        except Exception:
            return None

    def extract_peso_bruto(self, root):
        try:
            tipos_peso = ['PESO BRUTO', 'PESO BASE DE CALCULO', 'PESO BASE CÁLCULO', 'PESO']
            for prefix, uri in CTE_NAMESPACES.items():
                infQ_elements = root.findall(f'.//{{{uri}}}infQ')
                for infQ in infQ_elements:
                    tpMed  = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
                    if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                        for tipo_peso in tipos_peso:
                            if tipo_peso in tpMed.text.upper():
                                return float(qCarga.text)
            infQ_elements = root.findall('.//infQ')
            for infQ in infQ_elements:
                tpMed  = infQ.find('tpMed')
                qCarga = infQ.find('qCarga')
                if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                    for tipo_peso in tipos_peso:
                        if tipo_peso in tpMed.text.upper():
                            return float(qCarga.text)
            return 0.0
        except Exception:
            return 0.0

    def extract_cte_data(self, xml_content, filename):
        try:
            root = ET.fromstring(xml_content)

            def find_text(element, xpath):
                try:
                    for prefix, uri in CTE_NAMESPACES.items():
                        full_xpath = xpath.replace('cte:', f'{{{uri}}}')
                        found = element.find(full_xpath)
                        if found is not None and found.text:
                            return found.text
                    found = element.find(xpath.replace('cte:', ''))
                    if found is not None and found.text:
                        return found.text
                    return None
                except Exception:
                    return None

            nCT          = find_text(root, './/cte:nCT')
            dhEmi        = find_text(root, './/cte:dhEmi')
            cMunIni      = find_text(root, './/cte:cMunIni')
            UFIni        = find_text(root, './/cte:UFIni')
            cMunFim      = find_text(root, './/cte:cMunFim')
            UFFim        = find_text(root, './/cte:UFFim')
            emit_xNome   = find_text(root, './/cte:emit/cte:xNome')
            vTPrest      = find_text(root, './/cte:vTPrest')
            rem_xNome    = find_text(root, './/cte:rem/cte:xNome')
            dest_xNome   = find_text(root, './/cte:dest/cte:xNome')
            dest_CNPJ    = find_text(root, './/cte:dest/cte:CNPJ')
            dest_CPF     = find_text(root, './/cte:dest/cte:CPF')
            dest_xLgr    = find_text(root, './/cte:dest/cte:enderDest/cte:xLgr')
            dest_nro     = find_text(root, './/cte:dest/cte:enderDest/cte:nro')
            dest_xBairro = find_text(root, './/cte:dest/cte:enderDest/cte:xBairro')
            dest_xMun    = find_text(root, './/cte:dest/cte:enderDest/cte:xMun')
            dest_UF      = find_text(root, './/cte:dest/cte:enderDest/cte:UF')
            dest_CEP     = find_text(root, './/cte:dest/cte:enderDest/cte:CEP')
            infNFe_chave = find_text(root, './/cte:infNFe/cte:chave')

            documento_destinatario = dest_CNPJ or dest_CPF or 'N/A'

            endereco_destinatario = ""
            if dest_xLgr:
                endereco_destinatario += f"{dest_xLgr}"
                if dest_nro:     endereco_destinatario += f", {dest_nro}"
                if dest_xBairro: endereco_destinatario += f" - {dest_xBairro}"
                if dest_xMun:    endereco_destinatario += f", {dest_xMun}"
                if dest_UF:      endereco_destinatario += f"/{dest_UF}"
                if dest_CEP:     endereco_destinatario += f" - CEP: {dest_CEP}"
            if not endereco_destinatario:
                endereco_destinatario = "N/A"

            numero_nfe = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            peso_bruto = self.extract_peso_bruto(root)

            data_formatada = None
            if dhEmi:
                try:
                    data_obj = datetime.strptime(dhEmi[:10], '%Y-%m-%d')
                    data_formatada = data_obj.strftime('%d/%m/%y')
                except:
                    try:
                        data_obj = datetime.strptime(dhEmi[:10], '%d/%m/%Y')
                        data_formatada = data_obj.strftime('%d/%m/%y')
                    except:
                        data_formatada = dhEmi[:10]

            try:
                vTPrest = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                vTPrest = 0.0

            return {
                'Arquivo': filename,
                'nCT': nCT or 'N/A',
                'Data Emissão': data_formatada or dhEmi or 'N/A',
                'Código Município Início': cMunIni or 'N/A',
                'UF Início': UFIni or 'N/A',
                'Código Município Fim': cMunFim or 'N/A',
                'UF Fim': UFFim or 'N/A',
                'Emitente': emit_xNome or 'N/A',
                'Valor Prestação': vTPrest,
                'Peso Bruto (kg)': peso_bruto,
                'Remetente': rem_xNome or 'N/A',
                'Destinatário': dest_xNome or 'N/A',
                'Documento Destinatário': documento_destinatario,
                'Endereço Destinatário': endereco_destinatario,
                'Município Destino': dest_xMun or 'N/A',
                'UF Destino': dest_UF or 'N/A',
                'Chave NFe': infNFe_chave or 'N/A',
                'Número NFe': numero_nfe or 'N/A',
                'Data Processamento': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
        except Exception as e:
            return None

    # IGUAL AO TKINTER — glob não-recursivo, encoding utf-8
    def process_xml_files_from_directory(self, directory_path, log_callback):
        xml_files = list(Path(directory_path).glob('*.xml'))
        log_callback(f"   📄 {len(xml_files)} XMLs encontrados")
        for xml_file in xml_files:
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'CTe' in content or 'conhecimento' in content.lower():
                    data = self.extract_cte_data(content, xml_file.name)
                    if data:
                        self.processed_data.append(data)
            except Exception:
                pass

    # IGUAL AO TKINTER — mas retorna bytes em vez de salvar em disco
    def export_to_excel(self):
        if self.processed_data:
            df = pd.DataFrame(self.processed_data)
            buf = BytesIO()
            df.to_excel(buf, index=False, sheet_name='Dados_CTe')
            buf.seek(0)
            return buf.getvalue(), len(df)
        return None, 0

    def clear_data(self):
        self.processed_data = []


# ==============================================================================
# esperar_downloads — IGUAL AO TKINTER
# ==============================================================================
def esperar_downloads(directory, timeout=120):
    start_time = time.time()
    while time.time() - start_time < timeout:
        crdownload_files = list(Path(directory).glob('*.crdownload'))
        if not crdownload_files:
            return True
        time.sleep(1)
    return False


# ==============================================================================
# processar_arquivos_baixados — IGUAL AO TKINTER (método para função)
# ==============================================================================
def processar_arquivos_baixados(base_dir, log_callback, state):
    log_callback("=" * 50)
    log_callback("📦 INICIANDO PROCESSAMENTO DOS ARQUIVOS")
    log_callback("=" * 50)

    state["stage"] = "extract"

    zip_files = list(Path(base_dir).glob('*.zip'))
    log_callback(f"🔍 {len(zip_files)} arquivos ZIP encontrados")

    if not zip_files:
        log_callback("⚠ Nenhum arquivo ZIP para processar!")
        state["error_msg"] = "Nenhum ZIP baixado. Verifique login e datas."
        return

    # IGUAL AO TKINTER
    extract_dir = tempfile.mkdtemp(prefix="mastersaf_extracted_")
    all_xml_dirs = []

    for idx, zip_file in enumerate(zip_files):
        try:
            zip_name     = zip_file.stem
            extract_path = os.path.join(extract_dir, zip_name)
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            all_xml_dirs.append(extract_path)
            log_callback(f"   ✔ {zip_file.name}")
        except Exception as e:
            log_callback(f"   ❌ Erro: {zip_file.name}")

    # IGUAL AO TKINTER
    state["stage"] = "excel"
    log_callback("📄 Processando XMLs de CT-e...")

    processor = CTeProcessor()

    for xml_dir in all_xml_dirs:
        processor.process_xml_files_from_directory(xml_dir, log_callback)

    total_processados = len(processor.processed_data)
    log_callback(f"📊 Total de CT-es identificados: {total_processados}")
    state["xml_count"] = total_processados

    if total_processados > 0:
        log_callback("📊 Gerando Excel consolidado...")

        # Calcula resumo ANTES de exportar (igual ao tkinter)
        df_tmp      = pd.DataFrame(processor.processed_data)
        peso_total  = df_tmp['Peso Bruto (kg)'].sum()
        valor_total = df_tmp['Valor Prestação'].sum()
        num_registros = len(df_tmp)

        excel_bytes, _ = processor.export_to_excel()
        processor.clear_data()

        state["excel_bytes"] = excel_bytes
        state["xml_count"]   = num_registros
        state["stage"]       = "done"

        log_callback(f"✅ Excel gerado com sucesso!")
        log_callback(f"📈 Resumo:")
        log_callback(f"   • Registros: {num_registros}")
        log_callback(f"   • Peso Bruto: {peso_total:,.2f} kg")
        log_callback(f"   • Valor Total: R$ {valor_total:,.2f}")
    else:
        processor.clear_data()
        log_callback("⚠ Nenhum CT-e processado")
        state["error_msg"] = "Nenhum CT-e válido encontrado nos XMLs."
        state["stage"]     = "done"

    # Limpa pasta de extração
    shutil.rmtree(extract_dir, ignore_errors=True)
    log_callback("=" * 50)


# ==============================================================================
# rodar_automacao — IGUAL AO TKINTER (método para função de thread)
# ==============================================================================
def rodar_automacao(usuario, senha, dt_ini, dt_fin, loops, state):
    temp_dir = tempfile.mkdtemp(prefix="mastersaf_downloads_")

    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        state["logs"].append(f"[{ts}] {msg}")
        state["status_msg"] = msg

    log(f"📁 Pasta temporária: {os.path.basename(temp_dir)}")
    driver = None

    try:
        # Configura Chrome — IGUAL AO TKINTER
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")

        prefs = {
            "download.default_directory": temp_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.binary_location = "/usr/bin/chromium"

        log("🌐 Iniciando navegador em segundo plano...")
        driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=chrome_options)

        log("🔗 Acessando MasterSAF...")
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
        time.sleep(3)

        log("🔑 Realizando login...")
        driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
        driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
        driver.find_element(By.XPATH, '//*[@id="enter"]').click()
        time.sleep(5)

        log("📋 Acessando Listagem Receptor CTEs...")
        driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a').click()
        time.sleep(5)

        log(f"📅 Configurando período: {dt_ini} a {dt_fin}")
        campo_dt_inicial = driver.find_element(By.XPATH, '//*[@id="consultaDataInicial"]')
        campo_dt_inicial.click()
        campo_dt_inicial.send_keys(Keys.CONTROL, 'a')
        campo_dt_inicial.send_keys(dt_ini)

        campo_dt_final = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        campo_dt_final.click()
        campo_dt_final.send_keys(Keys.CONTROL, 'a')
        campo_dt_final.send_keys(dt_fin)
        time.sleep(2)

        log("🔄 Atualizando listagem...")
        driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]').click()
        time.sleep(5)

        log("⚙️ Configurando exibição (200 itens por página)...")
        select_element = driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
        select_element.click()
        time.sleep(1)
        select_element.find_element(By.XPATH, './/option[@value="200"]').click()
        time.sleep(3)

        log(f"📥 Iniciando downloads ({loops} páginas)...")

        for i in range(loops):
            state["stage"] = "download"
            log(f"📄 Página {i + 1}/{loops}")

            # Seleciona todos os checkboxes — IGUAL AO TKINTER
            try:
                checkbox = driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                if not checkbox.is_selected():
                    checkbox.click()
                time.sleep(3)
            except:
                pass

            # Clica no botão de download múltiplo — IGUAL AO TKINTER
            try:
                driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3').click()
                time.sleep(3)
                driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]').click()
                time.sleep(3)
            except:
                log("   ⚠ Erro no botão de download")

            # Aguarda downloads terminarem — IGUAL AO TKINTER
            esperar_downloads(temp_dir)

            # Desmarca checkbox — IGUAL AO TKINTER
            try:
                checkbox = driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                if checkbox.is_selected():
                    checkbox.click()
                time.sleep(1)
            except:
                pass

            # Avança para próxima página — IGUAL AO TKINTER
            if i < loops - 1:
                try:
                    driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span').click()
                    time.sleep(5)
                except:
                    log("   ⚠ Fim das páginas disponíveis")
                    break

            state["page_atual"] = i + 1

        log("✅ Downloads concluídos!")

        # Processamento pós-download — IGUAL AO TKINTER
        processar_arquivos_baixados(temp_dir, log, state)

    except Exception as e:
        import traceback
        log(f"❌ ERRO: {str(e)}")
        log(traceback.format_exc())
        state["error_msg"] = str(e)
        state["stage"]     = "done"
    finally:
        log("🔒 Fechando navegador...")
        if driver:
            try: driver.quit()
            except: pass
        state["running"] = False
        state["done"]    = True
        # Limpa downloads
        shutil.rmtree(temp_dir, ignore_errors=True)
        log("=" * 50)


# ==============================================================================
# DISPARO DA THREAD
# ==============================================================================
if iniciar:
    if not usuario or not senha:
        st.error("⚠️ Preencha o usuário e a senha para continuar.")
    else:
        st.session_state.running     = True
        st.session_state.done        = False
        st.session_state.error_msg   = ""
        st.session_state.page_atual  = 0
        st.session_state.page_total  = int(qtd_loops)
        st.session_state.status_msg  = "Iniciando..."
        st.session_state.stage       = "download"
        st.session_state.xml_count   = 0
        st.session_state.excel_bytes = None
        st.session_state.logs        = []

        t = threading.Thread(
            target=rodar_automacao,
            args=(usuario, senha, data_ini, data_fin, int(qtd_loops), st.session_state),
            daemon=True,
        )
        t.start()
        st.rerun()

# ==============================================================================
# PAINEL DE PROGRESSO
# ==============================================================================
if st.session_state.running or st.session_state.done:
    total = st.session_state.page_total or 1
    atual = st.session_state.page_atual
    stage = st.session_state.stage

    pct = {"download": (atual/total)*0.65, "extract": 0.78,
           "excel": 0.92, "done": 1.0}.get(stage, 0.0)

    if st.session_state.error_msg:
        st.error(f"❌ {st.session_state.error_msg}")
    elif stage == "done" and st.session_state.excel_bytes:
        st.success(f"✅ {st.session_state.status_msg}")
    elif stage == "done":
        st.warning(f"⚠️ {st.session_state.status_msg}")
    else:
        st.info(f"⏳ {st.session_state.status_msg}")

    st.progress(pct)

    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-card"><div class="stat-label">Páginas Baixadas</div><div class="stat-value green">{atual}</div></div>
      <div class="stat-card"><div class="stat-label">Total Programado</div><div class="stat-value">{total}</div></div>
      <div class="stat-card"><div class="stat-label">CT-es Extraídos</div><div class="stat-value blue">{st.session_state.xml_count}</div></div>
      <div class="stat-card"><div class="stat-label">Etapa</div><div class="stat-value" style="font-size:0.9rem;padding-top:0.4rem">{stage.upper()}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Log terminal
    log_html = "\n".join(st.session_state.logs[-120:]) or "// aguardando..."
    st.markdown(f'<div class="log-box">{log_html}</div>', unsafe_allow_html=True)

    # Download Excel
    if stage == "done" and st.session_state.excel_bytes:
        st.markdown("---")
        periodo = f"{data_ini.replace('/','_')}_a_{data_fin.replace('/','_')}"
        st.download_button(
            label=f"📥  BAIXAR EXCEL — {st.session_state.xml_count} CT-e(s)",
            data=st.session_state.excel_bytes,
            file_name=f"CTe_MasterSAF_{periodo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    if st.session_state.running:
        time.sleep(3)
        st.rerun()
