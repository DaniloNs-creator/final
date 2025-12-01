import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import time

# Configuração da página para layout compacto
st.set_page_config(
    page_title="Cadastro de Funcionário - TOTVS",
    page_icon="👨‍💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS ultra compacto sem espaços desnecessários
st.markdown("""
<style>
    /* Reset completo para remover espaços */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .main {
        background: #ffffff;
        min-height: 100vh;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Header ultra compacto */
    .main-header {
        font-size: 1.4rem;
        font-weight: 600;
        color: #1f2937;
        margin: 0;
        padding: 0.25rem 0 0.1rem 0;
    }
    
    .header-subtitle {
        color: #6b7280;
        font-size: 0.75rem;
        margin: 0 0 0.5rem 0;
        font-weight: 400;
    }
    
    /* Container principal sem margens */
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        background: white;
    }
    
    /* Abas ultra compactas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #f9fafb;
        padding: 0;
        border-bottom: 1px solid #e5e7eb;
        margin: 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        background: transparent !important;
        color: #6b7280 !important;
        font-weight: 500;
        border: none !important;
        border-radius: 0 !important;
        margin: 0 !important;
        padding: 0 12px !important;
        position: relative;
        transition: all 0.2s ease;
        border-bottom: 2px solid transparent !important;
        font-size: 0.8rem;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #374151 !important;
        background: #f3f4f6 !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: #2563eb !important;
        background: white !important;
        border-bottom: 2px solid #2563eb !important;
    }
    
    /* Containers de formulário ultra compactos */
    .form-container {
        background: white;
        padding: 0.75rem;
        animation: fadeIn 0.3s ease-out;
        margin: 0;
    }
    
    .section-header {
        font-size: 1rem;
        font-weight: 600;
        color: #1f2937;
        margin: 0 0 0.75rem 0;
        padding: 0;
    }
    
    /* Grid responsivo compacto */
    .form-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 0.5rem;
        margin: 0 0 0.75rem 0;
    }
    
    /* Campos de entrada ultra compactos */
    .stTextInput>div>div>input, 
    .stDateInput>div>div>input, 
    .stSelectbox>div>div>select {
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 0.8rem;
        transition: all 0.2s ease;
        background: white;
        margin: 0;
    }
    
    .stTextInput>div>div>input:focus, 
    .stDateInput>div>div>input:focus, 
    .stSelectbox>div>div>select:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
        outline: none;
    }
    
    /* Radio buttons ultra compactos */
    .stRadio>div {
        gap: 4px;
        flex-wrap: wrap;
        margin: 0;
    }
    
    .stRadio>div>label {
        background: #f9fafb;
        padding: 6px 10px;
        border-radius: 4px;
        border: 1px solid #e5e7eb;
        transition: all 0.2s ease;
        flex: 1;
        min-width: 80px;
        text-align: center;
        font-size: 0.75rem;
        margin: 0;
    }
    
    .stRadio>div>label:hover {
        border-color: #2563eb;
        background: #f0f4ff;
    }
    
    /* Botões ultra compactos */
    .stButton button {
        background: #2563eb;
        color: white;
        font-weight: 500;
        border: none;
        padding: 6px 16px;
        border-radius: 4px;
        width: 100%;
        transition: all 0.2s ease;
        font-size: 0.8rem;
        margin: 0;
    }
    
    .stButton button:hover {
        background: #1d4ed8;
    }
    
    .save-button button {
        background: #059669 !important;
    }
    
    .save-button button:hover {
        background: #047857 !important;
    }
    
    /* Tabela ultra compacta */
    .dependent-table {
        width: 100%;
        border-collapse: collapse;
        margin: 0.5rem 0;
        font-size: 0.75rem;
    }
    
    .dependent-table th {
        background: #f9fafb;
        color: #374151;
        padding: 6px 8px;
        text-align: left;
        font-weight: 600;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .dependent-table td {
        padding: 6px 8px;
        border-bottom: 1px solid #f3f4f6;
    }
    
    .dependent-table tr:hover td {
        background: #f9fafb;
    }
    
    /* Mensagens ultra compactas */
    .success-message {
        background: #f0fdf4;
        color: #166534;
        padding: 0.5rem;
        border-radius: 4px;
        border: 1px solid #bbf7d0;
        margin: 0.5rem 0;
        font-size: 0.8rem;
    }
    
    .save-message {
        background: #f0f9ff;
        color: #0369a1;
        padding: 0.5rem;
        border-radius: 4px;
        border: 1px solid #bae6fd;
        margin: 0.5rem 0;
        font-size: 0.8rem;
    }
    
    .warning-message {
        background: #fffbeb;
        color: #92400e;
        padding: 0.5rem;
        border-radius: 4px;
        border: 1px solid #fed7aa;
        margin: 0.5rem 0;
        font-size: 0.8rem;
    }
    
    /* Progresso ultra compacto */
    .progress-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 0.5rem 0;
        padding: 0;
    }
    
    .progress-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        position: relative;
    }
    
    .step-number {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: #f3f4f6;
        color: #6b7280;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 500;
        font-size: 0.65rem;
        margin-bottom: 0.1rem;
        transition: all 0.3s ease;
    }
    
    .step-label {
        font-size: 0.65rem;
        color: #6b7280;
        font-weight: 500;
        text-align: center;
    }
    
    .progress-step.active .step-number {
        background: #2563eb;
        color: white;
    }
    
    .progress-step.completed .step-number {
        background: #059669;
        color: white;
    }
    
    .progress-step.completed .step-label {
        color: #059669;
    }
    
    .progress-connector {
        flex: 1;
        height: 1px;
        background: #e5e7eb;
        margin: 0 1px;
        position: relative;
        top: -10px;
    }
    
    .progress-connector.completed {
        background: #059669;
    }
    
    /* Cards informativos ultra compactos */
    .info-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        padding: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.75rem;
    }
    
    .info-card h3 {
        color: #374151;
        margin-bottom: 0.1rem;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .info-card p {
        color: #6b7280;
        font-size: 0.7rem;
        line-height: 1.3;
    }
    
    /* Labels dos campos ultra compactos */
    .field-label {
        font-weight: 500;
        color: #374151;
        margin-bottom: 0.1rem;
        display: block;
        font-size: 0.8rem;
    }
    
    .field-label.required::after {
        content: '*';
        color: #dc2626;
        margin-left: 1px;
    }
    
    /* Animações suaves */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    /* Remove todos os espaços padrão do Streamlit */
    .stApp {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .block-container {
        padding: 0.5rem 1rem !important;
        max-width: 1200px !important;
    }
    
    /* Remove espaços entre elementos do Streamlit */
    div[data-testid="stVerticalBlock"] > div {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.2rem;
        }
        
        .form-container {
            padding: 0.5rem;
        }
        
        .form-grid {
            grid-template-columns: 1fr;
            gap: 0.25rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0 8px !important;
            font-size: 0.7rem;
        }
        
        .progress-container {
            padding: 0;
        }
        
        .step-label {
            font-size: 0.6rem;
        }
        
        .block-container {
            padding: 0.25rem 0.5rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Funções de validação e formatação (mantidas)
def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11: return False
    if cpf == cpf[0] * 11: return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = 0 if (soma % 11) < 2 else 11 - (soma % 11)
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = 0 if (soma % 11) < 2 else 11 - (soma % 11)
    return int(cpf[9]) == digito1 and int(cpf[10]) == digito2

def formatar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf

def formatar_valor(valor):
    if not valor: return "0000000000000"
    return ''.join(filter(str.isdigit, str(valor))).zfill(13)

def formatar_texto(texto, tamanho):
    if not texto: texto = ""
    texto = str(texto)
    return texto[:tamanho] if len(texto) > tamanho else texto.ljust(tamanho)

def formatar_data(data):
    if isinstance(data, datetime): return data.strftime("%d%m%Y")
    elif isinstance(data, str):
        try: return datetime.strptime(data, "%Y-%m-%d").strftime("%d%m%Y")
        except: return "00000000"
    else: return "00000000"

def gerar_arquivo_totvs():
    header = "0000" + formatar_texto("EMPRESA EXEMPLO LTDA", 35) + formatar_texto("12345678000199", 14) + datetime.now().strftime("%d%m%Y") + "001" + " " * 935 + "\n"
    
    cpf_limpo = ''.join(filter(str.isdigit, st.session_state.get('cpf', '')))
    
    registro_0100 = "0100" + formatar_texto(cpf_limpo, 11) + formatar_texto(st.session_state.get('nome_completo', ''), 70)
    registro_0100 += formatar_data(st.session_state.get('data_nascimento', '')) + ("M" if st.session_state.get('sexo', '') == 'Masculino' else "F")
    registro_0100 += "1" if st.session_state.get('estado_civil', '') == 'Solteiro' else "2"
    
    grau_instrucao = st.session_state.get('grau_instrucao', '')
    if 'Fundamental' in grau_instrucao: registro_0100 += "01"
    elif 'Médio' in grau_instrucao: registro_0100 += "02"
    elif 'Superior' in grau_instrucao: registro_0100 += "03"
    elif 'Pós' in grau_instrucao: registro_0100 += "04"
    else: registro_0100 += "01"
    
    registro_0100 += "1" + formatar_texto(st.session_state.get('nome_mae', ''), 70) + formatar_texto(st.session_state.get('nome_pai', ''), 70)
    registro_0100 += formatar_texto(st.session_state.get('endereco', ''), 60) + formatar_texto(st.session_state.get('bairro', ''), 40)
    
    cidade = st.session_state.get('cidade', '')
    if ' - ' in cidade:
        parts = cidade.split(' - ')
        registro_0100 += formatar_texto(parts[0], 40) + formatar_texto(parts[1] if len(parts) > 1 else '', 2)
    else:
        registro_0100 += formatar_texto(cidade, 40) + "  "
    
    registro_0100 += formatar_texto(''.join(filter(str.isdigit, st.session_state.get('cep', ''))), 8)
    registro_0100 += formatar_texto(st.session_state.get('email', ''), 60)
    
    raca_cor = st.session_state.get('raca_cor', '')
    if raca_cor == 'Branca': registro_0100 += "01"
    elif raca_cor == 'Negra': registro_0100 += "02"
    elif raca_cor == 'Parda': registro_0100 += "03"
    elif raca_cor == 'Amarela': registro_0100 += "04"
    else: registro_0100 += "01"
    
    registro_0100 += " " * 572 + "\n"
    
    registro_0200 = "0200" + formatar_texto(cpf_limpo, 11) + formatar_texto(''.join(filter(str.isdigit, st.session_state.get('rg', ''))), 15)
    registro_0200 += formatar_texto(st.session_state.get('orgao_exp', ''), 10) + formatar_data(st.session_state.get('data_expedicao', ''))
    registro_0200 += formatar_texto(''.join(filter(str.isdigit, st.session_state.get('ctps', ''))), 11) + formatar_texto(st.session_state.get('serie', ''), 5)
    registro_0200 += formatar_texto(st.session_state.get('uf_ctps', ''), 2) + formatar_data(st.session_state.get('data_exp_ctps', ''))
    registro_0200 += formatar_texto(''.join(filter(str.isdigit, st.session_state.get('pis', ''))), 11) + formatar_texto(''.join(filter(str.isdigit, st.session_state.get('titulo_eleitor', ''))), 12)
    registro_0200 += formatar_texto(st.session_state.get('zona', ''), 4) + formatar_texto(st.session_state.get('secao', ''), 4)
    registro_0200 += formatar_texto(st.session_state.get('carteira_habilitacao', ''), 15) + formatar_texto(st.session_state.get('categoria_hab', ''), 2)
    registro_0200 += formatar_data(st.session_state.get('vencimento_hab', '')) + formatar_texto(st.session_state.get('uf_hab', ''), 2)
    registro_0200 += formatar_texto(st.session_state.get('reservista', ''), 15) + " " * 850 + "\n"
    
    registro_0300 = "0300" + formatar_texto(cpf_limpo, 11) + formatar_texto(st.session_state.get('banco', ''), 3)
    registro_0300 += formatar_texto(st.session_state.get('agencia', ''), 5) + formatar_texto(st.session_state.get('conta', ''), 10)
    registro_0300 += formatar_texto(st.session_state.get('chave_pix', ''), 77) + " " * 882 + "\n"
    
    registro_0400 = "0400" + formatar_texto(cpf_limpo, 11) + formatar_texto("00217252923", 11)
    registro_0400 += formatar_texto("LAURA HELENA MATOS FERREIRA LEITE", 70) + formatar_data("2024-03-13") + "FSN06" + " " * 864 + "\n"
    
    registro_0500 = "0500" + formatar_texto(cpf_limpo, 11) + formatar_data(st.session_state.get('data_inicio', ''))
    registro_0500 += formatar_texto(st.session_state.get('cargo_funcao', ''), 50) + formatar_valor(st.session_state.get('salario', ''))
    registro_0500 += formatar_texto(st.session_state.get('horario_trabalho', ''), 100) + formatar_texto(st.session_state.get('centro_custo', ''), 30)
    registro_0500 += formatar_texto(st.session_state.get('sindicato', ''), 50)
    
    beneficios = [
        st.session_state.get('vale_transporte', '') == "Sim",
        st.session_state.get('vale_alimentacao', '') == "Sim",
        st.session_state.get('vale_refeicao', '') == "Sim",
        st.session_state.get('adicional_noturno', '') == "Sim",
        st.session_state.get('insalubridade', '') == "Sim",
        st.session_state.get('periculosidade', '') == "Sim"
    ]
    
    for beneficio in beneficios:
        registro_0500 += "S" if beneficio else "N"
    
    registro_0500 += " " * 698 + "\n"
    
    trailer = "99000006" + " " * 984 + "\n"
    
    return header + registro_0100 + registro_0200 + registro_0300 + registro_0400 + registro_0500 + trailer

def get_download_link(content, filename):
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="{filename}" class="stButton button">📥 Baixar Arquivo TXT</a>'

def initialize_session_state():
    defaults = {
        'dados_pessoais_salvos': False, 'documentacao_salvos': False, 'dados_bancarios_salvos': False,
        'dependentes_salvos': False, 'beneficios_salvos': False, 'dados_empresa_salvos': False,
        'formulario_enviado': False, 'arquivo_gerado': False, 'current_tab': 0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def campo_obrigatorio(label, key, **kwargs):
    st.markdown(f'<div class="field-label required">{label}</div>', unsafe_allow_html=True)
    return st.text_input("", key=key, **kwargs)

def campo_opcional(label, key, **kwargs):
    st.markdown(f'<div class="field-label">{label}</div>', unsafe_allow_html=True)
    return st.text_input("", key=key, **kwargs)

def selectbox_obrigatorio(label, key, options, **kwargs):
    st.markdown(f'<div class="field-label required">{label}</div>', unsafe_allow_html=True)
    return st.selectbox("", options, key=key, **kwargs)

def selectbox_opcional(label, key, options, **kwargs):
    st.markdown(f'<div class="field-label">{label}</div>', unsafe_allow_html=True)
    return st.selectbox("", options, key=key, **kwargs)

def date_input_obrigatorio(label, key, **kwargs):
    st.markdown(f'<div class="field-label required">{label}</div>', unsafe_allow_html=True)
    return st.date_input("", key=key, **kwargs)

def date_input_opcional(label, key, **kwargs):
    st.markdown(f'<div class="field-label">{label}</div>', unsafe_allow_html=True)
    return st.date_input("", key=key, **kwargs)

def radio_obrigatorio(label, key, options, **kwargs):
    st.markdown(f'<div class="field-label required">{label}</div>', unsafe_allow_html=True)
    return st.radio("", options, key=key, **kwargs)

def radio_opcional(label, key, options, **kwargs):
    st.markdown(f'<div class="field-label">{label}</div>', unsafe_allow_html=True)
    return st.radio("", options, key=key, **kwargs)

def main():
    initialize_session_state()
    
    # Header ultra compacto no topo absoluto
    st.markdown('<div class="main-header">Cadastro de Funcionário</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-subtitle">Sistema de integração TOTVS</div>', unsafe_allow_html=True)
    
    # Barra de progresso ultra compacta
    steps = [
        ("Dados", st.session_state.dados_pessoais_salvos),
        ("Doc", st.session_state.documentacao_salvos),
        ("Banco", st.session_state.dados_bancarios_salvos),
        ("Dep", st.session_state.dependentes_salvos),
        ("Ben", st.session_state.beneficios_salvos),
        ("Emp", st.session_state.dados_empresa_salvos)
    ]
    
    st.markdown('<div class="progress-container">', unsafe_allow_html=True)
    for i, (label, completed) in enumerate(steps):
        status = "completed" if completed else "active" if i == st.session_state.current_tab else ""
        st.markdown(f'''
            <div class="progress-step {status}">
                <div class="step-number">{i+1}</div>
                <div class="step-label">{label}</div>
            </div>
            {f'<div class="progress-connector completed"></div>' if i < len(steps)-1 and completed else f'<div class="progress-connector"></div>' if i < len(steps)-1 else ''}
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Abas ultra compactas
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👤 Dados", "📄 Doc", "💳 Banco", "👨‍👩‍👧 Dep", "🎁 Ben", "🏢 Emp"])
    
    with tab1:
        st.session_state.current_tab = 0
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Dados Pessoais</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-grid">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nome_completo = campo_obrigatorio("Nome Completo", "nome_completo", value="ADRIELLY DOS SANTOS MATOS")
            estado_civil = radio_obrigatorio("Estado Civil", "estado_civil", ["Solteiro", "Casado"], index=0)
            sexo = radio_obrigatorio("Sexo", "sexo", ["Masculino", "Feminino"], index=1)
            data_nascimento = date_input_obrigatorio("Data Nascimento", "data_nascimento", value=datetime(1999, 7, 8))
        
        with col2:
            naturalidade = campo_opcional("Naturalidade", "naturalidade", value="ARCOVERDE - PE")
            endereco = campo_obrigatorio("Endereço", "endereco", value="R POETA FRANCISCO FERREIRA LEITE, 40, BL 04 AP 12")
            bairro = campo_obrigatorio("Bairro", "bairro", value="CRISTO REI")
            cidade = campo_obrigatorio("Cidade", "cidade", value="CURITIBA - PR")
        
        with col3:
            cep = campo_obrigatorio("CEP", "cep", value="80050-360")
            nome_pai = campo_opcional("Nome Pai", "nome_pai", value="ANTONIO MARCOS DA SILVA MATOS")
            nome_mae = campo_obrigatorio("Nome Mãe", "nome_mae", value="ANDRÉA DOS SANTOS MELO")
        
        col4, col5 = st.columns(2)
        with col4:
            grau_instrucao = selectbox_obrigatorio("Grau Instrução", "grau_instrucao", 
                ["Fundamental", "Médio", "Superior", "Pós"], index=2)
        with col5:
            email = campo_opcional("E-mail", "email", value="adriellymatos8@gmail.com")
            raca_cor = selectbox_obrigatorio("Raça/Cor", "raca_cor", 
                ["Branca", "Negra", "Parda", "Amarela"], index=0)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Salvar Dados", key="gravar_dados_pessoais", use_container_width=True):
            if all([nome_completo, data_nascimento, endereco, bairro, cidade, cep, nome_mae]):
                st.session_state.dados_pessoais_salvos = True
                st.markdown('<div class="save-message">Dados salvos</div>', unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Preencha os campos obrigatórios")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.session_state.current_tab = 1
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Documentação</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-grid">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            rg = campo_obrigatorio("RG", "rg", value="060.375.391-46")
            orgao_exp = campo_obrigatorio("Órgão Expedidor", "orgao_exp", value="SESP/PR")
            data_expedicao = date_input_obrigatorio("Data Expedição", "data_expedicao", value=datetime(2024, 5, 26))
            cpf = campo_obrigatorio("CPF", "cpf", value="060.375.391-46")
            if cpf and not validar_cpf(cpf):
                st.error("CPF inválido")
        
        with col2:
            titulo_eleitor = campo_opcional("Título Eleitor", "titulo_eleitor", value="0268 4243 1929")
            ctps = campo_obrigatorio("CTPS", "ctps", value="7551374")
            serie = campo_obrigatorio("Série", "serie", value="00050")
            uf_ctps = campo_obrigatorio("UF", "uf_ctps", value="MS")
            data_exp_ctps = date_input_obrigatorio("Data CTPS", "data_exp_ctps", value=datetime(2020, 3, 27))
            pis = campo_obrigatorio("PIS", "pis", value="160.94867.47-46")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Salvar Documentação", key="gravar_documentacao", use_container_width=True):
            campos = [rg, orgao_exp, data_expedicao, cpf, ctps, serie, uf_ctps, data_exp_ctps, pis]
            if all(campos) and validar_cpf(cpf):
                st.session_state.documentacao_salvos = True
                st.markdown('<div class="save-message">Documentação salva</div>', unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Preencha os campos obrigatórios")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.session_state.current_tab = 2
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Dados Bancários</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown('<h3>Opcional</h3><p>Campos opcionais</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            banco = campo_opcional("Banco", "banco", value="MÊNTORE BANK")
        
        with col2:
            agencia = campo_opcional("Agência", "agencia")
        
        with col3:
            conta = campo_opcional("Conta", "conta")
        
        chave_pix = campo_opcional("PIX", "chave_pix")
        
        if st.button("Salvar Banco", key="gravar_dados_bancarios", use_container_width=True):
            st.session_state.dados_bancarios_salvos = True
            st.markdown('<div class="save-message">Dados salvos</div>', unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab4:
        st.session_state.current_tab = 3
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Dependentes</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown('<h3>Opcional</h3><p>Campos opcionais</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <table class="dependent-table">
            <tr>
                <th>Nome</th>
                <th>CPF</th>
                <th>Nascimento</th>
                <th>IRRF</th>
                <th>Família</th>
            </tr>
            <tr>
                <td>LAURA HELENA MATOS</td>
                <td>002.172.529-23</td>
                <td>13/03/2024</td>
                <td>SIM</td>
                <td>NÃO</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)
        
        if st.button("Salvar Dependentes", key="gravar_dependentes", use_container_width=True):
            st.session_state.dependentes_salvos = True
            st.markdown('<div class="save-message">Dependentes salvos</div>', unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab5:
        st.session_state.current_tab = 4
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Benefícios</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown('<h3>Opcional</h3><p>Campos opcionais</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            vale_transporte = radio_opcional("Vale Transporte", "vale_transporte", ["Sim", "Não"], index=0)
            vale_alimentacao = radio_opcional("Vale Alimentação", "vale_alimentacao", ["Sim", "Não"], index=0)
        
        with col2:
            vale_refeicao = radio_opcional("Vale Refeição", "vale_refeicao", ["Sim", "Não"], index=1)
            cesta_basica = radio_opcional("Cesta Básica", "cesta_basica", ["Sim", "Não"], index=1)
        
        if st.button("Salvar Benefícios", key="gravar_beneficios", use_container_width=True):
            st.session_state.beneficios_salvos = True
            st.markdown('<div class="save-message">Benefícios salvos</div>', unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab6:
        st.session_state.current_tab = 5
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Dados Empresa</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-grid">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            empresa = campo_opcional("Empresa", "empresa", value="OBRA PRIMA S/A")
            cargo_funcao = campo_obrigatorio("Cargo", "cargo_funcao", value="ASSISTENTE I")
            data_inicio = date_input_obrigatorio("Data Início", "data_inicio", value=datetime(2025, 11, 10))
        
        with col2:
            salario = campo_obrigatorio("Salário", "salario", value="R$ 2.946,15")
            horario_trabalho = campo_opcional("Horário", "horario_trabalho", value="08:30-17:30")
            sindicato = campo_opcional("Sindicato", "sindicato", value="SINEEPRES")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Salvar Empresa", key="gravar_dados_empresa", use_container_width=True):
            if all([cargo_funcao, data_inicio, salario]):
                st.session_state.dados_empresa_salvos = True
                st.markdown('<div class="save-message">Dados salvos</div>', unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Preencha os campos obrigatórios")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Botão final ultra compacto
        todas_salvas = all([st.session_state.dados_pessoais_salvos, st.session_state.documentacao_salvos,
                           st.session_state.dados_bancarios_salvos, st.session_state.dependentes_salvos,
                           st.session_state.beneficios_salvos, st.session_state.dados_empresa_salvos])
        
        if todas_salvas:
            if st.button("Enviar Formulário", key="enviar_formulario", use_container_width=True):
                st.session_state.formulario_enviado = True
                st.markdown('<div class="success-message">Formulário enviado</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warning-message">Salve todas as abas</div>', unsafe_allow_html=True)
    
    # Geração do arquivo ultra compacta
    if st.session_state.formulario_enviado:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Gerar TOTVS</div>', unsafe_allow_html=True)
        
        if st.button("Gerar Arquivo TXT", key="gerar_txt", use_container_width=True):
            with st.spinner("Gerando..."):
                time.sleep(1)
                try:
                    conteudo_txt = gerar_arquivo_totvs()
                    cpf_limpo = ''.join(filter(str.isdigit, st.session_state.get('cpf', '')))
                    nome_arquivo = f"CADASTRO_{cpf_limpo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    
                    st.markdown(get_download_link(conteudo_txt, nome_arquivo), unsafe_allow_html=True)
                    
                    with st.expander("Visualizar"):
                        st.text_area("", conteudo_txt, height=150, key="preview_arquivo")
                    
                    st.success("Arquivo gerado")
                    
                except Exception as e:
                    st.error(f"Erro: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()