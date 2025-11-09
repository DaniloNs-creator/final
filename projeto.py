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

# Função principal do aplicativo
def main():
    st.markdown('<h1 class="main-header">FORMULÁRIO DE CADASTRO DE FUNCIONÁRIO</h1>', unsafe_allow_html=True)
    
    # Cria abas para organizar o formulário
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Dados Pessoais", 
        "Documentação", 
        "Dados Bancários", 
        "Dependentes", 
        "Benefícios", 
        "Dados Empresa"
    ])
    
    with tab1:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">1) DADOS PESSOAIS</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nome_completo = st.text_input("Nome Completo", value="ADRIELLY DOS SANTOS MATOS")
            estado_civil = st.radio("Estado Civil", ["Solteiro", "Casado", "Outros"], index=0)
            sexo = st.radio("Sexo", ["Masculino", "Feminino"], index=1)
            data_nascimento = st.date_input("Data de Nascimento", value=datetime(1999, 7, 8))
        
        with col2:
            naturalidade = st.text_input("Naturalidade", value="ARCOVERDE - PE")
            endereco = st.text_input("Endereço", value="R POETA FRANCISCO FERREIRA LEITE, 40, BL 04 AP 12")
            bairro = st.text_input("Bairro", value="CRISTO REI")
            cidade = st.text_input("Cidade", value="CURITIBA - PR")
        
        with col3:
            cep = st.text_input("CEP", value="80050-360")
            nome_pai = st.text_input("Nome do Pai", value="ANTONIO MARCOS DA SILVA MATOS")
            nome_mae = st.text_input("Nome da Mãe", value="ANDRÉA DOS SANTOS MELO")
        
        col4, col5 = st.columns(2)
        
        with col4:
            grau_instrucao = st.selectbox(
                "Grau de Instrução", 
                ["Ensino Fundamental", "Ensino Médio", "Curso Superior", "Pós Graduação"],
                index=2
            )
            instrucao_completa = st.radio("Completo?", ["Sim", "Não"], index=1, horizontal=True)
        
        with col5:
            email = st.text_input("E-mail", value="adriellymatos8@gmail.com")
            raca_cor = st.selectbox(
                "Raça/Cor", 
                ["Branca", "Negra", "Parda", "Amarela"],
                index=0
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">2) DOCUMENTAÇÃO</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            rg = st.text_input("RG", value="060.375.391-46")
            orgao_exp = st.text_input("Órgão Expedidor", value="SESP/PR")
            data_expedicao = st.date_input("Data de Expedição", value=datetime(2024, 5, 26))
            cpf = st.text_input("CPF", value="060.375.391-46")
            
            if cpf and not validar_cpf(cpf):
                st.error("CPF inválido! Por favor, verifique o número digitado.")
        
        with col2:
            titulo_eleitor = st.text_input("Título de Eleitor", value="0268 4243 1929")
            zona = st.text_input("Zona", value="177")
            secao = st.text_input("Seção", value="0801")
            ctps = st.text_input("CTPS", value="7551374")
            serie = st.text_input("Série", value="00050")
            uf_ctps = st.text_input("UF", value="MS")
            data_exp_ctps = st.date_input("Data Expedição CTPS", value=datetime(2020, 3, 27))
            pis = st.text_input("PIS", value="160.94867.47-46")
        
        col3, col4 = st.columns(2)
        
        with col3:
            carteira_habilitacao = st.text_input("Carteira de Habilitação")
            categoria_hab = st.text_input("Categoria")
        
        with col4:
            vencimento_hab = st.text_input("Vencimento")
            uf_hab = st.text_input("UF")
            reservista = st.text_input("Reservista")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">3) DADOS BANCÁRIOS</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            banco = st.text_input("Banco", value="MÊNTORE BANK")
        
        with col2:
            agencia = st.text_input("Agência")
        
        with col3:
            conta = st.text_input("Conta Corrente")
        
        chave_pix = st.text_input("Chave PIX")
        
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
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab5:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">5) BENEFÍCIOS</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            vale_transporte = st.radio("Vale Transporte", ["Sim", "Não"], index=0, horizontal=True)
            if vale_transporte == "Sim":
                empresa_transporte = st.text_input("Empresa", value="URBS")
                qtd_vts = st.text_input("Quantidade por dia", value="2 VTS POR DIA")
                valor_tarifa = st.text_input("Valor da Tarifa", value="R$ 6,00")
                cartao_transporte = st.text_input("Número Cartão Transporte/SIC", value="NF 65587068991923205")
        
        with col2:
            vale_alimentacao = st.radio("Vale Alimentação", ["Sim", "Não"], index=0, horizontal=True)
            vale_refeicao = st.radio("Vale Refeição", ["Sim", "Não"], index=1, horizontal=True)
            if vale_alimentacao == "Sim" or vale_refeicao == "Sim":
                valor_diario = st.text_input("Valor por dia", value="R$ 1.090,00 P/ MÊS")
            
            cesta_basica = st.radio("Cesta Básica", ["Sim", "Não"], index=1, horizontal=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab6:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">6) DADOS A SEREM PREENCHIDOS PELO EMPREGADOR (EMPRESA)</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            empresa = st.text_input("Empresa", value="OBRA PRIMA S/A TECNOLOGIA E ADMINISTRAÇÃO DE SERVIÇOS")
            local_posto = st.text_input("Local/Posto", value="SEBRAE – CURITIBA (UNIDADE DE AMBIENTE DE NEGOCIOS)")
            centro_custo = st.text_input("Centro de Custo", value="735903")
            sessao_folha = st.text_input("Sessão da folha")
            
            ja_trabalhou = st.radio("Já trabalhou nesta empresa?", ["Sim", "Não"], index=1, horizontal=True)
            contrato_experiencia = st.radio("Contrato de Experiência", ["Sim", "Não"], index=0, horizontal=True)
            
            if contrato_experiencia == "Sim":
                periodo_experiencia = st.radio(
                    "Período de Experiência", 
                    ["45 dias, prorrogável por mais 45 dias", "Outros"], 
                    index=0, 
                    horizontal=True
                )
        
        with col2:
            forma_contratacao = st.selectbox(
                "Forma de Contratação", 
                ["CLT", "Estágio", "PJ", "Autônomo"],
                index=0
            )
            cargo_funcao = st.text_input("Cargo/Função", value="ASSISTENTE I")
            data_inicio = st.date_input("Data de Início", value=datetime(2025, 11, 10))
            salario = st.text_input("Salário", value="R$ 2.946,15")
            
            horario_trabalho = st.text_input("Horário de Trabalho", value="Das: 08:30 às 17:30 Intervalo: 12:00 às 13:00")
            trabalha_sabado = st.radio("Sábado", ["Sim", "Não"], index=1, horizontal=True)
            qtd_sabados = st.text_input("Quantidade Sábados Mês")
            
            adicional_noturno = st.radio("Adicional Noturno", ["Sim", "Não"], index=1, horizontal=True)
            sindicato = st.text_input("Sindicato", value="SINEEPRES")
        
        col3, col4 = st.columns(2)
        
        with col3:
            insalubridade = st.radio("Insalubridade", ["Sim", "Não"], index=1, horizontal=True)
            if insalubridade == "Sim":
                grau_insalubridade = st.radio(
                    "Grau de Insalubridade", 
                    ["10% Mínima", "20% Média", "40% Máxima"],
                    index=0,
                    horizontal=True
                )
            
            periculosidade = st.radio("Adicional Periculosidade (30%)", ["Sim", "Não"], index=1, horizontal=True)
        
        with col4:
            assiduidade = st.radio("Assiduidade", ["SIM", "NÃO"], index=1, horizontal=True)
            gratificacao_artigo = st.radio("Gratificações - ARTIGO 62 -40%", ["Sim", "Não"], index=1, horizontal=True)
            gratificacao_cct = st.radio("Gratificações de Função CCT", ["Sim", "Não"], index=1, horizontal=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Botão de envio
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("ENVIAR FORMULÁRIO", key="enviar"):
            # Validação básica dos campos obrigatórios
            if not nome_completo:
                st.error("Por favor, preencha o campo Nome Completo.")
            elif not cpf or not validar_cpf(cpf):
                st.error("Por favor, insira um CPF válido.")
            else:
                # Aqui você pode adicionar a lógica para salvar os dados
                # Por exemplo, em um banco de dados ou arquivo
                
                st.markdown("""
                <div class="success-message">
                    <h3>✅ Formulário enviado com sucesso!</h3>
                    <p>Seus dados foram registrados no sistema. Obrigado!</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Exibir resumo dos dados (opcional)
                with st.expander("Ver Resumo dos Dados Enviados"):
                    st.write(f"**Nome:** {nome_completo}")
                    st.write(f"**CPF:** {formatar_cpf(cpf)}")
                    st.write(f"**Data de Nascimento:** {data_nascimento.strftime('%d/%m/%Y')}")
                    st.write(f"**Cargo:** {cargo_funcao}")
                    st.write(f"**Data de Início:** {data_inicio.strftime('%d/%m/%Y')}")
                    st.write(f"**Salário:** {salario}")

if __name__ == "__main__":
    main()
