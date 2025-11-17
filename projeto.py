import streamlit as st
import pandas as pd
from datetime import datetime
import base64

# Configuração da página
st.set_page_config(
    page_title="Formulário de Cadastro",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado para estilização avançada
st.markdown("""
<style>
    /* Estilos gerais */
    .main-header {
        font-size: 2.5rem;
        color: #1f3a60;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    
    .section-header {
        font-size: 1.5rem;
        color: #1f3a60;
        border-bottom: 2px solid #1f3a60;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    .form-container {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stButton button {
        background-color: #1f3a60;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 5px;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        background-color: #2c5282;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    .save-button {
        background-color: #28a745 !important;
    }
    
    .save-button:hover {
        background-color: #218838 !important;
    }
    
    .send-button {
        background-color: #dc3545 !important;
    }
    
    .send-button:hover {
        background-color: #c82333 !important;
    }
    
    .generate-button {
        background-color: #17a2b8 !important;
    }
    
    .generate-button:hover {
        background-color: #138496 !important;
    }
    
    /* Estilização dos campos de entrada */
    .stTextInput input, .stDateInput input, .stSelectbox select {
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 0.5rem;
    }
    
    /* Estilização dos checkboxes e radio buttons */
    .stCheckbox, .stRadio {
        margin-bottom: 0.5rem;
    }
    
    /* Estilização das abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f1f3f4;
        border-radius: 4px 4px 0px 0px;
        gap: 1rem;
        padding: 10px 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1f3a60;
        color: white;
    }
    
    /* Estilização da tabela de dependentes */
    .dependent-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
    }
    
    .dependent-table th, .dependent-table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    
    .dependent-table th {
        background-color: #1f3a60;
        color: white;
    }
    
    /* Estilização da mensagem de sucesso */
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin-top: 1rem;
    }
    
    .save-message {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #bee5eb;
        margin-top: 1rem;
    }
    
    .tab-status {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    
    .completed {
        background-color: #28a745;
        color: white;
    }
    
    .pending {
        background-color: #ffc107;
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# Função para validar CPF
def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Calcula o primeiro dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Calcula o segundo dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    # Verifica se os dígitos calculados conferem com os informados
    if int(cpf[9]) == digito1 and int(cpf[10]) == digito2:
        return True
    else:
        return False

# Função para validar e formatar CPF
def formatar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf

# Função para formatar valores numéricos
def formatar_valor(valor):
    """Remove caracteres não numéricos e formata para o layout"""
    if not valor:
        return "0000000000000"
    
    # Remove R$, pontos, vírgulas e espaços
    valor_limpo = ''.join(filter(str.isdigit, str(valor)))
    
    # Preenche com zeros à esquerda para ter 13 dígitos
    return valor_limpo.zfill(13)

# Função para formatar texto com tamanho fixo
def formatar_texto(texto, tamanho):
    """Formata texto para ter tamanho fixo, truncando ou preenchendo com espaços"""
    if not texto:
        texto = ""
    
    texto = str(texto)
    if len(texto) > tamanho:
        return texto[:tamanho]
    else:
        return texto.ljust(tamanho)

# Função para formatar data
def formatar_data(data):
    """Formata data para DDMMAAAA"""
    if isinstance(data, datetime):
        return data.strftime("%d%m%Y")
    elif isinstance(data, str):
        try:
            return datetime.strptime(data, "%Y-%m-%d").strftime("%d%m%Y")
        except:
            return "00000000"
    else:
        return "00000000"

# Função para gerar arquivo TXT conforme layout TOTVS
def gerar_arquivo_totvs():
    """Gera o arquivo TXT no formato especificado pela TOTVS"""
    
    # Registro 0000 - Header
    header = "0000"
    header += formatar_texto("EMPRESA EXEMPLO", 35)  # Nome da empresa
    header += formatar_texto("12345678000199", 14)   # CNPJ
    header += datetime.now().strftime("%d%m%Y")      # Data geração
    header += "001"                                   # Número sequencial
    header += " " * 935                              # Brancos
    header += "\n"
    
    # Registro 0100 - Dados do Funcionário
    registro_0100 = "0100"
    
    # CPF (apenas números)
    cpf_limpo = ''.join(filter(str.isdigit, st.session_state.get('cpf', '')))
    registro_0100 += formatar_texto(cpf_limpo, 11)
    
    # Nome do funcionário
    registro_0100 += formatar_texto(st.session_state.get('nome_completo', ''), 70)
    
    # Data de nascimento
    registro_0100 += formatar_data(st.session_state.get('data_nascimento', ''))
    
    # Sexo
    sexo = st.session_state.get('sexo', '')
    if sexo == 'Masculino':
        registro_0100 += "M"
    elif sexo == 'Feminino':
        registro_0100 += "F"
    else:
        registro_0100 += " "
    
    # Estado civil
    estado_civil = st.session_state.get('estado_civil', '')
    if estado_civil == 'Solteiro':
        registro_0100 += "1"
    elif estado_civil == 'Casado':
        registro_0100 += "2"
    else:
        registro_0100 += "3"
    
    # Grau de instrução
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
    
    # Nacionalidade (1 - Brasileiro)
    registro_0100 += "1"
    
    # Nome da mãe
    registro_0100 += formatar_texto(st.session_state.get('nome_mae', ''), 70)
    
    # Nome do pai
    registro_0100 += formatar_texto(st.session_state.get('nome_pai', ''), 70)
    
    # Endereço
    registro_0100 += formatar_texto(st.session_state.get('endereco', ''), 60)
    
    # Bairro
    registro_0100 += formatar_texto(st.session_state.get('bairro', ''), 40)
    
    # Cidade
    cidade = st.session_state.get('cidade', '')
    if ' - ' in cidade:
        cidade_parts = cidade.split(' - ')
        registro_0100 += formatar_texto(cidade_parts[0], 40)
        registro_0100 += formatar_texto(cidade_parts[1] if len(cidade_parts) > 1 else '', 2)
    else:
        registro_0100 += formatar_texto(cidade, 40)
        registro_0100 += "  "
    
    # CEP
    cep_limpo = ''.join(filter(str.isdigit, st.session_state.get('cep', '')))
    registro_0100 += formatar_texto(cep_limpo, 8)
    
    # Email
    registro_0100 += formatar_texto(st.session_state.get('email', ''), 60)
    
    # Raça/Cor
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
    
    # Brancos restantes
    registro_0100 += " " * 572
    registro_0100 += "\n"
    
    # Registro 0200 - Documentação
    registro_0200 = "0200"
    registro_0200 += formatar_texto(cpf_limpo, 11)
    
    # RG
    rg_limpo = ''.join(filter(str.isdigit, st.session_state.get('rg', '')))
    registro_0200 += formatar_texto(rg_limpo, 15)
    
    # Órgão expedidor
    registro_0200 += formatar_texto(st.session_state.get('orgao_exp', ''), 10)
    
    # Data expedição RG
    registro_0200 += formatar_data(st.session_state.get('data_expedicao', ''))
    
    # CTPS
    ctps_limpo = ''.join(filter(str.isdigit, st.session_state.get('ctps', '')))
    registro_0200 += formatar_texto(ctps_limpo, 11)
    
    # Série CTPS
    registro_0200 += formatar_texto(st.session_state.get('serie', ''), 5)
    
    # UF CTPS
    registro_0200 += formatar_texto(st.session_state.get('uf_ctps', ''), 2)
    
    # Data expedição CTPS
    registro_0200 += formatar_data(st.session_state.get('data_exp_ctps', ''))
    
    # PIS/PASEP
    pis_limpo = ''.join(filter(str.isdigit, st.session_state.get('pis', '')))
    registro_0200 += formatar_texto(pis_limpo, 11)
    
    # Título eleitor
    titulo_limpo = ''.join(filter(str.isdigit, st.session_state.get('titulo_eleitor', '')))
    registro_0200 += formatar_texto(titulo_limpo, 12)
    
    # Zona eleitoral
    registro_0200 += formatar_texto(st.session_state.get('zona', ''), 4)
    
    # Seção eleitoral
    registro_0200 += formatar_texto(st.session_state.get('secao', ''), 4)
    
    # Carteira habilitação
    registro_0200 += formatar_texto(st.session_state.get('carteira_habilitacao', ''), 15)
    
    # Categoria habilitação
    registro_0200 += formatar_texto(st.session_state.get('categoria_hab', ''), 2)
    
    # Data validade CNH
    registro_0200 += formatar_data(st.session_state.get('vencimento_hab', ''))
    
    # UF CNH
    registro_0200 += formatar_texto(st.session_state.get('uf_hab', ''), 2)
    
    # Reservista
    registro_0200 += formatar_texto(st.session_state.get('reservista', ''), 15)
    
    # Brancos restantes
    registro_0200 += " " * 850
    registro_0200 += "\n"
    
    # Registro 0300 - Dados Bancários
    registro_0300 = "0300"
    registro_0300 += formatar_texto(cpf_limpo, 11)
    
    # Banco
    registro_0300 += formatar_texto(st.session_state.get('banco', ''), 3)
    
    # Agência
    registro_0300 += formatar_texto(st.session_state.get('agencia', ''), 5)
    
    # Conta corrente
    registro_0300 += formatar_texto(st.session_state.get('conta', ''), 10)
    
    # Chave PIX
    registro_0300 += formatar_texto(st.session_state.get('chave_pix', ''), 77)
    
    # Brancos restantes
    registro_0300 += " " * 882
    registro_0300 += "\n"
    
    # Registro 0400 - Dependentes
    # Dependente 1 (filha)
    registro_0400 = "0400"
    registro_0400 += formatar_texto(cpf_limpo, 11)
    
    # CPF do dependente
    registro_0400 += formatar_texto("00217252923", 11)
    
    # Nome dependente
    registro_0400 += formatar_texto("LAURA HELENA MATOS FERREIRA LEITE", 70)
    
    # Data nascimento dependente
    registro_0400 += formatar_data("2024-03-13")
    
    # Sexo dependente
    registro_0400 += "F"
    
    # IRRF
    registro_0400 += "S"
    
    # Salário família
    registro_0400 += "N"
    
    # Parentesco (06 - Filho(a))
    registro_0400 += "06"
    
    # Brancos restantes
    registro_0400 += " " * 864
    registro_0400 += "\n"
    
    # Registro 0500 - Dados Empresa
    registro_0500 = "0500"
    registro_0500 += formatar_texto(cpf_limpo, 11)
    
    # Data admissão
    registro_0500 += formatar_data(st.session_state.get('data_inicio', ''))
    
    # Cargo
    registro_0500 += formatar_texto(st.session_state.get('cargo_funcao', ''), 50)
    
    # Salário
    salario_limpo = ''.join(filter(str.isdigit, st.session_state.get('salario', '')))
    registro_0500 += formatar_valor(salario_limpo)
    
    # Horário de trabalho
    registro_0500 += formatar_texto(st.session_state.get('horario_trabalho', ''), 100)
    
    # Centro de custo
    registro_0500 += formatar_texto(st.session_state.get('centro_custo', ''), 30)
    
    # Sindicato
    registro_0500 += formatar_texto(st.session_state.get('sindicato', ''), 50)
    
    # Vale transporte
    vt = st.session_state.get('vale_transporte', '')
    registro_0500 += "S" if vt == "Sim" else "N"
    
    # Vale alimentação
    va = st.session_state.get('vale_alimentacao', '')
    registro_0500 += "S" if va == "Sim" else "N"
    
    # Vale refeição
    vr = st.session_state.get('vale_refeicao', '')
    registro_0500 += "S" if vr == "Sim" else "N"
    
    # Adicional noturno
    an = st.session_state.get('adicional_noturno', '')
    registro_0500 += "S" if an == "Sim" else "N"
    
    # Insalubridade
    ins = st.session_state.get('insalubridade', '')
    registro_0500 += "S" if ins == "Sim" else "N"
    
    # Periculosidade
    per = st.session_state.get('periculosidade', '')
    registro_0500 += "S" if per == "Sim" else "N"
    
    # Brancos restantes
    registro_0500 += " " * 698
    registro_0500 += "\n"
    
    # Registro 9900 - Trailer
    trailer = "9900"
    trailer += "0005"  # Quantidade de registros (header + 4 registros de dados)
    trailer += " " * 984
    trailer += "\n"
    
    # Concatena todos os registros
    conteudo_arquivo = header + registro_0100 + registro_0200 + registro_0300 + registro_0400 + registro_0500 + trailer
    
    return conteudo_arquivo

# Função para criar link de download
def get_download_link(content, filename):
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}" class="stButton button generate-button">📥 BAIXAR ARQUIVO TXT</a>'
    return href

# Função para inicializar o estado da sessão
def initialize_session_state():
    if 'dados_pessoais_salvos' not in st.session_state:
        st.session_state.dados_pessoais_salvos = False
    if 'documentacao_salvos' not in st.session_state:
        st.session_state.documentacao_salvos = False
    if 'dados_bancarios_salvos' not in st.session_state:
        st.session_state.dados_bancarios_salvos = False
    if 'dependentes_salvos' not in st.session_state:
        st.session_state.dependentes_salvos = False
    if 'beneficios_salvos' not in st.session_state:
        st.session_state.beneficios_salvos = False
    if 'dados_empresa_salvos' not in st.session_state:
        st.session_state.dados_empresa_salvos = False
    if 'formulario_enviado' not in st.session_state:
        st.session_state.formulario_enviado = False
    if 'arquivo_gerado' not in st.session_state:
        st.session_state.arquivo_gerado = False

# Função principal do aplicativo
def main():
    initialize_session_state()
    
    st.markdown('<h1 class="main-header">FORMULÁRIO DE CADASTRO DE FUNCIONÁRIO</h1>', unsafe_allow_html=True)
    
    # Cria abas para organizar o formulário
    tab_names = [
        f"Dados Pessoais {'✓' if st.session_state.dados_pessoais_salvos else '⏳'}",
        f"Documentação {'✓' if st.session_state.documentacao_salvos else '⏳'}",
        f"Dados Bancários {'✓' if st.session_state.dados_bancarios_salvos else '⏳'}",
        f"Dependentes {'✓' if st.session_state.dependentes_salvos else '⏳'}",
        f"Benefícios {'✓' if st.session_state.beneficios_salvos else '⏳'}",
        f"Dados Empresa {'✓' if st.session_state.dados_empresa_salvos else '⏳'}"
    ]
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tab_names)
    
    with tab1:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">1) DADOS PESSOAIS</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nome_completo = st.text_input("Nome Completo", value="ADRIELLY DOS SANTOS MATOS", key="nome_completo")
            estado_civil = st.radio("Estado Civil", ["Solteiro", "Casado", "Outros"], index=0, key="estado_civil")
            sexo = st.radio("Sexo", ["Masculino", "Feminino"], index=1, key="sexo")
            data_nascimento = st.date_input("Data de Nascimento", value=datetime(1999, 7, 8), key="data_nascimento")
        
        with col2:
            naturalidade = st.text_input("Naturalidade", value="ARCOVERDE - PE", key="naturalidade")
            endereco = st.text_input("Endereço", value="R POETA FRANCISCO FERREIRA LEITE, 40, BL 04 AP 12", key="endereco")
            bairro = st.text_input("Bairro", value="CRISTO REI", key="bairro")
            cidade = st.text_input("Cidade", value="CURITIBA - PR", key="cidade")
        
        with col3:
            cep = st.text_input("CEP", value="80050-360", key="cep")
            nome_pai = st.text_input("Nome do Pai", value="ANTONIO MARCOS DA SILVA MATOS", key="nome_pai")
            nome_mae = st.text_input("Nome da Mãe", value="ANDRÉA DOS SANTOS MELO", key="nome_mae")
        
        col4, col5 = st.columns(2)
        
        with col4:
            grau_instrucao = st.selectbox(
                "Grau de Instrução", 
                ["Ensino Fundamental", "Ensino Médio", "Curso Superior", "Pós Graduação"],
                index=2,
                key="grau_instrucao"
            )
            instrucao_completa = st.radio("Completo?", ["Sim", "Não"], index=1, horizontal=True, key="instrucao_completa")
        
        with col5:
            email = st.text_input("E-mail", value="adriellymatos8@gmail.com", key="email")
            raca_cor = st.selectbox(
                "Raça/Cor", 
                ["Branca", "Negra", "Parda", "Amarela"],
                index=0,
                key="raca_cor"
            )
        
        # Botão Gravar para Dados Pessoais
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 GRAVAR DADOS PESSOAIS", key="gravar_dados_pessoais", use_container_width=True):
                if nome_completo and data_nascimento:
                    st.session_state.dados_pessoais_salvos = True
                    st.markdown("""
                    <div class="save-message">
                        <strong>✅ Dados pessoais salvos com sucesso!</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    st.rerun()
                else:
                    st.error("Por favor, preencha pelo menos o Nome Completo e Data de Nascimento.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">2) DOCUMENTAÇÃO</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            rg = st.text_input("RG", value="060.375.391-46", key="rg")
            orgao_exp = st.text_input("Órgão Expedidor", value="SESP/PR", key="orgao_exp")
            data_expedicao = st.date_input("Data de Expedição", value=datetime(2024, 5, 26), key="data_expedicao")
            cpf = st.text_input("CPF", value="060.375.391-46", key="cpf")
            
            if cpf and not validar_cpf(cpf):
                st.error("CPF inválido! Por favor, verifique o número digitado.")
        
        with col2:
            titulo_eleitor = st.text_input("Título de Eleitor", value="0268 4243 1929", key="titulo_eleitor")
            zona = st.text_input("Zona", value="177", key="zona")
            secao = st.text_input("Seção", value="0801", key="secao")
            ctps = st.text_input("CTPS", value="7551374", key="ctps")
            serie = st.text_input("Série", value="00050", key="serie")
            uf_ctps = st.text_input("UF", value="MS", key="uf_ctps")
            data_exp_ctps = st.date_input("Data Expedição CTPS", value=datetime(2020, 3, 27), key="data_exp_ctps")
            pis = st.text_input("PIS", value="160.94867.47-46", key="pis")
        
        col3, col4 = st.columns(2)
        
        with col3:
            carteira_habilitacao = st.text_input("Carteira de Habilitação", key="carteira_habilitacao")
            categoria_hab = st.text_input("Categoria", key="categoria_hab")
        
        with col4:
            vencimento_hab = st.text_input("Vencimento", key="vencimento_hab")
            uf_hab = st.text_input("UF", key="uf_hab")
            reservista = st.text_input("Reservista", key="reservista")
        
        # Botão Gravar para Documentação
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 GRAVAR DOCUMENTAÇÃO", key="gravar_documentacao", use_container_width=True):
                if rg and cpf and validar_cpf(cpf):
                    st.session_state.documentacao_salvos = True
                    st.markdown("""
                    <div class="save-message">
                        <strong>✅ Documentação salva com sucesso!</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    st.rerun()
                else:
                    st.error("Por favor, preencha pelo menos RG e um CPF válido.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">3) DADOS BANCÁRIOS</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            banco = st.text_input("Banco", value="MÊNTORE BANK", key="banco")
        
        with col2:
            agencia = st.text_input("Agência", key="agencia")
        
        with col3:
            conta = st.text_input("Conta Corrente", key="conta")
        
        chave_pix = st.text_input("Chave PIX", key="chave_pix")
        
        # Botão Gravar para Dados Bancários
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 GRAVAR DADOS BANCÁRIOS", key="gravar_dados_bancarios", use_container_width=True):
                st.session_state.dados_bancarios_salvos = True
                st.markdown("""
                <div class="save-message">
                    <strong>✅ Dados bancários salvos com sucesso!</strong>
                </div>
                """, unsafe_allow_html=True)
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab4:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">4) DEPENDENTES SALÁRIO FAMÍLIA E IMPOSTO DE RENDA</h2>', unsafe_allow_html=True)
        
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
                <td>Cônjuge</td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr>
                <td>LAURA HELENA MATOS FERREIRA LEITE</td>
                <td>002.172.529-23</td>
                <td>13/03/2024</td>
                <td>SIM</td>
                <td>NÃO</td>
            </tr>
            <tr>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
        </table>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="margin-top: 1rem;">
            <p><strong>Observação:</strong> Para adicionar ou modificar dependentes, entre em contato com o departamento pessoal.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Botão Gravar para Dependentes
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 GRAVAR DEPENDENTES", key="gravar_dependentes", use_container_width=True):
                st.session_state.dependentes_salvos = True
                st.markdown("""
                <div class="save-message">
                    <strong>✅ Dependentes salvos com sucesso!</strong>
                </div>
                """, unsafe_allow_html=True)
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab5:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">5) BENEFÍCIOS</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            vale_transporte = st.radio("Vale Transporte", ["Sim", "Não"], index=0, horizontal=True, key="vale_transporte")
            if vale_transporte == "Sim":
                empresa_transporte = st.text_input("Empresa", value="URBS", key="empresa_transporte")
                qtd_vts = st.text_input("Quantidade por dia", value="2 VTS POR DIA", key="qtd_vts")
                valor_tarifa = st.text_input("Valor da Tarifa", value="R$ 6,00", key="valor_tarifa")
                cartao_transporte = st.text_input("Número Cartão Transporte/SIC", value="NF 65587068991923205", key="cartao_transporte")
        
        with col2:
            vale_alimentacao = st.radio("Vale Alimentação", ["Sim", "Não"], index=0, horizontal=True, key="vale_alimentacao")
            vale_refeicao = st.radio("Vale Refeição", ["Sim", "Não"], index=1, horizontal=True, key="vale_refeicao")
            if vale_alimentacao == "Sim" or vale_refeicao == "Sim":
                valor_diario = st.text_input("Valor por dia", value="R$ 1.090,00 P/ MÊS", key="valor_diario")
            
            cesta_basica = st.radio("Cesta Básica", ["Sim", "Não"], index=1, horizontal=True, key="cesta_basica")
        
        # Botão Gravar para Benefícios
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 GRAVAR BENEFÍCIOS", key="gravar_beneficios", use_container_width=True):
                st.session_state.beneficios_salvos = True
                st.markdown("""
                <div class="save-message">
                    <strong>✅ Benefícios salvos com sucesso!</strong>
                </div>
                """, unsafe_allow_html=True)
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab6:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">6) DADOS A SEREM PREENCHIDOS PELO EMPREGADOR (EMPRESA)</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            empresa = st.text_input("Empresa", value="OBRA PRIMA S/A TECNOLOGIA E ADMINISTRAÇÃO DE SERVIÇOS", key="empresa")
            local_posto = st.text_input("Local/Posto", value="SEBRAE – CURITIBA (UNIDADE DE AMBIENTE DE NEGOCIOS)", key="local_posto")
            centro_custo = st.text_input("Centro de Custo", value="735903", key="centro_custo")
            sessao_folha = st.text_input("Sessão da folha", key="sessao_folha")
            
            ja_trabalhou = st.radio("Já trabalhou nesta empresa?", ["Sim", "Não"], index=1, horizontal=True, key="ja_trabalhou")
            contrato_experiencia = st.radio("Contrato de Experiência", ["Sim", "Não"], index=0, horizontal=True, key="contrato_experiencia")
            
            if contrato_experiencia == "Sim":
                periodo_experiencia = st.radio(
                    "Período de Experiência", 
                    ["45 dias, prorrogável por mais 45 dias", "Outros"], 
                    index=0, 
                    horizontal=True,
                    key="periodo_experiencia"
                )
        
        with col2:
            forma_contratacao = st.selectbox(
                "Forma de Contratação", 
                ["CLT", "Estágio", "PJ", "Autônomo"],
                index=0,
                key="forma_contratacao"
            )
            cargo_funcao = st.text_input("Cargo/Função", value="ASSISTENTE I", key="cargo_funcao")
            data_inicio = st.date_input("Data de Início", value=datetime(2025, 11, 10), key="data_inicio")
            salario = st.text_input("Salário", value="R$ 2.946,15", key="salario")
            
            horario_trabalho = st.text_input("Horário de Trabalho", value="Das: 08:30 às 17:30 Intervalo: 12:00 às 13:00", key="horario_trabalho")
            trabalha_sabado = st.radio("Sábado", ["Sim", "Não"], index=1, horizontal=True, key="trabalha_sabado")
            qtd_sabados = st.text_input("Quantidade Sábados Mês", key="qtd_sabados")
            
            adicional_noturno = st.radio("Adicional Noturno", ["Sim", "Não"], index=1, horizontal=True, key="adicional_noturno")
            sindicato = st.text_input("Sindicato", value="SINEEPRES", key="sindicato")
        
        col3, col4 = st.columns(2)
        
        with col3:
            insalubridade = st.radio("Insalubridade", ["Sim", "Não"], index=1, horizontal=True, key="insalubridade")
            if insalubridade == "Sim":
                grau_insalubridade = st.radio(
                    "Grau de Insalubridade", 
                    ["10% Mínima", "20% Média", "40% Máxima"],
                    index=0,
                    horizontal=True,
                    key="grau_insalubridade"
                )
            
            periculosidade = st.radio("Adicional Periculosidade (30%)", ["Sim", "Não"], index=1, horizontal=True, key="periculosidade")
        
        with col4:
            assiduidade = st.radio("Assiduidade", ["SIM", "NÃO"], index=1, horizontal=True, key="assiduidade")
            gratificacao_artigo = st.radio("Gratificações - ARTIGO 62 -40%", ["Sim", "Não"], index=1, horizontal=True, key="gratificacao_artigo")
            gratificacao_cct = st.radio("Gratificações de Função CCT", ["Sim", "Não"], index=1, horizontal=True, key="gratificacao_cct")
        
        # Botão Gravar para Dados Empresa
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 GRAVAR DADOS EMPRESA", key="gravar_dados_empresa", use_container_width=True):
                if empresa and cargo_funcao and data_inicio and salario:
                    st.session_state.dados_empresa_salvos = True
                    st.markdown("""
                    <div class="save-message">
                        <strong>✅ Dados da empresa salvos com sucesso!</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    st.rerun()
                else:
                    st.error("Por favor, preencha pelo menos Empresa, Cargo/Função, Data de Início e Salário.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Botão Enviar e Gerar TXT (apenas na última aba)
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Verificar se todas as abas anteriores foram salvas
            todas_abas_salvas = (
                st.session_state.dados_pessoais_salvos and
                st.session_state.documentacao_salvos and
                st.session_state.dados_bancarios_salvos and
                st.session_state.dependentes_salvos and
                st.session_state.beneficios_salvos and
                st.session_state.dados_empresa_salvos
            )
            
            if todas_abas_salvas:
                if st.button("🚀 ENVIAR FORMULÁRIO COMPLETO", key="enviar_formulario", use_container_width=True):
                    # Validação final
                    if not st.session_state.get('nome_completo', ''):
                        st.error("Por favor, preencha o campo Nome Completo.")
                    elif not st.session_state.get('cpf', '') or not validar_cpf(st.session_state.get('cpf', '')):
                        st.error("Por favor, insira um CPF válido.")
                    else:
                        st.session_state.formulario_enviado = True
                        st.session_state.arquivo_gerado = True
                        st.markdown("""
                        <div class="success-message">
                            <h3>✅ Formulário enviado com sucesso!</h3>
                            <p>Seus dados foram registrados no sistema. Obrigado!</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Exibir resumo dos dados
                        with st.expander("Ver Resumo dos Dados Enviados"):
                            st.write(f"**Nome:** {st.session_state.get('nome_completo', '')}")
                            st.write(f"**CPF:** {formatar_cpf(st.session_state.get('cpf', ''))}")
                            st.write(f"**Data de Nascimento:** {st.session_state.get('data_nascimento', datetime.now()).strftime('%d/%m/%Y')}")
                            st.write(f"**Cargo:** {st.session_state.get('cargo_funcao', '')}")
                            st.write(f"**Data de Início:** {st.session_state.get('data_inicio', datetime.now()).strftime('%d/%m/%Y')}")
                            st.write(f"**Salário:** {st.session_state.get('salario', '')}")
            else:
                st.warning("⚠️ Para enviar o formulário, é necessário gravar todas as abas anteriores primeiro.")
                abas_pendentes = []
                if not st.session_state.dados_pessoais_salvos:
                    abas_pendentes.append("Dados Pessoais")
                if not st.session_state.documentacao_salvos:
                    abas_pendentes.append("Documentação")
                if not st.session_state.dados_bancarios_salvos:
                    abas_pendentes.append("Dados Bancários")
                if not st.session_state.dependentes_salvos:
                    abas_pendentes.append("Dependentes")
                if not st.session_state.beneficios_salvos:
                    abas_pendentes.append("Benefícios")
                if not st.session_state.dados_empresa_salvos:
                    abas_pendentes.append("Dados Empresa")
                
                st.info(f"**Abas pendentes:** {', '.join(abas_pendentes)}")
    
    # Botão GERAR TXT (sempre visível após envio do formulário)
    if st.session_state.formulario_enviado:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">GERAR ARQUIVO TOTVS</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📄 GERAR ARQUIVO TXT TOTVS", key="gerar_txt", use_container_width=True, type="primary"):
                try:
                    conteudo_txt = gerar_arquivo_totvs()
                    
                    # Nome do arquivo com CPF e data
                    cpf_limpo = ''.join(filter(str.isdigit, st.session_state.get('cpf', '')))
                    nome_arquivo = f"CADASTRO_{cpf_limpo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    
                    # Criar link de download
                    st.markdown(get_download_link(conteudo_txt, nome_arquivo), unsafe_allow_html=True)
                    
                    # Exibir preview do arquivo
                    with st.expander("Visualizar conteúdo do arquivo TXT"):
                        st.text_area("Conteúdo do arquivo:", conteudo_txt, height=300)
                    
                    st.success("✅ Arquivo TXT gerado com sucesso! Clique no botão acima para baixar.")
                    
                except Exception as e:
                    st.error(f"Erro ao gerar arquivo: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()