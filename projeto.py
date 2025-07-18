import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Configuração inicial da página
st.set_page_config(
    page_title="Controle de Atividades Fiscais",
    page_icon="📊",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
:root {
    --primary: #4a6fa5;
    --secondary: #166088;
    --success: #4caf50;
    --warning: #ff9800;
    --danger: #f44336;
    --light: #f8f9fa;
    --dark: #212529;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f5f7fa;
}

.stApp {
    background-color: #f5f7fa;
}

.header {
    color: var(--secondary);
    padding: 1rem;
    border-bottom: 1px solid #e1e4e8;
    margin-bottom: 2rem;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.card {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.card-title {
    color: var(--secondary);
    font-size: 1.25rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid #e1e4e8;
    padding-bottom: 0.5rem;
}

.status-pendente {
    background-color: #fff3cd;
    color: #856404;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
}

.status-andamento {
    background-color: #cce5ff;
    color: #004085;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
}

.status-finalizado {
    background-color: #d4edda;
    color: #155724;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
}

.dificuldade-baixa {
    background-color: #d4edda;
    color: #155724;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
}

.dificuldade-media {
    background-color: #fff3cd;
    color: #856404;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
}

.dificuldade-alta {
    background-color: #f8d7da;
    color: #721c24;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
}

.prazo-proximo {
    color: #ff9800;
    font-weight: 600;
}

.prazo-urgente {
    color: #f44336;
    font-weight: 600;
}

.prazo-normal {
    color: #4caf50;
    font-weight: 600;
}

.stDataFrame {
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stButton>button {
    background-color: var(--primary);
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    transition: all 0.3s;
}

.stButton>button:hover {
    background-color: var(--secondary);
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.stSelectbox, .stDateInput, .stTextInput, .stTextArea {
    margin-bottom: 1rem;
}

.filter-container {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}

.filter-item {
    flex: 1;
    min-width: 200px;
}

.stats-container {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}

.stat-card {
    flex: 1;
    min-width: 150px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 1rem;
    text-align: center;
}

.stat-value {
    font-size: 1.5rem;
    font-weight: 600;
    margin: 0.5rem 0;
}

.stat-label {
    color: #6c757d;
    font-size: 0.9rem;
}

@media (max-width: 768px) {
    .filter-container, .stats-container {
        flex-direction: column;
    }
    
    .filter-item, .stat-card {
        width: 100%;
    }
}
</style>
""", unsafe_allow_html=True)

# Dados iniciais
def carregar_dados():
    atividades = [
        {
            "Obrigação": "Sped Fiscal",
            "Descrição Técnica da Atividade": "Entrega do arquivo digital da EFD ICMS/IPI com registros fiscais de entradas, saídas, apuração de ICMS e IPI.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite de Entrega": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Grau de Dificuldade": "Média",
            "Responsável": "Equipe Fiscal",
            "Data de Início": (datetime.now() - timedelta(days=5)).date(),
            "Prazo Final": (datetime.now() + timedelta(days=3)).date(),
            "Progresso": 30
        },
        {
            "Obrigação": "Apuração do ICMS",
            "Descrição Técnica da Atividade": "Cálculo do ICMS devido no período com base nas operações de entrada e saída.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite de Entrega": "Até o dia 10 do mês subsequente",
            "Status": "Em Andamento",
            "Grau de Dificuldade": "Alta",
            "Responsável": "João Silva",
            "Data de Início": (datetime.now() - timedelta(days=2)).date(),
            "Prazo Final": (datetime.now() + timedelta(days=5)).date(),
            "Progresso": 65
        },
        {
            "Obrigação": "Diferencial de Alíquota",
            "Descrição Técnica da Atividade": "Cálculo e recolhimento do DIFAL nas aquisições interestaduais destinadas ao consumo ou ativo imobilizado.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite de Entrega": "Até o dia 10 do mês subsequente",
            "Status": "Finalizado",
            "Grau de Dificuldade": "Baixa",
            "Responsável": "Maria Oliveira",
            "Data de Início": (datetime.now() - timedelta(days=10)).date(),
            "Prazo Final": (datetime.now() - timedelta(days=2)).date(),
            "Progresso": 100
        },
        {
            "Obrigação": "Parametrização do sistema",
            "Descrição Técnica da Atividade": "Atualização do sistema ERP com as novas margens de valor agregado (MVA) do ICMS ST.",
            "Periodicidade": "Eventual",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite de Entrega": "Conforme publicação de nova legislação",
            "Status": "Pendente",
            "Grau de Dificuldade": "Alta",
            "Responsável": "Equipe TI",
            "Data de Início": None,
            "Prazo Final": None,
            "Progresso": 0
        },
        {
            "Obrigação": "GIA-Normal",
            "Descrição Técnica da Atividade": "Declaração mensal com informações do ICMS apurado e recolhido.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite de Entrega": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Grau de Dificuldade": "Média",
            "Responsável": "Carlos Santos",
            "Data de Início": (datetime.now() - timedelta(days=1)).date(),
            "Prazo Final": (datetime.now() + timedelta(days=7)).date(),
            "Progresso": 15
        },
        {
            "Obrigação": "Sped Contribuições",
            "Descrição Técnica da Atividade": "Entrega da EFD Contribuições com dados de PIS e COFINS.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite de Entrega": "Até o 10º dia útil do segundo mês subsequente",
            "Status": "Em Andamento",
            "Grau de Dificuldade": "Alta",
            "Responsável": "Ana Paula",
            "Data de Início": (datetime.now() - timedelta(days=3)).date(),
            "Prazo Final": (datetime.now() + timedelta(days=12)).date(),
            "Progresso": 45
        },
        {
            "Obrigação": "Cálculo PIS COFINS",
            "Descrição Técnica da Atividade": "Apuração dos valores de PIS e COFINS com base na receita bruta.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite de Entrega": "Até o 25º dia do mês subsequente",
            "Status": "Pendente",
            "Grau de Dificuldade": "Média",
            "Responsável": "Equipe Fiscal",
            "Data de Início": None,
            "Prazo Final": (datetime.now() + timedelta(days=20)).date(),
            "Progresso": 0
        },
        {
            "Obrigação": "Preenchimento DARFs",
            "Descrição Técnica da Atividade": "Geração dos DARFs para pagamento de tributos federais (PIS, COFINS, IPI, IRPJ, CSLL).",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite de Entrega": "Até o último dia útil do mês subsequente",
            "Status": "Finalizado",
            "Grau de Dificuldade": "Baixa",
            "Responsável": "Pedro Almeida",
            "Data de Início": (datetime.now() - timedelta(days=8)).date(),
            "Prazo Final": (datetime.now() - timedelta(days=1)).date(),
            "Progresso": 100
        }
    ]
    return pd.DataFrame(atividades)

# Inicialização do DataFrame
if 'df_atividades' not in st.session_state:
    st.session_state.df_atividades = carregar_dados()

# Funções auxiliares
def aplicar_estilo_status(val):
    if val == "Pendente":
        return "background-color: #fff3cd; color: #856404;"
    elif val == "Em Andamento":
        return "background-color: #cce5ff; color: #004085;"
    elif val == "Finalizado":
        return "background-color: #d4edda; color: #155724;"
    return ""

def aplicar_estilo_dificuldade(val):
    if val == "Baixa":
        return "background-color: #d4edda; color: #155724;"
    elif val == "Média":
        return "background-color: #fff3cd; color: #856404;"
    elif val == "Alta":
        return "background-color: #f8d7da; color: #721c24;"
    return ""

def calcular_dias_restantes(row):
    if pd.isna(row['Prazo Final']):
        return "Sem prazo"
    prazo = row['Prazo Final']
    if isinstance(prazo, str):
        try:
            prazo = datetime.strptime(prazo, "%Y-%m-%d").date()
        except:
            return "Sem prazo"
    dias = (prazo - datetime.now().date()).days
    return dias

def aplicar_estilo_prazo(val):
    if isinstance(val, str):
        return ""
    if val < 0:
        return "color: #f44336; font-weight: 600;"
    elif val <= 3:
        return "color: #f44336; font-weight: 600;"
    elif val <= 7:
        return "color: #ff9800; font-weight: 600;"
    else:
        return "color: #4caf50; font-weight: 600;"

# Interface do usuário
st.markdown('<div class="header"><h1>📊 Controle de Atividades Fiscais</h1></div>', unsafe_allow_html=True)

# Filtros
with st.container():
    st.markdown('<div class="card"><div class="card-title">Filtros</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_status = st.selectbox("Status", ["Todos", "Pendente", "Em Andamento", "Finalizado"])
    
    with col2:
        filtro_dificuldade = st.selectbox("Grau de Dificuldade", ["Todos", "Baixa", "Média", "Alta"])
    
    with col3:
        filtro_responsavel = st.selectbox("Responsável", ["Todos"] + list(st.session_state.df_atividades["Responsável"].unique()))
    
    st.markdown('</div>', unsafe_allow_html=True)

# Aplicar filtros
df_filtrado = st.session_state.df_atividades.copy()

if filtro_status != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Status"] == filtro_status]

if filtro_dificuldade != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Grau de Dificuldade"] == filtro_dificuldade]

if filtro_responsavel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Responsável"] == filtro_responsavel]

# Estatísticas
with st.container():
    st.markdown('<div class="stats-container">', unsafe_allow_html=True)
    
    total_atividades = len(st.session_state.df_atividades)
    pendentes = len(st.session_state.df_atividades[st.session_state.df_atividades["Status"] == "Pendente"])
    andamento = len(st.session_state.df_atividades[st.session_state.df_atividades["Status"] == "Em Andamento"])
    finalizadas = len(st.session_state.df_atividades[st.session_state.df_atividades["Status"] == "Finalizado"])
    
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">Total de Atividades</div>
        <div class="stat-value">{total_atividades}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Pendentes</div>
        <div class="stat-value">{pendentes}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Em Andamento</div>
        <div class="stat-value">{andamento}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Finalizadas</div>
        <div class="stat-value">{finalizadas}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Tabela de atividades
with st.container():
    st.markdown('<div class="card"><div class="card-title">Lista de Atividades</div>', unsafe_allow_html=True)
    
    # Adicionar coluna de dias restantes
    df_exibicao = df_filtrado.copy()
    df_exibicao["Dias Restantes"] = df_exibicao.apply(calcular_dias_restantes, axis=1)
    
    # Selecionar colunas para exibição
    colunas_exibicao = [
        "Obrigação", "Descrição Técnica da Atividade", "Periodicidade", 
        "Órgão Responsável", "Data Limite de Entrega", "Status", 
        "Grau de Dificuldade", "Responsável", "Dias Restantes", "Progresso"
    ]
    
    # Aplicar estilos diretamente no DataFrame
    styled_df = df_exibicao[colunas_exibicao].style.apply(
        lambda x: [aplicar_estilo_status(v) for v in x], subset=["Status"]
    ).apply(
        lambda x: [aplicar_estilo_dificuldade(v) for v in x], subset=["Grau de Dificuldade"]
    ).apply(
        lambda x: [aplicar_estilo_prazo(v) if isinstance(v, (int, float)) else "" for v in x], subset=["Dias Restantes"]
    )
    
    # Exibir o DataFrame estilizado
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=600,
        column_config={
            "Progresso": st.column_config.ProgressColumn(
                "Progresso",
                help="Progresso da atividade",
                format="%d%%",
                min_value=0,
                max_value=100
            ),
            "Dias Restantes": st.column_config.TextColumn(
                "Dias Restantes",
                help="Dias restantes para o prazo final"
            )
        }
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

# Formulário para adicionar nova atividade
with st.container():
    st.markdown('<div class="card"><div class="card-title">Adicionar Nova Atividade</div>', unsafe_allow_html=True)
    
    with st.form(key="form_nova_atividade"):
        col1, col2 = st.columns(2)
        
        with col1:
            obrigacao = st.text_input("Obrigação")
            descricao = st.text_area("Descrição Técnica da Atividade")
            periodicidade = st.selectbox("Periodicidade", ["Mensal", "Trimestral", "Anual", "Eventual", "Extinta"])
            orgao_responsavel = st.text_input("Órgão Responsável")
        
        with col2:
            data_limite = st.text_input("Data Limite de Entrega")
            status = st.selectbox("Status", ["Pendente", "Em Andamento", "Finalizado"])
            dificuldade = st.selectbox("Grau de Dificuldade", ["Baixa", "Média", "Alta"])
            responsavel = st.text_input("Responsável")
            prazo_final = st.date_input("Prazo Final", min_value=datetime.now().date())
            progresso = st.slider("Progresso (%)", 0, 100, 0)
        
        submitted = st.form_submit_button("Adicionar Atividade")
        
        if submitted:
            nova_atividade = {
                "Obrigação": obrigacao,
                "Descrição Técnica da Atividade": descricao,
                "Periodicidade": periodicidade,
                "Órgão Responsável": orgao_responsavel,
                "Data Limite de Entrega": data_limite,
                "Status": status,
                "Grau de Dificuldade": dificuldade,
                "Responsável": responsavel,
                "Data de Início": datetime.now().date(),
                "Prazo Final": prazo_final,
                "Progresso": progresso
            }
            
            novo_df = pd.concat([st.session_state.df_atividades, pd.DataFrame([nova_atividade])], ignore_index=True)
            st.session_state.df_atividades = novo_df
            st.success("Atividade adicionada com sucesso!")
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
