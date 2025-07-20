import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import base64
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="PerformanceFit - Controle de Treinos",
    page_icon="🚴‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS embutido diretamente no código
def inject_css():
    st.markdown("""
    <style>
        /* Estilos gerais */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
            background-color: #f5f7fa;
        }

        /* Cabeçalho */
        .stApp header {
            background: linear-gradient(90deg, #1e3c72, #2a5298);
            color: white;
            padding: 1rem;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        /* Sidebar */
        .stSidebar {
            background: linear-gradient(180deg, #ffffff, #f8f9fa);
            padding: 1rem;
            border-right: 1px solid #e1e5eb;
        }

        .user-profile {
            animation: fadeIn 1s ease-in-out;
        }

        .profile-card {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            margin-bottom: 1rem;
            transition: transform 0.3s ease;
        }

        .profile-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
        }

        /* Cards de refeição */
        .meal-option {
            background: white;
            padding: 1rem;
            margin-bottom: 0.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            border-left: 4px solid #2a5298;
        }

        .meal-option:hover {
            background: #f8f9fa;
            transform: translateX(5px);
        }

        /* Abas */
        .stTabs [aria-selected="true"] {
            font-weight: bold;
            color: #1e3c72 !important;
        }

        .stTabs [aria-selected="true"]:after {
            content: '';
            display: block;
            width: 100%;
            height: 3px;
            background: #1e3c72;
            margin-top: 5px;
            animation: expand 0.3s ease-out;
        }

        /* Rodapé */
        .footer {
            text-align: center;
            padding: 1rem;
            font-size: 0.8rem;
            color: #666;
        }

        /* Animações */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes expand {
            from { width: 0; }
            to { width: 100%; }
        }

        /* Botões */
        .stButton>button {
            background: linear-gradient(90deg, #1e3c72, #2a5298);
            color: white;
            border: none;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }

        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }

        /* Tabelas */
        .stDataFrame {
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        /* Card de treino do dia */
        .workout-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            border-left: 5px solid #2a5298;
        }
        
        /* Calendário */
        .stDateInput>div>div>input {
            font-size: 1rem;
            padding: 0.5rem;
        }
        
        .date-picker-container {
            margin-bottom: 1.5rem;
        }
        
        /* Inputs de acompanhamento */
        .tracking-input {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.5rem;
        }
        
        /* Gráficos */
        .chart-container {
            background: white;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

# Injetar CSS
inject_css()

# Dados do usuário - ATUALIZADO com VO2 Max de 183
user_data = {
    "nome": "Usuário",
    "idade": 28,
    "altura": 1.87,
    "peso": 108,
    "v02max": 183,
    "objetivo": "Emagrecimento e Performance no Ciclismo",
    "nivel": "Iniciante",
    "disponibilidade": "6 dias/semana"
}

# Zonas de frequência cardíaca baseadas no VO2max de 183
def calculate_zones(v02max):
    return {
        "Z1 (Recuperação)": (0.50 * v02max, 0.60 * v02max),  # 92-110 bpm
        "Z2 (Aeróbico)": (0.60 * v02max, 0.70 * v02max),     # 110-128 bpm
        "Z3 (Tempo)": (0.70 * v02max, 0.80 * v02max),        # 128-146 bpm
        "Z4 (Limiar)": (0.80 * v02max, 0.90 * v02max),       # 146-165 bpm
        "Z5 (VO2 Max)": (0.90 * v02max, 1.00 * v02max)       # 165-183 bpm
    }

zones = calculate_zones(user_data["v02max"])

# Dieta baseada em alimentos acessíveis
diet_plan = {
    "Café da Manhã": {
        "Opção 1": "3 ovos + 2 fatias pão integral + 1 banana + 1 colher aveia",
        "Opção 2": "Vitamina (200ml leite + 1 banana + 1 colher aveia + 1 colher chia)",
        "Opção 3": "2 fatias pão integral + queijo cottage + 1 fruta"
    },
    "Lanche da Manhã": {
        "Opção 1": "1 fruta + 10 castanhas",
        "Opção 2": "1 iogurte natural + 1 colher linhaça",
        "Opção 3": "1 fatia pão integral + 1 colher pasta amendoim"
    },
    "Almoço": {
        "Opção 1": "1 concha arroz + 1 concha feijão + 150g frango + salada",
        "Opção 2": "2 batatas médias + 150g carne moída + legumes refogados",
        "Opção 3": "1 concha arroz integral + 150g peixe + brócolis cozido"
    },
    "Lanche da Tarde": {
        "Opção 1": "1 ovo cozido + 1 torrada integral",
        "Opção 2": "1 copo de vitamina (leite + fruta)",
        "Opção 3": "1 iogurte + 1 colher granola caseira"
    },
    "Jantar": {
        "Opção 1": "Omelete (3 ovos) + salada + 1 fatia pão integral",
        "Opção 2": "150g carne + purê de abóbora + salada",
        "Opção 3": "Sopa de legumes com frango desfiado"
    },
    "Ceia": {
        "Opção 1": "1 copo leite morno",
        "Opção 2": "1 iogurte natural",
        "Opção 3": "1 fatia queijo branco"
    }
}

# Dados de acompanhamento (persistência com session_state)
if 'tracking_data' not in st.session_state:
    st.session_state.tracking_data = pd.DataFrame(columns=['Data', 'Peso', 'Frequencia_Cardiaca'])

# Função para adicionar novos dados de acompanhamento
def add_tracking_data(date, weight, heart_rate):
    new_data = pd.DataFrame({
        'Data': [date],
        'Peso': [weight],
        'Frequencia_Cardiaca': [heart_rate]
    })
    st.session_state.tracking_data = pd.concat([st.session_state.tracking_data, new_data]).sort_values('Data').drop_duplicates('Data', keep='last')

# Plano de treino de 60 dias começando em 21/07/2025 com FCs atualizadas
def generate_workout_plan():
    plan = []
    start_date = datetime(2025, 7, 21).date()
    current_date = start_date
    workout_count = 0
    
    # Padrão de treino semanal com FCs atualizadas para VO2 Max de 183
    workout_pattern = [
        {   # Segunda-feira
            "name": "Ciclismo - Endurance", 
            "duration": "1h15min", 
            "zone": "Z2 (Aeróbico)", 
            "desc": "Pedal constante em terreno plano, mantendo FC entre 110-128 bpm"
        },
        {   # Terça-feira
            "name": "Força - Membros Inferiores", 
            "duration": "1h", 
            "zone": "N/A", 
            "desc": "Agachamento 4x12, Leg Press 4x12, Cadeira Extensora 3x15, Panturrilha 4x20"
        },
        {   # Quarta-feira
            "name": "Ciclismo - Intervalado", 
            "duration": "1h", 
            "zone": "Z4-Z5 (Limiar-VO2)", 
            "desc": "8x (2min em 146-183 bpm + 2min recuperação em Z1)"
        },
        {   # Quinta-feira
            "name": "Ciclismo - Recuperação Ativa", 
            "duration": "45min", 
            "zone": "Z1 (Recuperação)", 
            "desc": "Pedal leve em terreno plano, mantendo FC entre 92-110 bpm"
        },
        {   # Sexta-feira
            "name": "Força - Core e Superior", 
            "duration": "1h", 
            "zone": "N/A", 
            "desc": "Flexões 4x12, Remada Curvada 4x12, Prancha 3x1min, Abdominal Supra 3x20"
        },
        {   # Sábado
            "name": "Ciclismo - Longão", 
            "duration": "2h30min", 
            "zone": "Z2-Z3 (Aeróbico-Tempo)", 
            "desc": "Pedal longo com variação de terreno, FC entre 110-146 bpm"
        }
    ]
    
    # Ajustar duração do longão conforme as semanas avançam
    def get_long_duration(week):
        if week < 3:
            return "2h30min"
        elif week < 6:
            return "3h"
        else:
            return "3h30min"
    
    while workout_count < 60:
        day_of_week = current_date.weekday()  # 0=Segunda, 6=Domingo
        
        # Domingo é dia de descanso
        if day_of_week == 6:
            current_date += timedelta(days=1)
            continue
            
        # Determinar o tipo de treino baseado no dia da semana
        if day_of_week < 6:  # Segunda a Sábado
            workout_type = workout_pattern[day_of_week]
            
            # Ajustar o longão no sábado
            if day_of_week == 5:  # Sábado
                week_number = (workout_count // 6) + 1
                workout_type = {
                    "name": "Ciclismo - Longão",
                    "duration": get_long_duration(week_number),
                    "zone": "Z2-Z3 (Aeróbico-Tempo)",
                    "desc": f"Pedal longo com variação de terreno, FC entre 110-146 bpm"
                }
            
            # Calcular FC Alvo com base no VO2 Max de 183
            if "Z1" in workout_type["zone"]:
                fc_range = "92-110 bpm"
            elif "Z2" in workout_type["zone"]:
                fc_range = "110-128 bpm"
            elif "Z3" in workout_type["zone"]:
                fc_range = "128-146 bpm"
            elif "Z4-Z5" in workout_type["zone"]:
                fc_range = "146-183 bpm"
            else:
                fc_range = "N/A"
            
            workout = {
                "Dia": current_date.strftime("%d/%m/%Y"),
                "Data": current_date,
                "Dia da Semana": current_date.strftime("%A"),
                "Tipo de Treino": workout_type["name"],
                "Duração": workout_type["duration"],
                "Zona FC": workout_type["zone"],
                "FC Alvo": fc_range,
                "Descrição": workout_type["desc"]
            }
            
            plan.append(workout)
            workout_count += 1
        
        current_date += timedelta(days=1)
    
    return pd.DataFrame(plan)

# Interface do aplicativo
st.title("🚴‍♂️ PerformanceFit - Controle de Treinos e Dieta")
st.markdown("---")

# Sidebar com informações do usuário ATUALIZADAS
with st.sidebar:
    st.markdown("""
    <div class="user-profile">
        <h2>Perfil do Atleta</h2>
        <div class="profile-card">
            <p><strong>Nome:</strong> {nome}</p>
            <p><strong>Idade:</strong> {idade} anos</p>
            <p><strong>Altura:</strong> {altura}m</p>
            <p><strong>Peso:</strong> {peso}kg</p>
            <p><strong>VO2 Máx:</strong> {v02max} bpm</p>
            <p><strong>Objetivo:</strong> {objetivo}</p>
            <p><strong>Nível:</strong> {nivel}</p>
            <p><strong>Disponibilidade:</strong> {disponibilidade}</p>
        </div>
    </div>
    """.format(**user_data), unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### Zonas de Frequência Cardíaca (VO2 Max: 183 bpm)")
    for zone, (min_fc, max_fc) in zones.items():
        st.markdown(f"**{zone}:** {int(min_fc)}-{int(max_fc)} bpm")
    
    st.markdown("---")
    st.markdown("### Download do Plano")
    if st.button("Exportar para Excel"):
        workout_plan = generate_workout_plan()
        
        # Criar um arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workout_plan.to_excel(writer, sheet_name='Plano de Treino', index=False)
            
            # Adicionar a dieta
            diet_sheet = pd.DataFrame.from_dict({(i,j): diet_plan[i][j] 
                                               for i in diet_plan.keys() 
                                               for j in diet_plan[i].keys()},
                                               orient='index')
            diet_sheet.to_excel(writer, sheet_name='Plano Alimentar')
            
            # Adicionar dados de acompanhamento
            if not st.session_state.tracking_data.empty:
                st.session_state.tracking_data.to_excel(writer, sheet_name='Acompanhamento', index=False)
        
        output.seek(0)
        b64 = base64.b64encode(output.read()).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="Plano_Treino_Dieta.xlsx">Baixar Plano Completo</a>'
        st.markdown(href, unsafe_allow_html=True)

# Abas principais
tab1, tab2, tab3 = st.tabs(["📅 Plano de Treino", "🍽 Plano Alimentar", "📊 Acompanhamento"])

with tab1:
    workout_plan = generate_workout_plan()
    end_date = workout_plan["Data"].max()
    st.header(f"Plano de Treino - 60 Dias (21/07/2025 a {end_date.strftime('%d/%m/%Y')})")
    
    # Seletor de data em formato de calendário
    st.subheader("📆 Consultar Treino por Data")
    
    # Definir range de datas para o calendário
    min_date = workout_plan["Data"].min()
    max_date = workout_plan["Data"].max()
    
    # Widget de seleção de data
    selected_date = st.date_input(
        "Selecione a data para ver o treino:",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY"
    )
    
    # Converter a data selecionada para o mesmo formato usado no DataFrame
    selected_date_str = selected_date.strftime("%d/%m/%Y")
    
    # Filtrar o treino da data selecionada
    selected_workout = workout_plan[workout_plan["Dia"] == selected_date_str]
    
    if not selected_workout.empty:
        workout = selected_workout.iloc[0]
        st.markdown(f"""
        <div class="workout-card">
            <h3>Treino do dia {workout['Dia']} ({workout['Dia da Semana']})</h3>
            <p><strong>🔹 Tipo de Treino:</strong> {workout['Tipo de Treino']}</p>
            <p><strong>⏱ Duração:</strong> {workout['Duração']}</p>
            <p><strong>❤️ Zona FC:</strong> {workout['Zona FC']}</p>
            <p><strong>🎯 FC Alvo:</strong> {workout['FC Alvo']}</p>
            <p><strong>📝 Descrição:</strong> {workout['Descrição']}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Dia de descanso ou nenhum treino encontrado para a data selecionada.")
    
    # Filtros
    st.subheader("Filtrar Treinos")
    col1, col2 = st.columns(2)
    with col1:
        filter_type = st.selectbox("Filtrar por Tipo de Treino", ["Todos"] + list(workout_plan["Tipo de Treino"].unique()))
    with col2:
        filter_week = st.selectbox("Filtrar por Semana", ["Todas"] + [f"Semana {i}" for i in range(1, 11)])
    
    # Aplicar filtros
    filtered_plan = workout_plan.copy()
    if filter_type != "Todos":
        filtered_plan = filtered_plan[filtered_plan["Tipo de Treino"] == filter_type]
    if filter_week != "Todas":
        week_num = int(filter_week.split()[1])
        start_idx = (week_num - 1) * 6
        end_idx = start_idx + 6
        filtered_plan = filtered_plan.iloc[start_idx:end_idx]
    
    # Mostrar tabela
    st.dataframe(filtered_plan.drop(columns=["Data"]), hide_index=True, use_container_width=True)
    
    # Gráfico de distribuição de treinos
    st.subheader("Distribuição de Treinos")
    workout_dist = workout_plan["Tipo de Treino"].value_counts().reset_index()
    workout_dist.columns = ["Tipo de Treino", "Quantidade"]
    
    fig = px.pie(workout_dist, values="Quantidade", names="Tipo de Treino", 
                 color_discrete_sequence=px.colors.sequential.RdBu,
                 hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Plano Alimentar - Opções Variadas")
    
    for meal, options in diet_plan.items():
        with st.expander(f"🔸 {meal}"):
            for opt, desc in options.items():
                st.markdown(f"""
                <div class="meal-option">
                    <h4>{opt}</h4>
                    <p>{desc}</p>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("Recomendações Nutricionais")
    st.markdown("""
    - Consuma proteína em todas as refeições (ovos, frango, carne, peixe)
    - Hidrate-se bem (3-4L de água por dia)
    - Prefira carboidratos complexos (arroz integral, batata, aveia)
    - Gorduras saudáveis (castanhas, azeite, abacate)
    - Coma legumes e verduras à vontade
    """)

with tab3:
    st.header("📊 Acompanhamento de Evolução")
    
    # Seção para adicionar novos dados
    with st.container():
        st.subheader("Adicionar Novos Dados")
        today = datetime.now().date()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            tracking_date = st.date_input("Data", value=today)
        with col2:
            weight = st.number_input("Peso (kg)", min_value=30.0, max_value=200.0, value=user_data["peso"], step=0.1)
        with col3:
            heart_rate = st.number_input("Frequência Cardíaca em Repouso (bpm)", min_value=40, max_value=120, value=65)
        
        if st.button("Salvar Dados"):
            add_tracking_data(tracking_date, weight, heart_rate)
            st.success("Dados salvos com sucesso!")
            user_data["peso"] = weight  # Atualiza o peso no perfil
    
    # Seção de gráficos
    if not st.session_state.tracking_data.empty:
        st.markdown("---")
        st.subheader("Evolução ao Longo do Tempo")
        
        # Processar dados
        tracking_df = st.session_state.tracking_data.sort_values('Data')
        tracking_df['Data'] = pd.to_datetime(tracking_df['Data'])
        tracking_df = tracking_df.set_index('Data').resample('D').mean().interpolate().reset_index()
        
        # Gráfico de peso
        st.markdown("#### Evolução do Peso")
        fig_weight = px.line(tracking_df, x='Data', y='Peso', 
                            labels={'Peso': 'Peso (kg)'},
                            markers=True,
                            color_discrete_sequence=['#1e3c72'])
        fig_weight.update_layout(yaxis_range=[tracking_df['Peso'].min()-2, tracking_df['Peso'].max()+2])
        st.plotly_chart(fig_weight, use_container_width=True)
        
        # Gráfico de frequência cardíaca
        st.markdown("#### Evolução da Frequência Cardíaca em Repouso")
        fig_hr = px.line(tracking_df, x='Data', y='Frequencia_Cardiaca', 
                        labels={'Frequencia_Cardiaca': 'FC (bpm)'},
                        markers=True,
                        color_discrete_sequence=['#e63946'])
        fig_hr.update_layout(yaxis_range=[tracking_df['Frequencia_Cardiaca'].min()-5, tracking_df['Frequencia_Cardiaca'].max()+5])
        st.plotly_chart(fig_hr, use_container_width=True)
        
        # Mostrar tabela com dados históricos
        st.markdown("---")
        st.subheader("Histórico Completo")
        st.dataframe(st.session_state.tracking_data.sort_values('Data', ascending=False), hide_index=True)
    else:
        st.warning("Nenhum dado de acompanhamento registrado ainda. Adicione dados acima.")

# Rodapé
st.markdown("---")
st.markdown("""
<div class="footer">
    <p>PerformanceFit © 2023 - Plano personalizado para {nome}</p>
    <p>Atualizado em: {date}</p>
</div>
""".format(nome=user_data["nome"], date=datetime.now().strftime("%d/%m/%Y")), unsafe_allow_html=True)
