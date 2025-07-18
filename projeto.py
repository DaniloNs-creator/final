import streamlit as st
from streamlit.components.v1 import html
from datetime import datetime, timedelta

# Configuração inicial da página
st.set_page_config(
    page_title="Performance Sport Agency",
    page_icon="🚴‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Avançado incorporado diretamente no código
st.markdown("""
<style>
:root {
    --primary: #2c3e50;
    --secondary: #3498db;
    --accent: #e74c3c;
    --light: #ecf0f1;
    --dark: #2c3e50;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

.header {
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    color: white;
    padding: 2rem;
    border-radius: 10px;
    margin-bottom: 2rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    animation: fadeIn 1s ease-out;
}

.header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

.header p {
    font-size: 1.2rem;
    opacity: 0.9;
}

.card {
    background: white;
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    animation: fadeIn 0.8s ease-out;
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}

.section-title {
    color: var(--primary);
    border-bottom: 3px solid var(--secondary);
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
    font-size: 1.8rem;
}

.btn {
    background: var(--secondary);
    color: white;
    border: none;
    padding: 0.8rem 1.5rem;
    border-radius: 30px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 10px rgba(52, 152, 219, 0.3);
    display: inline-block;
    margin: 0.5rem 0;
}

.btn:hover {
    background: var(--primary);
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(52, 152, 219, 0.4);
}

.progress-container {
    width: 100%;
    background-color: #f1f1f1;
    border-radius: 10px;
    margin: 1rem 0;
}

.progress-bar {
    height: 20px;
    border-radius: 10px;
    background: linear-gradient(90deg, var(--secondary), var(--accent));
    text-align: center;
    line-height: 20px;
    color: white;
    transition: width 1s ease-in-out;
    animation: pulse 2s infinite;
}

.meal-card {
    background: #f8f9fa;
    border-left: 5px solid var(--secondary);
    border-radius: 5px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.meal-title {
    font-weight: bold;
    color: var(--primary);
    margin-bottom: 0.5rem;
}

.workout-day {
    background: #e8f4fc;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    border-left: 5px solid var(--accent);
}

.day-title {
    font-weight: bold;
    color: var(--accent);
    margin-bottom: 0.5rem;
}

.exercise {
    margin-left: 1rem;
    margin-bottom: 0.5rem;
}

.timeline {
    position: relative;
    max-width: 1200px;
    margin: 0 auto;
}

.timeline::after {
    content: '';
    position: absolute;
    width: 6px;
    background-color: var(--secondary);
    top: 0;
    bottom: 0;
    left: 50%;
    margin-left: -3px;
}

.timeline-item {
    padding: 10px 40px;
    position: relative;
    width: 50%;
    box-sizing: border-box;
}

.timeline-item::after {
    content: '';
    position: absolute;
    width: 25px;
    height: 25px;
    right: -12px;
    background-color: white;
    border: 4px solid var(--accent);
    top: 15px;
    border-radius: 50%;
    z-index: 1;
}

.left {
    left: 0;
}

.right {
    left: 50%;
}

.left::before {
    content: " ";
    height: 0;
    position: absolute;
    top: 22px;
    width: 0;
    z-index: 1;
    right: 30px;
    border: medium solid var(--secondary);
    border-width: 10px 0 10px 10px;
    border-color: transparent transparent transparent var(--secondary);
}

.right::before {
    content: " ";
    height: 0;
    position: absolute;
    top: 22px;
    width: 0;
    z-index: 1;
    left: 30px;
    border: medium solid var(--secondary);
    border-width: 10px 10px 10px 0;
    border-color: transparent var(--secondary) transparent transparent;
}

.right::after {
    left: -12px;
}

.timeline-content {
    padding: 20px 30px;
    background-color: white;
    position: relative;
    border-radius: 6px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

@media screen and (max-width: 768px) {
    .timeline::after {
        left: 31px;
    }
    
    .timeline-item {
        width: 100%;
        padding-left: 70px;
        padding-right: 25px;
    }
    
    .timeline-item::before {
        left: 60px;
        border: medium solid var(--secondary);
        border-width: 10px 10px 10px 0;
        border-color: transparent var(--secondary) transparent transparent;
    }
    
    .left::after, .right::after {
        left: 18px;
    }
    
    .right {
        left: 0%;
    }
}
</style>
""", unsafe_allow_html=True)

# Cabeçalho com animação
st.markdown("""
<div class="header">
    <h1>Performance Sport Agency</h1>
    <p>Seu plano personalizado de 60 dias para emagrecimento e performance no ciclismo</p>
</div>
""", unsafe_allow_html=True)

# Dados do usuário
user_data = {
    "name": "Atleta",
    "age": 28,
    "height": 1.87,
    "weight": 108,
    "goal": "Emagrecimento e Performance no Ciclismo",
    "start_date": datetime.now().strftime("%d/%m/%Y"),
    "end_date": (datetime.now() + timedelta(days=60)).strftime("%d/%m/%Y")
}

# Barra de progresso
st.markdown(f"""
<div class="card">
    <h2 class="section-title">Seu Progresso</h2>
    <p>Meta de 60 dias: {user_data['start_date']} - {user_data['end_date']}</p>
    <div class="progress-container">
        <div class="progress-bar" style="width: 0%">0%</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Abas para navegação
tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "🍽 Plano Alimentar", "💪 Rotina de Treinos"])

with tab1:
    st.markdown(f"""
    <div class="card">
        <h2 class="section-title">Seu Perfil</h2>
        <p><strong>Nome:</strong> {user_data['name']}</p>
        <p><strong>Idade:</strong> {user_data['age']} anos</p>
        <p><strong>Altura:</strong> {user_data['height']}m</p>
        <p><strong>Peso atual:</strong> {user_data['weight']}kg</p>
        <p><strong>Objetivo:</strong> {user_data['goal']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card">
        <h2 class="section-title">Metas para 60 Dias</h2>
        <div class="timeline">
            <div class="timeline-item left">
                <div class="timeline-content">
                    <h3>Semana 1-2</h3>
                    <p>Adaptação metabólica e estabelecimento de rotina</p>
                    <p>Meta de peso: -2kg</p>
                </div>
            </div>
            <div class="timeline-item right">
                <div class="timeline-content">
                    <h3>Semana 3-4</h3>
                    <p>Intensificação dos treinos e ajuste nutricional</p>
                    <p>Meta de peso: -3kg</p>
                </div>
            </div>
            <div class="timeline-item left">
                <div class="timeline-content">
                    <h3>Semana 5-6</h3>
                    <p>Foco em endurance e potência no ciclismo</p>
                    <p>Meta de peso: -3kg</p>
                </div>
            </div>
            <div class="timeline-item right">
                <div class="timeline-content">
                    <h3>Semana 7-8</h3>
                    <p>Consolidação de performance e perda de gordura</p>
                    <p>Meta de peso: -3kg</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with tab2:
    st.markdown("""
    <div class="card">
        <h2 class="section-title">Plano Alimentar para Emagrecimento</h2>
        <p>Dieta baseada em alimentos acessíveis e nutritivos para performance no ciclismo</p>
        <p><strong>Meta calórica diária:</strong> ~2,200 kcal (déficit moderado)</p>
        <p><strong>Distribuição macro:</strong> 40% Carboidratos | 35% Proteínas | 25% Gorduras</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>Dia Tipo (Treino)</h3>
            
            <div class="meal-card">
                <div class="meal-title">Café da Manhã</div>
                <p>• 3 ovos mexidos com espinafre</p>
                <p>• 2 fatias de pão integral</p>
                <p>• 1 banana</p>
                <p>• 1 colher de sopa de pasta de amendoim</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Lanche Pré-Treino</div>
                <p>• 1 copo de aveia com 1 colher de whey</p>
                <p>• 1 xícara de café preto</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Almoço</div>
                <p>• 150g de frango grelhado</p>
                <p>• 1 concha de arroz integral</p>
                <p>• 1 concha de feijão</p>
                <p>• Salada à vontade (brócolis, cenoura, beterraba)</p>
                <p>• 1 fio de azeite</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Lanche da Tarde</div>
                <p>• 1 iogurte natural</p>
                <p>• 1 colher de linhaça</p>
                <p>• 1 fruta (maçã ou pera)</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Jantar</div>
                <p>• 150g de carne moída magra</p>
                <p>• Purê de abóbora ou batata-doce</p>
                <p>• Legumes refogados (berinjela, abobrinha)</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Ceia</div>
                <p>• 1 fatia de queijo branco</p>
                <p>• 1 punhado de castanhas</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>Dia Tipo (Descanso)</h3>
            
            <div class="meal-card">
                <div class="meal-title">Café da Manhã</div>
                <p>• 2 ovos cozidos</p>
                <p>• 1 fatia de pão integral</p>
                <p>• 1/2 abacate</p>
                <p>• Chá verde</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Lanche da Manhã</div>
                <p>• 1 iogurte natural com 1 colher de chia</p>
                <p>• 5 morangos</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Almoço</div>
                <p>• 1 posta de peixe (sardinha ou atum)</p>
                <p>• 1/2 concha de arroz integral</p>
                <p>• Lentilha cozida</p>
                <p>• Salada verde à vontade</p>
                <p>• 1 fio de azeite</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Lanche da Tarde</div>
                <p>• Vitamina de abacate com leite desnatado</p>
                <p>• 1 colher de sopa de aveia</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Jantar</div>
                <p>• Omelete de 2 ovos com queijo branco</p>
                <p>• Salada de folhas verdes</p>
                <p>• 1 colher de sopa de quinoa</p>
            </div>
            
            <div class="meal-card">
                <div class="meal-title">Ceia</div>
                <p>• 1 copo de leite desnatado</p>
                <p>• Canela em pó</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card">
        <h3>Orientações Nutricionais</h3>
        <ul>
            <li>Mantenha hidratação constante (3-4L de água/dia)</li>
            <li>Priorize alimentos integrais e minimamente processados</li>
            <li>Consuma proteína em todas as refeições</li>
            <li>Inclua gorduras saudáveis (azeite, castanhas, abacate)</li>
            <li>Nos dias de treino intenso, aumente os carboidratos</li>
            <li>Nos dias de descanso, reduza ligeiramente os carboidratos</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with tab3:
    st.markdown("""
    <div class="card">
        <h2 class="section-title">Rotina de Treinos - 60 Dias</h2>
        <p>Programa de 6 dias por semana com foco em emagrecimento e desenvolvimento para ciclismo</p>
        <p><strong>Duração:</strong> Dias de semana até 1h30 | Finais de semana sem limite</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Semana tipo
    st.markdown("""
    <div class="card">
        <h3>Estrutura Semanal</h3>
        
        <div class="workout-day">
            <div class="day-title">Segunda-feira: Treino de Força (Membros Inferiores + Core)</div>
            <div class="exercise">• Agachamento livre: 4x8-10</div>
            <div class="exercise">• Leg press: 3x10-12</div>
            <div class="exercise">• Stiff: 3x10</div>
            <div class="exercise">• Elevação pélvica: 3x12</div>
            <div class="exercise">• Prancha abdominal: 3x40s</div>
            <div class="exercise">• Bike ergométrica (leve): 15min</div>
        </div>
        
        <div class="workout-day">
            <div class="day-title">Terça-feira: Ciclismo Intervalado</div>
            <div class="exercise">• Aquecimento: 15min leve</div>
            <div class="exercise">• Intervalos: 8x(2min forte / 2min leve)</div>
            <div class="exercise">• Desaquecimento: 10min leve</div>
            <div class="exercise">• Alongamento pós-treino</div>
        </div>
        
        <div class="workout-day">
            <div class="day-title">Quarta-feira: Treino de Força (Superiores + Mobilidade)</div>
            <div class="exercise">• Barra fixa assistida: 3x6-8</div>
            <div class="exercise">• Remada curvada: 3x10</div>
            <div class="exercise">• Desenvolvimento militar: 3x10</div>
            <div class="exercise">• Mobilidade de quadril e tornozelo</div>
            <div class="exercise">• Esteira inclinada: 15min</div>
        </div>
        
        <div class="workout-day">
            <div class="day-title">Quinta-feira: Ciclismo Endurance</div>
            <div class="exercise">• Pedalada contínua: 45-60min em ritmo moderado</div>
            <div class="exercise">• Manter cadência entre 80-90rpm</div>
            <div class="exercise">• Alongamento pós-treino</div>
        </div>
        
        <div class="workout-day">
            <div class="day-title">Sexta-feira: Treino Funcional para Ciclismo</div>
            <div class="exercise">• Saltos em caixa: 3x10</div>
            <div class="exercise">• Afundo com salto: 3x8 cada perna</div>
            <div class="exercise">• Burpees: 3x12</div>
            <div class="exercise">• Bike sprints: 10x30s</div>
            <div class="exercise">• Core: Russian twist 3x15 cada lado</div>
        </div>
        
        <div class="workout-day">
            <div class="day-title">Sábado: Long Ride</div>
            <div class="exercise">• Pedalada longa: 2-4 horas (progressivo)</div>
            <div class="exercise">• Incluir subidas graduais</div>
            <div class="exercise">• Hidratação e reposição energética durante</div>
        </div>
        
        <div class="workout-day">
            <div class="day-title">Domingo: Recuperação Ativa</div>
            <div class="exercise">• Caminhada ou pedalada leve: 30-45min</div>
            <div class="exercise">• Alongamento completo</div>
            <div class="exercise">• Rolagem com foam roller</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Progressão ao longo das semanas
    st.markdown("""
    <div class="card">
        <h3>Progressão do Treino</h3>
        <table>
            <tr>
                <th>Fase</th>
                <th>Semanas</th>
                <th>Foco</th>
                <th>Ajustes</th>
            </tr>
            <tr>
                <td>Adaptação</td>
                <td>1-2</td>
                <td>Base aeróbica e técnica</td>
                <td>Volume moderado, intensidade baixa</td>
            </tr>
            <tr>
                <td>Construção</td>
                <td>3-6</td>
                <td>Força específica e endurance</td>
                <td>Aumento gradual de volume e intensidade</td>
            </tr>
            <tr>
                <td>Intensificação</td>
                <td>7-9</td>
                <td>Potência e limiar láctico</td>
                <td>Intervalos mais intensos, redução de volume</td>
            </tr>
            <tr>
                <td>Tapering</td>
                <td>10</td>
                <td>Recuperação e performance</td>
                <td>Redução de volume, manutenção de intensidade</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

# Rodapé
st.markdown(f"""
<div class="card" style="text-align: center; margin-top: 2rem;">
    <p>Performance Sport Agency © 2023 - Plano personalizado para {user_data['name']}</p>
    <p>Início: {user_data['start_date']} | Término: {user_data['end_date']}</p>
    <button class="btn" onclick="alert('Plano salvo com sucesso!')">Salvar Plano Completo</button>
</div>
""", unsafe_allow_html=True)

# Script JavaScript para animar a barra de progresso
html_script = f"""
<script>
// Animar barra de progresso
document.addEventListener('DOMContentLoaded', function() {{
    const progressBar = document.querySelector('.progress-bar');
    let width = 0;
    
    // Converter datas para o formato JavaScript (MM/DD/YYYY)
    const startDateParts = "{user_data['start_date']}".split('/');
    const endDateParts = "{user_data['end_date']}".split('/');
    
    const startDate = new Date(startDateParts[1] + '/' + startDateParts[0] + '/' + startDateParts[2]);
    const endDate = new Date(endDateParts[1] + '/' + endDateParts[0] + '/' + endDateParts[2]);
    const today = new Date();
    
    // Calcular progresso
    const totalDays = (endDate - startDate) / (1000 * 60 * 60 * 24);
    const daysPassed = (today - startDate) / (1000 * 60 * 60 * 24);
    let progress = (daysPassed / totalDays) * 100;
    
    // Limitar entre 0 e 100
    progress = Math.max(0, Math.min(100, progress));
    
    // Animar
    const interval = setInterval(function() {{
        if (width >= progress) {{
            clearInterval(interval);
        }} else {{
            width++;
            progressBar.style.width = width + '%';
            progressBar.textContent = Math.round(width) + '%';
        }}
    }}, 20);
}});
</script>
"""

html(html_script, height=0)
