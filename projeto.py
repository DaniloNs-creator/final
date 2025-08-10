import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta, date
import base64
from io import BytesIO
import time

# Configuração da página premium
st.set_page_config(
    page_title="🏋️‍♂️ PerformanceFit Pro",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.performancefit.com.br/ajuda',
        'Report a bug': "https://www.performancefit.com.br/bug",
        'About': "### Versão Premium 2.0\nSistema de controle de treinos e nutrição avançado"
    }
)

# CSS Premium com animações e efeitos otimizados
def inject_premium_css():
    st.markdown("""
    <style>
        :root {
            --primary: #4361ee;
            --secondary: #3f37c9;
            --accent: #4895ef;
            --light: #f8f9fa;
            --dark: #212529;
            --success: #4cc9f0;
            --warning: #f72585;
            --border-radius: 12px;
            --box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }
        
        /* Efeito de fundo dinâmico otimizado */
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
            background-attachment: fixed;
            animation: gradientBG 15s ease infinite;
        }
        
        @keyframes gradientBG {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }
        
        /* Cabeçalho premium otimizado */
        .stApp header {
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 0 0 var(--border-radius) var(--border-radius);
            box-shadow: var(--box-shadow);
            position: sticky;
            top: 0;
            z-index: 999;
            animation: fadeInDown 0.5s ease-out;
        }
        
        /* Sidebar premium com performance melhorada */
        .stSidebar {
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(5px);
            padding: 1rem;
            border-right: none;
            box-shadow: 5px 0 15px rgba(0, 0, 0, 0.05);
        }
        
        /* Cards reutilizáveis com classes consistentes */
        .card {
            background: white;
            padding: 1.25rem;
            border-radius: var(--border-radius);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.25rem;
            transition: var(--transition);
            border-left: 4px solid var(--accent);
        }
        
        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }
        
        .card-highlight {
            border-left: 4px solid var(--primary);
        }
        
        /* Títulos consistentes */
        .card h3, .card h4 {
            margin-top: 0;
            color: var(--primary);
        }
        
        /* Abas premium com hover suave */
        .stTabs [aria-selected="true"] {
            font-weight: 600;
            color: var(--primary) !important;
        }
        
        .stTabs [aria-selected="true"]:after {
            content: '';
            display: block;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
            margin-top: 0.25rem;
            border-radius: 2px;
            animation: tabUnderline 0.3s ease-out;
        }
        
        /* Botões com efeitos acessíveis */
        .stButton>button {
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1.25rem;
            transition: var(--transition);
            font-weight: 500;
            box-shadow: 0 4px 6px rgba(67, 97, 238, 0.15);
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(67, 97, 238, 0.2);
        }
        
        /* Inputs com foco visível */
        .stTextInput>div>div>input:focus,
        .stNumberInput>div>div>input:focus,
        .stDateInput>div>div>input:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 2px rgba(72, 149, 239, 0.2) !important;
        }
        
        /* Animações otimizadas */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes slideInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Efeitos de loading otimizados */
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Layout responsivo para cards */
        .card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        
        /* Melhorias de acessibilidade */
        [aria-selected="true"] {
            font-weight: 600;
        }
        
        /* Tooltips acessíveis */
        [data-tooltip] {
            position: relative;
        }
        
        [data-tooltip]:hover:after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: var(--dark);
            color: white;
            padding: 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            white-space: nowrap;
            z-index: 1000;
        }
        
        /* Espaçamento consistente */
        .section {
            margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

# Injetar CSS premium
inject_premium_css()

# Efeito de loading inicial otimizado
@st.cache_data
def simulate_loading():
    time.sleep(1.2)
    return True

with st.spinner('Carregando seus dados premium...'):
    simulate_loading()

# Dados do usuário premium (agora com cache)
@st.cache_data
def get_user_data():
    return {
        "nome": "Atleta Elite",
        "idade": 28,
        "altura": 1.87,
        "peso": 108,
        "v02max": 173,
        "objetivo": "Performance Olímpica no Ciclismo",
        "nivel": "Avançado",
        "disponibilidade": "6 dias/semana",
        "membro_desde": "01/01/2023",
        "plano": "Premium Diamond"
    }

user_data = get_user_data()

# Zonas de frequência cardíaca com cache
@st.cache_data
def calculate_zones(v02max):
    zones = {
        "Z1 (Recuperação)": (0.50 * v02max, 0.60 * v02max),
        "Z2 (Aeróbico)": (0.60 * v02max, 0.70 * v02max),
        "Z3 (Tempo)": (0.70 * v02max, 0.80 * v02max),
        "Z4 (Limiar)": (0.80 * v02max, 0.90 * v02max),
        "Z5 (VO2 Max)": (0.90 * v02max, 1.00 * v02max)
    }
    
    zone_colors = {
        "Z1 (Recuperação)": "#4cc9f0",
        "Z2 (Aeróbico)": "#4895ef",
        "Z3 (Tempo)": "#4361ee",
        "Z4 (Limiar)": "#3f37c9",
        "Z5 (VO2 Max)": "#3a0ca3"
    }
    
    return zones, zone_colors

zones, zone_colors = calculate_zones(user_data["v02max"])

# Dieta premium com cache
@st.cache_data
def get_diet_plan():
    return {
        "Café da Manhã": {
            "Opção 1": "🥚 3 ovos + 🍞 2 fatias pão integral + 🍌 1 banana + 🌾 1 colher aveia",
            "Opção 2": "🥛 Vitamina (200ml leite + 🍌 1 banana + 🌾 1 colher aveia + 🌱 1 colher chia)",
            "Opção 3": "🍞 2 fatias pão integral + 🧀 queijo cottage + 🍓 1 fruta"
        },
        "Lanche da Manhã": {
            "Opção 1": "🍎 1 fruta + 🌰 10 castanhas",
            "Opção 2": "🥛 1 iogurte natural + 🌱 1 colher linhaça",
            "Opção 3": "🍞 1 fatia pão integral + 🥜 1 colher pasta amendoim"
        },
        "Almoço": {
            "Opção 1": "🍚 1 concha arroz + 🫘 1 concha feijão + 🍗 150g frango + 🥗 salada",
            "Opção 2": "🥔 2 batatas médias + 🥩 150g carne moída + 🥦 legumes refogados",
            "Opção 3": "🍚 1 concha arroz integral + 🐟 150g peixe + 🥦 brócolis cozido"
        },
        "Lanche da Tarde": {
            "Opção 1": "🥚 1 ovo cozido + 🍞 1 torrada integral",
            "Opção 2": "🥛 1 copo de vitamina (leite + fruta)",
            "Opção 3": "🥛 1 iogurte + 🍯 1 colher granola caseira"
        },
        "Jantar": {
            "Opção 1": "🍳 Omelete (3 ovos) + 🥗 salada + 🍞 1 fatia pão integral",
            "Opção 2": "🥩 150g carne + 🎃 purê de abóbora + 🥗 salada",
            "Opção 3": "🍜 Sopa de legumes com frango desfiado"
        },
        "Ceia": {
            "Opção 1": "🥛 1 copo leite morno",
            "Opção 2": "🥛 1 iogurte natural",
            "Opção 3": "🧀 1 fatia queijo branco"
        }
    }

diet_plan = get_diet_plan()

# Plano de treino premium com cache
@st.cache_data
def generate_workout_plan():
    plan = []
    current_date = date(2025, 8, 11)  # Data fixa de início
    
    for week in range(1, 9):  # 8 semanas
        for day in range(1, 7):  # 6 dias de treino/semana
            intensity = min(week / 8, 1.0)  # Progressão de 0 a 1
            
            if day == 1:  # Segunda - Endurance
                duration = f"{int(60 + 15 * intensity)}min"
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Ciclismo - Endurance",
                    "Duração": duration,
                    "Zona FC": "Z2 (Aeróbico)",
                    "FC Alvo": f"{int(zones['Z2 (Aeróbico)'][0])}-{int(zones['Z2 (Aeróbico)'][1])} bpm",
                    "Descrição": f"Pedal constante em terreno plano, mantendo FC na Z2. Semana {week}/8",
                    "Intensidade": f"{int(intensity * 100)}%",
                    "Semana": week
                }
            elif day == 2:  # Terça - Força
                sets = 3 + (1 if week > 4 else 0)
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Força - Membros Inferiores",
                    "Duração": "1h",
                    "Zona FC": "N/A",
                    "FC Alvo": "N/A",
                    "Descrição": f"Agachamento {sets}x12, Leg Press {sets}x12, Cadeira Extensora {sets}x15, Panturrilha {sets}x20",
                    "Intensidade": f"{int(intensity * 100)}%",
                    "Semana": week
                }
            elif day == 3:  # Quarta - Intervalado
                intervals = 6 + (2 if week > 2 else 0)
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Ciclismo - Intervalado",
                    "Duração": "1h",
                    "Zona FC": "Z4-Z5 (Limiar-VO2)",
                    "FC Alvo": f"{int(zones['Z4 (Limiar)'][0])}-{int(zones['Z5 (VO2 Max)'][1])} bpm",
                    "Descrição": f"{intervals}x (2min Z4 + 2min Z1 recuperação)",
                    "Intensidade": f"{int(intensity * 100)}%",
                    "Semana": week
                }
            elif day == 4:  # Quinta - Recuperação
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Ciclismo - Recuperação Ativa",
                    "Duração": "45min",
                    "Zona FC": "Z1 (Recuperação)",
                    "FC Alvo": f"{int(zones['Z1 (Recuperação)'][0])}-{int(zones['Z1 (Recuperação)'][1])} bpm",
                    "Descrição": "Pedal leve em terreno plano",
                    "Intensidade": "30%",
                    "Semana": week
                }
            elif day == 5:  # Sexta - Core/Superior
                sets = 3 + (1 if week > 3 else 0)
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Força - Core e Superior",
                    "Duração": "1h",
                    "Zona FC": "N/A",
                    "FC Alvo": "N/A",
                    "Descrição": f"Flexões {sets}x12, Remada Curvada {sets}x12, Prancha {sets}x1min, Abdominal Supra {sets}x20",
                    "Intensidade": f"{int(intensity * 100)}%",
                    "Semana": week
                }
            elif day == 6:  # Sábado - Longão
                duration = "2h30min" if week < 3 else "3h" if week < 6 else "3h30min"
                workout = {
                    "Dia": current_date.strftime("%d/%m/%Y"),
                    "Data": current_date,
                    "Dia da Semana": current_date.strftime("%A"),
                    "Tipo de Treino": "Ciclismo - Longão",
                    "Duração": duration,
                    "Zona FC": "Z2-Z3 (Aeróbico-Tempo)",
                    "FC Alvo": f"{int(zones['Z2 (Aeróbico)'][0])}-{int(zones['Z3 (Tempo)'][1])} bpm",
                    "Descrição": f"Pedal longo com variação de terreno. Duração: {duration}",
                    "Intensidade": f"{int(intensity * 100)}%",
                    "Semana": week
                }
            
            plan.append(workout)
            current_date += timedelta(days=1)
        
        current_date += timedelta(days=1)  # Domingo de descanso
    
    return pd.DataFrame(plan)

workout_plan = generate_workout_plan()

# Componentes reutilizáveis
def user_profile_card():
    """Componente de perfil do usuário para sidebar"""
    st.markdown(f"""
    <div class="card">
        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
            <div style="width: 50px; height: 50px; background: linear-gradient(135deg, var(--primary), var(--accent)); 
                        border-radius: 50%; display: flex; align-items: center; justify-content: center; 
                        margin-right: 1rem; color: white; font-size: 1.25rem; font-weight: bold;">
                {user_data['nome'][0]}
            </div>
            <div>
                <h3 style="margin: 0; font-size: 1.1rem;">{user_data['nome']}</h3>
                <p style="margin: 0; font-size: 0.8rem; color: #6c757d;">{user_data['plano']}</p>
            </div>
        </div>
        
        <div style="margin-top: 1rem;">
            <p><strong>📏 Altura:</strong> {user_data['altura']}m</p>
            <p><strong>⚖️ Peso:</strong> {user_data['peso']}kg</p>
            <p><strong>❤️ VO2 Máx:</strong> {user_data['v02max']} bpm</p>
            <p><strong>🎯 Objetivo:</strong> {user_data['objetivo']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def heart_rate_zones():
    """Componente de zonas de FC para sidebar"""
    st.markdown("### ❤️ Zonas de Frequência Cardíaca")
    for zone, (min_fc, max_fc) in zones.items():
        color = zone_colors[zone]
        st.markdown(f"""
        <div style="background: {color}15; padding: 0.7rem; border-radius: 8px; 
                    margin-bottom: 0.5rem; border-left: 3px solid {color};">
            <p style="margin: 0; font-weight: 500; color: {color};">{zone}</p>
            <p style="margin: 0; font-size: 0.85rem;">{int(min_fc)}-{int(max_fc)} bpm</p>
        </div>
        """, unsafe_allow_html=True)

def workout_day_card(workout):
    """Componente de card de treino do dia"""
    zone_color = zone_colors.get(workout["Zona FC"], "#4361ee")
    
    return f"""
    <div class="card card-highlight">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h3 style="margin: 0;">Treino do dia {workout['Dia']}</h3>
            <div style="background: {zone_color}15; color: {zone_color}; 
                        padding: 0.25rem 0.75rem; border-radius: 20px; 
                        font-size: 0.85rem; font-weight: 500;">
                {workout['Dia da Semana']}
            </div>
        </div>
        
        <div class="card-grid">
            <div class="card">
                <p style="margin: 0 0 0.3rem; font-size: 0.9rem; color: #6c757d;">Tipo de Treino</p>
                <p style="margin: 0; font-weight: 500;">{workout['Tipo de Treino']}</p>
            </div>
            
            <div class="card">
                <p style="margin: 0 0 0.3rem; font-size: 0.9rem; color: #6c757d;">Duração</p>
                <p style="margin: 0; font-weight: 500;">{workout['Duração']}</p>
            </div>
            
            <div class="card">
                <p style="margin: 0 0 0.3rem; font-size: 0.9rem; color: #6c757d;">Zona FC</p>
                <p style="margin: 0; font-weight: 500; color: {zone_color};">{workout['Zona FC']}</p>
            </div>
            
            <div class="card">
                <p style="margin: 0 0 0.3rem; font-size: 0.9rem; color: #6c757d;">Intensidade</p>
                <p style="margin: 0; font-weight: 500;">{workout['Intensidade']}</p>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 1rem;">
            <p style="margin: 0 0 0.5rem; font-weight: 500; color: #6c757d;">Descrição do Treino</p>
            <p style="margin: 0;">{workout['Descrição']}</p>
        </div>
        
        <div style="display: flex; gap: 0.75rem;">
            <button style="background: var(--primary); color: white; border: none; 
                          padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; 
                          transition: var(--transition); font-size: 0.9rem;">
                ✅ Marcar como Concluído
            </button>
            <button style="background: white; color: var(--primary); border: 1px solid var(--primary); 
                          padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; 
                          transition: var(--transition); font-size: 0.9rem;">
                ✏️ Editar Treino
            </button>
        </div>
    </div>
    """

def meal_option_card(option, description):
    """Componente de opção de refeição"""
    return f"""
    <div class="card">
        <h4 style="margin-top: 0; color: var(--primary);">{option}</h4>
        <p style="margin-bottom: 0.5rem;">{description}</p>
        <button style="background: var(--primary); color: white; border: none; 
                      padding: 0.3rem 0.8rem; border-radius: 6px; margin-top: 0.5rem; 
                      font-size: 0.8rem; cursor: pointer; transition: var(--transition);">
            ➕ Adicionar
        </button>
    </div>
    """

# Interface Principal
st.title("🏋️‍♂️ PerformanceFit Pro")
st.markdown("""
    <div class="card" style="background: linear-gradient(90deg, var(--primary), var(--secondary)); 
                color: white; margin-bottom: 1.5rem; padding: 1.25rem;">
        <h2 style="color: white; margin: 0;">Sistema de Controle de Treinos Premium</h2>
        <p style="margin: 0.5rem 0 0; opacity: 0.9;">Plano personalizado iniciando em 11/08/2025</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar Premium
with st.sidebar:
    user_profile_card()
    st.markdown("---")
    heart_rate_zones()
    st.markdown("---")
    
    # Progresso do plano
    st.markdown("### 📅 Progresso do Plano")
    current_week = 1  # Simulação - poderia ser dinâmico
    total_weeks = 8
    
    st.markdown(f"**Semana {current_week} de {total_weeks}**")
    st.markdown(f"""
    <div style="width: 100%; background-color: #e9ecef; border-radius: 10px; margin: 0.5rem 0;">
        <div style="height: 8px; border-radius: 10px; 
                    background: linear-gradient(90deg, var(--primary), var(--accent)); 
                    width: {current_week/total_weeks*100}%;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Download premium
    st.markdown("### 📤 Exportar Plano")
    if st.button("💾 Exportar para Excel", key="export_btn"):
        with st.spinner('Gerando arquivo premium...'):
            time.sleep(1)
            
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
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="PerformanceFit_Plano_Premium.xlsx" style="color: white; text-decoration: none;">⬇️ Baixar Plano Completo</a>'
            st.markdown(f"""
            <div style="background: var(--success); padding: 0.75rem; border-radius: 8px; 
                        text-align: center; margin-top: 1rem; animation: fadeIn 0.5s ease-out;">
                {href}
            </div>
            """, unsafe_allow_html=True)

# Abas principais premium
tab1, tab2, tab3 = st.tabs(["🏋️‍♂️ Plano de Treino", "🍏 Nutrição Premium", "📊 Análises"])

with tab1:
    # Seção de calendário premium
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2>📅 Calendário de Treinos</h2>
        <div class="card" style="padding: 0.5rem 1rem;">
            <p style="margin: 0; font-weight: 500;">Início: 11/08/2025</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Seletor de data premium
    min_date = workout_plan["Data"].min()
    max_date = workout_plan["Data"].max()
    
    selected_date = st.date_input(
        "🔍 Selecione a data para ver o treino:",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY",
        key="date_selector"
    )
    
    # Card de treino do dia
    selected_date_str = selected_date.strftime("%d/%m/%Y")
    selected_workout = workout_plan[workout_plan["Dia"] == selected_date_str]
    
    if not selected_workout.empty:
        workout = selected_workout.iloc[0]
        st.markdown(workout_day_card(workout), unsafe_allow_html=True)
    else:
        st.warning("Nenhum treino encontrado para a data selecionada.")
    
    # Filtros avançados
    st.markdown("---")
    st.markdown("### 🔍 Filtros Avançados")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox("Tipo de Treino", ["Todos"] + list(workout_plan["Tipo de Treino"].unique()))
    with col2:
        filter_week = st.selectbox("Semana", ["Todas"] + [f"Semana {i}" for i in range(1, 9)])
    with col3:
        filter_intensity = st.select_slider("Intensidade", options=["0-30%", "30-60%", "60-80%", "80-100%"])
    
    # Aplicar filtros
    filtered_plan = workout_plan.copy()
    if filter_type != "Todos":
        filtered_plan = filtered_plan[filtered_plan["Tipo de Treino"] == filter_type]
    if filter_week != "Todas":
        week_num = int(filter_week.split()[1])
        filtered_plan = filtered_plan[filtered_plan["Semana"] == week_num]
    
    # Mostrar tabela premium
    st.markdown("### 📋 Lista Completa de Treinos")
    st.dataframe(
        filtered_plan.drop(columns=["Data", "Semana"]), 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Dia": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Duraçã": st.column_config.ProgressColumn(
                "Duração",
                help="Duração do treino",
                format="%f",
                min_value=0,
                max_value=240
            )
        }
    )
    
    # Gráficos de análise
    st.markdown("---")
    st.markdown("### 📊 Análise de Treinos")
    
    fig1 = px.pie(
        workout_plan, 
        names="Tipo de Treino", 
        title="Distribuição de Tipos de Treino",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2>🍏 Plano Nutricional Premium</h2>
        <div class="card" style="background: #4cc9f015; color: #4cc9f0; padding: 0.5rem 1rem;">
            <p style="margin: 0; font-weight: 500;">{user_data['peso']}kg | {user_data['altura']}m</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Seção de macros
    st.markdown("### 📊 Macronutrientes Diários")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="card" style="text-align: center;">
            <p style="margin: 0 0 0.3rem; font-size: 0.9rem; color: #6c757d;">Calorias</p>
            <p style="margin: 0; font-size: 1.4rem; font-weight: 700; color: var(--accent);">2,800</p>
            <p style="margin: 0.3rem 0 0; font-size: 0.8rem;">kcal/dia</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="card" style="text-align: center;">
            <p style="margin: 0 0 0.3rem; font-size: 0.9rem; color: #6c757d;">Proteínas</p>
            <p style="margin: 0; font-size: 1.4rem; font-weight: 700; color: var(--accent);">210g</p>
            <p style="margin: 0.3rem 0 0; font-size: 0.8rem;">(30% kcal)</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="card" style="text-align: center;">
            <p style="margin: 0 0 0.3rem; font-size: 0.9rem; color: #6c757d;">Carboidratos</p>
            <p style="margin: 0; font-size: 1.4rem; font-weight: 700; color: var(--accent);">350g</p>
            <p style="margin: 0.3rem 0 0; font-size: 0.8rem;">(50% kcal)</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="card" style="text-align: center;">
            <p style="margin: 0 0 0.3rem; font-size: 0.9rem; color: #6c757d;">Gorduras</p>
            <p style="margin: 0; font-size: 1.4rem; font-weight: 700; color: var(--accent);">78g</p>
            <p style="margin: 0.3rem 0 0; font-size: 0.8rem;">(20% kcal)</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Plano alimentar premium
    for meal, options in diet_plan.items():
        with st.expander(f"🍽️ {meal}", expanded=True):
            cols = st.columns(len(options))
            for i, (opt, desc) in enumerate(options.items()):
                with cols[i]:
                    st.markdown(meal_option_card(opt, desc), unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 💡 Recomendações Nutricionais")
    
    rec_col1, rec_col2 = st.columns(2)
    with rec_col1:
        st.markdown("""
        <div class="card">
            <h4 style="margin-top: 0;">📌 Dicas de Alimentação</h4>
            <ul style="padding-left: 1.2rem; margin-bottom: 0;">
                <li>Consuma proteína em todas as refeições</li>
                <li>Hidrate-se bem (3-4L de água/dia)</li>
                <li>Prefira carboidratos complexos</li>
                <li>Gorduras saudáveis em quantidades moderadas</li>
                <li>Legumes e verduras à vontade</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with rec_col2:
        st.markdown("""
        <div class="card">
            <h4 style="margin-top: 0;">⏰ Timing Nutricional</h4>
            <ul style="padding-left: 1.2rem; margin-bottom: 0;">
                <li><strong>Pré-treino:</strong> Carboidratos + proteína leve</li>
                <li><strong>Pós-treino:</strong> Proteína + carboidratos rápidos</li>
                <li><strong>Noite:</strong> Proteína de digestão lenta</li>
                <li><strong>Dia de descanso:</strong> Menos carboidratos, mais gordura</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2>📊 Análises de Performance</h2>
        <div class="card" style="background: #f7258515; color: #f72585; padding: 0.5rem 1rem;">
            <p style="margin: 0; font-weight: 500;">Última Atualização: Hoje</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Gráficos de performance
    st.markdown("### 📈 Progresso Semanal")
    
    # Dados simulados para os gráficos
    weeks = list(range(1, 9))
    performance_data = {
        "Volume de Treino (horas)": [4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8],
        "Intensidade Média (%)": [60, 65, 70, 75, 80, 85, 90, 95],
        "Frequência Cardíaca Média": [140, 138, 136, 134, 132, 130, 128, 126],
        "Peso (kg)": [108, 106, 105, 104, 103, 102, 101, 100]
    }
    
    # Seleção de métrica
    metric = st.selectbox("Selecione a métrica", list(performance_data.keys()))
    
    fig = px.line(
        x=weeks,
        y=performance_data[metric],
        title=f"Progresso de {metric}",
        labels={"x": "Semana", "y": metric},
        markers=True
    )
    fig.update_traces(line_color='#4361ee', line_width=2.5)
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#f0f2f6')
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Métricas de performance
    st.markdown("---")
    st.markdown("### 🏆 Métricas Chave")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="card">
            <h4 style="margin-top: 0; color: var(--primary);">VO2 Máx</h4>
            <div style="display: flex; align-items: baseline;">
                <span style="font-size: 1.75rem; font-weight: 700;">173</span>
                <span style="margin-left: 0.5rem; color: var(--success); font-weight: 500; font-size: 0.9rem;">(+5% desde o início)</span>
            </div>
            <div style="width: 100%; background-color: #e9ecef; border-radius: 10px; margin: 0.75rem 0 0.5rem;">
                <div style="height: 8px; border-radius: 10px; background: linear-gradient(90deg, var(--success), var(--accent)); width: 85%;"></div>
            </div>
            <p style="margin: 0; font-size: 0.85rem; color: #6c757d;">Objetivo: 180</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="card">
            <h4 style="margin-top: 0; color: var(--primary);">Frequência Cardíaca de Repouso</h4>
            <div style="display: flex; align-items: baseline;">
                <span style="font-size: 1.75rem; font-weight: 700;">58</span>
                <span style="margin-left: 0.5rem; color: var(--success); font-weight: 500; font-size: 0.9rem;">(-3 bpm desde o início)</span>
            </div>
            <div style="width: 100%; background-color: #e9ecef; border-radius: 10px; margin: 0.75rem 0 0.5rem;">
                <div style="height: 8px; border-radius: 10px; background: linear-gradient(90deg, var(--success), var(--accent)); width: 75%;"></div>
            </div>
            <p style="margin: 0; font-size: 0.85rem; color: #6c757d;">Objetivo: 55</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <h4 style="margin-top: 0; color: var(--primary);">Força Relativa</h4>
            <div style="display: flex; align-items: baseline;">
                <span style="font-size: 1.75rem; font-weight: 700;">1.6x</span>
                <span style="margin-left: 0.5rem; color: var(--success); font-weight: 500; font-size: 0.9rem;">(+0.2x desde o início)</span>
            </div>
            <div style="width: 100%; background-color: #e9ecef; border-radius: 10px; margin: 0.75rem 0 0.5rem;">
                <div style="height: 8px; border-radius: 10px; background: linear-gradient(90deg, var(--success), var(--accent)); width: 65%;"></div>
            </div>
            <p style="margin: 0; font-size: 0.85rem; color: #6c757d;">Objetivo: 1.8x peso corporal</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="card">
            <h4 style="margin-top: 0; color: var(--primary);">% Gordura Corporal</h4>
            <div style="display: flex; align-items: baseline;">
                <span style="font-size: 1.75rem; font-weight: 700;">18%</span>
                <span style="margin-left: 0.5rem; color: var(--success); font-weight: 500; font-size: 0.9rem;">(-2% desde o início)</span>
            </div>
            <div style="width: 100%; background-color: #e9ecef; border-radius: 10px; margin: 0.75rem 0 0.5rem;">
                <div style="height: 8px; border-radius: 10px; background: linear-gradient(90deg, var(--success), var(--accent)); width: 60%;"></div>
            </div>
            <p style="margin: 0; font-size: 0.85rem; color: #6c757d;">Objetivo: 15%</p>
        </div>
        """, unsafe_allow_html=True)

# Rodapé Premium
st.markdown("---")
st.markdown("""
<div class="card" style="background: linear-gradient(90deg, var(--primary), var(--secondary)); 
            color: white; text-align: center; margin-top: 2rem; padding: 1.25rem;">
    <h3 style="margin: 0 0 0.5rem; font-size: 1.25rem;">PerformanceFit Pro</h3>
    <p style="margin: 0; opacity: 0.9; font-size: 0.95rem;">Sistema de controle de treinos e nutrição avançado</p>
    <p style="margin: 0.5rem 0 0; font-size: 0.8rem; opacity: 0.7;">© 2025 Todos os direitos reservados | Versão 2.0 Premium</p>
</div>
""", unsafe_allow_html=True)
