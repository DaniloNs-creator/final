import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from io import BytesIO
import calendar

# Configuração da página
st.set_page_config(
    page_title="PerformanceFit - Controle de Treinos",
    page_icon="🚴‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
def inject_css():
    st.markdown("""
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
            background-color: #f5f7fa;
        }
        .stApp header {
            background: linear-gradient(90deg, #1e3c72, #2a5298);
            color: white;
            padding: 1rem;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .stSidebar {
            background: linear-gradient(180deg, #ffffff, #f8f9fa);
            padding: 1rem;
            border-right: 1px solid #e1e5eb;
        }
        .profile-card {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            margin-bottom: 1rem;
        }
        .workout-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
            border-left: 5px solid #2a5298;
        }
        .calendar-day {
            padding: 5px;
            text-align: center;
            border-radius: 5px;
        }
        .calendar-day.workout {
            background-color: #e6f7ff;
            font-weight: bold;
        }
        .calendar-day.today {
            background-color: #fff2cc;
        }
        .calendar-day.selected {
            background-color: #d4edda;
        }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# Dados do usuário
user_data = {
    "nome": "Usuário",
    "idade": 28,
    "altura": 1.87,
    "peso": 108,
    "v02max": 173,
    "objetivo": "Emagrecimento e Performance no Ciclismo",
    "nivel": "Iniciante",
    "disponibilidade": "6 dias/semana"
}

# Zonas de frequência cardíaca
def calculate_zones(v02max):
    return {
        "Z1 (Recuperação)": (0.50 * v02max, 0.60 * v02max),
        "Z2 (Aeróbico)": (0.60 * v02max, 0.70 * v02max),
        "Z3 (Tempo)": (0.70 * v02max, 0.80 * v02max),
        "Z4 (Limiar)": (0.80 * v02max, 0.90 * v02max),
        "Z5 (VO2 Max)": (0.90 * v02max, 1.00 * v02max)
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

# Plano de treino de 60 dias
def generate_workout_plan(start_date):
    plan = []
    current_date = start_date
    
    for week in range(1, 9):  # 8 semanas = ~60 dias
        for day in range(1, 7):  # 6 dias de treino por semana
            if day == 1:  # Segunda-feira
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Ciclismo - Endurance",
                    "Duração": "1h15min",
                    "Zona FC": "Z2 (Aeróbico)",
                    "FC Alvo": f"{int(zones['Z2 (Aeróbico)'][0])}-{int(zones['Z2 (Aeróbico)'][1])} bpm",
                    "Descrição": "Pedal constante em terreno plano, mantendo FC na Z2"
                }
            elif day == 2:  # Terça-feira
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Força - Membros Inferiores",
                    "Duração": "1h",
                    "Zona FC": "N/A",
                    "FC Alvo": "N/A",
                    "Descrição": "Agachamento 4x12, Leg Press 4x12, Cadeira Extensora 3x15, Panturrilha 4x20"
                }
            elif day == 3:  # Quarta-feira
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Ciclismo - Intervalado",
                    "Duração": "1h",
                    "Zona FC": "Z4-Z5 (Limiar-VO2)",
                    "FC Alvo": f"{int(zones['Z4 (Limiar)'][0])}-{int(zones['Z5 (VO2 Max)'][1])} bpm",
                    "Descrição": "8x (2min Z4 + 2min Z1 recuperação)"
                }
            elif day == 4:  # Quinta-feira
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Ciclismo - Recuperação Ativa",
                    "Duração": "45min",
                    "Zona FC": "Z1 (Recuperação)",
                    "FC Alvo": f"{int(zones['Z1 (Recuperação)'][0])}-{int(zones['Z1 (Recuperação)'][1])} bpm",
                    "Descrição": "Pedal leve em terreno plano"
                }
            elif day == 5:  # Sexta-feira
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Força - Core e Superior",
                    "Duração": "1h",
                    "Zona FC": "N/A",
                    "FC Alvo": "N/A",
                    "Descrição": "Flexões 4x12, Remada Curvada 4x12, Prancha 3x1min, Abdominal Supra 3x20"
                }
            elif day == 6:  # Sábado
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Ciclismo - Longão",
                    "Duração": "2h30min" if week < 3 else "3h" if week < 6 else "3h30min",
                    "Zona FC": "Z2-Z3 (Aeróbico-Tempo)",
                    "FC Alvo": f"{int(zones['Z2 (Aeróbico)'][0])}-{int(zones['Z3 (Tempo)'][1])} bpm",
                    "Descrição": "Pedal longo com variação de terreno, focando em manter FC"
                }
            
            plan.append(workout)
            current_date += timedelta(days=1)
        
        current_date += timedelta(days=1)  # Domingo é dia de descanso
    
    return pd.DataFrame(plan)

# Interface do aplicativo
st.title("🚴‍♂️ PerformanceFit - Controle de Treinos e Dieta")
st.markdown("---")

# Sidebar com informações do usuário
with st.sidebar:
    st.markdown("""
    <div class="profile-card">
        <h3>Perfil do Atleta</h3>
        <p><strong>Nome:</strong> {nome}</p>
        <p><strong>Idade:</strong> {idade} anos</p>
        <p><strong>Altura:</strong> {altura}m</p>
        <p><strong>Peso:</strong> {peso}kg</p>
        <p><strong>VO2 Máx:</strong> {v02max} bpm</p>
        <p><strong>Objetivo:</strong> {objetivo}</p>
    </div>
    """.format(**user_data), unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### Zonas de Frequência Cardíaca")
    for zone, (min_fc, max_fc) in zones.items():
        st.markdown(f"**{zone}:** {int(min_fc)}-{int(max_fc)} bpm")
    
    st.markdown("---")
    if st.button("Exportar Plano para Excel"):
        today = datetime.now().date()
        workout_plan = generate_workout_plan(today)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workout_plan.to_excel(writer, sheet_name='Plano de Treino', index=False)
            diet_sheet = pd.DataFrame.from_dict({(i,j): diet_plan[i][j] 
                                               for i in diet_plan.keys() 
                                               for j in diet_plan[i].keys()},
                                               orient='index')
            diet_sheet.to_excel(writer, sheet_name='Plano Alimentar')
        
        output.seek(0)
        b64 = base64.b64encode(output.read()).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="Plano_Treino_Dieta.xlsx">Baixar Plano Completo</a>'
        st.markdown(href, unsafe_allow_html=True)

# Abas principais
tab1, tab2 = st.tabs(["📅 Plano de Treino", "🍽 Plano Alimentar"])

with tab1:
    today = datetime.now().date()
    workout_plan = generate_workout_plan(today)
    
    # Seção do calendário e treino do dia
    st.header("Calendário de Treinos")
    
    # Selecionar mês e ano
    col1, col2 = st.columns(2)
    with col1:
        selected_month = st.selectbox("Mês", range(1, 13), datetime.now().month - 1)
    with col2:
        selected_year = st.selectbox("Ano", range(datetime.now().year, datetime.now().year + 2), 0)
    
    # Gerar calendário
    cal = calendar.monthcalendar(selected_year, selected_month)
    
    # Mostrar calendário
    st.markdown(f"### {calendar.month_name[selected_month]} {selected_year}")
    
    # Cabeçalho dos dias da semana
    cols = st.columns(7)
    weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
    for i, day in enumerate(weekdays):
        cols[i].write(f"**{day}**")
    
    # Dias do mês
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                date_str = f"{day:02d}/{selected_month:02d}/{selected_year}"
                date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
                
                # Verificar se há treino nesse dia
                has_workout = any(workout['Dia'] == date_str for _, workout in workout_plan.iterrows())
                is_today = (day == datetime.now().day and 
                           selected_month == datetime.now().month and 
                           selected_year == datetime.now().year)
                
                day_class = "calendar-day"
                if has_workout:
                    day_class += " workout"
                if is_today:
                    day_class += " today"
                
                if cols[i].button(str(day), key=f"day_{day}", 
                                 help=date_str if has_workout else "Sem treino"):
                    selected_date = date_obj
                
                cols[i].markdown(f"""<div class="{day_class}">{day}</div>""", 
                                unsafe_allow_html=True)
    
    # Mostrar treino do dia selecionado
    st.markdown("---")
    st.header("Treino do Dia")
    
    # Selecionar data (padrão: hoje)
    selected_date = st.date_input("Selecione uma data", today)
    selected_date_str = selected_date.strftime("%d/%m/%Y")
    
    # Encontrar treino para a data selecionada
    daily_workout = workout_plan[workout_plan['Dia'] == selected_date_str]
    
    if not daily_workout.empty:
        workout = daily_workout.iloc[0]
        
        st.markdown(f"""<div class="workout-card">
            <h3>{workout['Dia da Semana']} - {selected_date_str}</h3>
            <p><strong>Tipo:</strong> {workout['Tipo de Treino']}</p>
            <p><strong>Duração:</strong> {workout['Duração']}</p>
            {f"<p><strong>Zona FC:</strong> {workout['Zona FC']}</p>" if workout['Zona FC'] != "N/A" else ""}
            {f"<p><strong>FC Alvo:</strong> {workout['FC Alvo']}</p>" if workout['FC Alvo'] != "N/A" else ""}
            <p><strong>Descrição:</strong> {workout['Descrição']}</p>
        </div>""", unsafe_allow_html=True)
        
        # Mostrar gráfico de zona de FC se aplicável
        if workout['Zona FC'] != "N/A":
            zone = workout['Zona FC']
            min_fc, max_fc = zones[zone]
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = (min_fc + max_fc) / 2,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': f"Zona FC Alvo: {zone}"},
                gauge = {
                    'axis': {'range': [None, 200]},
                    'steps': [
                        {'range': [0, min_fc], 'color': "lightgray"},
                        {'range': [min_fc, max_fc], 'color': "lightgreen"},
                        {'range': [max_fc, 200], 'color': "lightgray"}],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': (min_fc + max_fc) / 2}}))
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum treino programado para esta data")
    
    # Visualização completa do plano
    st.markdown("---")
    st.header("Plano Completo de Treinos")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        filter_type = st.selectbox("Filtrar por tipo", ["Todos"] + list(workout_plan["Tipo de Treino"].unique()))
    with col2:
        filter_week = st.selectbox("Filtrar por semana", ["Todas"] + [f"Semana {i}" for i in range(1, 9)])
    
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
    st.dataframe(filtered_plan[["Dia", "Dia da Semana", "Tipo de Treino", "Duração", "Zona FC", "FC Alvo"]], 
                 hide_index=True, use_container_width=True)

with tab2:
    st.header("Plano Alimentar - Opções Variadas")
    
    for meal, options in diet_plan.items():
        with st.expander(f"🔸 {meal}"):
            for opt, desc in options.items():
                st.markdown(f"""
                <div style="padding: 10px; margin-bottom: 10px; border-left: 3px solid #2a5298;">
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

# Rodapé
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 1rem; font-size: 0.8rem; color: #666;">
    <p>PerformanceFit © 2023 - Plano personalizado para {nome}</p>
    <p>Atualizado em: {date}</p>
</div>
""".format(nome=user_data["nome"], date=datetime.now().strftime("%d/%m/%Y")), unsafe_allow_html=True)
