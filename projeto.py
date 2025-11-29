import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import time

# Configuração da página
st.set_page_config(
    page_title="Sistema de Cadastro - TOTVS",
    page_icon="👨‍💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado avançado com animações e design profissional
st.markdown("""
<style>
    /* Variáveis CSS */
    :root {
        --primary-color: #1f3a60;
        --secondary-color: #2c5282;
        --accent-color: #17a2b8;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
        --light-color: #f8f9fa;
        --dark-color: #343a40;
        --gradient-primary: linear-gradient(135deg, #1f3a60 0%, #2c5282 100%);
        --gradient-success: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        --gradient-accent: linear-gradient(135deg, #17a2b8 0%, #6f42c1 100%);
        --shadow-light: 0 4px 6px rgba(0, 0, 0, 0.1);
        --shadow-medium: 0 8px 15px rgba(0, 0, 0, 0.1);
        --shadow-heavy: 0 15px 35px rgba(0, 0, 0, 0.15);
    }

    /* Reset e estilos gerais */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        padding: 20px;
    }

    .main-header {
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 2rem;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        animation: fadeInDown 1s ease-out;
        position: relative;
    }

    .main-header::after {
        content: '';
        position: absolute;
        bottom: -10px;
        left: 50%;
        transform: translateX(-50%);
        width: 100px;
        height: 4px;
        background: var(--gradient-accent);
        border-radius: 2px;
    }

    /* Container principal */
    .main-container {
        max-width: 1400px;
        margin: 0 auto;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        box-shadow: var(--shadow-heavy);
        overflow: hidden;
        animation: slideUp 0.8s ease-out;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* Abas estilizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--gradient-primary);
        padding: 0 20px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 60px;
        background: transparent !important;
        color: white !important;
        font-weight: 600;
        border: none !important;
        border-radius: 0 !important;
        margin: 0 !important;
        padding: 0 25px !important;
        position: relative;
        transition: all 0.3s ease;
        border-bottom: 3px solid transparent !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        transform: translateY(-2px);
    }

    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.15) !important;
        border-bottom: 3px solid var(--accent-color) !important;
    }

    .stTabs [data-baseweb="tab"]::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 8px;
        transform: translateY(-50%);
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--accent-color);
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .stTabs [aria-selected="true"]::before {
        opacity: 1;
    }

    /* Containers de formulário */
    .form-container {
        background: white;
        padding: 2.5rem;
        border-radius: 15px;
        margin: 1rem;
        box-shadow: var(--shadow-light);
        border: 1px solid rgba(0, 0, 0, 0.05);
        animation: fadeIn 0.6s ease-out;
        position: relative;
        overflow: hidden;
    }

    .form-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 5px;
        height: 100%;
        background: var(--gradient-accent);
    }

    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--primary-color);
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid var(--light-color);
        position: relative;
        animation: slideInLeft 0.6s ease-out;
    }

    .section-header::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 60px;
        height: 2px;
        background: var(--gradient-accent);
    }

    /* Botões estilizados */
    .stButton button {
        background: var(--gradient-primary);
        color: white;
        font-weight: 600;
        border: none;
        padding: 12px 30px;
        border-radius: 50px;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-light);
        position: relative;
        overflow: hidden;
    }

    .stButton button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s ease;
    }

    .stButton button:hover::before {
        left: 100%;
    }

    .stButton button:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-medium);
        background: var(--secondary-color);
    }

    .stButton button:active {
        transform: translateY(-1px);
    }

    .save-button button {
        background: var(--gradient-success) !important;
    }

    .send-button button {
        background: var(--gradient-accent) !important;
    }

    .generate-button button {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%) !important;
    }

    /* Campos de entrada estilizados */
    .stTextInput>div>div>input, .stDateInput>div>div>input, .stSelectbox>div>div>select {
        border: 2px solid #e9ecef;
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 14px;
        transition: all 0.3s ease;
        background: white;
    }

    .stTextInput>div>div>input:focus, .stDateInput>div>div>input:focus, .stSelectbox>div>div>select:focus {
        border-color: var(--accent-color);
        box-shadow: 0 0 0 3px rgba(23, 162, 184, 0.1);
        transform: translateY(-2px);
    }

    .stRadio>div {
        gap: 15px;
    }

    .stRadio>div>label {
        background: var(--light-color);
        padding: 10px 20px;
        border-radius: 10px;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }

    .stRadio>div>label:hover {
        border-color: var(--accent-color);
        transform: translateY(-2px);
    }

    .stRadio>div>label[data-baseweb="radio"]>div:first-child {
        border-color: var(--primary-color);
    }

    /* Tabela de dependentes */
    .dependent-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin-top: 1rem;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: var(--shadow-light);
        animation: fadeIn 0.8s ease-out;
    }

    .dependent-table th {
        background: var(--gradient-primary);
        color: white;
        padding: 15px;
        text-align: left;
        font-weight: 600;
        position: relative;
    }

    .dependent-table th::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 2px;
        background: var(--accent-color);
    }

    .dependent-table td {
        padding: 12px 15px;
        border-bottom: 1px solid #e9ecef;
        transition: background-color 0.3s ease;
    }

    .dependent-table tr:hover td {
        background-color: rgba(23, 162, 184, 0.05);
    }

    /* Mensagens de status */
    .success-message {
        background: var(--gradient-success);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-top: 1rem;
        box-shadow: var(--shadow-light);
        animation: bounceIn 0.6s ease-out;
        position: relative;
        overflow: hidden;
    }

    .success-message::before {
        content: '✓';
        position: absolute;
        top: 50%;
        right: 20px;
        transform: translateY(-50%);
        font-size: 3rem;
        opacity: 0.2;
    }

    .save-message {
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        color: #0c5460;
        padding: 1.25rem;
        border-radius: 12px;
        margin-top: 1rem;
        border-left: 4px solid var(--accent-color);
        animation: slideInRight 0.5s ease-out;
    }

    .warning-message {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        color: #856404;
        padding: 1.25rem;
        border-radius: 12px;
        margin-top: 1rem;
        border-left: 4px solid var(--warning-color);
        animation: pulse 2s infinite;
    }

    /* Progresso das abas */
    .tab-progress {
        display: flex;
        justify-content: space-between;
        margin: 2rem 0;
        position: relative;
    }

    .tab-progress::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 3px;
        background: #e9ecef;
        transform: translateY(-50%);
        z-index: 1;
    }

    .progress-step {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: white;
        border: 3px solid #e9ecef;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        color: #6c757d;
        position: relative;
        z-index: 2;
        transition: all 0.3s ease;
    }

    .progress-step.active {
        background: var(--accent-color);
        border-color: var(--accent-color);
        color: white;
        transform: scale(1.1);
        box-shadow: 0 0 0 5px rgba(23, 162, 184, 0.2);
    }

    .progress-step.completed {
        background: var(--success-color);
        border-color: var(--success-color);
        color: white;
    }

    /* Animações CSS */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(50px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes bounceIn {
        0% {
            opacity: 0;
            transform: scale(0.3);
        }
        50% {
            opacity: 1;
            transform: scale(1.05);
        }
        70% {
            transform: scale(0.9);
        }
        100% {
            opacity: 1;
            transform: scale(1);
        }
    }

    @keyframes pulse {
        0% {
            box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.4);
        }
        70% {
            box-shadow: 0 0 0 10px rgba(255, 193, 7, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(255, 193, 7, 0);
        }
    }

    @keyframes float {
        0%, 100% {
            transform: translateY(0);
        }
        50% {
            transform: translateY(-10px);
        }
    }

    /* Cards informativos */
    .info-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: var(--shadow-medium);
        animation: float 3s ease-in-out infinite;
    }

    .info-card h3 {
        margin-bottom: 0.5rem;
        font-size: 1.2rem;
    }

    .info-card p {
        opacity: 0.9;
        font-size: 0.9rem;
    }

    /* Indicadores de campo obrigatório */
    .required-field {
        color: var(--danger-color);
        font-weight: bold;
        animation: pulse 2s infinite;
    }

    .field-label {
        font-weight: 600;
        color: var(--dark-color);
        margin-bottom: 0.5rem;
        display: block;
    }

    /* Loading spinner */
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(255,255,255,.3);
        border-radius: 50%;
        border-top-color: #fff;
        animation: spin 1s ease-in-out infinite;
        margin-right: 10px;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    /* Efeitos de foco melhorados */
    .focused {
        transform: scale(1.02);
        z-index: 10;
        position: relative;
    }

    /* Responsividade */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem;
        }
        
        .form-container {
            padding: 1.5rem;
            margin: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0 15px !important;
            font-size: 0.9rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Função para validar CPF
def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    
    if len(cpf) != 11:
        return False
    
    if cpf == cpf[0] * 11:
        return False
    
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return int(cpf[9]) == digito1 and int(cpf[10]) == digito2

# Função para formatar CPF
def formatar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf

# Função para formatar valores
def formatar_valor(valor):
    if not valor:
        return "0000000000000"
    valor_limpo = ''.join(filter(str.isdigit, str(valor)))
    return valor_limpo.zfill(13)

# Função para formatar texto
def formatar_texto(texto, tamanho):
    if not texto:
        texto = ""
    texto = str(texto)
    if len(texto) > tamanho:
        return texto[:tamanho]
    else:
        return texto.ljust(tamanho)

# Função para formatar data
def formatar_data(data):
    if isinstance(data, datetime):
        return data.strftime("%d%m%Y")
    elif isinstance(data, str):
        try:
            return datetime.strptime(data, "%Y-%m-%d").strftime("%d%m%Y")
        except:
            return "00000000"
    else:
        return "00000000"

# Função para gerar arquivo TXT TOTVS
def gerar_arquivo_totvs():
    header = "0000"
    header += formatar_texto("EMPRESA EXEMPLO LTDA", 35)
    header += formatar_texto("12345678000199", 14)
    header += datetime.now().strftime("%d%m%Y")
    header += "001"
    header += " " * 935
    header += "\n"
    
    cpf_limpo = ''.join(filter(str.isdigit, st.session_state.get('cpf', '')))
    
    registro_0100 = "0100"
    registro_0100 += formatar_texto(cpf_limpo, 11)
    registro_0100 += formatar_texto(st.session_state.get('nome_completo', ''), 70)
    registro_0100 += formatar_data(st.session_state.get('data_nascimento', ''))
    
    sexo = st.session_state.get('sexo', '')
    if sexo == 'Masculino':
        registro_0100 += "M"
    else:
        registro_0100 += "F"
    
    estado_civil = st.session_state.get('estado_civil', '')
    if estado_civil == 'Solteiro':
        registro_0100 += "1"
    elif estado_civil == 'Casado':
        registro_0100 += "2"
    else:
        registro_0100 += "1"
    
    grau_instrucao = st.session_state.get('grau_instrucao', '')
    if 'Fundamental' in grau_instrucao:
        registro_0100 += "01"
    elif 'Médio' in grau_instrucao:
        registro_0100 += "02"
    elif 'Superior' in grau_instrucao:
        registro_0100 += "03"
    elif 'Pós' in grau_instrucao:
        registro_0100 += "04"
    else:
        registro_0100 += "01"
    
    registro_0100 += "1"
    registro_0100 += formatar_texto(st.session_state.get('nome_mae', ''), 70)
    registro_0100 += formatar_texto(st.session_state.get('nome_pai', ''), 70)
    registro_0100 += formatar_texto(st.session_state.get('endereco', ''), 60)
    registro_0100 += formatar_texto(st.session_state.get('bairro', ''), 40)
    
    cidade = st.session_state.get('cidade', '')
    if ' - ' in cidade:
        cidade_parts = cidade.split(' - ')
        registro_0100 += formatar_texto(cidade_parts[0], 40)
        registro_0100 += formatar_texto(cidade_parts[1] if len(cidade_parts) > 1 else '', 2)
    else:
        registro_0100 += formatar_texto(cidade, 40)
        registro_0100 += "  "
    
    cep_limpo = ''.join(filter(str.isdigit, st.session_state.get('cep', '')))
    registro_0100 += formatar_texto(cep_limpo, 8)
    registro_0100 += formatar_texto(st.session_state.get('email', ''), 60)
    
    raca_cor = st.session_state.get('raca_cor', '')
    if raca_cor == 'Branca':
        registro_0100 += "01"
    elif raca_cor == 'Negra':
        registro_0100 += "02"
    elif raca_cor == 'Parda':
        registro_0100 += "03"
    elif raca_cor == 'Amarela':
        registro_0100 += "04"
    else:
        registro_0100 += "01"
    
    registro_0100 += " " * 572
    registro_0100 += "\n"
    
    registro_0200 = "0200"
    registro_0200 += formatar_texto(cpf_limpo, 11)
    rg_limpo = ''.join(filter(str.isdigit, st.session_state.get('rg', '')))
    registro_0200 += formatar_texto(rg_limpo, 15)
    registro_0200 += formatar_texto(st.session_state.get('orgao_exp', ''), 10)
    registro_0200 += formatar_data(st.session_state.get('data_expedicao', ''))
    ctps_limpo = ''.join(filter(str.isdigit, st.session_state.get('ctps', '')))
    registro_0200 += formatar_texto(ctps_limpo, 11)
    registro_0200 += formatar_texto(st.session_state.get('serie', ''), 5)
    registro_0200 += formatar_texto(st.session_state.get('uf_ctps', ''), 2)
    registro_0200 += formatar_data(st.session_state.get('data_exp_ctps', ''))
    pis_limpo = ''.join(filter(str.isdigit, st.session_state.get('pis', '')))
    registro_0200 += formatar_texto(pis_limpo, 11)
    
    titulo_limpo = ''.join(filter(str.isdigit, st.session_state.get('titulo_eleitor', '')))
    registro_0200 += formatar_texto(titulo_limpo, 12)
    registro_0200 += formatar_texto(st.session_state.get('zona', ''), 4)
    registro_0200 += formatar_texto(st.session_state.get('secao', ''), 4)
    registro_0200 += formatar_texto(st.session_state.get('carteira_habilitacao', ''), 15)
    registro_0200 += formatar_texto(st.session_state.get('categoria_hab', ''), 2)
    registro_0200 += formatar_data(st.session_state.get('vencimento_hab', ''))
    registro_0200 += formatar_texto(st.session_state.get('uf_hab', ''), 2)
    registro_0200 += formatar_texto(st.session_state.get('reservista', ''), 15)
    registro_0200 += " " * 850
    registro_0200 += "\n"
    
    registro_0300 = "0300"
    registro_0300 += formatar_texto(cpf_limpo, 11)
    registro_0300 += formatar_texto(st.session_state.get('banco', ''), 3)
    registro_0300 += formatar_texto(st.session_state.get('agencia', ''), 5)
    registro_0300 += formatar_texto(st.session_state.get('conta', ''), 10)
    registro_0300 += formatar_texto(st.session_state.get('chave_pix', ''), 77)
    registro_0300 += " " * 882
    registro_0300 += "\n"
    
    registro_0400 = "0400"
    registro_0400 += formatar_texto(cpf_limpo, 11)
    registro_0400 += formatar_texto("00217252923", 11)
    registro_0400 += formatar_texto("LAURA HELENA MATOS FERREIRA LEITE", 70)
    registro_0400 += formatar_data("2024-03-13")
    registro_0400 += "F"
    registro_0400 += "S"
    registro_0400 += "N"
    registro_0400 += "06"
    registro_0400 += " " * 864
    registro_0400 += "\n"
    
    registro_0500 = "0500"
    registro_0500 += formatar_texto(cpf_limpo, 11)
    registro_0500 += formatar_data(st.session_state.get('data_inicio', ''))
    registro_0500 += formatar_texto(st.session_state.get('cargo_funcao', ''), 50)
    
    salario_limpo = ''.join(filter(str.isdigit, st.session_state.get('salario', '')))
    registro_0500 += formatar_valor(salario_limpo)
    registro_0500 += formatar_texto(st.session_state.get('horario_trabalho', ''), 100)
    registro_0500 += formatar_texto(st.session_state.get('centro_custo', ''), 30)
    registro_0500 += formatar_texto(st.session_state.get('sindicato', ''), 50)
    
    vt = st.session_state.get('vale_transporte', '')
    registro_0500 += "S" if vt == "Sim" else "N"
    
    va = st.session_state.get('vale_alimentacao', '')
    registro_0500 += "S" if va == "Sim" else "N"
    
    vr = st.session_state.get('vale_refeicao', '')
    registro_0500 += "S" if vr == "Sim" else "N"
    
    an = st.session_state.get('adicional_noturno', '')
    registro_0500 += "S" if an == "Sim" else "N"
    
    ins = st.session_state.get('insalubridade', '')
    registro_0500 += "S" if ins == "Sim" else "N"
    
    per = st.session_state.get('periculosidade', '')
    registro_0500 += "S" if per == "Sim" else "N"
    
    registro_0500 += " " * 698
    registro_0500 += "\n"
    
    trailer = "9900"
    trailer += "0006"
    trailer += " " * 984
    trailer += "\n"
    
    conteudo_arquivo = header + registro_0100 + registro_0200 + registro_0300 + registro_0400 + registro_0500 + trailer
    
    return conteudo_arquivo

# Função para download
def get_download_link(content, filename):
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}" class="stButton button generate-button">📥 BAIXAR ARQUIVO TXT</a>'
    return href

# Inicialização do estado da sessão
def initialize_session_state():
    session_vars = {
        'dados_pessoais_salvos': False,
        'documentacao_salvos': False,
        'dados_bancarios_salvos': False,
        'dependentes_salvos': False,
        'beneficios_salvos': False,
        'dados_empresa_salvos': False,
        'formulario_enviado': False,
        'arquivo_gerado': False,
        'current_tab': 0
    }
    
    for key, value in session_vars.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Funções para campos com estilo
def campo_obrigatorio(label, key, **kwargs):
    return st.text_input(f"{label} <span class='required-field'>*</span>", key=key, **kwargs)

def selectbox_obrigatorio(label, key, options, **kwargs):
    return st.selectbox(f"{label} <span class='required-field'>*</span>", options, key=key, **kwargs)

def date_input_obrigatorio(label, key, **kwargs):
    return st.date_input(f"{label} <span class='required-field'>*</span>", key=key, **kwargs)

def radio_obrigatorio(label, key, options, **kwargs):
    return st.radio(f"{label} <span class='required-field'>*</span>", options, key=key, **kwargs)

# Função principal
def main():
    initialize_session_state()
    
    st.markdown('<div class="main">', unsafe_allow_html=True)
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">SISTEMA DE CADASTRO DE FUNCIONÁRIOS</h1>', unsafe_allow_html=True)
    
    # Card informativo
    st.markdown("""
    <div class="info-card">
        <h3>🚀 Sistema Integrado TOTVS</h3>
        <p>Preencha todas as abas do formulário para gerar o arquivo de integração com o sistema TOTVS.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Barra de progresso
    st.markdown("""
    <div class="tab-progress">
        <div class="progress-step {}">1</div>
        <div class="progress-step {}">2</div>
        <div class="progress-step {}">3</div>
        <div class="progress-step {}">4</div>
        <div class="progress-step {}">5</div>
        <div class="progress-step {}">6</div>
    </div>
    """.format(
        "completed" if st.session_state.dados_pessoais_salvos else "active" if st.session_state.current_tab == 0 else "",
        "completed" if st.session_state.documentacao_salvos else "active" if st.session_state.current_tab == 1 else "",
        "completed" if st.session_state.dados_bancarios_salvos else "active" if st.session_state.current_tab == 2 else "",
        "completed" if st.session_state.dependentes_salvos else "active" if st.session_state.current_tab == 3 else "",
        "completed" if st.session_state.beneficios_salvos else "active" if st.session_state.current_tab == 4 else "",
        "completed" if st.session_state.dados_empresa_salvos else "active" if st.session_state.current_tab == 5 else ""
    ), unsafe_allow_html=True)
    
    # Abas
    tab_names = [
        f"👤 Dados Pessoais {'✓' if st.session_state.dados_pessoais_salvos else ''}",
        f"📄 Documentação {'✓' if st.session_state.documentacao_salvos else ''}",
        f"💳 Dados Bancários {'✓' if st.session_state.dados_bancarios_salvos else ''}",
        f"👨‍👩‍👧 Dependentes {'✓' if st.session_state.dependentes_salvos else ''}",
        f"🎁 Benefícios {'✓' if st.session_state.beneficios_salvos else ''}",
        f"🏢 Dados Empresa {'✓' if st.session_state.dados_empresa_salvos else ''}"
    ]
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tab_names)
    
    with tab1:
        st.session_state.current_tab = 0
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">👤 DADOS PESSOAIS</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nome_completo = campo_obrigatorio("Nome Completo", "nome_completo", value="ADRIELLY DOS SANTOS MATOS")
            estado_civil = radio_obrigatorio("Estado Civil", "estado_civil", ["Solteiro", "Casado", "Divorciado", "Viúvo"], index=0)
            sexo = radio_obrigatorio("Sexo", "sexo", ["Masculino", "Feminino"], index=1)
            data_nascimento = date_input_obrigatorio("Data de Nascimento", "data_nascimento", value=datetime(1999, 7, 8))
        
        with col2:
            naturalidade = st.text_input("Naturalidade", value="ARCOVERDE - PE", key="naturalidade")
            endereco = campo_obrigatorio("Endereço", "endereco", value="R POETA FRANCISCO FERREIRA LEITE, 40, BL 04 AP 12")
            bairro = campo_obrigatorio("Bairro", "bairro", value="CRISTO REI")
            cidade = campo_obrigatorio("Cidade", "cidade", value="CURITIBA - PR")
        
        with col3:
            cep = campo_obrigatorio("CEP", "cep", value="80050-360")
            nome_pai = st.text_input("Nome do Pai", value="ANTONIO MARCOS DA SILVA MATOS", key="nome_pai")
            nome_mae = campo_obrigatorio("Nome da Mãe", "nome_mae", value="ANDRÉA DOS SANTOS MELO")
        
        col4, col5 = st.columns(2)
        
        with col4:
            grau_instrucao = selectbox_obrigatorio(
                "Grau de Instrução", 
                "grau_instrucao",
                ["Ensino Fundamental", "Ensino Médio", "Curso Superior", "Pós Graduação"],
                index=2
            )
        
        with col5:
            email = st.text_input("E-mail", value="adriellymatos8@gmail.com", key="email")
            raca_cor = selectbox_obrigatorio(
                "Raça/Cor", 
                "raca_cor",
                ["Branca", "Negra", "Parda", "Amarela", "Indígena"],
                index=0
            )
        
        if st.button("💾 SALVAR DADOS PESSOAIS", key="gravar_dados_pessoais", use_container_width=True):
            campos_obrigatorios = [nome_completo, data_nascimento, endereco, bairro, cidade, cep, nome_mae]
            if all(campos_obrigatorios):
                st.session_state.dados_pessoais_salvos = True
                st.markdown("""
                <div class="save-message">
                    <strong>✅ Dados pessoais salvos com sucesso!</strong>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.session_state.current_tab = 1
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">📄 DOCUMENTAÇÃO</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            rg = campo_obrigatorio("RG", "rg", value="060.375.391-46")
            orgao_exp = campo_obrigatorio("Órgão Expedidor", "orgao_exp", value="SESP/PR")
            data_expedicao = date_input_obrigatorio("Data de Expedição", "data_expedicao", value=datetime(2024, 5, 26))
            cpf = campo_obrigatorio("CPF", "cpf", value="060.375.391-46")
            
            if cpf and not validar_cpf(cpf):
                st.error("CPF inválido!")
        
        with col2:
            titulo_eleitor = st.text_input("Título de Eleitor", value="0268 4243 1929", key="titulo_eleitor")
            ctps = campo_obrigatorio("CTPS", "ctps", value="7551374")
            serie = campo_obrigatorio("Série", "serie", value="00050")
            uf_ctps = campo_obrigatorio("UF", "uf_ctps", value="MS")
            data_exp_ctps = date_input_obrigatorio("Data Expedição CTPS", "data_exp_ctps", value=datetime(2020, 3, 27))
            pis = campo_obrigatorio("PIS", "pis", value="160.94867.47-46")
        
        if st.button("💾 SALVAR DOCUMENTAÇÃO", key="gravar_documentacao", use_container_width=True):
            campos_obrigatorios = [rg, orgao_exp, data_expedicao, cpf, ctps, serie, uf_ctps, data_exp_ctps, pis]
            if all(campos_obrigatorios) and validar_cpf(cpf):
                st.session_state.documentacao_salvos = True
                st.markdown("""
                <div class="save-message">
                    <strong>✅ Documentação salva com sucesso!</strong>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios com CPF válido.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.session_state.current_tab = 2
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">💳 DADOS BANCÁRIOS</h2>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-card">
            <h3>💡 Informação</h3>
            <p>Todos os campos desta seção são opcionais</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            banco = st.text_input("Banco", value="MÊNTORE BANK", key="banco")
        
        with col2:
            agencia = st.text_input("Agência", key="agencia")
        
        with col3:
            conta = st.text_input("Conta Corrente", key="conta")
        
        chave_pix = st.text_input("Chave PIX", key="chave_pix")
        
        if st.button("💾 SALVAR DADOS BANCÁRIOS", key="gravar_dados_bancarios", use_container_width=True):
            st.session_state.dados_bancarios_salvos = True
            st.markdown("""
            <div class="save-message">
                <strong>✅ Dados bancários salvos com sucesso!</strong>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab4:
        st.session_state.current_tab = 3
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">👨‍👩‍👧 DEPENDENTES</h2>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-card">
            <h3>💡 Informação</h3>
            <p>Todos os campos desta seção são opcionais</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <table class="dependent-table">
            <tr>
                <th>Nome</th>
                <th>CPF</th>
                <th>Data de Nascimento</th>
                <th>IRRF</th>
                <th>Salário Família</th>
            </tr>
            <tr>
                <td>LAURA HELENA MATOS FERREIRA LEITE</td>
                <td>002.172.529-23</td>
                <td>13/03/2024</td>
                <td>SIM</td>
                <td>NÃO</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)
        
        if st.button("💾 SALVAR DEPENDENTES", key="gravar_dependentes", use_container_width=True):
            st.session_state.dependentes_salvos = True
            st.markdown("""
            <div class="save-message">
                <strong>✅ Dependentes salvos com sucesso!</strong>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab5:
        st.session_state.current_tab = 4
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">🎁 BENEFÍCIOS</h2>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-card">
            <h3>💡 Informação</h3>
            <p>Todos os campos desta seção são opcionais</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            vale_transporte = st.radio("Vale Transporte", ["Sim", "Não"], index=0, horizontal=True, key="vale_transporte")
            vale_alimentacao = st.radio("Vale Alimentação", ["Sim", "Não"], index=0, horizontal=True, key="vale_alimentacao")
        
        with col2:
            vale_refeicao = st.radio("Vale Refeição", ["Sim", "Não"], index=1, horizontal=True, key="vale_refeicao")
            cesta_basica = st.radio("Cesta Básica", ["Sim", "Não"], index=1, horizontal=True, key="cesta_basica")
        
        if st.button("💾 SALVAR BENEFÍCIOS", key="gravar_beneficios", use_container_width=True):
            st.session_state.beneficios_salvos = True
            st.markdown("""
            <div class="save-message">
                <strong>✅ Benefícios salvos com sucesso!</strong>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab6:
        st.session_state.current_tab = 5
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">🏢 DADOS EMPRESA</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            empresa = st.text_input("Empresa", value="OBRA PRIMA S/A TECNOLOGIA E ADMINISTRAÇÃO DE SERVIÇOS", key="empresa")
            cargo_funcao = campo_obrigatorio("Cargo/Função", "cargo_funcao", value="ASSISTENTE I")
            data_inicio = date_input_obrigatorio("Data de Início", "data_inicio", value=datetime(2025, 11, 10))
        
        with col2:
            salario = campo_obrigatorio("Salário", "salario", value="R$ 2.946,15")
            horario_trabalho = st.text_input("Horário de Trabalho", value="Das: 08:30 às 17:30 Intervalo: 12:00 às 13:00", key="horario_trabalho")
            sindicato = st.text_input("Sindicato", value="SINEEPRES", key="sindicato")
        
        if st.button("💾 SALVAR DADOS EMPRESA", key="gravar_dados_empresa", use_container_width=True):
            campos_obrigatorios = [cargo_funcao, data_inicio, salario]
            if all(campos_obrigatorios):
                st.session_state.dados_empresa_salvos = True
                st.markdown("""
                <div class="save-message">
                    <strong>✅ Dados da empresa salvos com sucesso!</strong>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Botão final
        st.markdown("<br>", unsafe_allow_html=True)
        
        todas_abas_salvas = all([
            st.session_state.dados_pessoais_salvos,
            st.session_state.documentacao_salvos,
            st.session_state.dados_bancarios_salvos,
            st.session_state.dependentes_salvos,
            st.session_state.beneficios_salvos,
            st.session_state.dados_empresa_salvos
        ])
        
        if todas_abas_salvas:
            if st.button("🚀 ENVIAR FORMULÁRIO COMPLETO", key="enviar_formulario", use_container_width=True):
                st.session_state.formulario_enviado = True
                st.markdown("""
                <div class="success-message">
                    <h3>🎉 Formulário Enviado com Sucesso!</h3>
                    <p>Seus dados foram registrados no sistema. Agora você pode gerar o arquivo TOTVS.</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="warning-message">
                <strong>⚠️ Atenção</strong>
                <p>Para enviar o formulário, é necessário salvar todas as abas anteriores.</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Seção de geração do arquivo
    if st.session_state.formulario_enviado:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">📄 GERAR ARQUIVO TOTVS</h2>', unsafe_allow_html=True)
        
        if st.button("⚡ GERAR ARQUIVO TXT TOTVS", key="gerar_txt", use_container_width=True, type="primary"):
            with st.spinner("Gerando arquivo TOTVS..."):
                time.sleep(2)
                try:
                    conteudo_txt = gerar_arquivo_totvs()
                    cpf_limpo = ''.join(filter(str.isdigit, st.session_state.get('cpf', '')))
                    nome_arquivo = f"CADASTRO_{cpf_limpo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    
                    st.markdown(get_download_link(conteudo_txt, nome_arquivo), unsafe_allow_html=True)
                    
                    with st.expander("📋 Visualizar Conteúdo do Arquivo"):
                        st.text_area("", conteudo_txt, height=300, key="preview_arquivo")
                    
                    st.balloons()
                    st.success("✅ Arquivo TOTVS gerado com sucesso!")
                    
                except Exception as e:
                    st.error(f"❌ Erro ao gerar arquivo: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()