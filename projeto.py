import streamlit as st
import pandas as pd

# Dados das atividades (exemplo com 5 atividades, pode expandir)
atividades = [
    {
        "Obrigação": "Sped Fiscal",
        "Descrição Técnica da Atividade": "Entrega do arquivo digital da EFD ICMS/IPI com registros fiscais de entradas, saídas, apuração de ICMS e IPI.",
        "Periodicidade": "Mensal",
        "Órgão Responsável": "SEFAZ-PR",
        "Data Limite de Entrega": "Até o dia 10 do mês subsequente"
    },
    {
        "Obrigação": "Apuração do ICMS",
        "Descrição Técnica da Atividade": "Cálculo do ICMS devido no período com base nas operações de entrada e saída.",
        "Periodicidade": "Mensal",
        "Órgão Responsável": "SEFAZ-PR",
        "Data Limite de Entrega": "Até o dia 10 do mês subsequente"
    },
    {
        "Obrigação": "Diferencial de Alíquota",
        "Descrição Técnica da Atividade": "Cálculo e recolhimento do DIFAL nas aquisições interestaduais destinadas ao consumo ou ativo imobilizado.",
        "Periodicidade": "Mensal",
        "Órgão Responsável": "SEFAZ-PR",
        "Data Limite de Entrega": "Até o dia 10 do mês subsequente"
    },
    {
        "Obrigação": "Parametrização do sistema",
        "Descrição Técnica da Atividade": "Atualização do sistema ERP com as novas margens de valor agregado (MVA) do ICMS ST.",
        "Periodicidade": "Eventual",
        "Órgão Responsável": "SEFAZ-PR",
        "Data Limite de Entrega": "Conforme publicação de nova legislação"
    },
    {
        "Obrigação": "GIA-Normal",
        "Descrição Técnica da Atividade": "Declaração mensal com informações do ICMS apurado e recolhido.",
        "Periodicidade": "Mensal",
        "Órgão Responsável": "SEFAZ-PR",
        "Data Limite de Entrega": "Até o dia 10 do mês subsequente"
    }
]

# Configuração da página
st.set_page_config(page_title="Controle de Atividades Fiscais", layout="wide")
st.markdown("<h1 style='text-align: center; color: #4B8BBE;'>Controle de Atividades Fiscais</h1>", unsafe_allow_html=True)

# Estilo CSS
st.markdown("""
    <style>
        .stSelectbox, .stTextInput, .stDateInput {
            background-color: #f0f2f6;
            border-radius: 5px;
            padding: 5px;
        }
        .activity-box {
            background-color: #ffffff;
            border: 1px solid #d3d3d3;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 2px 2px 5px #ccc;
        }
        .activity-title {
            font-size: 20px;
            font-weight: bold;
            color: #306998;
        }
        .activity-detail {
            font-size: 16px;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Interface para cada atividade
for atividade in atividades:
    with st.container():
        st.markdown("<div class='activity-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='activity-title'>{atividade['Obrigação']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='activity-detail'><strong>Descrição:</strong> {atividade['Descrição Técnica da Atividade']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='activity-detail'><strong>Periodicidade:</strong> {atividade['Periodicidade']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='activity-detail'><strong>Órgão Responsável:</strong> {atividade['Órgão Responsável']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='activity-detail'><strong>Data Limite:</strong> {atividade['Data Limite de Entrega']}</div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            status = st.selectbox("Status", ["Pendente", "Em Andamento", "Finalizado"], key=atividade['Obrigação'] + "_status")
        with col2:
            dificuldade = st.selectbox("Grau de Dificuldade", ["Baixa", "Média", "Alta"], key=atividade['Obrigação'] + "_dificuldade")
        with col3:
            prazo = st.date_input("Prazo de Entrega", key=atividade['Obrigação'] + "_prazo")
        st.markdown("</div>", unsafe_allow_html=True)
