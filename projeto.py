import streamlit as st
import os
import shutil
import zipfile
import time
import threading
import tempfile
import xml.etree.ElementTree as ET
import pandas as pd
from io import BytesIO
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="MasterSAF — CT-e para Excel",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;500;700&display=swap');
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
html, body, [data-testid="stAppViewContainer"] { background: #0a0c10 !important; color: #d4dbe8 !important; font-family: 'DM Sans', sans-serif !important; }
[data-testid="stSidebar"] { background: #0e1117 !important; border-right: 1px solid #1e2535 !important; }
[data-testid="stSidebar"] * { color: #c4ccd8 !important; }
.hero { padding: 2.5rem 0 1.5rem; border-bottom: 1px solid #1e2535; margin-bottom: 2rem; }
.hero-tag { font-family: 'Space Mono', monospace; font-size: 0.7rem; letter-spacing: 0.2em; color: #00e5a0; text-transform: uppercase; margin-bottom: 0.5rem; }
.hero-title { font-family: 'Space Mono', monospace; font-size: 2.1rem; font-weight: 700; color: #eef2ff; line-height: 1.15; margin: 0; }
.hero-title span { color: #00e5a0; }
.hero-subtitle { font-size: 0.95rem; color: #6b7a99; margin-top: 0.5rem; font-weight: 300; }
.pipeline { display: flex; align-items: center; gap: 0; margin: 1.5rem 0 2rem; flex-wrap: wrap; }
.step { display: flex; align-items: center; gap: 0.6rem; background: #0e1117; border: 1px solid #1e2535; border-radius: 8px; padding: 0.7rem 1.1rem; font-family: 'Space Mono', monospace; font-size: 0.72rem; color: #4a5568; }
.step.active { border-color: #00e5a0; color: #00e5a0; box-shadow: 0 0 12px rgba(0,229,160,0.15); }
.step.done { border-color: #0070f3; color: #0070f3; }
.step-arrow { color: #1e2535; font-size: 1.1rem; padding: 0 0.3rem; }
[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, #00e5a0, #0070f3) !important; border-radius: 4px !important; }
[data-testid="stProgress"] > div { background: #1e2535 !important; border-radius: 4px !important; height: 6px !important; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input { background: #070910 !important; border: 1px solid #1e2535 !important; border-radius: 6px !important; color: #d4dbe8 !important; font-family: 'Space Mono', monospace !important; font-size: 0.82rem !important; }
[data-testid="stSidebar"] label { font-family: 'Space Mono', monospace !important; font-size: 0.72rem !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; color: #4a5568 !important; }
[data-testid="stSidebar"] .stButton button { background: linear-gradient(135deg, #00e5a0, #0070f3) !important; color: #020408 !important; font-family: 'Space Mono', monospace !important; font-weight: 700 !important; border: none !important; border-radius: 6px !important; padding: 0.75rem 1.5rem !important; width: 100% !important; }
.stDownloadButton button { background: linear-gradient(135deg, #00e5a0, #0070f3) !important; color: #020408 !important; font-family: 'Space Mono', monospace !important; font-weight: 700 !important; font-size: 1rem !important; border-radius: 8px !important; padding: 0.9rem 2rem !important; width: 100% !important; border: none !important; }
[data-testid="stAlert"] { background: #0e1117 !important; border-radius: 8px !important; border-left: 3px solid !important; font-family: 'Space Mono', monospace !important; font-size: 0.8rem !important; }
.section-label { font-family: 'Space Mono', monospace; font-size: 0.65rem; letter-spacing: 0.2em; color: #4a5568; text-transform: uppercase; margin-bottom: 0.8rem; margin-top: 1.8rem; border-bottom: 1px solid #1e2535; padding-bottom: 0.4rem; }
.sidebar-logo { font-family: 'Space Mono', monospace; font-size: 0.95rem; font-weight: 700; color: #eef2ff; padding: 1.2rem 0 1.5rem; border-bottom: 1px solid #1e2535; margin-bottom: 1.2rem; }
.sidebar-logo span { color: #00e5a0; }
.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin: 1.2rem 0; }
.stat-card { background: #0e1117; border: 1px solid #1e2535; border-radius: 8px; padding: 1rem 1.2rem; position: relative; overflow: hidden; }
.stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, #00e5a0, #0070f3); }
.stat-label { font-family: 'Space Mono', monospace; font-size: 0.6rem; letter-spacing: 0.15em; color: #4a5568; text-transform: uppercase; margin-bottom: 0.3rem; }
.stat-value { font-family: 'Space Mono', monospace; font-size: 1.6rem; font-weight: 700; color: #eef2ff; }
.stat-value.green { color: #00e5a0; } .stat-value.blue { color: #0070f3; }
.log-terminal { background: #070910; border: 1px solid #1e2535; border-radius: 8px; padding: 1rem 1.2rem; font-family: 'Space Mono', monospace; font-size: 0.72rem; color: #00e5a0; max-height: 320px; overflow-y: auto; line-height: 1.8; white-space: pre-wrap; word-break: break-all; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ESTADO DA SESSÃO
# ==============================================================================
defaults = {
    "running": False, "done": False, "error_msg": "",
    "page_atual": 0, "page_total": 0, "status_msg": "",
    "stage": "idle", "xml_count": 0, "excel_bytes": None, "logs": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==============================================================================
# HERO + PIPELINE
# ==============================================================================
st.markdown("""
<div class="hero">
    <div class="hero-tag">⚡ Automação Fiscal Completa</div>
    <h1 class="hero-title">Master<span>SAF</span> → Excel</h1>
    <p class="hero-subtitle">Baixa CT-es do portal, extrai os XMLs e entrega uma planilha Excel — tudo automaticamente</p>
</div>
""", unsafe_allow_html=True)

def render_pipeline():
    stage = st.session_state.stage
    steps = [("download","01 Download"),("extract","02 Extrair ZIPs"),("excel","03 Gerar Excel"),("done","04 Pronto")]
    order = [s[0] for s in steps]
    cur_idx = order.index(stage) if stage in order else -1
    html = '<div class="pipeline">'
    for i,(key,label) in enumerate(steps):
        idx = order.index(key)
        css  = "done" if idx < cur_idx else ("active" if idx == cur_idx else "")
        icon = "✓"   if idx < cur_idx else ("●"      if idx == cur_idx else str(i+1).zfill(2))
        html += f'<div class="step {css}"><span>{icon}</span><span>{label}</span></div>'
        if i < len(steps)-1: html += '<span class="step-arrow">→</span>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

render_pipeline()

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown('<div class="sidebar-logo">MASTER<span>SAF</span> //</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Credenciais</div>', unsafe_allow_html=True)
    usuario   = st.text_input("Usuário", placeholder="login@empresa.com.br", disabled=st.session_state.running)
    senha     = st.text_input("Senha", type="password", placeholder="••••••••", disabled=st.session_state.running)
    st.markdown('<div class="section-label">Período</div>', unsafe_allow_html=True)
    data_ini  = st.text_input("Data Inicial", value="08/05/2026", disabled=st.session_state.running)
    data_fin  = st.text_input("Data Final",   value="08/05/2026", disabled=st.session_state.running)
    st.markdown('<div class="section-label">Parâmetros</div>', unsafe_allow_html=True)
    qtd_loops = st.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5, disabled=st.session_state.running)
    st.markdown("<br>", unsafe_allow_html=True)
    if not st.session_state.running:
        iniciar = st.button("⚡ Iniciar Automação")
    else:
        st.button("⏳ Processando...", disabled=True)
        iniciar = False

# ==============================================================================
# CLASSE CTeProcessor — CÓPIA EXATA DO TKINTER
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
                for infQ in root.findall(f'.//{{{uri}}}infQ'):
                    tpMed  = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
                    if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                        for tp in tipos_peso:
                            if tp in tpMed.text.upper():
                                return float(qCarga.text)
            for infQ in root.findall('.//infQ'):
                tpMed  = infQ.find('tpMed')
                qCarga = infQ.find('qCarga')
                if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                    for tp in tipos_peso:
                        if tp in tpMed.text.upper():
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
                        found = element.find(xpath.replace('cte:', f'{{{uri}}}'))
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

            doc_dest = dest_CNPJ or dest_CPF or 'N/A'
            end_dest = ""
            if dest_xLgr:
                end_dest += dest_xLgr
                if dest_nro:     end_dest += f", {dest_nro}"
                if dest_xBairro: end_dest += f" - {dest_xBairro}"
                if dest_xMun:    end_dest += f", {dest_xMun}"
                if dest_UF:      end_dest += f"/{dest_UF}"
                if dest_CEP:     end_dest += f" - CEP: {dest_CEP}"
            if not end_dest: end_dest = "N/A"

            numero_nfe = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            peso_bruto = self.extract_peso_bruto(root)

            data_formatada = None
            if dhEmi:
                try:
                    data_formatada = datetime.strptime(dhEmi[:10], '%Y-%m-%d').strftime('%d/%m/%y')
                except:
                    try:
                        data_formatada = datetime.strptime(dhEmi[:10], '%d/%m/%Y').strftime('%d/%m/%y')
                    except:
                        data_formatada = dhEmi[:10]

            try:
                vTPrest = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                vTPrest = 0.0

            return {
                'Arquivo': filename, 'nCT': nCT or 'N/A',
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
                'Documento Destinatário': doc_dest,
                'Endereço Destinatário': end_dest,
                'Município Destino': dest_xMun or 'N/A',
                'UF Destino': dest_UF or 'N/A',
                'Chave NFe': infNFe_chave or 'N/A',
                'Número NFe': numero_nfe or 'N/A',
                'Data Processamento': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            }
        except Exception:
            return None

    # IGUAL ao tkinter: glob('*.xml') não-recursivo por pasta
    def process_xml_files_from_directory(self, directory_path, log_fn):
        xml_files = list(Path(directory_path).glob('*.xml'))
        log_fn(f"   {len(xml_files)} XMLs em: {os.path.basename(directory_path)}")
        for xml_file in xml_files:
            try:
                # tenta utf-8 primeiro, depois latin-1 (igual ao tkinter)
                try:
                    with open(xml_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(xml_file, 'r', encoding='latin-1') as f:
                        content = f.read()
                if 'CTe' in content or 'conhecimento' in content.lower():
                    data = self.extract_cte_data(content, xml_file.name)
                    if data:
                        self.processed_data.append(data)
            except Exception:
                pass

    def export_to_excel_bytes(self):
        if not self.processed_data:
            return None, 0
        df = pd.DataFrame(self.processed_data)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Dados_CTe')
            wb = writer.book
            ws = writer.sheets['Dados_CTe']
            hfmt = wb.add_format({'bold': True, 'bg_color': '#0e1117', 'font_color': '#00e5a0',
                                   'border': 1, 'border_color': '#1e2535', 'align': 'center', 'valign': 'vcenter'})
            mfmt = wb.add_format({'num_format': 'R$ #,##0.00'})
            wfmt = wb.add_format({'num_format': '#,##0.000'})
            pfmt = wb.add_format({'valign': 'vcenter'})
            for col_num, col_name in enumerate(df.columns):
                ws.write(0, col_num, col_name, hfmt)
                if col_name == 'Valor Prestação':
                    ws.set_column(col_num, col_num, 20, mfmt)
                elif 'Peso' in col_name:
                    ws.set_column(col_num, col_num, 18, wfmt)
                else:
                    ws.set_column(col_num, col_num, max(len(col_name)+2, 16), pfmt)
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, len(df), len(df.columns)-1)
        return buf.getvalue(), len(df)

    def clear_data(self):
        self.processed_data = []


# ==============================================================================
# DRIVER
# ==============================================================================
def get_driver(download_path):
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-popup-blocking")
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.binary_location = "/usr/bin/chromium"
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=opts)


# ==============================================================================
# esperar_downloads — IGUAL ao tkinter
# ==============================================================================
def esperar_downloads(directory, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        if not list(Path(directory).glob('*.crdownload')):
            return True
        time.sleep(1)
    return False


# ==============================================================================
# processar_arquivos_baixados — IGUAL ao tkinter, traduzido para Python puro
# ==============================================================================
def processar_arquivos_baixados(base_dir, state, log_fn):
    """
    Cópia exata do método processar_arquivos_baixados() do tkinter.
    Extrai ZIPs, processa XMLs por pasta, gera Excel em memória.
    """
    log_fn("=" * 45)
    log_fn("INICIANDO PROCESSAMENTO DOS ARQUIVOS")
    log_fn("=" * 45)

    state["stage"] = "extract"
    zip_files = list(Path(base_dir).glob('*.zip'))
    log_fn(f"{len(zip_files)} arquivos ZIP encontrados")

    if not zip_files:
        log_fn("⚠ Nenhum arquivo ZIP para processar!")
        state["error_msg"] = "Nenhum ZIP foi baixado. Verifique login e datas."
        return

    # Pasta de extração separada — IGUAL ao tkinter (tempfile.mkdtemp)
    extract_dir = tempfile.mkdtemp(prefix="mastersaf_extracted_")
    all_xml_dirs = []

    log_fn("Extraindo arquivos ZIP...")
    for zip_file in zip_files:
        try:
            zip_name     = zip_file.stem
            extract_path = os.path.join(extract_dir, zip_name)
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            all_xml_dirs.append(extract_path)
            log_fn(f"   ✔ {zip_file.name}")
        except Exception as e:
            log_fn(f"   ❌ Erro ao extrair {zip_file.name}: {e}")

    # Processa XMLs — IGUAL ao tkinter: chama por pasta, não rglob
    state["stage"] = "excel"
    log_fn("Processando arquivos XML de CT-e...")
    processor = CTeProcessor()

    for xml_dir in all_xml_dirs:
        processor.process_xml_files_from_directory(xml_dir, log_fn)

    total = len(processor.processed_data)
    log_fn(f"Total de CT-es identificados: {total}")
    state["xml_count"] = total

    if total > 0:
        log_fn("Gerando Excel consolidado...")

        # Resumo igual ao tkinter
        df_res      = pd.DataFrame(processor.processed_data)
        peso_total  = df_res['Peso Bruto (kg)'].sum()
        valor_total = df_res['Valor Prestação'].sum()

        excel_bytes, n = processor.export_to_excel_bytes()
        processor.clear_data()

        state["excel_bytes"] = excel_bytes
        state["xml_count"]   = n
        state["stage"]       = "done"

        log_fn(f"✅ Excel gerado! {n} registros")
        log_fn(f"   • Peso Bruto Total: {peso_total:,.2f} kg")
        log_fn(f"   • Valor Total: R$ {valor_total:,.2f}")
    else:
        processor.clear_data()
        log_fn("⚠ Nenhum CT-e válido encontrado nos XMLs")
        state["error_msg"] = "XMLs extraídos mas nenhum CT-e válido identificado."
        state["stage"]     = "done"

    # Limpa pasta de extração
    try:
        shutil.rmtree(extract_dir, ignore_errors=True)
    except Exception:
        pass


# ==============================================================================
# WORKER — thread isolada
# ==============================================================================
def automation_worker(usuario, senha, data_ini, data_fin, qtd_loops, temp_dir, state):
    driver = None

    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        state["logs"].append(f"[{ts}] {msg}")
        state["status_msg"] = msg

    try:
        # ── Download ──────────────────────────────────────────────────────────
        state["stage"] = "download"
        log("Iniciando navegador...")
        driver = get_driver(temp_dir)

        log("Acessando MasterSAF...")
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
        time.sleep(3)

        log("Realizando login...")
        driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
        driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
        driver.find_element(By.XPATH, '//*[@id="enter"]').click()
        time.sleep(5)

        log("Acessando Listagem Receptor CTEs...")
        driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a').click()
        time.sleep(5)

        log(f"Configurando período: {data_ini} a {data_fin}")
        campo_ini = driver.find_element(By.XPATH, '//*[@id="consultaDataInicial"]')
        campo_ini.click()
        campo_ini.send_keys(Keys.CONTROL, 'a')
        campo_ini.send_keys(data_ini)

        campo_fin = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        campo_fin.click()
        campo_fin.send_keys(Keys.CONTROL, 'a')
        campo_fin.send_keys(data_fin)
        time.sleep(2)

        log("Atualizando listagem...")
        driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]').click()
        time.sleep(5)

        log("Configurando exibição (200 itens por página)...")
        sel = driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
        sel.click()
        time.sleep(1)
        sel.find_element(By.XPATH, './/option[@value="200"]').click()
        time.sleep(3)

        log(f"Iniciando downloads ({qtd_loops} páginas)...")

        for i in range(int(qtd_loops)):
            log(f"Página {i+1}/{qtd_loops}")

            try:
                cb = driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                if not cb.is_selected():
                    cb.click()
                time.sleep(3)
            except Exception:
                pass

            try:
                driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3').click()
                time.sleep(3)
                driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]').click()
                time.sleep(3)
            except Exception:
                log("   ⚠ Erro no botão de download")

            # Aguarda .crdownload sumir — IGUAL ao tkinter
            esperar_downloads(temp_dir)

            # Log dos arquivos baixados até agora
            zips_ate_agora = list(Path(temp_dir).glob('*.zip'))
            log(f"   ✔ {len(zips_ate_agora)} ZIP(s) na pasta")

            try:
                cb = driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                if cb.is_selected():
                    cb.click()
                time.sleep(1)
            except Exception:
                pass

            if i < int(qtd_loops) - 1:
                try:
                    driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span').click()
                    time.sleep(5)
                except Exception:
                    log("   ⚠ Fim das páginas disponíveis")
                    break

            state["page_atual"] = i + 1

        log("Downloads concluídos!")
        driver.quit()
        driver = None

        # ── Processa ZIPs → XMLs → Excel (IGUAL ao tkinter) ──────────────────
        processar_arquivos_baixados(temp_dir, state, log)

    except Exception as e:
        import traceback
        log(f"ERRO CRITICO: {str(e)}")
        log(traceback.format_exc())
        state["error_msg"] = str(e)
        state["stage"]     = "done"
    finally:
        state["running"] = False
        state["done"]    = True
        if driver:
            try: driver.quit()
            except Exception: pass
        # Limpa pasta de downloads
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


# ==============================================================================
# DISPARO
# ==============================================================================
if iniciar:
    if not usuario or not senha:
        st.error("⚠️ Preencha o usuário e a senha para continuar.")
    else:
        # IGUAL ao tkinter: tempfile.mkdtemp com prefixo
        temp_dir = tempfile.mkdtemp(prefix="mastersaf_downloads_")

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
            target=automation_worker,
            args=(usuario, senha, data_ini, data_fin, qtd_loops, temp_dir, st.session_state),
            daemon=True,
        )
        t.start()
        st.rerun()

# ==============================================================================
# PAINEL DE PROGRESSO
# ==============================================================================
if st.session_state.running or st.session_state.done:
    st.markdown('<div class="section-label">Execução</div>', unsafe_allow_html=True)

    total = st.session_state.page_total or 1
    atual = st.session_state.page_atual
    stage = st.session_state.stage

    pct = {
        "download": (atual / total) * 0.65,
        "extract":  0.75,
        "excel":    0.90,
        "done":     1.0,
    }.get(stage, 0.0)

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
        <div class="stat-card"><div class="stat-label">CT-es no Excel</div><div class="stat-value blue">{st.session_state.xml_count}</div></div>
        <div class="stat-card"><div class="stat-label">Etapa</div><div class="stat-value" style="font-size:1rem;padding-top:0.3rem">{stage.upper()}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Terminal de log — mostra tudo para debug
    st.markdown('<div class="section-label">Log de Atividades</div>', unsafe_allow_html=True)
    log_html = "\n".join(st.session_state.logs[-100:])
    st.markdown(f'<div class="log-terminal">{log_html if log_html else "// aguardando eventos..."}</div>', unsafe_allow_html=True)

    # Download
    if stage == "done" and st.session_state.excel_bytes:
        st.markdown('<div class="section-label">Download</div>', unsafe_allow_html=True)
        periodo = f"{data_ini.replace('/','- ')}_a_{data_fin.replace('/','- ')}"
        st.download_button(
            label=f"📥  BAIXAR EXCEL — {st.session_state.xml_count} CT-e(s)",
            data=st.session_state.excel_bytes,
            file_name=f"CTe_MasterSAF_{periodo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    if st.session_state.running:
        time.sleep(3)
        st.rerun()
