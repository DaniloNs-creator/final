import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

# Configuração inicial da página
st.set_page_config(
    page_title="Controle de Atividades Fiscais - HÄFELE BRASIL",
    page_icon="📊",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    :root {
        --primary-color: #4a8fe7;
        --secondary-color: #f0f2f6;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
        --dark-color: #343a40;
        --light-color: #f8f9fa;
    }
    
    /* Estilos gerais */
    .stApp {
        background-color: #f5f7fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: var(--dark-color);
        font-weight: 600;
    }
    
    /* Estilo do cabeçalho */
    .header {
        background: linear-gradient(135deg, #4a8fe7 0%, #1e3c72 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .header h1 {
        color: white;
        margin: 0;
    }
    
    /* Estilo dos cards */
    .card {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Estilo dos botões */
    .stButton>button {
        border-radius: 0.5rem;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Estilo dos selects */
    .stSelectbox>div>div>select {
        border-radius: 0.5rem;
        padding: 0.5rem;
    }
    
    /* Estilo das tabelas */
    .stDataFrame {
        border-radius: 0.5rem;
        overflow: hidden;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .status-pendente {
        background-color: #fff3cd;
        color: #856404;
    }
    
    .status-andamento {
        background-color: #cce5ff;
        color: #004085;
    }
    
    .status-finalizado {
        background-color: #d4edda;
        color: #155724;
    }
    
    /* Dificuldade badges */
    .dificuldade-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .dificuldade-baixa {
        background-color: #d4edda;
        color: #155724;
    }
    
    .dificuldade-media {
        background-color: #fff3cd;
        color: #856404;
    }
    
    .dificuldade-alta {
        background-color: #f8d7da;
        color: #721c24;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate-fadeIn {
        animation: fadeIn 0.5s ease-out forwards;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .header {
            padding: 1rem;
        }
        
        .card {
            padding: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Dados iniciais
def load_initial_data():
    data = [
        {
            "Obrigação": "Sped Fiscal",
            "Descrição": "Entrega do arquivo digital da EFD ICMS/IPI com registros fiscais de entradas, saídas, apuração de ICMS e IPI.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": datetime.now() - timedelta(days=5),
            "Data Conclusão": None
        },
        {
            "Obrigação": "Apuração do ICMS",
            "Descrição": "Cálculo do ICMS devido no período com base nas operações de entrada e saída.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Diferencial de Alíquota",
            "Descrição": "Cálculo e recolhimento do DIFAL nas aquisições interestaduais destinadas ao consumo ou ativo imobilizado.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Parametrização do sistema",
            "Descrição": "Atualização do sistema ERP com as novas margens de valor agregado (MVA) do ICMS ST.",
            "Periodicidade": "Eventual",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Conforme publicação de nova legislação",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": datetime.now() + timedelta(days=90),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "GIA-Normal",
            "Descrição": "Declaração mensal com informações do ICMS apurado e recolhido.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Em Andamento",
            "Dificuldade": "Média",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": datetime.now() - timedelta(days=3),
            "Data Conclusão": None
        },
        {
            "Obrigação": "GIA-ST",
            "Descrição": "Declaração mensal do ICMS-ST devido por substituição tributária.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Finalizado",
            "Dificuldade": "Alta",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": datetime.now() - timedelta(days=10),
            "Data Conclusão": datetime.now() - timedelta(days=1)
        },
        {
            "Obrigação": "Apuração IPI",
            "Descrição": "Cálculo do IPI devido com base nas saídas de produtos industrializados.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Baixa",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Sped Contribuições",
            "Descrição": "Entrega da EFD Contribuições com dados de PIS e COFINS.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o 10º dia útil do segundo mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=60),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Cálculo PIS COFINS",
            "Descrição": "Apuração dos valores de PIS e COFINS com base na receita bruta.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o 25º dia do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": datetime.now().replace(day=25) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Preenchimento DARFs",
            "Descrição": "Geração dos DARFs para pagamento de tributos federais (PIS, COFINS, IPI, IRPJ, CSLL).",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o último dia útil do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Baixa",
            "Prazo": datetime.now() + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Preenchimento GR-PR ICMS",
            "Descrição": "Geração da guia de recolhimento do ICMS normal no Paraná.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Baixa",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "DIRF - Prestadores",
            "Descrição": "Declaração de retenções de IRRF sobre pagamentos a prestadores de serviços.",
            "Periodicidade": "Anual",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Último dia útil de fevereiro",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": datetime(datetime.now().year, 2, 28),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "INSS Faturamento",
            "Descrição": "Apuração da contribuição previdenciária sobre a receita bruta.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o dia 20 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": datetime.now().replace(day=20) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "REINF",
            "Descrição": "Entrega da EFD-REINF com retenções de INSS e contribuições previdenciárias.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o dia 15 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": datetime.now().replace(day=15) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "DCTF WEB",
            "Descrição": "Declaração de débitos e créditos tributários federais via eSocial/REINF.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o dia 15 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": datetime.now().replace(day=15) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "DCTF",
            "Descrição": "Declaração de débitos e créditos tributários federais convencionais.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Até o 15º dia útil do segundo mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": datetime.now() + timedelta(days=60),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "ISS Eletrônico",
            "Descrição": "Declaração e recolhimento do ISS sobre serviços prestados.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "Prefeitura de Piraquara",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Média",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Conciliação GNRE ICMS ST",
            "Descrição": "Conferência entre GNREs pagas e notas fiscais de saída com ICMS ST.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "ST Faturamento",
            "Descrição": "Conferência dos cálculos de ICMS ST nas vendas com substituição tributária.",
            "Periodicidade": "Mensal",
            "Órgão Responsável": "SEFAZ-PR",
            "Data Limite": "Até o dia 10 do mês subsequente",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": datetime.now().replace(day=10) + timedelta(days=30),
            "Data Início": None,
            "Data Conclusão": None
        },
        {
            "Obrigação": "Cálculo IRPJ/CSLL",
            "Descrição": "Apuração do IRPJ e CSLL com base no lucro presumido ou real.",
            "Periodicidade": "Trimestral",
            "Órgão Responsável": "Receita Federal",
            "Data Limite": "Último dia útil do mês subsequente ao trimestre",
            "Status": "Pendente",
            "Dificuldade": "Alta",
            "Prazo": datetime.now() + timedelta(days=90),
            "Data Início": None,
            "Data Conclusão": None
        }
    ]
    return pd.DataFrame(data)

# Carregar ou inicializar dados
if 'df_atividades' not in st.session_state:
    st.session_state.df_atividades = load_initial_data()

# Funções auxiliares
def apply_status_style(status):
    if status == "Pendente":
        return '<span class="status-badge status-pendente">Pendente</span>'
    elif status == "Em Andamento":
        return '<span class="status-badge status-andamento">Em Andamento</span>'
    else:
        return '<span class="status-badge status-finalizado">Finalizado</span>'

def apply_difficulty_style(dificuldade):
    if dificuldade == "Baixa":
        return '<span class="dificuldade-badge dificuldade-baixa">Baixa</span>'
    elif dificuldade == "Média":
        return '<span class="dificuldade-badge dificuldade-media">Média</span>'
    else:
        return '<span class="dificuldade-badge dificuldade-alta">Alta</span>'

def calculate_days_remaining(row):
    if pd.isna(row['Prazo']) or row['Status'] == 'Finalizado':
        return None
    hoje = datetime.now()
    prazo = row['Prazo']
    return (prazo - hoje).days

# Interface do usuário
def main():
    st.markdown('<div class="header animate-fadeIn"><h1>📊 Controle de Atividades Fiscais - HÄFELE BRASIL</h1></div>', unsafe_allow_html=True)
    
    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Status", ["Todos", "Pendente", "Em Andamento", "Finalizado"])
        with col2:
            dificuldade_filter = st.selectbox("Dificuldade", ["Todos", "Baixa", "Média", "Alta"])
        with col3:
            orgao_filter = st.selectbox("Órgão Responsável", ["Todos"] + list(st.session_state.df_atividades['Órgão Responsável'].unique()))
    
    # Aplicar filtros
    filtered_df = st.session_state.df_atividades.copy()
    if status_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    if dificuldade_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Dificuldade'] == dificuldade_filter]
    if orgao_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Órgão Responsável'] == orgao_filter]
    
    # Calcular dias restantes
    filtered_df['Dias Restantes'] = filtered_df.apply(calculate_days_remaining, axis=1)
    
    # Mostrar métricas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Atividades", len(st.session_state.df_atividades))
    with col2:
        st.metric("Pendentes", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Pendente"]))
    with col3:
        st.metric("Em Andamento", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Em Andamento"]))
    with col4:
        st.metric("Finalizadas", len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == "Finalizado"]))
    
    # Gráficos
    with st.expander("📈 Análise Gráfica", expanded=True):
        tab1, tab2, tab3 = st.tabs(["Status", "Dificuldade", "Prazo"])
        
        with tab1:
            status_counts = st.session_state.df_atividades['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Quantidade']
            fig_status = px.pie(status_counts, values='Quantidade', names='Status', 
                               title='Distribuição por Status',
                               color='Status',
                               color_discrete_map={'Pendente':'#ffc107', 'Em Andamento':'#007bff', 'Finalizado':'#28a745'})
            st.plotly_chart(fig_status, use_container_width=True)
        
        with tab2:
            dificuldade_counts = st.session_state.df_atividades['Dificuldade'].value_counts().reset_index()
            dificuldade_counts.columns = ['Dificuldade', 'Quantidade']
            fig_dificuldade = px.bar(dificuldade_counts, x='Dificuldade', y='Quantidade', 
                                   title='Distribuição por Nível de Dificuldade',
                                   color='Dificuldade',
                                   color_discrete_map={'Baixa':'#28a745', 'Média':'#ffc107', 'Alta':'#dc3545'})
            st.plotly_chart(fig_dificuldade, use_container_width=True)
        
        with tab3:
            prazo_df = st.session_state.df_atividades.copy()
            prazo_df['Prazo'] = pd.to_datetime(prazo_df['Prazo'])
            prazo_df = prazo_df.sort_values('Prazo')
            prazo_df['Prazo Formatado'] = prazo_df['Prazo'].dt.strftime('%d/%m/%Y')
            
            # Criar datas mínimas para o gráfico de timeline
            prazo_df['Data Início'] = prazo_df['Data Início'].fillna(prazo_df['Prazo'] - timedelta(days=1))
            
            fig_prazo = px.timeline(prazo_df, x_start="Data Início", x_end="Prazo", y="Obrigação", 
                                   color="Status",
                                   title='Linha do Tempo das Atividades',
                                   color_discrete_map={'Pendente':'#ffc107', 'Em Andamento':'#007bff', 'Finalizado':'#28a745'},
                                   hover_name="Obrigação",
                                   hover_data=["Status", "Dificuldade", "Prazo Formatado"])
            fig_prazo.update_yaxes(autorange="reversed")
            fig_prazo.update_layout(showlegend=True)
            st.plotly_chart(fig_prazo, use_container_width=True)
    
    # Tabela de atividades
    st.markdown('<div class="card animate-fadeIn"><h3>📋 Lista de Atividades</h3></div>', unsafe_allow_html=True)
    
    # Formatar DataFrame para exibição
    display_df = filtered_df.copy()
    display_df['Status'] = display_df['Status'].apply(apply_status_style)
    display_df['Dificuldade'] = display_df['Dificuldade'].apply(apply_difficulty_style)
    display_df['Prazo'] = display_df['Prazo'].dt.strftime('%d/%m/%Y')
    display_df['Data Início'] = display_df['Data Início'].apply(
        lambda x: x.strftime('%d/%m/%Y') if not pd.isna(x) else ''
    )
    display_df['Data Conclusão'] = display_df['Data Conclusão'].apply(
        lambda x: x.strftime('%d/%m/%Y') if not pd.isna(x) else ''
    )
    
    # Selecionar colunas para exibição
    cols_to_display = ['Obrigação', 'Descrição', 'Periodicidade', 'Órgão Responsável', 
                      'Data Limite', 'Status', 'Dificuldade', 'Prazo', 'Dias Restantes']
    
    st.write(display_df[cols_to_display].to_html(escape=False, index=False), unsafe_allow_html=True)
    
    # Adicionar nova atividade
    with st.expander("➕ Adicionar Nova Atividade", expanded=False):
        with st.form("nova_atividade_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nova_obrigacao = st.text_input("Obrigação*", placeholder="Nome da obrigação fiscal")
                nova_descricao = st.text_area("Descrição*", placeholder="Descrição detalhada da atividade")
                nova_periodicidade = st.selectbox("Periodicidade*", ["Mensal", "Trimestral", "Anual", "Eventual", "Extinta"])
            with col2:
                novo_orgao = st.text_input("Órgão Responsável*", placeholder="Órgão responsável")
                nova_data_limite = st.text_input("Data Limite de Entrega*", placeholder="Ex: Até o dia 10 do mês subsequente")
                novo_status = st.selectbox("Status*", ["Pendente", "Em Andamento", "Finalizado"])
                nova_dificuldade = st.selectbox("Dificuldade*", ["Baixa", "Média", "Alta"])
                novo_prazo = st.date_input("Prazo Final*")
            
            if st.form_submit_button("Adicionar Atividade"):
                if nova_obrigacao and nova_descricao and novo_orgao and nova_data_limite:
                    nova_atividade = {
                        "Obrigação": nova_obrigacao,
                        "Descrição": nova_descricao,
                        "Periodicidade": nova_periodicidade,
                        "Órgão Responsável": novo_orgao,
                        "Data Limite": nova_data_limite,
                        "Status": novo_status,
                        "Dificuldade": nova_dificuldade,
                        "Prazo": datetime.combine(novo_prazo, datetime.min.time()),
                        "Data Início": datetime.now() if novo_status == "Em Andamento" else None,
                        "Data Conclusão": datetime.now() if novo_status == "Finalizado" else None
                    }
                    
                    # Adicionar nova atividade usando concat
                    new_df = pd.DataFrame([nova_atividade])
                    st.session_state.df_atividades = pd.concat(
                        [st.session_state.df_atividades, new_df], 
                        ignore_index=True
                    )
                    st.success("✅ Atividade adicionada com sucesso!")
                else:
                    st.error("⚠️ Preencha todos os campos obrigatórios (marcados com *)")
    
    # Editar status das atividades
    with st.expander("✏️ Editar Status das Atividades", expanded=False):
        atividades_para_editar = st.session_state.df_atividades['Obrigação'].unique()
        atividade_selecionada = st.selectbox("Selecione a atividade para editar", atividades_para_editar)
        
        atividade_idx = st.session_state.df_atividades[st.session_state.df_atividades['Obrigação'] == atividade_selecionada].index[0]
        current_status = st.session_state.df_atividades.loc[atividade_idx, 'Status']
        
        col1, col2 = st.columns([1, 3])
        with col1:
            novo_status = st.selectbox("Novo Status", ["Pendente", "Em Andamento", "Finalizado"], 
                                      index=["Pendente", "Em Andamento", "Finalizado"].index(current_status))
        
        if st.button("Atualizar Status"):
            st.session_state.df_atividades.loc[atividade_idx, 'Status'] = novo_status
            
            if novo_status == "Em Andamento" and pd.isna(st.session_state.df_atividades.loc[atividade_idx, 'Data Início']):
                st.session_state.df_atividades.loc[atividade_idx, 'Data Início'] = datetime.now()
            
            if novo_status == "Finalizado":
                st.session_state.df_atividades.loc[atividade_idx, 'Data Conclusão'] = datetime.now()
            
            st.success(f"✅ Status da atividade '{atividade_selecionada}' atualizado para '{novo_status}'!")

if __name__ == "__main__":
    main()
