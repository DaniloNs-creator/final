import streamlit as st
from datetime import datetime

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
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .form-section {
        background: white;
        border-radius: 10px;
        padding: 0;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        border: 1px solid #e0e0e0;
        overflow: hidden;
    }
    
    .section-header {
        background: linear-gradient(135deg, #1f3a60 0%, #2c5282 100%);
        color: white;
        padding: 1rem 1.5rem;
        margin: 0;
        font-size: 1.3rem;
        font-weight: bold;
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: all 0.3s ease;
    }
    
    .section-header:hover {
        background: linear-gradient(135deg, #2c5282 0%, #1f3a60 100%);
    }
    
    .section-content {
        padding: 1.5rem;
        background-color: #f8f9fa;
    }
    
    .section-icon {
        font-size: 1.2rem;
        transition: transform 0.3s ease;
    }
    
    .section-expanded .section-icon {
        transform: rotate(180deg);
    }
    
    /* Estilização dos campos */
    .stTextInput input, .stDateInput input, .stSelectbox select, .stTextArea textarea {
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 0.75rem;
        font-size: 0.9rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus, .stDateInput input:focus, .stSelectbox select:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* Estilização dos radio buttons e checkboxes */
    .stRadio > div {
        flex-direction: row;
        gap: 2rem;
    }
    
    .stRadio label, .stCheckbox label {
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    
    /* Grid layout para campos */
    .field-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1rem;
        margin-bottom: 1rem;
    }
    
    .field-group {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
    }
    
    .field-label {
        font-weight: 600;
        color: #374151;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    
    /* Tabela de dependentes */
    .dependent-table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        background: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .dependent-table th {
        background: #1f3a60;
        color: white;
        padding: 0.75rem;
        text-align: left;
        font-weight: 600;
    }
    
    .dependent-table td {
        padding: 0.75rem;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .dependent-table tr:hover {
        background-color: #f9fafb;
    }
    
    /* Badges para status */
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-active {
        background-color: #d1fae5;
        color: #065f46;
    }
    
    .status-inactive {
        background-color: #fee2e2;
        color: #991b1b;
    }
    
    /* Botões */
    .stButton button {
        background: linear-gradient(135deg, #1f3a60 0%, #2c5282 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 6px;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    /* Mensagens de sucesso/erro */
    .success-message {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        text-align: center;
        margin-top: 1rem;
    }
    
    .error-message {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Função para criar seções expansíveis
def create_expandable_section(title, content_func, default_expanded=True):
    section_id = title.replace(" ", "_").lower()
    
    # Estado para controlar se a seção está expandida
    if f"section_{section_id}" not in st.session_state:
        st.session_state[f"section_{section_id}"] = default_expanded
    
    # Header clicável
    col1, col2 = st.columns([9, 1])
    
    with col1:
        st.markdown(f'<div class="section-header" onclick="toggleSection(\'{section_id}\')">{title}</div>', unsafe_allow_html=True)
    
    with col2:
        icon = "▼" if st.session_state[f"section_{section_id}"] else "▶"
        st.markdown(f'<div class="section-icon" onclick="toggleSection(\'{section_id}\')">{icon}</div>', unsafe_allow_html=True)
    
    # Conteúdo da seção
    if st.session_state[f"section_{section_id}"]:
        st.markdown('<div class="section-content">', unsafe_allow_html=True)
        content_func()
        st.markdown('</div>', unsafe_allow_html=True)

# JavaScript para controlar a expansão/colapso
st.markdown("""
<script>
function toggleSection(sectionId) {
    // Esta função será chamada quando o usuário clicar no header
    // O estado real é controlado pelo Streamlit via session_state
    // Esta é apenas uma indicação visual
    const element = document.querySelector(`[onclick="toggleSection('${sectionId}')"]`);
    if (element) {
        const icon = element.nextElementSibling?.querySelector('.section-icon');
        if (icon) {
            if (icon.textContent === '▼') {
                icon.textContent = '▶';
            } else {
                icon.textContent = '▼';
            }
        }
    }
}
</script>
""", unsafe_allow_html=True)

# Funções de conteúdo para cada seção
def personal_data_content():
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.text_input("**Nome Completo**", value="ADRIELLY DOS SANTOS MATOS", key="nome_completo")
        st.radio("**Estado Civil**", ["Solteiro", "Casado", "Outros"], index=0, key="estado_civil", horizontal=True)
        st.radio("**Sexo**", ["Masculino", "Feminino"], index=1, key="sexo", horizontal=True)
        st.date_input("**Data de Nascimento**", value=datetime(1999, 7, 8), key="data_nascimento")
    
    with col2:
        st.text_input("**Naturalidade**", value="ARCOVERDE - PE", key="naturalidade")
        st.text_input("**Endereço**", value="R POETA FRANCISCO FERREIRA LEITE, 40, BL 04 AP 12", key="endereco")
        st.text_input("**Bairro**", value="CRISTO REI", key="bairro")
        st.text_input("**Cidade**", value="CURITIBA - PR", key="cidade")
    
    with col3:
        st.text_input("**CEP**", value="80050-360", key="cep")
        st.text_input("**Nome do Pai**", value="ANTONIO MARCOS DA SILVA MATOS", key="nome_pai")
        st.text_input("**Nome da Mãe**", value="ANDRÉA DOS SANTOS MELO", key="nome_mae")
    
    col4, col5 = st.columns(2)
    
    with col4:
        st.selectbox("**Grau de Instrução**", ["Ensino Fundamental", "Ensino Médio", "Curso Superior", "Pós Graduação"], index=2, key="grau_instrucao")
        st.radio("**Completo?**", ["Sim", "Não"], index=1, key="instrucao_completa", horizontal=True)
    
    with col5:
        st.text_input("**E-mail**", value="adriellymatos8@gmail.com", key="email")
        st.selectbox("**Raça/Cor**", ["Branca", "Negra", "Parda", "Amarela"], index=0, key="raca_cor")

def documentation_content():
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("**RG**", value="060.375.391-46", key="rg")
        st.text_input("**Órgão Expedidor**", value="SESP/PR", key="orgao_exp")
        st.date_input("**Data de Expedição**", value=datetime(2024, 5, 26), key="data_expedicao")
        st.text_input("**CPF**", value="060.375.391-46", key="cpf")
        st.text_input("**Título de Eleitor**", value="0268 4243 1929", key="titulo_eleitor")
        st.text_input("**Zona**", value="177", key="zona")
        st.text_input("**Seção**", value="0801", key="secao")
    
    with col2:
        st.text_input("**CTPS**", value="7551374", key="ctps")
        st.text_input("**Série**", value="00050", key="serie")
        st.text_input("**UF**", value="MS", key="uf_ctps")
        st.date_input("**Data Expedição CTPS**", value=datetime(2020, 3, 27), key="data_exp_ctps")
        st.text_input("**PIS**", value="160.94867.47-46", key="pis")
        st.text_input("**Carteira de Habilitação**", key="carteira_habilitacao")
        st.text_input("**Categoria**", key="categoria_hab")
        st.text_input("**Vencimento**", key="vencimento_hab")
        st.text_input("**UF**", key="uf_hab")
        st.text_input("**Reservista**", key="reservista")

def bank_data_content():
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.text_input("**Banco**", value="MÊNTORE BANK", key="banco")
    
    with col2:
        st.text_input("**Agência**", key="agencia")
    
    with col3:
        st.text_input("**Conta Corrente**", key="conta")
    
    st.text_input("**Chave PIX**", key="chave_pix")

def dependents_content():
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
            <td><span class="status-badge status-inactive">NÃO</span></td>
            <td><span class="status-badge status-inactive">NÃO</span></td>
        </tr>
        <tr>
            <td>LAURA HELENA MATOS FERREIRA LEITE</td>
            <td>002.172.529-23</td>
            <td>13/03/2024</td>
            <td><span class="status-badge status-active">SIM</span></td>
            <td><span class="status-badge status-inactive">NÃO</span></td>
        </tr>
        <tr>
            <td></td>
            <td></td>
            <td></td>
            <td><span class="status-badge status-inactive">NÃO</span></td>
            <td><span class="status-badge status-inactive">NÃO</span></td>
        </tr>
        <tr>
            <td></td>
            <td></td>
            <td></td>
            <td><span class="status-badge status-inactive">NÃO</span></td>
            <td><span class="status-badge status-inactive">NÃO</span></td>
        </tr>
    </table>
    """, unsafe_allow_html=True)
    
    st.info("💡 **Observação:** Para adicionar ou modificar dependentes, entre em contato com o departamento pessoal.")

def benefits_content():
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Vale Transporte")
        vt_option = st.radio("Vale Transporte", ["Sim", "Não"], index=0, key="vale_transporte", horizontal=True)
        if vt_option == "Sim":
            st.text_input("**Empresa**", value="URBS", key="empresa_transporte")
            st.text_input("**Quantidade por dia**", value="2 VTS POR DIA", key="qtd_vts")
            st.text_input("**Valor da Tarifa**", value="R$ 6,00", key="valor_tarifa")
            st.text_input("**Número Cartão Transporte/SIC**", value="NF 65587068991923205", key="cartao_transporte")
    
    with col2:
        st.subheader("Vale Alimentação/Refeição")
        st.radio("**Vale Alimentação**", ["Sim", "Não"], index=0, key="vale_alimentacao", horizontal=True)
        st.radio("**Vale Refeição**", ["Sim", "Não"], index=1, key="vale_refeicao", horizontal=True)
        st.text_input("**Valor por dia**", value="R$ 1.090,00 P/ MÊS", key="valor_diario")
        
        st.subheader("Outros Benefícios")
        st.radio("**Cesta Básica**", ["Sim", "Não"], index=1, key="cesta_basica", horizontal=True)

def company_data_content():
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("**Empresa**", value="OBRA PRIMA S/A TECNOLOGIA E ADMINISTRAÇÃO DE SERVIÇOS", key="empresa")
        st.text_input("**Local/Posto**", value="SEBRAE – CURITIBA (UNIDADE DE AMBIENTE DE NEGOCIOS)", key="local_posto")
        st.text_input("**Centro de Custo**", value="735903", key="centro_custo")
        st.text_input("**Sessão da folha**", key="sessao_folha")
        
        st.radio("**Já trabalhou nesta empresa?**", ["Sim", "Não"], index=1, key="ja_trabalhou", horizontal=True)
        st.radio("**Contrato de Experiência**", ["Sim", "Não"], index=0, key="contrato_experiencia", horizontal=True)
        
        if st.session_state.contrato_experiencia == "Sim":
            st.radio("**Período de Experiência**", ["45 dias, prorrogável por mais 45 dias", "Outros"], index=0, key="periodo_experiencia", horizontal=True)
    
    with col2:
        st.selectbox("**Forma de Contratação**", ["CLT", "Estágio", "PJ", "Autônomo"], index=0, key="forma_contratacao")
        st.text_input("**Cargo/Função**", value="ASSISTENTE I", key="cargo_funcao")
        st.date_input("**Data de Início**", value=datetime(2025, 11, 10), key="data_inicio")
        st.text_input("**Salário**", value="R$ 2.946,15", key="salario")
        st.text_input("**Horário de Trabalho**", value="Das: 08:30 às 17:30 Intervalo: 12:00 às 13:00", key="horario_trabalho")
        
        st.radio("**Sábado**", ["Sim", "Não"], index=1, key="trabalha_sabado", horizontal=True)
        st.text_input("**Quantidade Sábados Mês**", key="qtd_sabados")
        st.radio("**Adicional Noturno**", ["Sim", "Não"], index=1, key="adicional_noturno", horizontal=True)
        st.text_input("**Sindicato**", value="SINEEPRES", key="sindicato")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("Condições Especiais")
        insalubridade = st.radio("**Insalubridade**", ["Sim", "Não"], index=1, key="insalubridade", horizontal=True)
        if insalubridade == "Sim":
            st.radio("**Grau de Insalubridade**", ["10% Mínima", "20% Média", "40% Máxima"], index=0, key="grau_insalubridade", horizontal=True)
        
        st.radio("**Adicional Periculosidade (30%)**", ["Sim", "Não"], index=1, key="periculosidade", horizontal=True)
    
    with col4:
        st.subheader("Gratificações")
        st.radio("**Assiduidade**", ["SIM", "NÃO"], index=1, key="assiduidade", horizontal=True)
        st.radio("**Gratificações - ARTIGO 62 -40%**", ["Sim", "Não"], index=1, key="gratificacao_artigo", horizontal=True)
        st.radio("**Gratificações de Função CCT**", ["Sim", "Não"], index=1, key="gratificacao_cct", horizontal=True)

# Função principal
def main():
    st.markdown('<h1 class="main-header">📋 FORMULÁRIO DE CADASTRO DE FUNCIONÁRIO</h1>', unsafe_allow_html=True)
    
    # Seções expansíveis
    create_expandable_section("1) DADOS PESSOAIS", personal_data_content, default_expanded=True)
    create_expandable_section("2) DOCUMENTAÇÃO", documentation_content, default_expanded=False)
    create_expandable_section("3) DADOS BANCÁRIOS", bank_data_content, default_expanded=False)
    create_expandable_section("4) DEPENDENTES SALÁRIO FAMÍLIA E IMPOSTO DE RENDA", dependents_content, default_expanded=False)
    create_expandable_section("5) BENEFÍCIOS", benefits_content, default_expanded=False)
    create_expandable_section("6) DADOS A SEREM PREENCHIDOS PELO EMPREGADOR", company_data_content, default_expanded=False)
    
    # Botão de envio
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("✅ ENVIAR FORMULÁRIO", use_container_width=True):
        st.markdown("""
        <div class="success-message">
            <h3>✅ Formulário enviado com sucesso!</h3>
            <p>Seus dados foram registrados no sistema. Obrigado!</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()