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

# CSS moderno e clean
st.markdown("""
<style>
    /* Reset e base */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    .main {
        background: #f8fafc;
        min-height: 100vh;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        color: #1e293b;
        margin-bottom: 1.5rem;
        padding-top: 2rem;
        background: linear-gradient(135deg, #1e293b 0%, #475569 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .header-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 3rem;
        font-weight: 400;
    }
    
    /* Container principal */
    .main-container {
        max-width: 1400px;
        margin: 0 auto;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
    
    /* Abas modernas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #f8fafc;
        padding: 0 24px;
        border-bottom: 1px solid #e2e8f0;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        background: transparent !important;
        color: #64748b !important;
        font-weight: 500;
        border: none !important;
        border-radius: 0 !important;
        margin: 0 !important;
        padding: 0 24px !important;
        position: relative;
        transition: all 0.2s ease;
        border-bottom: 2px solid transparent !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #334155 !important;
        background: #f1f5f9 !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: #2563eb !important;
        background: white !important;
        border-bottom: 2px solid #2563eb !important;
    }
    
    /* Containers de formulário */
    .form-container {
        background: white;
        padding: 2rem;
        animation: fadeIn 0.3s ease-out;
    }
    
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .section-header::before {
        content: '';
        width: 4px;
        height: 24px;
        background: #2563eb;
        border-radius: 2px;
    }
    
    /* Grid responsivo */
    .form-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    /* Campos de entrada */
    .stTextInput>div>div>input, 
    .stDateInput>div>div>input, 
    .stSelectbox>div>div>select {
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 14px;
        transition: all 0.2s ease;
        background: white;
    }
    
    .stTextInput>div>div>input:focus, 
    .stDateInput>div>div>input:focus, 
    .stSelectbox>div>div>select:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        outline: none;
    }
    
    /* Radio buttons modernos */
    .stRadio>div {
        gap: 12px;
        flex-wrap: wrap;
    }
    
    .stRadio>div>label {
        background: #f8fafc;
        padding: 12px 20px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        transition: all 0.2s ease;
        flex: 1;
        min-width: 120px;
        text-align: center;
    }
    
    .stRadio>div>label:hover {
        border-color: #2563eb;
        background: #f0f4ff;
    }
    
    .stRadio>div>label[data-baseweb="radio"]>div:first-child {
        border-color: #64748b;
    }
    
    /* Botões */
    .stButton button {
        background: #2563eb;
        color: white;
        font-weight: 500;
        border: none;
        padding: 12px 32px;
        border-radius: 8px;
        width: 100%;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
    
    .stButton button:hover {
        background: #1d4ed8;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .save-button button {
        background: #059669 !important;
    }
    
    .save-button button:hover {
        background: #047857 !important;
    }
    
    .send-button button {
        background: #7c3aed !important;
    }
    
    .send-button button:hover {
        background: #6d28d9 !important;
    }
    
    .generate-button button {
        background: #dc2626 !important;
    }
    
    .generate-button button:hover {
        background: #b91c1c !important;
    }
    
    /* Tabela */
    .dependent-table {
        width: 100%;
        border-collapse: collapse;
        margin: 1.5rem 0;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .dependent-table th {
        background: #f8fafc;
        color: #374151;
        padding: 12px 16px;
        text-align: left;
        font-weight: 600;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .dependent-table td {
        padding: 12px 16px;
        border-bottom: 1px solid #f3f4f6;
    }
    
    .dependent-table tr:hover td {
        background: #f9fafb;
    }
    
    /* Mensagens */
    .success-message {
        background: #f0fdf4;
        color: #166534;
        padding: 1.25rem;
        border-radius: 8px;
        border: 1px solid #bbf7d0;
        margin: 1rem 0;
    }
    
    .save-message {
        background: #f0f9ff;
        color: #0369a1;
        padding: 1rem 1.25rem;
        border-radius: 8px;
        border: 1px solid #bae6fd;
        margin: 1rem 0;
    }
    
    .warning-message {
        background: #fffbeb;
        color: #92400e;
        padding: 1rem 1.25rem;
        border-radius: 8px;
        border: 1px solid #fed7aa;
        margin: 1rem 0;
    }
    
    /* Progresso */
    .progress-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 2rem 0;
        padding: 0 2rem;
    }
    
    .progress-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        position: relative;
    }
    
    .step-number {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: #e2e8f0;
        color: #64748b;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 0.5rem;
        transition: all 0.3s ease;
        z-index: 2;
    }
    
    .step-label {
        font-size: 12px;
        color: #64748b;
        font-weight: 500;
        text-align: center;
    }
    
    .progress-step.active .step-number {
        background: #2563eb;
        color: white;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
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
        height: 2px;
        background: #e2e8f0;
        margin: 0 8px;
        position: relative;
        top: -24px;
    }
    
    .progress-connector.completed {
        background: #059669;
    }
    
    /* Cards informativos */
    .info-card {
        background: #f0f9ff;
        border: 1px solid #bae6fd;
        border-radius: 8px;
        padding: 1.25rem;
        margin: 1.5rem 0;
    }
    
    .info-card h3 {
        color: #0369a1;
        margin-bottom: 0.5rem;
        font-size: 1rem;
        font-weight: 600;
    }
    
    .info-card p {
        color: #64748b;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    
    /* Indicadores obrigatórios */
    .required-field {
        color: #dc2626;
        font-weight: 600;
    }
    
    .field-label {
        font-weight: 500;
        color: #374151;
        margin-bottom: 0.5rem;
        display: block;
        font-size: 14px;
    }
    
    /* Animações */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    /* Utilitários */
    .text-center { text-align: center; }
    .mb-2 { margin-bottom: 0.5rem; }
    .mb-4 { margin-bottom: 1rem; }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem;
            padding-top: 1rem;
        }
        
        .form-container {
            padding: 1.5rem;
        }
        
        .form-grid {
            grid-template-columns: 1fr;
            gap: 1rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0 16px !important;
            font-size: 0.9rem;
        }
        
        .progress-container {
            padding: 0 1rem;
        }
        
        .step-label {
            font-size: 10px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Funções de validação e formatação (mantidas da versão anterior)
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
    
    # Registro 0100 - Dados Pessoais
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
    
    # Registro 0200 - Documentação
    registro_0200 = "0200" + formatar_texto(cpf_limpo, 11) + formatar_texto(''.join(filter(str.isdigit, st.session_state.get('rg', ''))), 15)
    registro_0200 += formatar_texto(st.session_state.get('orgao_exp', ''), 10) + formatar_data(st.session_state.get('data_expedicao', ''))
    registro_0200 += formatar_texto(''.join(filter(str.isdigit, st.session_state.get('ctps', ''))), 11) + formatar_texto(st.session_state.get('serie', ''), 5)
    registro_0200 += formatar_texto(st.session_state.get('uf_ctps', ''), 2) + formatar_data(st.session_state.get('data_exp_ctps', ''))
    registro_0200 += formatar_texto(''.join(filter(str.isdigit, st.session_state.get('pis', ''))), 11) + formatar_texto(''.join(filter(str.isdigit, st.session_state.get('titulo_eleitor', ''))), 12)
    registro_0200 += formatar_texto(st.session_state.get('zona', ''), 4) + formatar_texto(st.session_state.get('secao', ''), 4)
    registro_0200 += formatar_texto(st.session_state.get('carteira_habilitacao', ''), 15) + formatar_texto(st.session_state.get('categoria_hab', ''), 2)
    registro_0200 += formatar_data(st.session_state.get('vencimento_hab', '')) + formatar_texto(st.session_state.get('uf_hab', ''), 2)
    registro_0200 += formatar_texto(st.session_state.get('reservista', ''), 15) + " " * 850 + "\n"
    
    # Registro 0300 - Dados Bancários
    registro_0300 = "0300" + formatar_texto(cpf_limpo, 11) + formatar_texto(st.session_state.get('banco', ''), 3)
    registro_0300 += formatar_texto(st.session_state.get('agencia', ''), 5) + formatar_texto(st.session_state.get('conta', ''), 10)
    registro_0300 += formatar_texto(st.session_state.get('chave_pix', ''), 77) + " " * 882 + "\n"
    
    # Registro 0400 - Dependentes
    registro_0400 = "0400" + formatar_texto(cpf_limpo, 11) + formatar_texto("00217252923", 11)
    registro_0400 += formatar_texto("LAURA HELENA MATOS FERREIRA LEITE", 70) + formatar_data("2024-03-13") + "FSN06" + " " * 864 + "\n"
    
    # Registro 0500 - Dados Empresa
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
    return f'<a href="data:file/txt;base64,{b64}" download="{filename}" class="stButton button generate-button">📥 BAIXAR ARQUIVO TXT</a>'

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
    return st.text_input(f"{label} <span class='required-field'>*</span>", key=key, **kwargs)

def selectbox_obrigatorio(label, key, options, **kwargs):
    return st.selectbox(f"{label} <span class='required-field'>*</span>", options, key=key, **kwargs)

def date_input_obrigatorio(label, key, **kwargs):
    return st.date_input(f"{label} <span class='required-field'>*</span>", key=key, **kwargs)

def radio_obrigatorio(label, key, options, **kwargs):
    return st.radio(f"{label} <span class='required-field'>*</span>", options, key=key, **kwargs)

def main():
    initialize_session_state()
    
    st.markdown('<div class="main">', unsafe_allow_html=True)
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">Sistema de Cadastro de Funcionários</h1>', unsafe_allow_html=True)
    st.markdown('<p class="header-subtitle">Preencha o formulário completo para gerar o arquivo de integração TOTVS</p>', unsafe_allow_html=True)
    
    # Barra de progresso
    steps = [
        ("Dados Pessoais", st.session_state.dados_pessoais_salvos),
        ("Documentação", st.session_state.documentacao_salvos),
        ("Dados Bancários", st.session_state.dados_bancarios_salvos),
        ("Dependentes", st.session_state.dependentes_salvos),
        ("Benefícios", st.session_state.beneficios_salvos),
        ("Empresa", st.session_state.dados_empresa_salvos)
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
    
    # Abas
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "👤 Dados Pessoais", "📄 Documentação", "💳 Dados Bancários", 
        "👨‍👩‍👧 Dependentes", "🎁 Benefícios", "🏢 Dados Empresa"
    ])
    
    with tab1:
        st.session_state.current_tab = 0
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">Dados Pessoais</h2>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-grid">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nome_completo = campo_obrigatorio("Nome Completo", "nome_completo", value="ADRIELLY DOS SANTOS MATOS")
            estado_civil = radio_obrigatorio("Estado Civil", "estado_civil", ["Solteiro", "Casado"], index=0)
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
            grau_instrucao = selectbox_obrigatorio("Grau de Instrução", "grau_instrucao", 
                ["Ensino Fundamental", "Ensino Médio", "Curso Superior", "Pós Graduação"], index=2)
        with col5:
            email = st.text_input("E-mail", value="adriellymatos8@gmail.com", key="email")
            raca_cor = selectbox_obrigatorio("Raça/Cor", "raca_cor", 
                ["Branca", "Negra", "Parda", "Amarela"], index=0)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("💾 Salvar Dados Pessoais", key="gravar_dados_pessoais", use_container_width=True):
            if all([nome_completo, data_nascimento, endereco, bairro, cidade, cep, nome_mae]):
                st.session_state.dados_pessoais_salvos = True
                st.markdown('<div class="save-message"><strong>✅ Dados pessoais salvos com sucesso!</strong></div>', unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.session_state.current_tab = 1
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">Documentação</h2>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-grid">', unsafe_allow_html=True)
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
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("💾 Salvar Documentação", key="gravar_documentacao", use_container_width=True):
            campos = [rg, orgao_exp, data_expedicao, cpf, ctps, serie, uf_ctps, data_exp_ctps, pis]
            if all(campos) and validar_cpf(cpf):
                st.session_state.documentacao_salvos = True
                st.markdown('<div class="save-message"><strong>✅ Documentação salva com sucesso!</strong></div>', unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ... (outras abas similares - mantendo a estrutura mas com design clean)
    
    with tab6:
        st.session_state.current_tab = 5
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">Dados da Empresa</h2>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-grid">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            empresa = st.text_input("Empresa", value="OBRA PRIMA S/A TECNOLOGIA E ADMINISTRAÇÃO DE SERVIÇOS", key="empresa")
            cargo_funcao = campo_obrigatorio("Cargo/Função", "cargo_funcao", value="ASSISTENTE I")
            data_inicio = date_input_obrigatorio("Data de Início", "data_inicio", value=datetime(2025, 11, 10))
        
        with col2:
            salario = campo_obrigatorio("Salário", "salario", value="R$ 2.946,15")
            horario_trabalho = st.text_input("Horário de Trabalho", value="Das: 08:30 às 17:30 Intervalo: 12:00 às 13:00", key="horario_trabalho")
            sindicato = st.text_input("Sindicato", value="SINEEPRES", key="sindicato")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("💾 Salvar Dados da Empresa", key="gravar_dados_empresa", use_container_width=True):
            if all([cargo_funcao, data_inicio, salario]):
                st.session_state.dados_empresa_salvos = True
                st.markdown('<div class="save-message"><strong>✅ Dados da empresa salvos com sucesso!</strong></div>', unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Botão final
        todas_salvas = all([st.session_state.dados_pessoais_salvos, st.session_state.documentacao_salvos,
                           st.session_state.dados_bancarios_salvos, st.session_state.dependentes_salvos,
                           st.session_state.beneficios_salvos, st.session_state.dados_empresa_salvos])
        
        if todas_salvas:
            if st.button("🚀 Enviar Formulário Completo", key="enviar_formulario", use_container_width=True, type="primary"):
                st.session_state.formulario_enviado = True
                st.markdown('''
                <div class="success-message">
                    <h3>✅ Formulário Enviado com Sucesso!</h3>
                    <p>Seus dados foram registrados no sistema. Agora você pode gerar o arquivo TOTVS.</p>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="warning-message">
                <strong>⚠️ Atenção</strong>
                <p>Para enviar o formulário, é necessário salvar todas as abas anteriores.</p>
            </div>
            ''', unsafe_allow_html=True)
    
    # Geração do arquivo
    if st.session_state.formulario_enviado:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">Gerar Arquivo TOTVS</h2>', unsafe_allow_html=True)
        
        if st.button("⚡ Gerar Arquivo TXT TOTVS", key="gerar_txt", use_container_width=True, type="primary"):
            with st.spinner("Gerando arquivo TOTVS..."):
                time.sleep(1)
                try:
                    conteudo_txt = gerar_arquivo_totvs()
                    cpf_limpo = ''.join(filter(str.isdigit, st.session_state.get('cpf', '')))
                    nome_arquivo = f"CADASTRO_{cpf_limpo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    
                    st.markdown(get_download_link(conteudo_txt, nome_arquivo), unsafe_allow_html=True)
                    
                    with st.expander("📋 Visualizar Conteúdo do Arquivo"):
                        st.text_area("", conteudo_txt, height=300, key="preview_arquivo")
                    
                    st.success("✅ Arquivo TOTVS gerado com sucesso!")
                    
                except Exception as e:
                    st.error(f"❌ Erro ao gerar arquivo: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()